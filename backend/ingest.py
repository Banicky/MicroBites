"""Load recipes_sample.csv into Postgres with Voyage embeddings.

Safe to re-run: recipes already in the table are skipped.
Usage:
    python ingest.py            # load new recipes
    python ingest.py --reembed  # rebuild embeddings of existing rows in place
"""
import csv, html, json, re
import os
import sys
from pathlib import Path

import voyageai
from psycopg2.extras import execute_values

from db import connect, to_vector

CSV_PATH = Path(__file__).resolve().parent.parent / "dataset" / "recipes_sample.csv"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
BATCH_SIZE = 128


def unescape(text):
    # The dataset keeps HTML entities from food.com ("&amp;", "&eacute;"),
    # some double-encoded ("&amp;deg;"), so decode until nothing changes
    while (decoded := html.unescape(text)) != text:
        text = decoded
    return text


def clean(text):
    return re.sub(r"\s+", " ", unescape(text or "")).strip()


def parse_list(value):
    try:
        items = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []
    return [clean(str(item)) for item in items if clean(str(item))]


def build_embed_text(name, description, ingredients_raw):
    # What the embedding "sees": the parts a user is likely to search by.
    # Uses ingredients_raw: the dataset's cleaned `ingredients` column drops
    # common items (eggs, flour, sugar...) from most recipes.
    return "\n".join(filter(None, [
        name,
        description,
        "Ingredients: " + "; ".join(ingredients_raw),
    ]))


def parse_row(row):
    recipe = {
        "id": int(row["id"]),
        "name": clean(row["name"]),
        "description": clean(row["description"]) or None,
        "ingredients_raw": parse_list(row["ingredients_raw"]),
        "steps": parse_list(row["steps"]),
        "servings": float(row["servings"]) if row["servings"] else None,
        "serving_size": clean(row["serving_size"]) or None,
    }
    recipe["embed_text"] = build_embed_text(recipe["name"], recipe["description"], recipe["ingredients_raw"])
    return recipe


def embed(voyage_client, model, texts):
    return voyage_client.embed(texts, model=model, input_type="document", truncation=True).embeddings


def reembed(cursor, conn, voyage_client, model):
    """Rebuild embed_text and embeddings for rows already in the table, updating in place.

    Only rows whose embed_text would change are re-embedded."""
    cursor.execute("select id, name, description, ingredients_raw, embed_text from recipe order by id")
    rows = [
        (row[0], text)
        for row in cursor.fetchall()
        if (text := build_embed_text(*row[1:4])) != row[4]
    ]
    print(f"{len(rows)} recipes to re-embed")
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        embeddings = embed(voyage_client, model, [text for _, text in batch])
        execute_values(
            cursor,
            """
            update recipe set embed_text = data.embed_text, embedding = data.embedding::vector
            from (values %s) as data (id, embed_text, embedding)
            where recipe.id = data.id
            """,
            [(recipe_id, text, to_vector(e)) for (recipe_id, text), e in zip(batch, embeddings)],
        )
        conn.commit()
        print(f"{min(start + BATCH_SIZE, len(rows))}/{len(rows)}")


def main():
    voyage_client = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"), max_retries=5)
    model = os.environ.get("VOYAGE_MODEL")

    conn = connect()
    cursor = conn.cursor()

    if "--reembed" in sys.argv:
        reembed(cursor, conn, voyage_client, model)
        conn.close()
        return

    cursor.execute(SCHEMA_PATH.read_text())
    conn.commit()

    cursor.execute("select id from recipe")
    existing = {row[0] for row in cursor.fetchall()}

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        recipes = [parse_row(row) for row in csv.DictReader(f)]
    recipes = [r for r in recipes if r["id"] not in existing]
    print(f"{len(existing)} already ingested, {len(recipes)} to go")

    for start in range(0, len(recipes), BATCH_SIZE):
        batch = recipes[start:start + BATCH_SIZE]
        embeddings = embed(voyage_client, model, [r["embed_text"] for r in batch])
        execute_values(
            cursor,
            """
            insert into recipe (id, name, description, ingredients_raw, steps,
                                servings, serving_size, embed_text, embedding)
            values %s
            on conflict (id) do nothing
            """,
            [
                (r["id"], r["name"], r["description"], r["ingredients_raw"],
                 r["steps"], r["servings"], r["serving_size"], r["embed_text"],
                 to_vector(embedding))
                for r, embedding in zip(batch, embeddings)
            ],
        )
        conn.commit()
        print(f"{min(start + BATCH_SIZE, len(recipes))}/{len(recipes)}")

    conn.close()


if __name__ == "__main__":
    main()
