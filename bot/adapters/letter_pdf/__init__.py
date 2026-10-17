"""Letter PDFs: from a feed URL to the parts of a budget-transfer letter, one step per file.

    download.py  local_copy — a local path for the PDF (downloads and caches a URL, with retries);
                 save_copy — copy it somewhere
    reader.py    PdfDocument — reads a local PDF: bidi-fixed text, tables, OCR for scans
    parser.py    BudgetLetter — a letter's budget table, budget history, letterhead, decision links
    loader.py    open_letter — the three above, chained: what the Extractor gets as `load`
"""
