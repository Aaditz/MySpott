"""Tests for checking a link without using it up, and for the resend waiting time."""

from datetime import timedelta

from sqlalchemy import update

from app.extensions import db
from app.models import EmailToken
from app.models.user import utc_now
from app.services import auth_service

VERIFY = EmailToken.PURPOSE_VERIFY_EMAIL
RESET = EmailToken.PURPOSE_RESET_PASSWORD


def register():
    return auth_service.register_user("Ada Lovelace", "ada@example.com", "correct-horse-battery")


def backdate_tokens(minutes):
    old = utc_now() - timedelta(minutes=minutes)
    db.session.execute(update(EmailToken).values(created_at=old))
    db.session.commit()


def test_is_token_usable_checks_without_using_the_token_up(app):
    user = register()
    raw = auth_service.issue_token(user, VERIFY)

    assert auth_service.is_token_usable(raw, VERIFY) is True
    assert auth_service.is_token_usable(raw, VERIFY) is True  # still fine: nothing was consumed
    assert auth_service.verify_email(raw) == user
    assert auth_service.is_token_usable(raw, VERIFY) is False  # now it is used up


def test_is_token_usable_rejects_wrong_purpose_expired_and_garbage_tokens(app):
    user = register()
    raw = auth_service.issue_token(user, VERIFY)

    assert auth_service.is_token_usable(raw, RESET) is False
    for bad in [None, "", "garbage", "x" * 500, 12345]:
        assert auth_service.is_token_usable(bad, VERIFY) is False, repr(bad)

    db.session.execute(update(EmailToken).values(expires_at=utc_now() - timedelta(minutes=1)))
    db.session.commit()
    assert auth_service.is_token_usable(raw, VERIFY) is False


def test_resend_wait_is_zero_before_any_email_was_sent(app):
    assert auth_service.resend_wait_seconds(register(), VERIFY) == 0


def test_resend_wait_counts_down_after_an_email_is_sent(app):
    user = register()
    auth_service.issue_token(user, VERIFY)

    wait = auth_service.resend_wait_seconds(user, VERIFY)
    assert 1 <= wait <= 60

    backdate_tokens(minutes=2)
    assert auth_service.resend_wait_seconds(user, VERIFY) == 0


def test_resend_wait_is_tracked_separately_for_each_kind_of_email(app):
    user = register()
    auth_service.issue_token(user, RESET)

    assert auth_service.resend_wait_seconds(user, RESET) > 0
    assert auth_service.resend_wait_seconds(user, VERIFY) == 0