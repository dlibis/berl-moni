"""SendRunsRepository: the `send_runs` table — one row per daily send, holding its sender, recipients
and attachment batches while it is `sending`, and why it stopped if it `failed`."""
from psycopg.types.json import Jsonb

from bot.domain.statuses import SendKind


class SendRunsRepository:
    def __init__(self, conn):
        self.conn = conn

    def find_open(self) -> dict | None:
        """The run in state sending or failed, if any."""
        return self.conn.execute("SELECT * FROM send_runs WHERE status IN ('sending', 'failed') "
                                 "ORDER BY id DESC LIMIT 1").fetchone()

    def start(self, day, from_address: str, reply_to_address: str, recipients: list[str],
              batches: list[list[str]], kind: SendKind = "auto", requested_by: str | None = None) -> int:
        return self.conn.execute(
            "INSERT INTO send_runs "
            "(day, status, from_address, reply_to_address, recipients, batches, kind, requested_by) "
            "VALUES (%s, 'sending', %s, %s, %s, %s, %s, %s) RETURNING id",
            (day, from_address, reply_to_address, Jsonb(recipients), Jsonb(batches), kind,
             requested_by)).fetchone()["id"]

    def get(self, run_id: int) -> dict | None:
        return self.conn.execute("SELECT * FROM send_runs WHERE id = %s", (run_id,)).fetchone()

    def lock_budget(self) -> None:
        self.conn.execute("SELECT pg_advisory_xact_lock(hashtext('letters-send'))")

    def open_for(self, url: str) -> bool:
        """Whether a run that is still sending, or parked failed for a person, carries this letter."""
        return self.conn.execute(
            "SELECT EXISTS (SELECT 1 FROM send_runs WHERE status IN ('sending', 'failed') AND batches @> %s) AS open",
            (Jsonb([[url]]),)).fetchone()["open"]

    def reserved_emails(self) -> int:
        """Emails the `sending` runs will still send: each batch goes to every recipient (49 per message, plus
        the reply-to inbox), minus what email_log already counts for them."""
        return self.conn.execute(
            "SELECT coalesce(sum(greatest(jsonb_array_length(r.batches) * (n + ceil(n / 49.0)) - coalesce("
            "  (SELECT sum(emails) FROM email_log WHERE idempotency_key LIKE 'run' || r.id || '-%%'), 0), 0)), 0)::int "
            "AS reserved FROM send_runs r, jsonb_array_length(coalesce(r.recipients, '[]')) AS n "
            "WHERE r.status = 'sending'").fetchone()["reserved"]

    def lock(self, run_id: int) -> str | None:
        """Re-read the run FOR UPDATE and return its status (None if it does not exist)."""
        row = self.conn.execute("SELECT status FROM send_runs WHERE id = %s FOR UPDATE", (run_id,)).fetchone()
        return row and row["status"]

    def mark_failed(self, run_id: int, error: str) -> None:
        """`error` is Resend's error name or an exception class, never a body."""
        self.conn.execute("UPDATE send_runs SET status = 'failed', failed_at = now(), error = %s WHERE id = %s",
                          (error, run_id))

    def clear_resume_request(self, run_id: int) -> None:
        self.conn.execute("UPDATE send_runs SET resume_requested_at = NULL WHERE id = %s", (run_id,))

    def finish(self, run_id: int) -> bool:
        """Run -> sent, recipients wiped. False (nothing written) if the run is no longer sending."""
        return bool(self.conn.execute("UPDATE send_runs SET status = 'sent', finished_at = now(), recipients = NULL "
                                      "WHERE id = %s AND status = 'sending'", (run_id,)).rowcount)
