"""Entry point: the `send` job. Read the Knesset budget-transfer feed, scan only the letters
not seen before, and email every pending summary PDF to the mailing list through Resend.

The job reads top-to-bottom in send_job() (spec steps 1-12): resume a stuck run, check the
schedule and settings, read the feed, scan new letters (one `letters` row each, committed
right away), batch the pending PDFs, check the email budget, then send (batch, chunk)
messages in order and finish the run. Every exit after due_day() passes writes one `scans`
row; a failed scan exits non-zero.

    uv run python bot/main.py                       # the send job (GitHub Actions)
    uv run python bot/main.py --to me@example.com   # local test: pending PDFs to this address only
    uv run python bot/main.py --no-email            # local: render PDFs to files/outputs/, write nothing to Neon
    uv run python bot/main.py --mark-seen           # T7: record every current feed URL as sent, scan nothing

Everything but secrets lives in Neon (programs, mailing list, schedule, addresses, limits);
the model (MODEL_NAME, MODEL_PROVIDER, its key) and RESEND_API_KEY come from the environment.
Logs carry counts only, never an address.
"""
import argparse
import logging
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

# Make the project root importable so `common` can be found.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import send_plan as plan
from agent import Agent
from aggregator import FeedUnreachable, get_pdf_urls
from common import letter_store as store
from common.config_manager import ConfigManager
from common.db import connect, get_setting, list_emails, load_programs
from common.limits import list_cap
from common.schedule_due import ISRAEL, due_day
from notifier import ResendError, send_message
from pdf_document import NoTextError
from reports import Reports
from utils_function import _slug

logging.basicConfig(level=logging.INFO)
# httpx logs every request line (incl. the OpenAI call) at INFO — quiet it so it
# doesn't drown the app's own logs; keep warnings/errors.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("./files/outputs/")

EMAIL_SUBJECT = "סיכום מכתבי העברה תקציבית"
EMAIL_HTML = '<div dir="rtl"><p>מצורפים סיכומי מכתבי ההעברה התקציבית הרלוונטיים לתוכניות הקרן.</p></div>'


def render_summary(result, slug: str, output_dir: Path, relevant_programs: dict) -> Path:
    """Render the summary PDF for one relevant letter; raises on failure."""
    letter = result.letter
    return Path(Reports().write_summary(
        output_dir / f"{slug}_summary.pdf",
        fields=result.fields,
        table=result.table,
        letterhead=letter.extract_letterhead(),
        name_column=letter.NAME_COLUMN,
        budget_history=letter.extract_budget_history(),
        source_url=letter.source,
        llm_usage=result.llm_usage,
        relevant_programs=relevant_programs,
        scanned=result.scanned,
    ))


def failure_reason(error: Exception) -> str:
    """Map an error from Agent.extract to a `letters.reason`."""
    text = str(error)
    if text.startswith("Failed to download"):  # PdfDocument._download gave up
        return "provider_5xx" if re.search(r"HTTP Error 5\d\d", text) else "network"
    status = next((s for s in (getattr(error, "status_code", None), getattr(error, "code", None),
                               getattr(getattr(error, "response", None), "status_code", None))
                   if isinstance(s, int)), None)
    if status == 429 or re.search(r"quota|rate.?limit|resource.?exhausted", f"{type(error).__name__} {text}", re.I):
        return "quota"
    if (status or 0) >= 500:
        return "provider_5xx"
    if isinstance(error, (requests.Timeout, requests.ConnectionError, urllib.error.URLError, TimeoutError)):
        return "network"
    if isinstance(error, NoTextError):
        return "no_text"
    return "extract_error"  # ExtractionError and anything else


