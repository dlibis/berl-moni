
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
        conn.execute("INSERT INTO mailing_list (email, name) VALUES (%s, %s)", ("duplicate@example.com", "Dup"))
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(mailing_list_bp)
    response = app.test_client().post("/api/v1/mailing_list", json={"email": "duplicate@example.com", "name": "Other"}, headers={"Origin": "https://berl.site"})
    assert response.status_code == 400
    assert "duplicate@example.com" not in caplog.text
    with connection() as conn:
        conn.execute("DELETE FROM mailing_list WHERE email = %s", ("duplicate@example.com",))


def test_delete_recipient_uses_json_body(migrated_db, monkeypatch):
    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: SessionResponse())
    connection = lambda: psycopg.connect(migrated_db, row_factory=dict_row)
    monkeypatch.setattr("web.routes.mailing_list.connect", connection)
    with connection() as conn:
        conn.execute("DELETE FROM mailing_list WHERE email = %s", ("gone@example.com",))
        conn.execute("INSERT INTO mailing_list (email, name) VALUES (%s, %s)", ("gone@example.com", "Gone"))
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(mailing_list_bp)
    client = app.test_client()
    headers = {"Origin": "https://berl.site"}
    assert client.delete("/api/v1/mailing_list", json={"email": "gone@example.com"}, headers=headers).status_code == 200
    assert client.delete("/api/v1/mailing_list", json={"email": "gone@example.com"}, headers=headers).status_code == 404
    with connection() as conn:
        assert conn.execute("SELECT email FROM mailing_list WHERE email = %s", ("gone@example.com",)).fetchone() is None
