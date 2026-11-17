"""Tests for how login cookies map back to users."""

from flask_login import current_user

from app.extensions import db
from app.models import User


def add_whoami_route(app):
    """A tiny test-only page that reports who the login cookie says is logged in."""

    @app.get("/_whoami")
    def whoami():
        return {"id": current_user.get_id() if current_user.is_authenticated else None}


def login_session_as(client, session_id):
    with client.session_transaction() as session:
        session["_user_id"] = session_id


def save(user):
    db.session.add(user)
    db.session.commit()
    return user


def test_get_id_has_the_user_id_and_a_fingerprint(app, user_factory):
    user = save(user_factory())

    user_id, fingerprint = user.get_id().split(":")

    assert user_id == str(user.id)
    assert len(fingerprint) == 16
    assert all(character in "0123456789abcdef" for character in fingerprint)


def test_the_fingerprint_changes_when_the_password_changes(app, user_factory):
    user = save(user_factory())
    before = user.get_id()

    user.set_password("another-password-1")

    assert user.get_id() != before


def test_the_login_cookie_does_not_contain_the_password_hash(app, user_factory):
    user = save(user_factory())

    assert user.password_hash not in user.get_id()
    assert user.password_hash[:20] not in user.get_id()


def test_parse_session_id_accepts_only_well_formed_values():
    assert User.parse_session_id("12:abcdef0123456789") == (12, "abcdef0123456789")

    bad_values = [
        None, 5, "", "12", "12:", ":abc", "a:b", "-1:abc", "1:2:3", "١٢:abc", "1" * 19 + ":abc",
    ]
    for bad in bad_values:
        assert User.parse_session_id(bad) is None, repr(bad)


def test_active_user_is_active(app, user_factory):
    user = save(user_factory())

    assert user.account_status == "active"
    assert user.is_active is True


def test_suspended_user_is_not_active(app, user_factory):
    assert user_factory(account_status="suspended").is_active is False


def test_a_valid_login_cookie_loads_the_user(app, client, user_factory):
    user = save(user_factory())
    add_whoami_route(app)

    login_session_as(client, user.get_id())

    assert client.get("/_whoami").get_json() == {"id": user.get_id()}


def test_bad_login_cookies_mean_nobody_is_logged_in(app, client, user_factory):
    user = save(user_factory())
    add_whoami_route(app)

    for bad in ["not-a-number", "999999", "999999:abc", f"{user.id}", f"{user.id}:wrongfingerprint0"]:
        login_session_as(client, bad)
        assert client.get("/_whoami").get_json() == {"id": None}, bad


def test_a_deleted_users_cookie_no_longer_logs_in(app, client, user_factory):
    user = save(user_factory())
    session_id = user.get_id()
    db.session.delete(user)
    db.session.commit()
    add_whoami_route(app)

    login_session_as(client, session_id)

    assert client.get("/_whoami").get_json() == {"id": None}


def test_changing_the_password_logs_out_existing_logins(app, client, user_factory):
    user = save(user_factory())
    add_whoami_route(app)
    login_session_as(client, user.get_id())
    assert client.get("/_whoami").get_json() == {"id": user.get_id()}

    user.set_password("another-password-1")
    db.session.commit()

    assert client.get("/_whoami").get_json() == {"id": None}


def test_suspending_a_user_logs_them_out_straight_away(app, client, user_factory):
    user = save(user_factory())
    add_whoami_route(app)
    login_session_as(client, user.get_id())
    assert client.get("/_whoami").get_json() == {"id": user.get_id()}

    user.account_status = "suspended"
    db.session.commit()

    assert client.get("/_whoami").get_json() == {"id": None}