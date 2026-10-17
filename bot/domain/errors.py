"""The failures the use cases tell apart. Adapters raise them; the service layer maps them to a
`letters.reason` / `scans.reason`, so it never imports an adapter to catch one."""


class ExtractionError(ValueError):
    """The letter can't be read reliably (missing heading, empty required field, bad arithmetic)."""


class NoTextError(ValueError):
    """No text layer, and OCR found no text either."""


class DownloadError(RuntimeError):
    """The PDF could not be downloaded after every retry. `status` is the last HTTP status, or
    None when no response came back (DNS, refused, timeout)."""

    def __init__(self, url: str, attempts: int, last_error: Exception | None):
        super().__init__(f"Failed to download {url} after {attempts} attempts: {last_error}")
        code = getattr(last_error, "code", None)
        self.status = code if isinstance(code, int) else None


class FeedUnreachable(Exception):
    """The Knesset feed could not be read completely (network, HTTP error, or a malformed page)."""


class ResendError(RuntimeError):
    """A failed send. `status` is the HTTP status (None if no response); the message holds only the
    Resend error name or the exception class."""

    def __init__(self, status: int | None, name: str):
        super().__init__(f"Resend {status}: {name}" if status else f"Resend: {name}")
        self.status = status
        self.name = name
