from datetime import date

import psycopg
import pytest
from flask import Flask, g, jsonify
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from bot.adapters.github.dispatch import dispatch_workflow
from bot.domain.versions import analysis_version
from bot.tests.fixtures.extractions import complete_extraction
from web.auth import require_session
from web.csrf import register_csrf
from web.routes.letters import letters_bp


class SessionResponse:
    status_code = 200
    def json(self):
        return {"session": {"id": "test"}, "user": {"id": "u1", "email": "a@example.com"}}


@pytest.fixture
def db(test_db_url):
    connection = lambda: psycopg.connect(test_db_url, row_factory=dict_row)
    with connection() as conn:
        conn.execute("TRUNCATE letters, programs RESTART IDENTITY CASCADE")
        conn.execute("INSERT INTO programs (code, name) VALUES ('200102', 'b')")
    return connection


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: SessionResponse())
    monkeypatch.setattr("web.routes.letters.connect", db)
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(letters_bp)

    @app.get("/test/user")
    @require_session
    def echo_user():
        return jsonify({"user": g.user})

    return app.test_client()


def insert(db, n: int, extraction=None, version=None, status="discovered", day=None) -> str:
    slug = f"s{n}"
    with db() as conn:
        conn.execute(
            "INSERT INTO letters (letter_url, slug, analysis_status, letter_date, extraction, codes, extraction_version) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (f"https://example.test/{n}.pdf", slug, status, day or date(2026, 1, 1 + n % 28),
             Jsonb(extraction.to_json()) if extraction else None,
             sorted(extraction.codes()) if extraction else None, version))
    return slug


@pytest.fixture
def seed(db):
    for n in range(27):
        insert(db, n)
    for n in range(27, 30):
        insert(db, n, complete_extraction(), analysis_version("m"), "analyzed")


@pytest.fixture
def analyzed_relevant(db):
    return insert(db, 100, complete_extraction(), analysis_version("m"), "analyzed")


@pytest.fixture
def discovered(db):
    return insert(db, 101)


def test_list_pages_and_filters(client, seed):           # seed: 30 letters, 3 relevant
    r = client.get("/api/v1/letters?page=2&page_size=25").get_json()
    assert r["total"] == 30 and len(r["items"]) == 5
    assert client.get("/api/v1/letters?status=relevant").get_json()["total"] == 3


def test_page_past_the_end_is_empty(client, seed):
    r = client.get("/api/v1/letters?page=9").get_json()
    assert r == {"items": [], "total": 30}


def test_bad_query_is_400(client):
    assert client.get("/api/v1/letters?page_size=500").status_code == 400
    assert client.get("/api/v1/letters?status=nope").status_code == 400
    assert client.get("/api/v1/letters?page=0").status_code == 400
    assert client.get("/api/v1/letters?page=x").status_code == 400


def test_detail_has_report_only_when_analyzed(client, analyzed_relevant, discovered):
    assert client.get(f"/api/v1/letters/{analyzed_relevant}").get_json()["report"]["summary"]
    assert client.get(f"/api/v1/letters/{discovered}").get_json()["report"] is None
    assert client.get("/api/v1/letters/unknown").status_code == 404


def test_derived_flags_and_outdated_filter(client, db):
    insert(db, 1, complete_extraction(), "m|prompt:0|schema:1", "analyzed")
    incomplete = complete_extraction()
    incomplete.fields = None
    insert(db, 2, incomplete, analysis_version("m"), "analyzed")
    insert(db, 3)
    items = {i["slug"]: i for i in client.get("/api/v1/letters").get_json()["items"]}
    assert items["s1"]["relevant"] and items["s1"]["complete"] and items["s1"]["outdated"]
    assert items["s2"]["needs_analysis"] and not items["s2"]["outdated"]
    assert not items["s3"]["relevant"] and not items["s3"]["outdated"] and items["s3"]["request_numbers"] == []
    assert [i["slug"] for i in client.get("/api/v1/letters?status=outdated").get_json()["items"]] == ["s1"]
    assert [i["slug"] for i in client.get("/api/v1/letters?status=needs_analysis").get_json()["items"]] == ["s2"]


def test_session_user_reaches_g(client):
    assert client.get("/test/user").get_json() == {"user": "a@example.com"}


def test_dispatch_without_token_is_false():
    assert dispatch_workflow(None, "dlibis/berl-moni") is False
