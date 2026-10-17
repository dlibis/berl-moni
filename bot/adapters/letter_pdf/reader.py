"""PDF reader: PdfDocument reads a letter PDF from disk and gives back clean text and tables.

This module owns everything messy about the PDF file itself: opening it, correcting pdfplumber's
right-to-left (bidi) text, reading tables, and OCR for scans. The one thing it knows about budget
letters is how to spot their table pages (the HEADER line); request fields are not its business.

Its public surface is small and stable, so a consumer (see letter_pdf.parser.BudgetLetter)
can rely on it without caring how the PDF was parsed:

    doc = PdfDocument(path)            # a local file (letter_pdf.download.local_copy for a URL)
    doc.text        -> str             # every page, bidi-corrected (lines reversed)
    doc.raw_text    -> str             # every page, exactly as pdfplumber emits it
    doc.pages       -> list[PageData]  # per-page text + its tables (cells cleaned, not yet typed)
    doc.markdown    -> str             # pymupdf4llm text (OCR for a scan), narrative source
    doc.scanned     -> bool            # True when the PDF has no text layer (OCR'd)
    doc.tables      -> list[DataFrame] # header-page tables, split into from/to/delta

Number direction is normalized here too, so consumers get correct digits without
re-ordering anything themselves.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd
import pdfplumber
import pymupdf4llm

from bot.domain.errors import NoTextError


@dataclass
class PageData:
    """One page's readable text and its raw pdfplumber tables (rows of cells)."""

    text: str
    tables: list  # list[list[list[str | None]]] — cells cleaned, not yet parsed into DataFrames


