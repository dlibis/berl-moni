import pytest

from bot.domain.report import report_view
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
