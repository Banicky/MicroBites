import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

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


_pool = None


def get_pool():
    # Created on first use so the pipeline scripts that only call connect() don't open a pool
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(1, 10, **DB_CONFIG)
    return _pool


def query(sql, params=()):
    """Run a statement on a pooled connection, commit, and return rows as dicts (empty if none)."""
    conn = get_pool().getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall() if cursor.description else []
        conn.commit()
        return rows
    except Exception:
        conn.rollback()
        raise
    finally:
        get_pool().putconn(conn)


def to_vector(embedding):
    """Format a list of floats as a pgvector literal."""
    return "[" + ",".join(map(str, embedding)) + "]"
