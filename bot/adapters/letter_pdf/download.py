"""Letter PDF download: local_copy(source) gives a local path for a letter PDF. A URL is downloaded
once (with retries) into an on-disk cache and reused on later runs; a local path is returned as is.
Raises DownloadError when every retry fails."""
import hashlib
import logging
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from bot.domain.errors import DownloadError, ExtractionError
from bot.domain.slug import letter_slug

logger = logging.getLogger(__name__)


def _is_pdf(data: bytes) -> bool:
    return data.startswith(b"%PDF-")



def local_copy(source: str) -> str:
    """The PDF on disk: `source` itself if local, else the cached download (keyed by URL) — the
    download is the slow part, not the parsing."""
    if not source.startswith(("http://", "https://")):
        return source
    cache_dir = Path(tempfile.gettempdir()) / "moni_letter_pdfs"
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / (hashlib.sha256(source.encode()).hexdigest() + ".pdf")
    if cache_file.exists() and not _is_pdf(cache_file.read_bytes()):
        cache_file.unlink()
    if not cache_file.exists():
        cache_file.write_bytes(_download(source))
    return str(cache_file)


def save_copy(source: str, dest: Path) -> None:
    """Copy the letter PDF (downloading a URL first) to `dest`, to eyeball it next to its summary."""
    shutil.copyfile(local_copy(source), dest)


def _download(url: str, attempts: int = 4) -> bytes:
    """Retry network failures and non-PDF responses with backoff; never cache an error page."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
                logger.info("PDF download %s attempt %d/%d: status=%s content_type=%r bytes=%d pdf_signature=%s",
                            letter_slug(url), attempt + 1, attempts, response.status,
                            response.headers.get("Content-Type"), len(data), _is_pdf(data))
                if not _is_pdf(data):
                    raise ExtractionError(f"Source did not return a PDF: {url}")
                return data
        except (urllib.error.URLError, TimeoutError, ExtractionError) as error:
            last_error = error
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
    if isinstance(last_error, ExtractionError):
        raise last_error
    raise DownloadError(url, attempts, last_error)
