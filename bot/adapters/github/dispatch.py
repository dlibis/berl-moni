"""GitHub Actions dispatch: dispatch_workflow() starts the letters worker (`mode: drain`) through the
REST API (https://docs.github.com/rest/actions/workflows#create-a-workflow-dispatch-event).

A failed dispatch is not an error for the caller: work stays queued for the hourly scheduler.
Logs the HTTP status only, never the token."""
import logging

import requests

logger = logging.getLogger(__name__)


def dispatch_workflow(token: str | None, repo: str, workflow: str = "letters.yml", ref: str = "main") -> bool:
    """True iff GitHub accepted the dispatch (204)."""
    if not token:
        return False
    try:
        response = requests.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/dispatches",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"ref": ref, "inputs": {"mode": "drain"}}, timeout=10)
    except requests.RequestException:
        logger.warning("workflow dispatch failed: request error")
        return False
    if response.status_code != 204:
        logger.warning("workflow dispatch failed: HTTP %s", response.status_code)
        return False
    return True
