"""Registration, login, logout and email confirmation pages."""

from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import limiter
from app.models import EmailToken
from app.services import auth_service, email_service, validation
from app.services.email_service import EmailDeliveryError
from app.services.validation import ValidationError
from app.web import rate_limits

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# One message for every failed login, so nobody can find out which emails have accounts.
GENERIC_LOGIN_ERROR = "Incorrect email or password."

INVALID_VERIFY_LINK_MESSAGE = (
    "This confirmation link is not valid. It may have expired or already been used."
)
INVALID_RESET_LINK_MESSAGE = (
    "This password reset link is not valid. It may have expired or already been used."
)

# The same answer whether or not the address has an account, so the form cannot be used
# to find out who is registered.
RESET_REQUESTED_MESSAGE = (
    "If an account exists for that email address, we have sent a link to reset the password."
)


@auth_bp.after_request
def stop_links_leaking_in_referrer(response):
    """Pages under /auth/ can have secret tokens in their address. Never pass them on to
    other sites through the browser's 'Referer' header."""
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def safe_next_url(target):
    """Return `target` only if it is a path on this site, otherwise None.

    After login people are sent back to the page they wanted. Without this check, a
    crafted link could send them to a fake site right after they typed their password.
    """
    if not target or not isinstance(target, str):
        return None
    if "\\" in target or any(ord(character) < 32 for character in target):
        return None
    parts = urlparse(target)
    if parts.scheme or parts.netloc:
        return None
    if not target.startswith("/") or target.startswith("//"):
        return None
    return target


# ------------------------------------------------------- register, login, logout

@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit(rate_limits.REGISTER_PER_ADDRESS, methods=["POST"], scope="register-by-address")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("web.home"))

    if request.method == "GET":
        return render_template("auth/register.html", errors={}, form={"role": "seeker"})

    form = {
        "name": request.form.get("name", ""),
        "email": request.form.get("email", ""),
        "role": request.form.get("role", "seeker"),
    }
    try:
        user = auth_service.register_user(
            name=form["name"],
            email=form["email"],
            password=request.form.get("password", ""),
            role=form["role"],
        )
    except ValidationError as error:
        # The password is never sent back to the page.
        return render_template("auth/register.html", errors=error.errors, form=form), 400

    _start_session(user)
    _send_verification_email(user, new_account=True)
    return redirect(url_for("web.home"))


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(rate_limits.LOGIN_PER_ADDRESS, methods=["POST"], scope="login-by-address")
@limiter.limit(
    rate_limits.LOGIN_FAILURES_PER_ACCOUNT,
    methods=["POST"],
    key_func=rate_limits.typed_email_key,
    deduct_when=rate_limits.only_failed_logins,
    scope="login-failures-by-account",
)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("web.home"))

    next_url = safe_next_url(request.values.get("next"))

    if request.method == "GET":
        return render_template("auth/login.html", error=None, email="", next_url=next_url)

    email = request.form.get("email", "")
    user = auth_service.authenticate(email, request.form.get("password", ""))
    if user is None:
        return (
            render_template(
                "auth/login.html", error=GENERIC_LOGIN_ERROR, email=email, next_url=next_url
            ),
            401,
        )

    _start_session(user)
    return redirect(next_url or url_for("web.home"))


@auth_bp.post("/logout")
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("web.home"))


# ------------------------------------------------------------ email confirmation

@auth_bp.get("/verify-email/<token>")
def verify_email_page(token):
    """The page the emailed link opens. It only SHOWS a button; it does not confirm anything.

    Some email programs open every link in a message to scan it for viruses. If opening
    the link confirmed the address, that scan would use up the one-time link before the
    person ever clicked it.
    """
    if not auth_service.is_token_usable(token, EmailToken.PURPOSE_VERIFY_EMAIL):
        return render_template("auth/link_invalid.html", message=INVALID_VERIFY_LINK_MESSAGE), 400
    return render_template("auth/verify_email.html", token=token)


