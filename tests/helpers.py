"""Small helpers shared by the page tests."""

import re

from app.extensions import db
from app.models import User
from app.services import auth_service

GOOD_PASSWORD = "correct-horse-battery"


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


def page(client, path="/"):
    return client.get(path).get_data(as_text=True)


def create_user(**overrides):
    values = {"name": "Ada Lovelace", "email": "ada@example.com", "password": GOOD_PASSWORD}
    values.update(overrides)
    return auth_service.register_user(**values)


def log_in(client, email="ada@example.com", password=GOOD_PASSWORD, **extra):
    return post_form(client, "/auth/login", {"email": email, "password": password, **extra})


def register_via_page(client, **overrides):
    data = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "password": GOOD_PASSWORD,
        "role": "seeker",
    }
    data.update(overrides)
    return post_form(client, "/auth/register", data)


def verification_path_from(message):
    """The /auth/verify-email/<token> part of the link inside an email."""
    match = re.search(r"http://localhost(/auth/verify-email/\S+)", message.get_content())
    assert match, "the email should contain a verification link"
    return match.group(1)


def count_users():
    return db.session.scalar(db.select(db.func.count(User.id)))