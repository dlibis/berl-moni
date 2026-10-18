"""The summary PDF's font, colors and money format, shared by the page and its flow chart."""
from pathlib import Path

from reportlab.lib import colors

# Arimo (SIL OFL, fonts/OFL.txt): Hebrew + Latin, Arial's metrics. Bundled so the PDF renders the
# same on macOS and on the GitHub Actions runner.
FONT = "Hebrew"
FONT_PATH = Path(__file__).parent / "fonts" / "Arimo[wght].ttf"

INK = colors.HexColor("#1f1f1f")
MUTED = colors.HexColor("#6b6b6b")
MASTER_BLUE = colors.HexColor("#2a78d6")   # a program on the master list
SOURCE_RED = colors.HexColor("#c0392b")    # money leaving a program
DEST_GREEN = colors.HexColor("#1a7f4b")    # money reaching a program
HUB_GREY = colors.HexColor("#8a8a8a")
COALITION_ORANGE = "#b35c00"
HEAD_TINT = colors.HexColor("#eef3fb")     # header rows and label cells
RULE = colors.HexColor("#d0d0d0")          # lines between rows

UNIT = "אלפי ש״ח"   # every amount in a letter is in thousands of shekels


def money(thousands: float) -> str:
    """A letter's figure as printed, with its unit: '139,917 אלפי ש״ח'."""
    return f"{abs(thousands):,.0f} {UNIT}"
