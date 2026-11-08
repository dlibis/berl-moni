"""Web composition root (Cosmic Python ch. 13): the adapters the Flask routes hand to the use cases.

Unlike bot.bootstrap it imports no LLM, OCR or PDF-parsing adapter (they are not in the Vercel bundle);
the renderer is imported on the first render, in the send path."""
import os
from functools import cache

from flask import request

from bot.adapters.github.dispatch import dispatch_workflow
from bot.adapters.knesset.feed import fetch_approvals, fetch_letters
from bot.adapters.knesset.identity import GoogleIdentity
from bot.adapters.knesset.remote import KnessetClient
from bot.adapters.resend.email_sender import send_email
from bot.domain.extraction import Extraction
from bot.service_layer.services import Ports
from bot.service_layer.unit_of_work import UnitOfWork


def uow() -> UnitOfWork:
    return UnitOfWork()


def dispatch() -> bool:
    """Start the worker workflow; False leaves work queued for the hourly scheduler."""
    return dispatch_workflow(os.environ.get("GITHUB_DISPATCH_TOKEN"),
                             os.environ.get("GITHUB_REPOSITORY", "dlibis/berl-moni"))


@cache
def _renderer():
    from bot.adapters.summary_pdf.renderer import SummaryPdfRenderer
    return SummaryPdfRenderer()


def render(extraction: Extraction, programs: dict[str, str]) -> bytes:
    return _renderer().render(extraction, programs)


def _not_in_web(*args, **kwargs):
    raise RuntimeError("analysis runs in the worker, not in the web app")


def ports() -> Ports:
    url = os.environ.get("KNESSET_FETCH_URL")
    account = os.environ.get("KNESSET_FETCH_SERVICE_ACCOUNT")
    identity = GoogleIdentity(
        url, account, provider=os.environ.get("KNESSET_FETCH_IDENTITY_PROVIDER"),
        subject_token=lambda: request.headers.get("x-vercel-oidc-token")) if url and account else None
    client = KnessetClient(url, os.environ.get("KNESSET_FETCH_TOKEN", ""), identity) if url else None
    feed = client.fetch_letters if client else fetch_letters
    return Ports(feed=feed, extractor=_not_in_web, render=render, send_email=send_email,
                 save_copy=_not_in_web, approvals=client.fetch_approvals if client else fetch_approvals)
