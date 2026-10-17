"""Service layer: the use cases, and the Unit of Work they commit through.

    services.py      send_job (the daily job), resume_run, mark_seen, render_all, and the test sends:
                     send_pending_test, send_test_message
    unit_of_work.py  UnitOfWork — one Postgres connection; the only place that commits
"""
