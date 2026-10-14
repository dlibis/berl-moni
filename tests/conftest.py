import os

import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture
def test_db_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    if url == os.environ.get("DATABASE_URL"):
        pytest.fail("TEST_DATABASE_URL equals DATABASE_URL; refusing to run against production")
    return url
