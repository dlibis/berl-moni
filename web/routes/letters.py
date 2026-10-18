from flask import Blueprint, jsonify, request

from common.db import connect, load_programs
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
