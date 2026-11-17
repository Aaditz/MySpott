"""Every rate limit for the account pages, in one place.

Limits are per visitor address (IP) unless the name says otherwise. Many students share one
campus Wi-Fi address, so the per-address limits are deliberately generous. The strict limits
are per account, which is what actually stops someone guessing passwords.
"""

import hashlib

from flask import request
from flask_limiter.util import get_remote_address
from flask_login import current_user

from app.services import validation

LOGIN_PER_ADDRESS = "60 per minute"
LOGIN_FAILURES_PER_ACCOUNT = "5 per 15 minutes"  # only wrong passwords count
REGISTER_PER_ADDRESS = "30 per hour"
FORGOT_PASSWORD_PER_ADDRESS = "20 per 15 minutes"
FORGOT_PASSWORD_PER_ACCOUNT = "3 per hour"
RESEND_PER_USER = "5 per hour"


def typed_email_key():
    """Counts attempts per typed email address.

    It counts whatever was typed, whether or not an account exists, so being limited tells
    nobody anything about who is registered. Only a fingerprint of the address is kept.
    """
    email = validation.normalise_email(request.form.get("email", ""))
    if not email:
        return get_remote_address()
    return "email:" + hashlib.sha256(email.encode("utf-8")).hexdigest()[:32]


def logged_in_user_key():
    """Counts per logged-in user (falls back to the visitor address)."""
    if current_user.is_authenticated:
        return f"user:{current_user.id}"
    return get_remote_address()


def only_failed_logins(response):
    """True when the login attempt was refused (wrong email or password)."""
    return response.status_code == 401