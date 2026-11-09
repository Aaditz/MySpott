"""Tests for the User model (these run against the real PostgreSQL test database)."""

import time

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User


def make_user(**overrides):
    """Build a valid user; tests override only the field they care about."""
    values = {"name": "Ada Lovelace", "email": "ada@example.com"}
    values.update(overrides)
    user = User(**values)
    user.set_password("a-test-password")
    return user


def test_new_user_gets_sensible_defaults(app):
    user = make_user()
    db.session.add(user)
    db.session.commit()

    assert user.id is not None
    assert user.role == "seeker"
    assert user.account_status == "active"
    assert user.is_email_verified is False
    assert user.created_at is not None
    assert user.last_login_at is None


def test_email_is_stored_trimmed_and_lowercase(app):
    user = make_user(email="  Ada@Example.COM ")
    db.session.add(user)
    db.session.commit()

    assert user.email == "ada@example.com"


def test_duplicate_email_is_rejected_even_with_different_capitals(app):
    db.session.add(make_user(email="ada@example.com"))
    db.session.commit()

    db.session.add(make_user(name="Someone Else", email="ADA@example.com"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_password_is_hashed_and_can_be_checked(app):
    user = make_user()
    assert user.password_hash != "a-test-password"
    assert "a-test-password" not in user.password_hash
    assert user.check_password("a-test-password") is True
    assert user.check_password("wrong-password") is False


def test_invalid_role_is_rejected_by_the_database(app):
    db.session.add(make_user(role="superhero"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_name_is_required(app):
    db.session.add(make_user(name=None))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_updated_at_changes_when_a_user_is_edited(app):
    user = make_user()
    db.session.add(user)
    db.session.commit()
    first_update_time = user.updated_at

    time.sleep(0.05)
    user.name = "Ada King"
    db.session.commit()

    assert user.updated_at > first_update_time