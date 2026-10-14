from flask import Blueprint, jsonify

from common.db import connect
from web.auth import require_session

recovery_bp = Blueprint("recovery", __name__, url_prefix="/api/v1")


@recovery_bp.post("/letters/<slug>/retry")
@require_session
def retry_letter(slug):
    with connect() as conn:
        row = conn.execute("DELETE FROM letters WHERE slug = %s AND status = 'failed' RETURNING slug", (slug,)).fetchone()
    return (jsonify({"status": "ok"}), 200) if row else (jsonify({"error": "conflict"}), 409)


@recovery_bp.post("/send-runs/<int:run_id>/resume")
@require_session
def resume_run(run_id):
    with connect() as conn:
        row = conn.execute("UPDATE send_runs SET resume_requested_at = now(), status = 'sending' WHERE id = %s AND status = 'failed' AND failed_at >= now() - interval '24 hours' RETURNING id", (run_id,)).fetchone()
    return (jsonify({"status": "ok"}), 200) if row else (jsonify({"error": "conflict"}), 409)


@recovery_bp.post("/send-runs/<int:run_id>/abandon")
@require_session
def abandon_run(run_id):
    with connect() as conn:
        row = conn.execute("UPDATE send_runs SET status = 'abandoned', recipients = NULL WHERE id = %s AND status = 'failed' RETURNING id", (run_id,)).fetchone()
    return (jsonify({"status": "ok"}), 200) if row else (jsonify({"error": "conflict"}), 409)
