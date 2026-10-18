import datetime

import pytest

from bot.adapters.postgres.email_log import EmailLogRepository
from bot.adapters.postgres.letters import LettersRepository
from bot.adapters.postgres.scans import ScansRepository
from bot.adapters.postgres.send_runs import SendRunsRepository
from common.db import connect

DAY = datetime.date(2026, 10, 18)


@pytest.fixture
def conn(test_db_url):
    with connect(test_db_url) as conn:
        conn.execute("TRUNCATE letters, scans, email_log, send_runs RESTART IDENTITY CASCADE")
        yield conn
        conn.rollback()


def test_letters_roundtrip_and_pending_order(conn):
    LettersRepository(conn).insert("https://x/b.pdf", "pending", pdf=b"b")
    LettersRepository(conn).insert("https://x/a.pdf", "pending", pdf=b"aa")
    LettersRepository(conn).insert("https://x/c.pdf", "irrelevant")
    LettersRepository(conn).insert("https://x/d.pdf", "failed", reason="quota")
    conn.execute("UPDATE letters SET scanned_at = '2026-10-18 10:00:00+00'")  # same second: url breaks the tie
    assert LettersRepository(conn).known_urls() == {f"https://x/{c}.pdf" for c in "abcd"}
    pending = LettersRepository(conn).pending()
    assert [p["letter_url"] for p in pending] == ["https://x/a.pdf", "https://x/b.pdf"]
    assert [p["pdf_bytes"] for p in pending] == [2, 1]
    assert LettersRepository(conn).load_pdfs(["https://x/b.pdf", "https://x/a.pdf"]) == [b"b", b"aa"]


def test_mark_seen_skips_existing(conn):
    LettersRepository(conn).insert("https://x/a.pdf", "pending", pdf=b"a")
    LettersRepository(conn).mark_seen(["https://x/a.pdf", "https://x/b.pdf"])
    rows = {r["letter_url"]: r["status"] for r in conn.execute("SELECT letter_url, status FROM letters")}
    assert rows == {"https://x/a.pdf": "pending", "https://x/b.pdf": "sent"}


def test_run_lifecycle_and_finish(conn):
    for u in ("a", "b", "c"):
        LettersRepository(conn).insert(f"https://x/{u}.pdf", "pending", pdf=b"p")
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
    assert [p["letter_url"] for p in LettersRepository(conn).pending()] == ["https://x/c.pdf"]
    assert not SendRunsRepository(conn).finish(run_id)  # no longer sending
    assert SendRunsRepository(conn).find_open() is None


def test_failed_run_blocks_finish_and_is_open(conn):
    LettersRepository(conn).insert("https://x/a.pdf", "pending", pdf=b"p")
    run_id = SendRunsRepository(conn).start(DAY, "from@berl.site", "reply@example.com", ["one@example.com"],
                                  [["https://x/a.pdf"]])
    SendRunsRepository(conn).mark_failed(run_id, "ConnectionError")
    run = SendRunsRepository(conn).find_open()
    assert (run["status"], run["error"]) == ("failed", "ConnectionError") and run["failed_at"]
    assert not SendRunsRepository(conn).finish(run_id)
    assert len(LettersRepository(conn).pending()) == 1


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
