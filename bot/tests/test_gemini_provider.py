"""Provider switch: the API key and default model follow MODEL_PROVIDER."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "bot"))

from common.config_manager import ConfigManager  # noqa: E402
import agent  # noqa: E402


def _set_provider(monkeypatch, provider):
    if provider:
        monkeypatch.setenv("MODEL_PROVIDER", provider)
    else:
        monkeypatch.delenv("MODEL_PROVIDER", raising=False)


def test_gemini_provider_uses_gemini_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-gemini")
    _set_provider(monkeypatch, "google_genai")
    assert ConfigManager.get_api_key() == "AIza-gemini"


def test_openai_provider_uses_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-gemini")
    _set_provider(monkeypatch, "openai")
    assert ConfigManager.get_api_key() == "sk-openai"
    _set_provider(monkeypatch, None)
    assert ConfigManager.get_api_key() == "sk-openai"  # default


def test_missing_gemini_key_is_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    _set_provider(monkeypatch, "google_genai")
    assert ConfigManager.get_api_key() is None


def test_agent_default_model_follows_provider():
    assert agent.Agent(set(), provider="google_genai").model == agent.DEFAULT_MODELS["google_genai"]
    assert agent.Agent(set(), provider="openai").model == agent.DEFAULT_MODELS["openai"]
    assert agent.Agent(set()).model == agent.DEFAULT_MODEL
    assert agent.Agent(set(), provider="google_genai", model="gemini-2.5-pro").model == "gemini-2.5-pro"


def test_agent_from_config_passes_provider_and_gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-gemini")
    _set_provider(monkeypatch, "google_genai")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    # Don't depend on the DB: the master set is not what's under test.
    monkeypatch.setattr(agent, "load_programs", lambda: {"000001": "x"})
    a = agent.Agent.from_config()
    assert a.provider == "google_genai"
    assert a.api_key == "AIza-gemini"
    assert a.model == agent.DEFAULT_MODELS["google_genai"]
