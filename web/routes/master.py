import re

from flask import Blueprint, jsonify, request
from psycopg.errors import UniqueViolation

from common.db import connect
from web.auth import require_session

master_bp = Blueprint("master", __name__, url_prefix="/api/v1/master")
CODE_RE = re.compile(r"^[0-9]{1,6}$")


def _code(value):
    return value.zfill(6) if isinstance(value, str) and CODE_RE.fullmatch(value) else None


@master_bp.get("")
@require_session
def get_master():
    with connect() as conn:
        rows = list(conn.execute("SELECT code, name FROM programs ORDER BY code"))
    return jsonify({"programs": rows})


@master_bp.post("")
@require_session
def add_program():
    data = request.get_json(silent=True) or {}
    code, name = _code(data.get("code")), data.get("name")
    if code is None or not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid program"}), 400
    try:
        with connect() as conn:
            conn.execute("INSERT INTO programs (code, name) VALUES (%s, %s)", (code, name.strip()))
    except UniqueViolation:
        return jsonify({"error": "code exists"}), 400
    return jsonify({"code": code, "name": name.strip()}), 201


@master_bp.put("/<old_code>")
@require_session
def update_program(old_code):
    data = request.get_json(silent=True) or {}
    old, code, name = _code(old_code), _code(data.get("code")), data.get("name")
    if old is None or code is None or not isinstance(name, str) or not name.strip():
        return jsonify({"error": "invalid program"}), 400
    try:
        with connect() as conn:
            row = conn.execute("UPDATE programs SET code = %s, name = %s WHERE code = %s RETURNING code", (code, name.strip(), old)).fetchone()
    except UniqueViolation:
        return jsonify({"error": "code exists"}), 400
    return (jsonify({"code": code, "name": name.strip()}), 200) if row else (jsonify({"error": "not found"}), 404)


@master_bp.delete("/<code>")
@require_session
def delete_program(code):
    code = _code(code)
    if code is None:
        return jsonify({"error": "invalid program"}), 400
    with connect() as conn:
        changed = conn.execute("DELETE FROM programs WHERE code = %s", (code,)).rowcount
    return (jsonify({"status": "ok"}), 200) if changed else (jsonify({"error": "not found"}), 404)
