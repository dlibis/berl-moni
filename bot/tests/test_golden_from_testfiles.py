"""Golden tests driven by the local PDFs in bot/tests/test_files/.

Each test_files PDF whose request has a golden fixture (bot/tests/fixtures/golden/
<req>.json) becomes a parametrized case. The deterministic test runs offline (no
network, no LLM) and checks the fields the Extractor derives without the model; the
full-extraction test runs the whole Extractor (incl. the one coalition LLM call) and
is skipped without an API key for the provider set in MODEL_PROVIDER.
"""
import json
import os
import re

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.env import load_env

load_env()

from bot import bootstrap  # noqa: E402
from common.config import llm_settings  # noqa: E402
from common.db import connect, load_programs  # noqa: E402
from bot.domain.extraction import Extraction, Extractor  # noqa: E402
from bot.adapters.letter_pdf.loader import open_letter  # noqa: E402

TEST_FILES = os.path.join(os.path.dirname(__file__), "test_files")
GOLDEN = os.path.join(os.path.dirname(__file__), "fixtures", "golden")


def _extractor(neon_test_db_url) -> Extractor:
    """The Extractor as the app builds it (model/key from env), with programs from the test DB."""
    with connect(neon_test_db_url) as conn:
        programs = load_programs(conn)
    return bootstrap.extractor(programs)


_HAS_KEY = bool(llm_settings()["api_key"])


def _cases():
    """(request, pdf_path, golden_dict) for every test_files PDF that has a fixture."""
    out = []
    for fname in sorted(os.listdir(TEST_FILES)):
        if not fname.endswith(".pdf"):
            continue
        m = re.search(r"_13_(\d+)\.pdf$", fname) or re.match(r"(\d+)_original\.pdf$", fname)
        if not m:
            continue
        req = m.group(1)
        golden_path = os.path.join(GOLDEN, f"{req}.json")
        if os.path.isfile(golden_path):
            out.append((req, os.path.join(TEST_FILES, fname),
                        json.load(open(golden_path, encoding="utf-8"))))
    return out


CASES = _cases()
IDS = [c[0] for c in CASES]


@pytest.mark.skipif(not CASES, reason="no test_files PDF has a golden fixture")
@pytest.mark.parametrize("req,pdf,golden", CASES, ids=IDS)
def test_deterministic_fields_match_golden(req, pdf, golden, neon_test_db_url):
    """Fields the Extractor derives WITHOUT the LLM — offline, no network."""
    letter = open_letter(pdf)
    text = letter.doc.text
    extractor = _extractor(neon_test_db_url)

    assert Extractor._date(text) == golden["text"]["date"]
    assert extractor._request_number(text) == golden["text"]["request_number"]
    assert Extractor._staffing(text) == golden["text"]["staffing_changes"]

    # table + master relevance (no LLM involved)
    matched = Extraction(pdf, letter.extract_combined_table()).matched(extractor.master)
    assert sorted(matched) == golden["master_matched"]
    assert bool(matched) == golden["expect_summary"]


@pytest.mark.skipif(not (CASES and _HAS_KEY),
                    reason="test_files fixtures or LLM API key (configured provider) not present")
@pytest.mark.parametrize("req,pdf,golden", CASES, ids=IDS)
def test_full_extraction_matches_golden(req, pdf, golden, neon_test_db_url):
    """The whole Extractor, incl. the one coalition LLM call — needs an API key."""
    extractor = _extractor(neon_test_db_url)
    result = extractor.extract(pdf)

    assert result.fields.date == golden["text"]["date"]
    assert result.fields.staffing_changes == golden["text"]["staffing_changes"]
    assert result.fields.coalition_funds == golden["text"]["coalition_funds"]
    assert result.fields.program_number == golden["text"]["program_number"]
    assert sorted(result.matched(extractor.master)) == golden["master_matched"]
    assert result.relevant_to(extractor.master) == golden["expect_summary"]
