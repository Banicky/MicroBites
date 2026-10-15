"""MicroBites API.

Run: fastapi dev main.py
"""
import os
from functools import lru_cache
from typing import Literal

import voyageai
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from db import DB_CONFIG, to_vector

# Values of recipe.diet_tags, filled by classify_diet.py
Diet = Literal["vegan", "vegetarian", "pescatarian", "gluten-free", "dairy-free", "egg-free", "nut-free", "keto"]

SUMMARY_COLUMNS = "id, name, description, diet_tags, servings, serving_size, image"

voyage_client = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"))
VOYAGE_MODEL = os.environ.get("VOYAGE_MODEL")
pool = ThreadedConnectionPool(1, 10, **DB_CONFIG)

app = FastAPI(title="MicroBites")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@lru_cache(maxsize=256)
def embed_query(q):
    # Cached so toggling diet filters on the same search doesn't call Voyage again
    return to_vector(voyage_client.embed([q], model=VOYAGE_MODEL, input_type="query").embeddings[0])


def run_query(sql, params):
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        pool.putconn(conn)


@app.get("/search")
def search(
    q: str = Query(min_length=1, max_length=300),
    diet: list[Diet] = Query(default=[]),
    limit: int = Query(20, ge=1, le=50),
):
    query_embedding = embed_query(q.strip())
    # Diet filters apply before ranking, so the results are the best matches
    # among recipes that fit every selected diet, not a subset of the unfiltered top results.
    # 5k rows: an exact scan is fast and, unlike an ANN index, never drops
    # matches when the filter is selective.
    rows = run_query(
        f"""
        select {SUMMARY_COLUMNS}, 1 - (embedding <=> %s::vector) as score
        from recipe
        where diet_tags @> %s
        order by embedding <=> %s::vector
        limit %s
        """,
        [query_embedding, list(diet), query_embedding, limit],
    )
    return {"query": q, "diets": diet, "results": rows}


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    rows = run_query(
        f"select {SUMMARY_COLUMNS}, ingredients_raw, steps from recipe where id = %s",
        [recipe_id],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return rows[0]
