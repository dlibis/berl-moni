import os
import re

import requests
from flask import Blueprint, Response, jsonify, request

auth_proxy_bp = Blueprint("auth_proxy", __name__, url_prefix="/api/auth")

FORWARDED = ("Cookie", "Origin", "Content-Type", "User-Agent")
DOMAIN = re.compile(r";\s*Domain=[^;]*", re.IGNORECASE)


@auth_proxy_bp.route("/<path:rest>", methods=["GET", "POST"])
def proxy(rest):
    url = f"{os.environ['NEON_AUTH_BASE_URL'].rstrip('/')}/{rest}"
    if request.query_string:
        url += "?" + request.query_string.decode()
    try:
        upstream = requests.request(
            request.method, url, data=request.get_data(),
            headers={name: request.headers[name] for name in FORWARDED if name in request.headers},
            timeout=5, allow_redirects=False)
    except requests.RequestException:
        return jsonify({"error": "authentication unavailable"}), 503
    if upstream.status_code >= 500:
        return jsonify({"error": "authentication unavailable"}), 503
    response = Response(upstream.content, upstream.status_code, content_type=upstream.headers.get("Content-Type"))
    for cookie in upstream.raw.headers.getlist("Set-Cookie"):
        response.headers.add("Set-Cookie", DOMAIN.sub("", cookie))
    return response
