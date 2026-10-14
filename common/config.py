"""Per-process environment validation (plan: Configuration). Never prints values."""
import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED = {
    "web": ["DATABASE_URL", "NEON_AUTH_BASE_URL", "SITE_ORIGIN"],
    "check": ["DATABASE_URL"],
    "send": ["DATABASE_URL", "RESEND_API_KEY", "MODEL_NAME", "MODEL_PROVIDER"],
}
PROVIDER_KEYS = {"google_genai": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}


def require(process: str) -> None:
    """Exit with a message naming the first missing or invalid variable for `process`."""
    names = list(REQUIRED[process])
    if process == "send":
        provider = os.environ.get("MODEL_PROVIDER")
        if provider and provider not in PROVIDER_KEYS:
            raise SystemExit(f"MODEL_PROVIDER must be one of {', '.join(PROVIDER_KEYS)}")
        if provider:
            names.append(PROVIDER_KEYS[provider])
    for name in names:
        if not os.environ.get(name):
            raise SystemExit(f"{name} is not set (required by {process})")
