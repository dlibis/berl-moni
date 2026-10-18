from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from bot.adapters.postgres.letters import slug_for
from bot.domain.errors import ExtractionError
from bot.domain.feed import FeedLetter
from bot.service_layer.analysis import drain_queue, refresh_feed, request_analysis
from bot.service_layer.unit_of_work import UnitOfWork
from bot.tests.fixtures.extractions import complete_extraction, irrelevant_extraction


def letter(url: str) -> FeedLetter:
    return FeedLetter(url, date(2026, 10, 1), "חינוך", ("13-206",), ({"ReportUrl": url},))


def extractor(extract):
    return SimpleNamespace(extract=extract)


def fail(error):
    def extract(source):
        raise error
    return extract


@pytest.fixture
def uow(test_db_url):
    with UnitOfWork(test_db_url) as uow:
        uow.conn.execute("TRUNCATE letters, programs RESTART IDENTITY CASCADE")
        uow.commit()
        yield uow


@pytest.fixture
def feed():
    return lambda: [letter("u1"), letter("u2")]


@pytest.fixture
def add_program(uow):
    def add(code: str) -> None:
        uow.conn.execute("INSERT INTO programs (code, name) VALUES (%s, 'p')", (code,))
        uow.commit()
    return add


@pytest.fixture
def discovered(uow):
    uow.letters.upsert_feed([letter("u1")], auto=False)
    uow.commit()
    return slug_for("u1")


@pytest.fixture
def queued(uow):
    uow.letters.upsert_feed([letter("u1")], auto=True)
    uow.commit()
    return slug_for("u1")


@pytest.fixture
def two_queued(uow):
    uow.letters.upsert_feed([letter("u1"), letter("u2")], auto=True)
    uow.commit()
    return slug_for("u1"), slug_for("u2")


def analyzed(uow, extraction) -> str:
    uow.letters.upsert_feed([letter("u9")], auto=True)
    claimed = uow.letters.claim()
    assert uow.letters.finish_analysis(claimed["letter_url"], claimed["lease_id"], extraction.to_json(),
                                       "m|prompt:1|schema:1", sorted(extraction.codes()), "ab", 3)
    uow.commit()
    return slug_for("u9")


@pytest.fixture
def analyzed_complete(uow):
    return analyzed(uow, complete_extraction())


@pytest.fixture
def analyzed_irrelevant(uow):
    return analyzed(uow, irrelevant_extraction())


@pytest.fixture
def fake_extractor():
    return extractor(lambda source: irrelevant_extraction())


@pytest.fixture
def failing_extractor():
    return extractor(fail(ExtractionError("no heading")))


@pytest.fixture
def quota_extractor():
    return extractor(fail(RuntimeError("quota exceeded")))


def test_refresh_inserts_new_and_updates_seen(uow, feed):
    assert refresh_feed(uow, feed) == (2, 0)
    assert refresh_feed(uow, lambda: feed()[:1]) == (0, 1)
    row = uow.letters.get(slug_for("u1"))
    assert row["analysis_status"] == "discovered" and row["last_seen_in_feed_at"]
    assert (row["ministry"], row["request_numbers"], row["feed_rows"]) == ("חינוך", ["13-206"], [{"ReportUrl": "u1"}])


def test_refresh_with_auto_queues_new_letters(uow, feed):
    refresh_feed(uow, feed, auto=True)
    assert uow.letters.get(slug_for("u1"))["analysis_status"] == "queued"


def test_request_queues_and_dispatches_once(uow, discovered):
    calls = []
    assert request_analysis(uow, discovered, "a@x", lambda: calls.append(1) or True) == ("queued", True)
    assert request_analysis(uow, discovered, "a@x", lambda: calls.append(1) or True).outcome == "busy"
    assert calls == [1]
    assert uow.letters.get(discovered)["analysis_requested_by"] == "a@x"


def test_request_unknown_slug_is_not_found(uow):
    assert request_analysis(uow, "nope", None, lambda: True) == ("not_found", False)


def test_complete_result_is_done_without_llm(uow, analyzed_complete):
    assert request_analysis(uow, analyzed_complete, None, lambda: True).outcome == "done"


def test_newly_relevant_letter_needs_llm(uow, analyzed_irrelevant, add_program):  # Review Focus 1
    assert request_analysis(uow, analyzed_irrelevant, None, lambda: True).outcome == "done"
    add_program("200101")
    assert request_analysis(uow, analyzed_irrelevant, None, lambda: True).outcome == "queued"


def test_drain_analyzes_and_saves_json(uow, queued, fake_extractor):
    assert drain_queue(uow, lambda programs: fake_extractor, "m") == (1, False)
    row = uow.letters.get(queued)
    assert row["analysis_status"] == "analyzed" and row["extraction"]["schema_version"] == 1
    assert row["extraction_version"] == "m|prompt:1|schema:1" and row["codes"] == ["200101"]
    assert row["lease_id"] is None and row["analyzed_at"] and row["attempts"] == 1


def test_stale_lease_writes_nothing(uow, queued):
    claimed = uow.letters.claim(); uow.commit()
    assert uow.letters.finish_analysis(claimed["letter_url"], uuid4(), {}, "v", [], "", 0) is False
    assert uow.letters.fail_analysis(claimed["letter_url"], uuid4(), "quota") is False
    assert uow.letters.get(queued)["analysis_status"] == "analyzing"


def test_two_claims_never_get_the_same_letter(test_db_url, two_queued):
    with UnitOfWork(test_db_url) as a, UnitOfWork(test_db_url) as b:
        first = a.letters.claim()   # a holds its row lock until it commits
        second = b.letters.claim()
        a.commit(); b.commit()
        assert b.letters.claim() is None
    assert {first["letter_url"], second["letter_url"]} == {"u1", "u2"}


def test_expired_lease_requeues_then_fails_after_three(uow, queued):
    assert uow.letters.has_queued()
    for attempt in (1, 2, 3):
        assert uow.letters.claim()["attempts"] == attempt
        uow.commit()
        assert not uow.letters.has_queued()
        uow.conn.execute("UPDATE letters SET lease_expires_at = now() - interval '1 minute'")
        uow.commit()
        assert uow.letters.has_queued()
        assert uow.letters.requeue_expired() == 1
        uow.commit()
    row = uow.letters.get(queued)
    assert (row["analysis_status"], row["last_error"], row["lease_id"]) == ("failed", "lease_expired", None)
    assert uow.letters.claim() is None


def test_reanalysis_failure_keeps_old_json(uow, analyzed_complete, failing_extractor):
    request_analysis(uow, analyzed_complete, None, lambda: True, reanalyze=True)
    drain_queue(uow, lambda p: failing_extractor, "m")
    row = uow.letters.get(analyzed_complete)
    assert row["analysis_status"] == "analyzed" and row["extraction"] and row["last_error"] == "extract_error"


def test_failure_without_old_json_is_failed_and_can_be_queued_again(uow, queued, failing_extractor):
    assert drain_queue(uow, lambda p: failing_extractor, "m").analyzed == 0
    assert uow.letters.get(queued)["analysis_status"] == "failed"
    assert request_analysis(uow, queued, None, lambda: False) == ("queued", False)


def test_quota_stops_the_drain(uow, two_queued, quota_extractor):
    assert drain_queue(uow, lambda p: quota_extractor, "m") == (0, False)
    rows = [uow.letters.get(slug) for slug in two_queued]
    assert sorted((r["analysis_status"], r["last_error"]) for r in rows) == [("failed", "quota"), ("queued", None)]
