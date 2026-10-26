"""Letter extraction: deterministic rules over the letter + one injected LLM call.

`Extractor` owns ALL request-field extraction for a budget-transfer letter. Most fields are
produced by deterministic methods over the FULL letter text (no truncation). One call to
`analyze` (bot.adapters.llm.letter_analyzer.LlmAnalyzer in production, a lambda in tests) over the narrative region
does the two things that vary per letter: judging `coalition_funds` and saying, per program,
what the request's money is for. No deterministic fallback. `load(source)` returns the letter
(bot.adapters.letter_pdf.loader.open_letter in production): its text, tables and links. The
Extractor reads no environment, no database and no PDF library itself: bot.bootstrap builds it.

    extractor = Extractor(programs, analyze=LlmAnalyzer(...), load=open_letter)
    result = extractor.extract(source)   # source = URL or local PDF path
    result.fields                  # RequestFields (None for an irrelevant letter: no LLM call)
    result.table                   # the budget table (a plain Table)
    result.matched(programs)       # letter codes that are in the master set
    result.relevant_to(programs)   # True iff a summary should be produced
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol

from bot.domain.errors import ExtractionError
from bot.domain.request_fields import PROGRAM_HEADING, ProgramUses, RequestFields
from bot.domain.table import Table
from bot.domain.versions import SCHEMA_VERSION

# The budget table's columns: code, name, then '<metric> from' / '<metric> to' per metric.
CODE_COLUMN = "number"
NAME_COLUMN = "name"

# With no table page after the narrative (no 'תאריך הבקשה'), the model reads at most this much text after
# the heading: an upper bound that keeps a long letter out of the prompt, not a measured narrative length.
NARRATIVE_MAX_CHARS = 16_000

# region -> (coalition 'כן'/'לא'/'אולי', what each program's money is for, token usage dict)
Analyze = Callable[[str], "tuple[str, list[ProgramUses], dict | None]"]

# Spec §2.1 exact-string bypass (literal substring on letter.doc.text — no OCR fuzzy match).
EXACT_BYPASS_MARKERS = (
    "כספים קואליציוניים: כן",
    "יישום הסכמים פוליטיים בעלי משמעות תקציבית",
)
# Persisted under extraction JSON key `relevance_provenance` (not a DB column).
RELEVANCE_PROVENANCE_KEY = "relevance_provenance"
PROVENANCE_EXACT_CLAUSES = (
    "Relevant due to explicit presence of Coalition Funds / Political Agreements clauses, "
    "independent of master program matching."
)
PROVENANCE_COALITION_FUNDS = (
    "Relevant due to coalition_funds = כן, independent of master program matching."
)
_FROZEN_PROVENANCE = frozenset({PROVENANCE_EXACT_CLAUSES, PROVENANCE_COALITION_FUNDS})


def exact_bypass_in_text(text: str) -> bool:
    return any(marker in text for marker in EXACT_BYPASS_MARKERS)


def relevance_sql(programs_param: str = "%(programs)s::text[]") -> str:
    """SQL for `is_relevant` on a `letters` row (same semantics as Extraction.is_relevant)."""
    key = RELEVANCE_PROVENANCE_KEY
    return (
        f"(coalesce(extraction->>'{key}' IN (%(prov_exact)s, %(prov_coalition)s), false) "
        f"OR coalesce(extraction->'fields'->>'coalition_funds' = 'כן', false) "
        f"OR coalesce(codes && {programs_param}, false))"
    )


class LetterText(Protocol):
    """The text representations and scan flag exposed by a loaded letter."""
    scanned: bool
    markdown: str
    text: str


class LetterDocument(Protocol):
    """The loaded-letter operations used by Extractor."""
    doc: LetterText
    source_sha256: str
    source_size: int

    def extract_combined_table(self) -> Table: ...
    def arithmetic_failures(self) -> list[str]: ...
    def decision_links(self) -> list[str]: ...
    def extract_letterhead(self) -> list[str]: ...
    def extract_budget_history(self) -> list[tuple[str, Table]]: ...


Load = Callable[[str], LetterDocument]


@dataclass
class Extraction:
    """Everything read from one letter: what decides relevance, and, for a relevant letter,
    everything its summary PDF shows. Plain data; nothing here goes back to the PDF.
    Letterhead and budget-history parsing happen here, so their failures are `extract_error`.
    Relevance depends on the programs list, so it is computed, never stored."""
    source: str                # the letter's URL (or path), printed as the summary's source link
    table: Table               # the budget table (CODE_COLUMN, NAME_COLUMN, metrics)
    scanned: bool = False      # OCR'd letter: the PDF is marked "מכתב סרוק — יש לאמת מול המקור"
    # Read only for a relevant letter:
    fields: RequestFields | None = None
    letterhead: list[str] = field(default_factory=list)
    budget_history: list[tuple[str, Table]] = field(default_factory=list)
    llm_usage: dict | None = None   # model + token counts of the one LLM call, for the job log
    source_sha256: str = ""
    source_size: int = 0
    relevance_provenance: str | None = None  # JSON key RELEVANCE_PROVENANCE_KEY; paths (1)/(2) only

    @staticmethod
    def _table_to_json(table: Table) -> dict:
        return {"columns": list(table.columns), "rows": [list(row) for row in table.rows]}

    @staticmethod
    def _table_from_json(data: dict) -> Table:
        return Table(tuple(data["columns"]), tuple(tuple(row) for row in data["rows"]))

    def to_json(self) -> dict:
        """The versioned, program-independent extraction persisted by the worker."""
        return {
            "schema_version": SCHEMA_VERSION,
            "source": self.source,
            "scanned": self.scanned,
            "table": self._table_to_json(self.table),
            "budget_history": [
                {"label": label, "table": self._table_to_json(table)}
                for label, table in self.budget_history
            ],
            "letterhead": self.letterhead,
            "fields": self.fields.model_dump() if self.fields is not None else None,
            "llm_usage": self.llm_usage,
            RELEVANCE_PROVENANCE_KEY: self.relevance_provenance,
        }

    @classmethod
    def from_json(cls, data: dict) -> Extraction:
        fields = RequestFields.model_validate(data["fields"]) if data.get("fields") is not None else None
        return cls(
            source=data["source"],
            table=cls._table_from_json(data["table"]),
            scanned=data.get("scanned", False),
            fields=fields,
            letterhead=list(data.get("letterhead", [])),
            budget_history=[
                (item["label"], cls._table_from_json(item["table"]))
                for item in data.get("budget_history", [])
            ],
            llm_usage=data.get("llm_usage"),
            relevance_provenance=data.get(RELEVANCE_PROVENANCE_KEY),
        )

    def codes(self) -> set[str]:
        """The letter's program codes, zero-padded to 6 digits (as the master set holds them)."""
        return {str(code).strip().zfill(6) for code in self.table.column(CODE_COLUMN)}

    def matched(self, programs: Iterable[str]) -> set[str]:
        """The letter's codes that are in `programs`."""
        return self.codes() & set(programs)

    def is_relevant(self, programs: Iterable[str]) -> bool:
        """Spec §2: any of exact-clause bypass, coalition_funds כן, or master code match."""
        if self.relevance_provenance in _FROZEN_PROVENANCE:
            return True
        if self.matched(programs):
            return True
        if self.fields is not None and self.fields.coalition_funds == "כן":
            return True
        return False

    def relevant_to(self, programs: Iterable[str]) -> bool:
        return self.is_relevant(programs)

    @property
    def complete(self) -> bool:
        """The LLM part ran."""
        return self.fields is not None

    def named_matches(self, programs: dict[str, str]) -> dict[str, str]:
        """{code: program name} for the master programs that make this letter relevant."""
        return {code: programs[code] for code in sorted(self.matched(programs))}


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
        source_details = {"source_sha256": letter.source_sha256, "source_size": letter.source_size}

        table = letter.extract_combined_table()
        exact_bypass = exact_bypass_in_text(letter.doc.text)

        bad_rows = letter.arithmetic_failures()
        if bad_rows and not scanned:
            raise ExtractionError(f"from + change != to in rows: {', '.join(bad_rows)}")

        # Narrative from the pymupdf4llm text; the labelled fields (date, numbers) read
        # better from the line-corrected text, except in a scan, which only has the OCR.
        region = self._narrative_region(letter.doc.markdown)
        if not region:
            raise ExtractionError("heading 'עיקרי הפנייה' not found or has no text")
        text = letter.doc.text
        # The ONE LLM call: coalition judgment + what each program's money is for.
        coalition, programs, usage = self.analyze(region)
        fields = RequestFields(
            date=self._date(text),
            request_number=self._request_number(text),
            program_number=self._program_number(region),
            total_amount=self._total_amount(region),
            programs=programs,
            decision_links=self._decision_links(letter),
            staffing_changes=self._staffing(text),
            coalition_funds=coalition,
        )
        # A scan's date / request number may be unreadable (flagged "verify"); a text
        # letter must have every required field.
        required = {} if scanned else {"date": fields.date, "request_number": fields.request_number}
        empty = [name for name, value in required.items() if not value.strip()]
        if not fields.programs:
            empty.append("programs")
        if empty:
            raise ExtractionError(f"empty required field: {', '.join(empty)}")

        if exact_bypass:
            provenance = PROVENANCE_EXACT_CLAUSES
        elif fields.coalition_funds == "כן":
            provenance = PROVENANCE_COALITION_FUNDS
        else:
            provenance = None

        return Extraction(source, table, scanned=scanned, fields=fields, **source_details,
                          letterhead=letter.extract_letterhead(), budget_history=letter.extract_budget_history(),
                          llm_usage=usage, relevance_provenance=provenance)

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
    def _total_amount(region: str) -> str:
        """The request's total as the opening sentence prints it ('... סך של 190,709 אלפי ש"ח'), in
        thousands of ₪; "" when the letter states none."""
        m = re.search(r"סך של\s*([\d,]+)\s*אלפי", region)
        return m.group(1) if m else ""

    @staticmethod
    def _program_number(scope: str) -> str:
        """Program codes headed 'NNNNNN:' or 'תכנית NNNNNN -' (21547) in the given text, in the order
        they appear, de-duplicated. The colon or dash is what makes a heading: a bare
        'תוכנית NNNNNN' at a line's end also opens the committee's questions after the narrative."""
        heading = rf"{PROGRAM_HEADING}|תו?כנית\s*(\d{{5,6}})\s+[-–]"
        codes = [m.group(1) or m.group(2) for m in re.finditer(heading, scope)]
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
