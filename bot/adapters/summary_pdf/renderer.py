"""Summary PDF renderer: SummaryPdfRenderer().render(extraction, programs) lays out one relevant
letter's summary as an A4 PDF and returns its bytes. It only draws what the Extraction holds; it never
reads the letter.

Built to be read at a glance: the bottom line first, a picture of the money, the reasons in short
bullets, and every raw figure in an appendix. The pages, top to bottom (one method each):

    title            'סיכום פנייה תקציבית', the letterhead in one grey line (+ "scanned, verify")
    summary box      total, internal transfer, coalition, master count, numbers, date, link
    flow chart       sources -> hubs -> destinations (flow_chart.py)
    why table        per destination, what its money is for; small ones in a sub-table with amounts
    appendix         the budget table as printed, the budget history, decision links, staffing

Hebrew must be reordered before reportlab draws it (see hebrew_text.py).
"""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from bot.adapters.summary_pdf.flow_chart import flow_chart
from bot.adapters.summary_pdf.hebrew_text import fix_split_words, rtl, wrap_rtl_html
from bot.adapters.summary_pdf.theme import (COALITION_ORANGE, FONT, FONT_PATH, HEAD_TINT, INK,
                                            MASTER_BLUE, MUTED, RULE, UNIT)
from bot.domain import report
from bot.domain.extraction import Extraction
from bot.domain.money_flow import Item, fold, hubs, transfer_summary
from bot.domain.report import amount as _amount, summary_rows
from bot.domain.request_fields import RequestFields
from bot.domain.table import Table as DataTable

MARGIN = 1.5 * cm                       # on every side of the page
CONTENT_WIDTH = A4[0] - 2 * MARGIN
HEADER_GREY = colors.HexColor("#d9d9d9")
SCANNED_NOTE = "מכתב סרוק — יש לאמת מול המקור"
COALITION_TAG = "קואליציוני"

# alignment: 0 left, 1 center, 2 right
H1 = ParagraphStyle("h1", fontName=FONT, fontSize=16, leading=22, alignment=2)
H2 = ParagraphStyle("h2", fontName=FONT, fontSize=12, leading=18, alignment=2, spaceBefore=10)
BODY = ParagraphStyle("body", fontName=FONT, fontSize=10, leading=14, alignment=2)
SMALL = ParagraphStyle("small", fontName=FONT, fontSize=8, leading=11, alignment=2, textColor=MUTED)
LINK = ParagraphStyle("link", fontName=FONT, fontSize=7, leading=10, alignment=0)
TITLE = ParagraphStyle("title", fontName=FONT, fontSize=13, leading=18, alignment=1)
HISTORY_HEADER = ParagraphStyle("hist_head", fontName=FONT, fontSize=7, alignment=1, leading=9)
TABLE_SIZE = 7.5                        # the why table is dense; small type keeps rows on one line
TABLE_TEXT = ParagraphStyle("tt", fontName=FONT, fontSize=TABLE_SIZE, leading=10, alignment=2)
TABLE_HEAD = ParagraphStyle("th", parent=TABLE_TEXT, textColor=MUTED)
TABLE_NUM = ParagraphStyle("tn", parent=TABLE_TEXT, alignment=1)
TABLE_CODE = ParagraphStyle("tc", parent=SMALL, fontSize=6.5, leading=8)


