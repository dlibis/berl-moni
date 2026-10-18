"""Every status and failure reason the job writes, in one place. Each is a state the status screen
shows, and each must match its column's CHECK constraint (tests/test_postgres_repositories.py checks).

    letters.status    pending → sent, or irrelevant / failed (with a LetterReason)
    send_runs.status  sending → sent, or failed (a person resumes or abandons it)
    scans.status      one per job run: sent / nothing_new / failed (with a ScanReason)
"""
from typing import Literal

LetterStatus = Literal["pending", "irrelevant", "failed", "sent"]
LetterReason = Literal["quota", "network", "provider_5xx", "extract_error", "render_error", "no_text",
                       "pdf_too_large"]
AnalysisStatus = Literal["discovered", "queued", "analyzing", "analyzed", "failed"]
RunStatus = Literal["sending", "sent", "failed", "abandoned"]
SendKind = Literal["auto", "manual"]
ScanStatus = Literal["sent", "nothing_new", "failed"]
ScanReason = Literal["missing_settings", "list_over_cap", "feed_unreachable", "quota", "over_budget",
                     "resend_error", "send_run_stuck"]
EmailKind = Literal["letter", "test"]
EmailStatus = Literal["sending", "sent", "unknown"]
