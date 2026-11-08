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
    validate_config({"SECRET_KEY": "a" * 64, "ENVIRONMENT": "production"})