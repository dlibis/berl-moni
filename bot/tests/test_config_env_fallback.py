"""Secrets and model settings live ONLY in the environment (.env).

OPENAI_API_KEY -> api key, MONI_SENDER -> sending address, MODEL_* -> model.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.config_manager import ConfigManager  # noqa: E402


def test_api_key_comes_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    assert ConfigManager.get_api_key() == "sk-from-env"


def test_api_key_none_when_env_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert ConfigManager.get_api_key() is None


def test_notifier_comes_from_env(monkeypatch):
    monkeypatch.setenv("MONI_SENDER", "env@example.com")
    assert ConfigManager.get_notifier_email() == "env@example.com"


def test_notifier_none_when_env_missing(monkeypatch):
    monkeypatch.delenv("MONI_SENDER", raising=False)
    assert ConfigManager.get_notifier_email() is None


def test_model_settings_come_from_env(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "gpt-4o")
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    assert ConfigManager.get_model_name() == "gpt-4o"
    assert ConfigManager.get_model_provider() == "openai"
