"""FR-4 — load_programs returns {six-digit code: program name} from Neon (read-only)."""
import os
import sys

# Make the project root importable so `common` resolves (mirrors bot/main.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.db import connect, load_programs  # noqa: E402


def test_load_programs_returns_code_map(test_db_url):
    # Needs the test branch seeded by seed_programs.py --test.
    with connect(test_db_url) as conn:
        programs = load_programs(conn)
    assert len(programs) >= 100
    assert all(len(code) == 6 and code.isdigit() for code in programs)
    assert "045110" in programs
    assert "פרויקטים" in programs["045110"]


def test_load_programs_is_deterministic(test_db_url):
    with connect(test_db_url) as conn:
        assert load_programs(conn) == load_programs(conn)
