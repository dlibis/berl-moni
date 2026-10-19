"""report_view(extraction, programs): the letter report as plain data, for the web page.

The same sections as the summary PDF (bot.adapters.summary_pdf.renderer), built by the same helpers
so the two show the same thing: header, summary box, money flow (sources -> hubs -> destinations),
why the money moves, and the appendix with every raw figure. `programs` is {code: master name}, as
the renderer takes it. Text here is in logical order; the PDF reorders Hebrew itself.
"""
from bot.domain.extraction import CODE_COLUMN, NAME_COLUMN, Extraction
from bot.domain.money_flow import INTERNAL_HUB, Item, fold, hubs, transfer_summary
from bot.domain.request_fields import RequestFields
from bot.domain.table import Table

UNIT = "אלפי ש״ח"   # every amount in a letter is in thousands of shekels


def report_view(extraction: Extraction, programs: dict[str, str]) -> dict:
    e = extraction
    fields = e.fields or RequestFields()   # an incomplete (irrelevant at analysis) letter has no fields
    master = e.matched(programs)
    sources, destinations, metric = transfer_summary(e.table)
    groups = hubs(sources, destinations, e.table)
    shown, folded = fold(destinations)
    rows, spans = budget_table_rows(e.table, master)
    return {
        "header": {"letterhead": list(e.letterhead), "scanned": e.scanned, "source": e.source},
        "summary": [{"label": label, "value": value}
                    for label, value in summary_rows(fields, groups, len(master), e.table)],
        "money_flow": {"metric": metric,
                       "hubs": [{"name": name, "items": _items(items)} for name, items in groups],
                       "destinations": _items(shown), "folded": _items(folded),
                       "master": sorted(master)},
        "why": {"shown": [_why(item, fields, master) for item in shown],
                "folded": [_why(item, fields, master) for item in folded],
                "sources": [code for code, _, _ in sources]},
        "appendix": {"table": {"rows": rows, "spans": spans},
                     "budget_history": [{"label": label, "table": _table(table)}
                                        for label, table in e.budget_history if table is not None and not table.empty],
                     "decision_links": [url.strip() for url in fields.decision_links.split("\n") if url.strip()],
                     "staffing_changes": fields.staffing_changes},
    }


def summary_rows(fields: RequestFields, groups: list[tuple[str, list[Item]]], master_count: int,
                 table: Table) -> list[tuple[str, str]]:
    """The summary box's label | value rows, empty values dropped: what a reader needs first."""
    internal = sum(a for name, items in groups if name == INTERNAL_HUB for _, _, a in items)
    numbers, *rest = [part.strip() for part in fields.request_number.split("|")]
    rows = [("סך הפנייה", f"{fields.total_amount} {UNIT}" if fields.total_amount else ""),
            ("העברה פנימית במשרד", money(internal) if internal else ""),
            ("כספים קואליציוניים", fields.coalition_funds),
            ("תוכניות מהמאסטר", f"{master_count} מתוך {len(set(table.column(CODE_COLUMN)))}"),
            ("מס' פנייה", numbers)]
    rows += [tuple(part.split(":", 1)) for part in rest if ":" in part]   # 'מספר פנייה לועדה: 65 עד 70'
    rows.append(("תאריך", fields.date))
    return [(label.strip(), value.strip()) for label, value in rows if value.strip()]


def budget_table_rows(table: Table, master: set[str]) -> tuple[list[list[str]], list[tuple[int, int, int]]]:
    """The budget table as the letter prints it, in logical (left-to-right) column order:
    a header, then two rows per item — מ- with the 'from' amounts, ל- with the 'to' amounts.
    The code, the name, שינוי (the first metric's change) and master (כן if the code is in `master`)
    span both rows; `spans` lists them as (column, top row, bottom row). Amounts are formatted."""
    metrics = [c.removesuffix(" from") for c in table.columns if str(c).endswith(" from")]
    header = ["מספר פרט", "שם הפרט", ""] + metrics + ["שינוי", "master"]
    last = len(header) - 1
    rows, spans = [header], []
    for item in table.records():
        top = len(rows)
        rows.append([str(item[CODE_COLUMN]), str(item[NAME_COLUMN] or ""), "מ-"]
                    + [amount(item.get(f"{m} from")) for m in metrics]
                    + [_change(item, metrics), "כן" if item[CODE_COLUMN] in master else "לא"])
        rows.append(["", "", "ל-"] + [amount(item.get(f"{m} to")) for m in metrics] + ["", ""])
        spans += [(col, top, top + 1) for col in (0, 1, last - 1, last)]
    return rows, spans


def money(thousands: float) -> str:
    """A letter's figure as printed, with its unit: '139,917 אלפי ש״ח'."""
    return f"{abs(thousands):,.0f} {UNIT}"


def amount(value) -> str:
    try:
        return f"{float(value):,.0f}" if value is not None else ""
    except (TypeError, ValueError):
        return ""


def _change(item, metrics: list[str]) -> str:
    """'to' minus 'from' for the first metric that has both, formatted; '' if none does."""
    for m in metrics:
        before, after = item.get(f"{m} from"), item.get(f"{m} to")
        if before is not None and after is not None:
            return amount(float(after) - float(before))
    return ""


def _items(items: list[Item]) -> list[dict]:
    return [{"code": code, "name": name, "amount": amount} for code, name, amount in items]


def _why(item: Item, fields: RequestFields, master: set[str]) -> dict:
    code, name, value = item
    return {"code": code, "name": name, "amount": value, "master": code in master,
            "uses": [{"text": use.text, "coalition": use.coalition} for use in fields.uses(code)]}


def _table(table: Table) -> dict:
    return {"columns": list(table.columns), "rows": [list(row) for row in table.rows]}