@auth_bp.post("/verify-email/<token>")
def verify_email_submit(token):
    user = auth_service.verify_email(token)
    if user is None:
        return render_template("auth/link_invalid.html", message=INVALID_VERIFY_LINK_MESSAGE), 400

    flash("Thank you! Your email address is confirmed.", "success")
    return redirect(url_for("web.home"))


@auth_bp.post("/resend-verification")
@limiter.limit(
    rate_limits.RESEND_PER_USER, key_func=rate_limits.logged_in_user_key, scope="resend-by-user"
)
@login_required
def resend_verification():
    user = current_user._get_current_object()

    if user.is_email_verified:
        flash("Your email address is already confirmed.", "info")
        return redirect(url_for("web.home"))

    wait = auth_service.resend_wait_seconds(user, EmailToken.PURPOSE_VERIFY_EMAIL)
    if wait > 0:
        flash(f"Please wait {wait} seconds before asking for another email.", "warning")
        return redirect(url_for("web.home"))

    _send_verification_email(user, new_account=False)
    return redirect(url_for("web.home"))


# ------------------------------------------------------------- password reset

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit(
    rate_limits.FORGOT_PASSWORD_PER_ADDRESS, methods=["POST"], scope="forgot-by-address"
)
@limiter.limit(
    rate_limits.FORGOT_PASSWORD_PER_ACCOUNT,
    methods=["POST"],
    key_func=rate_limits.typed_email_key,
    scope="forgot-by-account",
)
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("web.home"))

    if request.method == "GET":
        return render_template("auth/forgot_password.html", error=None, email="")

    email = request.form.get("email", "")
    problem = validation.email_error(email)
    if problem:
        return render_template("auth/forgot_password.html", error=problem, email=email), 400

    result = auth_service.start_password_reset(email)
    if result is not None:
        user, raw_token = result
        try:
            email_service.send_password_reset_email(user, raw_token)
        except EmailDeliveryError:
            # Deliberately say nothing here. The page must look exactly the same whether or
            # not the address has an account. (The failure is logged by the email service.)
            pass

    flash(RESET_REQUESTED_MESSAGE, "info")
    return redirect(url_for("auth.login"))


@auth_bp.get("/reset-password/<token>")
def reset_password_page(token):
    if not auth_service.is_token_usable(token, EmailToken.PURPOSE_RESET_PASSWORD):
        return _invalid_reset_link()
    return render_template("auth/reset_password.html", token=token, error=None)


@auth_bp.post("/reset-password/<token>")
def reset_password_submit(token):
    try:
        user = auth_service.reset_password(token, request.form.get("password", ""))
    except ValidationError as error:
        # The link is NOT used up, so the person can try again with a better password.
        return (
            render_template(
                "auth/reset_password.html", token=token, error=error.errors["password"]
            ),
            400,
        )
    if user is None:
        return _invalid_reset_link()

    flash("Your password has been changed. Please log in with your new password.", "success")
    return redirect(url_for("auth.login"))


# --------------------------------------------------------------------- helpers

def _start_session(user):
    """Log the user in with a fresh session (nothing left over from before the login)."""
    session.clear()
    login_user(user)
    auth_service.record_login(user)


def _send_verification_email(user, new_account):
    raw_token = auth_service.issue_token(user, EmailToken.PURPOSE_VERIFY_EMAIL)
    try:
        email_service.send_verification_email(user, raw_token)
    except EmailDeliveryError:
        if new_account:
            message = (
                "Your account was created, but we could not send the confirmation email. "
                "You can ask for a new one with the button at the top of the page."
            )
        else:
            message = (
                "We could not send the confirmation email. Please try again in a few minutes."
            )
        flash(message, "warning")
    else:
        if new_account:
            message = "Welcome to MySpott! We sent a confirmation link to your email address."
        else:
            message = "We sent you a new confirmation link."
        flash(message, "success")


def _invalid_reset_link():
    return (
        render_template(
            "auth/link_invalid.html",
            message=INVALID_RESET_LINK_MESSAGE,
            new_link_url=url_for("auth.forgot_password"),
            new_link_label="Request a new reset link",
        ),
        400,
    )