def scan_letter(extractor, url: str, programs: dict, out_dir: Path, save_original: bool = False):
    """Scan one letter. Returns (status, reason, summary PDF bytes); reason 'quota' means stop scanning."""
    slug = _slug(url)
    try:
        result = extractor.extract(url)
    except Exception as error:  # noqa: BLE001 - every failure becomes a reason on the letter's row
        logger.warning("%s: failed (%s)", slug, type(error).__name__)
        return "failed", failure_reason(error), None
    if not result.relevant:
        logger.info("%s: not relevant (no code in master), skipped", slug)
        return "irrelevant", None, None
    # The master programs (with names) that made THIS letter relevant — shown in the PDF.
    matched = {code: programs.get(code, "") for code in sorted(result.matched_codes)}
    try:
        pdf_path = render_summary(result, slug, out_dir, matched)
        pdf = pdf_path.read_bytes()
        if save_original:
            shutil.copyfile(result.letter.doc.local_path(), out_dir / f"{slug}_original.pdf")
    except Exception:  # noqa: BLE001 - one bad render must not stop the run
        logger.exception("%s: summary PDF failed", slug)
        return "failed", "render_error", None
    return "pending", None, pdf


def settings_problem(conn, from_address: str, reply_to: str, recipients: list[str]) -> str | None:
    """`missing_settings` / `list_over_cap` (step 3), or None when the sender and list are usable."""
    if not (from_address or "").endswith("@berl.site") or not (reply_to or "").strip() or not recipients:
        return "missing_settings"
    daily, reserve, _ = limits(conn)
    if len(recipients) > list_cap(daily - reserve):
        return "list_over_cap"
    return None


def limits(conn) -> tuple[int, int, int]:
    """(resend_daily_limit, resend_reserve, resend_monthly_limit) from settings."""
    return (get_setting(conn, "resend_daily_limit", 100), get_setting(conn, "resend_reserve", 5),
            get_setting(conn, "resend_monthly_limit", 3000))


