"""bot.entrypoints.main: the drain and the send job against the local test Postgres, with fake Ports for
the feed, the Extractor, the renderer and Resend."""
import logging
import urllib.error
from datetime import datetime, timedelta, timezone

import pytest
import requests

from bot.adapters.postgres.email_log import EmailLogRepository
from bot.adapters.postgres.send_runs import SendRunsRepository
from bot.domain.errors import DownloadError, ExtractionError, FeedUnreachable, NoTextError, ResendError
from bot.domain.feed import FeedLetter
from bot.entrypoints import main
from bot.service_layer import services
from bot.service_layer.services import Ports
from bot.service_layer.unit_of_work import UnitOfWork
from bot.tests.fixtures.extractions import complete_extraction, irrelevant_extraction
from common.db import connect, set_setting

FROM, REPLY = "news@berl.site", "staff@example.com"
LIST = [f"r{i:02d}@example.com" for i in range(3)]
A, B, C = (f"https://example.com/letters/{n}.pdf" for n in (1, 2, 3))
PDF = b"%PDF-1.4 summary"
PROGRAM = "200102"  # in complete_extraction(), not in irrelevant_extraction()
EVERY_DAY = [{"from": "2000-01-01", "to": "2099-12-31",
              "days": {d: {"enabled": True, "time": "00:00"} for d in ("sun", "mon", "tue", "wed", "thu", "fri", "sat")}}]


class Quota(Exception):
    status_code = 429


def letter(url):
    return FeedLetter(url, None, "", (), ())


class Stubs:
    """Fake Ports: the feed, the Extractor, the renderer and Resend. `outcomes` maps a URL to an Extraction
    (default: complete and relevant to PROGRAM) or an exception."""

    def __init__(self):
        self.urls, self.outcomes, self.scanned, self.sent = [], {}, [], []
        self.clock_ahead = timedelta(0)
        self.feed_down, self.fail_call, self.pdf = False, None, PDF

    def fetch_letters(self):
        if self.feed_down:
            raise FeedUnreachable("page 1: ConnectionError")
        return [letter(url) for url in self.urls]

    def extract(self, url):
        self.scanned.append(url)
        outcome = self.outcomes.get(url, complete_extraction())
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def send_email(self, **kwargs):
        if self.fail_call == len(self.sent) + 1:
            raise ResendError(422, "validation_error")
        self.sent.append(kwargs)
        return f"em_{len(self.sent)}"

    def render(self, result, programs):
        if isinstance(self.pdf, Exception):
            raise self.pdf
        return self.pdf

    def ports(self):
        return Ports(feed=self.fetch_letters, extractor=lambda programs: self, render=self.render,
                     send_email=self.send_email, save_copy=lambda source, dest: None,
                     now=lambda: datetime.now(timezone.utc) + self.clock_ahead)


@pytest.fixture
def stubs():
    return Stubs()


@pytest.fixture
def db(test_db_url, stubs, monkeypatch, tmp_path):
    with connect(test_db_url) as conn:
        conn.execute("TRUNCATE letters, scans, email_log, send_runs, mailing_list, programs RESTART IDENTITY CASCADE")
        conn.execute("INSERT INTO programs (code, name) VALUES (%s, 'p')", (PROGRAM,))
        for key, value in dict(schedule=EVERY_DAY, from_address=FROM, reply_to_address=REPLY, resend_daily_limit=100,
                               resend_monthly_limit=3000, resend_reserve=5,
                               auto_since="2000-01-01T00:00:00+00:00").items():
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


def run(stubs, *args):
    return main.main(list(args), ports=stubs.ports())


def analyzed(db, url, extraction=None):
    """A letter already discovered, analyzed and never sent (as the drain leaves it)."""
    with UnitOfWork(db) as uow:
        uow.letters.upsert_feed([letter(url)], auto=True)
        claimed = uow.letters.claim()
        extraction = extraction or complete_extraction()
        assert uow.letters.finish_analysis(url, claimed["lease_id"], extraction.to_json(), "m|prompt:1|schema:1",
                                           sorted(extraction.codes()), "ab", 3)
        uow.commit()


def test_nothing_new(db, stubs):
    assert run(stubs) == 0
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["new_letters"], scan["emails_sent"]) == ("nothing_new", 0, 0)
    assert stubs.sent == [] and rows(db, "SELECT * FROM send_runs") == []


