"""The one place that loads .env files. Never prints values.

APP_ENV=test loads .env.test over everything else (override, because `flask run`
loads .env before the app imports). Without APP_ENV, only .env loads, and real
environment variables win.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    app_env = os.environ.get("APP_ENV")
    if app_env:
        path = ROOT / f".env.{app_env}"
        if not path.exists():
            raise RuntimeError(f"APP_ENV={app_env} but {path.name} is missing")
        load_dotenv(path, override=True)
    load_dotenv(ROOT / ".env")
