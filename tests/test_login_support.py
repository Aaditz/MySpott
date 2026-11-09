"""Tests for the pieces that let Flask-Login work with the User model."""

from flask_login import current_user

from app.extensions import db


def add_whoami_route(app):
    """A tiny test-only page that reports who the session says is logged in."""

    @app.get("/_whoami")
    def whoami():
        return {"id": current_user.get_id() if current_user.is_authenticated else None}


def login_session_as(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)


def test_get_id_returns_the_id_as_text(app, user_factory):
    user = user_factory()
    db.session.add(user)
    db.session.commit()

    assert user.get_id() == str(user.id)


def test_active_user_is_active(app, user_factory):
    user = user_factory()
    db.session.add(user)
    db.session.commit()

    assert user.account_status == "active"
    assert user.is_active is True


def test_suspended_user_is_not_active(app, user_factory):
    assert user_factory(account_status="suspended").is_active is False


def test_session_user_id_loads_the_user(app, client, user_factory):
    user = user_factory()
    db.session.add(user)
    db.session.commit()
    add_whoami_route(app)

    login_session_as(client, user.id)

    assert client.get("/_whoami").get_json() == {"id": str(user.id)}


def test_garbage_session_id_means_nobody_is_logged_in(app, client):
    add_whoami_route(app)

    login_session_as(client, "not-a-number")

    assert client.get("/_whoami").get_json() == {"id": None}


def test_deleted_users_session_no_longer_logs_in(app, client, user_factory):
    user = user_factory()
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    db.session.delete(user)
    db.session.commit()
    add_whoami_route(app)

    login_session_as(client, user_id)

    assert client.get("/_whoami").get_json() == {"id": None}