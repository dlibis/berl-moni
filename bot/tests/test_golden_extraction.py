"""FR-7 — golden tests over a real letter's saved raw text: the Extractor's deterministic
tools only, no network and no LLM."""
import os

import pytest

from bot.domain.extraction import Extractor

RAW_21658 = os.path.join(os.path.dirname(__file__), "fixtures", "golden", "21658_raw.txt")


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
