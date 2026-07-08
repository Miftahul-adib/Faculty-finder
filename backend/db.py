"""
Shared MySQL connection helper.

Wraps mysql.connector so callers can keep using the sqlite3-style
`con.execute(sql, params).fetchall()` convenience chain the codebase was
originally written against, instead of the more verbose
`cur = con.cursor(); cur.execute(...)` pattern mysql.connector requires.
"""
import os
import mysql.connector
from mysql.connector import IntegrityError, Error as DatabaseError

MYSQL_HOST     = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT     = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER     = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "faculty_finder")


class Connection:
    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=None):
        cur = self._raw.cursor(dictionary=True)
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
    raw = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )
    return Connection(raw)


def col_exists(con, table: str, col: str) -> bool:
    cur = con.execute(
        """SELECT COUNT(*) AS n FROM information_schema.columns
           WHERE table_schema = %s AND table_name = %s AND column_name = %s""",
        (MYSQL_DATABASE, table, col),
    )
    return cur.fetchone()["n"] > 0
