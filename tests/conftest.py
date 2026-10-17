"""Two test databases:

- `test_db_url`: a local Postgres 18 (same major version as Neon), migrated once per session.
  Start it with
      docker run -d --name moni-test-pg -p 54318:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_DB=moni_test postgres:18
  or point LOCAL_TEST_DATABASE_URL elsewhere. Each test truncates what it uses.
- `neon_test_db_url`: the Neon test branch (TEST_DATABASE_URL in .env), only for what needs Neon or
  its seeded data: the migrations on Neon, the real program list, the golden letters.
"""
import os
import subprocess
import sys

import psycopg
import pytest
from dotenv import load_dotenv

load_dotenv()

LOCAL_URL = os.environ.get("LOCAL_TEST_DATABASE_URL", "postgresql://postgres:test@localhost:54318/moni_test")


def migrate(url: str) -> None:
    subprocess.run([sys.executable, "db/migrate.py", "--test"], check=True,
                   env={**os.environ, "TEST_DATABASE_URL": url}, capture_output=True)


@pytest.fixture(scope="session")
def test_db_url():
    try:
        psycopg.connect(LOCAL_URL, connect_timeout=3).close()
    except psycopg.OperationalError:
        pytest.fail(f"local test Postgres is not reachable at {LOCAL_URL}; see tests/conftest.py to start it")
    migrate(LOCAL_URL)
    return LOCAL_URL


@pytest.fixture
def neon_test_db_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    if url == os.environ.get("DATABASE_URL"):
        pytest.fail("TEST_DATABASE_URL equals DATABASE_URL; refusing to run against production")
    return url
