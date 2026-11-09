"""MySpott configuration.

All settings are read from environment variables (see .env.example).
Secrets are never written in source code.
"""

import os
from urllib.parse import urlparse

from dotenv import load_dotenv

# Reads the .env file in the project folder (if it exists) into the environment.
load_dotenv()


class ConfigError(RuntimeError):
    """Raised when a required setting is missing or unsafe."""


PLACEHOLDER_PREFIX = "change-me"

MAIL_BACKENDS = ("console", "memory", "smtp")


def _env_int(name, default):
    """Read a whole number from the environment, with a clear error if it is not a number."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        raise ConfigError(f"{name} must be a whole number, but it is '{value}'.") from None


def _env_flag(name, default):
    """Read a true/false setting from the environment."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


class BaseConfig:
    APP_NAME = "MySpott"
    ENVIRONMENT = "base"
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Quietly replaces database connections that went stale.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Login cookies: not readable by JavaScript, not sent along with requests from other sites.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # The public address of the site. Emailed links are built from THIS, never from the
    # incoming request, so nobody can trick the site into sending links to a fake address.
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000").strip().rstrip("/")

    # Email: "console" prints emails in the Terminal, "smtp" sends them through a real mail
    # server, "memory" keeps them in a list (used by automated tests).
    MAIL_BACKEND = os.environ.get("MAIL_BACKEND", "console").strip().lower()
    MAIL_FROM = os.environ.get("MAIL_FROM", "MySpott <no-reply@myspott.local>")
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = _env_int("MAIL_PORT", 587)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_USE_TLS = _env_flag("MAIL_USE_TLS", True)


class DevelopmentConfig(BaseConfig):
    ENVIRONMENT = "development"
    DEBUG = True


class TestingConfig(BaseConfig):
    ENVIRONMENT = "testing"
    TESTING = True
    # Tests use a fixed fake key so they never depend on your real .env file.
    SECRET_KEY = "testing-only-secret-key"
    # Tests use their OWN database, because they erase everything in it.
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL")
    # Tests never print or send real email, and use fixed addresses.
    MAIL_BACKEND = "memory"
    MAIL_FROM = "MySpott <no-reply@myspott.test>"
    APP_BASE_URL = "http://localhost"


class ProductionConfig(BaseConfig):
    ENVIRONMENT = "production"
    # Login cookies are only ever sent over HTTPS in production.
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def resolve_config(name=None):
    """Return the config class for the given name (or APP_ENV, default 'development')."""
    name = (name or os.environ.get("APP_ENV") or "development").strip().lower()
    try:
        return CONFIG_BY_NAME[name]
    except KeyError:
        valid = ", ".join(sorted(CONFIG_BY_NAME))
        raise ConfigError(
            f"Unknown APP_ENV '{name}'. Use one of: {valid}."
        ) from None


def validate_config(app_config):
    """Stop the app at startup with a clear message if a critical setting is bad.

    Error messages never include the database address, because it contains a password.
    """
    environment = app_config.get("ENVIRONMENT")

    secret = app_config.get("SECRET_KEY")
    if not secret:
        raise ConfigError(
            "SECRET_KEY is missing. Copy .env.example to .env and set SECRET_KEY "
            "(see the instructions in the project guide)."
        )
    if environment == "production" and secret.startswith(PLACEHOLDER_PREFIX):
        raise ConfigError("SECRET_KEY still has the placeholder value. Set a real random key.")

    variable = "TEST_DATABASE_URL" if environment == "testing" else "DATABASE_URL"
    database_uri = app_config.get("SQLALCHEMY_DATABASE_URI")
    if not database_uri:
        raise ConfigError(
            f"{variable} is missing. Add it to your .env file (see .env.example)."
        )
    if not database_uri.startswith("postgresql"):
        raise ConfigError(
            f"{variable} must be a PostgreSQL address starting with 'postgresql+psycopg://'."
        )
    if environment == "testing":
        database_name = urlparse(database_uri).path.strip("/")
        if not database_name.endswith("_test"):
            raise ConfigError(
                "TEST_DATABASE_URL must point to a database whose name ends with '_test', "
                "because tests erase all data in it."
            )

    mail_backend = app_config.get("MAIL_BACKEND", "console")
    if mail_backend not in MAIL_BACKENDS:
        raise ConfigError("MAIL_BACKEND must be one of: console, memory, smtp.")
    if mail_backend == "smtp" and not app_config.get("MAIL_SERVER"):
        raise ConfigError("MAIL_SERVER is missing. It is required when MAIL_BACKEND is 'smtp'.")
    if environment == "production":
        if mail_backend != "smtp":
            raise ConfigError("In production MAIL_BACKEND must be 'smtp', so real emails are sent.")
        if not str(app_config.get("APP_BASE_URL", "")).startswith("https://"):
            raise ConfigError("In production APP_BASE_URL must start with 'https://'.")