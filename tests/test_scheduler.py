from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event

import psycopg
import pytest
from flask import Flask
from psycopg.rows import dict_row

from common.db import get_setting, set_setting
from common.schedule_due import ISRAEL, eligibility
from web.routes import scheduler
from web.routes.recovery import recovery_bp

HEADERS = {"Authorization": "Bearer test-scheduler-secret"}


@pytest.fixture
def connection(test_db_url):
    def connect():
        return psycopg.connect(test_db_url, row_factory=dict_row)

    with connect() as conn:
        conn.execute("TRUNCATE send_runs RESTART IDENTITY CASCADE")
        conn.execute("TRUNCATE letters, scans")
        conn.execute("DELETE FROM settings WHERE key IN ('schedule', 'always_send', 'fetch_every_hours', "
                     "'last_feed_refresh_at', 'scheduler_last_dispatched_hour')")
    return connect


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("SCHEDULER_SECRET", "test-scheduler-secret")
    app = Flask(__name__)
    app.register_blueprint(scheduler.scheduler_bp)
    return app


def test_authentication_precedes_database_and_github(app, monkeypatch):
    def unexpected():
        pytest.fail("unauthenticated request reached database or GitHub")

    monkeypatch.setattr(scheduler, "connect", unexpected)
    monkeypatch.setattr(scheduler.bootstrap, "dispatch", unexpected)
    with app.test_client() as client:
        for headers in ({}, {"Authorization": "Bearer wrong"}, {"Authorization": "Bearer é"}):
            response = client.get("/api/internal/scheduler/tick", headers=headers)
            assert response.status_code == 401
            assert response.headers["Cache-Control"] == "no-store"
        monkeypatch.delenv("SCHEDULER_SECRET")
        assert client.get("/api/internal/scheduler/tick", headers=HEADERS).status_code == 503


def test_idle_tick_does_not_call_github(app, connection, monkeypatch):
    monkeypatch.setattr(scheduler, "connect", connection)
    monkeypatch.setattr(scheduler.bootstrap, "dispatch", lambda: pytest.fail("idle tick dispatched"))
    response = app.test_client().get("/api/internal/scheduler/tick", headers=HEADERS)
    assert response.json == {"status": "idle"}
    with connection() as conn:
        assert get_setting(conn, scheduler.LAST_DISPATCH) is None


def test_failed_dispatch_retries_then_duplicate_tick_is_suppressed(app, connection, monkeypatch):
    monkeypatch.setattr(scheduler, "connect", connection)
    with connection() as conn:
        set_setting(conn, "fetch_every_hours", 1)
    attempts = []

    def dispatch():
        attempts.append(True)
        return len(attempts) > 1

    monkeypatch.setattr(scheduler.bootstrap, "dispatch", dispatch)
    client = app.test_client()
    assert client.get("/api/internal/scheduler/tick", headers=HEADERS).status_code == 503
    with connection() as conn:
        assert get_setting(conn, scheduler.LAST_DISPATCH) is None
    assert client.get("/api/internal/scheduler/tick", headers=HEADERS).json == {"status": "dispatched"}
    assert client.get("/api/internal/scheduler/tick", headers=HEADERS).json == {"status": "already_dispatched"}
    assert len(attempts) == 2
    with connection() as conn:
        set_setting(conn, scheduler.LAST_DISPATCH, "2000-01-01T00:00:00+00:00")
    assert client.get("/api/internal/scheduler/tick", headers=HEADERS).json == {"status": "dispatched"}


def test_database_failure_is_safe_and_retryable(app, monkeypatch, caplog):
    def broken():
        raise psycopg.OperationalError("secret connection URL")

    monkeypatch.setattr(scheduler, "connect", broken)
    response = app.test_client().get("/api/internal/scheduler/tick", headers=HEADERS)
    assert response.status_code == 503
    assert response.json == {"error": "database_failed"}
    assert "secret connection URL" not in caplog.text


