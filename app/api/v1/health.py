"""Health check endpoint: confirms the app is running."""

from flask import current_app, jsonify

from . import api_v1


@api_v1.get("/health")
def health():
    return jsonify(
        status="ok",
        app=current_app.config["APP_NAME"],
        environment=current_app.config["ENVIRONMENT"],
    )