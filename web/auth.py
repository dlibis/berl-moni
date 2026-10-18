from functools import wraps
import os

import requests
from flask import g, jsonify, request


def require_session(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            response = requests.get(
                f"{os.environ['NEON_AUTH_BASE_URL'].rstrip('/')}/get-session",
                headers={"Cookie": request.headers.get("Cookie", "")}, timeout=5)
        except requests.RequestException:
            return jsonify({"error": "authentication unavailable"}), 503
        if response.status_code >= 500:
            return jsonify({"error": "authentication unavailable"}), 503
        if response.status_code != 200:
            return jsonify({"error": "unauthorized"}), 401
        try:
            data = response.json()
        except ValueError:
            return jsonify({"error": "authentication unavailable"}), 503
        if not isinstance(data, dict) or data.get("session") is None or not isinstance(data.get("user"), dict):
            return jsonify({"error": "unauthorized"}), 401
        g.user = data["user"].get("email") or data["user"].get("id")
        return view(*args, **kwargs)
    return wrapped
