from flask import current_app

from . import web


@web.get("/")
def home():
    return f"{current_app.config['APP_NAME']} is running."