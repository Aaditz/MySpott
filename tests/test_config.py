"""Tests for configuration loading and startup safety checks."""

import pytest

from app.config import (
    ConfigError,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    resolve_config,
    validate_config,
)

GOOD_DB = "postgresql+psycopg://user:pass@localhost:5432/myspott_dev"
GOOD_TEST_DB = "postgresql+psycopg://user:pass@localhost:5432/myspott_test"


def test_resolve_known_names():
    assert resolve_config("development") is DevelopmentConfig
    assert resolve_config("testing") is TestingConfig
    assert resolve_config("production") is ProductionConfig


def test_resolve_is_case_insensitive():
    assert resolve_config("  Production ") is ProductionConfig


def test_resolve_defaults_to_development(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    assert resolve_config() is DevelopmentConfig


def test_resolve_unknown_name_is_rejected():
    with pytest.raises(ConfigError, match="Unknown APP_ENV"):
        resolve_config("banana")


def test_missing_secret_key_is_rejected():
    with pytest.raises(ConfigError, match="SECRET_KEY is missing"):
        validate_config({"SECRET_KEY": None, "ENVIRONMENT": "development"})


def test_empty_secret_key_is_rejected():
    with pytest.raises(ConfigError, match="SECRET_KEY is missing"):
        validate_config({"SECRET_KEY": "", "ENVIRONMENT": "development"})


def test_placeholder_secret_key_is_rejected_in_production():
    with pytest.raises(ConfigError, match="placeholder"):
        validate_config({"SECRET_KEY": "change-me-please", "ENVIRONMENT": "production"})


def test_real_secret_key_is_accepted_in_production():
    validate_config(
        {
            "SECRET_KEY": "a" * 64,
            "ENVIRONMENT": "production",
            "SQLALCHEMY_DATABASE_URI": GOOD_DB,
            "MAIL_BACKEND": "smtp",
            "MAIL_SERVER": "smtp.example.com",
            "APP_BASE_URL": "https://myspott.example",
        }
    )


def test_missing_database_url_is_rejected():
    with pytest.raises(ConfigError, match="DATABASE_URL is missing"):
        validate_config({"SECRET_KEY": "abc", "ENVIRONMENT": "development"})


def test_missing_test_database_url_is_rejected():
    with pytest.raises(ConfigError, match="TEST_DATABASE_URL is missing"):
        validate_config({"SECRET_KEY": "abc", "ENVIRONMENT": "testing"})


def test_non_postgresql_database_is_rejected():
    with pytest.raises(ConfigError, match="PostgreSQL"):
        validate_config(
            {
                "SECRET_KEY": "abc",
                "ENVIRONMENT": "development",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///local.db",
            }
        )


def test_test_database_name_must_end_with_test():
    with pytest.raises(ConfigError, match="_test"):
        validate_config(
            {
                "SECRET_KEY": "abc",
                "ENVIRONMENT": "testing",
                "SQLALCHEMY_DATABASE_URI": GOOD_DB,  # a development database: must be refused
            }
        )


def test_valid_development_and_testing_settings_are_accepted():
    validate_config(
        {"SECRET_KEY": "abc", "ENVIRONMENT": "development", "SQLALCHEMY_DATABASE_URI": GOOD_DB}
    )
    validate_config(
        {"SECRET_KEY": "abc", "ENVIRONMENT": "testing", "SQLALCHEMY_DATABASE_URI": GOOD_TEST_DB}
    )


def test_error_messages_never_contain_the_database_password():
    with pytest.raises(ConfigError) as error:
        validate_config(
            {
                "SECRET_KEY": "abc",
                "ENVIRONMENT": "testing",
                "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg://user:topsecret@localhost/myspott_dev",
            }
        )
    assert "topsecret" not in str(error.value)