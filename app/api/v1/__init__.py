"""Version 1 of the MySpott JSON API (used by the website and the mobile apps)."""

from flask import Blueprint

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Importing the route modules attaches their routes to the blueprint.
from . import health  # noqa: E402,F401