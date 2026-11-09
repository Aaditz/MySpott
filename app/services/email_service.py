"""Sending email.

The backend is chosen by the MAIL_BACKEND setting:
  console - prints the email in the Terminal (development: click the link right there)
  smtp    - sends it through a real mail server (production)
  memory  - keeps it in a list called `outbox` (automated tests)
"""

import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

from app.models import EmailToken
from app.services import auth_service

logger = logging.getLogger(__name__)

# Emails "sent" by the memory backend. Tests read this list.
outbox = []

# The website pages for these paths are built in Phase 3, Steps 5 and 6.
VERIFY_EMAIL_PATH = "/auth/verify-email/"
RESET_PASSWORD_PATH = "/auth/reset-password/"


class EmailDeliveryError(Exception):
    """Raised when an email could not be handed to the mail server."""


def send_email(to_address, subject, body):
    """Send one plain-text email using the configured backend."""
    config = current_app.config

    message = EmailMessage()
    message["From"] = config["MAIL_FROM"]
    message["To"] = to_address  # a line break in here raises ValueError, which blocks header injection
    message["Subject"] = subject
    message.set_content(body)

    backend = config["MAIL_BACKEND"]
    if backend == "memory":
        outbox.append(message)
    elif backend == "console":
        _print_to_console(message)
    elif backend == "smtp":
        _send_with_smtp(message)
    else:
        raise ValueError(f"Unknown MAIL_BACKEND: {backend}")


def send_verification_email(user, raw_token):
    link = _build_link(VERIFY_EMAIL_PATH, raw_token)
    lifetime = _describe(auth_service.TOKEN_LIFETIMES[EmailToken.PURPOSE_VERIFY_EMAIL])
    body = (
        f"Hi {user.name},\n\n"
        "Welcome to MySpott! Please confirm your email address by opening this link:\n\n"
        f"{link}\n\n"
        f"The link works once and expires in {lifetime}.\n\n"
        "If you did not create a MySpott account, you can ignore this email.\n"
    )
    send_email(user.email, "Confirm your MySpott email address", body)


def send_password_reset_email(user, raw_token):
    link = _build_link(RESET_PASSWORD_PATH, raw_token)
    lifetime = _describe(auth_service.TOKEN_LIFETIMES[EmailToken.PURPOSE_RESET_PASSWORD])
    body = (
        f"Hi {user.name},\n\n"
        "We received a request to reset your MySpott password. Choose a new password here:\n\n"
        f"{link}\n\n"
        f"The link works once and expires in {lifetime}.\n\n"
        "If you did not ask for this, you can ignore this email. Your password will not change.\n"
    )
    send_email(user.email, "Reset your MySpott password", body)


# --------------------------------------------------------------------- helpers

def _build_link(path, raw_token):
    return f"{current_app.config['APP_BASE_URL']}{path}{raw_token}"


def _describe(lifetime):
    """Turn a time span into words, e.g. '24 hours' or '1 hour' or '45 minutes'."""
    seconds = int(lifetime.total_seconds())
    if seconds % 3600 == 0:
        hours = seconds // 3600
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    minutes = seconds // 60
    return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"


def _print_to_console(message):
    """Development only: show the email in the Terminal instead of sending it."""
    print("\n" + "=" * 70, flush=True)
    print("EMAIL (printed here because MAIL_BACKEND=console)", flush=True)
    print(f"To:      {message['To']}", flush=True)
    print(f"Subject: {message['Subject']}", flush=True)
    print("-" * 70, flush=True)
    print(message.get_content(), flush=True)
    print("=" * 70 + "\n", flush=True)


def _send_with_smtp(message):
    config = current_app.config
    try:
        with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=15) as server:
            if config["MAIL_USE_TLS"]:
                server.starttls()
            if config["MAIL_USERNAME"]:
                server.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"] or "")
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as error:
        # Log only the kind of failure: never the address, the password or the message.
        logger.error("Email delivery failed: %s", type(error).__name__)
        raise EmailDeliveryError("The email could not be sent.") from error