"""MySpott application factory."""

import logging

from flask import Flask

from .config import resolve_config, validate_config
from .extensions import db, login_manager, migrate


def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(resolve_config(config_name))
    validate_config(app.config)

    _configure_logging(app)
    _init_extensions(app)
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


def _init_extensions(app):
    # Importing the models makes every table known to SQLAlchemy and to migrations.
    from .models import User

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        """Turns the user id stored in the login cookie back into a User (or nobody)."""
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None


def _register_blueprints(app):
    from .api.v1 import api_v1
    from .web import web

    app.register_blueprint(api_v1)
    app.register_blueprint(web)