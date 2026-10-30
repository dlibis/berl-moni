"""The Vercel web bundle: the app and the summary renderer import without the bot-only packages."""
import json
import os
import subprocess
import sys
from pathlib import Path

BLOCKED = ("pandas", "numpy", "pydantic_ai", "pdfplumber", "pymupdf4llm", "openai")
SCRIPT = f"""
import sys, importlib.abc
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name.split('.')[0] in {BLOCKED!r} or name.startswith(('bot.adapters.llm', 'bot.adapters.letter_pdf')):
            raise ImportError('blocked: ' + name)
sys.meta_path.insert(0, Block())
import web.app, web.routes.letters, web.bootstrap
from bot.tests.fixtures.extractions import complete_extraction
pdf = web.bootstrap.ports().render(complete_extraction(), {{"200102": "b"}})
assert pdf.startswith(b"%PDF")
"""


def test_web_app_and_render_need_no_bot_only_packages():
    env = {**os.environ, "DATABASE_URL": "postgresql://x", "NEON_AUTH_BASE_URL": "https://a", "SITE_ORIGIN": "https://b"}
    r = subprocess.run([sys.executable, "-c", SCRIPT], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_vercel_ships_render_and_fonts_not_llm():
    cfg = json.loads(Path("vercel.json").read_text())["services"]["api"]["functions"]["web/app.py"]
    assert cfg["maxDuration"] == 300
    assert "bot/**" not in cfg["excludeFiles"] and "bot/adapters/llm/**" in cfg["excludeFiles"]
    assert "summary_pdf" not in cfg["excludeFiles"]
