from math import ceil

from requests import RequestException, post

FEED_URL = "https://www.knesset.gov.il/WebSiteApi/knessetapi/CommitteeReports/GetCommitteePortalsBudget"
PAGE_SIZE = 10
PAGE_TIMEOUT = 30


class FeedUnreachable(Exception):
    pass


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


def get_pdf_urls():
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

    urls = []
    for row in rows:
        url = row.get("ReportUrl")
        if not (url or "").strip() or url in urls:
            continue
        urls.append(url)
    return urls
