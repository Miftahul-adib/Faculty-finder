"""
Shared Postgres connection helper (Vercel deployment — Neon via the
Vercel Marketplace integration; MySQL is used by the Railway/HF deployments
instead, see deploy/railway and deploy/huggingface).

Wraps psycopg2 so callers can keep using the sqlite3-style
`con.execute(sql, params).fetchall()` convenience chain the codebase was
originally written against, instead of the more verbose
`cur = con.cursor(); cur.execute(...)` pattern psycopg2 requires. psycopg2
has no `cursor.lastrowid` (unlike mysql.connector) — the one call site that
needs it uses `INSERT ... RETURNING id` instead.
"""
import os
import psycopg2
import psycopg2.extras
from psycopg2 import IntegrityError, Error as DatabaseError

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")


class Connection:
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=None):
        cur = self._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        return cur

    def executescript(self, script):
        cur = self._raw.cursor()
        for statement in filter(None, (s.strip() for s in script.split(";"))):
            cur.execute(statement)
        cur.close()

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()
        return False


def get_conn() -> Connection:
    raw = psycopg2.connect(DATABASE_URL)
    return Connection(raw)


def col_exists(con, table: str, col: str) -> bool:
    cur = con.execute(
        """SELECT COUNT(*) AS n FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = %s AND column_name = %s""",
        (table, col),
    )
    return cur.fetchone()["n"] > 0
