"""Tests for the email confirmation page and the 'send me a new link' button."""

from datetime import timedelta

import pytest
from sqlalchemy import update

from app.extensions import db
from app.models import EmailToken
from app.models.user import utc_now
from app.services import auth_service, email_service
from app.services.email_service import EmailDeliveryError
from tests.helpers import (
    create_user,
    csrf_token_from,
    log_in,
    page,
    post_form,
    register_via_page,
    verification_path_from,
)


@pytest.fixture(autouse=True)
def empty_outbox():
    email_service.outbox.clear()
    yield
    email_service.outbox.clear()


def backdate_tokens(minutes):
    old = utc_now() - timedelta(minutes=minutes)
    db.session.execute(update(EmailToken).values(created_at=old))
    db.session.commit()


def expire_all_tokens():
    db.session.execute(update(EmailToken).values(expires_at=utc_now() - timedelta(minutes=1)))
    db.session.commit()


# -------------------------------------------------------------- confirmation page

def test_opening_the_emailed_link_shows_a_button_but_does_not_confirm(client):
    register_via_page(client)
    user = auth_service.authenticate("ada@example.com", "correct-horse-battery")
    path = verification_path_from(email_service.outbox[0])

    response = client.get(path)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Confirm my email address" in html
    assert 'name="csrf_token"' in html
    db.session.refresh(user)
    assert user.is_email_verified is False  # opening the link alone changes nothing


def test_pressing_the_button_confirms_the_email(client):
    register_via_page(client)
    user = auth_service.authenticate("ada@example.com", "correct-horse-battery")
    path = verification_path_from(email_service.outbox[0])

    response = post_form(client, path, {})

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    db.session.refresh(user)
    assert user.is_email_verified is True
    home = page(client, "/")
    assert "Your email address is confirmed" in home
    assert "Please confirm your email address" not in home


def test_a_confirmation_link_works_only_once(client):
    register_via_page(client)
    path = verification_path_from(email_service.outbox[0])
    post_form(client, path, {})

    response = client.get(path)

    assert response.status_code == 400
    assert "not valid" in response.get_data(as_text=True)


def test_garbage_and_expired_links_are_refused(client):
    register_via_page(client)
    path = verification_path_from(email_service.outbox[0])
    expire_all_tokens()

    assert client.get("/auth/verify-email/garbage").status_code == 400
    assert client.get(path).status_code == 400
    assert post_form(client, path, {}, form_page="/").status_code == 400


def test_confirming_works_from_a_browser_where_nobody_is_logged_in(client):
    user = create_user()
    raw = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)
    path = f"/auth/verify-email/{raw}"

    assert client.get(path).status_code == 200
    response = post_form(client, path, {})

    assert response.status_code == 302
    db.session.refresh(user)
    assert user.is_email_verified is True


def test_pressing_the_button_without_a_csrf_token_is_refused(client):
    user = create_user()
    raw = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)

    response = client.post(f"/auth/verify-email/{raw}")

    assert response.status_code == 400
    db.session.refresh(user)
    assert user.is_email_verified is False


def test_a_password_reset_link_cannot_confirm_an_email(client):
    user = create_user()
    reset_token = auth_service.issue_token(user, EmailToken.PURPOSE_RESET_PASSWORD)

    assert client.get(f"/auth/verify-email/{reset_token}").status_code == 400


def test_confirmation_pages_tell_browsers_not_to_share_the_address(client):
    user = create_user()
    raw = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)

    response = client.get(f"/auth/verify-email/{raw}")

    assert response.headers["Referrer-Policy"] == "no-referrer"


# ------------------------------------------------------------------------ resend

def test_the_banner_offers_a_resend_button_to_unverified_users(client):
    register_via_page(client)

    assert 'action="/auth/resend-verification"' in page(client, "/")


def test_resend_sends_a_new_working_link_and_cancels_the_old_one(client):
    register_via_page(client)
    old_path = verification_path_from(email_service.outbox[0])
    backdate_tokens(minutes=2)

    response = post_form(client, "/auth/resend-verification", {}, form_page="/")
    home = page(client, "/")  # read the "we sent you a new link" message before other pages use it up

    assert response.status_code == 302
    assert "new confirmation link" in home
    assert len(email_service.outbox) == 2
    new_path = verification_path_from(email_service.outbox[1])
    assert new_path != old_path
    assert client.get(new_path).status_code == 200
    assert client.get(old_path).status_code == 400


def test_resend_is_blocked_during_the_waiting_time(client):
    register_via_page(client)

    post_form(client, "/auth/resend-verification", {}, form_page="/")

    assert len(email_service.outbox) == 1  # no second email
    assert "Please wait" in page(client, "/")


def test_resend_for_an_already_confirmed_user_sends_nothing(client):
    user = create_user()
    log_in(client)
    user.email_verified_at = utc_now()
    db.session.commit()

    response = post_form(client, "/auth/resend-verification", {}, form_page="/")

    assert response.status_code == 302
    assert email_service.outbox == []
    assert "already confirmed" in page(client, "/")


def test_resend_needs_a_login(client):
    token = csrf_token_from(client, "/auth/login")

    response = client.post("/auth/resend-verification", data={"csrf_token": token})

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/auth/login")
    assert email_service.outbox == []


def test_resend_without_a_csrf_token_is_refused(client):
    register_via_page(client)
    backdate_tokens(minutes=2)

    response = client.post("/auth/resend-verification")

    assert response.status_code == 400
    assert len(email_service.outbox) == 1


def test_resend_tells_the_user_when_the_email_cannot_be_sent(client, monkeypatch):
    register_via_page(client)
    backdate_tokens(minutes=2)

    def broken_sender(user, raw_token):
        raise EmailDeliveryError("mail server is down")

    monkeypatch.setattr(email_service, "send_verification_email", broken_sender)

    response = post_form(client, "/auth/resend-verification", {}, form_page="/")

    assert response.status_code == 302
    assert "could not send the confirmation email" in page(client, "/")