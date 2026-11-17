"""Tests for rate limiting (real PostgreSQL test database).

Every test builds its own app, and each app starts with empty counters, so the tests
cannot disturb each other.
"""

import pytest

from app.extensions import limiter
from app.services import email_service
from app.web import rate_limits
from tests.helpers import create_user, log_in, page, post_form, register_via_page


@pytest.fixture(autouse=True)
def empty_outbox():
    email_service.outbox.clear()
    yield
    email_service.outbox.clear()


def allowed_count(limit_text):
    """'60 per minute' -> 60"""
    return int(limit_text.split()[0])


def ask_for_reset(client, email):
    return post_form(client, "/auth/forgot-password", {"email": email})


# ------------------------------------------------------------------------ login

def test_too_many_logins_from_one_address_are_stopped(client):
    limit = allowed_count(rate_limits.LOGIN_PER_ADDRESS)

    for number in range(limit):
        response = log_in(client, email=f"nobody{number}@example.com", password="wrong-password-1")
        assert response.status_code == 401, number

    blocked = log_in(client, email="someone-else@example.com", password="wrong-password-1")
    assert blocked.status_code == 429
    assert "Too many attempts" in blocked.get_data(as_text=True)


def test_five_wrong_passwords_for_one_account_block_further_attempts(client):
    create_user()
    create_user(name="Grace Hopper", email="grace@example.com")
    limit = allowed_count(rate_limits.LOGIN_FAILURES_PER_ACCOUNT)

    for _ in range(limit):
        assert log_in(client, password="wrong-password-1").status_code == 401

    # Even the CORRECT password is refused now, so a guesser gets nothing from trying again.
    assert log_in(client).status_code == 429
    # Other accounts are not affected.
    assert log_in(client, email="grace@example.com").status_code == 302


def test_correct_logins_never_count_as_failures(client):
    create_user()
    limit = allowed_count(rate_limits.LOGIN_FAILURES_PER_ACCOUNT)

    for _ in range(limit + 3):
        assert log_in(client).status_code == 302
        post_form(client, "/auth/logout", {}, form_page="/")


# ---------------------------------------------------------------------- sign-up

def test_too_many_sign_ups_from_one_address_are_stopped(app):
    limit = allowed_count(rate_limits.REGISTER_PER_ADDRESS)

    for number in range(limit):
        browser = app.test_client()
        response = register_via_page(browser, email=f"student{number}@example.com")
        assert response.status_code == 302, number

    blocked = register_via_page(app.test_client(), email="one-too-many@example.com")
    assert blocked.status_code == 429


# --------------------------------------------------------------- password reset

def test_password_reset_requests_are_limited_per_account(client):
    create_user()
    limit = allowed_count(rate_limits.FORGOT_PASSWORD_PER_ACCOUNT)

    for _ in range(limit):
        assert ask_for_reset(client, "ada@example.com").status_code == 302

    assert ask_for_reset(client, "ada@example.com").status_code == 429
    # The same limit applies to addresses that do not exist, so it reveals nothing.
    for _ in range(limit):
        assert ask_for_reset(client, "nobody@example.com").status_code == 302
    assert ask_for_reset(client, "nobody@example.com").status_code == 429


def test_password_reset_requests_are_limited_per_address(client):
    limit = allowed_count(rate_limits.FORGOT_PASSWORD_PER_ADDRESS)

    for number in range(limit):
        response = ask_for_reset(client, f"nobody{number}@example.com")
        assert response.status_code == 302, number

    assert ask_for_reset(client, "yet-another@example.com").status_code == 429


# ----------------------------------------------------------------------- resend

def test_asking_for_new_confirmation_links_is_limited_per_user(client):
    register_via_page(client)
    limit = allowed_count(rate_limits.RESEND_PER_USER)

    for number in range(limit):
        response = post_form(client, "/auth/resend-verification", {}, form_page="/")
        assert response.status_code == 302, number

    blocked = post_form(client, "/auth/resend-verification", {}, form_page="/")
    assert blocked.status_code == 429


# ------------------------------------------------------------------- error page

def test_the_too_many_requests_page_is_friendly_and_the_api_gets_json(app, client):
    @app.get("/_limited")
    @limiter.limit("1 per minute", scope="test-page")
    def limited_page():
        return "ok"

    @app.get("/api/v1/_limited")
    @limiter.limit("1 per minute", scope="test-api")
    def limited_api():
        return {"ok": True}

    assert client.get("/_limited").status_code == 200
    html = client.get("/_limited")
    assert html.status_code == 429
    assert "Too many attempts" in html.get_data(as_text=True)

    assert client.get("/api/v1/_limited").status_code == 200
    api = client.get("/api/v1/_limited")
    assert api.status_code == 429
    assert api.get_json() == {"error": "Too many requests. Please wait a few minutes and try again."}