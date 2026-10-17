"""Focused tests for the summary PDF's real output and pure layout helpers."""
import json
from pathlib import Path

import pandas as pd
import pymupdf

from bot.adapters.summary_pdf.hebrew_text import rtl, wrap_rtl_html
from bot.adapters.summary_pdf.renderer import FONT, SummaryPdfRenderer, budget_table_rows
from bot.domain.extraction import Extraction
from bot.domain.request_fields import RequestFields

GOLDEN = Path(__file__).parent / "fixtures" / "golden"


def test_render_real_summary_pdf(tmp_path):
    golden = json.loads((GOLDEN / "21656.json").read_text(encoding="utf-8"))
    extras = json.loads((GOLDEN / "21656_extras.json").read_text(encoding="utf-8"))
    history = [(item["title"], pd.DataFrame(item["data"], columns=item["columns"]))
               for item in extras["history"]]
    extraction = Extraction(
        source=golden["source"],
        table=pd.DataFrame(golden["table"]),
        matched_codes=set(golden["master_matched"]),
        relevant=True,
        fields=RequestFields(**golden["text"]),
        letterhead=extras["letterhead"],
        budget_history=history,
    )
    master = extraction.table[extraction.table["master"] == "כן"]
    programs = dict(zip(master["number"].astype(str), master["name"].astype(str).str.strip()))

    output = SummaryPdfRenderer().render(extraction, tmp_path / "21656_summary.pdf", programs)

    with pymupdf.open(output) as document:
        text = "".join(page.get_text() for page in document)
        assert document.page_count >= 1
    assert golden["source"] in text


def test_budget_table_rows_has_header_two_rows_per_item_and_spans():
    table = pd.DataFrame([
        {"number": "123456", "name": "תוכנית א", "הוצאה from": 100, "הוצאה to": 150,
         "הרשאה להתחייב from": 20, "הרשאה להתחייב to": 20, "master": "כן"},
        {"number": "654321", "name": "תוכנית ב", "הוצאה from": 80, "הוצאה to": 60,
         "הרשאה להתחייב from": 10, "הרשאה להתחייב to": 12, "master": "לא"},
    ])

    rows, spans = budget_table_rows(table)

    assert rows[0] == [rtl(value) for value in
                       ["מספר פרט", "שם הפרט", "", "הוצאה", "הרשאה להתחייב", "שינוי", "master"]]
    assert len(rows) == 1 + 2 * len(table)
    assert rows[1][0] == "123456" and rows[2][0] == ""
    assert rows[1][2] == rtl("מ-") and rows[2][2] == rtl("ל-")
    assert spans == [
        (0, 1, 2), (1, 1, 2), (5, 1, 2), (6, 1, 2),
        (0, 3, 4), (1, 3, 4), (5, 3, 4), (6, 3, 4),
    ]


def test_wrap_rtl_html_wraps_long_text_and_bolds_change_purpose_label():
    SummaryPdfRenderer()  # registers the bundled Hebrew font used by stringWidth
    text = "מטרת השינוי: " + " ".join(["טקסט ארוך לבדיקה"] * 12)

    html = wrap_rtl_html(text, 120, FONT, bold_labels=True)

    assert html.count("<br/>") >= 2
    assert f"<b>{rtl('מטרת השינוי:')}</b>" in html