def test_not_due_writes_no_scan(db, stubs):
    with connect(db) as conn:
        set_setting(conn, "schedule", [])
    assert run(stubs) == 0
    assert rows(db, "SELECT * FROM scans") == [] and stubs.scanned == []


def test_one_relevant_letter_is_sent_once(db, stubs):
    stubs.urls = [A]
    assert run(stubs) == 0
    [row] = rows(db, "SELECT * FROM letters")
    assert (row["letter_url"], row["analysis_status"], row["send_count"]) == (A, "analyzed", 1)
    assert row["last_sent_at"] is not None and row["extraction"]["fields"]
    [sent] = stubs.sent
    assert sent["bcc"] == LIST and sent["reply_to"] == REPLY and sent["idempotency_key"] == "run1-b0-c0"
    assert sent["attachments"] == [("1_summary.pdf", PDF)]
    [log] = rows(db, "SELECT * FROM email_log")
    assert (log["idempotency_key"], log["emails"], log["kind"]) == ("run1-b0-c0", 4, "letter")
    [r] = rows(db, "SELECT * FROM send_runs")
    assert r["status"] == "sent" and r["recipients"] is None
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["relevant"], scan["emails_sent"], scan["letters_in_feed"]) == ("sent", 1, 4, 1)
    # a second run on the same day does nothing, and scans nothing again
    assert run(stubs) == 0
    assert len(stubs.sent) == 1 and stubs.scanned == [A] and len(rows(db, "SELECT * FROM scans")) == 1


def test_irrelevant_letter_is_analyzed_and_not_sent(db, stubs):
    stubs.urls, stubs.outcomes = [A], {A: irrelevant_extraction()}
    assert run(stubs) == 0
    [row] = rows(db, "SELECT * FROM letters")
    assert (row["analysis_status"], row["send_count"], row["summary_pdf"]) == ("analyzed", 0, None)
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["new_letters"], scan["relevant"]) == ("nothing_new", 1, 0)
    assert stubs.sent == []


def statuses(db):
    return {r["letter_url"]: (r["analysis_status"], r["last_error"], r["send_count"])
            for r in rows(db, "SELECT * FROM letters")}


def test_quota_stops_the_drain_but_analyzed_letters_go_out(db, stubs):
    old = "https://example.com/old.pdf"
    analyzed(db, old)
    stubs.urls, stubs.outcomes = [A, B], {A: Quota("insufficient_quota")}
    assert run(stubs) == 0
    assert statuses(db) == {old: ("analyzed", None, 1), A: ("failed", "quota", 0), B: ("queued", None, 0)}
    assert stubs.scanned == [A] and len(stubs.sent) == 1
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["new_letters"], scan["relevant"]) == ("sent", 2, 1)


def test_quota_with_nothing_analyzed_is_nothing_new(db, stubs):
    stubs.urls, stubs.outcomes = [A], {A: Quota()}
    assert run(stubs) == 0
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["new_letters"]) == ("nothing_new", 1)


@pytest.mark.parametrize("error, reason", [
    (requests.Timeout("t"), "network"),
    (requests.ConnectionError("c"), "network"),
    (DownloadError("https://x/1.pdf", 4, urllib.error.HTTPError("https://x/1.pdf", 503, "Unavailable", None, None)),
     "provider_5xx"),
    (DownloadError("https://x/1.pdf", 4, urllib.error.URLError("refused")), "network"),
    (NoTextError("x"), "no_text"),
    (ExtractionError("x"), "extract_error"),
])
def test_failures_are_recorded_and_the_run_continues(db, stubs, error, reason):
    stubs.urls, stubs.outcomes = [A, B], {A: error}
    assert run(stubs) == 0
    assert statuses(db) == {A: ("failed", reason, 0), B: ("analyzed", None, 1)}
    assert stubs.scanned == [A, B]


def test_unexpected_error_is_recorded_the_other_letter_is_sent_and_the_job_fails(db, stubs):
    stubs.urls, stubs.outcomes = [A, B], {A: KeyError("bug")}
    assert run(stubs) == 1  # a bug must turn the GitHub run red
    assert statuses(db) == {A: ("failed", "extract_error", 0), B: ("analyzed", None, 1)}
    assert len(stubs.sent) == 1 and stubs.scanned == [A, B]
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["emails_sent"]) == ("sent", 4)


