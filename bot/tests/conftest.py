# The shared fixtures live in the repository-level tests/conftest.py (the `tests` package at the root),
# not in this file: pytest only auto-loads a conftest from a test file's own directory and its parents.
from tests.conftest import neon_test_db_url, test_db_url  # noqa: F401
