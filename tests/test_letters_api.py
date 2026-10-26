from datetime import date

import psycopg
import pytest
from flask import Flask, g, jsonify
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from bot.adapters.github.dispatch import dispatch_workflow
from bot.domain.versions import analysis_version
from bot.tests.fixtures.extractions import complete_extraction, complete_irrelevant_extraction
from web.auth import require_session
from bot.domain.errors import FeedUnreachable
from bot.service_layer.services import Ports
from bot.service_layer.unit_of_work import UnitOfWork
from common.db import set_setting
from web.csrf import register_csrf
from web.routes.status import status_bp
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
        conn.execute("DELETE FROM settings WHERE key IN ('schedule', 'fetch_every_hours', 'auto_since')")
        conn.execute("INSERT INTO programs (code, name) VALUES ('200102', 'b')")
    return connection


@pytest.fixture
def client(db, test_db_url, monkeypatch):
    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: SessionResponse())
    monkeypatch.setattr("web.routes.letters.connect", db)
    monkeypatch.setattr("web.routes.status.connect", db)
    monkeypatch.setattr("web.bootstrap.uow", lambda: UnitOfWork(test_db_url))
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(letters_bp)
    app.register_blueprint(status_bp)

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


def test_search_ministry_and_request_numbers_before_pagination(client, db):
    insert(db, 1)
    insert(db, 2, status="failed")
    insert(db, 3)
    with db() as conn:
        conn.execute("UPDATE letters SET ministry = %s, request_numbers = %s WHERE slug IN ('s1', 's2')",
                     ("משרד ראש הממשלה", ["13-212,83-226,04-234", "199 עד 201"]))
    for term in ("ראש הממשלה", "13-212", "83-226", "04-234", "199", "201"):
        result = client.get("/api/v1/letters", query_string={"search": term, "page_size": 1}).get_json()
        assert result["total"] == 2 and len(result["items"]) == 1
    result = client.get("/api/v1/letters", query_string={"search": " הממשלה ", "status": "failed"}).get_json()
    assert [item["slug"] for item in result["items"]] == ["s2"]
    for term in ("missing", "%", "_", "' OR true --"):
        assert client.get("/api/v1/letters", query_string={"search": term}).get_json() == {"items": [], "total": 0}
    assert client.get("/api/v1/letters", query_string={"search": "  "}).get_json()["total"] == 3


def test_bad_query_is_400(client):
    assert client.get("/api/v1/letters?page_size=500").status_code == 400
    assert client.get("/api/v1/letters?status=nope").status_code == 400
    assert client.get("/api/v1/letters?page=0").status_code == 400
    assert client.get("/api/v1/letters?page=x").status_code == 400


def test_detail_has_report_only_when_analyzed(client, analyzed_relevant, discovered):
    assert client.get(f"/api/v1/letters/{analyzed_relevant}").get_json()["report"]["summary"]
    assert client.get(f"/api/v1/letters/{discovered}").get_json()["report"] is None
    assert client.get("/api/v1/letters/unknown").status_code == 404


def test_derived_flags_and_filters(client, db):
    insert(db, 1, complete_extraction(), "m|prompt:0|schema:1", "analyzed")
    incomplete = complete_extraction()
    incomplete.fields = None
    insert(db, 2, incomplete, analysis_version("m"), "analyzed")
    insert(db, 3)
    insert(db, 4, status="queued")
    insert(db, 5, status="analyzing")
    items = {i["slug"]: i for i in client.get("/api/v1/letters").get_json()["items"]}
    assert items["s1"]["relevant"] and items["s1"]["complete"] and items["s1"]["outdated"]
    assert items["s1"]["requires_review"] is False and items["s1"]["passed"] is False
    assert items["s2"]["needs_analysis"] and not items["s2"]["outdated"]
    assert not items["s3"]["relevant"] and not items["s3"]["outdated"] and items["s3"]["request_numbers"] == []
    not_analyzed = {i["slug"] for i in client.get("/api/v1/letters?status=not_analyzed").get_json()["items"]}
    assert not_analyzed == {"s3", "s4", "s5"}
    assert [i["slug"] for i in client.get("/api/v1/letters?status=needs_analysis").get_json()["items"]] == ["s2"]
    for bad in ("sent", "outdated", "queued"):
        assert client.get(f"/api/v1/letters?status={bad}").status_code == 400


