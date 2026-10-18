"""Where a letter's money comes from and where it goes, read from its budget table (no drawing).

    sources, destinations, metric = transfer_summary(table)
    groups = hubs(sources, destinations, table)   # [(hub name, its sources)]
    shown, folded = fold(destinations)            # the chart's own rows + those under 'עוד N'

Items are (code, name, amount): amount in thousands of ₪, positive, largest first.
"""
from collections import Counter

import pandas as pd

from bot.domain.extraction import CODE_COLUMN, NAME_COLUMN

Item = tuple[str, str, float]

SHOWN = 5   # the chart and the table name this many destinations; the rest fold into 'עוד N'
INTERNAL_HUB = "העברה פנימית"


def transfer_summary(table: pd.DataFrame) -> tuple[list[Item], list[Item], str]:
    """(sources, destinations, metric): each item's net change in the first metric, summed over its
    occurrences — sources lost money, destinations gained it. An item that nets to zero (money
    passing through, like the general reserve) is left out."""
    metrics = [c.removesuffix(" from") for c in table.columns if str(c).endswith(" from")]
    if not metrics or table.empty:
        return [], [], ""
    metric = metrics[0]
    change = (pd.to_numeric(table[f"{metric} to"], errors="coerce")
              - pd.to_numeric(table[f"{metric} from"], errors="coerce")).fillna(0)
    codes = table[CODE_COLUMN].astype(str)
    net = change.groupby(codes).sum()
    names = table.groupby(codes)[NAME_COLUMN].first()
    items = [(code, str(names[code]).strip(), amount) for code, amount in net.items() if round(amount)]
    sources = sorted(((c, n, -a) for c, n, a in items if a < 0), key=lambda i: -i[2])
    destinations = sorted(((c, n, a) for c, n, a in items if a > 0), key=lambda i: -i[2])
    return sources, destinations, metric


def hubs(sources: list[Item], destinations: list[Item], table: pd.DataFrame) -> list[tuple[str, list[Item]]]:
    """The sources split by how their money travels. Sources in the destinations' own budget section
    (the first two digits) move money inside the ministry; the others come from outside — through
    the general reserve when the letter routes it there. The letter never pairs a source with a
    destination, so the chart joins them only through these hubs. Empty hubs are dropped."""
    if not destinations:
        return [("", sources)] if sources else []
    section = Counter(code[:2] for code, _, _ in destinations).most_common(1)[0][0]
    via_reserve = table[NAME_COLUMN].astype(str).str.contains("רזרבה").any()
    groups = [("רזרבה כללית" if via_reserve else "ממקורות אחרים", [s for s in sources if s[0][:2] != section]),
              (INTERNAL_HUB, [s for s in sources if s[0][:2] == section])]
    return [(name, items) for name, items in groups if items]


def fold(items: list[Item]) -> tuple[list[Item], list[Item]]:
    """(shown, folded): the largest SHOWN items and the rest; folding a single item gains nothing."""
    return (items[:SHOWN], items[SHOWN:]) if len(items) > SHOWN + 1 else (items, [])