class SummaryPdfRenderer:
    def __init__(self):
        pdfmetrics.registerFont(TTFont(FONT, str(FONT_PATH)))

    def render(self, extraction: Extraction, programs: dict[str, str]) -> bytes:
        """The summary PDF; `programs` is {code: master name} for the programs that make the
        letter relevant. Raises on failure."""
        e = extraction
        master = set(programs)
        sources, destinations, _ = transfer_summary(e.table)
        groups = hubs(sources, destinations, e.table)
        story = (self._title(e.letterhead, e.scanned)
                 + self._summary_box(e.fields, e.source, groups, len(master), e.table)
                 + self._flow_chart(groups, destinations, master)
                 + self._why_table(e.fields, sources, destinations, master)
                 + self._appendix(e, master))
        pdf = BytesIO()
        SimpleDocTemplate(pdf, pagesize=A4, topMargin=MARGIN, bottomMargin=MARGIN,
                          leftMargin=MARGIN, rightMargin=MARGIN).build(story)
        return pdf.getvalue()

    # ---- page 1: the bottom line and the picture ------------------------------

    def _title(self, letterhead: list[str], scanned: bool) -> list:
        flow = [_paragraph("סיכום פנייה תקציבית", H1)]
        if letterhead:
            flow.append(_paragraph(" · ".join(letterhead), SMALL))
        if scanned:
            flow.append(_paragraph(SCANNED_NOTE, ParagraphStyle("scan", parent=SMALL, textColor=colors.red)))
        return flow + [Spacer(1, 0.3 * cm)]

    def _summary_box(self, fields: RequestFields, source: str | None, groups, master_count: int,
                     table: DataTable) -> list:
        """Label | value rows (report.summary_rows): what a reader needs before anything else."""
        data = [[Paragraph(wrap_rtl_html(value, CONTENT_WIDTH - 4.5 * cm, FONT, size=11), BODY),
                 _paragraph(label, BODY)] for label, value in summary_rows(fields, groups, master_count, table)]
        if source:
            href = escape(source, {'"': "&quot;"})
            data.append([Paragraph(f'<a href="{href}" color="#1155cc">{escape(source)}</a>', LINK),
                         _paragraph("המכתב המקורי", BODY)])
        box = Table(data, colWidths=[CONTENT_WIDTH - 4 * cm, 4 * cm])
        box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.2, MASTER_BLUE),
            ("BACKGROUND", (1, 0), (1, -1), HEAD_TINT),
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, RULE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return [box]

    def _flow_chart(self, groups, destinations: list[Item], master: set[str]) -> list:
        if not groups or not destinations:
            return []
        shown, folded = fold(destinations)
        return [Spacer(1, 0.5 * cm), flow_chart(groups, shown, folded, master, CONTENT_WIDTH),
                _paragraph("שם בכחול = תוכנית מהמאסטר", SMALL)]

    # ---- page 2: why the money moves -------------------------------------------

    def _why_table(self, fields: RequestFields, sources: list[Item], destinations: list[Item],
                   master: set[str]) -> list:
        """One row per destination the chart shows, in its order; then the ones it folds into
        'עוד N', as a full-width sub-table — the only rows with an amount, since the chart shows
        the others'."""
        if not destinations:
            return []
        program_w = 6 * cm
        why_w = CONTENT_WIDTH - program_w
        shown, folded = fold(destinations)
        rows = [[_paragraph("למה", TABLE_HEAD), _paragraph("תוכנית", TABLE_HEAD)]]
        rows += [[_uses_cell(fields, code, why_w), _program_cell(code, name, program_w, master)]
                 for code, name, _ in shown]
        if folded:
            sub_program_w, sub_amount_w = program_w - 12, 1.7 * cm   # lined up with the main columns
            sub_why_w = CONTENT_WIDTH - 12 - sub_program_w - sub_amount_w
            sub_rows = [[_paragraph(UNIT, TABLE_HEAD), _paragraph("למה", TABLE_HEAD), _paragraph("תוכנית", TABLE_HEAD)]]
            sub_rows += [[Paragraph(f"+{_amount(amount)}", TABLE_NUM), _uses_cell(fields, code, sub_why_w),
                          _program_cell(code, name, sub_program_w, master)] for code, name, amount in folded]
            sub = Table(sub_rows, colWidths=[sub_amount_w, sub_why_w, sub_program_w])
            sub.setStyle(_rows_style())
            total = sum(a for _, _, a in folded)
            label = f"{escape(rtl(UNIT))} +{_amount(total)} · {escape(rtl(f'עוד {len(folded)} תוכניות'))}"
            rows += [[Paragraph(f"<b>{label}</b>", TABLE_TEXT), ""], [sub, ""]]   # a span shows column 0
        table = Table(rows, colWidths=[why_w, program_w], repeatRows=1)
        table.setStyle(_rows_style())
        if folded:
            n = len(rows)
            table.setStyle(TableStyle([("SPAN", (0, n - 2), (-1, n - 2)), ("SPAN", (0, n - 1), (-1, n - 1)),
                                       ("LINEBELOW", (0, n - 2), (-1, n - 2), 0, colors.white)]))
        flow = [CondPageBreak(8 * cm),            # the title goes to the next page with its table
                _paragraph("למה עובר הכסף", H2), _paragraph("לפי סדר הגודל בתרשים", SMALL),
                Spacer(1, 0.2 * cm), table]
        if sources:
            givers = ", ".join(code for code, _, _ in sources)
            flow += [Spacer(1, 0.2 * cm),
                     _paragraph(f"התוכניות שמהן נלקח הכסף ({givers}): המכתב אינו מפרט סיבה", SMALL)]
        return flow

    # ---- the appendix: every figure, for checking -----------------------------

    def _appendix(self, e: Extraction, master: set[str]) -> list:
        flow = [PageBreak(), _paragraph("נספח: הנתונים המלאים", H1), Spacer(1, 0.3 * cm)]
        flow += self._budget_table(e.table, master) + self._budget_history(e.budget_history)
        links = [url for url in e.fields.decision_links.split("\n") if url.strip()]
        if links:
            flow += [Spacer(1, 0.5 * cm), _paragraph("קישורים להחלטות ממשלה", H2)]
            flow += [Paragraph(escape(url), LINK) for url in links]
        if e.fields.staffing_changes:
            flow += [Spacer(1, 0.3 * cm), _paragraph(f"שינויים בכוח אדם: {e.fields.staffing_changes}", BODY)]
        return flow

    def _budget_table(self, table: DataTable, master: set[str]) -> list:
        rows, spans = budget_table_rows(table, master)
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
            # right-to-left: the first column is drawn rightmost
            rows = [[_header_cell(column) for column in history.columns[::-1]]]
            rows += [[str(cell) for cell in row[::-1]] for row in history.rows]
            flow += [Spacer(1, 0.6 * cm), _paragraph(title, TITLE), Spacer(1, 0.2 * cm), _grid_table(rows)]
        return flow


