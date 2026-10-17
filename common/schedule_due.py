"""due_day(): is a send due now? Stdlib + psycopg only (plan: T2, Data > Schedule shape)."""
import os
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

ISRAEL = ZoneInfo("Asia/Jerusalem")
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]  # date.weekday() order
WAIT_FOR_PERSON = ("send_run_stuck", "missing_settings", "list_over_cap")


def day_time(schedule: list, day: date) -> time | None:
    """The send time on `day` if a range covers it and its weekday is enabled, else None."""
    for r in schedule:
        if date.fromisoformat(r["from"]) <= day <= date.fromisoformat(r["to"]):
            slot = r.get("days", {}).get(DAY_KEYS[day.weekday()])
            if slot and slot.get("enabled"):
                return time.fromisoformat(slot["time"])
    return None


def due_day(now_utc: datetime, schedule: list, conn) -> date | None:
    """Today's Israel date if a send is due now, else None."""
    local = now_utc.astimezone(ISRAEL)
    today = local.date()
    at = day_time(schedule, today)
    if at is None or local.time() < at:
        return None
    if conn.execute("SELECT 1 FROM send_runs WHERE day = %s AND status IN ('sending', 'sent', 'abandoned')",
                    (today,)).fetchone():
        return None
    if conn.execute("SELECT 1 FROM scans WHERE day = %s AND reason = ANY(%s)",
                    (today, list(WAIT_FOR_PERSON))).fetchone():
        return None
    return today


def resume_requested(conn) -> bool:
    """True if a person pressed resume on a run that is still `sending`."""
    return conn.execute("SELECT 1 FROM send_runs WHERE status = 'sending' AND resume_requested_at IS NOT NULL").fetchone() is not None


def main() -> None:
    """Prints exactly due=true or due=false, for `>> $GITHUB_OUTPUT` in letters.yml."""
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'schedule'").fetchone()
        schedule = row["value"] if row else []
        due = due_day(datetime.now(timezone.utc), schedule, conn) is not None or resume_requested(conn)
    print(f"due={str(due).lower()}")


if __name__ == "__main__":
    main()
