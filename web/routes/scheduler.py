"""Lightweight admission for the hourly Neon trigger; no worker dependencies."""
import hmac
import os
from datetime import timezone

import psycopg
from flask import Blueprint, current_app, jsonify, request

from common.db import connect, get_setting, set_setting
from common.schedule_due import eligibility
from web import bootstrap

scheduler_bp = Blueprint("scheduler", __name__, url_prefix="/api/internal/scheduler")
LAST_DISPATCH = "scheduler_last_dispatched_hour"


@scheduler_bp.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@scheduler_bp.get("/tick")
def tick():
    secret = os.environ.get("SCHEDULER_SECRET")
    if not secret:
        return jsonify({"error": "scheduler_unconfigured"}), 503
    expected = f"Bearer {secret}".encode()
    if not hmac.compare_digest(request.headers.get("Authorization", "").encode(), expected):
        return jsonify({"error": "unauthorized"}), 401
    try:
        with connect() as conn:
            conn.execute("SET LOCAL lock_timeout = '5s'")
            conn.execute("SELECT pg_advisory_xact_lock(hashtext('berl-moni:scheduler'))")
            now = conn.execute("SELECT clock_timestamp() AS now").fetchone()["now"]
            hour = now.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat()
            if get_setting(conn, LAST_DISPATCH) == hour:
                outcome = "already_dispatched"
            elif not any(eligibility(conn, now)):
                outcome = "idle"
            elif not bootstrap.dispatch():
                current_app.logger.warning("scheduler dispatch_failed")
                return jsonify({"error": "dispatch_failed"}), 503
            else:
                # shortcut: dispatch and commit are not atomic, add an outbox if redundant runs become costly.
                set_setting(conn, LAST_DISPATCH, hour)
                outcome = "dispatched"
    except psycopg.Error:
        current_app.logger.warning("scheduler database_failed")
        return jsonify({"error": "database_failed"}), 503
    print(f"scheduler {hour} {outcome}", flush=True)
    return jsonify({"status": outcome})
