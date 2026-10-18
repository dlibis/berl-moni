"""Composition root (Cosmic Python ch. 13): the one place that loads .env, configures logging and
builds the real adapters. Nothing else in bot/ reads the environment or wires dependencies.
"""
import logging

from bot.adapters.knesset.feed import fetch_letters
from bot.adapters.letter_pdf.download import save_copy
from bot.adapters.letter_pdf.loader import open_letter
from bot.adapters.llm.letter_analyzer import LlmAnalyzer
from bot.adapters.resend.email_sender import send_email
from bot.adapters.summary_pdf.renderer import SummaryPdfRenderer
from bot.domain.extraction import Extractor
from bot.service_layer.services import Ports
from common.config import llm_settings
from common.env import load_env


def setup() -> None:
    """Process-wide setup, once per entry point: .env, then logging."""
    load_env()
    logging.basicConfig(level=logging.INFO)
    # httpx logs every request line (incl. the OpenAI call) at INFO — quiet it so it
    # doesn't drown the app's own logs; keep warnings/errors.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    # pdfminer (under pdfplumber) warns "Could not get FontBBox" for PDFs whose font
    # descriptors omit a FontBBox; it doesn't affect text/table output.
    logging.getLogger("pdfminer").setLevel(logging.ERROR)


def extractor(programs: dict) -> Extractor:
    """The Extractor with the configured model (MODEL_NAME, MODEL_PROVIDER, its key)."""
    return Extractor(programs, analyze=LlmAnalyzer(**llm_settings()), load=open_letter)


def ports() -> Ports:
    return Ports(feed=fetch_letters, extractor=extractor, render=SummaryPdfRenderer().render, send_email=send_email,
                 save_copy=save_copy)
