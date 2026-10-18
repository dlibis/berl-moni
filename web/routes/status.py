from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify

from common.db import connect, get_setting
from common.schedule_due import ISRAEL, day_time
from web.auth import require_session

status_bp = Blueprint("status", __name__, url_prefix="/api/v1/status")


def _json(row):
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()} if row else None


@status_bp.get("")
@require_session
def get_status():
    with connect() as conn:
        scan = conn.execute("SELECT * FROM scans ORDER BY ran_at DESC LIMIT 1").fetchone()
        run = conn.execute("SELECT id, day, failed_at, error, batches, recipients FROM send_runs WHERE status = 'failed' ORDER BY failed_at DESC LIMIT 1").fetchone()
        schedule = get_setting(conn, "schedule", [])
        sent = conn.execute("SELECT count(*) AS count FROM email_log WHERE idempotency_key LIKE %s", (f"run{run['id']}-%",)).fetchone()["count"] if run else 0
    next_day = None
    today = datetime.now(ISRAEL).date()
    for delta in range(367):
        candidate = today + timedelta(days=delta)
        if day_time(schedule, candidate) is not None:
            next_day = candidate.isoformat()
            break
    failed_run = None
    if run:
        recipients = len(run["recipients"] or [])
        chunks = (recipients + 48) // 49
        total = len(run["batches"] or []) * chunks
        failed_run = {"id": run["id"], "day": run["day"].isoformat(), "failed_at": run["failed_at"].isoformat(), "error": run["error"], "sent_messages": sent, "unsent_messages": max(total - sent, 0), "keys_expired": (datetime.now(timezone.utc) - run["failed_at"]).total_seconds() > 86400}
    return jsonify({"latest_scan": _json(scan), "next_scheduled_send_day": next_day, "failed_send_run": failed_run})
