import re
from datetime import date

from flask import Blueprint, jsonify, request

from common.db import connect, get_setting, list_emails, set_setting
from common.limits import projected_monthly_emails
from common.schedule_due import DAY_KEYS
from web.auth import require_session

schedule_bp = Blueprint("schedule", __name__, url_prefix="/api/v1/schedule")
TIME_RE = re.compile(r"^([01][0-9]|2[0-3]):00$")


def _valid(schedule):
    if not isinstance(schedule, list):
        return False
    ranges = []
    for item in schedule:
        if not isinstance(item, dict) or set(item) != {"from", "to", "days"} or not isinstance(item["days"], dict):
            return False
        try:
            start, end = date.fromisoformat(item["from"]), date.fromisoformat(item["to"])
        except (TypeError, ValueError):
            return False
        if start > end or any(key not in DAY_KEYS for key in item["days"]):
            return False
        for value in item["days"].values():
            if not isinstance(value, dict) or set(value) != {"enabled", "time"} or not isinstance(value["enabled"], bool) or not TIME_RE.fullmatch(value["time"] or ""):
                return False
        ranges.append((start, end))
    ranges.sort()
    return all(ranges[i - 1][1] < ranges[i][0] for i in range(1, len(ranges)))


def _month(offset=0):
    today = date.today()
    total = today.year * 12 + today.month - 1 + offset
    return date(total // 12, total % 12 + 1, 1)


@schedule_bp.get("")
@require_session
def get_schedule():
    with connect() as conn:
        schedule = get_setting(conn, "schedule", [])
        count = len(list_emails(conn))
        limit = int(get_setting(conn, "resend_monthly_limit", 3000))
    months = (_month(), _month(1))
    return jsonify({"schedule": schedule, "projected_monthly_emails": {m.isoformat(): projected_monthly_emails(count, schedule, m) for m in months}, "monthly_limit": limit})


@schedule_bp.post("")
@require_session
def set_schedule():
    data = request.get_json(silent=True)
    schedule = data.get("schedule") if isinstance(data, dict) else data
    if not _valid(schedule):
        return jsonify({"error": "invalid schedule"}), 400
    with connect() as conn:
        set_setting(conn, "schedule", schedule)
    return jsonify({"schedule": schedule})
