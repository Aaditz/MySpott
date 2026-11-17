"""MySpott application factory."""

import hmac
import logging

from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFError

from .config import resolve_config, validate_config
from .extensions import csrf, db, limiter, login_manager, migrate


def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(resolve_config(config_name))
    validate_config(app.config)
    # Forms stay valid for 8 hours (Flask-WTF's default is only 1 hour).
    app.config.setdefault("WTF_CSRF_TIME_LIMIT", 8 * 60 * 60)

    _configure_logging(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_commands(app)

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
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    # Where people are sent when a page needs a login.
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(session_id):
        """Turns the text in the login cookie back into a User, or nobody.

        The cookie holds 'user id:password fingerprint'. It stops working when the account is
        deleted or suspended, or when the password has changed since the login.
        """
        parsed = User.parse_session_id(session_id)
        if parsed is None:
            return None
        user_id, fingerprint = parsed

        user = db.session.get(User, user_id)
        if user is None or not user.is_active:
            return None
        if not hmac.compare_digest(
            fingerprint.encode("utf-8"), user.session_fingerprint.encode("utf-8")
        ):
            return None
        return user


def _register_blueprints(app):
    from .api.v1 import api_v1
    from .web import web
    from .web.auth import auth_bp

    app.register_blueprint(api_v1)
    app.register_blueprint(web)
    app.register_blueprint(auth_bp)


def _register_error_handlers(app):
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return (
            render_template(
                "error.html",
                title="Please try again",
                message="Your form expired or could not be verified. "
                "Go back, reload the page and submit it again.",
            ),
            400,
        )

    @app.errorhandler(403)
    def handle_forbidden(error):
        if request.path.startswith("/api/"):
            return jsonify(error="You do not have access to this."), 403
        return (
            render_template(
                "error.html",
                title="No access",
                message="You do not have permission to open this page.",
            ),
            403,
        )

    @app.errorhandler(429)
    def handle_too_many_requests(error):
        if request.path.startswith("/api/"):
            return jsonify(error="Too many requests. Please wait a few minutes and try again."), 429
        return (
            render_template(
                "error.html",
                title="Too many attempts",
                message="You have tried this too many times. "
                "Please wait a few minutes and try again.",
            ),
            429,
        )

    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith("/api/"):
            return jsonify(error="Not found."), 404
        return (
            render_template(
                "error.html",
                title="Page not found",
                message="We could not find the page you were looking for.",
            ),
            404,
        )


def _register_commands(app):
    from .cli import register_commands

    register_commands(app)