"""bot/main.py: the send job against a Neon test branch, with the feed, Agent, renderer and Resend stubbed."""
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest
import requests

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "bot"))

import main  # noqa: E402
from aggregator import FeedUnreachable  # noqa: E402
from common import letter_store as store  # noqa: E402
from common.db import connect, set_setting  # noqa: E402
from notifier import ResendError  # noqa: E402
from pdf_document import ExtractionError  # noqa: E402

FROM, REPLY = "news@berl.site", "staff@example.com"
LIST = [f"r{i:02d}@example.com" for i in range(3)]
A, B, C = (f"https://example.com/letters/{n}.pdf" for n in (1, 2, 3))
EVERY_DAY = [{"from": "2000-01-01", "to": "2099-12-31",
              "days": {d: {"enabled": True, "time": "00:00"} for d in ("sun", "mon", "tue", "wed", "thu", "fri", "sat")}}]


class Quota(Exception):
    status_code = 429


@dataclass
class Extraction:
    relevant: bool = True
    matched_codes: set = field(default_factory=lambda: {"123456"})


class Stubs:
    """The feed, the Agent, the renderer and Resend. `outcomes` maps a URL to an Extraction or an exception."""

    def __init__(self):
        self.urls, self.outcomes, self.scanned, self.sent = [], {}, [], []
        self.feed_down, self.fail_call = False, None

    def get_pdf_urls(self):
        if self.feed_down:
            raise FeedUnreachable("page 1: ConnectionError")
        return list(self.urls)

    def extract(self, url):
        self.scanned.append(url)
        outcome = self.outcomes.get(url, Extraction())
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def send_message(self, **kwargs):
        if self.fail_call == len(self.sent) + 1:
            raise ResendError(422, "validation_error")
        self.sent.append(kwargs)


@pytest.fixture
def stubs(monkeypatch):
    s = Stubs()
    monkeypatch.setattr(main, "get_pdf_urls", s.get_pdf_urls)
    monkeypatch.setattr(main, "Agent", SimpleNamespace(from_config=lambda: s))
    monkeypatch.setattr(main, "send_message", s.send_message)

    def render(result, slug, out_dir, programs):
        path = out_dir / f"{slug}_summary.pdf"
        path.write_bytes(b"%PDF-1.4 " + slug.encode())
        return path
    monkeypatch.setattr(main, "render_summary", render)
    return s


@pytest.fixture
def db(test_db_url, stubs, monkeypatch, tmp_path):
    subprocess.run([sys.executable, os.path.join(_ROOT, "db", "migrate.py"), "--test"], check=True,
                   env={**os.environ, "TEST_DATABASE_URL": test_db_url})
    with connect(test_db_url) as conn:
        conn.execute("TRUNCATE letters, scans, email_log, send_runs, mailing_list RESTART IDENTITY CASCADE")
        for key, value in dict(schedule=EVERY_DAY, from_address=FROM, reply_to_address=REPLY, resend_daily_limit=100,
                               resend_monthly_limit=3000, resend_reserve=5).items():
            set_setting(conn, key, value)
        for email in LIST + [REPLY]:
            conn.execute("INSERT INTO mailing_list (email) VALUES (%s)", (email,))
    for name, value in dict(DATABASE_URL=test_db_url, RESEND_API_KEY="re_test", MODEL_NAME="m",
                            MODEL_PROVIDER="openai", OPENAI_API_KEY="k").items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(main, "OUTPUT_DIR", tmp_path / "out")
    return test_db_url


def rows(db, sql):
    with connect(db) as conn:
        return list(conn.execute(sql))


def run(*args):
    return main.main(list(args))


def test_nothing_new(db, stubs):
    assert run() == 0
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["new_letters"], scan["emails_sent"]) == ("nothing_new", 0, 0)
    assert stubs.sent == [] and rows(db, "SELECT * FROM send_runs") == []


def test_not_due_writes_no_scan(db, stubs):
    with connect(db) as conn:
        set_setting(conn, "schedule", [])
    assert run() == 0
    assert rows(db, "SELECT * FROM scans") == [] and stubs.scanned == []


