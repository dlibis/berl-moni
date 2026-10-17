"""The Knesset feed is read in pages of 10 until TotalCount rows are in hand.

requests.post is stubbed; no network.
"""
import json
import os
import sys
from unittest import mock

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aggregator import FeedUnreachable, get_pdf_urls  # noqa: E402


def _rows(urls, total=None):
    total = len(urls) if total is None else total
    return [{"ReportUrl": url, "TotalCount": total} for url in urls]


def _response(body, status=200):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(body).encode()
    return response


def _pages(*bodies):
    return mock.patch("aggregator.post", side_effect=[_response(body) for body in bodies])


def test_twelve_rows_take_two_pages():
    urls = [f"https://example.com/{i}.pdf" for i in range(12)]
    page_one, page_two = _rows(urls[:10], 12), _rows(urls[10:], 12)
    with _pages(page_one, page_two) as post:
        assert get_pdf_urls() == urls
    assert post.call_count == 2
    assert post.call_args_list[1].kwargs["json"]["PageNumber"] == 2
    assert post.call_args_list[0].kwargs["timeout"] == 30


def test_zero_rows_is_empty_list_after_one_post():
    with _pages([]) as post:
        assert get_pdf_urls() == []
    assert post.call_count == 1


def test_short_page_is_unreachable():
    urls = [f"https://example.com/{i}.pdf" for i in range(12)]
    with _pages(_rows(urls[:10], 12), _rows(urls[10:11], 12)):
        with pytest.raises(FeedUnreachable):
            get_pdf_urls()


def test_http_500_is_unreachable():
    with mock.patch("aggregator.post", return_value=_response([], status=500)):
        with pytest.raises(FeedUnreachable):
            get_pdf_urls()


def test_timeout_is_unreachable():
    with mock.patch("aggregator.post", side_effect=requests.exceptions.Timeout()):
        with pytest.raises(FeedUnreachable):
            get_pdf_urls()


def test_non_list_body_is_unreachable():
    with _pages({"error": "maintenance"}):
        with pytest.raises(FeedUnreachable):
            get_pdf_urls()


def test_empty_report_url_is_skipped():
    rows = _rows(["https://example.com/a.pdf", "   ", "https://example.com/b.pdf", None])
    with _pages(rows):
        assert get_pdf_urls() == ["https://example.com/a.pdf", "https://example.com/b.pdf"]


def test_duplicates_are_dropped_keeping_first_position():
    urls = ["https://example.com/a.pdf", "https://example.com/b.pdf", "https://example.com/a.pdf"]
    with _pages(_rows(urls)):
        assert get_pdf_urls() == ["https://example.com/a.pdf", "https://example.com/b.pdf"]
