"""Tests for the EmailToken model (real PostgreSQL test database)."""

from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import EmailToken
from app.models.user import utc_now


def save_user(user_factory):
    user = user_factory()
    db.session.add(user)
    db.session.commit()
    return user


def make_token(user, **overrides):
    values = {
        "user_id": user.id,
        "purpose": EmailToken.PURPOSE_VERIFY_EMAIL,
        "token_hash": "a" * 64,
        "expires_at": utc_now() + timedelta(hours=24),
    }
    values.update(overrides)
    return EmailToken(**values)


def test_new_token_gets_defaults(app, user_factory):
    user = save_user(user_factory)
    token = make_token(user)
    db.session.add(token)
    db.session.commit()

    assert token.id is not None
    assert token.created_at is not None
    assert token.used_at is None
    assert token.is_used is False


def test_invalid_purpose_is_rejected_by_the_database(app, user_factory):
    user = save_user(user_factory)
    db.session.add(make_token(user, purpose="steal_account"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_duplicate_token_hash_is_rejected(app, user_factory):
    user = save_user(user_factory)
    db.session.add(make_token(user, token_hash="b" * 64))
    db.session.commit()

    db.session.add(make_token(user, token_hash="b" * 64))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_token_must_belong_to_a_user(app):
    db.session.add(
        EmailToken(
            user_id=None,
            purpose=EmailToken.PURPOSE_VERIFY_EMAIL,
            token_hash="c" * 64,
            expires_at=utc_now() + timedelta(hours=1),
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_deleting_a_user_deletes_their_tokens(app, user_factory):
    user = save_user(user_factory)
    db.session.add(make_token(user, token_hash="d" * 64))
    db.session.commit()

    db.session.delete(user)
    db.session.commit()

    remaining = db.session.scalar(db.select(db.func.count(EmailToken.id)))
    assert remaining == 0


def test_expiry_and_used_helpers(app, user_factory):
    user = save_user(user_factory)

    fresh = make_token(user, token_hash="e" * 64, expires_at=utc_now() + timedelta(hours=1))
    stale = make_token(user, token_hash="f" * 64, expires_at=utc_now() - timedelta(seconds=1))
    assert fresh.is_expired() is False
    assert stale.is_expired() is True

    fresh.used_at = utc_now()
    assert fresh.is_used is True