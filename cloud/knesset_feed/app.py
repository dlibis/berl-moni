"""Authenticated, read-only Knesset fetches from Israel; no database or mail credentials."""
import hmac
import os
from dataclasses import asdict
from urllib.parse import urlsplit

import requests
from flask import Flask, Response, jsonify, request

from bot.adapters.knesset.feed import fetch_approvals, fetch_letters
from bot.domain.errors import FeedUnreachable

app = Flask(__name__)
MAX_PDF_BYTES = 64 * 1024 * 1024


@app.before_request
def authenticate():
    token = os.environ.get("KNESSET_FETCH_TOKEN")
    if not token or not hmac.compare_digest(request.headers.get("Authorization", "").encode(), f"Bearer {token}".encode()):
        return jsonify(error="unauthorized"), 401


@app.get("/feed")
def feed():
    try:
        letters = fetch_letters()
    except FeedUnreachable as error:
        app.logger.warning("Knesset feed failed: %s", error)
        return jsonify(error="feed_unreachable"), 502
    response = jsonify([{**asdict(letter), "letter_date": letter.letter_date.isoformat() if letter.letter_date else None}
                        for letter in letters])
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/pdf")
def pdf():
    url = request.args.get("url", "")
    try:
        parsed = urlsplit(url)
    except ValueError:
        return jsonify(error="invalid_url"), 400
    if parsed.scheme != "https" or parsed.netloc != "fs.knesset.gov.il" or not parsed.path.lower().startswith("/globaldocs/finance/"):
        return jsonify(error="invalid_url"), 400
    try:
        with requests.get(url, timeout=30, allow_redirects=False, stream=True) as upstream:
            if upstream.status_code != 200:
                return jsonify(error="pdf_unreachable"), 502
            data = bytearray()
            for chunk in upstream.iter_content(256 * 1024):
                data.extend(chunk)
                if len(data) > MAX_PDF_BYTES:
                    return jsonify(error="pdf_too_large"), 502
            if not data.startswith(b"%PDF-"):
                return jsonify(error="not_pdf"), 502
    except requests.RequestException as error:
        app.logger.warning("Knesset PDF failed: %s", type(error).__name__)
        return jsonify(error="pdf_unreachable"), 502
    return Response(bytes(data), mimetype="application/pdf", headers={"Cache-Control": "no-store"})


@app.get("/approvals")
def approvals():
    try:
        rows = fetch_approvals()
    except FeedUnreachable as error:
        app.logger.warning("Knesset approvals failed: %s", error)
        return jsonify(error="feed_unreachable"), 502
    response = jsonify([{"request_numbers": row.request_numbers,
                         "approved_date": row.approved_date.isoformat() if row.approved_date else None}
                        for row in rows])
    response.headers["Cache-Control"] = "no-store"
    return response
