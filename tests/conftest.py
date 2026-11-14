"""Shared fixtures: load the custom integration from this checkout."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant's test harness find custom_components/."""
    yield
