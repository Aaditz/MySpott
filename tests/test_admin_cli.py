"""Tests for the command-line tools that create and promote administrators."""

from sqlalchemy import select

from app.extensions import db
from app.models import User
from tests.helpers import GOOD_PASSWORD, create_user


def run(app, *args, input=None):
    return app.test_cli_runner().invoke(args=list(args), input=input)


def find_user(email):
    return db.session.scalar(select(User).where(User.email == email))


def test_create_admin_makes_a_confirmed_administrator(app):
    result = run(
        app, "create-admin", "--name", "Site Admin", "--email", "Admin@Example.com",
        "--password", GOOD_PASSWORD,
    )

    assert result.exit_code == 0, result.output
    assert "Administrator account created for admin@example.com" in result.output
    admin = find_user("admin@example.com")
    assert admin.role == "admin"
    assert admin.is_email_verified is True
    assert admin.check_password(GOOD_PASSWORD) is True


def test_create_admin_asks_for_anything_missing(app):
    answers = f"Site Admin\nadmin@example.com\n{GOOD_PASSWORD}\n{GOOD_PASSWORD}\n"

    result = run(app, "create-admin", input=answers)

    assert result.exit_code == 0, result.output
    assert find_user("admin@example.com").role == "admin"
    assert GOOD_PASSWORD not in result.output  # the password is never echoed


def test_create_admin_refuses_a_weak_password(app):
    result = run(
        app, "create-admin", "--name", "Site Admin", "--email", "admin@example.com",
        "--password", "short",
    )

    assert result.exit_code == 1
    assert "at least 8 characters" in result.output
    assert find_user("admin@example.com") is None


def test_create_admin_refuses_an_email_that_already_exists(app):
    create_user(email="admin@example.com")

    result = run(
        app, "create-admin", "--name", "Site Admin", "--email", "admin@example.com",
        "--password", GOOD_PASSWORD,
    )

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert find_user("admin@example.com").role == "seeker"


def test_promote_admin_upgrades_an_existing_account(app):
    user = create_user()

    result = run(app, "promote-admin", "--email", "ADA@example.com")

    assert result.exit_code == 0, result.output
    assert "is now an administrator" in result.output
    db.session.refresh(user)
    assert user.role == "admin"


def test_promote_admin_refuses_an_unknown_email(app):
    result = run(app, "promote-admin", "--email", "nobody@example.com")

    assert result.exit_code == 1
    assert "No account" in result.output