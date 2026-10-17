import os
import subprocess
import sys

import psycopg

TABLES = {"programs", "mailing_list", "settings", "letters", "scans", "send_runs", "email_log",
          "schema_migrations"}


def run(url):
    env = {**os.environ, "TEST_DATABASE_URL": url}
    return subprocess.run([sys.executable, "db/migrate.py", "--test"], env=env, capture_output=True, text=True,
                          check=True).stdout


def test_migrate_idempotent_and_concurrent_safe(neon_test_db_url):
    env = {**os.environ, "TEST_DATABASE_URL": neon_test_db_url}
    procs = [subprocess.Popen([sys.executable, "db/migrate.py", "--test"], env=env, stdout=subprocess.PIPE,
                              text=True) for _ in range(2)]
    applied = [line for p in procs for line in p.communicate()[0].splitlines() if line.startswith("applied")]
    assert all(p.returncode == 0 for p in procs)
    assert len(applied) == len(set(applied))  # each file applied at most once

    assert "applied" not in run(neon_test_db_url)  # second run applies nothing
    with psycopg.connect(neon_test_db_url) as conn:
        names = {r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
        assert TABLES <= names
        assert conn.execute("SELECT value FROM settings WHERE key = 'resend_reserve'").fetchone()[0] == 5
