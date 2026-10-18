"""report_view(extraction, programs): the letter report as plain data, for the web page.

The same sections as the summary PDF (bot.adapters.summary_pdf.renderer), from the same money-flow
grouping: header, summary box, money flow (sources -> hubs -> destinations), why the money moves,
and the appendix with every raw figure. `programs` is {code: master name}, as the renderer takes it.
"""
from bot.domain.extraction import CODE_COLUMN, Extraction
from bot.domain.money_flow import Item, fold, hubs, transfer_summary
from bot.domain.request_fields import RequestFields
from bot.domain.table import Table

COALITION_TAG = "קואליציוני"   # as the PDF tags a coalition-funded use


def report_view(extraction: Extraction, programs: dict[str, str]) -> dict:
    e = extraction
    fields = e.fields or RequestFields()   # an incomplete (irrelevant at analysis) letter has no fields
    master = e.matched(programs)
    sources, destinations, metric = transfer_summary(e.table)
    shown, folded = fold(destinations)
    why = ([_why(item, "in", fields, master) for item in destinations]
           + [_why(item, "out", fields, master) for item in sources])
    return {
        "header": {"letterhead": list(e.letterhead), "scanned": e.scanned, "source": e.source},
        "summary": {"date": fields.date, "request_number": fields.request_number,
                    "total_amount": fields.total_amount, "coalition_funds": fields.coalition_funds,
                    "program_count": len(set(e.table.column(CODE_COLUMN))), "master_count": len(master)},
        "money_flow": {"metric": metric,
                       "hubs": [{"name": name, "items": _items(items)} for name, items in hubs(sources, destinations, e.table)],
                       "destinations": _items(shown), "folded": _items(folded)},
        "why": why,
        "appendix": {"table": _table(e.table),
                     "budget_history": [{"label": label, "table": _table(table)} for label, table in e.budget_history],
                     "decision_links": [url.strip() for url in fields.decision_links.split("\n") if url.strip()],
                     "staffing_changes": fields.staffing_changes},
    }


def _items(items: list[Item]) -> list[dict]:
    return [{"code": code, "name": name, "amount": amount} for code, name, amount in items]


def _why(item: Item, direction: str, fields: RequestFields, master: set[str]) -> dict:
    code, name, amount = item
    uses = "; ".join(use.text + (f" · {COALITION_TAG}" if use.coalition else "") for use in fields.uses(code))
    return {"code": code, "name": name, "amount": amount, "direction": direction,
            "master": code.zfill(6) in master, "uses": uses}


def _table(table: Table) -> dict:
    return {"columns": list(table.columns), "rows": [list(row) for row in table.rows]}
