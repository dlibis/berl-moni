"""Per-process environment validation and the LLM model setting (plan: Configuration). Never prints values.

Reads os.environ only; the entry point loads .env first (common.env.load_env).
"""
import os

# GITHUB_DISPATCH_TOKEN is optional for `web`: without it the hourly run drains the analysis queue.
REQUIRED = {
    "web": ["DATABASE_URL", "NEON_AUTH_BASE_URL", "SITE_ORIGIN"],
    "send": ["DATABASE_URL", "RESEND_API_KEY", "MODEL"],
    "test_send": ["DATABASE_URL", "RESEND_API_KEY"],
    "render": ["DATABASE_URL", "MODEL"],
}
# The provider's key is checked by bot.bootstrap (pydantic_ai names the variable it wants).
DEFAULT_MODEL = "google:gemini-3.6-flash"


def require(process: str) -> None:
    """Exit with a message naming the first missing variable for `process`."""
    for name in REQUIRED[process]:
        if not os.environ.get(name):
            raise SystemExit(f"{name} is not set (required by {process})")


def llm_model() -> str:
    """MODEL as '<provider>:<model>' (e.g. 'google:gemini-3.6-flash', 'openai:gpt-4o'), or DEFAULT_MODEL.
    The provider reads its own key: GOOGLE_API_KEY (or GEMINI_API_KEY), OPENAI_API_KEY, ANTHROPIC_API_KEY..."""
    return os.environ.get("MODEL") or DEFAULT_MODEL