def test_each_url_is_scanned_once_across_runs(db, stubs):
    stubs.urls, stubs.outcomes = [A, B], {A: requests.Timeout()}
    run(stubs)
    with connect(db) as conn:
        conn.execute("DELETE FROM scans")  # a new day's run
        conn.execute("UPDATE send_runs SET day = day - 1")
    stubs.urls = [A, B, C]
    run(stubs)
    assert stubs.scanned == [A, B, C]


def test_feed_unreachable_scans_nothing(db, stubs):
    stubs.feed_down = True
    assert run(stubs) == 1
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["reason"]) == ("failed", "feed_unreachable")
    assert stubs.scanned == [] and rows(db, "SELECT * FROM letters") == []


def test_only_the_reply_to_inbox_on_the_list_is_missing_settings(db, stubs):
    with connect(db) as conn:
        conn.execute("DELETE FROM mailing_list WHERE email <> %s", (REPLY,))
    stubs.urls = [A]
    assert run(stubs) == 1
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
    assert run(stubs) == 1
    [r] = rows(db, "SELECT * FROM send_runs")
    assert (r["status"], r["error"]) == ("failed", "validation_error") and r["failed_at"] is not None
    assert [(k["idempotency_key"], k["status"]) for k in rows(db, "SELECT * FROM email_log ORDER BY idempotency_key")] == \
        [("run1-b0-c0", "sent"), ("run1-b0-c1", "sending")]
    assert [x["send_count"] for x in rows(db, "SELECT * FROM letters")] == [0]
    assert rows(db, "SELECT reason FROM scans")[0]["reason"] == "resend_error"

    assert run(stubs) == 1  # a later run stops: no scanning, no new run
    assert [s["reason"] for s in rows(db, "SELECT reason FROM scans ORDER BY id")] == ["resend_error", "send_run_stuck"]
    assert len(stubs.sent) == 1 and stubs.scanned == [A]

    with connect(db) as conn:  # the list changes, then a person presses resume
        conn.execute("DELETE FROM mailing_list WHERE email LIKE 'm%'")
        conn.execute("INSERT INTO mailing_list (email) VALUES ('new@example.com')")
        conn.execute("UPDATE send_runs SET status = 'sending', resume_requested_at = now(), failed_at = NULL")
    stubs.fail_call = None
    assert run(stubs) == 0
    assert len(stubs.sent) == 2
    assert stubs.sent[1]["idempotency_key"] == "run1-b0-c1" and stubs.sent[1]["bcc"] == ["m49@example.com"]
    assert [k["idempotency_key"] for k in rows(db, "SELECT * FROM email_log ORDER BY idempotency_key")] == \
        ["run1-b0-c0", "run1-b0-c1"]
    assert rows(db, "SELECT status FROM send_runs")[0]["status"] == "sent"
    assert rows(db, "SELECT send_count FROM letters")[0]["send_count"] == 1


def test_stale_sending_row_becomes_unknown_and_parks_run(db, stubs):
    analyzed(db, A)
    with connect(db) as conn:
        run_id = SendRunsRepository(conn).start(
            services.datetime.now().date(), FROM, REPLY, LIST, [[A]])
        EmailLogRepository(conn).start(f"run{run_id}-b0-c0", "letter", len(LIST) + 1)
        conn.execute("UPDATE email_log SET started_at = now() - interval '25 hours'")
        conn.execute("UPDATE send_runs SET resume_requested_at = now() WHERE id = %s", (run_id,))

    assert run(stubs) == 1
    assert rows(db, "SELECT status FROM email_log")[0]["status"] == "unknown"
    assert rows(db, "SELECT status, error FROM send_runs")[0] == {"status": "failed", "error": "send_unknown"}
    assert stubs.sent == []


def test_crash_after_start_retries_same_key(db, stubs):
    analyzed(db, A)
    with connect(db) as conn:
        run_id = SendRunsRepository(conn).start(
            services.datetime.now().date(), FROM, REPLY, LIST, [[A]])
        key = f"run{run_id}-b0-c0"
        EmailLogRepository(conn).start(key, "letter", len(LIST) + 1)
        conn.execute("UPDATE email_log SET started_at = now() - interval '1 hour'")
        conn.execute("UPDATE send_runs SET resume_requested_at = now() WHERE id = %s", (run_id,))

    assert run(stubs) == 0
    assert [message["idempotency_key"] for message in stubs.sent] == [key]
    assert stubs.sent[0]["attachments"] == [("1_summary.pdf", PDF)]
    assert rows(db, "SELECT status, resend_email_id FROM email_log")[0] == {
        "status": "sent", "resend_email_id": "em_1"}
    assert rows(db, "SELECT status FROM send_runs")[0]["status"] == "sent"


