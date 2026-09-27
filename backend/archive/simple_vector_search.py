import voyageai
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

voyage_client = voyageai.Client(api_key=os.environ.get("VOYAGE_API_KEY"))
postgres_connection = psycopg2.connect(
    dbname="microbites_db",
    user="banicky",
    password=os.environ.get("DB_PASSWORD"),
    host="localhost",
    port=5433,
)
cursor = postgres_connection.cursor()

# Embedding part
docs = [
    "The cat sat on the mat.",
    "Python is a programming language.",
    "Dogs are loyal animals.",
]

result = voyage_client.embed(docs, model=os.environ.get("VOYAGE_MODEL"), input_type="document")

for text, embedding in zip(docs, result.embeddings):
    cursor.execute(
        "insert into documents (content, embedding) values (%s, %s)",
        (text, embedding)
    )
    postgres_connection.commit()

# Query part
query = "what animal is on the rug?"
query_embed = voyage_client.embed([query], model=os.environ.get("VOYAGE_MODEL"), input_type="query").embeddings[0]

cursor.execute(
    """
    select content, embedding <=> %s::vector as distance
    from documents
    order by distance
    limit 3
    """,
    (query_embed,)
)

for content, distance in cursor.fetchall():
    print(f"{distance:.4f}  {content}")