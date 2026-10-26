import re

from flask import Blueprint, jsonify, request
from psycopg.errors import UniqueViolation

from common.db import add_subscriber, connect, get_setting, list_subscribers, remove_email
from common.limits import list_cap
from web.auth import require_session

mailing_list_bp = Blueprint("mailing_list", __name__, url_prefix="/api/v1/mailing_list")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
LOCK_KEY = 73421


def _email(value):
    value = value.strip().lower() if isinstance(value, str) else ""
    return value if EMAIL_RE.fullmatch(value) else None


def _name(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def _cap(conn):
    return list_cap(int(get_setting(conn, "resend_daily_limit", 100)) - int(get_setting(conn, "resend_reserve", 5)))


@mailing_list_bp.get("")
@require_session
def get_mailing_list():
    with connect() as conn:
        subscribers = list_subscribers(conn)
        cap = _cap(conn)
    return jsonify({"subscribers": subscribers, "count": len(subscribers), "cap": cap})


@mailing_list_bp.post("")
@require_session
def add_mailing_list_email():
    body = request.get_json(silent=True) or {}
    email = _email(body.get("email"))
    name = _name(body.get("name"))
    if email is None:
        return jsonify({"error": "invalid email"}), 400
    if name is None:
        return jsonify({"error": "invalid name"}), 400
    try:
        with connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_KEY,))
            count = conn.execute("SELECT count(*) AS count FROM mailing_list").fetchone()["count"]
            if count >= _cap(conn):
                return jsonify({"error": "mailing list is at capacity"}), 400
            add_subscriber(conn, email, name)
    except UniqueViolation:
        return jsonify({"error": "email exists"}), 400
    return jsonify({"email": email, "name": name}), 201


@mailing_list_bp.delete("")
@require_session
def delete_mailing_list_email():
    email = _email((request.get_json(silent=True) or {}).get("email"))
    if email is None:
        return jsonify({"error": "invalid email"}), 400
    with connect() as conn:
        changed = remove_email(conn, email)
    return (jsonify({"status": "ok"}), 200) if changed else (jsonify({"error": "not found"}), 404)
