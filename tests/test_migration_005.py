from pathlib import Path

import psycopg
import pytest


MIGRATION = Path("db/migrations/005_letters_page.sql").read_text()


@pytest.fixture
def conn(test_db_url):
    with psycopg.connect(test_db_url, row_factory=psycopg.rows.dict_row) as conn:
        conn.execute("TRUNCATE letters, email_log, send_runs RESTART IDENTITY CASCADE")
        yield conn
        conn.rollback()


@pytest.mark.parametrize("legacy, expected", [
    (dict(status="pending", summary_pdf=b"%PDF"), dict(analysis_status="analyzed", send_count=0)),
    (dict(status="irrelevant"), dict(analysis_status="discovered")),
    (dict(status="failed", reason="quota"), dict(analysis_status="failed", last_error="quota")),
    (dict(status="sent", with_run=True), dict(analysis_status="discovered", send_count=1)),
    (dict(status="sent", with_run=False), dict(analysis_status="discovered", send_count=0)),
])
def test_backfill_maps_legacy_rows(conn, legacy, expected):
    legacy = legacy.copy()
    run_id = None
    if legacy.pop("with_run", False):
        run_id = conn.execute(
            """INSERT INTO send_runs
                   (day, status, from_address, reply_to_address, batches)
               VALUES ('2026-10-18', 'sent', 'from@example.com', 'reply@example.com', '[]')
               RETURNING id"""
        ).fetchone()["id"]

    sent_at = "2026-10-18 11:00:00+00" if legacy["status"] == "sent" else None
    conn.execute(
        """INSERT INTO letters
               (letter_url, slug, status, reason, summary_pdf, scanned_at, sent_at, send_run_id)
           VALUES (%s, 'legacy', %s, %s, %s, '2026-10-18 10:00:00+00', %s, %s)""",
        ("https://example.com/legacy.pdf", legacy["status"], legacy.get("reason"),
         legacy.get("summary_pdf"), sent_at, run_id),
    )

    conn.execute(MIGRATION)

    row = conn.execute("SELECT * FROM letters WHERE slug = 'legacy'").fetchone()
    for column, value in expected.items():
        assert row[column] == value
    assert row["first_seen_at"] == row["scanned_at"]
    if run_id is not None:
        assert row["last_sent_at"] == row["sent_at"]


def test_migration_is_idempotent(conn):
    conn.execute(MIGRATION)
    conn.execute(MIGRATION)


def test_manual_runs_are_not_limited_to_one_per_day(conn):
    values = ("2026-10-18", "sending", "from@example.com", "reply@example.com", "[]")
    statement = """INSERT INTO send_runs
        (day, status, from_address, reply_to_address, batches, kind)
        VALUES (%s, %s, %s, %s, %s, %s)"""
    conn.execute(statement, (*values, "manual"))
    conn.execute(statement, (*values, "manual"))
    conn.execute(statement, (*values, "auto"))

    with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
        conn.execute(statement, (*values, "auto"))
