import datetime
import os
import subprocess
import sys

import pytest

from common import letter_store as store
from common.db import connect

DAY = datetime.date(2026, 10, 18)


@pytest.fixture
def conn(test_db_url):
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = test_db_url
    subprocess.run([sys.executable, "db/migrate.py", "--test"], check=True, env=env)
    with connect(test_db_url) as conn:
        conn.execute("TRUNCATE letters, scans, email_log, send_runs RESTART IDENTITY CASCADE")
        yield conn
        conn.rollback()


def test_letters_roundtrip_and_pending_order(conn):
    store.insert_letter_result(conn, "https://x/b.pdf", "pending", pdf=b"b")
    store.insert_letter_result(conn, "https://x/a.pdf", "pending", pdf=b"aa")
    store.insert_letter_result(conn, "https://x/c.pdf", "irrelevant")
    store.insert_letter_result(conn, "https://x/d.pdf", "failed", reason="quota")
    conn.execute("UPDATE letters SET scanned_at = '2026-10-18 10:00:00+00'")  # same second: url breaks the tie
    assert store.known_urls(conn) == {f"https://x/{c}.pdf" for c in "abcd"}
    pending = store.pending_letters(conn)
    assert [p["letter_url"] for p in pending] == ["https://x/a.pdf", "https://x/b.pdf"]
    assert [p["pdf_bytes"] for p in pending] == [2, 1]
    assert store.load_pdfs(conn, ["https://x/b.pdf", "https://x/a.pdf"]) == [b"b", b"aa"]


def test_mark_seen_skips_existing(conn):
    store.insert_letter_result(conn, "https://x/a.pdf", "pending", pdf=b"a")
    store.mark_seen(conn, ["https://x/a.pdf", "https://x/b.pdf"])
    rows = {r["letter_url"]: r["status"] for r in conn.execute("SELECT letter_url, status FROM letters")}
    assert rows == {"https://x/a.pdf": "pending", "https://x/b.pdf": "sent"}


def test_run_lifecycle_and_finish(conn):
    for u in ("a", "b", "c"):
        store.insert_letter_result(conn, f"https://x/{u}.pdf", "pending", pdf=b"p")
    assert store.send_run_open(conn) is None
    run_id = store.start_send_run(conn, DAY, "from@berl.site", "reply@example.com", ["one@example.com"],
                                  [["https://x/a.pdf", "https://x/b.pdf"]])
    assert store.send_run_open(conn)["id"] == run_id
    assert store.lock_run(conn, run_id) == "sending"
    assert store.lock_run(conn, run_id + 1) is None
    store.log_email(conn, f"run{run_id}-b0-c0", "letter", 2)
    store.log_email(conn, f"run{run_id}-b0-c0", "letter", 2)  # duplicate key: ignored
    store.log_email(conn, "test-1", "test", 1)
    assert store.sent_keys(conn, run_id) == {f"run{run_id}-b0-c0"}

    assert store.finish_run(conn, run_id)
    run = conn.execute("SELECT * FROM send_runs WHERE id = %s", (run_id,)).fetchone()
    assert (run["status"], run["recipients"]) == ("sent", None) and run["finished_at"]
    sent = {r["letter_url"]: r["send_run_id"] for r in conn.execute("SELECT * FROM letters WHERE status = 'sent'")}
    assert sent == {"https://x/a.pdf": run_id, "https://x/b.pdf": run_id}
    assert [p["letter_url"] for p in store.pending_letters(conn)] == ["https://x/c.pdf"]
    assert not store.finish_run(conn, run_id)  # no longer sending
    assert store.send_run_open(conn) is None


def test_failed_run_blocks_finish_and_is_open(conn):
    store.insert_letter_result(conn, "https://x/a.pdf", "pending", pdf=b"p")
    run_id = store.start_send_run(conn, DAY, "from@berl.site", "reply@example.com", ["one@example.com"],
                                  [["https://x/a.pdf"]])
    store.mark_run_failed(conn, run_id, "ConnectionError")
    run = store.send_run_open(conn)
    assert (run["status"], run["error"]) == ("failed", "ConnectionError") and run["failed_at"]
    assert not store.finish_run(conn, run_id)
    assert len(store.pending_letters(conn)) == 1


def test_email_counts_use_utc_day_and_month(conn):
    store.log_email(conn, "test-now", "test", 5)
    store.log_email(conn, "test-old-day", "test", 7)
    store.log_email(conn, "test-old-month", "test", 11)
    conn.execute("UPDATE email_log SET sent_at = date_trunc('day', now() AT TIME ZONE 'utc') AT TIME ZONE 'utc' "
                 "- interval '1 second' WHERE idempotency_key = 'test-old-day'")
    conn.execute("UPDATE email_log SET sent_at = date_trunc('month', now() AT TIME ZONE 'utc') AT TIME ZONE 'utc' "
                 "- interval '1 second' WHERE idempotency_key = 'test-old-month'")
    day, month = store.email_counts(conn)
    assert day == 5
    # yesterday's last second is in the previous month only when today is the 1st (UTC)
    assert month == 5 + (0 if datetime.datetime.now(datetime.timezone.utc).day == 1 else 7)


def test_write_scan_has_counts_only(conn):
    store.write_scan(conn, DAY, "failed", "quota", letters_in_feed=3, new_letters=2, relevant=1, failed=1)
    row = conn.execute("SELECT * FROM scans").fetchone()
    assert (row["status"], row["reason"], row["new_letters"], row["emails_sent"]) == ("failed", "quota", 2, 0)
    assert not any("@" in str(v) for v in row.values())
