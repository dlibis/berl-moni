"""open_letter(source): get one letter PDF (downloading a URL) and parse it into a BudgetLetter. This
is the Extractor's `load`, and the one place the three letter_pdf steps are chained."""
from bot.adapters.letter_pdf.download import local_copy
from bot.adapters.letter_pdf.parser import BudgetLetter
from bot.adapters.letter_pdf.reader import PdfDocument


def open_letter(source: str, *, request_for=None) -> BudgetLetter:
    return BudgetLetter(PdfDocument(local_copy(source, request_for=request_for)), source)
