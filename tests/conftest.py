"""Shared test setup. Fixtures defined here are available to every test file."""

import pytest

from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture()
def app():
    """A MySpott app on the TEST database, with fresh empty tables for each test.

    validate_config() guarantees the test database name ends with '_test', so
    the cleanup below can never erase your development data.
    """
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """A fake browser that can call the app without starting a server."""
    return app.test_client()


@pytest.fixture()
def user_factory(app):
    """Returns a function that builds a valid (unsaved) user. Override any field you need."""

    def build(**overrides):
        values = {"name": "Ada Lovelace", "email": "ada@example.com"}
        values.update(overrides)
        user = User(**values)
        user.set_password("a-test-password")
        return user

    return build