def test_complete_not_relevant_is_false_and_in_irrelevant_filter(client, db):
    slug = insert(db, 200, complete_irrelevant_extraction(), analysis_version("m"), "analyzed")
    insert(db, 201, status="failed")
    items = {i["slug"]: i for i in client.get("/api/v1/letters").get_json()["items"]}
    assert items[slug]["relevant"] is False
    assert items[slug]["complete"] is True
    irrelevant = {i["slug"] for i in client.get("/api/v1/letters?status=irrelevant").get_json()["items"]}
    assert slug in irrelevant
    assert "s201" not in irrelevant


def test_manual_flags_and_requires_review_filter(client, db, monkeypatch):
    slug = insert(db, 50)
    assert client.get(f"/api/v1/letters/{slug}").get_json()["passed"] is False
    r = client.patch(f"/api/v1/letters/{slug}", json={"requires_review": True, "passed": True}, headers=ORIGIN)
    assert r.status_code == 200
    body = r.get_json()
    assert body["requires_review"] is True and body["passed"] is True
    filtered = client.get("/api/v1/letters?status=requires_review").get_json()["items"]
    assert [i["slug"] for i in filtered] == [slug]
    monkeypatch.setattr("web.bootstrap.dispatch", lambda: True)
    client.post(f"/api/v1/letters/{slug}/analyze", json={}, headers=ORIGIN)
    assert client.get(f"/api/v1/letters/{slug}").get_json()["requires_review"] is True


def test_session_user_reaches_g(client):
    assert client.get("/test/user").get_json() == {"user": "a@example.com"}


def test_dispatch_without_token_is_false():
    assert dispatch_workflow(None, "dlibis/berl-moni") is False


ORIGIN = {"Origin": "https://berl.site"}


@pytest.fixture
def fake_ports(db, monkeypatch):
    with db() as conn:
        conn.execute("DELETE FROM email_log")
        conn.execute("DELETE FROM send_runs")
        conn.execute("DELETE FROM mailing_list")
        conn.execute("INSERT INTO mailing_list (email) VALUES ('m@x.org')")
        set_setting(conn, "from_address", "moni@berl.site")
        set_setting(conn, "reply_to_address", "r@x.org")
    sent = []
    monkeypatch.setattr("web.bootstrap.ports", lambda: Ports(
        feed=None, extractor=None, render=lambda extraction, programs: b"%PDF-1.7 fake",
        send_email=lambda **kwargs: sent.append(kwargs) or f"id{len(sent)}", save_copy=None))
    return sent


def test_analyze_queues_and_reports_dispatch_failure(client, discovered, monkeypatch):
    monkeypatch.setattr("web.bootstrap.dispatch", lambda: False)
    r = client.post(f"/api/v1/letters/{discovered}/analyze", json={}, headers=ORIGIN)
    assert r.status_code == 202 and r.get_json() == {"status": "queued", "dispatch_failed": True}
    assert client.post(f"/api/v1/letters/{discovered}/analyze", json={}, headers=ORIGIN).status_code == 409


def test_analyze_done_and_unknown(client, analyzed_relevant, monkeypatch):
    monkeypatch.setattr("web.bootstrap.dispatch", lambda: True)
    r = client.post(f"/api/v1/letters/{analyzed_relevant}/analyze", json={}, headers=ORIGIN)
    assert (r.status_code, r.get_json()) == (200, {"status": "done"})
    r = client.post(f"/api/v1/letters/{analyzed_relevant}/reanalyze", json={}, headers=ORIGIN)
    assert (r.status_code, r.get_json()) == (202, {"status": "queued", "dispatch_failed": False})
    assert client.post("/api/v1/letters/nope/analyze", json={}, headers=ORIGIN).status_code == 404


def test_send_confirm_flow(client, analyzed_relevant, fake_ports):
    assert client.post(f"/api/v1/letters/{analyzed_relevant}/send", json={}, headers=ORIGIN).status_code == 200
    r = client.post(f"/api/v1/letters/{analyzed_relevant}/send", json={}, headers=ORIGIN)
    assert (r.status_code, r.get_json()["error"]) == (409, "confirm_resend")
    assert client.post(f"/api/v1/letters/{analyzed_relevant}/send", json={"resend": True}, headers=ORIGIN).status_code == 200
    assert len(fake_ports) == 2


