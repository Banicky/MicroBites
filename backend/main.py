"""MicroBites API.

Run: fastapi dev main.py
Every endpoint except /auth/* requires a logged-in user whose account was
unlocked with the access code (see auth.py), since they spend API credits.
"""
import os
import threading
from collections import defaultdict
from functools import lru_cache
from typing import Literal

import anthropic
import httpx
import voyageai
from fastapi import Depends, FastAPI, HTTPException, Query
from psycopg2.extras import Json

import auth
import nutrition
from db import query, to_vector

# Values of recipe.diet_tags, filled by classify_diet.py
Diet = Literal["vegan", "vegetarian", "pescatarian", "gluten-free", "dairy-free", "egg-free", "nut-free", "keto"]

SUMMARY_COLUMNS = "r.id, r.name, r.description, r.diet_tags, r.servings, r.serving_size, r.image"
# Whether the current user saved the recipe; expects the user id as a parameter
IS_FAVORITE = "exists(select 1 from favorite f where f.recipe_id = r.id and f.user_id = %s) as is_favorite"

voyage_client = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"))
VOYAGE_MODEL = os.environ.get("VOYAGE_MODEL")

# The frontend reaches this API through a same-origin proxy (Vite in development,
# nginx in production), so no CORS setup is needed and none is allowed.
app = FastAPI(title="MicroBites")
app.include_router(auth.router)


@lru_cache(maxsize=256)
def embed_query(q):
    # Cached so toggling diet filters on the same search doesn't call Voyage again
    return to_vector(voyage_client.embed([q], model=VOYAGE_MODEL, input_type="query").embeddings[0])


@app.get("/search")
def search(
    q: str = Query(min_length=1, max_length=300),
    diet: list[Diet] = Query(default=[]),
    limit: int = Query(20, ge=1, le=50),
    user=Depends(auth.user_with_access),
):
    query_embedding = embed_query(q.strip())
    # Diet filters apply before ranking, so the results are the best matches
    # among recipes that fit every selected diet, not a subset of the unfiltered top results.
    # 5k rows: an exact scan is fast and, unlike an ANN index, never drops
    # matches when the filter is selective.
    rows = query(
        f"""
        select {SUMMARY_COLUMNS}, {IS_FAVORITE}, 1 - (r.embedding <=> %s::vector) as score
        from recipe r
        where r.diet_tags @> %s
        order by r.embedding <=> %s::vector
        limit %s
        """,
        [user["id"], query_embedding, list(diet), query_embedding, limit],
    )
    return {"query": q, "diets": diet, "results": rows}


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int, user=Depends(auth.user_with_access)):
    rows = query(
        f"select {SUMMARY_COLUMNS}, {IS_FAVORITE}, r.ingredients_raw, r.steps, r.nutrition from recipe r where r.id = %s",
        [user["id"], recipe_id],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return rows[0]


@app.get("/favorites")
def list_favorites(user=Depends(auth.user_with_access)):
    return query(
        f"""
        select {SUMMARY_COLUMNS}, true as is_favorite
        from favorite f join recipe r on r.id = f.recipe_id
        where f.user_id = %s
        order by f.created_at desc
        """,
        [user["id"]],
    )


@app.put("/favorites/{recipe_id}")
def add_favorite(recipe_id: int, user=Depends(auth.user_with_access)):
    rows = query(
        """
        insert into favorite (user_id, recipe_id)
        select %s, id from recipe where id = %s
        on conflict do nothing
        returning recipe_id
        """,
        [user["id"], recipe_id],
    )
    if not rows and not query("select 1 from recipe where id = %s", [recipe_id]):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"recipe_id": recipe_id, "is_favorite": True}


@app.delete("/favorites/{recipe_id}")
def remove_favorite(recipe_id: int, user=Depends(auth.user_with_access)):
    query("delete from favorite where user_id = %s and recipe_id = %s", [user["id"], recipe_id])
    return {"recipe_id": recipe_id, "is_favorite": False}


# One analysis per recipe at a time, so double clicks don't pay twice
analysis_locks = defaultdict(threading.Lock)


@app.post("/recipes/{recipe_id}/nutrition")
def analyze_nutrition(recipe_id: int, user=Depends(auth.user_with_access)):
    with analysis_locks[recipe_id]:
        rows = query(
            "select id, name, ingredients_raw, servings, nutrition from recipe where id = %s",
            [recipe_id],
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Recipe not found")
        recipe = rows[0]
        if recipe["nutrition"]:
            return recipe["nutrition"]

        try:
            result = nutrition.analyze(recipe)
        except anthropic.APIError as exc:
            raise HTTPException(status_code=502, detail=f"Claude request failed: {exc}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"USDA FoodData Central request failed: {exc}") from exc

        query("update recipe set nutrition = %s where id = %s", [Json(result), recipe_id])
        return result
