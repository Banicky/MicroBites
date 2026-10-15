import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = dict(
    dbname="microbites_db",
    user="banicky",
    password=os.environ.get("DB_PASSWORD"),
    host="localhost",
    port=5433,
)


def connect():
    return psycopg2.connect(**DB_CONFIG)


def to_vector(embedding):
    """Format a list of floats as a pgvector literal."""
    return "[" + ",".join(map(str, embedding)) + "]"
