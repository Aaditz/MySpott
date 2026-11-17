"""Tests for the forgot-password and choose-a-new-password pages."""

import re
from datetime import timedelta

import pytest
from sqlalchemy import update

from app.extensions import db
from app.models import EmailToken
from app.models.user import utc_now
from app.services import auth_service, email_service
from app.services.email_service import EmailDeliveryError
from tests.helpers import (
    GOOD_PASSWORD,
    create_user,
    log_in,
    page,
    post_form,
    register_via_page,
)

NEW_PASSWORD = "a-brand-new-password"
REQUESTED = "If an account exists for that email address"


@pytest.fixture(autouse=True)
def empty_outbox():
    email_service.outbox.clear()
    yield
    email_service.outbox.clear()


def reset_path_from(message):
    match = re.search(r"http://localhost(/auth/reset-password/\S+)", message.get_content())
    assert match, "the email should contain a reset link"
    return match.group(1)


def ask_for_reset(client, email="ada@example.com"):
    return post_form(client, "/auth/forgot-password", {"email": email})


def expire_all_tokens():
    db.session.execute(update(EmailToken).values(expires_at=utc_now() - timedelta(minutes=1)))
    db.session.commit()


# ------------------------------------------------------------ asking for the link

def test_the_login_page_links_to_forgot_password(client):
    assert 'href="/auth/forgot-password"' in page(client, "/auth/login")


def test_forgot_password_page_shows_the_form(client):
    response = client.get("/auth/forgot-password")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Forgot your password?" in html
    assert 'name="csrf_token"' in html
    assert 'name="email"' in html


def test_a_known_address_gets_a_reset_email(client):
    create_user()

    response = ask_for_reset(client)

    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/login"
    assert len(email_service.outbox) == 1
    message = email_service.outbox[0]
    assert message["To"] == "ada@example.com"
    assert "Reset" in message["Subject"]
    assert REQUESTED in page(client, "/auth/login")


def test_an_unknown_address_gets_the_same_answer_but_no_email(client):
    response = ask_for_reset(client, "nobody@example.com")

    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/login"
    assert email_service.outbox == []
    assert REQUESTED in page(client, "/auth/login")


def test_a_badly_typed_address_is_rejected_with_a_message(client):
    response = ask_for_reset(client, "not-an-email")

    assert response.status_code == 400
    assert "valid email address" in response.get_data(as_text=True)
    assert email_service.outbox == []


def test_a_suspended_account_gets_no_email_but_the_same_answer(client):
    user = create_user()
    user.account_status = "suspended"
    db.session.commit()

    response = ask_for_reset(client)

    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/login"
    assert email_service.outbox == []
    assert REQUESTED in page(client, "/auth/login")


def test_asking_twice_quickly_sends_only_one_email(client):
    create_user()

    ask_for_reset(client)
    second = ask_for_reset(client)

    assert len(email_service.outbox) == 1
    assert second.status_code == 302
    assert REQUESTED in page(client, "/auth/login")  # the person still sees the usual answer


def test_email_trouble_does_not_change_what_the_person_sees(client, monkeypatch):
    create_user()

    def broken_sender(user, raw_token):
        raise EmailDeliveryError("mail server is down")

    monkeypatch.setattr(email_service, "send_password_reset_email", broken_sender)

    response = ask_for_reset(client)
    html = page(client, "/auth/login")

    assert response.status_code == 302
    assert REQUESTED in html
    assert "could not send" not in html


def test_forgot_password_needs_a_csrf_token(client):
    create_user()

    response = client.post("/auth/forgot-password", data={"email": "ada@example.com"})

    assert response.status_code == 400
    assert email_service.outbox == []


def test_logged_in_users_are_sent_home_from_forgot_password(client):
    register_via_page(client)

    response = client.get("/auth/forgot-password")

    assert response.status_code == 302
    assert response.headers["Location"] == "/"


# ----------------------------------------------------------- choosing a new password

def test_opening_the_reset_link_shows_the_form_without_using_it_up(client):
    create_user()
    ask_for_reset(client)
    path = reset_path_from(email_service.outbox[0])

    response = client.get(path)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="password"' in html
    assert 'name="csrf_token"' in html
    raw_token = path.rsplit("/", 1)[1]
    assert auth_service.is_token_usable(raw_token, EmailToken.PURPOSE_RESET_PASSWORD) is True


def test_choosing_a_new_password_works_and_the_old_one_stops_working(client):
    create_user()
    ask_for_reset(client)
    path = reset_path_from(email_service.outbox[0])

    response = post_form(client, path, {"password": NEW_PASSWORD})

    assert response.status_code == 302
    assert response.headers["Location"] == "/auth/login"
    assert "password has been changed" in page(client, "/auth/login")
    assert log_in(client, password=GOOD_PASSWORD).status_code == 401
    new_login = log_in(client, password=NEW_PASSWORD)
    assert new_login.status_code == 302
    assert new_login.headers["Location"] == "/"


def test_a_reset_link_works_only_once(client):
    user = create_user()
    ask_for_reset(client)
    path = reset_path_from(email_service.outbox[0])
    post_form(client, path, {"password": NEW_PASSWORD})

    assert client.get(path).status_code == 400
    again = post_form(client, path, {"password": "yet-another-password-1"}, form_page="/auth/login")

    assert again.status_code == 400
    assert auth_service.authenticate("ada@example.com", "yet-another-password-1") is None
    assert auth_service.authenticate("ada@example.com", NEW_PASSWORD) == user


def test_a_weak_new_password_shows_an_error_and_keeps_the_link_usable(client):
    create_user()
    ask_for_reset(client)
    path = reset_path_from(email_service.outbox[0])

    weak = post_form(client, path, {"password": "short"})

    assert weak.status_code == 400
    assert "at least 8 characters" in weak.get_data(as_text=True)
    good = post_form(client, path, {"password": NEW_PASSWORD})
    assert good.status_code == 302


def test_garbage_and_expired_reset_links_are_refused(client):
    create_user()
    ask_for_reset(client)
    path = reset_path_from(email_service.outbox[0])
    expire_all_tokens()

    assert client.get("/auth/reset-password/garbage").status_code == 400
    expired = client.get(path)
    assert expired.status_code == 400
    assert "Request a new reset link" in expired.get_data(as_text=True)
    submitted = post_form(client, path, {"password": NEW_PASSWORD}, form_page="/auth/login")
    assert submitted.status_code == 400


def test_a_confirmation_link_cannot_reset_a_password(client):
    user = create_user()
    verify_token = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)

    assert client.get(f"/auth/reset-password/{verify_token}").status_code == 400


def test_choosing_a_password_needs_a_csrf_token(client):
    user = create_user()
    ask_for_reset(client)
    path = reset_path_from(email_service.outbox[0])

    response = client.post(path, data={"password": NEW_PASSWORD})

    assert response.status_code == 400
    assert auth_service.authenticate("ada@example.com", GOOD_PASSWORD) == user


def test_reset_pages_tell_browsers_not_to_share_the_address(client):
    create_user()
    ask_for_reset(client)
    path = reset_path_from(email_service.outbox[0])

    assert client.get(path).headers["Referrer-Policy"] == "no-referrer"