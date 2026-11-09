"""Tests for registration, login checks and email tokens (real PostgreSQL test database)."""

from datetime import timedelta

import pytest
from sqlalchemy import update

from app.extensions import db
from app.models import EmailToken, User
from app.models.user import utc_now
from app.services import auth_service
from app.services.validation import ValidationError

GOOD_PASSWORD = "correct-horse-battery"


def register(**overrides):
    values = {"name": "Ada Lovelace", "email": "ada@example.com", "password": GOOD_PASSWORD}
    values.update(overrides)
    return auth_service.register_user(**values)


def expire_all_tokens():
    db.session.execute(update(EmailToken).values(expires_at=utc_now() - timedelta(minutes=1)))
    db.session.commit()


# ------------------------------------------------------------------ registration

def test_register_creates_an_active_seeker_with_a_hashed_password(app):
    user = register()

    assert user.id is not None
    assert user.role == "seeker"
    assert user.account_status == "active"
    assert user.is_email_verified is False
    assert user.password_hash != GOOD_PASSWORD
    assert user.check_password(GOOD_PASSWORD) is True


def test_register_trims_the_name_and_lowercases_the_email(app):
    user = register(name="  Ada Lovelace  ", email="  ADA@Example.com ")

    assert user.name == "Ada Lovelace"
    assert user.email == "ada@example.com"


def test_register_allows_owners(app):
    assert register(role="owner").role == "owner"


def test_register_refuses_to_create_admins(app):
    with pytest.raises(ValidationError) as error:
        register(role="admin")

    assert "role" in error.value.errors
    assert db.session.scalar(db.select(db.func.count(User.id))) == 0


def test_register_reports_every_problem_at_once(app):
    with pytest.raises(ValidationError) as error:
        register(name="", email="not-an-email", password="short")

    assert set(error.value.errors) == {"name", "email", "password"}


def test_register_rejects_a_duplicate_email_in_any_capitalisation(app):
    register(email="ada@example.com")

    with pytest.raises(ValidationError) as error:
        register(name="Someone Else", email="ADA@example.com")

    assert error.value.errors == {"email": auth_service.EMAIL_TAKEN_MESSAGE}
    assert db.session.scalar(db.select(db.func.count(User.id))) == 1


# ------------------------------------------------------------------------- login

def test_authenticate_accepts_the_right_email_and_password(app):
    user = register()

    assert auth_service.authenticate("ada@example.com", GOOD_PASSWORD) == user


def test_authenticate_ignores_capitals_and_spaces_in_the_email(app):
    user = register()

    assert auth_service.authenticate("  ADA@Example.com ", GOOD_PASSWORD) == user


def test_authenticate_rejects_a_wrong_password(app):
    register()

    assert auth_service.authenticate("ada@example.com", "wrong-password-123") is None


def test_authenticate_rejects_an_unknown_email(app):
    assert auth_service.authenticate("nobody@example.com", GOOD_PASSWORD) is None


def test_authenticate_rejects_empty_and_overlong_passwords(app):
    register()

    assert auth_service.authenticate("ada@example.com", "") is None
    assert auth_service.authenticate("ada@example.com", None) is None
    assert auth_service.authenticate("ada@example.com", "x" * 500) is None


def test_authenticate_rejects_a_suspended_account(app):
    user = register()
    user.account_status = "suspended"
    db.session.commit()

    assert auth_service.authenticate("ada@example.com", GOOD_PASSWORD) is None


def test_record_login_sets_last_login_time(app):
    user = register()
    assert user.last_login_at is None

    auth_service.record_login(user)

    assert user.last_login_at is not None


# ------------------------------------------------------------------ email tokens

def test_issue_token_stores_only_a_hash_of_the_token(app):
    user = register()

    raw = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)

    stored = db.session.scalars(db.select(EmailToken)).all()
    assert len(stored) == 1
    assert len(raw) >= 40
    assert stored[0].token_hash != raw
    assert raw not in stored[0].token_hash
    assert len(stored[0].token_hash) == 64


def test_issue_token_gives_a_different_token_each_time(app):
    user = register()

    first = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)
    second = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)

    assert first != second


def test_a_new_token_cancels_the_previous_unused_one(app):
    user = register()
    old = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)
    new = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)

    assert auth_service.verify_email(old) is None
    assert auth_service.verify_email(new) == user


def test_tokens_of_different_purposes_do_not_cancel_each_other(app):
    user = register()
    verify = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)
    reset = auth_service.issue_token(user, EmailToken.PURPOSE_RESET_PASSWORD)

    assert auth_service.verify_email(verify) == user
    assert auth_service.reset_password(reset, "a-brand-new-password") == user


def test_unknown_token_purpose_is_refused(app):
    user = register()

    with pytest.raises(ValueError):
        auth_service.issue_token(user, "steal_account")


def test_verify_email_marks_the_user_verified_and_works_only_once(app):
    user = register()
    raw = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)

    assert auth_service.verify_email(raw) == user
    assert user.is_email_verified is True
    assert auth_service.verify_email(raw) is None


def test_verify_email_rejects_an_expired_link(app):
    user = register()
    raw = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)
    expire_all_tokens()

    assert auth_service.verify_email(raw) is None
    db.session.refresh(user)
    assert user.is_email_verified is False


def test_verify_email_rejects_garbage_and_wrong_kind_of_token(app):
    user = register()
    reset_token = auth_service.issue_token(user, EmailToken.PURPOSE_RESET_PASSWORD)

    assert auth_service.verify_email(reset_token) is None  # a reset link cannot verify email
    for bad in [None, "", "not-a-real-token", "x" * 500, 12345]:
        assert auth_service.verify_email(bad) is None, repr(bad)


def test_reset_password_changes_the_password_and_works_only_once(app):
    user = register()
    raw = auth_service.issue_token(user, EmailToken.PURPOSE_RESET_PASSWORD)

    assert auth_service.reset_password(raw, "a-brand-new-password") == user

    assert auth_service.authenticate("ada@example.com", GOOD_PASSWORD) is None
    assert auth_service.authenticate("ada@example.com", "a-brand-new-password") == user
    assert auth_service.reset_password(raw, "yet-another-password-1") is None


def test_a_weak_new_password_does_not_use_up_the_link(app):
    user = register()
    raw = auth_service.issue_token(user, EmailToken.PURPOSE_RESET_PASSWORD)

    with pytest.raises(ValidationError) as error:
        auth_service.reset_password(raw, "short")
    assert "password" in error.value.errors

    # The same link still works with a good password.
    assert auth_service.reset_password(raw, "a-brand-new-password") == user


def test_reset_password_rejects_expired_and_invalid_links(app):
    user = register()
    raw = auth_service.issue_token(user, EmailToken.PURPOSE_RESET_PASSWORD)
    expire_all_tokens()

    assert auth_service.reset_password(raw, "a-brand-new-password") is None
    assert auth_service.reset_password("garbage", "a-brand-new-password") is None
    assert auth_service.authenticate("ada@example.com", GOOD_PASSWORD) == user