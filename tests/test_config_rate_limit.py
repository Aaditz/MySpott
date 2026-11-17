"""Tests for the rate-limiting settings."""

import pytest

from app.config import ConfigError, validate_config

GOOD_DB = "postgresql+psycopg://user:pass@localhost:5432/myspott_dev"

PRODUCTION = {
    "SECRET_KEY": "a" * 64,
    "ENVIRONMENT": "production",
    "SQLALCHEMY_DATABASE_URI": GOOD_DB,
    "MAIL_BACKEND": "smtp",
    "MAIL_SERVER": "smtp.example.com",
    "APP_BASE_URL": "https://myspott.example",
}


def test_production_must_keep_rate_limiting_switched_on():
    with pytest.raises(ConfigError, match="RATELIMIT_ENABLED"):
        validate_config({**PRODUCTION, "RATELIMIT_ENABLED": False})

    validate_config({**PRODUCTION, "RATELIMIT_ENABLED": True})
    validate_config(PRODUCTION)  # on by default


def test_rate_limiting_may_be_switched_off_while_developing():
    validate_config(
        {
            "SECRET_KEY": "abc",
            "ENVIRONMENT": "development",
            "SQLALCHEMY_DATABASE_URI": GOOD_DB,
            "RATELIMIT_ENABLED": False,
        }
    )