def test_one_relevant_letter_is_sent_once(db, stubs):
    stubs.urls = [A]
    assert run() == 0
    [letter] = rows(db, "SELECT * FROM letters")
    assert (letter["letter_url"], letter["status"], letter["send_run_id"]) == (A, "sent", 1)
    [sent] = stubs.sent
    assert sent["bcc"] == LIST and sent["reply_to"] == REPLY and sent["idempotency_key"] == "run1-b0-c0"
    assert [name for name, _ in sent["attachments"]] == ["1_summary.pdf"]
    [log] = rows(db, "SELECT * FROM email_log")
    assert (log["idempotency_key"], log["emails"], log["kind"]) == ("run1-b0-c0", 4, "letter")
    [r] = rows(db, "SELECT * FROM send_runs")
    assert r["status"] == "sent" and r["recipients"] is None
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["relevant"], scan["emails_sent"], scan["letters_in_feed"]) == ("sent", 1, 4, 1)
    # a second run on the same day does nothing, and scans nothing again
    assert run() == 0
    assert len(stubs.sent) == 1 and stubs.scanned == [A] and len(rows(db, "SELECT * FROM scans")) == 1


def test_irrelevant_letter_is_stored_irrelevant(db, stubs):
    stubs.urls, stubs.outcomes = [A], {A: Extraction(relevant=False)}
    assert run() == 0
    [letter] = rows(db, "SELECT * FROM letters")
    assert letter["status"] == "irrelevant" and letter["summary_pdf"] is None
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["new_letters"], scan["relevant"]) == ("nothing_new", 1, 0)
    assert stubs.sent == []


def test_quota_stops_scanning_but_pending_letters_go_out(db, stubs):
    with connect(db) as conn:
        store.insert_letter_result(conn, "https://example.com/old.pdf", "pending", pdf=b"%PDF old")
    stubs.urls, stubs.outcomes = [A, B], {A: Quota("insufficient_quota")}
    assert run() == 0
    status = {r["letter_url"]: (r["status"], r["reason"]) for r in rows(db, "SELECT * FROM letters")}
    assert status == {"https://example.com/old.pdf": ("sent", None), A: ("failed", "quota")}  # B untouched
    assert stubs.scanned == [A] and len(stubs.sent) == 1
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["reason"], scan["failed"]) == ("sent", "quota", 1)


def test_quota_with_nothing_pending_is_nothing_new(db, stubs):
    stubs.urls, stubs.outcomes = [A], {A: Quota()}
    assert run() == 0
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["reason"]) == ("nothing_new", "quota")


@pytest.mark.parametrize("error, reason", [
    (requests.Timeout("t"), "network"),
    (requests.ConnectionError("c"), "network"),
    (RuntimeError("Failed to download https://x/429.pdf after 4 attempts: HTTP Error 503: Unavailable"), "provider_5xx"),
    pytest.param(main.NoTextError("x"), "no_text", marks=pytest.mark.xfail(
        strict=True, reason="001_init.sql letters_reason_check does not allow 'no_text' yet")),
    (ExtractionError("x"), "extract_error"),
    (KeyError("x"), "extract_error"),
])
def test_failures_are_recorded_and_the_run_continues(db, stubs, error, reason):
    stubs.urls, stubs.outcomes = [A, B], {A: error}
    assert run() == 0
    status = {r["letter_url"]: (r["status"], r["reason"]) for r in rows(db, "SELECT * FROM letters")}
    assert status == {A: ("failed", reason), B: ("sent", None)}
    assert stubs.scanned == [A, B]


def test_each_url_is_scanned_once_across_runs(db, stubs):
    stubs.urls, stubs.outcomes = [A, B], {A: requests.Timeout()}
    run()
    with connect(db) as conn:
        conn.execute("DELETE FROM scans")  # a new day's run
        conn.execute("UPDATE send_runs SET day = day - 1")
    stubs.urls = [A, B, C]
    run()
    assert stubs.scanned == [A, B, C]


