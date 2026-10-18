"""send_letter: the immediate manual send of one analyzed letter (Send on the letters page).

It runs in the web. A manual send is a `send_runs` row of kind 'manual' with one batch holding the one
letter; delivery, the write-before-call email log and the failure parking are the send job's `deliver`.
"""
import logging
from typing import Literal, NamedTuple

from bot.domain import send_plan as plan
from bot.domain.extraction import Extraction
from bot.service_layer.services import Ports, SendRun, ScanCounts, attachments, deliver, limits, settings_problem
from common.schedule_due import ISRAEL

logger = logging.getLogger(__name__)


class SendResult(NamedTuple):
    outcome: Literal["sent", "not_found", "not_sendable", "confirm_resend", "run_open", "over_budget", "settings",
                     "failed"]
    detail: str | None = None


def send_letter(uow, ports: Ports, slug: str, user: str | None, resend: bool = False) -> SendResult:
    letter = uow.letters.get(slug)
    if letter is None:
        return SendResult("not_found")
    saved = letter["extraction"]
    if letter["analysis_status"] != "analyzed" or saved is None:  # legacy rows have no JSON to render
        return SendResult("not_sendable")
    extraction = Extraction.from_json(saved)
    if not extraction.complete or not extraction.relevant_to(uow.programs()):
        return SendResult("not_sendable")
    if letter["send_count"] > 0 and not resend:
        return SendResult("confirm_resend")

    from_address = uow.setting("from_address", "")
    reply_to = uow.setting("reply_to_address", "")
    recipients = [e for e in uow.mailing_list() if e != reply_to.strip().lower()]
    problem = settings_problem(uow, from_address, reply_to, recipients)
    if problem:
        return SendResult("settings", problem)

    url = letter["letter_url"]
    try:
        attachments(uow, ports, [url])  # a render error stops here with nothing written
    except Exception as error:  # noqa: BLE001 - reported to the caller as a failed send
        logger.exception("%s: render failed", slug)
        return SendResult("failed", type(error).__name__)

    uow.send_runs.lock_budget()  # held until the run row commits: a second click waits here, then sees the run
    if uow.send_runs.open_for(url):  # still sending, or parked for a person to resume or abandon
        uow.rollback()
        return SendResult("run_open")
    if uow.letters.get(slug)["send_count"] > 0 and not resend:  # sent while this click waited for the lock
        uow.rollback()
        return SendResult("confirm_resend")
    sent_today, sent_month = uow.email_log.counts()
    reserved = uow.send_runs.reserved_emails()
    daily, reserve, monthly = limits(uow)
    if not plan.fit_budget([[url]], plan.chunks(recipients), sent_today + reserved, sent_month + reserved,
                           daily, reserve, monthly):
        uow.rollback()  # release the send lock
        return SendResult("over_budget")
    day = ports.now().astimezone(ISRAEL).date()
    run_id = uow.send_runs.start(day, from_address, reply_to, recipients, [[url]], kind="manual", requested_by=user)
    uow.commit()

    run = SendRun(id=run_id, from_address=from_address, reply_to_address=reply_to,
                  recipients=recipients, batches=[[url]])
    # ponytail: deliver renders again from the same JSON; pass the bytes in if the second render is too slow
    deliver(uow, ports, run, day, ScanCounts(), record_scan=False)
    row = uow.send_runs.get(run_id)
    if row["status"] == "sent":
        return SendResult("sent")
    return SendResult("failed", row["error"] or row["status"])
