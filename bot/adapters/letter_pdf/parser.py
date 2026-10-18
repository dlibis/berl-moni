"""Letter parser: BudgetLetter reads a budget-transfer letter's parts out of its PDF — the combined
budget table, the budget history, the letterhead and the government-decision links.

It takes a PdfDocument (clean text + tables) and exposes the raw materials the Extractor
(bot/domain/extraction.py) builds on. It never touches pdfplumber or raw PDFs — that is
PdfDocument's job. Request-field extraction is NOT here; it lives in bot/domain/extraction.py.

    letter = BudgetLetter(PdfDocument(path), source)   # see letter_pdf.loader.open_letter
    letter.extract_combined_table()                    # -> Table (DataFrames inside, converted at the edge)
"""
from __future__ import annotations

import re

from bot.adapters.letter_pdf.reader import PdfDocument
from bot.adapters.letter_pdf.tables import to_table
from bot.domain.extraction import CODE_COLUMN, NAME_COLUMN


class BudgetLetter:
    """A budget-transfer request letter, exposed as typed answers."""

    # Combined-table column names (see extract_combined_table, added in Task 5).
    CODE_COLUMN = CODE_COLUMN  # the table contract lives in the domain (bot/domain/extraction.py)
    NAME_COLUMN = NAME_COLUMN
    # The budget item name column (שם הפרט), identified by its char-reversed header.
    NAME_SOURCE_HEADER = "שם הפרט"

    # The appendix table (נספח לדברי ההסבר) listing each program's multi-year
    # net-expenditure history; its page is found by this marker in the readable text.
    BUDGET_HISTORY_GENERIC = "היסטוריה תקציבית של הפנייה"  # when the metric is unknown
    BUDGET_HISTORY_MARKER = "היסטוריה תקציבית"

    def __init__(self, doc: PdfDocument, source: str):
        self.doc = doc
        self.source = source  # the URL (or path) the letter came from, printed on the summary

    # ---- combined budget table + arithmetic check ----

    def extract_combined_table(self):
        """The letter's data tables combined into one clean table.

        Columns: number, name, then '<metric> from' / '<metric> to' for each METRIC (see
        _combine_tables). Only leaf rows (5-6 digit codes) kept.
        A scan has no readable cell structure, so its table is the codes only (number,
        name), taken from the 6-digit cells of the OCR markdown's table rows.
        """
        if self.doc.scanned:
            return to_table(self._scan_table())
        return to_table(self._combine_tables(self.doc.tables))

    def _scan_table(self):
        """Codes from the 6-digit cells of the OCR markdown's table rows — never from
        free text, where any 6-digit number (phone, amount) would give false matches."""
        import pandas as pd

        codes: list[str] = []
        for line in self.doc.markdown.splitlines():
            if not line.startswith("|"):
                continue
            for cell in line.strip("|").split("|"):
                codes += [c for c in (p.strip() for p in cell.split("<br>"))
                          if re.fullmatch(r"\d{6}", c)]
        return pd.DataFrame({self.CODE_COLUMN: list(dict.fromkeys(codes)),
                             self.NAME_COLUMN: ""})

    def arithmetic_failures(self) -> list[str]:
        """Codes of rows whose change amounts disagree with to - from.

        Each table is checked on its own: the change values sit in the columns before its first
        metric column, and the pages of one letter spell those headers differently, so a merged
        table would misplace them. A row's non-zero changes must equal its non-zero (to - from)
        values; a row with an unreadable change cell can't be verified and is not reported.
        """
        if self.doc.scanned:
            return []  # ponytail: OCR tables have no cell structure to check
        tables = [df for df in self.doc.tables if any(str(c).endswith("delta") for c in df.columns)]
        return [code for table in tables for code in self._unbalanced_rows(table)]

    def _unbalanced_rows(self, table) -> list[str]:
        import pandas as pd

        code_column = self._find_code_column(table)
        rows = table[table[code_column].astype(str).str.strip().str.fullmatch(r"\d{5,6}")]
        prefixes = [prefix for _, prefix in self.METRICS]
        columns = list(table.columns)
        first_metric = next(
            (i for i, c in enumerate(columns) if any(str(c).startswith(p) for p in prefixes)), 0)
        change_columns = columns[:first_metric]

        bad = []
        for _, row in rows.iterrows():
            deltas = []
            for prefix in prefixes:
                lo, hi = row.get(f"{prefix} from"), row.get(f"{prefix} to")
                if pd.notna(lo) and pd.notna(hi) and abs(hi - lo) > 1e-6:
                    deltas.append(hi - lo)
            changes, readable = [], True
            for column in change_columns:
                cell = str(row[column]).strip()
                if cell in ("", "nan"):
                    continue
                value = PdfDocument._parse_trailing_minus(cell)
                if value is None:
                    readable = False
                elif abs(value) > 1e-6:
                    changes.append(value)
            if readable and not self._same_amounts(deltas, changes):
                bad.append(str(row[code_column]).strip().zfill(6))
        return bad

    @staticmethod
    def _same_amounts(a: list[float], b: list[float]) -> bool:
        """True if the two lists hold the same amounts, ignoring order."""
        return len(a) == len(b) and all(abs(x - y) < 0.01 for x, y in zip(sorted(a), sorted(b)))

    METRICS = [
        ("הוצאה", "הוצאה"),
        ("הוצאה מותנית", "הוצאה\nמותנית"),
        ("הרשאה להתחייב", "הרשאה\nלהתחייב"),
        ("שיא כח אדם", 'שכ"א'),
        ('עב"צ', 'עב"צ'),
    ]

    def _combine_tables(self, tables):
        """One row per 6-digit budget line (per occurrence, faithful to the PDF), with
        every metric's from/to value. Columns: number, name, then '<metric> from' /
        '<metric> to' for each METRIC. The report renders each row as מ-/ל- rows + שינוי.
        """
        import pandas as pd

        data_tables = [
            df for df in tables if any(str(c).endswith("delta") for c in df.columns)
        ]
        if not data_tables:
            raise ValueError("No data tables (with a 'delta' column) found to combine.")

        combined = pd.concat(data_tables, ignore_index=True)
        code_column = self._find_code_column(combined)
        codes = combined[code_column].astype(str).str.strip()
        # Keep only program-level rows (5-6 digit codes); drop 2-digit section and
        # 4-digit domain aggregates. Left-pad 5-digit codes to 6 digits.
        combined = combined[codes.str.fullmatch(r"\d{5,6}")].reset_index(drop=True)

        out = pd.DataFrame()
        out[self.CODE_COLUMN] = combined[code_column].astype(str).str.strip().str.zfill(6)
        name_column = self._find_name_column(combined)
        out[self.NAME_COLUMN] = (
            combined[name_column].map(self._clean_name).values
            if name_column is not None else ""
        )

        n = len(combined)
        for display, prefix in self.METRICS:
            raw_from = combined.get(f"{prefix} from")
            raw_to = combined.get(f"{prefix} to")
            out[f"{display} from"] = (
                pd.to_numeric(raw_from, errors="coerce").values
                if raw_from is not None else [pd.NA] * n)
            out[f"{display} to"] = (
                pd.to_numeric(raw_to, errors="coerce").values
                if raw_to is not None else [pd.NA] * n)
        return out.reset_index(drop=True)

    @classmethod
    def _find_name_column(cls, df):
        """Return the שם הפרט column, matched by its (now correct-order) header.

        PdfDocument returns cells in correct reading order, so the header is compared
        directly — whitespace-insensitively, which also absorbs any split final letter.
        """
        target = "".join(cls.NAME_SOURCE_HEADER.split())
        for column in df.columns:
            if "".join(str(column).split()) == target:
                return column
        return None

    @staticmethod
    def _clean_name(value) -> str:
        """Join a cell's lines into one string, dropping decorative separator lines.

        PdfDocument already returns cells in correct reading order (see
        PdfDocument._clean_cell), so no reversing happens here — this only tidies
        whitespace and drops lines with no letters/digits (===, ---, .-.-).
        """
        lines = (line.strip() for line in str(value).split("\n"))
        meaningful = [line for line in lines if re.search(r"\w", line)]
        return " ".join(meaningful).strip()

    @staticmethod
    def _find_code_column(df) -> str:
        """Return the column that holds budget item codes (the one with the most all-digit values).

        The column name comes from the PDF character-reversed, so it's identified by
        content rather than by its (unreliable) header text.
        """
        best_column = None
        best_score = -1
        for column in df.columns:
            values = df[column].astype(str).str.strip()
            score = values.str.fullmatch(r"\d{1,6}").sum()
            if score > best_score:
                best_score = score
                best_column = column
        if best_column is None or best_score == 0:
            raise ValueError("Could not find a budget item code column.")
        return best_column

    # ---- decision links, budget history, letterhead ----

    def decision_links(self) -> list[str]:
        """Return the government-decision URLs (קישורים להחלטות ממשלה), one per decision.

        URLs are read from the raw page text (not the bidi-reversed text) so they read
        correctly, then de-duplicated by decision number (dec####), keeping the first
        URL seen for each — that yields the links printed in the request letter.
        """
        raw = self.doc.raw_text
        seen: dict[str, str] = {}
        for url in re.findall(r"https?://\S+", raw):
            url = url.rstrip('".,)”–- ')
            match = re.search(r"dec[_-]?(\d+)", url)
            if match and match.group(1) not in seen:
                seen[match.group(1)] = url
        return list(seen.values())

    def extract_budget_history(self):
        """Return the appendix's budget-history tables as (title, Table) pairs.

        The 'היסטוריה תקציבית' appendix holds one table per budget metric — e.g.
        הוצאה נטו / הוצאה מותנית בהכנסה / הרשאה להתחייב — each introduced by its own
        'היסטוריה תקציבית של הפנייה – <metric>' title line. The pairs come back in
        document order (the k-th title goes with the k-th table on the appendix pages);
        an empty list when the letter has no such appendix.
        """
        titles: list[str] = []
        raw: list = []
        for page in self.doc.pages:
            if self.BUDGET_HISTORY_MARKER not in page.text:
                continue
            titles += [t for t in map(self._history_title, page.text.splitlines()) if t]
            raw += [t for t in page.tables if t]

        # One metric = one table, even when it spills across pages: a continuation page
        # either repeats the same header or (when pdfplumber drops it) starts on data.
        # DIFFERENT metric tables have different headers, so they stay separate — this
        # combines a table's own pages without ever fusing distinct metrics.
        groups: list[list] = []
        for table in raw:
            header = self._is_header_row(table[0])
            if groups and (not header or self._same_header(table[0], groups[-1][0])):
                groups[-1] += table[1:] if header else table   # drop the repeated header
            else:
                groups.append(list(table))

        out = []
        for i, table in enumerate(groups):
            if len(titles) == len(groups):
                title = titles[i]                    # one metric title per table
            elif len(groups) == 1 and titles:
                title = titles[0]                    # single table with its own title
            else:
                title = self.BUDGET_HISTORY_GENERIC  # metric unknown — don't assert one
            out.append((title, to_table(self._clean_history_table(table))))
        return out

    def _same_header(self, a, b) -> bool:
        """True if two rows are the same header, ignoring the PDF's stray whitespace."""
        squash = lambda row: [self._clean_name(c).replace(" ", "") for c in row]
        return squash(a) == squash(b)

    @staticmethod
    def _is_header_row(row) -> bool:
        """True if the row is a real header (has Hebrew label text), not a data row.

        Header cells read like 'קוד תוכנית' / 'מקורי 2023'; data rows are codes and
        amounts only. Lets a page whose title row pdfplumber missed render without a
        data row masquerading as the header.
        """
        return any(re.search(r"[א-ת]", str(cell or "")) for cell in row)

    @classmethod
    def _history_title(cls, line: str) -> str | None:
        """A budget-history title line ('...היסטוריה תקציבית... – <metric>') or None.

        Only lines that name a metric after a dash qualify; the bare section header
        ('היסטוריה תקציבית של הפנייה') has no metric and is skipped. Matching ignores
        whitespace so the PDF's stray in-word spacing (e.g. 'תקציבי ת') still matches.
        """
        collapsed = " ".join(line.split())
        if cls.BUDGET_HISTORY_MARKER.replace(" ", "") not in collapsed.replace(" ", ""):
            return None
        parts = re.split(r"[–—-]", collapsed, maxsplit=1)
        if len(parts) == 2 and parts[1].strip():
            return collapsed
        return None

    def _clean_history_table(self, table):
        """Turn a raw budget-history table (header + data rows) into a clean DataFrame.

        Only the Hebrew header cells come out character-reversed and need flipping
        back; pdfplumber lays the numeric/code cells out left-to-right already
        (045101, -2,550, 786,257), so the data is kept verbatim.
        """
        import pandas as pd

        if self._is_header_row(table[0]):
            header, *data = table
            columns = [self._clean_name(cell) for cell in header]
        else:
            # A continuation page whose title row pdfplumber dropped: no header to show,
            # so render every row as data under blank headings (never numbers-as-title).
            columns = [""] * len(table[0])
            data = table

        # pdfplumber can return ragged rows (a row with more/fewer cells than the header),
        # so pad columns/rows to a common width — otherwise the DataFrame build throws.
        ncol = max([len(columns)] + [len(r) for r in data])
        columns = (columns + [""] * ncol)[:ncol]

        # Drop duplicate rows: a table split across pages repeats its seam rows on both
        # pages, so the same program code can appear twice. Each code is unique here, so
        # any exact repeat is that artifact — keep the first, preserve order.
        rows, seen = [], set()
        for record in data:
            cleaned = [(cell or "").strip() for cell in record]
            cleaned = (cleaned + [""] * ncol)[:ncol]
            key = tuple(cleaned)
            if key in seen:
                continue
            seen.add(key)
            rows.append(cleaned)
        return pd.DataFrame(rows, columns=columns)

    def extract_letterhead(self, lines: int = 3) -> list[str]:
        """Return the letter's first few Hebrew header lines, for use as a letterhead.

        These are lines like מדינת ישראל / האוצר - אגף התקציבים / תקציב פיתוח.
        pdfplumber splits a word's final letter off with a space ("התקציבי ם");
        a lone trailing Hebrew letter is re-joined before returning.
        """
        header_lines = []
        if self.doc.scanned:  # OCR'd lines are unreliable; the letterhead is the same on every letter
            return ["מדינת ישראל", PdfDocument.HEADER][:lines]
        for line in self.doc.text.splitlines():
            cleaned = re.sub(r"(\S) ([֐-ת])(?=\s|$)", r"\1\2", line.strip())
            if re.search(r"[֐-ת]", cleaned):
                header_lines.append(cleaned)
            if len(header_lines) == lines:
                break
        return header_lines