def test_feed_unreachable_scans_nothing(db, stubs):
    stubs.feed_down = True
    assert run() == 1
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["reason"]) == ("failed", "feed_unreachable")
    assert stubs.scanned == [] and rows(db, "SELECT * FROM letters") == []


def test_only_the_reply_to_inbox_on_the_list_is_missing_settings(db, stubs):
    with connect(db) as conn:
        conn.execute("DELETE FROM mailing_list WHERE email <> %s", (REPLY,))
    stubs.urls = [A]
    assert run() == 1
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["reason"]) == ("failed", "missing_settings")
    assert stubs.scanned == [] and rows(db, "SELECT * FROM letters") == []


def two_chunk_list(db):
    with connect(db) as conn:
        conn.execute("DELETE FROM mailing_list")
        for i in range(50):
            conn.execute("INSERT INTO mailing_list (email) VALUES (%s)", (f"m{i:02d}@example.com",))
        conn.execute("INSERT INTO mailing_list (email) VALUES (%s)", (REPLY,))


def test_chunk_two_failure_parks_the_run_and_resume_sends_only_chunk_two(db, stubs):
    two_chunk_list(db)
    stubs.urls, stubs.fail_call = [A], 2
    assert run() == 1
    [r] = rows(db, "SELECT * FROM send_runs")
    assert (r["status"], r["error"]) == ("failed", "validation_error") and r["failed_at"] is not None
    assert [k["idempotency_key"] for k in rows(db, "SELECT * FROM email_log")] == ["run1-b0-c0"]
    assert [x["status"] for x in rows(db, "SELECT * FROM letters")] == ["pending"]
    assert rows(db, "SELECT reason FROM scans")[0]["reason"] == "resend_error"

    assert run() == 1  # a later run stops: no scanning, no new run
    assert [s["reason"] for s in rows(db, "SELECT reason FROM scans ORDER BY id")] == ["resend_error", "send_run_stuck"]
    assert len(stubs.sent) == 1 and stubs.scanned == [A]

    with connect(db) as conn:  # the list changes, then a person presses resume
        conn.execute("DELETE FROM mailing_list WHERE email LIKE 'm%'")
        conn.execute("INSERT INTO mailing_list (email) VALUES ('new@example.com')")
        conn.execute("UPDATE send_runs SET status = 'sending', resume_requested_at = now(), failed_at = NULL")
    stubs.fail_call = None
    assert run() == 0
    assert len(stubs.sent) == 2
    assert stubs.sent[1]["idempotency_key"] == "run1-b0-c1" and stubs.sent[1]["bcc"] == ["m49@example.com"]
    assert [k["idempotency_key"] for k in rows(db, "SELECT * FROM email_log ORDER BY idempotency_key")] == \
        ["run1-b0-c0", "run1-b0-c1"]
    assert rows(db, "SELECT status FROM send_runs")[0]["status"] == "sent"
    assert rows(db, "SELECT status FROM letters")[0]["status"] == "sent"


def test_sending_run_without_resume_request_is_job_died(db, stubs):
    two_chunk_list(db)
    stubs.urls = [A]
    run()
    with connect(db) as conn:
        conn.execute("UPDATE send_runs SET status = 'sending', resume_requested_at = NULL")
    sent_before = len(stubs.sent)
    assert run() == 1
    [r] = rows(db, "SELECT * FROM send_runs")
    assert (r["status"], r["error"]) == ("failed", "job_died")
    assert rows(db, "SELECT reason FROM scans ORDER BY id")[-1]["reason"] == "send_run_stuck"
    assert len(stubs.sent) == sent_before


def test_resume_over_budget_goes_back_to_failed(db, stubs):
    two_chunk_list(db)
    stubs.urls, stubs.fail_call = [A], 2
    run()
    with connect(db) as conn:
        conn.execute("UPDATE send_runs SET status = 'sending', resume_requested_at = now()")
        store.log_email(conn, "test-other", "test", 44)  # 50 + 44 sent today; chunk 2 needs 2 of the 95 usable
    stubs.fail_call = None
    assert run() == 1
    assert rows(db, "SELECT status FROM send_runs")[0]["status"] == "failed"
    assert rows(db, "SELECT reason FROM scans ORDER BY id")[-1]["reason"] == "over_budget"
    assert len(stubs.sent) == 1


