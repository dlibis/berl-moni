"""Apply new db/migrations/NNN_*.sql files in filename order.

Usage: python db/migrate.py [--test]   (DATABASE_URL_DIRECT, or TEST_DATABASE_URL with --test)
"""
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

MIGRATIONS = Path(__file__).resolve().parent / "migrations"
LOCK_KEY = 4207  # any constant; only migrate.py takes it


def main(argv):
    load_dotenv()
    var = "TEST_DATABASE_URL" if "--test" in argv else "DATABASE_URL_DIRECT"
    url = os.environ.get(var)
    if not url:
        sys.exit(f"{var} is not set")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                     "filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        done = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations")}
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if path.name in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            print(f"applied {path.name}")
    print("migrations up to date")


if __name__ == "__main__":
    main(sys.argv[1:])
