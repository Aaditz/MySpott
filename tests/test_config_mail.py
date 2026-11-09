"""Tests for the email and site-address settings."""

import pytest

from app import config
from app.config import ConfigError, TestingConfig, validate_config

GOOD_DB = "postgresql+psycopg://user:pass@localhost:5432/myspott_dev"

GOOD_PRODUCTION = {
    "SECRET_KEY": "a" * 64,
    "ENVIRONMENT": "production",
    "SQLALCHEMY_DATABASE_URI": GOOD_DB,
    "MAIL_BACKEND": "smtp",
    "MAIL_SERVER": "smtp.example.com",
    "APP_BASE_URL": "https://myspott.example",
}


def settings(**overrides):
    values = dict(GOOD_PRODUCTION)
    values.update(overrides)
    return values


def test_testing_config_never_sends_real_email():
    assert TestingConfig.MAIL_BACKEND == "memory"


def test_complete_production_settings_are_accepted():
    validate_config(settings())


def test_unknown_mail_backend_is_rejected():
    with pytest.raises(ConfigError, match="MAIL_BACKEND must be one of"):
        validate_config(settings(MAIL_BACKEND="carrier-pigeon"))


def test_smtp_needs_a_mail_server():
    with pytest.raises(ConfigError, match="MAIL_SERVER is missing"):
        validate_config(settings(MAIL_SERVER=None))


def test_production_refuses_console_and_memory_email():
    for backend in ["console", "memory"]:
        with pytest.raises(ConfigError, match="must be 'smtp'"):
            validate_config(settings(MAIL_BACKEND=backend))


def test_production_requires_an_https_site_address():
    with pytest.raises(ConfigError, match="https://"):
        validate_config(settings(APP_BASE_URL="http://myspott.example"))


def test_development_may_use_console_email_and_plain_http():
    validate_config(
        {
            "SECRET_KEY": "abc",
            "ENVIRONMENT": "development",
            "SQLALCHEMY_DATABASE_URI": GOOD_DB,
            "MAIL_BACKEND": "console",
            "APP_BASE_URL": "http://127.0.0.1:5000",
        }
    )


def test_mail_port_must_be_a_number(monkeypatch):
    monkeypatch.setenv("MAIL_PORT", "five-eighty-seven")
    with pytest.raises(ConfigError, match="MAIL_PORT must be a whole number"):
        config._env_int("MAIL_PORT", 587)


def test_mail_port_defaults_and_reads_numbers(monkeypatch):
    monkeypatch.delenv("MAIL_PORT", raising=False)
    assert config._env_int("MAIL_PORT", 587) == 587
    monkeypatch.setenv("MAIL_PORT", "2525")
    assert config._env_int("MAIL_PORT", 587) == 2525


def test_true_false_settings_are_read_correctly(monkeypatch):
    monkeypatch.delenv("MAIL_USE_TLS", raising=False)
    assert config._env_flag("MAIL_USE_TLS", True) is True
    for off in ["false", "FALSE", "0", "no", "off"]:
        monkeypatch.setenv("MAIL_USE_TLS", off)
        assert config._env_flag("MAIL_USE_TLS", True) is False, off
    monkeypatch.setenv("MAIL_USE_TLS", "true")
    assert config._env_flag("MAIL_USE_TLS", False) is True