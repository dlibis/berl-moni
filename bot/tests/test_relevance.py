"""Relevance paths (spec §2), provenance freeze, and extractor bypass behavior."""
from types import SimpleNamespace

import pytest

from bot.domain.extraction import (
    PROVENANCE_COALITION_FUNDS,
    PROVENANCE_EXACT_CLAUSES,
    RELEVANCE_PROVENANCE_KEY,
    Extraction,
    Extractor,
    exact_bypass_in_text,
)
from bot.domain.request_fields import ProgramUses, Use
from bot.domain.table import Table
from bot.tests.fixtures.extractions import (
    coalition_bypass_extraction,
    complete_extraction,
    complete_irrelevant_extraction,
    exact_bypass_extraction,
    irrelevant_extraction,
)
from bot.service_layer.analysis import request_analysis
from bot.service_layer.unit_of_work import UnitOfWork


def test_exact_bypass_marker():
    assert exact_bypass_in_text("prefix כספים קואליציוניים: כן suffix")


def test_is_relevant_paths():
    master = {"200102"}
    assert complete_extraction().is_relevant(master)
    assert not complete_irrelevant_extraction().is_relevant(master)
    assert coalition_bypass_extraction().is_relevant(set())
    assert exact_bypass_extraction().is_relevant(set())


def test_frozen_provenance_without_master_overlap():
    ext = coalition_bypass_extraction()
    assert ext.is_relevant({"999999"})
    data = ext.to_json()
    again = Extraction.from_json(data)
    assert again.relevance_provenance == PROVENANCE_COALITION_FUNDS
    assert again.is_relevant(set())


def test_provenance_round_trip_key():
    data = exact_bypass_extraction().to_json()
    assert data[RELEVANCE_PROVENANCE_KEY] == PROVENANCE_EXACT_CLAUSES
    assert complete_extraction().to_json().get(RELEVANCE_PROVENANCE_KEY) is None


def test_extractor_exact_bypass_runs_llm(monkeypatch):
    calls = []

    def analyze(region):
        calls.append(region)
        return "לא", [ProgramUses(code="999999", uses=[Use(text="u")])], None

    table = Table.from_records(["number", "name"], [{"number": "999999", "name": "x"}])
    text = "כספים קואליציוניים: כן\nעיקרי הפנייה:\nbody\nתאריך הבקשה: 1/1/2026\nבקשה מספר 13-206"
    letter = SimpleNamespace(
        doc=SimpleNamespace(scanned=False, text=text, markdown=f"עיקרי הפנייה:\nbody\n{text}"),
        source_sha256="a",
        source_size=1,
        extract_combined_table=lambda: table,
        arithmetic_failures=lambda: [],
        decision_links=lambda: [],
        extract_letterhead=lambda: [],
        extract_budget_history=lambda: [],
    )
    result = Extractor(set(), analyze, lambda s: letter).extract("x")
    assert calls and result.is_relevant(set())
    assert result.relevance_provenance == PROVENANCE_EXACT_CLAUSES


@pytest.fixture
def uow(test_db_url):
    with UnitOfWork(test_db_url) as uow:
        uow.conn.execute("TRUNCATE letters, programs RESTART IDENTITY CASCADE")
        uow.commit()
        yield uow


def test_frozen_coalition_stays_done_when_programs_empty(uow):
    from bot.adapters.postgres.letters import slug_for
    from bot.domain.feed import FeedLetter
    from datetime import date

    uow.letters.upsert_feed([FeedLetter("u1", date(2026, 10, 1), "m", (), ())], auto=True)
    claimed = uow.letters.claim()
    ext = coalition_bypass_extraction()
    uow.letters.finish_analysis(
        claimed["letter_url"], claimed["lease_id"], ext.to_json(), "v", sorted(ext.codes()), "ab", 1
    )
    uow.commit()
    slug = slug_for("u1")
    assert request_analysis(uow, slug, None, lambda: True).outcome == "done"
