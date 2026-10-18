import psycopg
import pytest
from flask import Flask
from psycopg.rows import dict_row

from common.db import get_setting
from tests.test_schedule_due import EVERY_DAY
from tests.test_web_db import SessionResponse
from web.csrf import register_csrf
from web.routes.schedule import schedule_bp

EVERY_DAY_AT_10 = [{**EVERY_DAY[0], "days": {k: {**v, "time": "10:00"} for k, v in EVERY_DAY[0]["days"].items()}}]


@pytest.fixture
def conn(test_db_url):
    with psycopg.connect(test_db_url, row_factory=dict_row, autocommit=True) as conn:
        conn.execute("DELETE FROM settings WHERE key IN ('schedule', 'auto_since')")
        yield conn


@pytest.fixture
def post_schedule(test_db_url, monkeypatch):
    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: SessionResponse())
    monkeypatch.setattr("web.routes.schedule.connect", lambda: psycopg.connect(test_db_url, row_factory=dict_row))
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(schedule_bp)
    client = app.test_client()

    def post(schedule):
        response = client.post("/api/v1/schedule", json={"schedule": schedule}, headers={"Origin": "https://berl.site"})
        assert response.status_code == 200
    return post


def test_reenabling_schedule_resets_auto_since(post_schedule, conn):
    post_schedule(EVERY_DAY)
    first = get_setting(conn, "auto_since")
    post_schedule([])
    assert get_setting(conn, "auto_since") is None
    post_schedule(EVERY_DAY)
    assert get_setting(conn, "auto_since") > first


def test_editing_a_configured_schedule_keeps_auto_since(post_schedule, conn):
    post_schedule(EVERY_DAY)
    first = get_setting(conn, "auto_since")
    post_schedule(EVERY_DAY_AT_10)
    assert get_setting(conn, "auto_since") == first