def test_send_refusals(client, discovered, fake_ports):
    r = client.post(f"/api/v1/letters/{discovered}/send", json={}, headers=ORIGIN)
    assert (r.status_code, r.get_json()) == (409, {"error": "not_sendable"})
    assert client.post("/api/v1/letters/nope/send", json={}, headers=ORIGIN).status_code == 404


def test_refresh_counts_and_auto_since(client, monkeypatch):
    from bot.domain.feed import FeedLetter
    monkeypatch.setattr("web.bootstrap.ports", lambda: Ports(
        feed=lambda: [FeedLetter("https://example.test/f.pdf", date(2026, 1, 1), "m", ("1",), ())],
        extractor=None, render=None, send_email=None, save_copy=None))
    r = client.post("/api/v1/letters/refresh", json={}, headers=ORIGIN)
    assert (r.status_code, r.get_json()) == (200, {"new": 1, "seen": 0})
    assert client.get("/api/v1/status").get_json()["last_feed_refresh_at"]
    r = client.post("/api/v1/letters/refresh", json={}, headers=ORIGIN)
    assert r.get_json() == {"new": 0, "seen": 1}


def test_refresh_after_the_schedule_ended_does_not_queue_paid_analysis(client, monkeypatch, test_db_url):
    from bot.domain.feed import FeedLetter
    from common.db import set_setting
    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:  # auto_since stays set when a range runs out
        set_setting(conn, "auto_since", "2000-01-01T00:00:00+00:00")
        set_setting(conn, "schedule", [{"from": "2000-01-01", "to": "2000-01-02",
                                        "days": {"mon": {"enabled": True, "time": "09:00"}}}])
    monkeypatch.setattr("web.bootstrap.ports", lambda: Ports(
        feed=lambda: [FeedLetter("https://example.test/g.pdf", date(2026, 1, 1), "m", ("1",), ())],
        extractor=None, render=None, send_email=None, save_copy=None))
    client.post("/api/v1/letters/refresh", json={}, headers=ORIGIN)
    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
        row = conn.execute("SELECT analysis_status FROM letters WHERE letter_url = 'https://example.test/g.pdf'").fetchone()
    assert row["analysis_status"] == "discovered"


def test_refresh_queues_when_only_fetch_cadence_is_on(client, monkeypatch, test_db_url):
    from bot.domain.feed import FeedLetter
    from common.db import set_setting
    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
        set_setting(conn, "schedule", [])
        set_setting(conn, "fetch_every_hours", 1)
    monkeypatch.setattr("web.bootstrap.ports", lambda: Ports(
        feed=lambda: [FeedLetter("https://example.test/h.pdf", date(2026, 1, 1), "m", ("1",), ())],
        extractor=None, render=None, send_email=None, save_copy=None))
    client.post("/api/v1/letters/refresh", json={}, headers=ORIGIN)
    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
        row = conn.execute("SELECT analysis_status FROM letters WHERE letter_url = 'https://example.test/h.pdf'").fetchone()
    assert row["analysis_status"] == "queued"


def test_refresh_feed_down_is_502(client, monkeypatch):
    def down():
        raise FeedUnreachable("page 1")
    monkeypatch.setattr("web.bootstrap.ports", lambda: Ports(
        feed=down, extractor=None, render=None, send_email=None, save_copy=None))
    r = client.post("/api/v1/letters/refresh", json={}, headers=ORIGIN)
    assert (r.status_code, r.get_json()) == (502, {"error": "feed_unreachable"})


def test_post_without_origin_is_rejected(client, discovered):
    assert client.post(f"/api/v1/letters/{discovered}/analyze", json={}).status_code == 403


def test_retry_route_is_gone(client):
    assert client.post("/api/v1/letters/x/retry", json={}, headers=ORIGIN).status_code == 404


def test_status_has_no_failed_letters(client):
    assert "failed_letters" not in client.get("/api/v1/status").get_json()
