"""Postgres repositories (Cosmic Python ch. 2), one per table the send job owns. Each wraps one open
connection and never commits; the Unit of Work does (bot/service_layer/unit_of_work.py).

    letters.py    LettersRepository   — each scanned feed letter: status, reason, its summary PDF
    send_runs.py  SendRunsRepository  — one row per daily send: recipients, batches, sending/sent/failed
    email_log.py  EmailLogRepository  — every message sent (idempotency key, email count), for budgets
    scans.py      ScansRepository     — one row per job run: what happened, counts only
"""
