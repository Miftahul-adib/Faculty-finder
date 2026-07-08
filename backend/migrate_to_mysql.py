"""
One-time migration: copies all data from the legacy SQLite database into
MySQL (connection settings from .env — see db.py).

Run once from backend/:  python migrate_to_mysql.py

Safe to re-run: it recreates the MySQL schema fresh each time (drops any
existing tables this script owns) before copying data back in.
"""
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.getenv("SQLITE_PATH", "F:/Faculty-finder/data/Faculty_database.db")

import db
import student_db

# faculty_id -> detail child tables that share the same simple shape
DETAIL_TABLES = [
    "education", "conferences", "books",
    "external_affiliations", "teaching", "awards", "graduate_supervision",
]


def sqlite_conn():
    con = sqlite3.connect(SQLITE_PATH)
    con.row_factory = sqlite3.Row
    return con


def reset_autoincrement(con, table, id_col="id"):
    row = con.execute(f"SELECT MAX({id_col}) AS m FROM {table}").fetchone()
    max_id = row["m"] or 0
    con.execute(f"ALTER TABLE {table} AUTO_INCREMENT = {max_id + 1}")


def migrate_faculty(sconn, mconn):
    print("── faculty ─────────────────────────────────────────")
    mconn.execute("DROP TABLE IF EXISTS research_interests")
    mconn.execute("DROP TABLE IF EXISTS education")
    mconn.execute("DROP TABLE IF EXISTS publications")
    mconn.execute("DROP TABLE IF EXISTS conferences")
    mconn.execute("DROP TABLE IF EXISTS books")
    mconn.execute("DROP TABLE IF EXISTS research_projects")
    mconn.execute("DROP TABLE IF EXISTS external_affiliations")
    mconn.execute("DROP TABLE IF EXISTS teaching")
    mconn.execute("DROP TABLE IF EXISTS awards")
    mconn.execute("DROP TABLE IF EXISTS graduate_supervision")
    mconn.execute("DROP TABLE IF EXISTS faculty")
    mconn.commit()

    mconn.execute("""
        CREATE TABLE faculty (
            id INT AUTO_INCREMENT PRIMARY KEY,
            department VARCHAR(255),
            name VARCHAR(255),
            designation VARCHAR(255),
            phone VARCHAR(100),
            email VARCHAR(255),
            office_address VARCHAR(500),
            biography TEXT,
            photo_url VARCHAR(500),
            profile_url VARCHAR(500),
            research_summary TEXT,
            embedding LONGBLOB
        )
    """)
    mconn.commit()

    rows = sconn.execute("SELECT * FROM faculty").fetchall()
    data = [
        (r["id"], r["department"], r["name"], r["designation"], r["phone"], r["email"],
         r["office_address"], r["biography"], r["photo_url"], r["profile_url"],
         r["research_summary"], r["embedding"])
        for r in rows
    ]
    cur = mconn._raw.cursor()
    cur.executemany(
        "INSERT INTO faculty (id,department,name,designation,phone,email,office_address,"
        "biography,photo_url,profile_url,research_summary,embedding) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        data,
    )
    mconn.commit()
    reset_autoincrement(mconn, "faculty")
    mconn.commit()
    print(f"  {len(data)} faculty rows migrated")


def migrate_research_interests(sconn, mconn):
    mconn.execute("""
        CREATE TABLE research_interests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            faculty_id INT,
            interest VARCHAR(1000),
            FOREIGN KEY (faculty_id) REFERENCES faculty(id)
        )
    """)
    mconn.commit()
    rows = sconn.execute("SELECT id, faculty_id, interest FROM research_interests").fetchall()
    cur = mconn._raw.cursor()
    cur.executemany(
        "INSERT INTO research_interests (id, faculty_id, interest) VALUES (%s,%s,%s)",
        [(r["id"], r["faculty_id"], r["interest"]) for r in rows],
    )
    mconn.commit()
    reset_autoincrement(mconn, "research_interests")
    mconn.commit()
    print(f"  {len(rows)} research_interests rows migrated")


def migrate_detail_table(sconn, mconn, table):
    mconn.execute(f"""
        CREATE TABLE {table} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            faculty_id INT,
            detail TEXT,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id)
        )
    """)
    mconn.commit()
    rows = sconn.execute(f"SELECT id, faculty_id, detail FROM {table}").fetchall()
    cur = mconn._raw.cursor()
    cur.executemany(
        f"INSERT INTO {table} (id, faculty_id, detail) VALUES (%s,%s,%s)",
        [(r["id"], r["faculty_id"], r["detail"]) for r in rows],
    )
    mconn.commit()
    reset_autoincrement(mconn, table)
    mconn.commit()
    print(f"  {len(rows)} {table} rows migrated")


def migrate_publications(sconn, mconn):
    mconn.execute("""
        CREATE TABLE publications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            faculty_id INT,
            title TEXT,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id)
        )
    """)
    mconn.commit()
    rows = sconn.execute("SELECT id, faculty_id, title FROM publications").fetchall()
    cur = mconn._raw.cursor()
    cur.executemany(
        "INSERT INTO publications (id, faculty_id, title) VALUES (%s,%s,%s)",
        [(r["id"], r["faculty_id"], r["title"]) for r in rows],
    )
    mconn.commit()
    reset_autoincrement(mconn, "publications")
    mconn.commit()
    print(f"  {len(rows)} publications rows migrated")


