"""LettersRepository: the `letters` table — one row per feed letter the job has seen, with its status
(pending / irrelevant / failed / sent), the failure reason and the rendered summary PDF."""
import hashlib

from bot.domain.statuses import LetterReason, LetterStatus


def slug_for(url: str) -> str:
    """Stable unique slug for a letter URL (letters.slug is NOT NULL UNIQUE)."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


class LettersRepository:
    def __init__(self, conn):
        self.conn = conn

    def known_urls(self) -> set[str]:
        return {r["letter_url"] for r in self.conn.execute("SELECT letter_url FROM letters")}

    def insert(self, url: str, status: LetterStatus, reason: LetterReason | None = None,
               pdf: bytes | None = None, pdf_bytes: int | None = None, slug: str | None = None) -> None:
        """One row per scanned letter. `pdf` is the rendered summary; pdf_bytes defaults to its length."""
        if pdf_bytes is None and pdf is not None:
            pdf_bytes = len(pdf)
        self.conn.execute("INSERT INTO letters (letter_url, slug, status, reason, summary_pdf, pdf_bytes) "
                          "VALUES (%s, %s, %s, %s, %s, %s)",
                          (url, slug or slug_for(url), status, reason, pdf, pdf_bytes))

    def mark_seen(self, urls) -> None:
        """Record feed URLs as already sent, without scanning them."""
        self.conn.cursor().executemany("INSERT INTO letters (letter_url, slug, status, sent_at) VALUES (%s, %s, 'sent', now()) "
                                       "ON CONFLICT (letter_url) DO NOTHING", [(u, slug_for(u)) for u in urls])

    def pending(self) -> list[dict]:
        """Pending letters, oldest first; letter_url breaks ties between letters scanned in the same second.
        No PDF bytes: load them per batch with load_pdfs()."""
        return list(self.conn.execute("SELECT letter_url, slug, pdf_bytes, scanned_at FROM letters "
                                      "WHERE status = 'pending' ORDER BY scanned_at, letter_url"))

    def load_pdfs(self, urls) -> list[bytes]:
        """Summary PDFs in the order of `urls`."""
        rows = {r["letter_url"]: bytes(r["summary_pdf"]) for r in self.conn.execute(
            "SELECT letter_url, summary_pdf FROM letters WHERE letter_url = ANY(%s)", (list(urls),))}
        return [rows[u] for u in urls]

    def load_extractions(self, urls) -> list[dict | None]:
        """Saved extraction JSON in the order of `urls`."""
        rows = {r["letter_url"]: r["extraction"] for r in self.conn.execute(
            "SELECT letter_url, extraction FROM letters WHERE letter_url = ANY(%s)", (list(urls),))}
        return [rows.get(u) for u in urls]

    def mark_failed(self, url: str, reason: LetterReason) -> None:
        """Take a letter out of the send set (e.g. a PDF over the batch limit)."""
        self.conn.execute("UPDATE letters SET status = 'failed', reason = %s, summary_pdf = NULL, pdf_bytes = NULL "
                          "WHERE letter_url = %s", (reason, url))

    def mark_sent(self, urls, run_id: int) -> None:
        """The pending letters among `urls` -> sent by run `run_id`."""
        self.conn.execute("UPDATE letters SET status = 'sent', sent_at = now(), send_run_id = %s "
                          "WHERE status = 'pending' AND letter_url = ANY(%s)", (run_id, list(urls)))

    def mark_delivered(self, urls: list[str]) -> None:
        self.conn.execute("UPDATE letters SET last_sent_at = now(), send_count = send_count + 1 "
                          "WHERE letter_url = ANY(%s)", (urls,))
