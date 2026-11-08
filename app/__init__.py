"""MySpott application factory."""

import logging

from flask import Flask

from .config import resolve_config, validate_config


def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(resolve_config(config_name))
    validate_config(app.config)

    _configure_logging(app)
    _register_blueprints(app)

    app.logger.info(
        "%s started in %s mode", app.config["APP_NAME"], app.config["ENVIRONMENT"]
    )
    return app


def _configure_logging(app):
    level = logging.DEBUG if app.config["DEBUG"] else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app.logger.setLevel(level)


def _register_blueprints(app):
    from .api.v1 import api_v1
    from .web import web

    app.register_blueprint(api_v1)
    app.register_blueprint(web)