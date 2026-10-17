"""Provider switch: the API key and default model follow MODEL_PROVIDER."""
from bot import bootstrap
from bot.adapters.llm.letter_analyzer import DEFAULT_MODEL, DEFAULT_MODELS, LlmAnalyzer
from common.config import llm_settings


def _set_provider(monkeypatch, provider):
    if provider:
        monkeypatch.setenv("MODEL_PROVIDER", provider)
    else:
        monkeypatch.delenv("MODEL_PROVIDER", raising=False)


def test_gemini_provider_uses_gemini_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-gemini")
    _set_provider(monkeypatch, "google_genai")
    assert llm_settings()["api_key"] == "AIza-gemini"


def test_openai_provider_uses_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-gemini")
    _set_provider(monkeypatch, "openai")
    assert llm_settings()["api_key"] == "sk-openai"
    _set_provider(monkeypatch, None)
    assert llm_settings()["api_key"] == "sk-openai"  # default


def test_missing_gemini_key_is_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    _set_provider(monkeypatch, "google_genai")
    assert llm_settings()["api_key"] is None


def test_default_model_follows_provider():
    assert LlmAnalyzer(provider="google_genai").model == DEFAULT_MODELS["google_genai"]
    assert LlmAnalyzer(provider="openai").model == DEFAULT_MODELS["openai"]
    assert LlmAnalyzer().model == DEFAULT_MODEL
    assert LlmAnalyzer(provider="google_genai", model="gemini-2.5-pro").model == "gemini-2.5-pro"


def test_bootstrap_extractor_passes_provider_and_gemini_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-gemini")
    _set_provider(monkeypatch, "google_genai")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    analyze = bootstrap.extractor({"000001": "x"}).analyze
    assert (analyze.provider, analyze.api_key, analyze.model) == \
        ("google_genai", "AIza-gemini", DEFAULT_MODELS["google_genai"])
