"""
Database helpers. Run this file directly to create data/onetricks.db
from sql/schema.sql:

    python src/db.py

Running it again is safe. Existing tables and data are left alone.
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "onetricks.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"


def connect():
    """Open the database with foreign key checks turned on."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # SQLite ignores REFERENCES unless this is turned on for each connection
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    print(f"Database ready at {DB_PATH}")


if __name__ == "__main__":
    init_db()
