"""The Knesset feed is read in pages of 10 until TotalCount rows are in hand.

requests.post is stubbed; no network.
"""
import json
from datetime import date
from unittest import mock

import pytest
import requests

from bot.adapters.knesset.feed import fetch_letters
from bot.domain.errors import FeedUnreachable


def _rows(urls, total=None):
    total = len(urls) if total is None else total
    return [{"ReportUrl": url, "TotalCount": total} for url in urls]


def _response(body, status=200):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode()
    return response


def _pages(*bodies):
    return mock.patch("bot.adapters.knesset.feed.post", side_effect=[_response(body) for body in bodies])


def test_twelve_rows_take_two_pages():
    urls = [f"https://example.com/{i}.pdf" for i in range(12)]
    page_one, page_two = _rows(urls[:10], 12), _rows(urls[10:], 12)
    with _pages(page_one, page_two) as post:
        assert [l.url for l in fetch_letters()] == urls
    assert post.call_count == 2
    assert post.call_args_list[1].kwargs["json"]["PageNumber"] == 2
    assert post.call_args_list[0].kwargs["timeout"] == 30


def test_zero_rows_is_empty_list_after_one_post():
    with _pages([]) as post:
        assert [l.url for l in fetch_letters()] == []
    assert post.call_count == 1


def test_short_page_is_unreachable():
    urls = [f"https://example.com/{i}.pdf" for i in range(12)]
    with _pages(_rows(urls[:10], 12), _rows(urls[10:11], 12)):
        with pytest.raises(FeedUnreachable):
            fetch_letters()


def test_http_500_is_unreachable():
    with mock.patch("bot.adapters.knesset.feed.post", return_value=_response([], status=500)):
        with pytest.raises(FeedUnreachable):
            fetch_letters()


def test_timeout_is_unreachable():
    with mock.patch("bot.adapters.knesset.feed.post", side_effect=requests.exceptions.Timeout()):
        with pytest.raises(FeedUnreachable):
            fetch_letters()


def test_non_list_body_is_unreachable():
    with _pages({"error": "maintenance"}):
        with pytest.raises(FeedUnreachable):
            fetch_letters()


def test_empty_report_url_is_skipped():
    rows = _rows(["https://example.com/a.pdf", "   ", "https://example.com/b.pdf", None])
    with _pages(rows):
        assert [l.url for l in fetch_letters()] == ["https://example.com/a.pdf", "https://example.com/b.pdf"]


def test_duplicates_are_dropped_keeping_first_position():
    urls = ["https://example.com/a.pdf", "https://example.com/b.pdf", "https://example.com/a.pdf"]
    with _pages(_rows(urls)):
        assert [l.url for l in fetch_letters()] == ["https://example.com/a.pdf", "https://example.com/b.pdf"]


def _row(url, number="13-206", date="2026-07-14T03:00:00", ministry="חינוך"):
    return {"ReportUrl": url, "RequestNumberRange": number, "ApprovedDate": date, "GovMinistryName": ministry,
            "Description": "d", "TotalCount": 3}


def test_rows_sharing_a_pdf_become_one_letter():
    rows = [_row("u1", "13-206", "2026-07-14T03:00:00", "הוצאות שונות"),
            _row("u1", "13-207", "2026-07-10T03:00:00", "הוצאות שונות"),
            _row("u2", "20-001", "2026-07-15T03:00:00", "חינוך")]
    with _pages(rows):
        [a, b] = fetch_letters()
    assert (a.url, a.letter_date, a.request_numbers) == ("u1", date(2026, 7, 10), ("13-206", "13-207"))
    assert a.ministry == "הוצאות שונות" and "Description" not in a.rows[0] and b.url == "u2"
    assert "TotalCount" not in a.rows[0]


def test_missing_date_is_none():
    with _pages([_row("u1", date=None) | {"TotalCount": 1}]):
        assert fetch_letters()[0].letter_date is None
