import datetime

import pytest

from bot.adapters.postgres.email_log import EmailLogRepository
from bot.adapters.postgres.letters import LettersRepository
from bot.adapters.postgres.scans import ScansRepository
from bot.adapters.postgres.send_runs import SendRunsRepository
from bot.domain.extraction import Extraction
from bot.domain.feed import FeedLetter
from bot.tests.fixtures.extractions import complete_extraction, irrelevant_extraction
from common.db import connect

DAY = datetime.date(2026, 10, 18)


@pytest.fixture
def conn(test_db_url):
    with connect(test_db_url) as conn:
        conn.execute("TRUNCATE letters, scans, email_log, send_runs RESTART IDENTITY CASCADE")
        yield conn
        conn.rollback()


def insert_legacy(conn, url: str, pdf: bytes = b"p") -> None:
    """A `pending` row as the job wrote it before analysis_status (summary PDF stored, no extraction)."""
    conn.execute("INSERT INTO letters (letter_url, slug, status, summary_pdf, pdf_bytes) VALUES (%s, %s, 'pending', %s, %s)",
                 (url, url, pdf, len(pdf)))


def analyzed(conn, url: str, extraction: Extraction) -> None:
    letters = LettersRepository(conn)
    letters.upsert_feed([FeedLetter(url, None, "", (), ())], auto=True)
    claimed = letters.claim()
    assert letters.finish_analysis(url, claimed["lease_id"], extraction.to_json(), "m|prompt:1|schema:1",
                                   sorted(extraction.codes()), "ab", 3)


def test_auto_eligible_is_analyzed_complete_relevant_unsent_and_recent(conn):
    conn.execute("TRUNCATE programs")
    conn.execute("INSERT INTO programs (code, name) VALUES ('200102', 'p')")
    incomplete = Extraction(source="x", table=complete_extraction().table)  # relevant, but the LLM part never ran
    for url, extraction in [("https://x/b.pdf", complete_extraction()), ("https://x/a.pdf", complete_extraction()),
                            ("https://x/sent.pdf", complete_extraction()), ("https://x/old.pdf", complete_extraction()),
                            ("https://x/irrelevant.pdf", irrelevant_extraction()), ("https://x/incomplete.pdf", incomplete)]:
        analyzed(conn, url, extraction)
    LettersRepository(conn).upsert_feed([FeedLetter("https://x/discovered.pdf", None, "", (), ())], auto=False)
    conn.execute("UPDATE letters SET first_seen_at = '2026-10-18 10:00:00+00'")  # same second: url breaks the tie
    conn.execute("UPDATE letters SET first_seen_at = '2026-10-17 10:00:00+00' WHERE letter_url = 'https://x/old.pdf'")
    LettersRepository(conn).mark_delivered(["https://x/sent.pdf"])
    assert LettersRepository(conn).auto_eligible("2026-10-18T00:00:00+00:00") == ["https://x/a.pdf", "https://x/b.pdf"]
    assert LettersRepository(conn).auto_eligible(None) == ["https://x/old.pdf", "https://x/a.pdf", "https://x/b.pdf"]


def test_legacy_summary_pdfs_load_in_order(conn):
    insert_legacy(conn, "https://x/b.pdf", b"b")
    insert_legacy(conn, "https://x/a.pdf", b"aa")
    assert LettersRepository(conn).load_pdfs(["https://x/b.pdf", "https://x/a.pdf"]) == [b"b", b"aa"]


