"""Focused tests for the summary PDF's real output and pure layout helpers."""
import json
from pathlib import Path

import pymupdf

from bot.adapters.summary_pdf.hebrew_text import rtl, wrap_rtl_html
from bot.adapters.summary_pdf.renderer import SummaryPdfRenderer, budget_table_rows
from bot.adapters.summary_pdf.theme import FONT
from bot.domain.extraction import Extraction
from bot.domain.money_flow import fold, hubs, transfer_summary
from bot.domain.request_fields import ProgramUses, RequestFields, Use
from bot.domain.table import Table

GOLDEN = Path(__file__).parent / "fixtures" / "golden"


def _table(records: list[dict]) -> Table:
    """A budget table from fixture records, without their stored master column."""
    return Table.from_records([c for c in records[0] if c != "master"], records)


def test_render_real_summary_pdf():
    golden = json.loads((GOLDEN / "21656.json").read_text(encoding="utf-8"))
    extras = json.loads((GOLDEN / "21656_extras.json").read_text(encoding="utf-8"))
    history = [(item["title"], Table(tuple(item["columns"]), tuple(map(tuple, item["data"]))))
               for item in extras["history"]]
    extraction = Extraction(
        source=golden["source"],
        table=_table(golden["table"]),
        fields=RequestFields(**golden["text"]),
        letterhead=extras["letterhead"],
        budget_history=history,
    )
    names = dict(zip(extraction.table.column("number"), extraction.table.column("name")))
    programs = {code: names[code].strip() for code in golden["master_matched"]}

    pdf = SummaryPdfRenderer().render(extraction, programs)

    assert pdf.startswith(b"%PDF")
    with pymupdf.open(stream=pdf) as document:
        links = [link.get("uri") for page in document for link in page.get_links()]
        assert document.page_count >= 1
    assert golden["source"] in links


def test_budget_table_rows_has_header_two_rows_per_item_and_spans():
    table = _table([
        {"number": "123456", "name": "תוכנית א", "הוצאה from": 100, "הוצאה to": 150,
         "הרשאה להתחייב from": 20, "הרשאה להתחייב to": 20},
        {"number": "654321", "name": "תוכנית ב", "הוצאה from": 80, "הוצאה to": 60,
         "הרשאה להתחייב from": 10, "הרשאה להתחייב to": 12},
    ])

    rows, spans = budget_table_rows(table, {"123456"})

    assert rows[0] == [rtl(value) for value in
                       ["מספר פרט", "שם הפרט", "", "הוצאה", "הרשאה להתחייב", "שינוי", "master"]]
    assert len(rows) == 1 + 2 * len(table.rows)
    assert rows[1][0] == "123456" and rows[2][0] == ""
    assert rows[1][-1] == rtl("כן") and rows[3][-1] == rtl("לא")
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
    table = _table([
        {"number": "470102", "name": "רזרבה", "הוצאה from": -90, "הוצאה to": 0},
        {"number": "121101", "name": "גמלאות", "הוצאה from": 500, "הוצאה to": 410},
        {"number": "470102", "name": "רזרבה", "הוצאה from": 90, "הוצאה to": 0},
        {"number": "231039", "name": "שירותים", "הוצאה from": 100, "הוצאה to": 190},
    ])

    sources, destinations, metric = transfer_summary(table)

    assert metric == "הוצאה"
    assert sources == [("121101", "גמלאות", 90)]
    assert destinations == [("231039", "שירותים", 90)]


def test_hubs_split_sources_into_reserve_and_internal_transfer():
    table = _table([{"number": "470102", "name": "תוכנית מעבר - רזרבה כללית"}])
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


def test_why_table_shows_each_use_and_tags_coalition_money():
    table = _table([
        {"number": "230120", "name": "שירותי משרד מרכזיים", "הוצאה from": 100, "הוצאה to": 200},
        {"number": "230721", "name": "חוץ ביתי", "הוצאה from": 300, "הוצאה to": 200},
    ])
    fields = RequestFields(total_amount="100", programs=[ProgramUses(code="230120", uses=[
        Use(text="הפעלה שוטפת של המיזם לביטחון תזונתי"),
        Use(text="הרחבת מבחן התמיכה בארגונים", coalition=True)])])
    extraction = Extraction(source="https://example.org/x.pdf", table=table, fields=fields)

    pdf = SummaryPdfRenderer().render(extraction, {"230721": "חוץ ביתי"})

    assert pdf.startswith(b"%PDF")
    with pymupdf.open(stream=pdf) as document:
        text = "".join(page.get_text() for page in document)
    for words in ("הפעלה שוטפת", "ביטחון תזונתי", "קואליציוני", "העברה פנימית"):
        assert rtl(words) in text or words in text, words
