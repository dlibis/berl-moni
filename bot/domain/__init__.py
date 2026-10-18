"""Domain: the rules, with no I/O and no imports from the other layers.

    extraction.py      Extractor — reads a letter's request fields and decides relevance (master codes)
    request_fields.py  RequestFields — the typed fields of one letter, with their Hebrew labels
    table.py           Table — a plain table (columns + rows), the budget table and history without pandas
    money_flow.py      transfer_summary / hubs / fold — where the money comes from and goes (no drawing)
    send_plan.py       attachment batches, recipient chunks, the email budget, idempotency keys
    slug.py            letter_slug — a letter's short id for file names
    errors.py          the failures the use cases tell apart (raised by adapters)
"""
