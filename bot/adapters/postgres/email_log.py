"""EmailLogRepository: the `email_log` table — one row per message sent (its idempotency key and how
many emails it counted), so a resumed run skips what went out and the daily/monthly budgets hold."""
from bot.domain.statuses import EmailKind


class EmailLogRepository:
    def __init__(self, conn):
        self.conn = conn

    def add(self, key: str, kind: EmailKind, emails: int) -> None:
        self.conn.execute("INSERT INTO email_log (idempotency_key, emails, kind) VALUES (%s, %s, %s) "
                          "ON CONFLICT DO NOTHING", (key, emails, kind))

    def start(self, key: str, kind: EmailKind, emails: int) -> bool:
        row = self.conn.execute(
            "INSERT INTO email_log (idempotency_key, emails, kind, status, started_at) "
            "VALUES (%s, %s, %s, 'sending', now()) ON CONFLICT DO NOTHING RETURNING idempotency_key",
            (key, emails, kind)).fetchone()
        return row is not None

    def complete(self, key: str, resend_email_id: str) -> None:
        self.conn.execute(
            "UPDATE email_log SET status = 'sent', sent_at = now(), resend_email_id = %s "
            "WHERE idempotency_key = %s AND status = 'sending'", (resend_email_id, key))

    def expire_stale(self) -> list[str]:
        return [row["idempotency_key"] for row in self.conn.execute(
            "UPDATE email_log SET status = 'unknown' "
            "WHERE status = 'sending' AND started_at < now() - interval '24 hours' "
            "RETURNING idempotency_key")]

    def sent_keys(self, run_id: int) -> set[str]:
        """Idempotency keys already logged for this run's letter messages."""
        return {r["idempotency_key"] for r in self.conn.execute(
            "SELECT idempotency_key FROM email_log WHERE idempotency_key LIKE %s AND status = 'sent'",
            (f"run{run_id}-b%",))}

    def counts(self) -> tuple[int, int]:
        """Emails logged since the start of the current UTC day and the current UTC month."""
        row = self.conn.execute(
            "SELECT coalesce(sum(emails) FILTER (WHERE coalesce(started_at, sent_at) >= "
            "date_trunc('day', now() AT TIME ZONE 'utc') AT TIME ZONE 'utc'), 0) AS day, "
            "coalesce(sum(emails) FILTER (WHERE coalesce(started_at, sent_at) >= "
            "date_trunc('month', now() AT TIME ZONE 'utc') AT TIME ZONE 'utc'), 0) AS month "
            "FROM email_log").fetchone()
        return int(row["day"]), int(row["month"])
