"""MySpott configuration.

All settings are read from environment variables (see .env.example).
Secrets are never written in source code.
"""

import os

from dotenv import load_dotenv

# Reads the .env file in the project folder (if it exists) into the environment.
load_dotenv()


class ConfigError(RuntimeError):
    """Raised when a required setting is missing or unsafe."""


PLACEHOLDER_PREFIX = "change-me"


class BaseConfig:
    APP_NAME = "MySpott"
    ENVIRONMENT = "base"
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SECRET_KEY")


class DevelopmentConfig(BaseConfig):
    ENVIRONMENT = "development"
    DEBUG = True


class TestingConfig(BaseConfig):
    ENVIRONMENT = "testing"
    TESTING = True
    # Tests use a fixed fake key so they never depend on your real .env file.
    SECRET_KEY = "testing-only-secret-key"


class ProductionConfig(BaseConfig):
    ENVIRONMENT = "production"


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
    """Stop the app at startup with a clear message if a critical setting is bad."""
    secret = app_config.get("SECRET_KEY")
    if not secret:
        raise ConfigError(
            "SECRET_KEY is missing. Copy .env.example to .env and set SECRET_KEY "
            "(see the instructions in the project guide)."
        )
    if app_config.get("ENVIRONMENT") == "production" and secret.startswith(PLACEHOLDER_PREFIX):
        raise ConfigError("SECRET_KEY still has the placeholder value. Set a real random key.")