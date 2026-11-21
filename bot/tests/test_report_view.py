import pytest

from bot.domain.extraction import Extraction
from bot.domain.report import budget_table_rows, report_view
from bot.domain.request_fields import ProgramUses, RequestFields, Use
from bot.domain.table import Table
from bot.tests.fixtures.extractions import complete_extraction as make_complete_extraction


@pytest.fixture
def complete_extraction():
    return make_complete_extraction()


def test_report_view_matches_money_flow(complete_extraction):
    view = report_view(complete_extraction, {"200102": "b"})
    assert view["money_flow"]["metric"] == "net"
    assert view["money_flow"]["master"] == ["200102"]
    assert view["why"]["shown"][0]["master"] is True and view["why"]["sources"] == ["200101"]


def test_report_view_sections(complete_extraction):
    view = report_view(complete_extraction, {"200102": "b"})
    assert view["summary"] == [
        {"label": "סך הפנייה", "value": "60 אלפי ש״ח"},
        {"label": "העברה פנימית במשרד", "value": "60 אלפי ש״ח"},
        {"label": "כספים קואליציוניים", "value": "לא"},
        {"label": "תוכניות מהמאסטר", "value": "1 מתוך 2"},
        {"label": "מס' פנייה", "value": "13-206"},
        {"label": "תאריך", "value": "18/10/2026"},
    ]
    assert view["money_flow"]["destinations"] == [{"code": "200102", "name": "b", "amount": 60.0}]
    assert view["why"]["shown"][0]["uses"] == [{"text": "test use", "coalition": False}]
    assert view["appendix"]["table"]["rows"][1] == ["200101", "a", "מ-", "100", "-60", "לא"]
    assert view["appendix"]["decision_links"] == ["https://example.test/decision"]
    assert view["appendix"]["budget_history"][0]["table"]["columns"] == ["year", "net"]


@pytest.mark.parametrize("stored_links", [
    "1. https://www.gov.il/he/pages/dec3425\n\n  2. https://www.gov.il/he/pages/dec550_2021  ",
    " https://www.gov.il/he/pages/dec3425 \nhttps://www.gov.il/he/pages/dec550_2021",
])
def test_report_view_returns_urls_without_list_numbering(complete_extraction, stored_links):
    complete_extraction.fields.decision_links = stored_links

    view = report_view(complete_extraction, {})

    assert view["appendix"]["decision_links"] == [
        "https://www.gov.il/he/pages/dec3425",
        "https://www.gov.il/he/pages/dec550_2021",
    ]
    assert complete_extraction.fields.decision_links == stored_links


def test_report_view_without_decision_links(complete_extraction):
    complete_extraction.fields.decision_links = " \n\n"

    assert report_view(complete_extraction, {})["appendix"]["decision_links"] == []


def _reserve_commitment_extraction() -> Extraction:
    """54-247: הוצאה is unchanged; the 139,049 move is הרשאה להתחייב, source is a 2-digit סעיף."""
    table = Table.from_records(
        ["number", "name", "הוצאה from", "הוצאה to", "הוצאה מותנית from", "הוצאה מותנית to",
         "הרשאה להתחייב from", "הרשאה להתחייב to", "שיא כח אדם from", "שיא כח אדם to",
         'עב"צ from', 'עב"צ to'],
        [
            {"number": "470103", "name": "רזרבת שיא כח אדם למשרדי הממשלה",
             "הוצאה from": None, "הוצאה to": None, "הוצאה מותנית from": None, "הוצאה מותנית to": None,
             "הרשאה להתחייב from": None, "הרשאה להתחייב to": None,
             "שיא כח אדם from": 537.0, "שיא כח אדם to": 537.0, 'עב"צ from': None, 'עב"צ to': None},
            {"number": "543501", "name": "הרשות להתחדשות עירונית",
             "הוצאה from": 343273.0, "הוצאה to": 343273.0, "הוצאה מותנית from": 50000.0, "הוצאה מותנית to": 50000.0,
             "הרשאה להתחייב from": 215889.0, "הרשאה להתחייב to": 354938.0,
             "שיא כח אדם from": 33.0, "שיא כח אדם to": 33.0, 'עב"צ from': 6.0, 'עב"צ to': 18.0},
        ],
    )
    fields = RequestFields(
        date="15/09/2026",
        request_number="54-247 | מספר פנייה לועדה: 224",
        total_amount="",
        programs=[ProgramUses(code="543501", uses=[Use(text="הסכמי מסגרת לעידוד התחדשות עירונית")])],
        coalition_funds="לא",
        staffing_changes="כן",
    )
    return Extraction(source="https://example.test/22107.pdf", table=table, fields=fields)


def test_report_view_uses_commitment_when_expenditure_did_not_move():
    view = report_view(_reserve_commitment_extraction(), {})
    assert view["summary"][0] == {"label": "סך הפנייה", "value": "139,049 אלפי ש״ח"}
    assert view["money_flow"]["metric"] == "הרשאה להתחייב"
    assert view["money_flow"]["destinations"] == [
        {"code": "543501", "name": "הרשות להתחדשות עירונית", "amount": 139049.0}]
    assert view["money_flow"]["hubs"] == [
        {"name": "רזרבה כללית", "items": [{"code": "", "name": "רזרבה כללית", "amount": 139049.0}]}]
    assert view["why"]["shown"][0]["uses"] == [
        {"text": "הסכמי מסגרת לעידוד התחדשות עירונית", "coalition": False}]
    assert view["why"]["sources"] == []
    rows, _ = budget_table_rows(_reserve_commitment_extraction().table, set())
    assert rows[3][-2] == "139,049"  # 543501 שינוי is הרשאה, not the zero הוצאה column
