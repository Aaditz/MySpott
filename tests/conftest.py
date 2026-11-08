"""Shared test setup. Fixtures defined here are available to every test file."""

import pytest

from app import create_app


@pytest.fixture()
def app():
    """A MySpott app using the 'testing' configuration."""
    return create_app("testing")


@pytest.fixture()
def client(app):
    """A fake browser that can call the app without starting a server."""
    return app.test_client()