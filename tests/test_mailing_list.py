import psycopg
import pytest
from flask import Flask
from psycopg.rows import dict_row

from tests.test_web_db import SessionResponse
from web.csrf import register_csrf
from web.routes.mailing_list import mailing_list_bp


@pytest.fixture
def client(test_db_url, monkeypatch):
    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: SessionResponse())
    monkeypatch.setattr(
        "web.routes.mailing_list.connect",
        lambda: psycopg.connect(test_db_url, row_factory=dict_row),
    )
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(mailing_list_bp)
    return app.test_client()


def test_post_without_name_is_400(client):
    headers = {"Origin": "https://berl.site"}
    assert client.post("/api/v1/mailing_list", json={"email": "a@example.com"}, headers=headers).status_code == 400


def test_get_returns_names(client, test_db_url):
    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
        conn.execute("DELETE FROM mailing_list")
        conn.execute(
            "INSERT INTO mailing_list (email, name) VALUES (%s, %s)",
            ("z@example.com", "Zee"),
        )
    headers = {"Origin": "https://berl.site"}
    data = client.get("/api/v1/mailing_list", headers=headers).get_json()
    assert data["subscribers"] == [{"email": "z@example.com", "name": "Zee"}]
