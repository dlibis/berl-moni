import os

from flask import jsonify, request

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def register_csrf(app):
    @app.before_request
    def check_csrf():
        if not request.path.startswith(("/api/v1/", "/api/auth/")) or request.method not in UNSAFE_METHODS:
            return None
        if request.headers.get("Origin") != os.environ["SITE_ORIGIN"]:
            return jsonify({"error": "forbidden"}), 403
        if request.get_data(cache=True) and request.mimetype not in (
            "application/json",
            "multipart/form-data",
        ):
            return jsonify({"error": "forbidden"}), 403
        return None
