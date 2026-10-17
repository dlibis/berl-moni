"""Letter extraction: deterministic rules over the letter + one injected LLM call.

`Extractor` owns ALL request-field extraction for a budget-transfer letter. Most fields are
produced by deterministic methods over the FULL letter text (no truncation). One call to
`analyze` (bot.adapters.llm.letter_analyzer.LlmAnalyzer in production, a lambda in tests) over the narrative region
does the two things that vary per letter: judging `coalition_funds` and returning the
request text VERBATIM. No deterministic fallback. `load(source)` returns the letter
(bot.adapters.letter_pdf.loader.open_letter in production): its text, tables and links. The
Extractor reads no environment, no database and no PDF library itself: bot.bootstrap builds it.

    extractor = Extractor(programs, analyze=LlmAnalyzer(...), load=open_letter)
    result = extractor.extract(source)   # source = URL or local PDF path
    result.fields        # RequestFields
    result.table         # budget table + a `master` (כן/לא) column
    result.matched_codes # letter codes that are in the master set
    result.relevant      # True iff a summary should be produced
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Protocol

import pandas as pd

from bot.domain.errors import ExtractionError
from bot.domain.request_fields import RequestFields

# The budget table's columns: code, name, '<metric> from' / '<metric> to' per metric, then master.
CODE_COLUMN = "number"
NAME_COLUMN = "name"
MASTER_COLUMN = "master"   # 'כן' if the code is in the master set, else 'לא'

# With no table page after the narrative (no 'תאריך הבקשה'), the model reads at most this much text after
# the heading: an upper bound that keeps a long letter out of the prompt, not a measured narrative length.
NARRATIVE_MAX_CHARS = 16_000

# region -> (coalition 'כן'/'לא', the request text verbatim, token usage dict)
Analyze = Callable[[str], "tuple[str, str, dict | None]"]


class LetterText(Protocol):
    """The text representations and scan flag exposed by a loaded letter."""
    scanned: bool
    markdown: str
    text: str


class LetterDocument(Protocol):
    """The loaded-letter operations used by Extractor."""
    doc: LetterText

    def extract_combined_table(self) -> pd.DataFrame: ...
    def arithmetic_failures(self) -> list[str]: ...
    def decision_links(self) -> list[str]: ...
    def extract_letterhead(self) -> list[str]: ...
    def extract_budget_history(self) -> list[tuple[str, pd.DataFrame]]: ...


Load = Callable[[str], LetterDocument]


@dataclass
class Extraction:
    """Everything read from one letter: what decides relevance, and, for a relevant letter,
    everything its summary PDF shows. Plain data; nothing here goes back to the PDF.
    Letterhead and budget-history parsing happen here, so their failures are `extract_error`."""
    source: str                # the letter's URL (or path), printed as the summary's source link
    table: pd.DataFrame        # the budget table (CODE_COLUMN, NAME_COLUMN, metrics, MASTER_COLUMN)
    matched_codes: set[str]    # letter codes that are in the master set
    relevant: bool             # a summary is produced iff this is True
    scanned: bool = False      # OCR'd letter: the PDF is marked "מכתב סרוק — יש לאמת מול המקור"
    # Read only for a relevant letter:
    fields: RequestFields = field(default_factory=RequestFields)
    letterhead: list[str] = field(default_factory=list)
    budget_history: list[tuple[str, pd.DataFrame]] = field(default_factory=list)
    llm_usage: dict | None = None   # model + token counts of the one LLM call, for the job log

    def named_matches(self, programs: dict[str, str]) -> dict[str, str]:
        """{code: program name} for the master programs that made this letter relevant."""
        return {code: programs.get(code, "") for code in sorted(self.matched_codes)}


class Extractor:
    """Deterministic tools + one injected coalition LLM call.

    Letterhead and budget-history parsing happen during extraction, so their failures are
    recorded as `extract_error`.
    """

    def __init__(self, master_programs, analyze: Analyze, load: Load):
        self.master = set(master_programs)
        self.analyze = analyze
        self.load = load

    # ------------------------------------------------------------------ entry
    def extract(self, source: str) -> Extraction:
        """Extract one letter (URL or local path) into fields + table + relevance."""
        letter = self.load(source)
        scanned = letter.doc.scanned

        # Relevance first: an irrelevant letter makes no model call and no field checks.
        table, matched = self._table(letter)
        if not matched:
            return Extraction(source, table, matched, relevant=False, scanned=scanned)

        bad_rows = letter.arithmetic_failures()
        if bad_rows and not scanned:
            raise ExtractionError(f"from + change != to in rows: {', '.join(bad_rows)}")

        # Narrative from the pymupdf4llm text; the labelled fields (date, numbers) read
        # better from the line-corrected text, except in a scan, which only has the OCR.
        region = self._narrative_region(letter.doc.markdown)
        if not region:
            raise ExtractionError("heading 'עיקרי הפנייה' not found or has no text")
        text = letter.doc.text
        # The ONE LLM call: coalition judgment + the full request text (not a summary).
        coalition, summary, usage = self.analyze(region)
        fields = RequestFields(
            date=self._date(text),
            request_number=self._request_number(text),
            program_number=self._program_number(summary),
            request_summary=summary,
            decision_links=self._decision_links(letter),
            staffing_changes=self._staffing(text),
            coalition_funds=coalition,
        )
        # A scan's date / request number may be unreadable (flagged "verify"); a text
        # letter must have every required field.
        required = {"request_summary": fields.request_summary}
        if not scanned:
            required |= {"date": fields.date, "request_number": fields.request_number}
        empty = [name for name, value in required.items() if not value.strip()]
        if empty:
            raise ExtractionError(f"empty required field: {', '.join(empty)}")

        return Extraction(source, table, matched, relevant=True, scanned=scanned, fields=fields,
                          letterhead=letter.extract_letterhead(), budget_history=letter.extract_budget_history(),
                          llm_usage=usage)

    # --------------------------------------------------- deterministic tools
    @staticmethod
    def _date(text: str) -> str:
        """The request date from the table pages ("תאריך הבקשה: DD/MM/YYYY"; OCR puts the
        date first and the words in reverse order)."""
        m = (re.search(r"תאריך הבקשה\s*:?\s*(\d{1,4}[./]\d{1,2}[./]\d{2,4})", text)
             or re.search(r"(\d{1,4}[./]\d{1,2}[./]\d{2,4})\s*הבקשה\s*:?\s*תאריך", text))
        return m.group(1) if m else ""

    def _request_number(self, text: str) -> str:
        """The 'בקשה מספר NN-NNN' numbers + the committee number, canonicalized."""
        numbers = list(dict.fromkeys(
            m.replace(" ", "")
            for m in (re.findall(r"בקשה מספר\s*(\d{2,3}\s*-\s*\d{2,3})", text)
                      or re.findall(r"(\d{2,3}-\d{2,3})\s*מספר\s*בקשה", text))  # OCR order
        ))
        committee = re.search(r"מספר פני\S* לועדה\s*:?\s*([^\n]+)", text)
        parts = []
        if numbers:
            parts.append(", ".join(numbers))
        if committee:
            parts.append(f"מספר פנייה לועדה: {committee.group(1).strip()}")
        return self._canonical_request_numbers(" | ".join(parts))

    @staticmethod
    def _narrative_region(text: str) -> str:
        """The narrative text (verbatim), from AFTER 'עיקרי הפנייה:' up to the budget-table
        pages — a bounded window the LLM returns as the whole request text verbatim. The heading
        itself is excluded (the report's field label supplies it), so it isn't doubled.
        Both spellings (הפניה / הפנייה) and, for OCR, either word order are accepted;
        "" when there is no heading."""
        m = re.search(r"עיקרי\s*הפניי?ה\s*:?|הפניי?ה\s*:\s*עיקרי", text)
        if not m:
            return ""
        # The table pages begin at 'תאריך הבקשה'; the narrative ends before them.
        table_start = text.find("תאריך הבקשה", m.end())
        end = table_start if table_start != -1 else min(len(text), m.start() + NARRATIVE_MAX_CHARS)
        return text[m.end():end].strip()

    @staticmethod
    def _program_number(scope: str) -> str:
        """Program codes named as 'NNNNNN:' in the given text, in order, de-duplicated."""
        codes = re.findall(r"תו?כנית\s*:?\s*(\d{5,6})", scope)
        codes += re.findall(r"(?m)^\s*(\d{5,6})\s*:", scope)
        return ", ".join(dict.fromkeys(codes))

    @staticmethod
    def _staffing(text: str) -> str:
        """'כן'/'לא' from the labeled statement 'השפעה על כוח אדם:' (or an explicit
        'שינוי בכוח אדם'); absence defaults to 'לא'."""
        m = re.search(r"השפעה על כוח אדם\s*:?\s*(\S+)", text)
        if m:
            value = m.group(1)
            if any(neg in value for neg in ("אין", "אינם", "ללא")):
                return "לא"
            return "כן"
        return "כן" if re.search(r"שינוי\S* בכוח אדם", text) else "לא"

    @staticmethod
    def _decision_links(letter) -> str:
        """Government-decision links, from the raw (LTR) text via BudgetLetter."""
        links = letter.decision_links()
        return "\n".join(f"{i}. {url}" for i, url in enumerate(links, 1))

    @staticmethod
    def _canonical_request_numbers(value: str) -> str:
        """Order every hyphenated request number as NN-NNN (2-digit group first)."""
        def fix(m: re.Match) -> str:
            a, b = m.group(1), m.group(2)
            return f"{b}-{a}" if len(a) == 3 and len(b) == 2 else f"{a}-{b}"
        return re.sub(r"(\d{2,3})-(\d{2,3})", fix, value)

    # ------------------------------------------------------- table + master
    def _table(self, letter):
        """The combined budget table + a `master` column and the matched codes."""
        table = letter.extract_combined_table().copy()
        table[MASTER_COLUMN] = [
            "כן" if self._normalize(c) in self.master else "לא"
            for c in table[CODE_COLUMN]
        ]
        matched = {self._normalize(c) for c in table[CODE_COLUMN]} & self.master
        return table, matched

    @staticmethod
    def _normalize(code) -> str:
        """A program code as a zero-padded 6-digit string (matches the master set)."""
        return str(code).strip().zfill(6)
