"""Service layer (Cosmic Python ch. 4): the send job and its local variants, as use cases.

Each use case takes a UnitOfWork and the Ports it needs — no globals, no environment, no SQL — and
returns the process exit code. bot.bootstrap builds the real Ports; the tests pass fakes.

send_job (spec steps 1-12): resume a stuck run, check the schedule and settings, read the feed (new
letters are queued), drain the analysis queue, render the letters due for an auto send from their saved
extraction, check the email budget, then send (batch, chunk) messages in order and finish the run. Every
exit after the schedule check writes one `scans` row; a failed scan exits non-zero. Logs carry counts
only, never an address.
"""
import logging
import re
import urllib.error
import uuid
from dataclasses import dataclass, field
from functools import partial
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Protocol, TypedDict

import requests

from bot.domain import send_plan as plan
from bot.domain.errors import DownloadError, ExtractionError, FeedUnreachable, NoTextError, ResendError
from bot.domain.extraction import Extraction
from bot.domain.feed import FeedLetter
from bot.domain.slug import letter_slug
from bot.domain.statuses import LetterReason, ScanReason, ScanStatus
from common.limits import list_cap
from common.schedule_due import ISRAEL

logger = logging.getLogger(__name__)

EMAIL_SUBJECT = "סיכום מכתבי העברה תקציבית"
EMAIL_HTML = '<div dir="rtl"><p>מצורפים סיכומי מכתבי ההעברה התקציבית הרלוונטיים לתוכניות הקרן.</p></div>'
SENDER_DOMAIN = "berl.site"  # the verified Resend domain every from_address must use
# Longer than the web function's maxDuration (300 s): a manual run younger than this may still be sending.
MANUAL_SEND_GRACE = timedelta(minutes=5)
TEST_SUBJECT = "moni – test email"
TEST_HTML = "<p>This is a test email from the moni budget-letter bot.</p>"


class LetterExtractor(Protocol):
    def extract(self, source: str) -> Extraction: ...


class SendEmail(Protocol):
    def __call__(self, *, from_address: str, reply_to: str, bcc: list[str], attachments: list[tuple[str, bytes]],
                 subject: str, html: str, idempotency_key: str) -> str: ...


@dataclass
class Ports:
    """The outside world the use cases talk to (Cosmic Python ch. 13: injected, not imported)."""
    feed: Callable[[], list[FeedLetter]]                          # knesset.feed.fetch_letters
    extractor: Callable[[dict[str, str]], LetterExtractor]        # programs -> domain.extraction.Extractor
    render: Callable[[Extraction, dict[str, str]], bytes]         # summary_pdf.renderer.SummaryPdfRenderer.render
    send_email: SendEmail                                         # resend.email_sender.send_email
    save_copy: Callable[[str, Path], None]                        # letter_pdf.download.save_copy (--no-email)
    now: Callable[[], datetime] = field(default=lambda: datetime.now(timezone.utc))
    model: str = ""                                               # the configured model, for analysis_version


class SendRun(TypedDict):
    """A send run as the delivery loop needs it (a `send_runs` row, or one just started)."""
    id: int
    from_address: str
    reply_to_address: str
    recipients: list[str]
    batches: list[list[str]]  # letter URLs per attachment batch, oldest first


class ScanCounts(TypedDict, total=False):
    """The counts written to this run's `scans` row."""
    letters_in_feed: int
    new_letters: int
    relevant: int
    failed: int
    emails_sent: int


def failure_reason(error: Exception) -> LetterReason:
    """Map an error from Extractor.extract to a `letters.reason`."""
    if isinstance(error, DownloadError):  # PdfDocument gave up after its retries
        return "provider_5xx" if (error.status or 0) >= 500 else "network"
    status = next((s for s in (getattr(error, "status_code", None), getattr(error, "code", None),
                               getattr(getattr(error, "response", None), "status_code", None))
                   if isinstance(s, int)), None)
    if status == 429 or re.search(r"quota|rate.?limit|resource.?exhausted", f"{type(error).__name__} {error}", re.I):
        return "quota"
    if (status or 0) >= 500:
        return "provider_5xx"
    if isinstance(error, (requests.Timeout, requests.ConnectionError, urllib.error.URLError, TimeoutError)):
        return "network"
    if isinstance(error, NoTextError):
        return "no_text"
    return "extract_error"  # ExtractionError and anything else


