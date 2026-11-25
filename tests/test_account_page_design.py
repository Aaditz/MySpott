"""Tests for the design of the account pages: structure, labels, errors and accessibility."""

import re

from sqlalchemy import select

from app.extensions import db
from app.models import EmailToken, User
from app.services import auth_service
from tests.helpers import create_user, log_in, page, post_form

ACCOUNT_PAGES = ["/auth/login", "/auth/register", "/auth/forgot-password"]


def the_test_user():
    """The test account: created the first time it is needed, reused after that."""
    user = db.session.scalar(select(User).where(User.email == "ada@example.com"))
    return user or create_user()


def token_path(purpose, address):
    raw_token = auth_service.issue_token(the_test_user(), purpose)
    return f"{address}{raw_token}"


def reset_page_path():
    return token_path(EmailToken.PURPOSE_RESET_PASSWORD, "/auth/reset-password/")


def visible_fields(html):
    """The id of every control a person can see or type into (None if it has no id)."""
    ids = []
    for tag in re.findall(r"<(?:input|select|textarea)\b[^>]*>", html):
        kind = re.search(r'\btype="([^"]+)"', tag)
        if kind and kind.group(1) in ("hidden", "submit", "button"):
            continue
        identifier = re.search(r'\bid="([^"]+)"', tag)
        ids.append(identifier.group(1) if identifier else None)
    return ids


def test_account_pages_use_the_centred_card(client):
    for path in ACCOUNT_PAGES + [reset_page_path()]:
        assert 'class="auth-card card"' in page(client, path), path


def test_every_form_field_has_a_label(client):
    for path in ACCOUNT_PAGES + [reset_page_path()]:
        html = page(client, path)
        fields = visible_fields(html)
        assert fields, path
        for identifier in fields:
            assert identifier is not None, f"a field on {path} has no id"
            assert f'for="{identifier}"' in html, f"{identifier} has no label on {path}"


def test_password_fields_have_a_show_hide_button_and_a_hint(client):
    for path in ["/auth/login", "/auth/register", reset_page_path()]:
        html = page(client, path)
        assert "data-password-toggle" in html, path
        assert 'aria-controls="password"' in html, path
        assert 'aria-pressed="false"' in html, path

    register = page(client, "/auth/register")
    assert 'id="password-hint"' in register
    assert 'aria-describedby="password-hint"' in register


def test_field_errors_are_tied_to_their_fields_for_screen_readers(client):
    response = post_form(
        client, "/auth/register", {"name": "", "email": "nope", "password": "short", "role": "seeker"}
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 400
    assert html.count('aria-invalid="true"') == 3
    for identifier in ("name-error", "email-error", "password-error"):
        assert f'id="{identifier}"' in html, identifier
    assert 'aria-describedby="name-error"' in html
    assert 'aria-describedby="email-error"' in html
    assert 'aria-describedby="password-hint password-error"' in html
    assert 'role="alert"' in html


def test_a_failed_login_is_announced_and_linked_to_both_fields(client):
    create_user()

    response = log_in(client, password="not-the-password-1")
    html = response.get_data(as_text=True)

    assert response.status_code == 401
    assert 'role="alert"' in html
    assert 'id="login-error"' in html
    assert html.count('aria-describedby="login-error"') == 2
    assert "Incorrect email or password." in html


def test_account_pages_have_no_inline_styles_or_scripts(client):
    verify_path = token_path(EmailToken.PURPOSE_VERIFY_EMAIL, "/auth/verify-email/")
    paths = ACCOUNT_PAGES + [reset_page_path(), verify_path, "/auth/verify-email/garbage"]
    pages = [page(client, path) for path in paths]
    pages.append(
        post_form(client, "/auth/register", {"name": "", "email": "x", "password": "y"}).get_data(
            as_text=True
        )
    )

    for html in pages:
        assert ' style="' not in html
        assert re.search(r"<script(?![^>]*\bsrc=)", html) is None


def test_forms_that_send_data_are_protected_from_double_clicks(client):
    for path in ACCOUNT_PAGES + [reset_page_path()]:
        html = page(client, path)
        assert "data-submit-once" in html, path
        assert "data-loading-text=" in html, path


def test_the_role_choice_is_two_labelled_radio_buttons(client):
    html = page(client, "/auth/register")

    for identifier in ("role-seeker", "role-owner"):
        assert f'id="{identifier}"' in html
        assert f'for="{identifier}"' in html
    assert 'value="seeker" checked' in html
    assert 'value="owner" checked' not in html

    response = post_form(
        client, "/auth/register", {"name": "", "email": "x", "password": "y", "role": "owner"}
    )
    after_error = response.get_data(as_text=True)
    assert 'value="owner" checked' in after_error
    assert 'value="seeker" checked' not in after_error


def test_the_confirmation_and_invalid_link_pages_use_the_card(client):
    verify_path = token_path(EmailToken.PURPOSE_VERIFY_EMAIL, "/auth/verify-email/")

    confirm = page(client, verify_path)
    invalid = page(client, "/auth/verify-email/garbage")

    assert 'class="auth-card card"' in confirm
    assert "Confirm my email address" in confirm
    assert 'class="auth-card card"' in invalid
    assert "This link is not valid" in invalid
    assert 'class="btn btn-primary btn-block"' in invalid