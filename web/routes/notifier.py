import re

from flask import Blueprint, jsonify, request

from common.db import connect, get_setting, set_setting
from web.auth import require_session

notifier_bp = Blueprint("notifier", __name__, url_prefix="/api/v1/notifier")
LOCAL_RE = re.compile(r"^[a-z0-9._%+-]+$")


def _address(value, sender=False):
    value = value.strip().lower() if isinstance(value, str) else ""
    if value.count("@") != 1:
        return None
    local, domain = value.split("@")
    if not LOCAL_RE.fullmatch(local) or (domain != "berl.site" if sender else "." not in domain):
        return None
    return value


@notifier_bp.get("")
@require_session
def get_notifier():
    with connect() as conn:
        result = {"from_address": get_setting(conn, "from_address", ""), "reply_to_address": get_setting(conn, "reply_to_address", "")}
    return jsonify(result)


@notifier_bp.post("")
@require_session
def set_notifier():
    data = request.get_json(silent=True) or {}
    sender = _address(data.get("from_address"), sender=True)
    reply_to = _address(data.get("reply_to_address"))
    if sender is None or reply_to is None:
        return jsonify({"error": "invalid address"}), 400
    with connect() as conn:
        set_setting(conn, "from_address", sender)
        set_setting(conn, "reply_to_address", reply_to)
    return jsonify({"from_address": sender, "reply_to_address": reply_to})
