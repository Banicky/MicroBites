import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

load_dotenv()

# Defaults match the local development database; set these in production (e.g. for RDS)
DB_CONFIG = dict(
    dbname=os.environ.get("DB_NAME", "microbites_db"),
    user=os.environ.get("DB_USER", "banicky"),
    password=os.environ.get("DB_PASSWORD"),
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "5433")),
    # "require" encrypts the connection; use it for RDS. "prefer" uses SSL only when the server offers it.
    sslmode=os.environ.get("DB_SSLMODE", "prefer"),
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
