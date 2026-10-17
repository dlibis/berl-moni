"""Letter PDF download: local_copy(source) gives a local path for a letter PDF. A URL is downloaded
once (with retries) into an on-disk cache and reused on later runs; a local path is returned as is.
Raises DownloadError when every retry fails."""
import hashlib
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from bot.domain.errors import DownloadError



def local_copy(source: str) -> str:
    """The PDF on disk: `source` itself if local, else the cached download (keyed by URL) — the
    download is the slow part, not the parsing."""
    if not source.startswith(("http://", "https://")):
        return source
    cache_dir = Path(tempfile.gettempdir()) / "moni_letter_pdfs"
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / (hashlib.sha256(source.encode()).hexdigest() + ".pdf")
    if not cache_file.exists():
        cache_file.write_bytes(_download(source))
    return str(cache_file)


def save_copy(source: str, dest: Path) -> None:
    """Copy the letter PDF (downloading a URL first) to `dest`, to eyeball it next to its summary."""
    shutil.copyfile(local_copy(source), dest)


def _download(url: str, attempts: int = 4) -> bytes:
    """Download url, retrying with backoff so a transient URLError doesn't abort the run."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
    raise DownloadError(url, attempts, last_error)
