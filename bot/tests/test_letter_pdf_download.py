import hashlib
import logging
from pathlib import Path

import pytest

from bot.adapters.letter_pdf import download
from bot.domain.errors import DownloadError, ExtractionError


class Response:
    def __init__(self, data):
        self.data = data
        self.status = 200
        self.headers = {"Content-Type": "application/pdf" if data.startswith(b"%PDF-") else "text/html"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.data


def test_non_pdf_response_is_rejected_before_caching(tmp_path, monkeypatch):
    attempts, sleeps = [], []

    def invalid_response(*args, **kwargs):
        attempts.append(1)
        return Response(b"<html>error</html>")

    monkeypatch.setattr(download.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(download.urllib.request, "urlopen", invalid_response)
    monkeypatch.setattr(download.time, "sleep", sleeps.append)
    url = "https://example.test/letter.pdf"

    with pytest.raises(ExtractionError):
        download.local_copy(url)

    cache_file = tmp_path / "moni_letter_pdfs" / (hashlib.sha256(url.encode()).hexdigest() + ".pdf")
    assert not cache_file.exists()
    assert len(attempts) == 4 and sleeps == [1, 2, 4]


def test_non_pdf_response_retries_then_caches_only_the_pdf(tmp_path, monkeypatch, caplog):
    responses = iter([Response(b"<html>challenge-secret</html>"), Response(b"%PDF-1.7\n")])
    sleeps = []
    monkeypatch.setattr(download.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(download.urllib.request, "urlopen", lambda *a, **k: next(responses))
    monkeypatch.setattr(download.time, "sleep", sleeps.append)

    with caplog.at_level(logging.INFO):
        path = download.local_copy("https://example.test/letter.pdf")

    assert Path(path).read_bytes() == b"%PDF-1.7\n"
    assert sleeps == [1]
    assert "attempt 1/4: status=200 content_type='text/html' bytes=29 pdf_signature=False" in caplog.text
    assert "attempt 2/4: status=200 content_type='application/pdf' bytes=9 pdf_signature=True" in caplog.text
    assert "challenge-secret" not in caplog.text


def test_invalid_cached_bytes_are_replaced(tmp_path, monkeypatch):
    monkeypatch.setattr(download.tempfile, "gettempdir", lambda: str(tmp_path))
    url = "https://example.test/letter.pdf"
    cache_dir = tmp_path / "moni_letter_pdfs"
    cache_dir.mkdir()
    cache_file = cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".pdf")
    cache_file.write_bytes(b"not a pdf")
    monkeypatch.setattr(download, "_download", lambda source: b"%PDF-1.7\n")

    assert Path(download.local_copy(url)) == cache_file
    assert cache_file.read_bytes().startswith(b"%PDF-")


def test_valid_cached_bytes_are_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(download.tempfile, "gettempdir", lambda: str(tmp_path))
    url = "https://example.test/letter.pdf"
    cache_dir = tmp_path / "moni_letter_pdfs"
    cache_dir.mkdir()
    cache_file = cache_dir / (hashlib.sha256(url.encode()).hexdigest() + ".pdf")
    cache_file.write_bytes(b"%PDF-1.7 cached")

    def unexpected_download(*args, **kwargs):
        raise AssertionError("downloaded")

    monkeypatch.setattr(download.urllib.request, "urlopen", unexpected_download)

    assert Path(download.local_copy(url)) == cache_file


def test_transient_network_error_retries(monkeypatch):
    attempts = []
    sleeps = []

    def retrying_download(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise download.urllib.error.URLError("temporary")
        return Response(b"%PDF-1.7\n")

    monkeypatch.setattr(download.urllib.request, "urlopen", retrying_download)
    monkeypatch.setattr(download.time, "sleep", sleeps.append)

    assert download._download("https://example.test/letter.pdf") == b"%PDF-1.7\n"
    assert len(attempts) == 2 and sleeps == [1]


def test_network_failure_after_all_retries_is_a_download_error(monkeypatch):
    def unavailable(*args, **kwargs):
        raise download.urllib.error.HTTPError("https://example.test/letter.pdf", 503, "unavailable", {}, None)

    monkeypatch.setattr(download.urllib.request, "urlopen", unavailable)
    monkeypatch.setattr(download.time, "sleep", lambda seconds: None)

    with pytest.raises(DownloadError) as exc:
        download._download("https://example.test/letter.pdf")

    assert exc.value.status == 503


def test_israeli_pdf_request_keeps_original_cache_key_and_retries(tmp_path, monkeypatch):
    from bot.adapters.knesset.remote import KnessetClient
    url = "https://fs.knesset.gov.il/globaldocs/FINANCE/example.pdf"
    attempts = []
    sleeps = []
    monkeypatch.setattr(download.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(download.time, "sleep", sleeps.append)
    def fetch(request, **kwargs):
        attempts.append(request)
        return Response(b"<html>blocked</html>" if len(attempts) == 1 else b"%PDF-1.7\n")
    monkeypatch.setattr(download.urllib.request, "urlopen", fetch)
    path = download.local_copy(url, request_for=KnessetClient("https://fetch.example", "test-token").pdf_request)
    assert Path(path).name == hashlib.sha256(url.encode()).hexdigest() + ".pdf"
    assert Path(path).read_bytes() == b"%PDF-1.7\n" and sleeps == [1]
    assert attempts[0].get_header("Authorization") == "Bearer test-token"
    assert attempts[0].full_url.startswith("https://fetch.example/pdf?url=")