def finish_scan(conn, day, status: str, reason: str | None = None, **counts) -> int:
    """Write this run's one `scans` row and commit. Exit code: non-zero iff the scan failed."""
    store.write_scan(conn, day, status, reason, **counts)
    conn.commit()
    logger.info("scan %s%s: %s", status, f" ({reason})" if reason else "",
                ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 1 if status == "failed" else 0


def deliver(conn, run: dict, day, stats: dict, reason: str | None = None) -> int:
    """Steps 11-12: send every (batch, chunk) message not yet in email_log, then finish the run."""
    run_id = run["id"]
    chunks = plan.chunks(run["recipients"])
    done = store.sent_keys(conn, run_id)
    emails = messages = 0
    for b, urls in enumerate(run["batches"]):
        attachments = None
        for c, bcc in enumerate(chunks):
            key = plan.idempotency_key(run_id, b, c)
            if key in done:
                continue
            if store.lock_run(conn, run_id) != "sending":  # a person abandoned the run: write nothing more
                conn.rollback()
                logger.info("run %d is no longer sending, stopped", run_id)
                return finish_scan(conn, day, "nothing_new", reason, emails_sent=emails, **stats)
            if attachments is None:
                attachments = [(f"{_slug(u)}_summary.pdf", pdf)
                               for u, pdf in zip(urls, store.load_pdfs(conn, urls))]
            try:
                send_message(from_address=run["from_address"], reply_to=run["reply_to_address"], bcc=bcc,
                             attachments=attachments, subject=EMAIL_SUBJECT, html=EMAIL_HTML,
                             idempotency_key=key)
            except Exception as error:  # noqa: BLE001 - any send failure parks the run for a person
                name = error.name if isinstance(error, ResendError) else type(error).__name__
                logger.error("run %d: send failed (HTTP %s, %s)", run_id, getattr(error, "status", None), name)
                store.mark_run_failed(conn, run_id, name)
                return finish_scan(conn, day, "failed", "resend_error", emails_sent=emails, **stats)
            store.log_email(conn, key, "letter", len(bcc) + 1)
            conn.commit()
            emails += len(bcc) + 1
            messages += 1
    if not store.finish_run(conn, run_id):
        conn.rollback()
        return finish_scan(conn, day, "nothing_new", reason, emails_sent=emails, **stats)
    logger.info("run %d: sent %d messages", run_id, messages)
    return finish_scan(conn, day, "sent", reason, emails_sent=emails, **stats)


def resume_run(conn, run: dict, today) -> int:
    """Step 1: a run found `sending` or `failed` at the start of the job."""
    run_id = run["id"]
    if run["status"] == "failed":  # waiting for a person
        return finish_scan(conn, today, "failed", "send_run_stuck")
    if run["resume_requested_at"] is None:  # the job that started it died mid-send
        store.mark_run_failed(conn, run_id, "job_died")
        return finish_scan(conn, today, "failed", "send_run_stuck")
    store.clear_resume_request(conn, run_id)
    conn.commit()
    problem = settings_problem(conn, run["from_address"], run["reply_to_address"], run["recipients"])
    if problem:
        store.mark_run_failed(conn, run_id, problem)
        return finish_scan(conn, today, "failed", problem)
    chunks = plan.chunks(run["recipients"])
    done = store.sent_keys(conn, run_id)
    needed = sum(len(chunk) + 1 for b in range(len(run["batches"])) for c, chunk in enumerate(chunks)
                 if plan.idempotency_key(run_id, b, c) not in done)
    daily, reserve, monthly = limits(conn)
    sent_today, sent_month = store.email_counts(conn)
    if needed + sent_today > daily - reserve or needed + sent_month > monthly:
        store.mark_run_failed(conn, run_id, "over_budget")
        return finish_scan(conn, today, "failed", "over_budget")
    return deliver(conn, run, today, dict(new_letters=0, relevant=0, failed=0))


def send_job(conn) -> int:
    now = datetime.now(timezone.utc)
    today = now.astimezone(ISRAEL).date()
    run = store.send_run_open(conn)
    if run:
        return resume_run(conn, run, today)
    day = due_day(now, get_setting(conn, "schedule", []), conn)
    if day is None:
        return 0

    from_address = get_setting(conn, "from_address", "")
    reply_to = get_setting(conn, "reply_to_address", "")
    recipients = [e for e in list_emails(conn) if e != reply_to.strip().lower()]
    problem = settings_problem(conn, from_address, reply_to, recipients)
    if problem:
        return finish_scan(conn, day, "failed", problem)

    try:
        urls = get_pdf_urls()
    except FeedUnreachable as error:
        logger.error("feed unreachable: %s", error)
        return finish_scan(conn, day, "failed", "feed_unreachable")
    known = store.known_urls(conn)
    new = [u for u in urls if u not in known]

    stats = dict(new_letters=len(new), relevant=0, failed=0)
    quota = False
    if new:
        extractor, programs = Agent.from_config(), load_programs(conn)
        with tempfile.TemporaryDirectory() as tmp:
            for url in new:
                status, reason, pdf = scan_letter(extractor, url, programs, Path(tmp))
                store.insert_letter_result(conn, url, status, reason, pdf)
                conn.commit()
                stats["relevant"] += status == "pending"
                stats["failed"] += status == "failed"
                if reason == "quota":  # stop scanning; the rest stay untouched, pending ones still go out
                    quota = True
                    break
    stats["letters_in_feed"] = len(urls)
    reason = "quota" if quota else None
    logger.info("feed %d letters, scanned %d, relevant %d, failed %d",
                len(urls), len(new), stats["relevant"], stats["failed"])

    pending = store.pending_letters(conn)
    batches, oversized = plan.batches([(p["letter_url"], p["pdf_bytes"]) for p in pending])
    for url, _ in oversized:
        store.mark_letter_failed(conn, url, "render_error")
        stats["failed"] += 1
    conn.commit()
    if not batches:
        return finish_scan(conn, day, "nothing_new", reason, **stats)

    chunks = plan.chunks(recipients)
    daily, reserve, monthly = limits(conn)
    sent_today, sent_month = store.email_counts(conn)
    kept = plan.fit_budget(batches, chunks, sent_today, sent_month, daily, reserve, monthly)
    if not kept:
        return finish_scan(conn, day, "failed", "over_budget", **stats)

    batch_urls = [[url for url, _ in batch] for batch in kept]
    run_id = store.start_send_run(conn, day, from_address, reply_to, recipients, batch_urls)
    conn.commit()
    run = dict(id=run_id, from_address=from_address, reply_to_address=reply_to,
               recipients=recipients, batches=batch_urls)
    return deliver(conn, run, day, stats, reason)


def mark_seen_job(conn) -> int:
    """T7: record every current feed URL as sent without scanning; one `scans` row."""
    try:
        urls = get_pdf_urls()
    except FeedUnreachable as error:
        logger.error("feed unreachable: %s", error)
        return 1
    store.mark_seen(conn, urls)
    return finish_scan(conn, datetime.now(ISRAEL).date(), "nothing_new", letters_in_feed=len(urls))


def send_test_job(conn, address: str) -> int:
    """Local test: send the pending PDFs to `address` only; email_log kind 'test', nothing else written."""
    from_address = get_setting(conn, "from_address", "")
    pending = store.pending_letters(conn)
    batches, _ = plan.batches([(p["letter_url"], p["pdf_bytes"]) for p in pending])
    if not from_address or not batches:
        logger.error("nothing to test-send (from_address set: %s, pending batches: %d)",
                     bool(from_address), len(batches))
        return 1
    for batch in batches:
        urls = [url for url, _ in batch]
        attachments = [(f"{_slug(u)}_summary.pdf", pdf) for u, pdf in zip(urls, store.load_pdfs(conn, urls))]
        key = f"test-{uuid.uuid4()}"
        try:
            send_message(from_address=from_address, reply_to=address, bcc=[], attachments=attachments,
                         subject=EMAIL_SUBJECT, html=EMAIL_HTML, idempotency_key=key)
        except ResendError as error:
            logger.error("test send failed (HTTP %s, %s)", error.status, error.name)
            return 1
        store.log_email(conn, key, "test", 1)
        conn.commit()
    logger.info("test-sent %d messages", len(batches))
    return 0


def no_email_job() -> int:
    """Local: scan every feed letter, render to OUTPUT_DIR; Neon is only read, Resend never called."""
    try:
        urls = get_pdf_urls()
    except FeedUnreachable as error:
        logger.error("feed unreachable: %s", error)
        return 1
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    extractor, programs = Agent.from_config(), load_programs()
    rendered = 0
    for url in urls:
        status, reason, _ = scan_letter(extractor, url, programs, OUTPUT_DIR, save_original=True)
        rendered += status == "pending"
        if reason == "quota":
            break
    logger.info("--no-email: %d PDF(s) rendered, nothing sent", rendered)
    return 0


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the budget-letter send job.")
    parser.add_argument(
        "--to", metavar="EMAIL",
        help="local test: send the pending PDFs to this address only (logged as kind 'test')")
    parser.add_argument(
        "--no-email", action="store_true",
        help="local: render the summary PDFs to files/outputs/, write nothing to Neon, send nothing")
    parser.add_argument(
        "--mark-seen", action="store_true",
        help="record every current feed URL as sent without scanning (T7)")
    args = parser.parse_args(argv)
    if sum(map(bool, (args.to, args.no_email, args.mark_seen))) > 1:
        parser.error("--to, --no-email and --mark-seen are mutually exclusive")
    return args


def require_env(*names: str) -> bool:
    """Fail fast: log which variables are missing (names only)."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        logger.error("missing environment variables: %s", ", ".join(missing))
    return not missing


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.mark_seen:
        needed = ["DATABASE_URL"]
    elif args.to:
        needed = ["DATABASE_URL", "RESEND_API_KEY"]
    elif args.no_email:
        needed = ["DATABASE_URL", "MODEL_NAME", "MODEL_PROVIDER"]
    else:
        needed = ["DATABASE_URL", "RESEND_API_KEY", "MODEL_NAME", "MODEL_PROVIDER"]
    if not require_env(*needed):
        return 1
    if not (args.mark_seen or args.to) and not ConfigManager.get_api_key():
        logger.error("missing the API key for MODEL_PROVIDER")
        return 1
    if args.no_email:
        return no_email_job()
    with connect() as conn:
        if args.mark_seen:
            return mark_seen_job(conn)
        if args.to:
            return send_test_job(conn, args.to)
        return send_job(conn)


if __name__ == "__main__":
    sys.exit(main())
