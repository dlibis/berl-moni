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


def send_email(*, from_address: str, reply_to: str, bcc: list[str],
                 attachments: list[tuple[str, bytes]], subject: str, html: str,
                 idempotency_key: str) -> str:
    """POST one message to Resend; `to` is the Reply-to inbox, the mailing list goes in `bcc`."""
    try:
        response = requests.post(
            RESEND_EMAILS_URL,
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
                     "Idempotency-Key": idempotency_key},
            json={"from": from_address, "to": [reply_to], "reply_to": reply_to, "bcc": bcc,
                  "subject": subject, "html": html,
                  "attachments": [{"filename": filename, "content": base64.b64encode(data).decode("ascii")}
                                  for filename, data in attachments]},
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
