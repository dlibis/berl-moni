"""Hebrew text for reportlab, which has no bidi engine: every string must already be in visual
(right-to-left) order before it is drawn.

    rtl(text)              one line, reordered for display
    fix_split_words(text)  repairs words the source PDF's text layer split in two
    wrap_rtl_html(...)     a multi-line paragraph, wrapped first and reordered per line
"""
import re
from xml.sax.saxutils import escape

from bidi.algorithm import get_display
from reportlab.pdfbase.pdfmetrics import stringWidth

# A space the source PDF's text layer put inside a word. Fixed for display only; the extracted
# data keeps it. One known case so far: 'השי נוי' -> 'השינוי'.
_SPLIT_WORDS = ((re.compile(r"הש[יי] נוי"), "השינוי"),)

# The labels that open each program's narrative, bolded so the eye can find them. The optional
# space before the colon covers the 'מטרת השינוי :' variant seen in letters.
_SECTION_LABEL = re.compile(r"^\s*(תיאור הת[ו]?כנית\s*:|מטרת השינוי\s*:)")

# Wrap a little short of the column: stringWidth and reportlab's own line fill can disagree by up
# to a space, and a line reportlab re-wraps gets its last word reversed — the bug wrapping avoids.
_WRAP_SLACK_POINTS = 12


def rtl(text) -> str:
    """`text` in visual order. The right-to-left base keeps a Hebrew label first (rightmost) even
    when the value after it is all digits, e.g. 'מס' תוכנית: 231039'."""
    return get_display(str(text), base_dir="R")


def fix_split_words(text: str) -> str:
    for pattern, word in _SPLIT_WORDS:
        text = pattern.sub(word, text)
    return text


def wrap_rtl_html(text: str, max_width: float, font: str, size: int = 11, bold_labels: bool = False) -> str:
    """`text` wrapped to `max_width` points, each line reordered for display, joined with <br/> — HTML
    for one Paragraph whose lines already fit, so reportlab neither re-wraps nor re-reverses them.

    Reordering a long line and letting reportlab wrap it prints the rows bottom-to-top, so the
    wrapping is done here, on the logical text, and only then is each row reordered."""
    usable = max_width - _WRAP_SLACK_POINTS - stringWidth("  ", font, size)
    html_rows = []
    for line in str(text).split("\n"):
        label = _section_label(line) if bold_labels else None
        for i, row in enumerate(_wrap(line, usable, font, size)):
            html = escape(rtl(row))
            if label and i == 0:  # the label opens the line, so it is on its first row
                shown = escape(rtl(label))
                html = html.replace(shown, f"<b>{shown}</b>", 1)
            html_rows.append(html)
    return "<br/>".join(html_rows)


def _wrap(line: str, width: float, font: str, size: int) -> list[str]:
    """Greedy word wrap of one logical line, by measured width."""
    rows, current = [], ""
    for word in line.split(" "):
        trial = f"{current} {word}".strip()
        if not current or stringWidth(trial, font, size) <= width:
            current = trial
        else:
            rows.append(current)
            current = word
    return rows + [current]


def _section_label(line: str) -> str | None:
    m = _SECTION_LABEL.match(line)
    return m.group(1) if m else None
