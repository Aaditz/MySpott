"""Website pages. The real MySpott interface is built in Phase 4."""

from flask import Blueprint

web = Blueprint("web", __name__)

from . import routes  # noqa: E402,F401