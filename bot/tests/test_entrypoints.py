"""Every program in bot/entrypoints imports and parses --help (they have no other unit tests)."""
import importlib
import pkgutil

import pytest

import bot.entrypoints

NAMES = [m.name for m in pkgutil.iter_modules(bot.entrypoints.__path__)]


@pytest.mark.parametrize("name", NAMES)
def test_entrypoint_imports_and_has_help(name, capsys):
    module = importlib.import_module(f"bot.entrypoints.{name}")
    assert module.__doc__ and callable(module.main)
    with pytest.raises(SystemExit):
        module.parse_args(["--help"])
    assert "usage:" in capsys.readouterr().out


def test_every_entrypoint_is_found():
    assert set(NAMES) == {"main", "run_url", "send_test_mail"}