def limits(uow) -> tuple[int, int, int]:
    """(resend_daily_limit, resend_reserve, resend_monthly_limit) from settings."""
    return (uow.setting("resend_daily_limit", 100), uow.setting("resend_reserve", 5),
            uow.setting("resend_monthly_limit", 3000))


def settings_problem(uow, from_address: str, reply_to: str, recipients: list[str]) -> ScanReason | None:
    """`missing_settings` / `list_over_cap` (step 3), or None when the sender and list are usable."""
    if not (from_address or "").endswith("@" + SENDER_DOMAIN) or not (reply_to or "").strip() or not recipients:
        return "missing_settings"
    daily, reserve, _ = limits(uow)
    if len(recipients) > list_cap(daily - reserve):
        return "list_over_cap"
    return None


def finish_scan(uow, day, status: ScanStatus, reason: ScanReason | None = None, record: bool = True,
                **counts) -> int:
    """Write this run's one `scans` row (unless `record` is off) and commit. Exit code: non-zero iff the scan failed."""
    if record:
        uow.scans.add(day, status, reason, **counts)
    uow.commit()
    logger.info("scan %s%s: %s", status, f" ({reason})" if reason else "",
                ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 1 if status == "failed" else 0


def attachments(uow, ports: Ports, urls: list[str]) -> list[tuple[str, bytes]]:
    programs = uow.programs()
    files = []
    for url, saved in zip(urls, uow.letters.load_extractions(urls)):
        if saved is None:
            pdf = uow.letters.load_pdfs([url])[0]
        else:
            extraction = Extraction.from_json(saved)
            pdf = ports.render(extraction, extraction.named_matches(programs))
        files.append((f"{letter_slug(url)}_summary.pdf", pdf))
    return files


def deliver(uow, ports: Ports, run: SendRun, day, stats: ScanCounts, reason: ScanReason | None = None,
            record_scan: bool = True) -> int:
    """Steps 11-12: send every (batch, chunk) message not yet in email_log, then finish the run.
    A manual send passes `record_scan=False`: it is not a scan."""
    run_id = run["id"]
    finish = partial(finish_scan, record=record_scan)
    chunks = plan.chunks(run["recipients"])
    done = uow.email_log.sent_keys(run_id)
    emails = messages = 0
    for b, urls in enumerate(run["batches"]):
        files = None
        for c, bcc in enumerate(chunks):
            key = plan.idempotency_key(run_id, b, c)
            if key in done:
                continue
            if uow.send_runs.lock(run_id) != "sending":  # a person abandoned the run: write nothing more
                uow.rollback()
                logger.info("run %d is no longer sending, stopped", run_id)
                return finish(uow, day, "nothing_new", reason, emails_sent=emails, **stats)
            files = files or attachments(uow, ports, urls)
            uow.email_log.start(key, "letter", len(bcc) + 1)
            uow.commit()
            try:
                resend_email_id = ports.send_email(
                    from_address=run["from_address"], reply_to=run["reply_to_address"], bcc=bcc,
                    attachments=files, subject=EMAIL_SUBJECT, html=EMAIL_HTML, idempotency_key=key)
            except Exception as error:  # noqa: BLE001 - any send failure parks the run for a person
                name = error.name if isinstance(error, ResendError) else type(error).__name__
                logger.error("run %d: send failed (HTTP %s, %s)", run_id, getattr(error, "status", None), name)
                uow.send_runs.mark_failed(run_id, name)
                return finish(uow, day, "failed", "resend_error", emails_sent=emails, **stats)
            uow.email_log.complete(key, resend_email_id)
            uow.commit()
            emails += len(bcc) + 1
            messages += 1
    if not uow.send_runs.finish(run_id):
        uow.rollback()
        return finish(uow, day, "nothing_new", reason, emails_sent=emails, **stats)
    delivered = [url for urls in run["batches"] for url in urls]
    uow.letters.mark_delivered(delivered)
    uow.letters.mark_sent(delivered, run_id)  # legacy rows during the expand/contract migration
    logger.info("run %d: sent %d messages", run_id, messages)
    return finish(uow, day, "sent", reason, emails_sent=emails, **stats)


def resume_run(uow, ports: Ports, run: dict, today) -> int:
    """Step 1: a run found `sending` or `failed` at the start of the job."""
    run_id = run["id"]
    expired = uow.email_log.expire_stale()
    if any(key.startswith(f"run{run_id}-b") for key in expired):
        uow.send_runs.mark_failed(run_id, "send_unknown")
        return finish_scan(uow, today, "failed", "send_run_stuck")
    if run["status"] == "failed":  # waiting for a person
        return finish_scan(uow, today, "failed", "send_run_stuck")
    if run["resume_requested_at"] is None:  # the job that started it died mid-send
        uow.send_runs.mark_failed(run_id, "job_died")
        return finish_scan(uow, today, "failed", "send_run_stuck")
    uow.send_runs.clear_resume_request(run_id)
    uow.commit()
    problem = settings_problem(uow, run["from_address"], run["reply_to_address"], run["recipients"])
    if problem:
        uow.send_runs.mark_failed(run_id, problem)
        return finish_scan(uow, today, "failed", problem)
    chunks = plan.chunks(run["recipients"])
    done = uow.email_log.sent_keys(run_id)
    needed = sum(len(chunk) + 1 for b in range(len(run["batches"])) for c, chunk in enumerate(chunks)
                 if plan.idempotency_key(run_id, b, c) not in done)
    daily, reserve, monthly = limits(uow)
    uow.send_runs.lock_budget()
    sent_today, sent_month = uow.email_log.counts()
    if not plan.within_budget(needed, sent_today, sent_month, daily, reserve, monthly):
        uow.send_runs.mark_failed(run_id, "over_budget")
        return finish_scan(uow, today, "failed", "over_budget")
    return deliver(uow, ports, run, today, ScanCounts(new_letters=0, relevant=0, failed=0))


def send_job(uow, ports: Ports) -> int:
    now = ports.now()
    run = uow.send_runs.find_open()
    if run and run["kind"] == "manual" and run["status"] == "sending" and now - run["started_at"] < MANUAL_SEND_GRACE:
        logger.info("run %d: a manual send is still in its web request, left alone", run["id"])
        return 0
    if run:
        return resume_run(uow, ports, run, now.astimezone(ISRAEL).date())
    day = uow.due_day(now)
    if day is None:
        return 0

    from_address = uow.setting("from_address", "")
    reply_to = uow.setting("reply_to_address", "")
    recipients = [e for e in uow.mailing_list() if e != reply_to.strip().lower()]
    problem = settings_problem(uow, from_address, reply_to, recipients)
    if problem:
        return finish_scan(uow, day, "failed", problem)

    from bot.service_layer.analysis import drain_queue, refresh_feed  # analysis imports this module
    if uow.setting("auto_since") is None:  # a schedule saved before auto_since existed: auto mode starts now
        uow.set_setting("auto_since", uow.db_now())
        uow.commit()
    try:
        refreshed = refresh_feed(uow, ports.feed, auto=True)
    except FeedUnreachable as error:
        logger.error("feed unreachable: %s", error)
        return finish_scan(uow, day, "failed", "feed_unreachable")
    broken = drain_queue(uow, ports.extractor, ports.model).unexpected  # the run sends, then fails
    urls = uow.letters.auto_eligible(uow.setting("auto_since"))
    stats = ScanCounts(letters_in_feed=refreshed.new + refreshed.seen, new_letters=refreshed.new,
                       relevant=len(urls), failed=0)
    sizes = []
    for url in urls:
        try:
            [(_, pdf)] = attachments(uow, ports, [url])  # for its size; deliver renders it again to send
        except Exception:  # noqa: BLE001 - one bad render must not stop the run
            logger.exception("%s: summary PDF failed", letter_slug(url))
            stats["failed"] += 1
            broken = True
            continue
        sizes.append((url, len(pdf)))
    batches, oversized = plan.batches(sizes)
    stats["failed"] += len(oversized)  # rendered fine, but too big to attach to any email
    logger.info("feed %d letters, new %d, to send %d, failed %d",
                stats["letters_in_feed"], stats["new_letters"], stats["relevant"], stats["failed"])
    if not batches:
        code = finish_scan(uow, day, "nothing_new", **stats)
        return 1 if broken else code

    chunks = plan.chunks(recipients)
    daily, reserve, monthly = limits(uow)
    uow.send_runs.lock_budget()
    sent_today, sent_month = uow.email_log.counts()
    kept = plan.fit_budget(batches, chunks, sent_today, sent_month, daily, reserve, monthly)
    if not kept:
        return finish_scan(uow, day, "failed", "over_budget", **stats)

    batch_urls = [[url for url, _ in batch] for batch in kept]
    run_id = uow.send_runs.start(day, from_address, reply_to, recipients, batch_urls)
    uow.commit()
    run = SendRun(id=run_id, from_address=from_address, reply_to_address=reply_to,
                  recipients=recipients, batches=batch_urls)
    code = deliver(uow, ports, run, day, stats)
    return 1 if broken else code


def send_pending_test(uow, ports: Ports, address: str) -> int:
    """Local test: send the letters an auto run would send (any auto_since), rendered now, to `address`
    only; email_log kind 'test', nothing else written."""
    from_address = uow.setting("from_address", "")
    urls = uow.letters.auto_eligible(None)
    files = dict(zip(urls, attachments(uow, ports, urls)))
    batches, _ = plan.batches([(url, len(pdf)) for url, (_, pdf) in files.items()])
    if not from_address or not batches:
        logger.error("nothing to test-send (from_address set: %s, batches: %d)", bool(from_address), len(batches))
        return 1
    for batch in batches:
        key = f"test-{uuid.uuid4()}"
        try:
            ports.send_email(from_address=from_address, reply_to=address, bcc=[],
                             attachments=[files[url] for url, _ in batch],
                             subject=EMAIL_SUBJECT, html=EMAIL_HTML, idempotency_key=key)
        except ResendError as error:
            logger.error("test send failed (HTTP %s, %s)", error.status, error.name)
            return 1
        uow.email_log.add(key, "test", 1)
        uow.commit()
    logger.info("test-sent %d messages", len(batches))
    return 0


def send_test_message(uow, ports: Ports, recipients: list[str], files=(),
                      subject: str = TEST_SUBJECT, html: str = TEST_HTML) -> int:
    """Send one message to `recipients` (bcc) from the Neon addresses and log it as kind 'test'."""
    from_address = uow.setting("from_address", "")
    reply_to = uow.setting("reply_to_address", "") or from_address
    if not from_address:
        logger.error("settings.from_address is empty in Neon")
        return 1
    key = f"test-{uuid.uuid4()}"
    try:
        ports.send_email(from_address=from_address, reply_to=reply_to, bcc=recipients,
                         attachments=list(files), subject=subject, html=html, idempotency_key=key)
    except ResendError as error:
        logger.error("test send failed (HTTP %s, %s)", error.status, error.name)
        return 1
    uow.email_log.add(key, "test", len(recipients) + 1)
    uow.commit()
    return 0


def render_all(uow, ports: Ports, out_dir: Path) -> int:
    """Local: extract every feed letter and render the relevant ones to `out_dir`; Neon is only read,
    nothing is sent. Exits non-zero if any letter failed or the model quota stopped the run."""
    try:
        urls = [letter.url for letter in ports.feed()]
    except FeedUnreachable as error:
        logger.error("feed unreachable: %s", error)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    programs = uow.programs()
    extractor = ports.extractor(programs)
    rendered = failed = 0
    for i, url in enumerate(urls):
        slug = letter_slug(url)
        try:
            result = extractor.extract(url)
            pdf = result.relevant_to(programs) and ports.render(result, result.named_matches(programs))
        except Exception as error:  # noqa: BLE001 - one bad letter must not stop the run
            reason = failure_reason(error)
            if reason == "extract_error" and not isinstance(error, ExtractionError):
                logger.exception("%s: failed unexpectedly", slug)
            else:
                logger.warning("%s: failed (%s, %s)", slug, reason, type(error).__name__)
            failed += 1
            if reason == "quota":
                logger.error("--no-email: the model quota ran out, %d letter(s) not scanned", len(urls) - i - 1)
                break
            continue
        if not pdf:
            logger.info("%s: not relevant (no code in master), skipped", slug)
            continue
        (out_dir / f"{slug}_summary.pdf").write_bytes(pdf)
        rendered += 1
        try:
            ports.save_copy(url, out_dir / f"{slug}_original.pdf")
        except Exception:  # noqa: BLE001 - the summary is what matters here
            logger.exception("%s: could not save the original PDF", slug)
    logger.info("--no-email: %d PDF(s) rendered, %d failed, nothing sent", rendered, failed)
    return 1 if failed else 0
