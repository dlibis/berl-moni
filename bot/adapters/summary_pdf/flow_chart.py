"""The money-flow chart: flow_chart(...) draws sources (right) -> hubs (middle) -> destinations (left).

Band thickness is the amount. Every node is labelled in full beside it — name (blue for a master
program), amount, code — so nothing has to be looked up in a legend. The letter never says which
source pays which destination, so sources pour into their hub and the destinations fan out of the
hub column as a whole.
"""
from reportlab.graphics.shapes import Drawing, Path, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth

from bot.adapters.summary_pdf.hebrew_text import rtl, wrap
from bot.domain.money_flow import Item
from bot.adapters.summary_pdf.theme import (DEST_GREEN, FONT, HUB_GREY, INK, MASTER_BLUE, MUTED,
                                            SOURCE_RED, money)

LABEL_W = 4.6 * cm      # the labels' column on each side
LINE = 9.5              # points per label line
NODE_W, GAP = 7, 6      # node bar width, space between node slots
BAND_HEIGHT = 6.5 * cm  # the hub column's height; the labels set the drawing's height
TOP, BOTTOM = 34, 18    # room for the column titles / the lower hub's label
SOURCE_BAND = colors.Color(0.75, 0.22, 0.17, 0.28)
DEST_BAND = colors.Color(0.10, 0.50, 0.29, 0.28)


def flow_chart(hubs: list[tuple[str, list[Item]]], shown: list[Item], folded: list[Item],
               master: set[str], width: float) -> Drawing:
    """`hubs` is [(hub name, its sources)]; `shown` the destinations drawn one by one and `folded`
    those merged into one 'עוד N תוכניות' node."""
    sources = [item for _, items in hubs for item in items]   # grouped by hub: bands never cross
    destinations = list(shown)
    if folded:
        destinations.append(("", f"עוד {len(folded)} תוכניות", sum(a for _, _, a in folded)))
    total = sum(a for _, _, a in destinations)
    k = BAND_HEIGHT / total                                   # points per thousand ₪

    _, src_h = _place(sources, k, 0, master)
    _, dst_h = _place(destinations, k, 0, master)
    height = max(src_h, dst_h, total * k) + TOP + BOTTOM
    top = height - TOP
    src_nodes, _ = _place(sources, k, top, master)
    dst_nodes, _ = _place(destinations, k, top, master)
    x_src, x_dst = width - LABEL_W - 8 - NODE_W, LABEL_W + 8
    x_hub = (x_src + x_dst) / 2 - NODE_W / 2
    d = Drawing(width, height)

    # the hubs: one contiguous column, vertically centred; sources pour into their own hub
    hub_top = top - (top - BOTTOM - total * k) / 2
    y = hub_top
    nodes = iter(src_nodes)
    for i, (name, items) in enumerate(hubs):
        h = sum(a for _, _, a in items) * k
        d.add(Rect(x_hub, y - h, NODE_W, h, fillColor=HUB_GREY, strokeColor=colors.white, strokeWidth=1))
        y_in = y
        for _ in items:
            (_, _, a), node_top, node_bottom, _ = next(nodes)
            d.add(_band(x_hub + NODE_W, y_in, y_in - a * k, x_src, node_top, node_bottom, SOURCE_BAND))
            y_in -= a * k
        _hub_label(d, x_hub + NODE_W / 2, y + 5 if i == 0 else y - h - 11,   # first above, second below
                   f"{name} · {money(sum(a for _, _, a in items))}")
        y -= h
    for (code, name, amount), node_top, node_bottom, mid in src_nodes:
        d.add(Rect(x_src, node_bottom, NODE_W, node_top - node_bottom, fillColor=SOURCE_RED, strokeColor=None))
        _label(d, x_src + NODE_W + 5, mid, code, name, amount, master, "start")

    # the destinations fan out of the hub column, largest first
    y_out = hub_top
    for (code, name, amount), node_top, node_bottom, mid in dst_nodes:
        d.add(_band(x_dst + NODE_W, node_top, node_bottom, x_hub, y_out, y_out - amount * k, DEST_BAND))
        y_out -= amount * k
        d.add(Rect(x_dst, node_bottom, NODE_W, node_top - node_bottom, fillColor=DEST_GREEN, strokeColor=None))
        _label(d, x_dst - 5, mid, code, name, amount, master, "end")

    for x, title, anchor in ((width, "מאיפה מגיע הכסף", "end"), (0, "לאן הולך הכסף", "start")):
        d.add(String(x, height - 10, rtl(title), fontName=FONT, fontSize=11, textAnchor=anchor, fillColor=INK))
    return d


def _label_lines(code: str, name: str, amount: float, master: set[str]) -> list[tuple[str, float, colors.Color]]:
    """(text, size, color) per line: the full name, the amount, then the code small."""
    lines = [(line, 8.5, MASTER_BLUE if code in master else INK) for line in wrap(name, LABEL_W, FONT, 8.5)]
    lines.append((money(amount), 8.5, INK))
    if code:
        lines.append((f"תוכנית {code}", 6.5, MUTED))
    return lines


def _label(d: Drawing, x: float, mid: float, code, name, amount, master, anchor: str) -> None:
    lines = _label_lines(code, name, amount, master)
    y = mid + (len(lines) - 1) * LINE / 2
    for text, size, color in lines:
        d.add(String(x, y - 3, rtl(text), fontName=FONT, fontSize=size, textAnchor=anchor, fillColor=color))
        y -= LINE


def _hub_label(d: Drawing, x: float, y: float, text: str) -> None:
    """Centred on the hub, on a white patch so the bands behind it don't show through."""
    shown = rtl(text)
    w = stringWidth(shown, FONT, 8.5)
    d.add(Rect(x - w / 2 - 3, y - 3, w + 6, 12, fillColor=colors.white, strokeColor=None))
    d.add(String(x, y, shown, fontName=FONT, fontSize=8.5, textAnchor="middle", fillColor=INK))


def _place(items: list[Item], k: float, top: float, master: set[str]):
    """Stack nodes down from `top`, each in a slot tall enough for its label.
    Returns ([(item, node top, node bottom, slot middle)], the stack's height)."""
    out, y = [], top
    for item in items:
        h = item[2] * k
        slot = max(h, len(_label_lines(*item, master)) * LINE + 2)
        node_top = y - (slot - h) / 2
        out.append((item, node_top, node_top - h, y - slot / 2))
        y -= slot + GAP
    return out, top - y - GAP


def _band(x0, y0_top, y0_bottom, x1, y1_top, y1_bottom, color) -> Path:
    """A filled band from the edge [y0_top, y0_bottom] at x0 to [y1_top, y1_bottom] at x1."""
    mx = (x0 + x1) / 2
    p = Path(fillColor=color, strokeColor=None)
    p.moveTo(x0, y0_top)
    p.curveTo(mx, y0_top, mx, y1_top, x1, y1_top)
    p.lineTo(x1, y1_bottom)
    p.curveTo(mx, y1_bottom, mx, y0_bottom, x0, y0_bottom)
    p.closePath()
    return p
