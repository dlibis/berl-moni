import json
from types import SimpleNamespace

import pytest

from bot.domain.extraction import Extraction, Extractor
from bot.domain.request_fields import ProgramUses, Use
from bot.domain.table import Table
from bot.domain.versions import analysis_version, is_outdated
from bot.tests.fixtures.extractions import (
    complete_extraction as make_complete_extraction,
    irrelevant_extraction as make_irrelevant_extraction,
)


@pytest.fixture
def complete_extraction():
    return make_complete_extraction()


@pytest.fixture
def irrelevant_extraction():
    return make_irrelevant_extraction()


@pytest.fixture
def fake_letter():
    table = Table.from_records(
        ["number", "name"],
        [{"number": "200101", "name": "a"}],
    )
    return SimpleNamespace(
        doc=SimpleNamespace(scanned=False),
        source_sha256="ab",
        source_size=3,
        extract_combined_table=lambda: table,
    )


def test_round_trip_complete(complete_extraction):
    data = complete_extraction.to_json()
    assert data["schema_version"] == 2
    again = Extraction.from_json(json.loads(json.dumps(data)))
    assert again == complete_extraction and again.complete


def test_round_trip_irrelevant_has_no_fields(irrelevant_extraction):
    data = irrelevant_extraction.to_json()
    assert data["fields"] is None and not Extraction.from_json(data).complete


def test_relevance_is_recomputed_from_programs(irrelevant_extraction):
    extraction = Extraction.from_json(irrelevant_extraction.to_json())
    assert not extraction.relevant_to({"999999"}) and extraction.relevant_to({"200101"})


def test_versions():
    assert analysis_version("gpt-x") == "gpt-x|prompt:1|schema:2"
    assert not is_outdated("other-model|prompt:1|schema:2")
    assert is_outdated("gpt-x|prompt:0|schema:2")
    assert is_outdated("gpt-x|prompt:1|schema:1") and is_outdated(None)


def test_extractor_records_source_checksum(fake_letter):
    letter = fake_letter
    md = "עיקרי הפנייה:\nbody\nתאריך הבקשה: 1/1/2026\nבקשה מספר 13-206"
    letter.doc.markdown = md
    letter.doc.text = md
    letter.arithmetic_failures = lambda: []
    letter.decision_links = lambda: []
    letter.extract_letterhead = lambda: []
    letter.extract_budget_history = lambda: []
    result = Extractor(
        {"999999"},
        analyze=lambda region: ("לא", [ProgramUses(code="200101", uses=[Use(text="u")])], None),
        load=lambda source: letter,
    ).extract("x")
    assert (result.source_sha256, result.source_size) == ("ab", 3)
