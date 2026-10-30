from datetime import date
from unittest.mock import Mock

import pytest

from bot.adapters.knesset.feed import fetch_approvals
from bot.adapters.postgres.letters import LettersRepository
from bot.domain.errors import FeedUnreachable
from bot.domain.feed import Approval, request_key
from bot.service_layer.analysis import refresh_feed


def test_complete_number_set_ignores_order_and_grouping():
    assert request_key(['43-206, 17-211', '51-215']) == request_key(['51-215,17-211,43-206'])
    assert request_key(['43-206']) != request_key(['43-206,17-211'])


def repository(numbers):
    conn = Mock()
    conn.execute.return_value.fetchall.return_value = [
        {'letter_url': 'old-url', 'request_numbers': numbers}]
    return LettersRepository(conn), conn


def test_matches_numbers_and_keeps_sticky_values():
    repo, conn = repository(['43-206,17-211'])
    repo.record_approvals([Approval(('17-211,43-206',), date(2026, 10, 21))])
    sql, params = conn.execute.call_args.args
    assert params == (date(2026, 10, 21), 'old-url')
    assert 'passed = true' in sql
    assert 'COALESCE(passage_detected_at, now())' in sql
    assert 'COALESCE(passed_date, %s)' in sql


@pytest.mark.parametrize('approvals', [
    [Approval(('43-206',), date(2026, 10, 21))],
    [Approval(('43-206,17-211',), date(2026, 10, 21)),
     Approval(('43-206,17-211',), date(2025, 10, 21))],
    [],
])
def test_missing_partial_or_ambiguous_matches_do_not_update(approvals):
    repo, conn = repository(['43-206,17-211'])
    repo.record_approvals(approvals)
    assert conn.execute.call_count == 1


def test_missing_official_date_still_confirms_passage():
    repo, conn = repository(['43-206'])
    repo.record_approvals([Approval(('43-206',), None)])
    assert conn.execute.call_args.args[1] == (None, 'old-url')


def test_approval_failure_does_not_write_or_commit():
    uow = Mock()
    with pytest.raises(FeedUnreachable):
        refresh_feed(uow, lambda: [], approvals=Mock(side_effect=FeedUnreachable('down')))
    uow.letters.upsert_feed.assert_not_called()
    uow.commit.assert_not_called()


def test_approved_pagination_and_dates_without_pdf_heads(monkeypatch):
    pages = Mock(side_effect=[
        [{'TotalCount': 11, 'RequestNumberRange': str(n), 'ApprovedDate': 'invalid'} for n in range(10)],
        [{'TotalCount': 11, 'RequestNumberRange': '43-206', 'ApprovedDate': '2026-10-21T03:00:00'}],
    ])
    monkeypatch.setattr('bot.adapters.knesset.feed._get_page', pages)
    head = Mock()
    monkeypatch.setattr('bot.adapters.knesset.feed.head', head)
    result = fetch_approvals()
    assert len(result) == 11 and result[0].approved_date is None
    assert result[-1] == Approval(('43-206',), date(2026, 10, 21))
    assert pages.call_args_list[1].args == (2, 1)
    head.assert_not_called()


def test_incomplete_approval_pages_fail(monkeypatch):
    monkeypatch.setattr('bot.adapters.knesset.feed._get_page', lambda *a: [{'TotalCount': 2}])
    with pytest.raises(FeedUnreachable):
        fetch_approvals()


def test_approval_rows_sharing_pdf_form_complete_number_set(monkeypatch):
    monkeypatch.setattr('bot.adapters.knesset.feed._get_page', lambda *a: [
        {'TotalCount': 2, 'ReportUrl': 'new-url', 'RequestNumberRange': n,
         'ApprovedDate': '2026-10-21T03:00:00'} for n in ('43-206', '17-211')])
    assert fetch_approvals() == [Approval(('43-206', '17-211'), date(2026, 10, 21))]
