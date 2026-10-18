"""Per-process environment validation and the LLM settings (plan: Configuration). Never prints values.

Reads os.environ only; the entry point loads .env first (common.env.load_env).
"""
import os

# GITHUB_DISPATCH_TOKEN is optional for `web`: without it the hourly run drains the analysis queue.
REQUIRED = {
    "web": ["DATABASE_URL", "NEON_AUTH_BASE_URL", "SITE_ORIGIN"],
    "check": ["DATABASE_URL"],
    "send": ["DATABASE_URL", "RESEND_API_KEY", "MODEL_NAME", "MODEL_PROVIDER"],
    "test_send": ["DATABASE_URL", "RESEND_API_KEY"],
    "render": ["DATABASE_URL", "MODEL_NAME", "MODEL_PROVIDER"],
}
PROVIDER_KEYS = {"google_genai": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}


def require(process: str) -> None:
    """Exit with a message naming the first missing or invalid variable for `process`."""
    names = list(REQUIRED[process])
    if "MODEL_PROVIDER" in names:
        provider = os.environ.get("MODEL_PROVIDER")
        if provider and provider not in PROVIDER_KEYS:
            raise SystemExit(f"MODEL_PROVIDER must be one of {', '.join(PROVIDER_KEYS)}")
        if provider:
            names.append(PROVIDER_KEYS[provider])
    for name in names:
        if not os.environ.get(name):
            raise SystemExit(f"{name} is not set (required by {process})")


def llm_settings() -> dict:
    """{model, provider, api_key} for bot.adapters.llm.letter_analyzer.LlmAnalyzer. Unset provider -> openai's key."""
    provider = os.environ.get("MODEL_PROVIDER") or None
    return {
        "model": os.environ.get("MODEL_NAME") or None,
        "provider": provider,
        "api_key": os.environ.get(PROVIDER_KEYS.get(provider or "openai", "OPENAI_API_KEY")) or None,
    }
