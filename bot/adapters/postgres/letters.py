"""LettersRepository: the `letters` table — one row per feed letter, with its feed metadata, the saved
analysis (extraction JSON) and a delivery summary. Legacy rows keep their status and summary PDF.

It is also the analysis queue: `analysis_status` is the state, and a worker holds a letter through a
30-minute lease (`lease_id`); only the lease holder may write the result."""
import hashlib
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from bot.domain.feed import FeedLetter


def slug_for(url: str) -> str:
    """Stable unique slug for a letter URL (letters.slug is NOT NULL UNIQUE)."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


class LettersRepository:
    def __init__(self, conn):
        self.conn = conn

    def auto_eligible(self, auto_since: str | None) -> list[str]:
        """What the auto job sends: analyzed, complete, relevant to the current programs, never sent, and
        first seen at or after `auto_since` (None: any time). Oldest first; letter_url breaks ties."""
        return [r["letter_url"] for r in self.conn.execute(
            "SELECT letter_url FROM letters WHERE analysis_status = 'analyzed' AND send_count = 0 "
            "AND jsonb_typeof(extraction->'fields') = 'object' AND codes && ARRAY(SELECT code FROM programs) "
            "AND first_seen_at >= coalesce(%s::timestamptz, '-infinity') ORDER BY first_seen_at, letter_url",
            (auto_since,))]

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

    def mark_sent(self, urls, run_id: int) -> None:
        """The pending letters among `urls` -> sent by run `run_id`."""
        self.conn.execute("UPDATE letters SET status = 'sent', sent_at = now(), send_run_id = %s "
                          "WHERE status = 'pending' AND letter_url = ANY(%s)", (run_id, list(urls)))

    def upsert_feed(self, letters: list[FeedLetter], auto: bool) -> int:
        """Insert unknown letters (`queued` if auto, else `discovered`); refresh the feed metadata of
        known ones. Returns the number inserted."""
        inserted = 0
        for letter in letters:
            row = self.conn.execute(
                "INSERT INTO letters (letter_url, slug, analysis_status, letter_date, ministry, request_numbers, "
                "feed_rows, last_seen_in_feed_at) VALUES (%s, %s, %s, %s, %s, %s, %s, now()) "
                "ON CONFLICT (letter_url) DO UPDATE SET letter_date = EXCLUDED.letter_date, "
                "ministry = EXCLUDED.ministry, request_numbers = EXCLUDED.request_numbers, "
                "feed_rows = EXCLUDED.feed_rows, last_seen_in_feed_at = now() "
                "RETURNING xmax = 0 AS inserted",
                (letter.url, slug_for(letter.url), "queued" if auto else "discovered", letter.letter_date,
                 letter.ministry, list(letter.request_numbers), Jsonb(list(letter.rows)))).fetchone()
            inserted += row["inserted"]
        return inserted

    def get(self, slug: str) -> dict | None:
        return self.conn.execute("SELECT * FROM letters WHERE slug = %s", (slug,)).fetchone()

    def queue(self, slug: str, user: str | None, allowed: tuple[str, ...]) -> bool:
        """-> queued, only from one of the `allowed` analysis statuses."""
        return self.conn.execute(
            "UPDATE letters SET analysis_status = 'queued', analysis_requested_by = %s, attempts = 0 "
            "WHERE slug = %s AND analysis_status = ANY(%s)", (user, slug, list(allowed))).rowcount == 1

    def requeue_expired(self, max_attempts: int = 3) -> int:
        """Expired leases go back to `queued`; after `max_attempts` they fail with `lease_expired`
        (an older extraction keeps the letter `analyzed`, as in fail_analysis)."""
        return self.conn.execute(
            "UPDATE letters SET analysis_status = CASE WHEN attempts < %(max)s THEN 'queued' "
            "  WHEN extraction IS NOT NULL THEN 'analyzed' ELSE 'failed' END, "
            "last_error = CASE WHEN attempts < %(max)s THEN last_error ELSE 'lease_expired' END, "
            "last_error_at = CASE WHEN attempts < %(max)s THEN last_error_at ELSE now() END, "
            "lease_id = NULL, lease_expires_at = NULL "
            "WHERE analysis_status = 'analyzing' AND lease_expires_at < now()", {"max": max_attempts}).rowcount

    def claim(self) -> dict | None:
        """Take the oldest queued letter under a new 30-minute lease; None when nothing is queued.
        Commit right away: no transaction stays open while the letter is analyzed."""
        return self.conn.execute(
            "UPDATE letters SET analysis_status = 'analyzing', lease_id = %s, "
            "lease_expires_at = now() + interval '30 minutes', attempts = attempts + 1 "
            "WHERE letter_url = (SELECT letter_url FROM letters WHERE analysis_status = 'queued' "
            "                    ORDER BY first_seen_at, letter_url LIMIT 1 FOR UPDATE SKIP LOCKED) "
            "RETURNING *", (uuid4(),)).fetchone()

    def finish_analysis(self, url: str, lease_id: UUID, extraction: dict, version: str, codes: list[str],
                        sha256: str, size: int) -> bool:
        """Save the result, only if `lease_id` still holds the letter."""
        return self.conn.execute(
            "UPDATE letters SET analysis_status = 'analyzed', extraction = %s, extraction_version = %s, codes = %s, "
            "source_sha256 = %s, source_size = %s, analyzed_at = now(), last_error = NULL, last_error_at = NULL, "
            "lease_id = NULL, lease_expires_at = NULL WHERE letter_url = %s AND lease_id = %s",
            (Jsonb(extraction), version, codes, sha256, size, url, lease_id)).rowcount == 1

    def fail_analysis(self, url: str, lease_id: UUID, reason: str) -> bool:
        """Record a failed attempt; an older extraction keeps the letter `analyzed`."""
        return self.conn.execute(
            "UPDATE letters SET analysis_status = CASE WHEN extraction IS NOT NULL THEN 'analyzed' ELSE 'failed' END, "
            "last_error = %s, last_error_at = now(), lease_id = NULL, lease_expires_at = NULL "
            "WHERE letter_url = %s AND lease_id = %s", (reason, url, lease_id)).rowcount == 1

    def has_queued(self) -> bool:
        """Whether a worker has anything to do: a queued letter or an expired lease."""
        return self.conn.execute(
            "SELECT EXISTS (SELECT 1 FROM letters WHERE analysis_status = 'queued' "
            "OR (analysis_status = 'analyzing' AND lease_expires_at < now())) AS queued").fetchone()["queued"]

    def mark_delivered(self, urls: list[str]) -> None:
        self.conn.execute("UPDATE letters SET last_sent_at = now(), send_count = send_count + 1 "
                          "WHERE letter_url = ANY(%s)", (urls,))
