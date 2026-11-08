from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from flask import Flask
from google.auth.exceptions import GoogleAuthError
from google.oauth2.credentials import Credentials

from bot.adapters.knesset.identity import GoogleIdentity, _SubjectToken
from bot.adapters.knesset.remote import KnessetClient
from bot.domain.errors import FeedUnreachable

URL = "https://fetch.example"
ACCOUNT = "caller@example.iam.gserviceaccount.com"


def test_identity_reuses_token_and_refreshes_before_expiry(monkeypatch):
    token = Credentials("first-id-token")
    token.token = "first-id-token"
    token.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
    token.refresh = Mock(side_effect=lambda request: setattr(token, "token", "fresh-id-token"))
    factory = Mock(return_value=token)
    monkeypatch.setattr("google.auth.default", Mock(return_value=(Credentials("source-token"), None)))
    monkeypatch.setattr("google.auth.impersonated_credentials.IDTokenCredentials", factory)
    identity = GoogleIdentity(URL + "/", ACCOUNT)
    assert identity() == identity() == "first-id-token"
    token.refresh.assert_not_called()
    token.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=30)
    assert identity() == "fresh-id-token"
    token.refresh.assert_called_once()
    assert factory.call_args.kwargs == {"target_audience": URL, "include_email": True}


def test_vercel_subject_is_read_from_each_current_request():
    app = Flask(__name__)
    from flask import request
    supplier = _SubjectToken(lambda: request.headers.get("x-vercel-oidc-token"))
    for value in ["first", "rotated"]:
        with app.test_request_context(headers={"x-vercel-oidc-token": value}):
            assert supplier.get_subject_token(None, None) == value
    with app.test_request_context(), pytest.raises(GoogleAuthError):
        supplier.get_subject_token(None, None)


def test_vercel_uses_federation_instead_of_default_credentials(monkeypatch):
    default = Mock(side_effect=AssertionError("must not fall back to ADC"))
    monkeypatch.setattr("google.auth.default", default)
    identity = GoogleIdentity(URL, ACCOUNT, provider="projects/123/locations/global/workloadIdentityPools/p/providers/v",
                              subject_token=lambda: "vercel-subject")
    # Construct the real SDK credentials without making a network request.
    assert identity.credentials.token is None
    default.assert_not_called()


def test_web_bootstrap_uses_runtime_header_instead_of_build_token(monkeypatch):
    from web import bootstrap
    monkeypatch.setenv("KNESSET_FETCH_URL", URL)
    monkeypatch.setenv("KNESSET_FETCH_TOKEN", "app-token")
    monkeypatch.setenv("KNESSET_FETCH_SERVICE_ACCOUNT", ACCOUNT)
    monkeypatch.setenv("KNESSET_FETCH_IDENTITY_PROVIDER", "production-provider")
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", "stale-build-token")
    supplied = []

    def identity(url, account, *, provider, subject_token):
        assert (url, account, provider) == (URL, ACCOUNT, "production-provider")
        def token():
            supplied.append(subject_token())
            return "google-token"
        return token

    monkeypatch.setattr(bootstrap, "GoogleIdentity", identity)
    response = Mock()
    response.json.return_value = []
    monkeypatch.setattr("bot.adapters.knesset.remote.Session.get", Mock(return_value=response))
    with Flask(__name__).test_request_context(headers={"x-vercel-oidc-token": "runtime-token"}):
        assert bootstrap.ports().feed() == []
    assert supplied == ["runtime-token"]


@pytest.mark.parametrize("path", ["feed", "approvals", "pdf"])
def test_all_fetch_requests_keep_app_token_and_add_google_identity(monkeypatch, path):
    response = Mock()
    response.json.return_value = []
    get = Mock(return_value=response)
    monkeypatch.setattr("bot.adapters.knesset.remote.Session.get", get)
    client = KnessetClient(URL, "app-token", lambda: "google-token")
    if path == "pdf":
        headers = dict(client.pdf_request("https://fs.knesset.gov.il/a.pdf").header_items())
    else:
        getattr(client, "fetch_letters" if path == "feed" else "fetch_approvals")()
        headers = get.call_args.kwargs["headers"]
    assert {k.lower(): v for k, v in headers.items()} == {
        "authorization": "Bearer app-token", "x-serverless-authorization": "Bearer google-token"}


@pytest.mark.parametrize("path", ["feed", "approvals", "pdf"])
def test_identity_failure_never_sends_a_request_or_exposes_provider_error(monkeypatch, path):
    monkeypatch.setattr("google.auth.default", Mock(side_effect=GoogleAuthError("secret-provider-details")))
    get = Mock()
    monkeypatch.setattr("bot.adapters.knesset.remote.Session.get", get)
    client = KnessetClient(URL, "app-token", GoogleIdentity(URL, ACCOUNT))
    with pytest.raises(FeedUnreachable, match="Google authentication failed") as error:
        if path == "pdf":
            client.pdf_request("https://fs.knesset.gov.il/a.pdf")
        else:
            getattr(client, "fetch_letters" if path == "feed" else "fetch_approvals")()
    assert "secret-provider-details" not in str(error.value)
    assert error.value.__suppress_context__
    get.assert_not_called()
