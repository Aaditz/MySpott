"""Input checks shared by the website and (later) the mobile API.

Each *_error function returns a friendly message, or None when the value is fine.
"""

import re

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# A very small list of the most common passwords. This is a basic safety net, not a full blocklist.
COMMON_PASSWORDS = {
    "password",
    "password1",
    "password123",
    "12345678",
    "123456789",
    "1234567890",
    "qwertyui",
    "qwerty123",
    "iloveyou",
    "11111111",
    "00000000",
    "abc12345",
    "letmein1",
    "welcome1",
    "admin123",
}

# Something@something.something, with no spaces. The real proof an address works is the emailed link.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


class ValidationError(Exception):
    """Raised with a dictionary of {field name: friendly message}."""

    def __init__(self, errors):
        self.errors = dict(errors)
        super().__init__("; ".join(self.errors.values()))


def normalise_email(email):
    """Trim spaces and lowercase, so 'Ada@X.com ' and 'ada@x.com' are the same address."""
    return (email or "").strip().lower()


def name_error(name):
    cleaned = (name or "").strip()
    if len(cleaned) < 2:
        return "Please enter your name (at least 2 characters)."
    if len(cleaned) > 100:
        return "Your name is too long (100 characters at most)."
    if any(ord(character) < 32 for character in cleaned):
        return "Your name contains characters that are not allowed."
    return None


def email_error(email):
    cleaned = normalise_email(email)
    if not cleaned:
        return "Please enter your email address."
    if (
        len(cleaned) > 254
        or not _EMAIL_PATTERN.match(cleaned)
        or len(cleaned.split("@")[0]) > 64
    ):
        return "Please enter a valid email address."
    return None


def password_error(password, email=""):
    if not isinstance(password, str) or password == "":
        return "Please enter a password."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Your password must be at least {MIN_PASSWORD_LENGTH} characters long."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Your password must be at most {MAX_PASSWORD_LENGTH} characters long."
    if password.strip() == "":
        return "Your password cannot be only spaces."
    if password.lower() in COMMON_PASSWORDS:
        return "That password is too common. Please choose a less predictable one."
    if email and password.strip().lower() == normalise_email(email):
        return "Your password cannot be the same as your email address."
    return None