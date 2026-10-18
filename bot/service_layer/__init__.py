"""Service layer: the use cases, and the Unit of Work they commit through.

    services.py      send_job (the daily job), resume_run, render_all, and the test sends:
                     send_pending_test, send_test_message
    analysis.py      refresh_feed, request_analysis, drain_queue: the analysis queue
    unit_of_work.py  UnitOfWork — one Postgres connection; the only place that commits
"""