def test_sending_run_without_resume_request_is_job_died(db, stubs):
    two_chunk_list(db)
    stubs.urls = [A]
    run(stubs)
    with connect(db) as conn:
        conn.execute("UPDATE send_runs SET status = 'sending', resume_requested_at = NULL")
    sent_before = len(stubs.sent)
    assert run(stubs) == 1
    [r] = rows(db, "SELECT * FROM send_runs")
    assert (r["status"], r["error"]) == ("failed", "job_died")
    assert rows(db, "SELECT reason FROM scans ORDER BY id")[-1]["reason"] == "send_run_stuck"
    assert len(stubs.sent) == sent_before


def test_a_manual_send_still_in_its_web_request_is_left_alone(db, stubs):
    with connect(db) as conn:  # a Send click a moment ago: the Flask request is still delivering
        conn.execute("INSERT INTO send_runs (day, status, kind, from_address, reply_to_address, recipients, batches) "
                     "VALUES (current_date, 'sending', 'manual', %s, %s, '[]', '[]')", (FROM, REPLY))
    assert run(stubs) == 0
    [r] = rows(db, "SELECT status, error FROM send_runs")
    assert (r["status"], r["error"]) == ("sending", None) and stubs.sent == []


def test_a_manual_send_older_than_the_web_time_limit_is_job_died(db, stubs):
    with connect(db) as conn:
        conn.execute("INSERT INTO send_runs (day, status, kind, from_address, reply_to_address, recipients, batches, "
                     "started_at) VALUES (current_date, 'sending', 'manual', %s, %s, '[]', '[]', "
                     "now() - interval '10 minutes')", (FROM, REPLY))
    assert run(stubs) == 1
    assert rows(db, "SELECT error FROM send_runs")[0]["error"] == "job_died"


def test_resume_over_budget_goes_back_to_failed(db, stubs):
    two_chunk_list(db)
    stubs.urls, stubs.fail_call = [A], 2
    run(stubs)
    with connect(db) as conn:
        conn.execute("UPDATE send_runs SET status = 'sending', resume_requested_at = now()")
        EmailLogRepository(conn).add("test-other", "test", 44)  # 50 + 44 sent today; chunk 2 needs 2 of the 95 usable
    stubs.fail_call = None
    assert run(stubs) == 1
    assert rows(db, "SELECT status FROM send_runs")[0]["status"] == "failed"
    assert rows(db, "SELECT reason FROM scans ORDER BY id")[-1]["reason"] == "over_budget"
    assert len(stubs.sent) == 1


def test_over_budget_sends_nothing_and_keeps_letters_unsent(db, stubs):
    with connect(db) as conn:
        EmailLogRepository(conn).add("test-other", "test", 93)  # 95 usable today; a batch needs 4
    stubs.urls = [A]
    assert run(stubs) == 1
    assert rows(db, "SELECT reason FROM scans")[0]["reason"] == "over_budget"
    assert statuses(db) == {A: ("analyzed", None, 0)}
    assert stubs.sent == [] and rows(db, "SELECT * FROM send_runs") == []


def test_letters_discovered_before_auto_since_are_not_sent(db, stubs):
    with UnitOfWork(db) as uow:
        uow.letters.upsert_feed([letter(A)], auto=False)
        uow.commit()
    analyzed(db, B)
    with connect(db) as conn:
        conn.execute("UPDATE letters SET first_seen_at = now() - interval '1 day'")
        set_setting(conn, "auto_since", services.datetime.now(services.timezone.utc).isoformat())
    stubs.urls = [A, B]
    assert run(stubs) == 0
    assert statuses(db) == {A: ("discovered", None, 0), B: ("analyzed", None, 0)}
    assert stubs.scanned == [] and stubs.sent == []
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["letters_in_feed"], scan["new_letters"]) == ("nothing_new", 2, 0)


def test_first_due_run_without_auto_since_sets_it_and_sends_new_letters(db, stubs):
    with connect(db) as conn:  # a schedule saved before auto_since existed
        conn.execute("DELETE FROM settings WHERE key = 'auto_since'")
    stubs.urls, stubs.clock_ahead = [A], timedelta(seconds=2)  # the runner's clock ahead of Postgres'
    assert run(stubs) == 0
    assert statuses(db) == {A: ("analyzed", None, 1)} and len(stubs.sent) == 1
    assert rows(db, "SELECT value FROM settings WHERE key = 'auto_since'")[0]["value"]


