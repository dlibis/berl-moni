"""Summary PDF renderer: SummaryPdfRenderer().render(extraction, path, programs) lays out one relevant
letter's summary as an A4 PDF. It only draws what the Extraction holds; it never reads the letter.

The page, top to bottom (one method each, in this order below):

    letterhead       the letter's heading lines (+ "scanned, verify against the original")
    programs         the master programs that made the letter relevant
    request fields   '<label>: <value>' for each field; the decision links as a list of URLs
    budget table     two rows per item (מ- / ל-), one column per metric
    budget history   the letter's history appendix, one table per metric
    source link      the URL of the original letter

Hebrew must be reordered before reportlab draws it (see hebrew_text.py).
"""
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from bot.adapters.summary_pdf.hebrew_text import fix_split_words, rtl, wrap_rtl_html
from bot.domain.extraction import CODE_COLUMN, MASTER_COLUMN, NAME_COLUMN, Extraction
from bot.domain.request_fields import RequestFields

# Arimo (SIL OFL, fonts/OFL.txt): Hebrew + Latin, Arial's metrics. Bundled so the PDF renders the
# same on macOS and on the GitHub Actions runner.
FONT = "Hebrew"
FONT_PATH = Path(__file__).parent / "fonts" / "Arimo[wght].ttf"
MARGIN = 1.5 * cm                       # on every side of the page
CONTENT_WIDTH = A4[0] - 2 * MARGIN
HEADER_GREY = colors.HexColor("#d9d9d9")

FIELD_LABELS = RequestFields.field_labels()  # in the order the PDF lists them
DECISION_LINKS_LABEL = RequestFields.model_fields["decision_links"].alias
SCANNED_NOTE = "מכתב סרוק — יש לאמת מול המקור"

# alignment: 0 left, 1 center, 2 right
TITLE = ParagraphStyle("title", fontName=FONT, fontSize=13, leading=18, alignment=1)
FIELD = ParagraphStyle("field", fontName=FONT, fontSize=11, leading=18, alignment=2)
LINK = ParagraphStyle("link", fontName=FONT, fontSize=9, leading=12, alignment=0)
HISTORY_HEADER = ParagraphStyle("hist_head", fontName=FONT, fontSize=7, alignment=1, leading=9)
SOURCE = ParagraphStyle("source", fontName=FONT, fontSize=7, leading=10, alignment=0, textColor=colors.grey)


class SummaryPdfRenderer:
    def __init__(self):
        pdfmetrics.registerFont(TTFont(FONT, str(FONT_PATH)))

    def render(self, extraction: Extraction, output_path: Path, programs: dict[str, str]) -> Path:
        """Write the summary PDF; `programs` is {code: master name} for the programs that made the
        letter relevant. Returns `output_path`; raises on failure."""
        e = extraction
        story = (self._letterhead(e.letterhead, e.scanned)
                 + self._programs(programs)
                 + self._request_fields(e.fields)
                 + self._budget_table(e.table)
                 + self._budget_history(e.budget_history)
                 + self._source_link(e.source))
        SimpleDocTemplate(str(output_path), pagesize=A4, topMargin=MARGIN, bottomMargin=MARGIN,
                          leftMargin=MARGIN, rightMargin=MARGIN).build(story)
        return Path(output_path)

    # ---- the page, top to bottom -------------------------------------------

    def _letterhead(self, lines: list[str], scanned: bool) -> list:
        lines = list(lines) + ([SCANNED_NOTE] if scanned else [])
        return [_paragraph(line, TITLE) for line in lines] + [Spacer(1, 0.5 * cm)]

    def _programs(self, programs: dict[str, str]) -> list:
        """A titled name | number table. The title is all Hebrew: bidi mangles Latin words and
        parentheses inside a right-to-left line."""
        if not programs:
            return []
        rows = [[rtl("שם התוכנית"), rtl("מספר תוכנית")]] + [[rtl(name), code] for code, name in programs.items()]
        table = Table(rows, colWidths=[13 * cm, 4 * cm], repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_GREY),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),    # the name
            ("ALIGN", (1, 0), (1, -1), "CENTER"),   # the number
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        title = f"נמצאו {len(programs)} תוכניות רלוונטיות במאסטר"
        return [_paragraph(title, TITLE), Spacer(1, 0.2 * cm), table, Spacer(1, 0.6 * cm)]

    def _request_fields(self, fields: RequestFields) -> list:
        values = fields.model_dump(by_alias=True)
        flow = []
        for label in FIELD_LABELS:
            value = fix_split_words(str(values.get(label, "")))
            if not value.strip():
                continue
            if label == DECISION_LINKS_LABEL:
                flow += self._decision_links(label, value)
            else:
                flow.append(self._field(label, value))
        return flow + [Spacer(1, 0.6 * cm)]

    def _field(self, label: str, value: str) -> Paragraph:
        """'<label>: <value>', right-aligned; the label anchors each line so numbers keep their order."""
        return Paragraph(wrap_rtl_html(f"{label}: {value}", CONTENT_WIDTH, FONT, bold_labels=True), FIELD)

    def _decision_links(self, label: str, value: str) -> list:
        """The label, then one URL per row (URLs read left-to-right: no bidi)."""
        urls = [[Paragraph(escape(url), LINK)] for url in value.split("\n") if url.strip()]
        table = Table(urls, colWidths=[16 * cm])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [_paragraph(f"{label}:", FIELD), table]

    def _budget_table(self, table: pd.DataFrame) -> list:
        rows, spans = budget_table_rows(table)
        display = [row[::-1] for row in rows]  # right-to-left: the first column is drawn rightmost
        width = len(rows[0])
        mirrored = [("SPAN", (width - 1 - col, top), (width - 1 - col, bottom)) for col, top, bottom in spans]
        return [_grid_table(display, mirrored)]

    def _budget_history(self, history_tables: list) -> list:
        """One table per metric, under its title. Headers wrap and are reordered; amounts stay as
        they are, so a number's digits and leading minus sign are not reordered."""
        flow = []
        for title, history in history_tables:
            if history is None or history.empty:
                continue
            columns = list(history.columns)[::-1]  # right-to-left: the first column is drawn rightmost
            rows = [[_header_cell(column) for column in columns]]
            rows += [[str(record[column]) for column in columns] for _, record in history.iterrows()]
            flow += [Spacer(1, 0.6 * cm), _paragraph(title, TITLE), Spacer(1, 0.2 * cm), _grid_table(rows)]
        return flow

    def _source_link(self, url: str | None) -> list:
        flow = [Spacer(1, 0.5 * cm)]
        if url:
            href = escape(url, {'"': "&quot;"})
            flow.append(Paragraph(f'source: <a href="{href}" color="#1155cc">{escape(url)}</a>', SOURCE))
        return flow