def test_over_budget_sends_nothing_and_keeps_letters_pending(db, stubs):
    with connect(db) as conn:
        store.log_email(conn, "test-other", "test", 93)  # 95 usable today; a batch needs 4
    stubs.urls = [A]
    assert run() == 1
    assert rows(db, "SELECT reason FROM scans")[0]["reason"] == "over_budget"
    assert rows(db, "SELECT status FROM letters")[0]["status"] == "pending"
    assert stubs.sent == [] and rows(db, "SELECT * FROM send_runs") == []


def test_mark_seen_makes_the_next_run_scan_nothing(db, stubs):
    stubs.urls = [A, B]
    assert run("--mark-seen") == 0
    assert [(r["status"], r["scanned_at"] is not None) for r in rows(db, "SELECT * FROM letters")] == [("sent", True)] * 2
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["letters_in_feed"]) == ("nothing_new", 2)
    assert run() == 0
    assert stubs.scanned == [] and stubs.sent == []


def test_mark_seen_with_the_feed_down_writes_nothing(db, stubs):
    stubs.feed_down = True
    assert run("--mark-seen") == 1
    assert rows(db, "SELECT * FROM scans") == [] and rows(db, "SELECT * FROM letters") == []


def test_no_email_writes_nothing_to_neon(db, stubs, tmp_path):
    stubs.urls = [A, B]
    assert run("--no-email") == 0
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["1_summary.pdf", "2_summary.pdf"]
    for table in ("letters", "scans", "send_runs", "email_log"):
        assert rows(db, f"SELECT * FROM {table}") == []
    assert stubs.sent == []


def test_to_sends_pending_pdfs_to_one_address_and_logs_a_test(db, stubs):
    with connect(db) as conn:
        store.insert_letter_result(conn, A, "pending", pdf=b"%PDF a")
    assert run("--to", "me@example.com") == 0
    [sent] = stubs.sent
    assert sent["reply_to"] == "me@example.com" and sent["bcc"] == []
    [log] = rows(db, "SELECT * FROM email_log")
    assert (log["kind"], log["emails"]) == ("test", 1) and log["idempotency_key"].startswith("test-")
    assert rows(db, "SELECT status FROM letters")[0]["status"] == "pending"
    assert rows(db, "SELECT * FROM scans") == [] and rows(db, "SELECT * FROM send_runs") == []


@pytest.mark.parametrize("scenario", ["success", "resend_fails", "feed_down", "missing_settings", "quota", "timeout"])
def test_no_address_is_logged(db, stubs, caplog, scenario):
    stubs.urls = [A, B]
    if scenario == "resend_fails":
        stubs.fail_call = 1
    if scenario == "feed_down":
        stubs.feed_down = True
    if scenario == "quota":
        stubs.outcomes = {A: Quota("quota exceeded for r00@example.com")}
    if scenario == "timeout":
        stubs.outcomes = {A: requests.Timeout("timed out talking to staff@example.com")}
    if scenario == "missing_settings":
        with connect(db) as conn:
            conn.execute("DELETE FROM mailing_list WHERE email <> %s", (REPLY,))
    with caplog.at_level(logging.DEBUG):
        run()
        run("--to", "me@example.com")
    assert not any(a in caplog.text for a in LIST + [REPLY, FROM, "me@example.com", "example.com/r"])
    for scan in rows(db, "SELECT * FROM scans"):
        assert not any(a in str(dict(scan)) for a in LIST + [REPLY, FROM])


def test_parse_args_flags_are_exclusive():
    assert main.parse_args(["--to", "a@example.com"]).to == "a@example.com"
    with pytest.raises(SystemExit):
        main.parse_args(["--to", "a@example.com", "--no-email"])