def test_queued_letters_drain_even_when_not_due(db, stubs):
    with UnitOfWork(db) as uow:
        uow.letters.upsert_feed([letter(A)], auto=True)
        uow.commit()
        set_setting(uow.conn, "schedule", [])
        uow.commit()
    assert run(stubs) == 0
    assert statuses(db) == {A: ("analyzed", None, 0)} and stubs.scanned == [A]
    assert rows(db, "SELECT * FROM scans") == [] and stubs.sent == []


def test_mark_seen_flag_is_gone(capsys):
    with pytest.raises(SystemExit):
        main.parse_args(["--mark-seen"])


def test_no_email_writes_nothing_to_neon(db, stubs, tmp_path):
    stubs.urls = [A, B]
    assert run(stubs, "--no-email") == 0
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["1_summary.pdf", "2_summary.pdf"]
    for table in ("letters", "scans", "send_runs", "email_log"):
        assert rows(db, f"SELECT * FROM {table}") == []
    assert stubs.sent == []


def test_to_sends_unsent_letters_to_one_address_and_logs_a_test(db, stubs):
    analyzed(db, A)
    with connect(db) as conn:  # --to ignores auto_since
        set_setting(conn, "auto_since", "2099-01-01T00:00:00+00:00")
    assert run(stubs, "--to", "me@example.com") == 0
    [sent] = stubs.sent
    assert sent["reply_to"] == "me@example.com" and sent["bcc"] == []
    assert sent["attachments"] == [("1_summary.pdf", PDF)]
    [log] = rows(db, "SELECT * FROM email_log")
    assert (log["kind"], log["emails"]) == ("test", 1) and log["idempotency_key"].startswith("test-")
    assert statuses(db) == {A: ("analyzed", None, 0)}
    assert rows(db, "SELECT * FROM scans") == [] and rows(db, "SELECT * FROM send_runs") == []


def test_send_test_message_returns_one_when_resend_fails(db, stubs):
    stubs.fail_call = 1
    with UnitOfWork(db) as uow:
        assert services.send_test_message(uow, stubs.ports(), ["me@example.com"]) == 1
    assert stubs.sent == [] and rows(db, "SELECT * FROM email_log") == []


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
        run(stubs)
        run(stubs, "--to", "me@example.com")
    assert not any(a in caplog.text for a in LIST + [REPLY, FROM, "me@example.com", "example.com/r"])
    for scan in rows(db, "SELECT * FROM scans"):
        assert not any(a in str(dict(scan)) for a in LIST + [REPLY, FROM])


def test_parse_args_flags_are_exclusive():
    assert main.parse_args(["--to", "a@example.com"]).to == "a@example.com"
    with pytest.raises(SystemExit):
        main.parse_args(["--to", "a@example.com", "--no-email"])


def test_oversized_pdf_is_counted_failed_and_not_sent(db, stubs):
    stubs.urls, stubs.pdf = [A], b"%PDF" + bytes(30 * 2**20)  # rendered fine, but over the 24 MB cap once encoded
    assert run(stubs) == 0
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["relevant"], scan["failed"]) == ("nothing_new", 1, 1)
    assert stubs.sent == [] and statuses(db) == {A: ("analyzed", None, 0)}


def test_render_error_is_counted_failed_and_fails_the_job(db, stubs):
    stubs.urls, stubs.pdf = [A], ValueError("bad font")
    assert run(stubs) == 1
    [scan] = rows(db, "SELECT * FROM scans")
    assert (scan["status"], scan["failed"]) == ("nothing_new", 1)
    assert stubs.sent == [] and statuses(db) == {A: ("analyzed", None, 0)}


def test_unexpected_error_keeps_its_traceback_and_a_bad_letter_does_not(db, stubs, caplog):
    stubs.urls, stubs.outcomes = [A, B], {A: KeyError("bug"), B: ExtractionError("no heading")}
    with caplog.at_level(logging.WARNING):
        run(stubs)
    traced = {r.getMessage().split(":")[0] for r in caplog.records if r.exc_info}
    assert traced == {"1"}  # the KeyError (letter 1), not the unreadable letter 2


def test_no_email_exits_non_zero_when_a_letter_fails(db, stubs):
    stubs.urls, stubs.outcomes = [A, B], {A: ExtractionError("no heading")}
    assert run(stubs, "--no-email") == 1
