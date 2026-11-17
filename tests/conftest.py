"""Shared test setup. Fixtures defined here are available to every test file."""

import pytest
from flask import g

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

    @app.before_request
    def reset_per_request_globals():
        # A test keeps one app context open the whole time, so Flask's per-request scratchpad
        # (`g`) would carry over from one request to the next. A real browser never gets that:
        # every request starts with an empty scratchpad. Without this reset, a login or CSRF
        # token cached by one request leaks into the next, even into a different test browser.
        g.pop("csrf_token", None)
        g.pop("_login_user", None)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        # Every test builds its own app, and each app opens its own pool of database
        # connections. Closing them here stops them piling up until PostgreSQL runs out.
        db.engine.dispose()


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