def test_run_lifecycle_and_finish(conn):
    for u in ("a", "b", "c"):
        insert_legacy(conn, f"https://x/{u}.pdf")
    assert SendRunsRepository(conn).find_open() is None
    run_id = SendRunsRepository(conn).start(DAY, "from@berl.site", "reply@example.com", ["one@example.com"],
                                  [["https://x/a.pdf", "https://x/b.pdf"]])
    assert SendRunsRepository(conn).find_open()["id"] == run_id
    assert SendRunsRepository(conn).lock(run_id) == "sending"
    assert SendRunsRepository(conn).lock(run_id + 1) is None
    EmailLogRepository(conn).add(f"run{run_id}-b0-c0", "letter", 2)
    EmailLogRepository(conn).add(f"run{run_id}-b0-c0", "letter", 2)  # duplicate key: ignored
    EmailLogRepository(conn).add("test-1", "test", 1)
    assert EmailLogRepository(conn).sent_keys(run_id) == {f"run{run_id}-b0-c0"}

    assert SendRunsRepository(conn).finish(run_id)
    LettersRepository(conn).mark_sent(["https://x/a.pdf", "https://x/b.pdf"], run_id)
    run = conn.execute("SELECT * FROM send_runs WHERE id = %s", (run_id,)).fetchone()
    assert (run["status"], run["recipients"]) == ("sent", None) and run["finished_at"]
    sent = {r["letter_url"]: r["send_run_id"] for r in conn.execute("SELECT * FROM letters WHERE status = 'sent'")}
    assert sent == {"https://x/a.pdf": run_id, "https://x/b.pdf": run_id}
    assert [r["letter_url"] for r in conn.execute("SELECT letter_url FROM letters WHERE status = 'pending'")] == \
        ["https://x/c.pdf"]
    assert not SendRunsRepository(conn).finish(run_id)  # no longer sending
    assert SendRunsRepository(conn).find_open() is None


def test_failed_run_blocks_finish_and_is_open(conn):
    insert_legacy(conn, "https://x/a.pdf")
    run_id = SendRunsRepository(conn).start(DAY, "from@berl.site", "reply@example.com", ["one@example.com"],
                                  [["https://x/a.pdf"]])
    SendRunsRepository(conn).mark_failed(run_id, "ConnectionError")
    run = SendRunsRepository(conn).find_open()
    assert (run["status"], run["error"]) == ("failed", "ConnectionError") and run["failed_at"]
    assert not SendRunsRepository(conn).finish(run_id)


def test_email_log_counts_use_utc_day_and_month(conn):
    EmailLogRepository(conn).add("test-now", "test", 5)
    EmailLogRepository(conn).add("test-old-day", "test", 7)
    EmailLogRepository(conn).add("test-old-month", "test", 11)
    conn.execute("UPDATE email_log SET sent_at = date_trunc('day', now() AT TIME ZONE 'utc') AT TIME ZONE 'utc' "
                 "- interval '1 second' WHERE idempotency_key = 'test-old-day'")
    conn.execute("UPDATE email_log SET sent_at = date_trunc('month', now() AT TIME ZONE 'utc') AT TIME ZONE 'utc' "
                 "- interval '1 second' WHERE idempotency_key = 'test-old-month'")
    day, month = EmailLogRepository(conn).counts()
    assert day == 5
    # yesterday's last second is in the previous month only when today is the 1st (UTC)
    assert month == 5 + (0 if datetime.datetime.now(datetime.timezone.utc).day == 1 else 7)


def test_email_log_start_complete_and_counts(conn):
    log = EmailLogRepository(conn)
    assert log.start("run1-b0-c0", "letter", 3)
    assert not log.start("run1-b0-c0", "letter", 3)
    assert log.counts() == (3, 3)
    assert log.sent_keys(1) == set()
    log.complete("run1-b0-c0", "em_1")
    assert log.sent_keys(1) == {"run1-b0-c0"}


def test_scan_rows_have_counts_only(conn):
    ScansRepository(conn).add(DAY, "failed", "quota", letters_in_feed=3, new_letters=2, relevant=1, failed=1)
    row = conn.execute("SELECT * FROM scans").fetchone()
    assert (row["status"], row["reason"], row["new_letters"], row["emails_sent"]) == ("failed", "quota", 2, 0)
    assert not any("@" in str(v) for v in row.values())


@pytest.mark.parametrize("constraint, literal", [
    ("letters_status_check", "LetterStatus"), ("letters_reason_check", "LetterReason"),
    ("letters_analysis_status_check", "AnalysisStatus"),
    ("send_runs_status_check", "RunStatus"), ("scans_status_check", "ScanStatus"),
    ("send_runs_kind_check", "SendKind"),
    ("scans_reason_check", "ScanReason"), ("email_log_kind_check", "EmailKind"),
    ("email_log_status_check", "EmailStatus"),
])
def test_status_types_match_the_check_constraints(conn, constraint, literal):
    import re
    from typing import get_args

    from bot.domain import statuses
    definition = conn.execute("SELECT pg_get_constraintdef(oid) AS d FROM pg_constraint WHERE conname = %s",
                              (constraint,)).fetchone()["d"]
    assert set(re.findall(r"'([a-z_0-9]+)'", definition)) == set(get_args(getattr(statuses, literal)))
