"""Tests for the registration, login and logout pages (real PostgreSQL test database)."""

import re

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import EmailToken, User
from app.models.user import utc_now
from app.services import auth_service, email_service
from app.services.email_service import EmailDeliveryError
from app.web.auth import GENERIC_LOGIN_ERROR, safe_next_url

GOOD_PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def empty_outbox():
    email_service.outbox.clear()
    yield
    email_service.outbox.clear()


# ---------------------------------------------------------------------- helpers

def csrf_token_from(client, path):
    """Open a page like a browser and read the hidden CSRF token out of its form."""
    html = client.get(path).get_data(as_text=True)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    assert match, f"no CSRF token found on {path}"
    return match.group(1)


def post_form(client, path, data, form_page=None):
    """Submit a form like a browser: load the page first (to get a token), then post it."""
    token = csrf_token_from(client, form_page or path)
    return client.post(path, data={**data, "csrf_token": token})


def register_data(**overrides):
    values = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "password": GOOD_PASSWORD,
        "role": "seeker",
    }
    values.update(overrides)
    return values


def create_user(**overrides):
    values = {"name": "Ada Lovelace", "email": "ada@example.com", "password": GOOD_PASSWORD}
    values.update(overrides)
    return auth_service.register_user(**values)


def log_in(client, email="ada@example.com", password=GOOD_PASSWORD, **extra):
    return post_form(client, "/auth/login", {"email": email, "password": password, **extra})


def page(client, path="/"):
    return client.get(path).get_data(as_text=True)


def count_users():
    return db.session.scalar(db.select(db.func.count(User.id)))


# --------------------------------------------------------------------- register

def test_register_page_shows_the_form(client):
    response = client.get("/auth/register")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Create your account" in html
    assert 'name="csrf_token"' in html
    assert 'name="password"' in html


def test_successful_registration_logs_in_and_sends_a_verification_email(app, client):
    response = post_form(client, "/auth/register", register_data())

    assert response.status_code == 302
    assert response.headers["Location"] == "/"

    user = db.session.scalar(select(User).where(User.email == "ada@example.com"))
    assert user is not None
    assert user.role == "seeker"
    assert user.last_login_at is not None

    home = page(client, "/")
    assert "Hi, Ada Lovelace" in home
    assert "We sent a confirmation link" in home

    assert len(email_service.outbox) == 1
    message = email_service.outbox[0]
    assert message["To"] == "ada@example.com"
    link = re.search(r"http://localhost/auth/verify-email/(\S+)", message.get_content())
    assert link, "the email should contain a verification link"
    assert auth_service.verify_email(link.group(1)) == user


def test_registering_as_an_owner_saves_the_owner_role(client):
    post_form(client, "/auth/register", register_data(role="owner"))

    user = db.session.scalar(select(User).where(User.email == "ada@example.com"))
    assert user.role == "owner"


def test_a_tampered_admin_role_is_refused(client):
    response = post_form(client, "/auth/register", register_data(role="admin"))

    assert response.status_code == 400
    assert count_users() == 0


