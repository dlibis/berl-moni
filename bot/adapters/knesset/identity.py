"""Keyless Google ID tokens for the private Cloud Run fetcher."""
from collections.abc import Callable
from functools import cached_property

import google.auth
from google.auth import identity_pool, impersonated_credentials
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from requests import RequestException

from bot.domain.errors import FeedUnreachable

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class _SubjectToken(identity_pool.SubjectTokenSupplier):
    def __init__(self, token: Callable[[], str | None]):
        self.token = token

    def get_subject_token(self, context, request):
        token = self.token()
        if not token:
            raise GoogleAuthError("Missing Vercel request identity")
        return token


class GoogleIdentity:
    def __init__(self, audience: str, service_account: str, *,
                 provider: str | None = None, subject_token: Callable[[], str | None] | None = None):
        self.audience = audience.rstrip("/")
        self.service_account = service_account
        self.provider = provider
        self.subject_token = subject_token

    @cached_property
    def credentials(self):
        if self.provider:
            source = identity_pool.Credentials(
                audience=f"//iam.googleapis.com/{self.provider}",
                subject_token_type="urn:ietf:params:oauth:token-type:jwt",
                subject_token_supplier=_SubjectToken(self.subject_token), scopes=SCOPES)
        else:
            source, _ = google.auth.default(scopes=SCOPES)
        target = impersonated_credentials.Credentials(
            source_credentials=source, target_principal=self.service_account, target_scopes=SCOPES)
        return impersonated_credentials.IDTokenCredentials(
            target, target_audience=self.audience, include_email=True)

    def __call__(self) -> str:
        try:
            if not self.credentials.valid:
                self.credentials.refresh(Request())
            return self.credentials.token
        except (GoogleAuthError, RequestException):
            # Provider errors can contain credentials; expose only a safe message.
            raise FeedUnreachable("Israeli fetch service: Google authentication failed") from None
