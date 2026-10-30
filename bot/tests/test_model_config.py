"""One MODEL setting ('<provider>:<model>') picks the model; the provider's own key is checked at startup."""
import pytest

from bot import bootstrap
from common.config import DEFAULT_MODEL, llm_model, require


def test_model_comes_from_env(monkeypatch):
    monkeypatch.setenv("MODEL", "openai:gpt-4o")
    assert llm_model() == bootstrap.model_name() == "openai:gpt-4o"
    monkeypatch.delenv("MODEL")
    assert llm_model() == DEFAULT_MODEL


def test_send_requires_model(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "x")
    monkeypatch.setenv("RESEND_API_KEY", "x")
    monkeypatch.delenv("MODEL", raising=False)
    with pytest.raises(SystemExit, match="MODEL is not set"):
        require("send")


def test_bootstrap_extractor_uses_model_and_its_key(monkeypatch):
    monkeypatch.setenv("MODEL", "google:gemini-2.5-pro")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-gemini")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    extractor = bootstrap.extractor({"000001": "x"})
    assert extractor.analyze.model.model_name == "gemini-2.5-pro"
    assert extractor.visual_scan.keywords["model"] is extractor.analyze.model


def test_missing_provider_key_fails_at_startup(monkeypatch):
    monkeypatch.setenv("MODEL", "openai:gpt-4o")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(Exception, match="OPENAI_API_KEY"):
        bootstrap.extractor({"000001": "x"})