def test_overlapping_ticks_dispatch_once(app, connection, monkeypatch):
    monkeypatch.setattr(scheduler, "connect", connection)
    with connection() as conn:
        set_setting(conn, "fetch_every_hours", 1)
    entered, release = Event(), Event()
    calls = []

    def dispatch():
        calls.append(True)
        entered.set()
        assert release.wait(3)
        return True

    monkeypatch.setattr(scheduler.bootstrap, "dispatch", dispatch)

    def tick():
        with app.test_client() as client:
            return client.get("/api/internal/scheduler/tick", headers=HEADERS).json["status"]

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(tick)
        try:
            assert entered.wait(3)
            second = pool.submit(tick)
        finally:
            release.set()
        assert sorted([first.result(), second.result()]) == ["already_dispatched", "dispatched"]
    assert len(calls) == 1


@pytest.mark.parametrize("month,day", [(3, 22), (3, 29), (10, 18), (10, 25)])
def test_weekly_eligibility_across_daylight_saving_changes(connection, month, day):
    with connection() as conn:
        set_setting(conn, "always_send", True)
        before = datetime(2026, month, day, 8, 59, tzinfo=ISRAEL)
        after = datetime(2026, month, day, 9, tzinfo=ISRAEL)
        assert eligibility(conn, before.astimezone(timezone.utc)) == (False, False)
        assert eligibility(conn, after.astimezone(timezone.utc)) == (True, False)


def test_eligibility_detects_custom_schedule_resume_queue_and_expired_lease(connection):
    now = datetime(2026, 10, 29, 12, tzinfo=ISRAEL)
    with connection() as conn:
        assert eligibility(conn, now) == (False, False)
        schedule = [{"from": "2026-10-01", "to": "2026-10-31", "days": {
            "thu": {"enabled": True, "time": "09:00"}}}]
        set_setting(conn, "schedule", schedule)
        assert eligibility(conn, now) == (True, False)
        conn.execute("INSERT INTO send_runs (day, status, kind, from_address, reply_to_address, batches) "
                     "VALUES ('2026-10-29', 'sent', 'auto', 'a@b', 'r@b', '[]')")
        assert eligibility(conn, now) == (False, False)
        conn.execute("UPDATE send_runs SET status = 'sending', resume_requested_at = now()")
        assert eligibility(conn, now) == (True, False)
        conn.execute("TRUNCATE send_runs CASCADE")
        set_setting(conn, "schedule", [])
        conn.execute("INSERT INTO letters (letter_url, slug, analysis_status) VALUES ('https://example.com/1', '1', 'queued')")
        assert eligibility(conn, now) == (False, True)
        conn.execute("UPDATE letters SET analysis_status = 'analyzing', lease_expires_at = now() + interval '1 hour'")
        assert eligibility(conn, now) == (False, False)
        conn.execute("UPDATE letters SET lease_expires_at = now() - interval '1 minute'")
        assert eligibility(conn, now) == (False, True)


@pytest.mark.parametrize("accepted", [True, False])
def test_resume_commits_before_dispatch_and_keeps_request_on_failure(connection, monkeypatch, accepted):
    from web.routes import recovery

    monkeypatch.setattr(recovery, "connect", connection)
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")

    class Session:
        status_code = 200

        def json(self):
            return {"session": {}, "user": {"id": "test"}}

    monkeypatch.setattr("web.auth.requests.get", lambda *a, **k: Session())
    with connection() as conn:
        run_id = conn.execute("INSERT INTO send_runs (day, status, kind, failed_at, from_address, reply_to_address, batches) "
                              "VALUES (current_date, 'failed', 'auto', now(), 'a@b', 'r@b', '[]') RETURNING id").fetchone()["id"]
    calls = []

    def dispatch():
        with connection() as conn:
            row = conn.execute("SELECT status, resume_requested_at FROM send_runs WHERE id = %s", (run_id,)).fetchone()
            assert row["status"] == "sending" and row["resume_requested_at"] is not None
        calls.append(True)
        return accepted

    monkeypatch.setattr(recovery.bootstrap, "dispatch", dispatch)
    app = Flask(__name__)
    app.register_blueprint(recovery_bp)
    client = app.test_client()
    assert client.post(f"/api/v1/send-runs/{run_id}/resume").json == {"status": "ok"}
    assert client.post(f"/api/v1/send-runs/{run_id}/resume").status_code == 409
    assert len(calls) == 1
