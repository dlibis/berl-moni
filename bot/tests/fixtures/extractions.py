"""Small extraction fixtures shared by domain, web, and renderer tests."""
from bot.domain.extraction import Extraction
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
    table = Table.from_records(
        ["number", "name", "net from", "net to"],
        [{"number": "200101", "name": "a", "net from": 100.0, "net to": 40.0}],
    )
    return Extraction(source="https://example.test/irrelevant.pdf", table=table)
