"""Analysis use cases: read the feed into `letters`, queue a letter for analysis, and drain the queue.

refresh_feed and request_analysis run in the web; drain_queue runs in the worker. The queue is the
`letters.analysis_status` column with leases (LettersRepository.claim); each letter commits on its own.
"""
import logging
from datetime import datetime, timezone
from typing import Callable, Literal, NamedTuple

from bot.domain.errors import ExtractionError
from bot.domain.feed import FeedLetter
from bot.domain.slug import letter_slug
from bot.domain.versions import analysis_version
from bot.service_layer.services import LetterExtractor, failure_reason

logger = logging.getLogger(__name__)


class RefreshResult(NamedTuple):
    new: int
    seen: int


class AnalysisRequest(NamedTuple):
    outcome: Literal["queued", "done", "busy", "not_found"]
    dispatched: bool


def refresh_feed(uow, feed: Callable[[], list[FeedLetter]], auto: bool = False) -> RefreshResult:
    """Upsert the feed's letters; new ones are `queued` when auto, else `discovered`. FeedUnreachable propagates."""
    letters = feed()
    new = uow.letters.upsert_feed(letters, auto)
    uow.set_setting("last_feed_refresh_at", datetime.now(timezone.utc).isoformat())
    uow.commit()
    return RefreshResult(new, len(letters) - new)


def request_analysis(uow, slug: str, user: str | None, dispatch: Callable[[], bool],
                     reanalyze: bool = False) -> AnalysisRequest:
    """Queue a letter and dispatch the worker; existing reports require explicit `reanalyze`."""
    letter = uow.letters.get(slug)
    if letter is None:
        return AnalysisRequest("not_found", False)
    status = letter["analysis_status"]
    if status in ("queued", "analyzing"):
        return AnalysisRequest("busy", False)
    if (status == "analyzed" or letter["extraction"] is not None) and not reanalyze:
        return AnalysisRequest("done", False)
    if not uow.letters.queue(slug, user, (status,)):  # another request got there first
        uow.rollback()
        return AnalysisRequest("busy", False)
    uow.commit()
    return AnalysisRequest("queued", dispatch())


class DrainResult(NamedTuple):
    analyzed: int
    unexpected: bool  # an error that is a bug, not a letter we can't read: the job must fail


def drain_queue(uow, extractor: Callable[[dict[str, str]], LetterExtractor], model: str) -> DrainResult:
    """Requeue expired leases, then claim and analyze letters until none is queued. A quota failure stops
    the drain; the letters still queued wait for the next run."""
    uow.letters.requeue_expired()
    uow.commit()
    letter_extractor = extractor(uow.programs())
    analyzed, unexpected = 0, False
    while (letter := uow.letters.claim()) is not None:
        uow.commit()
        url, lease = letter["letter_url"], letter["lease_id"]
        try:
            result = letter_extractor.extract(url)
        except Exception as error:  # noqa: BLE001 - every failure becomes last_error on the letter's row
            reason = failure_reason(error)
            if reason == "extract_error" and not isinstance(error, ExtractionError):
                logger.exception("%s: failed unexpectedly", letter_slug(url))
                unexpected = True
            else:
                logger.warning("%s: failed (%s, %s)%s", letter_slug(url), reason, type(error).__name__,
                               f": {error}" if isinstance(error, ExtractionError) else "")
            uow.letters.fail_analysis(url, lease, reason)
            uow.commit()
            if reason == "quota":
                break
            continue
        analyzed += uow.letters.finish_analysis(url, lease, result.to_json(), analysis_version(model),
                                                sorted(result.codes()), result.source_sha256, result.source_size)
        uow.commit()
    return DrainResult(analyzed, unexpected)
