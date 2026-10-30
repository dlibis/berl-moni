"""due_day(): is a send due now? Stdlib + psycopg only (plan: T2, Data > Schedule shape)."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ISRAEL = ZoneInfo("Asia/Jerusalem")
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]  # date.weekday() order
WAIT_FOR_PERSON = ("send_run_stuck", "missing_settings", "list_over_cap")
FETCH_HOURS = (1, 6, 24)


def day_time(schedule: list, day: date) -> time | None:
    """The send time on `day` if a range covers it and its weekday is enabled, else None."""
    for r in schedule:
        if date.fromisoformat(r["from"]) <= day <= date.fromisoformat(r["to"]):
            slot = r.get("days", {}).get(DAY_KEYS[day.weekday()])
            if slot and slot.get("enabled"):
                return time.fromisoformat(slot["time"])
    return None


def schedule_configured(schedule: list) -> bool:
    """True if some range has not ended (Israel date) and enables at least one weekday."""
    today = datetime.now(ISRAEL).date()
    return any(date.fromisoformat(r["to"]) >= today and any(d.get("enabled") for d in r.get("days", {}).values())
               for r in schedule)


def due_day(now_utc: datetime, schedule: list, conn, always_send: bool = False) -> date | None:
    """Today's Israel date if a send is due now, else None."""
    if always_send:
        return None
    local = now_utc.astimezone(ISRAEL)
    today = local.date()
    at = day_time(schedule, today)
    if at is None or local.time() < at:
        return None
    for r in schedule:
        limit = r.get("count")
        if not isinstance(limit, int):
            continue
        row = conn.execute(
            "SELECT count(*) AS n FROM send_runs WHERE kind = 'auto' AND status IN ('sending', 'sent', 'abandoned') AND day >= %s",
            (r["from"],),
        ).fetchone() or {}
        if row.get("n", 0) >= limit:
            return None
    if conn.execute("SELECT 1 FROM send_runs WHERE day = %s AND kind = 'auto' AND status IN ('sending', 'sent', 'abandoned')",
                    (today,)).fetchone():
        return None
    if conn.execute("SELECT 1 FROM scans WHERE day = %s AND reason = ANY(%s)",
                    (today, list(WAIT_FOR_PERSON))).fetchone():
        return None
    return today


def fetch_due(now_utc: datetime, every_hours: int | None, last_at: str | None) -> bool:
    """True if a cadence is set and no feed pull has run within that many hours."""
    if isinstance(every_hours, bool) or every_hours not in FETCH_HOURS:
        return False
    if last_at is None:
        return True
    last = datetime.fromisoformat(last_at)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return now_utc - last >= timedelta(hours=every_hours)


def resume_requested(conn) -> bool:
    """True if a person pressed resume on a run that is still `sending`."""
    return conn.execute("SELECT 1 FROM send_runs WHERE status = 'sending' AND resume_requested_at IS NOT NULL").fetchone() is not None


def has_queued(conn) -> bool:
    """True if a letter waits for analysis or its analysis lease expired (same SQL as LettersRepository.has_queued)."""
    return conn.execute("SELECT EXISTS (SELECT 1 FROM letters WHERE analysis_status = 'queued' "
                        "OR (analysis_status = 'analyzing' AND lease_expires_at < now())) AS queued").fetchone()["queued"]


def eligibility(conn, now: datetime) -> tuple[bool, bool]:
    """Return (scheduled work due, analysis queued) for both admission paths."""
    from common.always_send_due import due_always_send

    row = conn.execute("SELECT value FROM settings WHERE key = 'schedule'").fetchone()
    schedule = row["value"] if row else []
    always_row = conn.execute("SELECT value FROM settings WHERE key = 'always_send'").fetchone()
    always = bool(always_row["value"]) if always_row else False
    hours_row = conn.execute("SELECT value FROM settings WHERE key = 'fetch_every_hours'").fetchone()
    every_hours = hours_row["value"] if hours_row else None
    last_row = conn.execute("SELECT value FROM settings WHERE key = 'last_feed_refresh_at'").fetchone()
    last_at = last_row["value"] if last_row else None
    due = (due_day(now, schedule, conn, always) is not None
           or due_always_send(now, always, conn) is not None or resume_requested(conn)
           or fetch_due(now, every_hours, last_at))
    return due, has_queued(conn)

