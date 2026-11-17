"""Checks that decide who may open a page.

Put one of these under the page's route decorator, for example:

    @web.get("/owner/dashboard")
    @owner_required
    def owner_dashboard(): ...
"""

from functools import wraps

from flask import abort, current_app, flash, redirect, url_for
from flask_login import current_user

from app.models import User


def roles_required(*roles):
    """Only logged-in users with one of these roles may open the page."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator


# Strict on purpose: an admin is not automatically an owner, and an owner is never an admin.
owner_required = roles_required(User.ROLE_OWNER)
admin_required = roles_required(User.ROLE_ADMIN)


def verified_required(view):
    """Only logged-in users who have confirmed their email address may open the page."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if not current_user.is_email_verified:
            flash("Please confirm your email address first. We emailed you a link.", "warning")
            return redirect(url_for("web.home"))
        return view(*args, **kwargs)

    return wrapper