"""Fixtures for testing."""

import pytest
from pysmarthashtag.tests.conftest import smart_fixture  # noqa: F401


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    return
