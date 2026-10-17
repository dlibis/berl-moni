"""Send one test email through Resend, from the Neon from_address to the mailing list.

    uv run python bot/send_test_mail.py                      # send to the mailing list
    uv run python bot/send_test_mail.py --to me@example.com  # send only to this address
    uv run python bot/send_test_mail.py --check              # only verify RESEND_API_KEY and berl.site

Needs RESEND_API_KEY in .env and settings.from_address / reply_to_address in Neon. Run from the repo root.
"""
import argparse
import os
import sys
import uuid

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.db import connect, get_setting, list_emails
from notifier import ResendError, send_message

SITE_DOMAIN = "berl.site"
TEST_SUBJECT = "moni – test email"
TEST_HTML = "<p>This is a test email from the moni budget-letter bot.</p>"


def check_resend() -> bool:
    """RESEND_API_KEY is set and berl.site is a verified Resend domain."""
    key = os.environ.get("RESEND_API_KEY")
    if not key:
        print("RESEND_API_KEY is missing from .env")
        return False
    try:
        response = requests.get("https://api.resend.com/domains",
                                headers={"Authorization": f"Bearer {key}"}, timeout=60)
    except requests.RequestException as e:
        print(f"could not reach Resend: {type(e).__name__}")
        return False
    if not response.ok:
        print(f"Resend rejected the key (HTTP {response.status_code})")
        return False
    domains = {d.get("name"): d.get("status") for d in response.json().get("data", [])}
    if domains.get(SITE_DOMAIN) != "verified":
        print(f"{SITE_DOMAIN} is not verified in Resend (status: {domains.get(SITE_DOMAIN)})")
        return False
    return True


def send_test(recipients: list[str], attachments: list[tuple[str, bytes]]) -> None:
    """Send one test message to `recipients` (bcc) from the Neon addresses; raises ResendError."""
    with connect() as conn:
        from_address = get_setting(conn, "from_address", "")
        reply_to = get_setting(conn, "reply_to_address", "") or from_address
    if not from_address:
        raise SystemExit("settings.from_address is empty in Neon")
    key = f"test-{uuid.uuid4()}"
    send_message(from_address=from_address, reply_to=reply_to, bcc=recipients,
                 attachments=attachments, subject=TEST_SUBJECT, html=TEST_HTML, idempotency_key=key)
    # TODO: common/db.py has no helper to insert email_log (kind='test'); add one and call it here with `key`.


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a test email through Resend.")
    parser.add_argument("--check", action="store_true", help="only verify the key and the domain")
    parser.add_argument("--to", action="append", metavar="EMAIL",
                        help="send to this address instead of the mailing list (repeatable)")
    args = parser.parse_args()

    if not check_resend():
        return 1
    print(f"Resend key OK, {SITE_DOMAIN} verified")
    if args.check:
        return 0

    if args.to:
        recipients = args.to
    else:
        with connect() as conn:
            recipients = list_emails(conn)
    if not recipients:
        print("mailing list is empty and no --to given")
        return 1
    print(f"sending test email to {len(recipients)} recipient(s)")
    try:
        send_test(recipients, [])
    except ResendError as e:
        print(f"send failed: {e}")
        return 1
    print("sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
