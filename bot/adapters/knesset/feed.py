"""Knesset feed client: fetch_letters() lists the budget-transfer requests pending in the Finance Committee
(requestStatus 2), one FeedLetter per PDF, reading every page of the feed. Raises FeedUnreachable.

letter_date is the PDF's HTTP Last-Modified (its upload day in Israel): the feed's ApprovedDate stays
empty until the committee discusses a letter, so it is missing for nearly every pending one."""
from email.utils import parsedate_to_datetime
from math import ceil
from zoneinfo import ZoneInfo

from requests import RequestException, head, post

from bot.domain.errors import FeedUnreachable
from bot.domain.feed import FeedLetter

FEED_URL = "https://www.knesset.gov.il/WebSiteApi/knessetapi/CommitteeReports/GetCommitteePortalsBudget"
PAGE_SIZE = 10
PAGE_TIMEOUT = 30
ISRAEL = ZoneInfo("Asia/Jerusalem")


def _get_page(page_num):
    try:
        response = post(
            FEED_URL,
            json={
                "FromDate": None,
                "ToDate": None,
                "requestStatus": 2,
                "PageNumber": page_num,
            },
            timeout=PAGE_TIMEOUT,
        )
        response.raise_for_status()
        rows = response.json()
    except (RequestException, ValueError) as error:
        raise FeedUnreachable(f"page {page_num}: {type(error).__name__}") from error
    if not isinstance(rows, list):
        raise FeedUnreachable(f"page {page_num}: body is not a list")
    return rows


def fetch_letters():
    first_page = _get_page(1)
    if not first_page:
        return []

    total = first_page[0].get("TotalCount")
    if not isinstance(total, int):
        raise FeedUnreachable("first row has no TotalCount")

    rows = list(first_page)
    for page_num in range(2, ceil(total / PAGE_SIZE) + 1):
        rows += _get_page(page_num)
    if len(rows) != total:
        raise FeedUnreachable(f"got {len(rows)} rows, TotalCount is {total}")

    by_url = {}
    for row in rows:
        url = row.get("ReportUrl")
        if (url or "").strip():
            by_url.setdefault(url, []).append(row)
    return [_letter(url, group) for url, group in by_url.items()]


def _uploaded_on(url):
    try:
        response = head(url, timeout=PAGE_TIMEOUT)
        response.raise_for_status()
        return parsedate_to_datetime(response.headers["Last-Modified"]).astimezone(ISRAEL).date()
    except (RequestException, KeyError, ValueError, TypeError):
        return None  # a missing date must not drop the letter


def _letter(url, rows):
    numbers = dict.fromkeys(row["RequestNumberRange"] for row in rows if row.get("RequestNumberRange"))
    return FeedLetter(
        url=url,
        letter_date=_uploaded_on(url),
        ministry=next((row["GovMinistryName"] for row in rows if row.get("GovMinistryName")), ""),
        request_numbers=tuple(numbers),
        rows=tuple({k: v for k, v in row.items() if k not in ("Description", "TotalCount")} for row in rows),
    )
