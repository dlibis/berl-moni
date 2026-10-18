from flask import Blueprint, g, jsonify, request

from bot.domain.errors import FeedUnreachable
from bot.service_layer.analysis import refresh_feed, request_analysis
from bot.service_layer.sending import send_letter
from common.db import connect, load_programs
from web import bootstrap
from web.auth import require_session
from web.views.letters import FILTERS, letter_detail, list_letters

letters_bp = Blueprint("letters", __name__, url_prefix="/api/v1/letters")

MAX_PAGE_SIZE = 100


@letters_bp.get("")
@require_session
def get_letters():
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 25))
    except ValueError:
        return jsonify({"error": "invalid query"}), 400
    status = request.args.get("status")
    if page < 1 or not 1 <= page_size <= MAX_PAGE_SIZE or (status is not None and status not in FILTERS):
        return jsonify({"error": "invalid query"}), 400
    with connect() as conn:
        items, total = list_letters(conn, page=page, page_size=page_size, status=status,
                                    programs=list(load_programs(conn)))
    return jsonify({"items": items, "total": total})


@letters_bp.get("/<slug>")
@require_session
def get_letter(slug):
    with connect() as conn:
        letter = letter_detail(conn, slug, load_programs(conn))
    return jsonify(letter) if letter else (jsonify({"error": "not found"}), 404)


@letters_bp.post("/refresh")
@require_session
def refresh():
    with bootstrap.uow() as uow:
        try:
            result = refresh_feed(uow, bootstrap.ports().feed, auto=bool(uow.setting("auto_since")))
        except FeedUnreachable:
            return jsonify({"error": "feed_unreachable"}), 502
    return jsonify({"new": result.new, "seen": result.seen})


def _analyze(slug, reanalyze):
    with bootstrap.uow() as uow:
        outcome, dispatched = request_analysis(uow, slug, g.user, bootstrap.dispatch, reanalyze=reanalyze)
    if outcome == "queued":
        return jsonify({"status": "queued", "dispatch_failed": not dispatched}), 202
    if outcome == "done":
        return jsonify({"status": "done"})
    return (jsonify({"error": "busy"}), 409) if outcome == "busy" else (jsonify({"error": "not found"}), 404)


@letters_bp.post("/<slug>/analyze")
@require_session
def analyze(slug):
    return _analyze(slug, False)


@letters_bp.post("/<slug>/reanalyze")
@require_session
def reanalyze(slug):
    return _analyze(slug, True)


SEND_STATUS = {"not_found": 404, "not_sendable": 409, "confirm_resend": 409, "over_budget": 429,
               "settings": 409, "failed": 502}


@letters_bp.post("/<slug>/send")
@require_session
def send(slug):
    body = request.get_json(silent=True) or {}
    with bootstrap.uow() as uow:
        outcome, detail = send_letter(uow, bootstrap.ports(), slug, g.user, resend=body.get("resend") is True)
    if outcome == "sent":
        return jsonify({"status": "sent"})
    error = detail if outcome in ("settings", "failed") else outcome
    return jsonify({"error": error}), SEND_STATUS[outcome]
