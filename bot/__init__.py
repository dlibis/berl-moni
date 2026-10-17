"""The budget-letter bot, in Cosmic Python's layers (dependencies point down this list, never up):

    entrypoints/    command-line programs: parse flags, call bootstrap, run one use case
    bootstrap.py    wires the real adapters into the use cases; loads .env and logging
    service_layer/  the use cases (the send job and its variants) and the Unit of Work
    adapters/       everything that talks to the outside world: Knesset, PDFs, the LLM, Postgres, Resend
    domain/         the rules: letter extraction, relevance, send planning — no I/O
"""
