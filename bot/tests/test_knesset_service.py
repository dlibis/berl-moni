from datetime import date
from io import BytesIO
from unittest.mock import Mock

import pytest
from requests import HTTPError
from urllib3.response import HTTPResponse

from bot.adapters.knesset.remote import KnessetClient
from bot.domain.errors import FeedUnreachable
from bot.domain.feed import FeedLetter
from cloud.knesset_feed.app import app

TOKEN = "test-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
LETTER = FeedLetter("https://fs.knesset.gov.il/globaldocs/FINANCE/example.pdf", date(2026, 10, 1), "ministry", ("1",), ({"a": 1},))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("KNESSET_FETCH_TOKEN", TOKEN)
    return app.test_client()


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "Bearer é"}])
def test_unauthorized_request_never_fetches(client, monkeypatch, headers):
    fetch = Mock()
    monkeypatch.setattr("cloud.knesset_feed.app.fetch_letters", fetch)
    assert client.get("/feed", headers=headers).status_code == 401
    fetch.assert_not_called()


def test_missing_service_token_fails_closed(client, monkeypatch):
    monkeypatch.delenv("KNESSET_FETCH_TOKEN")
    assert client.get("/feed", headers=HEADERS).status_code == 401


def test_service_response_round_trips_to_domain(client, monkeypatch):
    monkeypatch.setattr("cloud.knesset_feed.app.fetch_letters", lambda: [LETTER])
    result = client.get("/feed", headers=HEADERS)
    assert result.status_code == 200 and result.headers["Cache-Control"] == "no-store"
    response = Mock()
    response.json.return_value = result.get_json()
    get = Mock(return_value=response)
    monkeypatch.setattr("bot.adapters.knesset.remote.Session.get", get)
    assert KnessetClient("https://fetch.example/", TOKEN).fetch_letters() == [LETTER]
    assert get.call_args.kwargs["headers"] == HEADERS
    assert get.call_args.args == ("https://fetch.example/feed",)


def test_feed_failure_is_not_an_empty_success(client, monkeypatch):
    def down():
        raise FeedUnreachable("page 1")
    monkeypatch.setattr("cloud.knesset_feed.app.fetch_letters", down)
    assert client.get("/feed", headers=HEADERS).status_code == 502


@pytest.mark.parametrize("body", [{}, [{}], [{"url": "x", "letter_date": "bad-date"}]])
def test_remote_rejects_invalid_feed(monkeypatch, body):
    response = Mock()
    response.json.return_value = body
    monkeypatch.setattr("bot.adapters.knesset.remote.Session.get", lambda *a, **kw: response)
    with pytest.raises(FeedUnreachable):
        KnessetClient("https://fetch.example", TOKEN).fetch_letters()


def test_remote_http_error_is_feed_unreachable(monkeypatch):
    response = Mock()
    response.raise_for_status.side_effect = HTTPError()
    monkeypatch.setattr("bot.adapters.knesset.remote.Session.get", lambda *a, **kw: response)
    with pytest.raises(FeedUnreachable):
        KnessetClient("https://fetch.example", TOKEN).fetch_letters()


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_remote_retries_transient_status_then_succeeds(monkeypatch, status):
    request = Mock(side_effect=[HTTPResponse(status=status, body=BytesIO(b"busy"), preload_content=False),
                                HTTPResponse(status=200, body=BytesIO(b"[]"), preload_content=False)])
    monkeypatch.setattr("urllib3.connectionpool.HTTPSConnectionPool._make_request", request)
    # Avoid environment proxy configuration; exercise the real HTTPAdapter and Retry.
    monkeypatch.setenv("NO_PROXY", "fetch.example")
    assert KnessetClient("https://fetch.example", TOKEN).fetch_letters() == []
    assert request.call_count == 2


@pytest.mark.parametrize("status,attempts", [(429, 5), (401, 1), (403, 1)])
def test_remote_retry_limit_and_permanent_errors(monkeypatch, status, attempts):
    request = Mock(side_effect=lambda *a, **kw: HTTPResponse(status=status, body=BytesIO(b"busy"), preload_content=False))
    monkeypatch.setattr("urllib3.connectionpool.HTTPSConnectionPool._make_request", request)
    monkeypatch.setenv("NO_PROXY", "fetch.example")
    monkeypatch.setattr("urllib3.util.retry.time.sleep", Mock())
    with pytest.raises(FeedUnreachable, match=f"HTTP {status}"):
        KnessetClient("https://fetch.example", TOKEN).fetch_letters()
    assert request.call_count == attempts


def test_remote_caps_retry_after(monkeypatch):
    request = Mock(side_effect=[HTTPResponse(status=429, headers={"Retry-After": "600"}, body=BytesIO(b"busy"), preload_content=False),
                                HTTPResponse(status=200, body=BytesIO(b"[]"), preload_content=False)])
    monkeypatch.setattr("urllib3.connectionpool.HTTPSConnectionPool._make_request", request)
    monkeypatch.setenv("NO_PROXY", "fetch.example")
    sleep = Mock()
    monkeypatch.setattr("urllib3.util.retry.time.sleep", sleep)
    assert KnessetClient("https://fetch.example", TOKEN).fetch_letters() == []
    sleep.assert_called_once_with(10)


@pytest.mark.parametrize("url,token", [("http://fetch.example", TOKEN), ("https://fetch.example", "")])
def test_remote_requires_https_and_token(url, token):
    with pytest.raises(ValueError):
        KnessetClient(url, token)


@pytest.mark.parametrize("url", ["http://fs.knesset.gov.il/globaldocs/FINANCE/a.pdf",
                               "https://example.com/a.pdf", "http://169.254.169.254/",
                               "https://fs.knesset.gov.il@evil.example/globaldocs/FINANCE/a.pdf",
                               "https://fs.knesset.gov.il/other/a.pdf", "https://[bad"])
def test_pdf_proxy_rejects_other_destinations(client, monkeypatch, url):
    get = Mock()
    monkeypatch.setattr("cloud.knesset_feed.app.requests.get", get)
    assert client.get("/pdf", query_string={"url": url}, headers=HEADERS).status_code == 400
    get.assert_not_called()


def pdf_response(monkeypatch, body=b"%PDF-1.7\n", status=200):
    response = Mock(status_code=status)
    response.iter_content.return_value = [body]
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    get = Mock(return_value=response)
    monkeypatch.setattr("cloud.knesset_feed.app.requests.get", get)
    return get


def test_pdf_proxy_returns_only_pdf_bytes(client, monkeypatch):
    get = pdf_response(monkeypatch)
    result = client.get("/pdf", query_string={"url": LETTER.url}, headers=HEADERS)
    assert result.status_code == 200 and result.data == b"%PDF-1.7\n"
    assert get.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize("body,status", [(b"<html>blocked</html>", 200), (b"", 302), (b"", 500)])
def test_pdf_proxy_rejects_html_and_redirects(client, monkeypatch, body, status):
    pdf_response(monkeypatch, body, status)
    assert client.get("/pdf", query_string={"url": LETTER.url}, headers=HEADERS).status_code == 502


def test_pdf_proxy_bounds_download_size(client, monkeypatch):
    monkeypatch.setattr("cloud.knesset_feed.app.MAX_PDF_BYTES", 1)
    pdf_response(monkeypatch)
    assert client.get("/pdf", query_string={"url": LETTER.url}, headers=HEADERS).status_code == 502
