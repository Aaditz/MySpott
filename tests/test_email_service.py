"""Tests for email sending. No real email is ever sent."""

import smtplib

import pytest

from app.services import email_service
from app.services.email_service import EmailDeliveryError


@pytest.fixture(autouse=True)
def empty_outbox():
    email_service.outbox.clear()
    yield
    email_service.outbox.clear()


class FakeSMTP:
    """Stands in for a real mail server and records what it was asked to do."""

    instances = []
    fail_on = None  # "connect" or "send" makes the fake misbehave

    def __init__(self, host, port, timeout=None):
        if FakeSMTP.fail_on == "connect":
            raise ConnectionRefusedError("no server here")
        self.host, self.port, self.timeout = host, port, timeout
        self.calls = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def starttls(self):
        self.calls.append(("starttls",))

    def login(self, username, password):
        self.calls.append(("login", username, password))

    def send_message(self, message):
        if FakeSMTP.fail_on == "send":
            raise smtplib.SMTPRecipientsRefused({})
        self.calls.append(("send", message))


@pytest.fixture()
def fake_smtp(app, monkeypatch):
    FakeSMTP.instances = []
    FakeSMTP.fail_on = None
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    app.config.update(
        MAIL_BACKEND="smtp",
        MAIL_SERVER="smtp.example.com",
        MAIL_PORT=587,
        MAIL_USERNAME="mailer",
        MAIL_PASSWORD="mail-secret",
        MAIL_USE_TLS=True,
    )
    return FakeSMTP


def test_verification_email_contains_the_link_and_expiry(app, user_factory):
    user = user_factory()

    email_service.send_verification_email(user, "RAWTOKEN123")

    assert len(email_service.outbox) == 1
    message = email_service.outbox[0]
    body = message.get_content()
    assert message["To"] == "ada@example.com"
    assert message["From"] == app.config["MAIL_FROM"]
    assert "Confirm" in message["Subject"]
    assert "http://localhost/auth/verify-email/RAWTOKEN123" in body
    assert "Ada Lovelace" in body
    assert "24 hours" in body


def test_password_reset_email_contains_the_link_and_expiry(app, user_factory):
    user = user_factory()

    email_service.send_password_reset_email(user, "RESETTOKEN456")

    message = email_service.outbox[0]
    body = message.get_content()
    assert "Reset" in message["Subject"]
    assert "http://localhost/auth/reset-password/RESETTOKEN456" in body
    assert "1 hour" in body
    assert "ignore this email" in body


def test_links_use_the_configured_site_address_only(app, user_factory):
    app.config["APP_BASE_URL"] = "https://myspott.example"

    email_service.send_password_reset_email(user_factory(), "TOKEN")

    body = email_service.outbox[0].get_content()
    assert "https://myspott.example/auth/reset-password/TOKEN" in body


def test_time_spans_are_described_in_words():
    from datetime import timedelta

    assert email_service._describe(timedelta(hours=24)) == "24 hours"
    assert email_service._describe(timedelta(hours=1)) == "1 hour"
    assert email_service._describe(timedelta(minutes=60)) == "1 hour"
    assert email_service._describe(timedelta(minutes=45)) == "45 minutes"
    assert email_service._describe(timedelta(minutes=1)) == "1 minute"


def test_console_backend_prints_the_email(app, user_factory, capsys):
    app.config["MAIL_BACKEND"] = "console"

    email_service.send_verification_email(user_factory(), "CONSOLETOKEN")

    printed = capsys.readouterr().out
    assert "ada@example.com" in printed
    assert "/auth/verify-email/CONSOLETOKEN" in printed
    assert email_service.outbox == []


def test_smtp_backend_logs_in_and_sends_over_tls(fake_smtp, user_factory):
    email_service.send_verification_email(user_factory(), "SMTPTOKEN")

    server = fake_smtp.instances[0]
    assert (server.host, server.port, server.timeout) == ("smtp.example.com", 587, 15)
    assert [call[0] for call in server.calls] == ["starttls", "login", "send"]
    assert server.calls[1] == ("login", "mailer", "mail-secret")
    assert "SMTPTOKEN" in server.calls[2][1].get_content()


def test_smtp_backend_skips_tls_and_login_when_not_configured(fake_smtp, app, user_factory):
    app.config.update(MAIL_USE_TLS=False, MAIL_USERNAME=None, MAIL_PASSWORD=None)

    email_service.send_verification_email(user_factory(), "TOKEN")

    assert [call[0] for call in fake_smtp.instances[0].calls] == ["send"]


def test_smtp_connection_failure_becomes_a_delivery_error(fake_smtp, user_factory):
    fake_smtp.fail_on = "connect"

    with pytest.raises(EmailDeliveryError):
        email_service.send_verification_email(user_factory(), "TOKEN")


def test_smtp_refusal_becomes_a_delivery_error(fake_smtp, user_factory):
    fake_smtp.fail_on = "send"

    with pytest.raises(EmailDeliveryError):
        email_service.send_verification_email(user_factory(), "TOKEN")


def test_unknown_backend_is_refused(app):
    app.config["MAIL_BACKEND"] = "carrier-pigeon"

    with pytest.raises(ValueError):
        email_service.send_email("ada@example.com", "Hello", "Body")


def test_line_breaks_in_the_address_cannot_inject_extra_recipients(app):
    with pytest.raises(ValueError):
        email_service.send_email("ada@example.com\nBcc: evil@example.com", "Hello", "Body")

    assert email_service.outbox == []