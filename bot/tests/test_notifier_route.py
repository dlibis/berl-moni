import pytest
from flask import Flask

from web.csrf import register_csrf
from web.routes.notifier import notifier_bp


class Response:
    status_code = 200

    def json(self):
        return {"session": {"id": "test"}, "user": {"id": "test"}}


class Connection:
    def __init__(self):
        self.settings = {"from_address": "", "reply_to_address": ""}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params):
        if sql.startswith("SELECT"):
            self.row = {"value": self.settings.get(params[0], "")}
        else:
            self.settings[params[0]] = params[1].obj
            self.row = None
        return self

    def fetchone(self):
        return self.row


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("NEON_AUTH_BASE_URL", "https://auth.example")
    monkeypatch.setenv("SITE_ORIGIN", "https://berl.site")
    monkeypatch.setattr("web.auth.requests.get", lambda *args, **kwargs: Response())
    connection = Connection()
    monkeypatch.setattr("web.routes.notifier.connect", lambda: connection)
    app = Flask(__name__)
    register_csrf(app)
    app.register_blueprint(notifier_bp)
    return app.test_client(), connection


def test_notifier_round_trip(client):
    http, connection = client
    response = http.post("/api/v1/notifier", json={"from_address": "NEWS@BERL.SITE", "reply_to_address": "Staff@Example.com"}, headers={"Origin": "https://berl.site"})
    assert response.status_code == 200
    assert connection.settings == {"from_address": "news@berl.site", "reply_to_address": "staff@example.com"}
    assert http.get("/api/v1/notifier").get_json() == connection.settings


@pytest.mark.parametrize("sender,reply", [("x@example.com", "a@example.com"), ("x@berl.site", "invalid"), ("UP PER@berl.site", "a@example.com")])
def test_notifier_validation(client, sender, reply):
    http, _ = client
    response = http.post("/api/v1/notifier", json={"from_address": sender, "reply_to_address": reply}, headers={"Origin": "https://berl.site"})
    assert response.status_code == 400
