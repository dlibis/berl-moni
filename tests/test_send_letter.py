from datetime import date
from types import SimpleNamespace

import psycopg
import pytest
from psycopg.rows import dict_row

from bot.adapters.postgres.letters import slug_for
from bot.domain.errors import ResendError
from bot.domain.feed import FeedLetter
from bot.service_layer.sending import send_letter
from bot.service_layer.services import Ports
from bot.service_layer.unit_of_work import UnitOfWork
from bot.tests.fixtures.extractions import complete_extraction, irrelevant_extraction
from common.db import set_setting as write_setting


@pytest.fixture
def uow(test_db_url):
    with UnitOfWork(test_db_url) as uow:
        uow.conn.execute("TRUNCATE letters, programs, scans, email_log, send_runs, mailing_list RESTART IDENTITY CASCADE")
        uow.conn.execute("DELETE FROM settings WHERE key LIKE 'resend_%'")
        uow.conn.execute("INSERT INTO programs (code, name) VALUES ('200102', 'p')")
        uow.conn.execute("INSERT INTO mailing_list (email) VALUES ('m@x.org')")
        write_setting(uow.conn, "from_address", "moni@berl.site")
        write_setting(uow.conn, "reply_to_address", "r@x.org")
        uow.commit()
        yield uow


@pytest.fixture
def query(test_db_url):
    def run(sql):
        with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
            return conn.execute(sql).fetchall()
    return run


@pytest.fixture
def rows(query):
    return query


@pytest.fixture
def one(query):
    return lambda sql: query(sql)[0]


def make_ports(sent, render=lambda extraction, matches: b"%PDF-1.7 fake", fail=None):
    def send_email(**kwargs):
        if fail:
            raise fail
        sent.append(kwargs)
        return f"id{len(sent)}"
    ports = Ports(feed=None, extractor=None, render=render, send_email=send_email, save_copy=None)
    ports.sent = sent
    return ports


@pytest.fixture
def ports():
    return make_ports([])


def analyze(uow, url, extraction=None):
    """A letter in the table; with `extraction` it is analyzed with that result."""
    uow.letters.upsert_feed([FeedLetter(url, date(2026, 10, 1), "חינוך", ("13-206",), ({"ReportUrl": url},))], auto=True)
    if extraction:
        claimed = uow.letters.claim()
        uow.letters.finish_analysis(claimed["letter_url"], claimed["lease_id"], extraction.to_json(),
                                    "m|prompt:1|schema:1", sorted(extraction.codes()), "ab", 3)
    uow.commit()
    return slug_for(url)


@pytest.fixture
def analyzed_relevant(uow):
    return analyze(uow, "u1", complete_extraction())


@pytest.fixture
def irrelevant(uow):
    return analyze(uow, "u2", irrelevant_extraction())


@pytest.fixture
def legacy(uow):
    slug = analyze(uow, "u3", complete_extraction())
    uow.conn.execute("UPDATE letters SET extraction = NULL WHERE slug = %s", (slug,))
    uow.commit()
    return slug


@pytest.fixture
def discovered(uow):
    uow.letters.upsert_feed([FeedLetter("u4", date(2026, 10, 1), "חינוך", ("13-206",), ({"ReportUrl": "u4"},))],
                            auto=False)
    uow.commit()
    return slug_for("u4")


@pytest.fixture
def set_setting(uow):
    def set_(key, value):
        write_setting(uow.conn, key, value)
        uow.commit()
    return set_


@pytest.fixture
def broken_render_ports():
    def render(extraction, matches):
        raise RuntimeError("boom")
    return make_ports([], render=render)


@pytest.fixture
def failing_send_ports():
    return make_ports([], fail=ResendError(422, "validation_error"))


def test_sends_one_letter_to_every_chunk(uow, ports, analyzed_relevant, one, rows):
    assert send_letter(uow, ports, analyzed_relevant, "a@x").outcome == "sent"
    assert len(ports.sent) == 1 and ports.sent[0]["attachments"][0][1].startswith(b"%PDF")
    run = one("SELECT kind, requested_by, status FROM send_runs")
    assert run == {"kind": "manual", "requested_by": "a@x", "status": "sent"}
    assert uow.letters.get(analyzed_relevant)["send_count"] == 1 and rows("SELECT * FROM scans") == []


def test_second_send_without_resend_is_refused(uow, ports, analyzed_relevant):   # Review Focus 2
    send_letter(uow, ports, analyzed_relevant, None)
    assert send_letter(uow, ports, analyzed_relevant, None).outcome == "confirm_resend"
    assert send_letter(uow, ports, analyzed_relevant, None, resend=True).outcome == "sent"
    assert len(ports.sent) == 2 and len(set(k["idempotency_key"] for k in ports.sent)) == 2


def test_irrelevant_legacy_and_unanalyzed_are_not_sendable(uow, ports, irrelevant, legacy, discovered):
    assert {send_letter(uow, ports, s, None).outcome for s in (irrelevant, legacy, discovered)} == {"not_sendable"}


def test_unknown_slug_is_not_found(uow, ports):
    assert send_letter(uow, ports, "nope", None).outcome == "not_found"


def test_missing_settings_is_reported(uow, ports, analyzed_relevant, set_setting):
    set_setting("from_address", "")
    assert send_letter(uow, ports, analyzed_relevant, None) == ("settings", "missing_settings")


def test_over_budget_sends_nothing(uow, ports, analyzed_relevant, set_setting):
    set_setting("resend_daily_limit", 2)  # room for the one-recipient list, but one email is already used today
    set_setting("resend_reserve", 0)
    uow.email_log.add("earlier", "letter", 1)
    uow.commit()
    assert send_letter(uow, ports, analyzed_relevant, None).outcome == "over_budget" and ports.sent == []


def test_render_error_writes_nothing(uow, broken_render_ports, analyzed_relevant, rows):
    assert send_letter(uow, broken_render_ports, analyzed_relevant, None).outcome == "failed"
    assert rows("SELECT * FROM send_runs") == []


def test_resend_error_parks_the_run(uow, failing_send_ports, analyzed_relevant, one):
    r = send_letter(uow, failing_send_ports, analyzed_relevant, None)
    assert r == ("failed", "validation_error") and one("SELECT status FROM send_runs")["status"] == "failed"
