"""Fixtures for the integration suite."""

import os

import pytest


@pytest.fixture(scope="session")
def base_url():
    """Base URL of the running artifact, injected by `rbs integration-test`."""
    url = os.environ.get("RBS_BASE_URL")
    if not url:
        pytest.fail("RBS_BASE_URL is unset; run this suite via `rbs integration-test`")
    return url.rstrip("/")
