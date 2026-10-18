"""Adapters: one package per outside system; each file does one job against it.

    knesset/      feed.py           fetch_letter_urls — pending letters' PDF URLs from the Knesset API
    letter_pdf/   download.py       local_copy — the PDF on disk (downloads + caches a URL)
                  reader.py         PdfDocument — text, tables and OCR from a local PDF
                  parser.py         BudgetLetter — the letter's budget table, history, letterhead, links
                  loader.py         open_letter — download → read → parse; the Extractor's `load`
    llm/          letter_analyzer.py  LlmAnalyzer — the one model call: coalition judgment + what each program's money is for
    summary_pdf/  renderer.py       SummaryPdfRenderer.render — lays out a letter's summary PDF
                  flow_chart.py     flow_chart — the money's sources -> hubs -> destinations picture
                  money_flow.py     transfer_summary / hubs / fold — the money's flow, no drawing
                  theme.py          font, colors, money format
                  hebrew_text.py    rtl / wrap_rtl_html — Hebrew in visual order (reportlab has no bidi)
    postgres/     letters.py        LettersRepository — the `letters` table
                  send_runs.py      SendRunsRepository — the `send_runs` table
                  email_log.py      EmailLogRepository — the `email_log` table (budgets, idempotency)
                  scans.py          ScansRepository — the `scans` table (one row per job run)
    resend/       email_sender.py   send_email — one email with attachments through the Resend API
"""
