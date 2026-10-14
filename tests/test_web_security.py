import requests
import pytest
from flask import Flask

from web.csrf import register_csrf
from web.routes import register_routes


class Response:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self.body = body

    def json(self):
        return self.body


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    app = Flask(__name__)
    register_csrf(app)
    register_routes(app)
    return app


def test_session_cookie_forwarded(app, monkeypatch):
    seen = {}
    def get(url, **kwargs):
        seen.update(url=url, **kwargs)
        return Response(200, {"session": {"id": "s"}, "user": {"id": "u"}})
    monkeypatch.setattr("web.auth.requests.get", get)
    with app.test_request_context(headers={"Cookie": "session=abc"}):
        from web.auth import require_session
        assert require_session(lambda: "ok")() == "ok"
    assert seen == {"url": "https://auth.example/get-session", "headers": {"Cookie": "session=abc"}, "timeout": 5}


@pytest.mark.parametrize("response,status", [(Response(200, None), 401), (Response(200, {"session": None, "user": None}), 401), (Response(401, {}), 401), (Response(503, {}), 503)])
def test_session_failures(app, monkeypatch, response, status):
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: response)
    assert app.test_client().get("/api/v1/status").status_code == status


def test_session_timeout_is_503(app, monkeypatch):
    def timeout(*_args, **_kwargs):
        raise requests.Timeout()
    monkeypatch.setattr("web.auth.requests.get", timeout)
    assert app.test_client().get("/api/v1/status").status_code == 503


def test_every_v1_route_requires_session(app, monkeypatch):
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: Response(200, None))
    client = app.test_client()
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/api/v1/"):
            path = rule.rule.replace("<old_code>", "1").replace("<code>", "1").replace("<path:email>", "a@example.com").replace("<slug>", "letter").replace("<int:run_id>", "1")
            method = next(iter(rule.methods - {"HEAD", "OPTIONS"}))
            response = client.open(path, method=method, json={} if method != "GET" else None, headers={"Origin": "https://berl.site"})
            assert response.status_code == 401, (rule.rule, method)


def test_every_v1_post_rejects_cross_origin(app):
    client = app.test_client()
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/api/v1/") and "POST" in rule.methods:
            path = rule.rule.replace("<slug>", "letter").replace("<int:run_id>", "1")
            assert client.post(path, json={}, headers={"Origin": "https://evil.example"}).status_code == 403


def test_json_content_type_required(app):
    response = app.test_client().post("/api/v1/notifier", data="x", headers={"Origin": "https://berl.site", "Content-Type": "text/plain"})
    assert response.status_code == 403
