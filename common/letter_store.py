"""Letters, send runs, email log, and scans in Neon. Every function takes an open connection; the caller commits."""
import hashlib

from psycopg.types.json import Jsonb


def slug_for(url: str) -> str:
    """Stable unique slug for a letter URL (letters.slug is NOT NULL UNIQUE)."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def known_urls(conn) -> set[str]:
    return {r["letter_url"] for r in conn.execute("SELECT letter_url FROM letters")}


def insert_letter_result(conn, url: str, status: str, reason: str | None = None,
                         pdf: bytes | None = None, pdf_bytes: int | None = None, slug: str | None = None) -> None:
    """One row per scanned letter. `pdf` is the rendered summary; pdf_bytes defaults to its length."""
    if pdf_bytes is None and pdf is not None:
        pdf_bytes = len(pdf)
    conn.execute("INSERT INTO letters (letter_url, slug, status, reason, summary_pdf, pdf_bytes) "
                 "VALUES (%s, %s, %s, %s, %s, %s)",
                 (url, slug or slug_for(url), status, reason, pdf, pdf_bytes))


def mark_seen(conn, urls) -> None:
    """Record feed URLs as already sent, without scanning them."""
    conn.cursor().executemany("INSERT INTO letters (letter_url, slug, status, sent_at) VALUES (%s, %s, 'sent', now()) "
                              "ON CONFLICT (letter_url) DO NOTHING", [(u, slug_for(u)) for u in urls])


def pending_letters(conn) -> list[dict]:
    """Pending letters, oldest first; letter_url breaks ties between letters scanned in the same second.
    No PDF bytes: load them per batch with load_pdfs()."""
    return list(conn.execute("SELECT letter_url, slug, pdf_bytes, scanned_at FROM letters "
                             "WHERE status = 'pending' ORDER BY scanned_at, letter_url"))


def load_pdfs(conn, urls) -> list[bytes]:
    """Summary PDFs in the order of `urls`."""
    rows = {r["letter_url"]: bytes(r["summary_pdf"]) for r in conn.execute(
        "SELECT letter_url, summary_pdf FROM letters WHERE letter_url = ANY(%s)", (list(urls),))}
    return [rows[u] for u in urls]


def mark_letter_failed(conn, url: str, reason: str) -> None:
    """Take a letter out of the send set (e.g. a PDF over the batch limit)."""
    conn.execute("UPDATE letters SET status = 'failed', reason = %s, summary_pdf = NULL, pdf_bytes = NULL "
                 "WHERE letter_url = %s", (reason, url))


def send_run_open(conn) -> dict | None:
    """The run in state sending or failed, if any."""
    return conn.execute("SELECT * FROM send_runs WHERE status IN ('sending', 'failed') "
                        "ORDER BY id DESC LIMIT 1").fetchone()


def start_send_run(conn, day, from_address: str, reply_to_address: str, recipients: list[str],
                   batches: list[list[str]]) -> int:
    return conn.execute(
        "INSERT INTO send_runs (day, status, from_address, reply_to_address, recipients, batches) "
        "VALUES (%s, 'sending', %s, %s, %s, %s) RETURNING id",
        (day, from_address, reply_to_address, Jsonb(recipients), Jsonb(batches))).fetchone()["id"]


def lock_run(conn, run_id: int) -> str | None:
    """Re-read the run FOR UPDATE and return its status (None if it does not exist)."""
    row = conn.execute("SELECT status FROM send_runs WHERE id = %s FOR UPDATE", (run_id,)).fetchone()
    return row and row["status"]


def mark_run_failed(conn, run_id: int, error: str) -> None:
    """`error` is Resend's error name or an exception class, never a body."""
    conn.execute("UPDATE send_runs SET status = 'failed', failed_at = now(), error = %s WHERE id = %s",
                 (error, run_id))


def clear_resume_request(conn, run_id: int) -> None:
    conn.execute("UPDATE send_runs SET resume_requested_at = NULL WHERE id = %s", (run_id,))


def finish_run(conn, run_id: int) -> bool:
    """Run -> sent, its letters -> sent, recipients wiped. False (nothing written) if the run is no longer sending."""
    done = conn.execute("UPDATE send_runs SET status = 'sent', finished_at = now(), recipients = NULL "
                        "WHERE id = %s AND status = 'sending'", (run_id,)).rowcount
    if done:
        conn.execute("UPDATE letters SET status = 'sent', sent_at = now(), send_run_id = %s "
                     "WHERE status = 'pending' AND letter_url IN ("
                     "SELECT jsonb_array_elements_text(b) FROM send_runs, jsonb_array_elements(batches) b "
                     "WHERE id = %s)", (run_id, run_id))
    return bool(done)


def log_email(conn, key: str, kind: str, emails: int) -> None:
    conn.execute("INSERT INTO email_log (idempotency_key, emails, kind) VALUES (%s, %s, %s) "
                 "ON CONFLICT DO NOTHING", (key, emails, kind))


def sent_keys(conn, run_id: int) -> set[str]:
    """Idempotency keys already logged for this run's letter messages."""
    return {r["idempotency_key"] for r in conn.execute(
        "SELECT idempotency_key FROM email_log WHERE idempotency_key LIKE %s", (f"run{run_id}-b%",))}


def email_counts(conn) -> tuple[int, int]:
    """Emails logged since the start of the current UTC day and the current UTC month."""
    row = conn.execute(
        "SELECT coalesce(sum(emails) FILTER (WHERE sent_at >= date_trunc('day', now() AT TIME ZONE 'utc') AT TIME ZONE 'utc'), 0) AS day, "
        "coalesce(sum(emails) FILTER (WHERE sent_at >= date_trunc('month', now() AT TIME ZONE 'utc') AT TIME ZONE 'utc'), 0) AS month "
        "FROM email_log").fetchone()
    return int(row["day"]), int(row["month"])


def write_scan(conn, day, status: str, reason: str | None = None, letters_in_feed: int | None = None,
               new_letters: int = 0, relevant: int = 0, failed: int = 0, emails_sent: int = 0) -> None:
    """One scans row per send run: counts only, no addresses."""
    conn.execute("INSERT INTO scans (day, status, reason, letters_in_feed, new_letters, relevant, failed, emails_sent) "
                 "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                 (day, status, reason, letters_in_feed, new_letters, relevant, failed, emails_sent))
