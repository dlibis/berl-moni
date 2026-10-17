"""FR-4 — load_programs returns {six-digit code: program name} from Neon (read-only)."""

from common.db import connect, load_programs


def test_load_programs_returns_code_map(neon_test_db_url):
    # Needs the test branch seeded by seed_programs.py --test.
    with connect(neon_test_db_url) as conn:
        programs = load_programs(conn)
    assert len(programs) >= 100
    assert all(len(code) == 6 and code.isdigit() for code in programs)
    assert "045110" in programs
    assert "פרויקטים" in programs["045110"]


def test_load_programs_is_deterministic(neon_test_db_url):
    with connect(neon_test_db_url) as conn:
        assert load_programs(conn) == load_programs(conn)