def test_invalid_registration_shows_errors_and_keeps_typed_values(client):
    response = post_form(
        client,
        "/auth/register",
        register_data(name="", email="nope", password="short"),
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "Please enter your name" in html
    assert "valid email address" in html
    assert "at least 8 characters" in html
    assert 'value="nope"' in html  # what they typed is kept...
    assert 'value="short"' not in html  # ...but the password is never sent back
    assert count_users() == 0


def test_registering_an_existing_email_is_refused(client):
    create_user()

    response = post_form(client, "/auth/register", register_data(email="ADA@example.com"))

    assert response.status_code == 400
    assert "already exists" in response.get_data(as_text=True)
    assert count_users() == 1


def test_registration_without_a_csrf_token_is_refused(client):
    response = client.post("/auth/register", data=register_data())

    assert response.status_code == 400
    assert "Please try again" in response.get_data(as_text=True)
    assert count_users() == 0


def test_registration_still_works_if_the_email_cannot_be_sent(client, monkeypatch):
    def broken_sender(user, raw_token):
        raise EmailDeliveryError("mail server is down")

    monkeypatch.setattr(email_service, "send_verification_email", broken_sender)

    response = post_form(client, "/auth/register", register_data())

    assert response.status_code == 302
    assert count_users() == 1
    assert "could not send the confirmation email" in page(client, "/")


def test_logged_in_users_are_sent_home_from_the_register_and_login_pages(client):
    post_form(client, "/auth/register", register_data())

    for path in ["/auth/register", "/auth/login"]:
        response = client.get(path)
        assert response.status_code == 302, path
        assert response.headers["Location"] == "/", path


# ------------------------------------------------------------------------ login

def test_login_page_shows_the_form(client):
    response = client.get("/auth/login")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Log in" in html
    assert 'name="csrf_token"' in html


def test_login_with_correct_details_works(client):
    user = create_user()
    assert user.last_login_at is None

    response = log_in(client, email="  ADA@example.com ")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert "Hi, Ada Lovelace" in page(client, "/")
    db.session.refresh(user)
    assert user.last_login_at is not None


def test_wrong_password_and_unknown_email_give_the_same_answer(client):
    create_user()

    wrong_password = log_in(client, password="not-the-password-1")
    unknown_email = log_in(client, email="nobody@example.com")

    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert GENERIC_LOGIN_ERROR in response.get_data(as_text=True)
    assert "Log in" in page(client, "/")  # still logged out


def test_a_suspended_account_cannot_log_in(client):
    user = create_user()
    user.account_status = "suspended"
    db.session.commit()

    response = log_in(client)

    assert response.status_code == 401
    assert GENERIC_LOGIN_ERROR in response.get_data(as_text=True)


def test_login_returns_to_a_safe_next_page(client):
    create_user()

    response = log_in(client, next="/some/page")

    assert response.status_code == 302
    assert response.headers["Location"] == "/some/page"


def test_login_ignores_an_unsafe_next_address(client):
    create_user()

    response = log_in(client, next="https://evil.example/steal")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_safe_next_url_only_allows_paths_on_this_site():
    for good in ["/", "/some/page", "/auth/login?x=1", "/listings/12#top"]:
        assert safe_next_url(good) == good, good

    bad_values = [
        None, "", 5, "https://evil.example", "http://evil.example/x", "//evil.example",
        "///evil.example", "/\\evil.example", "\\\\evil.example", "javascript:alert(1)",
        "relative/path", "evil.example", "/ok\nSet-Cookie: x=1", "\t/evil",
    ]
    for bad in bad_values:
        assert safe_next_url(bad) is None, repr(bad)


def test_login_without_a_csrf_token_is_refused(client):
    create_user()

    response = client.post(
        "/auth/login", data={"email": "ada@example.com", "password": GOOD_PASSWORD}
    )

    assert response.status_code == 400
    assert "Log in" in page(client, "/")  # still logged out


# ----------------------------------------------------------------------- logout

def test_logout_logs_the_user_out(client):
    create_user()
    log_in(client)
    assert "Hi, Ada Lovelace" in page(client, "/")

    response = post_form(client, "/auth/logout", {}, form_page="/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    home = page(client, "/")
    assert "Hi, Ada Lovelace" not in home
    assert "Log in" in home


def test_logout_needs_post_and_a_csrf_token(client):
    create_user()
    log_in(client)

    assert client.get("/auth/logout").status_code == 405
    assert client.post("/auth/logout").status_code == 400
    assert "Hi, Ada Lovelace" in page(client, "/")  # still logged in


# -------------------------------------------------------------------- home page

def test_home_page_asks_unverified_users_to_confirm_their_email(client):
    user = create_user()
    log_in(client)

    assert "Please confirm your email address" in page(client, "/")

    user.email_verified_at = utc_now()
    db.session.commit()
    assert "Please confirm your email address" not in page(client, "/")