"""Tests for the input checks (no database needed)."""

from app.services import validation


def test_good_names_are_accepted():
    for name in ["Ada Lovelace", "  Jo  ", "Ananya Rao-Iyer", "李雷"]:
        assert validation.name_error(name) is None, name


def test_bad_names_are_rejected():
    for name in [None, "", " ", "A", "x" * 101, "Bad\nName"]:
        assert validation.name_error(name) is not None, repr(name)


def test_email_is_trimmed_and_lowercased():
    assert validation.normalise_email("  Ada@Example.COM ") == "ada@example.com"
    assert validation.normalise_email(None) == ""


def test_good_emails_are_accepted():
    for email in ["ada@example.com", "  Ada.L+rent@Mail.Example.co.in ", "a@b.co"]:
        assert validation.email_error(email) is None, email


def test_bad_emails_are_rejected():
    long_local = "a" * 65 + "@example.com"
    too_long = "a@" + "b" * 250 + ".com"
    for email in [None, "", "ada", "ada@", "@example.com", "ada@example", "ada @example.com",
                  "ada@@example.com", "ada@example..com", "ada@.example.com", long_local, too_long]:
        assert validation.email_error(email) is not None, repr(email)


def test_good_password_is_accepted():
    assert validation.password_error("correct-horse-battery", "ada@example.com") is None
    assert validation.password_error("x" * 128) is None


def test_short_and_long_passwords_are_rejected():
    assert "at least 8" in validation.password_error("short7!")
    assert "at most 128" in validation.password_error("x" * 129)


def test_empty_or_blank_passwords_are_rejected():
    assert validation.password_error(None) is not None
    assert validation.password_error("") is not None
    assert "only spaces" in validation.password_error("        ")


def test_common_passwords_are_rejected():
    for password in ["password", "Password123", "12345678", "QWERTY123"]:
        assert "too common" in validation.password_error(password), password


def test_password_cannot_be_the_email_address():
    message = validation.password_error("Ada@Example.com", "ada@example.com")
    assert "same as your email" in message


def test_validation_error_keeps_the_messages():
    error = validation.ValidationError({"email": "Bad email.", "password": "Too short."})
    assert error.errors == {"email": "Bad email.", "password": "Too short."}
    assert "Bad email." in str(error)