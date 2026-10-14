import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# One .env resolution for the whole app (bot, web, tests, gmail_auth): the nearest .env up
# the tree, falling back to the project root when none exists yet. Never overrides real env vars.
ENV_PATH = Path(find_dotenv() or Path(__file__).resolve().parent.parent / ".env")
load_dotenv(ENV_PATH)


class ConfigManager:
    """Environment-only settings for the bot and Gmail helpers.

    Everything else (programs, mailing list, schedule, addresses) lives in Neon; see common.db.
    Model settings and secrets come from the environment (loaded from the project-root .env):
      MODEL_NAME            -> get_model_name()
      MODEL_PROVIDER        -> get_model_provider()  (openai / google_genai; unset = openai)
      OPENAI_API_KEY        -> get_api_key()  (provider openai / unset)
      GEMINI_API_KEY        -> get_api_key()  (provider google_genai)
      MONI_SENDER           -> get_notifier_email()
      GOOGLE_CLIENT_ID      -> get_google_client_id()
      GOOGLE_CLIENT_SECRET  -> get_google_client_secret()
      GOOGLE_REFRESH_TOKEN  -> get_google_refresh_token()
    """

    API_KEY_ENV_BY_PROVIDER = {
        "openai": "OPENAI_API_KEY",
        "google_genai": "GEMINI_API_KEY",
    }

    @staticmethod
    def get_model_name() -> str | None:
        return os.environ.get("MODEL_NAME") or None

    @staticmethod
    def get_model_provider() -> str | None:
        return os.environ.get("MODEL_PROVIDER") or None

    @staticmethod
    def get_api_key() -> str | None:
        """The LLM key for the configured provider. Unknown/unset provider -> OpenAI."""
        provider = ConfigManager.get_model_provider() or "openai"
        return os.environ.get(ConfigManager.API_KEY_ENV_BY_PROVIDER.get(provider, "OPENAI_API_KEY")) or None

    @staticmethod
    def get_notifier_email() -> str | None:
        """Sending Gmail address, from MONI_SENDER in the environment / .env only."""
        return os.environ.get("MONI_SENDER") or None

    @staticmethod
    def get_google_client_id() -> str | None:
        """OAuth client id from the Google Cloud Console (GOOGLE_CLIENT_ID)."""
        return os.environ.get("GOOGLE_CLIENT_ID") or None

    @staticmethod
    def get_google_client_secret() -> str | None:
        """OAuth client secret from the Google Cloud Console (GOOGLE_CLIENT_SECRET)."""
        return os.environ.get("GOOGLE_CLIENT_SECRET") or None

    @staticmethod
    def get_google_refresh_token() -> str | None:
        """Refresh token written by bot/gmail_auth.py (GOOGLE_REFRESH_TOKEN)."""
        return os.environ.get("GOOGLE_REFRESH_TOKEN") or None