# ---- the budget table's content (no drawing) ----------------------------------

def budget_table_rows(table: pd.DataFrame) -> tuple[list[list[str]], list[tuple[int, int, int]]]:
    """The budget table as the letter prints it, in logical (left-to-right) column order:
    a header, then two rows per item — מ- with the 'from' amounts, ל- with the 'to' amounts.
    The code, the name, שינוי (the first metric's change) and master span both rows; `spans`
    lists them as (column, top row, bottom row). Amounts are formatted, Hebrew is reordered."""
    metrics = [c.removesuffix(" from") for c in table.columns if str(c).endswith(" from")]
    header = ["מספר פרט", "שם הפרט", ""] + metrics + ["שינוי", "master"]
    last = len(header) - 1
    rows, spans = [[rtl(h) for h in header]], []
    for _, item in table.iterrows():
        top = len(rows)
        rows.append([str(item[CODE_COLUMN]), rtl(item[NAME_COLUMN]), rtl("מ-")]
                    + [_amount(item.get(f"{m} from")) for m in metrics]
                    + [_change(item, metrics), rtl(item.get(MASTER_COLUMN, ""))])
        rows.append(["", "", rtl("ל-")] + [_amount(item.get(f"{m} to")) for m in metrics] + ["", ""])
        spans += [(col, top, top + 1) for col in (0, 1, last - 1, last)]
    return rows, spans


def _change(item, metrics: list[str]) -> str:
    """'to' minus 'from' for the first metric that has both, formatted; '' if none does."""
    for m in metrics:
        before, after = item.get(f"{m} from"), item.get(f"{m} to")
        if pd.notna(before) and pd.notna(after):
            return _amount(float(after) - float(before))
    return ""


def _amount(value) -> str:
    try:
        return f"{float(value):,.0f}" if pd.notna(value) else ""
    except (TypeError, ValueError):
        return ""


# ---- drawing building blocks ---------------------------------------------------

def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    """One line of Hebrew, reordered for display."""
    return Paragraph(escape(rtl(text)), style)


def _header_cell(text) -> Paragraph:
    """A wrapping table-header cell that keeps the text's own line breaks."""
    html = "<br/>".join(escape(rtl(line)) for line in str(text).split("\n"))
    return Paragraph(html or " ", HISTORY_HEADER)


def _grid_table(rows: list, spans: list = ()) -> Table:
    """The small, grey-headed, centred grid both budget tables use."""
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_GREY),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ] + list(spans)))
    return table
