import os
import subprocess
import sys

import psycopg
import pytest
from flask import Flask
from psycopg.rows import dict_row

from web.csrf import register_csrf
from web.routes.mailing_list import mailing_list_bp
from web.routes.recovery import recovery_bp


class SessionResponse:
    status_code = 200
    def json(self):
        return {"session": {"id": "test"}, "user": {"id": "test"}}


@pytest.fixture
def migrated_db(test_db_url):
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = test_db_url
    subprocess.run([sys.executable, "db/migrate.py", "--test"], check=True, env=env)
    return test_db_url


def test_recovery_returns_409_when_row_is_not_failed(migrated_db, monkeypatch):
    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: SessionResponse())
    monkeypatch.setattr("web.routes.recovery.connect", lambda: psycopg.connect(migrated_db, row_factory=dict_row))
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(recovery_bp)
    response = app.test_client().post("/api/v1/send-runs/999999/abandon", json={}, headers={"Origin": "https://berl.site"})
    assert response.status_code == 409


def test_duplicate_address_is_400_and_not_logged(migrated_db, monkeypatch, caplog):
    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: SessionResponse())
    connection = lambda: psycopg.connect(migrated_db, row_factory=dict_row)
    monkeypatch.setattr("web.routes.mailing_list.connect", connection)
    with connection() as conn:
        conn.execute("DELETE FROM mailing_list WHERE email = %s", ("duplicate@example.com",))
        conn.execute("INSERT INTO mailing_list (email) VALUES (%s)", ("duplicate@example.com",))
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(mailing_list_bp)
    response = app.test_client().post("/api/v1/mailing_list", json={"email": "duplicate@example.com"}, headers={"Origin": "https://berl.site"})
    assert response.status_code == 400
    assert "duplicate@example.com" not in caplog.text
    with connection() as conn:
        conn.execute("DELETE FROM mailing_list WHERE email = %s", ("duplicate@example.com",))