class PdfDocument:
    """A budget-letter PDF exposed as clean text and tables."""

    HEADER = "האוצר - אגף התקציבים"

    # The source PDFs draw some column borders as two near-overlapping vertical
    # lines, which makes pdfplumber split one logical column into a duplicate
    # sliver column. Snapping nearby vertical lines together merges them.
    TABLE_SETTINGS = {"snap_x_tolerance": 10}

    def __init__(self, path: str, *, use_first_row_as_header: bool = True):
        self.path = path  # a local file; letter_pdf.download.local_copy fetches URLs
        self.use_first_row_as_header = use_first_row_as_header
        self._markdown: str | None = None
        self._scanned: bool | None = None

    def _open(self):
        return pdfplumber.open(self.path)

    def _is_header_page(self, page) -> bool:
        """True if the page contains HEADER (i.e. a budget-table page).

        pdfplumber doesn't apply bidi reordering, so Hebrew lines come out
        character-reversed; reverse each line back before searching for HEADER.
        Word breaks can shift across line wraps, so whitespace is stripped
        entirely (not just collapsed) before comparing.
        """
        normalized_header = "".join(self.HEADER.split())
        lines = (line[::-1] for line in (page.extract_text() or "").splitlines())
        page_text = "".join("".join(lines).split())
        return normalized_header in page_text

    # ---- bidi / number direction ----

    @staticmethod
    def _reverse_number(token: str) -> str:
        """Put one number token (inside already line-reversed text) back into raw order.

        `line[::-1]` reverses the whole line to fix the Hebrew, which also reverses every
        number; reversing each number token again restores it to the order pdfplumber
        actually read off the page — the correct value for all of them: date 10/05/2026,
        amount 43,688, negative -2,550, request number 51-202, program codes. One uniform
        rule, no per-field special cases.
        """
        return token[::-1]

    @classmethod
    def _fix_numbers(cls, line: str) -> str:
        """Reverse every number run in a line back to correct order (see _reverse_number)."""
        return re.sub(r"\d[\d.,/ -]*\d|\d",
                      lambda m: cls._reverse_number(m.group(0)), line)

    @classmethod
    def _fix_line(cls, line: str) -> str:
        """Correct one raw pdfplumber line: reverse it (fixes Hebrew) then fix the numbers."""
        return cls._fix_numbers(line[::-1])

    # ---- text ----

    @property
    def scanned(self) -> bool:
        """True when no page has a text layer (the letter is a scan and goes through OCR)."""
        if self._scanned is None:
            with self._open() as pdf:
                self._scanned = not any((page.extract_text() or "").strip() for page in pdf.pages)
        return self._scanned

    @property
    def markdown(self) -> str:
        """The letter's text via pymupdf4llm: its text layer, or Tesseract OCR for a scan.

        OCR (heb+eng, 300 dpi) keeps digits exact but reverses word order per line and puts
        the minus sign after the number (66,970-); table-row minus signs are moved in front.
        Raises NoTextError when OCR finds nothing.
        """
        if self._markdown is None:
            if self.scanned:
                md = pymupdf4llm.to_markdown(
                    self.path, force_ocr=True, ocr_language="heb+eng", ocr_dpi=300)
                if not re.search(r"[\w]", md):
                    raise NoTextError("no text layer and OCR found no text")
                md = "\n".join(
                    re.sub(r"(?<![\w,.-])(\d[\d,]*(?:\.\d+)?)-(?!\w)", r"-\1", line)
                    if line.startswith("|") else line
                    for line in md.splitlines())
            else:
                md = pymupdf4llm.to_markdown(self.path, use_ocr=False)
            self._markdown = md
        return self._markdown

    @property
    def text(self) -> str:
        """Every page's text in correct reading order (Hebrew and numbers both fixed).

        A scan has no text layer, so its text is the OCR markdown.
        """
        if self.scanned:
            return self.markdown
        with self._open() as pdf:
            return "\n".join(
                "\n".join(self._fix_line(line) for line in (page.extract_text() or "").splitlines())
                for page in pdf.pages
            )

    @property
    def raw_text(self) -> str:
        """Every page's text exactly as pdfplumber emits it (no bidi reversal).

        Used for reading left-to-right content such as URLs, which come out correct
        in the raw text but backwards in the bidi-corrected text.
        """
        with self._open() as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)

    @property
    def pages(self) -> list[PageData]:
        """Per-page bidi-corrected text plus that page's raw tables."""
        result: list[PageData] = []
        with self._open() as pdf:
            for page in pdf.pages:
                text = "\n".join(
                    self._fix_line(line) for line in (page.extract_text() or "").splitlines()
                )
                raw_tables = page.extract_tables(self.TABLE_SETTINGS) or []
                clean_tables = [
                    [[self._clean_cell(cell) for cell in row] for row in table]
                    for table in raw_tables
                ]
                result.append(PageData(text=text, tables=clean_tables))
        return result

    # ---- tables ----

    def _header_page_tables(self) -> list[list[list[str | None]]]:
        """Return all raw tables found on every page that contains HEADER."""
        with self._open() as pdf:
            if not pdf.pages:
                raise ValueError("PDF has no pages")

            header_pages = [page for page in pdf.pages if self._is_header_page(page)]
            if not header_pages:
                raise ValueError(f"Header '{self.HEADER}' not found in any page of the PDF")

            tables = []
            for page in header_pages:
                tables.extend(page.extract_tables(self.TABLE_SETTINGS) or [])
        return tables

    @classmethod
    def _clean_cell(cls, cell) -> str:
        """Return a table cell in correct reading order, using the same rule as text.

        Each line is reversed (fixes Hebrew) and its numbers corrected via _fix_numbers,
        exactly like running text — so a year 2026 stays 2026 and codes/amounts (045110,
        337,434) are preserved. Line breaks are kept so stacked from/to cells still split
        correctly downstream.
        """
        if cell is None:
            return ""
        return "\n".join(cls._fix_numbers(line[::-1]).strip() for line in str(cell).split("\n"))

    def table_to_dataframe(self, table: list[list[str | None]]) -> pd.DataFrame:
        """Convert a raw table (list of rows) into a pandas DataFrame with clean cells."""
        if not table:
            return pd.DataFrame()

        cleaned = [[self._clean_cell(cell) for cell in row] for row in table]

        if self.use_first_row_as_header and len(cleaned) > 1:
            columns = cleaned[0]
            data = cleaned[1:]
            return pd.DataFrame(data, columns=columns)

        return pd.DataFrame(cleaned)

    @staticmethod
    def _parse_number(text: str) -> float | None:
        """Parse a numeric string like '1,539,800' or '461.5' into a float, else None."""
        import re

        cleaned = text.strip().replace(",", "")
        if re.fullmatch(r"-?\d+(\.\d+)?", cleaned):
            return float(cleaned)
        return None

    @classmethod
    def _parse_trailing_minus(cls, text: str) -> float | None:
        """Like _parse_number, but also reads a trailing minus ('10,850-') as negative."""
        text = text.strip()
        if text.endswith("-"):
            value = cls._parse_number(text[:-1])
            return -value if value is not None else None
        return cls._parse_number(text)

    def split_stacked_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Split every stacked מ/ל cell ('from\\nto') into <col> from, <col> to and <col> delta (to-from)."""
        columns: dict[str, list] = {}
        for j in range(df.shape[1]):
            series = df.iloc[:, j].astype(str)
            name = str(df.columns[j]).strip() or f"col{j}"

            parsed: list[tuple[float, float] | None] = []
            is_stacked = False
            for value in series:
                parts = value.split("\n")
                if len(parts) == 2:
                    top = self._parse_number(parts[0])
                    bottom = self._parse_number(parts[1])
                    if top is not None and bottom is not None:
                        parsed.append((top, bottom))
                        is_stacked = True
                        continue
                parsed.append(None)

            if is_stacked:
                columns[f"{name} from"] = [p[0] if p else None for p in parsed]
                columns[f"{name} to"] = [p[1] if p else None for p in parsed]
                columns[f"{name} delta"] = [p[1] - p[0] if p else None for p in parsed]
            else:
                columns[name] = series.tolist()

        return pd.DataFrame(columns)

    @property
    def tables(self) -> list[pd.DataFrame]:
        """
        Header-page tables, each split into 
        from/to/delta columns — ready to combine.
        """
        tables = self._header_page_tables()
        if not tables:
            raise ValueError("No tables found on the header pages.")
        return [self.split_stacked_columns(self.table_to_dataframe(t)) for t in tables]
