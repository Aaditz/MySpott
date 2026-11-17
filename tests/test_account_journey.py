"""One test that walks through a person's whole account life, the way they would in a browser."""

import re

from sqlalchemy import select

from app.extensions import db
from app.models import User
from app.services import email_service
from tests.helpers import (
    GOOD_PASSWORD,
    log_in,
    page,
    post_form,
    register_via_page,
    verification_path_from,
)

NEW_PASSWORD = "a-brand-new-password"


def reset_path_from(message):
    match = re.search(r"http://localhost(/auth/reset-password/\S+)", message.get_content())
    assert match, "the email should contain a reset link"
    return match.group(1)


def test_a_person_can_sign_up_confirm_log_out_reset_their_password_and_log_back_in(app, client):
    email_service.outbox.clear()

    # 1. Sign up as an owner: logged in at once, and told to confirm the email address.
    response = register_via_page(client, name="Priya Nair", email="priya@example.com", role="owner")
    assert response.status_code == 302
    home = page(client, "/")
    assert "Hi, Priya Nair" in home
    assert "Please confirm your email address" in home

    # 2. Open the link from the welcome email, then press the button.
    confirm_path = verification_path_from(email_service.outbox[0])
    assert client.get(confirm_path).status_code == 200
    assert post_form(client, confirm_path, {}).status_code == 302
    home = page(client, "/")
    assert "Your email address is confirmed" in home
    assert "Please confirm your email address" not in home

    # 3. Log out.
    assert post_form(client, "/auth/logout", {}, form_page="/").status_code == 302
    assert "Log in" in page(client, "/")

    # 4. Forgot the password: ask for a reset link and use it.
    forgot = post_form(client, "/auth/forgot-password", {"email": "priya@example.com"})
    assert forgot.status_code == 302
    reset_message = email_service.outbox[-1]
    assert "Reset" in reset_message["Subject"]
    reset_path = reset_path_from(reset_message)
    assert client.get(reset_path).status_code == 200
    assert post_form(client, reset_path, {"password": NEW_PASSWORD}).status_code == 302

    # 5. The old password no longer works, the new one does.
    assert log_in(client, email="priya@example.com", password=GOOD_PASSWORD).status_code == 401
    assert log_in(client, email="priya@example.com", password=NEW_PASSWORD).status_code == 302
    assert "Hi, Priya Nair" in page(client, "/")

    # 6. What ended up in the database.
    user = db.session.scalar(select(User).where(User.email == "priya@example.com"))
    assert user.role == "owner"
    assert user.is_email_verified is True
    assert user.last_login_at is not None