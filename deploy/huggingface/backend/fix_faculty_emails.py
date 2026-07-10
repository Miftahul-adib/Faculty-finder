"""
One-time data fix: the scraped `faculty.email` column contains the literal
Cloudflare obfuscation placeholder text ("[email protected]") for every row
instead of a real address. The real address is recoverable from the last
path segment of `profile_url` (the source site keys each faculty page by
email, e.g. .../faculty/mokhles.anp@sust.edu).

Updates both the live MySQL database and the source SQLite file so future
migrations stay consistent.
"""
import re
import sqlite3

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def extract_email(profile_url: str) -> str:
    if not profile_url:
        return ""
    last = profile_url.rstrip("/").split("/")[-1]
    return last if EMAIL_RE.match(last) else ""


def fix_sqlite(path: str):
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("SELECT id, profile_url FROM faculty")
    rows = cur.fetchall()
    updated = cleared = 0
    for fid, profile_url in rows:
        email = extract_email(profile_url)
        cur.execute("UPDATE faculty SET email=? WHERE id=?", (email, fid))
        if email:
            updated += 1
        else:
            cleared += 1
    con.commit()
    con.close()
    print(f"[sqlite] updated={updated} cleared={cleared} total={len(rows)}")


def fix_mysql():
    import os
    import mysql.connector

    con = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "123456"),
        database=os.getenv("MYSQL_DATABASE", "faculty_finder"),
    )
    cur = con.cursor()
    cur.execute("SELECT id, profile_url FROM faculty")
    rows = cur.fetchall()
    updated = cleared = 0
    for fid, profile_url in rows:
        email = extract_email(profile_url)
        cur.execute("UPDATE faculty SET email=%s WHERE id=%s", (email, fid))
        if email:
            updated += 1
        else:
            cleared += 1
    con.commit()
    cur.close()
    con.close()
    print(f"[mysql] updated={updated} cleared={cleared} total={len(rows)}")


if __name__ == "__main__":
    fix_mysql()
    fix_sqlite("F:/Faculty-finder/data/Faculty_database.db")