# ---- the why table's cells --------------------------------------------------------

def _program_cell(code: str, name: str, width: float, master: set[str]) -> list:
    """The name (blue for a master program), the code small under it."""
    style = ParagraphStyle("pn", parent=TABLE_TEXT, textColor=MASTER_BLUE if code in master else INK)
    return [Paragraph(wrap_rtl_html(name, width - 12, FONT, size=TABLE_SIZE), style),
            _paragraph(f"תוכנית {code}", TABLE_CODE)]


def _uses_cell(fields: RequestFields, code: str, width: float) -> list:
    """One bullet per use of the money; a coalition-funded use ends in an orange tag."""
    tag = escape(rtl(COALITION_TAG))
    cell = []
    for use in fields.uses(code):
        text = fix_split_words(f"• {use.text}") + (f" · {COALITION_TAG}" if use.coalition else "")
        html = wrap_rtl_html(text, width - 12, FONT, size=TABLE_SIZE)
        cell.append(Paragraph(html.replace(tag, f'<font color="{COALITION_ORANGE}"><b>{tag}</b></font>'),
                              TABLE_TEXT))
    return cell


def _rows_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_TINT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


# ---- the budget table's content (no drawing) ----------------------------------

def budget_table_rows(table: DataTable, master: set[str]) -> tuple[list[list[str]], list[tuple[int, int, int]]]:
    """report.budget_table_rows with its text reordered for display; amounts are left as they are,
    so a number's digits and leading minus sign are not reordered."""
    rows, spans = report.budget_table_rows(table, master)
    last = len(rows[0]) - 1
    text_columns = (1, 2, last)                     # name, מ-/ל-, כן/לא
    rows = [[rtl(h) for h in rows[0]]] + [[rtl(c) if i in text_columns else c for i, c in enumerate(row)]
                                          for row in rows[1:]]
    return rows, spans


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
