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
        conn.execute("DELETE FROM settings WHERE key IN ('schedule', 'auto_since', 'fetch_every_hours', 'fetch_schedule')")
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


def test_schedule_accepts_occurrence_count(post_schedule, conn):
    post_schedule([{**EVERY_DAY[0], "count": 3}])
    assert get_setting(conn, "schedule")[0]["count"] == 3


def test_fetch_every_hours_round_trips(test_db_url, monkeypatch, conn):
    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: SessionResponse())
    monkeypatch.setattr("web.routes.schedule.connect", lambda: psycopg.connect(test_db_url, row_factory=dict_row))
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(schedule_bp)
    client = app.test_client()
    headers = {"Origin": "https://berl.site"}
    empty = client.get("/api/v1/schedule")
    assert empty.status_code == 200 and empty.get_json()["fetch_every_hours"] is None
    body = {"schedule": [], "fetch_every_hours": 6}
    saved = client.post("/api/v1/schedule", json=body, headers=headers)
    assert saved.status_code == 200 and saved.get_json()["fetch_every_hours"] == 6
    assert get_setting(conn, "fetch_every_hours") == 6
    assert client.get("/api/v1/schedule").get_json()["fetch_every_hours"] == 6
    client.post("/api/v1/schedule", json={"schedule": EVERY_DAY}, headers=headers)
    assert get_setting(conn, "fetch_every_hours") == 6
    off = client.post("/api/v1/schedule", json={"schedule": [], "fetch_every_hours": None}, headers=headers)
    assert off.status_code == 200 and off.get_json()["fetch_every_hours"] is None
    bad = client.post("/api/v1/schedule", json={"schedule": [], "fetch_every_hours": 2}, headers=headers)
    assert bad.status_code == 400


def test_editing_a_configured_schedule_keeps_auto_since(post_schedule, conn):
    post_schedule(EVERY_DAY)
    first = get_setting(conn, "auto_since")
    post_schedule(EVERY_DAY_AT_10)
    assert get_setting(conn, "auto_since") == first


def test_fetch_schedule_round_trip_and_validation(post_schedule, conn):
    # Use the same authenticated Flask configuration as the fixture.
    app = Flask(__name__)
    app.register_blueprint(schedule_bp)
    client = app.test_client()
    config = {"days": ["sun", "thu"], "mode": "specific", "time": "09:00"}
    response = client.post("/api/v1/schedule", json={"schedule": [], "fetch_schedule": config})
    assert response.status_code == 200
    assert response.json["fetch_schedule"] == config
    assert client.get("/api/v1/schedule").json["fetch_schedule"] == config
    post_schedule([])
    assert get_setting(conn, "fetch_schedule") == config
    bad = {**config, "days": []}
    assert client.post("/api/v1/schedule", json={"schedule": [], "fetch_schedule": bad}).status_code == 400
    assert get_setting(conn, "fetch_schedule") == config
    assert client.post("/api/v1/schedule", json={"schedule": [], "fetch_schedule": None}).status_code == 200
    assert client.get("/api/v1/schedule").json["fetch_schedule"] is None
    assert client.post("/api/v1/schedule", json={"schedule": [], "fetch_every_hours": 6}).status_code == 200
    assert client.get("/api/v1/schedule").json["fetch_schedule"]["interval_hours"] == 6
