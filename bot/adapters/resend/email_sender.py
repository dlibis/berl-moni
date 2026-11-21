"""Resend email sender: send_email() sends one email with PDF attachments through the Resend API
(https://resend.com/docs/api-reference/emails/send-email).

RESEND_API_KEY comes from the environment. The caller writes email_log; this module touches no
database and logs counts only. Errors carry the HTTP status and Resend's error name, never an address.
"""
import base64
import logging
import os

import requests

from bot.domain.errors import ResendError

logger = logging.getLogger(__name__)

RESEND_EMAILS_URL = "https://api.resend.com/emails"
SENDER_NAME = "Berl Reports"  # display name shown before every from_address


def send_email(*, from_address: str, reply_to: str, bcc: list[str],
                 attachments: list[tuple[str, bytes]], subject: str, html: str,
                 idempotency_key: str) -> str:
    """POST one message to Resend. No Reply-To. Resend requires `to`, so the first list address is To and the rest stay in bcc."""
    to, rest = ([bcc[0]], bcc[1:]) if bcc else ([reply_to], [])
    body = {"from": f"{SENDER_NAME} <{from_address}>", "to": to, "subject": subject, "html": html,
            "attachments": [{"filename": filename, "content_type": "application/pdf",
                             "content": base64.b64encode(data).decode("ascii")}
                            for filename, data in attachments]}
    if rest:
        body["bcc"] = rest
    try:
        response = requests.post(
            RESEND_EMAILS_URL,
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
                     "Idempotency-Key": idempotency_key},
            json=body,
            timeout=60,
        )
    except requests.RequestException as e:
        raise ResendError(None, type(e).__name__) from None
    if not response.ok:
        try:
            name = str(response.json().get("name") or "unknown")
        except ValueError:
            name = "unknown"
        raise ResendError(response.status_code, name)
    logger.info("sent %d PDFs in 1 message", len(attachments))
    return str(response.json()["id"])
