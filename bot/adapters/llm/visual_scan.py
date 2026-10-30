"""Read an entire scanned PDF in one call to the configured multimodal model."""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from bot.domain.errors import ExtractionError
from bot.domain.table import Table


class Amounts(BaseModel):
    before: float | None
    change: float | None
    after: float | None
    blank_before: bool = False
    blank_after: bool = False


class BudgetRow(BaseModel):
    code: str
    name: str
    expenditure: Amounts


class History(BaseModel):
    label: str
    columns: list[str]
    rows: list[list[str]]


class ScanPage(BaseModel):
    page_number: int = Field(ge=1, description="Physical PDF page number, starting at 1")
    text: str = Field(description="Transcription of the page's narrative and headings, in reading order")
    budget_table_present: bool
    rows: list[BudgetRow]
    history_present: bool
    history: list[History]


class ScanDocument(BaseModel):
    pages: list[ScanPage]


PROMPT = """Read every page of this scanned Hebrew PDF visually, in physical page order.
Return one pages entry per PDF page, including blank pages, with its page_number.
For each page, transcribe narrative and headings in text in
reading order. Identify budget tables and list every 5 or 6 digit program-level row in source
order, including repeated codes. Record the printed code, name and הוצאה before, change and after.
Preserve leading zeros and negatives. For an unreadable value use null. For a visibly blank half
of a before/after pair set the corresponding blank flag true and its value null; never guess.
For other blank values use null. Do not include section or subtotal rows. If a budget-history table
is present, transcribe all its column headers and rows as history, preserving source order.
Report whether budget and history tables are present even if they cannot be read."""


def _validate_page(page: ScanPage) -> None:
    if not page.budget_table_present and page.rows:
        raise ExtractionError("Visual model returned rows without a budget table")
    if page.budget_table_present and not page.rows:
        raise ExtractionError("Visual model could not read a detected budget table")
    if page.history_present != bool(page.history):
        raise ExtractionError("Visual model could not read a detected history table")
    for history in page.history:
        if not history.columns or not history.rows or any(len(row) != len(history.columns) for row in history.rows):
            raise ExtractionError("Visual model returned an incomplete history table")
    for row in page.rows:
        if not re.fullmatch(r"\d{5,6}", row.code) or not row.name.strip():
            raise ExtractionError(f"Invalid budget row: {row.code!r}")
        values = row.expenditure
        if values.blank_before and values.before is None:
            values.before = 0
        elif values.blank_before:
            raise ExtractionError(f"Conflicting blank before value: {row.code}")
        if values.blank_after and values.after is None:
            values.after = 0
        elif values.blank_after:
            raise ExtractionError(f"Conflicting blank after value: {row.code}")
        if values.change is None and values.before is not None and values.before == values.after:
            values.change = 0
        if None in (values.before, values.change, values.after):
            raise ExtractionError(f"Unreadable or blank expenditure value: {row.code}")
        if abs(values.before + values.change - values.after) >= 0.01:
            raise ExtractionError(f"Expenditure arithmetic mismatch: {row.code}")


@dataclass
class VisualDocument:
    text: str
    table: Table
    history: list[tuple[str, Table]]


def read_document(path: str, *, model: str, provider: str, api_key: str, client=None) -> VisualDocument:
    import pymupdf
    from langchain_core.messages import HumanMessage

    if not api_key:
        raise ExtractionError("A model API key is required for visual scan extraction")
    with pymupdf.open(path) as pdf:
        page_count = len(pdf)
    if not page_count:
        raise ExtractionError("Scanned document has no pages")
    if client is None:
        from langchain.chat_models import init_chat_model
        client = init_chat_model(model, model_provider=provider, api_key=api_key, max_retries=0)
    encoded = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    result = client.with_structured_output(ScanDocument).invoke([HumanMessage(content=[
        {"type": "text", "text": f"{PROMPT}\nThe PDF has {page_count} pages; return all {page_count}."},
        {"type": "file", "source_type": "base64", "mime_type": "application/pdf",
         "data": encoded, "filename": "letter.pdf"},
    ])])
    try:
        document = ScanDocument.model_validate(result)
    except (ValueError, TypeError) as error:
        raise ExtractionError("Visual model returned an invalid scan document") from error
    if [page.page_number for page in document.pages] != list(range(1, page_count + 1)):
        raise ExtractionError("Visual model omitted, duplicated, or reordered PDF pages")
    pages, rows, history = [], [], []
    for page in document.pages:
        try:
            _validate_page(page)
        except ExtractionError as error:
            raise ExtractionError(f"Page {page.page_number}: {error}") from error
        pages.append(page.text)
        rows.extend((r.code.zfill(6), r.name.strip(), r.expenditure.before, r.expenditure.after)
                    for r in page.rows)
        history.extend((h.label or "היסטוריה תקציבית של הפנייה", Table(tuple(h.columns),
                       tuple(tuple(row) for row in h.rows))) for h in page.history)
    if not rows:
        raise ExtractionError("No budget program rows found in scanned document")
    return VisualDocument("\n".join(pages), Table(("number", "name", "הוצאה from", "הוצאה to"),
                                                tuple(rows)), history)
