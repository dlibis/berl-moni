"""T6 extraction: heading variants, relevance before the LLM, scans (OCR), arithmetic check.

The model is a fake `analyze` passed to the Extractor; the fixtures are real letters in test_files.
"""
import re
from pathlib import Path

import pytest

from bot.adapters.letter_pdf.loader import open_letter
from bot.adapters.letter_pdf.reader import PdfDocument
from bot.domain.errors import ExtractionError, NoTextError
from bot.domain.extraction import Extractor

FILES = Path(__file__).parent / "test_files"
MASTER = {"384001", "045211", "045110", "045203", "045212", "045213", "046303", "046401"}


CALLS = []  # every region the fake model was asked about, reset per test by `calls`


def fake_analyze(region):
    CALLS.append(region)
    return "לא", "סיכום", None


@pytest.fixture
def calls():
    CALLS.clear()
    return CALLS


@pytest.fixture(scope="module")
def _scan_markdown():
    """OCR the scan once (tens of seconds); the scan tests share the result."""
    return PdfDocument(str(FILES / "pending_199_201_scan.pdf")).markdown


@pytest.fixture
def scan_md(monkeypatch, _scan_markdown):
    monkeypatch.setattr(PdfDocument, "markdown", _scan_markdown)


def _extract(name):
    return Extractor(MASTER, fake_analyze, open_letter).extract(str(FILES / name))


TABLE_LAYOUT_BUG = "the table reader misses the הוצאה from/to columns in this letter's layout (headers shift between pages), so every row's change looks unbalanced and the letter fails as extract_error"


@pytest.mark.parametrize("name", [
    "pending_230_heading_variant.pdf",
    pytest.param("pending_206_213_heading_variant.pdf",
                 marks=pytest.mark.xfail(strict=True, reason=TABLE_LAYOUT_BUG))])
def test_heading_variants_found_with_narrative(calls, name):
    result = _extract(name)
    assert result.relevant and not result.scanned
    assert len(calls) == 1 and calls[0].strip()
    assert result.fields.request_summary == "סיכום"


@pytest.mark.parametrize("name", [
    "pending_170_171_not_relevant.pdf", "pending_21_not_relevant.pdf"])
def test_irrelevant_letter_makes_no_llm_call(calls, name):
    result = _extract(name)
    assert not result.relevant
    assert calls == []


def test_missing_heading_is_extract_error(calls, monkeypatch):
    md = PdfDocument(str(FILES / "pending_230_heading_variant.pdf")).markdown
    monkeypatch.setattr(PdfDocument, "markdown", re.sub(r"עיקרי\s*הפניי?ה", "", md))
    with pytest.raises(ExtractionError, match="heading"):
        _extract("pending_230_heading_variant.pdf")
    assert calls == []


def test_arithmetic_failure_fails_a_text_letter(calls, monkeypatch):
    monkeypatch.setattr("bot.adapters.letter_pdf.parser.BudgetLetter.arithmetic_failures", lambda self: ["045211"])
    with pytest.raises(ExtractionError, match="045211"):
        _extract("pending_230_heading_variant.pdf")
    assert calls == []


@pytest.mark.parametrize("name", [
    "pending_230_heading_variant.pdf",
    pytest.param("pending_206_213_heading_variant.pdf",
                 marks=pytest.mark.xfail(strict=True, reason=TABLE_LAYOUT_BUG))])
def test_arithmetic_passes_on_real_letters(name):
    assert open_letter(str(FILES / name)).arithmetic_failures() == []


def test_scan_is_ocrd_marked_and_relevant_by_table_codes(calls, scan_md):
    result = _extract("pending_199_201_scan.pdf")
    assert result.scanned and result.relevant
    assert result.matched_codes <= MASTER and result.matched_codes
    assert len(calls) == 1 and calls[0].strip()


def test_scan_ocr_with_no_text_is_no_text_error(monkeypatch):
    monkeypatch.setattr(PdfDocument, "scanned", True)
    monkeypatch.setattr("bot.adapters.letter_pdf.reader.pymupdf4llm.to_markdown", lambda *a, **k: "  \n")
    with pytest.raises(NoTextError):
        PdfDocument(str(FILES / "pending_199_201_scan.pdf")).markdown


def test_scan_with_unbalanced_rows_still_extracts(calls, scan_md, monkeypatch):
    monkeypatch.setattr("bot.adapters.letter_pdf.parser.BudgetLetter.arithmetic_failures", lambda self: ["045203"])
    result = _extract("pending_199_201_scan.pdf")
    assert result.scanned and result.relevant  # OCR'd tables can't be checked; the PDF says 'verify'


def test_scan_table_codes_come_from_table_rows_only(monkeypatch):
    md = "טלפון 111111 בטקסט\n|045203|14,100-|\n|x<br>045212|\n"
    monkeypatch.setattr(PdfDocument, "scanned", True)
    monkeypatch.setattr(PdfDocument, "markdown", md)
    table = open_letter("x.pdf").extract_combined_table()
    assert list(table["number"]) == ["045203", "045212"]


def test_scan_trailing_minus_is_moved_in_front(monkeypatch):
    monkeypatch.setattr(PdfDocument, "scanned", True)
    monkeypatch.setattr("bot.adapters.letter_pdf.reader.pymupdf4llm.to_markdown",
                        lambda *a, **k: "|66,970-|10,850-|\nבקשה 83-226 ו-5\n")
    md = PdfDocument("x.pdf").markdown
    assert "|-66,970|-10,850|" in md and "83-226" in md
