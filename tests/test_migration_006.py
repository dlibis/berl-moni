from pathlib import Path

import psycopg
import pytest

MIGRATION = Path("db/migrations/006_letters_flags.sql").read_text()


@pytest.fixture
def conn(test_db_url):
    with psycopg.connect(test_db_url, row_factory=psycopg.rows.dict_row) as conn:
        conn.execute("TRUNCATE letters RESTART IDENTITY CASCADE")
        conn.execute(
            "INSERT INTO letters (letter_url, slug) VALUES ('https://example.test/x.pdf', 'x')"
        )
        yield conn
        conn.rollback()


def test_new_columns_default_false(conn):
    conn.execute(MIGRATION)
    row = conn.execute("SELECT requires_review, passed FROM letters WHERE slug = 'x'").fetchone()
    assert row == {"requires_review": False, "passed": False}


def test_migration_is_idempotent(conn):
    conn.execute(MIGRATION)
    conn.execute(MIGRATION)
