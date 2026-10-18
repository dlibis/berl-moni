import base64
import logging

import pytest
import requests

from bot.adapters.resend import email_sender

ADDRESSES = ("news@example.com", "staff@example.com", "a@example.com", "b@example.com")
SEND = dict(from_address="news@example.com", reply_to="staff@example.com",
            bcc=["a@example.com", "b@example.com"], attachments=[("letter.pdf", b"%PDF-1")],
            subject="s", html="<p>h</p>", idempotency_key="run1-b0-c0")


class Response:
    def __init__(self, status, body=None):
        self.status_code = status
        self.ok = 200 <= status < 300
        self.body = body or {}

    def json(self):
        return self.body


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")


def test_success_posts_once_with_idempotency_key_and_base64(monkeypatch):
    calls = []
    monkeypatch.setattr(email_sender.requests, "post",
                        lambda url, **kw: calls.append((url, kw)) or Response(200, {"id": "em_1"}))
    email_sender.send_email(**SEND)
    [(url, kw)] = calls
    assert url == "https://api.resend.com/emails"
    assert kw["timeout"] == 60
    assert kw["headers"] == {"Authorization": "Bearer re_test", "Idempotency-Key": "run1-b0-c0"}
    assert kw["json"]["to"] == ["staff@example.com"] and kw["json"]["bcc"] == SEND["bcc"]
    assert kw["json"]["attachments"] == [{"filename": "letter.pdf", "content": base64.b64encode(b"%PDF-1").decode()}]


def test_returns_resend_email_id(monkeypatch):
    monkeypatch.setattr(email_sender.requests, "post", lambda *a, **kw: Response(200, {"id": "em_123"}))
    assert email_sender.send_email(**SEND) == "em_123"


def test_422_raises_without_address(monkeypatch, caplog):
    body = {"name": "validation_error", "message": "invalid to a@example.com"}
    monkeypatch.setattr(email_sender.requests, "post", lambda *a, **kw: Response(422, body))
    with caplog.at_level(logging.DEBUG), pytest.raises(email_sender.ResendError) as exc:
        email_sender.send_email(**SEND)
    assert exc.value.status == 422 and "validation_error" in str(exc.value)
    assert not any(a in str(exc.value) or a in caplog.text for a in ADDRESSES)


def test_timeout_raises(monkeypatch, caplog):
    def boom(*a, **kw):
        raise requests.Timeout("timed out talking to a@example.com")
    monkeypatch.setattr(email_sender.requests, "post", boom)
    with caplog.at_level(logging.DEBUG), pytest.raises(email_sender.ResendError) as exc:
        email_sender.send_email(**SEND)
    assert exc.value.status is None and "Timeout" in str(exc.value)
    assert not any(a in str(exc.value) or a in caplog.text for a in ADDRESSES)
