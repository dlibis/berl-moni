import hashlib
from pathlib import Path

import pytest

from bot.adapters.letter_pdf import download
from bot.domain.errors import ExtractionError


class Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.data


def test_non_pdf_response_is_rejected_before_caching(tmp_path, monkeypatch):
    monkeypatch.setattr(download.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(download.urllib.request, "urlopen", lambda *args, **kwargs: Response(b"<html>error</html>"))
    url = "https://example.test/letter.pdf"

    with pytest.raises(ExtractionError):
        download.local_copy(url)

    cache_file = tmp_path / "moni_letter_pdfs" / (hashlib.sha256(url.encode()).hexdigest() + ".pdf")
    assert not cache_file.exists()


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
