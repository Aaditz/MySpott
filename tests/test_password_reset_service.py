"""Tests for starting a password reset (real PostgreSQL test database)."""

from datetime import timedelta

from sqlalchemy import update

from app.extensions import db
from app.models import EmailToken
from app.models.user import utc_now
from app.services import auth_service

RESET = EmailToken.PURPOSE_RESET_PASSWORD
VERIFY = EmailToken.PURPOSE_VERIFY_EMAIL


def register():
    return auth_service.register_user("Ada Lovelace", "ada@example.com", "correct-horse-battery")


def token_count():
    return db.session.scalar(db.select(db.func.count(EmailToken.id)))


def test_starting_a_reset_returns_the_user_and_a_working_token(app):
    user = register()

    result = auth_service.start_password_reset("ada@example.com")

    assert result is not None
    found_user, raw_token = result
    assert found_user == user
    assert auth_service.is_token_usable(raw_token, RESET) is True


def test_starting_a_reset_ignores_capitals_and_spaces(app):
    user = register()

    result = auth_service.start_password_reset("  ADA@Example.com ")

    assert result is not None and result[0] == user


def test_unknown_and_empty_addresses_get_nothing(app):
    register()

    for address in ["nobody@example.com", "", None, "not-an-email"]:
        assert auth_service.start_password_reset(address) is None, repr(address)
    assert token_count() == 0


def test_suspended_accounts_get_nothing(app):
    user = register()
    user.account_status = "suspended"
    db.session.commit()

    assert auth_service.start_password_reset("ada@example.com") is None
    assert token_count() == 0


def test_asking_again_straight_away_gets_nothing_until_the_wait_is_over(app):
    register()
    first = auth_service.start_password_reset("ada@example.com")
    assert first is not None

    assert auth_service.start_password_reset("ada@example.com") is None

    old = utc_now() - timedelta(minutes=2)
    db.session.execute(update(EmailToken).values(created_at=old))
    db.session.commit()
    third = auth_service.start_password_reset("ada@example.com")
    assert third is not None
    assert auth_service.is_token_usable(first[1], RESET) is False  # the newest link replaces the old
    assert auth_service.is_token_usable(third[1], RESET) is True


def test_a_reset_request_does_not_start_the_confirmation_email_wait(app):
    user = register()

    auth_service.start_password_reset("ada@example.com")

    assert auth_service.resend_wait_seconds(user, RESET) > 0
    assert auth_service.resend_wait_seconds(user, VERIFY) == 0