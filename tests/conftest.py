"""Shared test setup."""

import pytest
from prefect.testing.utilities import prefect_test_harness


@pytest.fixture(scope="session", autouse=True)
def prefect_for_tests():
    """Run flows in tests against a throwaway Prefect database."""
    with prefect_test_harness(server_startup_timeout=90):
        yield