def migrate_research_projects(sconn, mconn):
    mconn.execute("""
        CREATE TABLE research_projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            faculty_id INT,
            project_type VARCHAR(255),
            detail TEXT,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id)
        )
    """)
    mconn.commit()
    rows = sconn.execute("SELECT id, faculty_id, project_type, detail FROM research_projects").fetchall()
    cur = mconn._raw.cursor()
    cur.executemany(
        "INSERT INTO research_projects (id, faculty_id, project_type, detail) VALUES (%s,%s,%s,%s)",
        [(r["id"], r["faculty_id"], r["project_type"], r["detail"]) for r in rows],
    )
    mconn.commit()
    reset_autoincrement(mconn, "research_projects")
    mconn.commit()
    print(f"  {len(rows)} research_projects rows migrated")


def migrate_app_data(sconn, mconn):
    print("── app data (students / tags / posts / saved) ────────")

    students = sconn.execute("SELECT * FROM students").fetchall()
    cur = mconn._raw.cursor()
    cur.executemany(
        "INSERT INTO students (id,name,email,password_hash,salt,university,department,year,"
        "bio,research_interests,research_summary,certifications,cv_path,created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        [(r["id"], r["name"], r["email"], r["password_hash"], r["salt"], r["university"],
          r["department"], r["year"], r["bio"],
          r["research_interests"] if "research_interests" in r.keys() else None,
          r["research_summary"] if "research_summary" in r.keys() else None,
          r["certifications"] if "certifications" in r.keys() else None,
          r["cv_path"] if "cv_path" in r.keys() else "",
          r["created_at"])
         for r in students],
    )
    mconn.commit()
    reset_autoincrement(mconn, "students")
    mconn.commit()
    print(f"  {len(students)} students migrated")

    tags = sconn.execute("SELECT * FROM student_tags").fetchall()
    cur.executemany(
        "INSERT INTO student_tags (id, student_id, tag, created_at) VALUES (%s,%s,%s,%s)",
        [(r["id"], r["student_id"], r["tag"], r["created_at"]) for r in tags],
    )
    mconn.commit()
    reset_autoincrement(mconn, "student_tags")
    mconn.commit()
    print(f"  {len(tags)} student_tags migrated")

    posts = sconn.execute("SELECT * FROM student_posts").fetchall()
    cur.executemany(
        "INSERT INTO student_posts (id, student_id, title, content, post_type, created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        [(r["id"], r["student_id"], r["title"], r["content"], r["post_type"], r["created_at"]) for r in posts],
    )
    mconn.commit()
    reset_autoincrement(mconn, "student_posts")
    mconn.commit()
    print(f"  {len(posts)} student_posts migrated")

    saved_fac = sconn.execute("SELECT * FROM student_saved_faculty").fetchall()
    cur.executemany(
        "INSERT INTO student_saved_faculty (id, student_id, faculty_id, added_at) VALUES (%s,%s,%s,%s)",
        [(r["id"], r["student_id"], r["faculty_id"], r["added_at"]) for r in saved_fac],
    )
    mconn.commit()
    reset_autoincrement(mconn, "student_saved_faculty")
    mconn.commit()
    print(f"  {len(saved_fac)} student_saved_faculty migrated")

    saved_phd = sconn.execute("SELECT * FROM student_saved_phd").fetchall()
    cur.executemany(
        "INSERT INTO student_saved_phd (id, student_id, phd_student_id, added_at) VALUES (%s,%s,%s,%s)",
        [(r["id"], r["student_id"], r["phd_student_id"], r["added_at"]) for r in saved_phd],
    )
    mconn.commit()
    reset_autoincrement(mconn, "student_saved_phd")
    mconn.commit()
    print(f"  {len(saved_phd)} student_saved_phd migrated")

    saved_stu = sconn.execute("SELECT * FROM student_saved_students").fetchall()
    cur.executemany(
        "INSERT INTO student_saved_students (id, student_id, target_student_id, added_at) VALUES (%s,%s,%s,%s)",
        [(r["id"], r["student_id"], r["target_student_id"], r["added_at"]) for r in saved_stu],
    )
    mconn.commit()
    reset_autoincrement(mconn, "student_saved_students")
    mconn.commit()
    print(f"  {len(saved_stu)} student_saved_students migrated")


def main():
    print(f"Source SQLite : {SQLITE_PATH}")
    print(f"Target MySQL  : {db.MYSQL_USER}@{db.MYSQL_HOST}:{db.MYSQL_PORT}/{db.MYSQL_DATABASE}\n")

    sconn = sqlite_conn()
    mconn = db.get_conn()

    try:
        migrate_faculty(sconn, mconn)
        migrate_research_interests(sconn, mconn)
        for table in DETAIL_TABLES:
            print(f"── {table} " + "─" * (40 - len(table)))
            migrate_detail_table(sconn, mconn, table)
        print("── publications " + "─" * 30)
        migrate_publications(sconn, mconn)
        print("── research_projects " + "─" * 25)
        migrate_research_projects(sconn, mconn)

        # Creates the 9 app tables + deterministically re-seeds phd_students
        # (same hardcoded list/order as before -> identical IDs).
        print("\n── app schema + phd_students seed ─────────────────────")
        student_db.setup_student_db()

        migrate_app_data(sconn, mconn)

        print("\nMigration complete.")
    finally:
        sconn.close()
        mconn.close()


if __name__ == "__main__":
    main()
