"""The from/to amounts of the budget tables: blank halves, negative amounts, and the arithmetic check."""
import pandas as pd
import pytest
from reportlab.pdfgen import canvas

from bot.adapters.letter_pdf.parser import BudgetLetter
from bot.adapters.letter_pdf.reader import PdfDocument
from bot.domain.errors import ExtractionError


def split(cells: dict) -> dict:
    return PdfDocument("unused.pdf").split_stacked_columns(pd.DataFrame(cells)).iloc[0].to_dict()


def test_a_blank_half_of_a_pair_is_zero_on_the_side_it_was_printed():
    # the reserve row of 21658: -90,000 on the מ- line, blank on ל- (cleaned negatives read 90,000-)
    row = split({"הוצאה": ["90,000-\n", "17,780,480\n17,690,480"]})
    assert (row["הוצאה from"], row["הוצאה to"], row["הוצאה delta"]) == (-90000, 0, 90000)
    row = split({"הוצאה": ["\n5,000", "1\n2"]})  # a new program: blank מ-, amount on ל-
    assert (row["הוצאה from"], row["הוצאה to"]) == (0, 5000)


def test_a_single_number_outside_a_pair_column_loses_the_blank_line():
    assert split({"change": ["90,000\n"]})["change"] == "90,000"


def unbalanced(change: str, before: float, after: float) -> list[str]:
    # amounts as floats, as split_stacked_columns gives them (an int like 10 would look like a code)
    table = pd.DataFrame({"col0": [change], "הוצאה from": [float(before)], "הוצאה to": [float(after)],
                          "הוצאה delta": [float(after - before)], "number": ["470102"]})
    return BudgetLetter(None, "x.pdf")._unbalanced_rows(table)


def test_the_arithmetic_check_passes_a_balanced_row_and_catches_an_unbalanced_one():
    assert unbalanced("90,000", -90000, 0) == []
    assert unbalanced("90,000", -90000, 10) == ["470102"]
    assert unbalanced("90,000-", 100000, 10000) == []  # a negative change, as cleaned


def test_malformed_pdf_is_a_handled_extraction_error(tmp_path):
    path = tmp_path / "malformed.pdf"
    path.write_bytes(b"%PDF-1.7\nnot a PDF")

    with pytest.raises(ExtractionError, match="Could not parse PDF"):
        PdfDocument(str(path)).text


def test_valid_minimal_pdf_is_parsed(tmp_path):
    path = tmp_path / "valid.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(72, 720, "minimal PDF")
    pdf.save()

    assert "minimal PDF" in PdfDocument(str(path)).raw_text


def test_unexpected_reader_error_is_not_hidden(tmp_path, monkeypatch):
    path = tmp_path / "valid.pdf"
    path.write_bytes(b"%PDF-1.7\n")
    monkeypatch.setattr("bot.adapters.letter_pdf.reader.pdfplumber.open", lambda path: (_ for _ in ()).throw(RuntimeError("bug")))

    with pytest.raises(RuntimeError, match="bug"):
        PdfDocument(str(path)).text
