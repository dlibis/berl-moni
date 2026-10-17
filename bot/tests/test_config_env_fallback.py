"""Secrets and model settings live ONLY in the environment (.env).

OPENAI_API_KEY -> api key, MODEL_* -> model.
"""
from common.config import llm_settings


def test_api_key_comes_from_env(monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    assert llm_settings()["api_key"] == "sk-from-env"


def test_api_key_none_when_env_missing(monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert llm_settings()["api_key"] is None


def test_model_settings_come_from_env(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "gpt-4o")
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    assert (llm_settings()["model"], llm_settings()["provider"]) == ("gpt-4o", "openai")
