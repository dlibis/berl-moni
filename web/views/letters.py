"""Read views of the letters table (Cosmic Python ch. 12): plain SQL, no domain model, no writes.

Relevance and completeness are derived here from the saved extraction and the current programs,
never stored; `outdated` compares the saved version in Python (bot.domain.versions)."""
from bot.domain.extraction import (
    PROVENANCE_COALITION_FUNDS,
    PROVENANCE_EXACT_CLAUSES,
    Extraction,
    relevance_sql,
)
from bot.domain.report import report_view
from bot.domain.versions import is_outdated

RELEVANT = relevance_sql()
COMPLETE = "coalesce(jsonb_typeof(extraction->'fields') = 'object', false)"

COLUMNS = f"""slug, letter_url, letter_date, ministry, coalesce(request_numbers, '{{}}') AS request_numbers,
    first_seen_at, analysis_status, analyzed_at, {RELEVANT} AS relevant, {COMPLETE} AS complete,
    extraction IS NULL AND summary_pdf IS NOT NULL AS legacy, extraction IS NOT NULL AS has_extraction,
    extraction_version, last_error, last_error_at, last_sent_at, send_count, analysis_requested_by,
    requires_review, passed, passed_date, passage_detected_at"""

FILTERS = {
    "not_analyzed": "analysis_status IN ('discovered', 'queued', 'analyzing')",
    "failed": "analysis_status = 'failed'",
    "requires_review": "requires_review IS TRUE",
    "needs_analysis": f"{RELEVANT} AND NOT {COMPLETE}",
    "relevant": RELEVANT,
    "irrelevant": f"{COMPLETE} AND NOT {RELEVANT}",
}

ORDER = "ORDER BY letter_date DESC NULLS LAST, letter_url"


def all_letter_rows(conn, *, programs: list[str]) -> list[dict]:
    """All letters (unfiltered), same row shape as list_letters items."""
    params = {
        "programs": list(programs),
        "prov_exact": PROVENANCE_EXACT_CLAUSES,
        "prov_coalition": PROVENANCE_COALITION_FUNDS,
    }
    rows = conn.execute(f"SELECT {COLUMNS} FROM letters {ORDER}", params)
    return [_item(row) for row in rows]


def list_letters(conn, *, page: int, page_size: int, status: str | None,
                 programs: list[str], search: str = "") -> tuple[list[dict], int]:
    """(one page of items, the total matching `status`); `status` is a FILTERS key or None."""
    where = FILTERS[status] if status else "true"
    if search:
        where = f"({where}) AND strpos(lower(concat_ws(' ', ministry, array_to_string(request_numbers, ' '))), lower(%(search)s)) > 0"
    params = {
        "programs": list(programs),
        "prov_exact": PROVENANCE_EXACT_CLAUSES,
        "prov_coalition": PROVENANCE_COALITION_FUNDS,
        "limit": page_size,
        "offset": (page - 1) * page_size,
        "search": search,
    }
    total = conn.execute(f"SELECT count(*) AS total FROM letters WHERE {where}", params).fetchone()["total"]
    rows = conn.execute(f"SELECT {COLUMNS} FROM letters WHERE {where} {ORDER} LIMIT %(limit)s OFFSET %(offset)s", params)
    return [_item(row) for row in rows], total


def patch_letter_flags(conn, slug: str, programs: dict[str, str], *,
                       requires_review: bool | None = None, passed: bool | None = None) -> dict | None:
    """Update manual flags; returns detail JSON or None if unknown."""
    sets, params = [], {"slug": slug, "programs": list(programs)}
    if requires_review is not None:
        sets.append("requires_review = %(requires_review)s")
        params["requires_review"] = requires_review
    if passed is not None:
        sets.append("passed = %(passed)s")
        params["passed"] = passed
    if not sets:
        return letter_detail(conn, slug, programs)
    row = conn.execute(f"UPDATE letters SET {', '.join(sets)} WHERE slug = %(slug)s "
                       f"RETURNING slug", params).fetchone()
    return letter_detail(conn, slug, programs) if row else None


def letter_detail(conn, slug: str, programs: dict[str, str]) -> dict | None:
    """The letter's item plus `report` (None until it has an extraction); None if unknown."""
    row = conn.execute(
        f"SELECT {COLUMNS}, extraction FROM letters WHERE slug = %(slug)s",
        {
            "slug": slug,
            "programs": list(programs),
            "prov_exact": PROVENANCE_EXACT_CLAUSES,
            "prov_coalition": PROVENANCE_COALITION_FUNDS,
        },
    ).fetchone()
    if row is None:
        return None
    data = row.pop("extraction")
    extraction = Extraction.from_json(data) if data is not None else None
    return {**_item(row), "report": report_view(extraction, extraction.named_matches(programs)) if extraction else None}


def _item(row: dict) -> dict:
    version, has_extraction = row.pop("extraction_version"), row.pop("has_extraction")
    row["needs_analysis"] = row["relevant"] and not row["complete"]
    row["outdated"] = has_extraction and is_outdated(version)
    row["report_available"] = has_extraction
    return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
