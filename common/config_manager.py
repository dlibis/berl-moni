import os

from common.env import load_env

load_env()


class ConfigManager:
    """Environment-only settings for the bot.

    Everything else (programs, mailing list, schedule, addresses) lives in Neon; see common.db.
    Model settings and secrets come from the environment (loaded from the project-root .env):
      MODEL_NAME            -> get_model_name()
      MODEL_PROVIDER        -> get_model_provider()  (openai / google_genai; unset = openai)
      OPENAI_API_KEY        -> get_api_key()  (provider openai / unset)
      GEMINI_API_KEY        -> get_api_key()  (provider google_genai)
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
