"""FR-7 — golden tests over a real letter, driven by the single Extractor.

The offline test exercises the Extractor's deterministic tools on the saved raw text (no
network/LLM). The end-to-end test runs the whole Extractor (incl. the one coalition LLM
call) on 21658's local PDF; it skips without an API key for the configured provider (there is no deterministic
fallback for coalition_funds).
"""
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.env import load_env

load_env()

from bot import bootstrap  # noqa: E402
from common.config import llm_settings  # noqa: E402
from common.db import connect, load_programs  # noqa: E402
from bot.domain.extraction import Extractor, MASTER_COLUMN  # noqa: E402

PDF_21658 = os.path.join(_ROOT, "bot", "tests", "test_files", "21658_original.pdf")
RAW_21658 = os.path.join(os.path.dirname(__file__), "fixtures", "golden", "21658_raw.txt")


def _extractor(neon_test_db_url) -> Extractor:
    """The Extractor as the app builds it (model/key from env), with programs from the test DB."""
    with connect(neon_test_db_url) as conn:
        programs = load_programs(conn)
    return bootstrap.extractor(programs)


_HAS_KEY = bool(llm_settings()["api_key"])


@pytest.mark.skipif(not os.path.isfile(RAW_21658), reason="21658 raw text not present")
def test_program_number_includes_programs_from_summary_and_breakdown():
    # FR-3: program codes named anywhere in the narrative. 231039 is introduced in the
    # summary and only detailed in the breakdown — it must still appear. Deterministic,
    # so no LLM/network.
    raw = open(RAW_21658, encoding="utf-8").read()
    codes = [c.strip() for c in Extractor._program_number(Extractor._narrative_region(raw)).split(",")]
    for code in ("231039", "230120", "231038", "230723", "230242", "230243",
                 "231175", "231165", "231202", "230722", "231203"):
        assert code in codes, f"{code} missing from program_number ({codes})"


def test_program_number_and_total_survive_a_one_line_narrative():
    # A heading may share its line with the text before it; nothing may depend on line breaks.
    one_line = ('עיקרי הפנייה: הפנייה נועדה לתקצוב סך של 190,709 אלפי ש"ח בהוצאה. להלן: '
                '231039: שירותים קהילתיים – 139,917 אלפי ש"ח. 230120: שירותי משרד מרכזיים – 104,678.')
    region = Extractor._narrative_region(one_line)
    assert Extractor._program_number(region) == "231039, 230120"
    assert Extractor._total_amount(region) == "190,709"


@pytest.mark.skipif(not (os.path.isfile(PDF_21658) and _HAS_KEY),
                    reason="21658 PDF or LLM API key (configured provider) not present")
def test_extractor_21658(neon_test_db_url):
    """The whole Extractor — deterministic fields + the one coalition LLM call + master."""
    result = _extractor(neon_test_db_url).extract(PDF_21658)

    # deterministic fields
    assert result.fields.date == "01/07/2026"
    assert result.fields.staffing_changes == "לא"
    assert "231039" in result.fields.program_number
    # the one LLM call
    assert result.fields.coalition_funds == "כן"
    assert result.fields.total_amount == "190,709"
    # uses come from 'מטרת השינוי' only: 230120's description is office upkeep (rent, cars), but
    # this request's money is for food security, part of it coalition-funded
    office = " ".join(u.text for u in result.fields.uses("230120"))
    assert "תזונתי" in office and "רכב" not in office and "שכר דירה" not in office
    assert any(u.coalition for u in result.fields.uses("230120"))
    # decisions are named by topic, never by number
    assert not any(n in u.text for p in result.fields.programs for u in p.uses for n in ("550", "1279", "3315"))

    # relevance (FR-5): 10 master matches -> relevant
    assert result.relevant is True
    assert len(result.matched_codes) == 10

    # master column (FR-6): כן/לא per row, correct for a known match and non-match
    assert MASTER_COLUMN in result.table.columns
    by_code = dict(zip(result.table["number"], result.table[MASTER_COLUMN]))
    assert by_code.get("231039") == "כן"   # in master
    assert by_code.get("470102") == "לא"   # not in master
