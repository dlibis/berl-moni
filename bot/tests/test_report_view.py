import pytest

from bot.domain.report import report_view
from bot.tests.fixtures.extractions import complete_extraction as make_complete_extraction


@pytest.fixture
def complete_extraction():
    return make_complete_extraction()


def test_report_view_matches_money_flow(complete_extraction):
    view = report_view(complete_extraction, {"200102": "b"})
    assert view["money_flow"]["metric"] == "net"
    assert [w["direction"] for w in view["why"]] == ["in", "out"] and view["why"][0]["master"] is True


def test_report_view_sections(complete_extraction):
    view = report_view(complete_extraction, {"200102": "b"})
    assert view["summary"] == {"date": "18/10/2026", "request_number": "13-206", "total_amount": "60",
                               "coalition_funds": "לא", "program_count": 2, "master_count": 1}
    assert view["money_flow"]["destinations"] == [{"code": "200102", "name": "b", "amount": 60.0}]
    assert view["why"][0]["uses"] == "test use"
    assert view["appendix"]["decision_links"] == ["https://example.test/decision"]
    assert view["appendix"]["budget_history"][0]["table"]["columns"] == ["year", "net"]
