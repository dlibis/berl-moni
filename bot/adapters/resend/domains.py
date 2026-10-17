"""Resend domain check: domain_problem(domain) says why `domain` can't send yet — no API key, the key
rejected, or the domain not verified in Resend — or None when it can."""
import os

import requests


def domain_problem(domain: str) -> str | None:
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        return "RESEND_API_KEY is missing from .env"
    try:
        response = requests.get("https://api.resend.com/domains",
                                headers={"Authorization": f"Bearer {key}"}, timeout=60)
    except requests.RequestException as e:
        return f"could not reach Resend: {type(e).__name__}"
    if not response.ok:
        return f"Resend rejected the key (HTTP {response.status_code})"
    try:
        statuses = {d["name"]: d["status"] for d in response.json()["data"]}
    except (KeyError, TypeError, ValueError):  # not JSON, or not the shape Resend documents
        return "Resend sent an unreadable response"
    status = statuses.get(domain)
    return None if status == "verified" else f"{domain} is not verified in Resend (status: {status})"
