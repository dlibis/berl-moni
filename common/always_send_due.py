"""Weekly Always Send (שלח תמיד): Sunday 09:00 Asia/Jerusalem when the setting is on."""
import os
from datetime import date, datetime, time, timezone

import psycopg
from psycopg.rows import dict_row

from common.schedule_due import ISRAEL, WAIT_FOR_PERSON

# Operators: weekly send window (Israel).
ALWAYS_SEND_WEEKDAY = 6  # Sunday (date.weekday())
ALWAYS_SEND_TIME = time(9, 0)


# Spec left Always Send vs custom-range overlap unspecified. This shares
# send_runs_one_auto_per_day with due_day: at most one auto send per Israel day.
def due_always_send(now_utc: datetime, enabled: bool, conn) -> date | None:
    if not enabled:
        return None
    local = now_utc.astimezone(ISRAEL)
    today = local.date()
    if today.weekday() != ALWAYS_SEND_WEEKDAY or local.time() < ALWAYS_SEND_TIME:
        return None
    if conn.execute(
        "SELECT 1 FROM send_runs WHERE day = %s AND kind = 'auto' AND status IN ('sending', 'sent', 'abandoned')",
        (today,),
    ).fetchone():
        return None
    if conn.execute(
        "SELECT 1 FROM scans WHERE day = %s AND reason = ANY(%s)",
        (today, list(WAIT_FOR_PERSON)),
    ).fetchone():
        return None
    return today


def main() -> None:
    """Prints due=<bool> for the weekly GitHub Actions workflow."""
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'always_send'").fetchone()
        enabled = bool(row["value"]) if row else False
        due = due_always_send(datetime.now(timezone.utc), enabled, conn) is not None
    print(f"due={str(due).lower()}")


if __name__ == "__main__":
    main()
