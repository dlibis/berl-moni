"""Focused tests for the summary PDF's real output and pure layout helpers."""
import json
from pathlib import Path

import pandas as pd
import pymupdf

from bot.adapters.summary_pdf.hebrew_text import rtl, wrap_rtl_html
from bot.adapters.summary_pdf.money_flow import fold, hubs, transfer_summary
from bot.adapters.summary_pdf.renderer import SummaryPdfRenderer, budget_table_rows
from bot.adapters.summary_pdf.theme import FONT
from bot.domain.extraction import Extraction
from bot.domain.request_fields import ProgramUses, RequestFields, Use

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
        links = [link.get("uri") for page in document for link in page.get_links()]
        assert document.page_count >= 1
    assert golden["source"] in links


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


def test_transfer_summary_nets_each_item_and_drops_pass_through():
    table = pd.DataFrame([
        {"number": "470102", "name": "רזרבה", "הוצאה from": -90, "הוצאה to": 0, "master": "לא"},
        {"number": "121101", "name": "גמלאות", "הוצאה from": 500, "הוצאה to": 410, "master": "לא"},
        {"number": "470102", "name": "רזרבה", "הוצאה from": 90, "הוצאה to": 0, "master": "לא"},
        {"number": "231039", "name": "שירותים", "הוצאה from": 100, "הוצאה to": 190, "master": "כן"},
    ])

    sources, destinations, metric = transfer_summary(table)

    assert metric == "הוצאה"
    assert sources == [("121101", "גמלאות", 90)]
    assert destinations == [("231039", "שירותים", 90)]


def test_hubs_split_sources_into_reserve_and_internal_transfer():
    table = pd.DataFrame([{"number": "470102", "name": "תוכנית מעבר - רזרבה כללית"}])
    sources = [("230721", "חוץ ביתי", 115), ("544003", "החלטות ממשלה", 100), ("121101", "גמלאות", 90)]
    destinations = [("231039", "שירותים", 205), ("230120", "משרד", 100)]

    assert hubs(sources, destinations, table) == [
        ("רזרבה כללית", [("544003", "החלטות ממשלה", 100), ("121101", "גמלאות", 90)]),
        ("העברה פנימית", [("230721", "חוץ ביתי", 115)]),
    ]


def test_fold_keeps_five_and_never_folds_a_single_item():
    items = [(str(i), "x", 10 - i) for i in range(8)]
    assert fold(items) == (items[:5], items[5:])
    assert fold(items[:6]) == (items[:6], [])


def test_why_table_shows_each_use_and_tags_coalition_money(tmp_path):
    table = pd.DataFrame([
        {"number": "230120", "name": "שירותי משרד מרכזיים", "הוצאה from": 100, "הוצאה to": 200, "master": "לא"},
        {"number": "230721", "name": "חוץ ביתי", "הוצאה from": 300, "הוצאה to": 200, "master": "כן"},
    ])
    fields = RequestFields(total_amount="100", programs=[ProgramUses(code="230120", uses=[
        Use(text="הפעלה שוטפת של המיזם לביטחון תזונתי"),
        Use(text="הרחבת מבחן התמיכה בארגונים", coalition=True)])])
    extraction = Extraction(source="https://example.org/x.pdf", table=table, matched_codes={"230721"},
                            relevant=True, fields=fields)

    output = SummaryPdfRenderer().render(extraction, tmp_path / "s.pdf", {"230721": "חוץ ביתי"})

    with pymupdf.open(output) as document:
        text = "".join(page.get_text() for page in document)
    for words in ("הפעלה שוטפת", "ביטחון תזונתי", "קואליציוני", "העברה פנימית"):
        assert rtl(words) in text or words in text, words
