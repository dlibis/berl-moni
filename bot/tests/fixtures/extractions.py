"""Small extraction fixtures shared by domain, web, and renderer tests."""
from bot.domain.extraction import PROVENANCE_COALITION_FUNDS, PROVENANCE_EXACT_CLAUSES, Extraction
from bot.domain.request_fields import ProgramUses, RequestFields, Use
from bot.domain.table import Table


def complete_extraction() -> Extraction:
    table = Table.from_records(
        ["number", "name", "net from", "net to"],
        [
            {"number": "200101", "name": "a", "net from": 100.0, "net to": 40.0},
            {"number": "200102", "name": "b", "net from": 0.0, "net to": 60.0},
        ],
    )
    history = Table.from_records(
        ["year", "net"],
        [{"year": "2025", "net": 60.0}],
    )
    fields = RequestFields(
        date="18/10/2026",
        request_number="13-206",
        program_number="200102",
        total_amount="60",
        programs=[ProgramUses(code="200102", uses=[Use(text="test use")])],
        decision_links="https://example.test/decision",
        coalition_funds="לא",
        staffing_changes="לא",
    )
    return Extraction(
        source="https://example.test/letter.pdf",
        table=table,
        fields=fields,
        letterhead=["Budget request"],
        budget_history=[("net history", history)],
        llm_usage={"model": "gpt-x", "input_tokens": 10, "output_tokens": 5},
    )


def irrelevant_extraction() -> Extraction:
    """Legacy master-only skip: no LLM fields (incomplete); still used for re-queue tests."""
    table = Table.from_records(
        ["number", "name", "net from", "net to"],
        [{"number": "200101", "name": "a", "net from": 100.0, "net to": 40.0}],
    )
    return Extraction(source="https://example.test/irrelevant.pdf", table=table)


def complete_irrelevant_extraction() -> Extraction:
    table = Table.from_records(
        ["number", "name", "net from", "net to"],
        [{"number": "200101", "name": "a", "net from": 100.0, "net to": 40.0}],
    )
    fields = RequestFields(
        date="18/10/2026",
        request_number="13-206",
        program_number="200101",
        total_amount="40",
        programs=[ProgramUses(code="200101", uses=[Use(text="x")])],
        decision_links="",
        coalition_funds="לא",
        staffing_changes="לא",
    )
    return Extraction(source="https://example.test/irrelevant-complete.pdf", table=table, fields=fields)


def coalition_bypass_extraction() -> Extraction:
    base = complete_irrelevant_extraction()
    fields = base.fields.model_copy(update={"coalition_funds": "כן"})
    return Extraction(
        source="https://example.test/coalition.pdf",
        table=base.table,
        fields=fields,
        relevance_provenance=PROVENANCE_COALITION_FUNDS,
    )


def exact_bypass_extraction() -> Extraction:
    ext = complete_extraction()
    return Extraction(
        source="https://example.test/exact-clause.pdf",
        table=Table.from_records(
            ["number", "name", "net from", "net to"],
            [{"number": "999999", "name": "x", "net from": 1.0, "net to": 1.0}],
        ),
        fields=ext.fields,
        relevance_provenance=PROVENANCE_EXACT_CLAUSES,
    )
