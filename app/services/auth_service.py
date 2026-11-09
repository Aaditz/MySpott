"""Account logic: registration, login checks, and emailed one-time tokens.

This file knows nothing about web pages. The website (and later the mobile API)
call these functions, so the rules live in exactly one place.
"""

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import EmailToken, User
from app.models.user import utc_now
from app.services import validation
from app.services.validation import ValidationError

# How long each kind of emailed link stays valid.
TOKEN_LIFETIMES = {
    EmailToken.PURPOSE_VERIFY_EMAIL: timedelta(hours=24),
    EmailToken.PURPOSE_RESET_PASSWORD: timedelta(minutes=60),
}

# People can sign up as seekers or owners. Admins are never created through sign-up.
SIGNUP_ROLES = (User.ROLE_SEEKER, User.ROLE_OWNER)

EMAIL_TAKEN_MESSAGE = "An account with this email already exists."

# Used to spend the same time on unknown emails as on real ones (see authenticate()).
_dummy_hash = None


# ---------------------------------------------------------------- registration

def register_user(name, email, password, role=User.ROLE_SEEKER):
    """Create a new account. Raises ValidationError with friendly messages if input is bad."""
    cleaned_email = validation.normalise_email(email)

    errors = {}
    problem = validation.name_error(name)
    if problem:
        errors["name"] = problem
    problem = validation.email_error(cleaned_email)
    if problem:
        errors["email"] = problem
    problem = validation.password_error(password, cleaned_email)
    if problem:
        errors["password"] = problem
    if role not in SIGNUP_ROLES:
        errors["role"] = "Please choose whether you are looking for a home or listing one."
    if errors:
        raise ValidationError(errors)

    if _find_user_by_email(cleaned_email) is not None:
        raise ValidationError({"email": EMAIL_TAKEN_MESSAGE})

    user = User(name=name.strip(), email=cleaned_email, role=role)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # Someone registered the same email at the very same moment.
        db.session.rollback()
        raise ValidationError({"email": EMAIL_TAKEN_MESSAGE}) from None
    return user


# ----------------------------------------------------------------------- login

def authenticate(email, password):
    """Return the user if the email and password are right and the account is active.

    Returns None in every failure case, so the website can show one generic message
    and never reveals which emails have accounts.
    """
    if not isinstance(password, str) or not password or len(password) > validation.MAX_PASSWORD_LENGTH:
        return None

    user = _find_user_by_email(validation.normalise_email(email))
    if user is None:
        # Do the same slow password check anyway, so response time doesn't give the answer away.
        check_password_hash(_get_dummy_hash(), password)
        return None

    password_ok = user.check_password(password)
    if password_ok and user.is_active:
        return user
    return None


def record_login(user):
    """Remember when the user last logged in."""
    user.last_login_at = utc_now()
    db.session.commit()


# ---------------------------------------------------------------- email tokens

def issue_token(user, purpose):
    """Create a one-time token for the user and return the RAW token (to put in the email).

    Only a fingerprint (hash) of the token is stored. If the database ever leaked,
    the stored values could not be used to take over accounts.
    """
    if purpose not in TOKEN_LIFETIMES:
        raise ValueError(f"Unknown token purpose: {purpose}")

    # Only the newest link should work: remove this user's unused tokens of the same kind.
    db.session.execute(
        delete(EmailToken).where(
            EmailToken.user_id == user.id,
            EmailToken.purpose == purpose,
            EmailToken.used_at.is_(None),
        )
    )

    raw_token = secrets.token_urlsafe(32)
    db.session.add(
        EmailToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=_hash_token(raw_token),
            expires_at=utc_now() + TOKEN_LIFETIMES[purpose],
        )
    )
    db.session.commit()
    return raw_token


def verify_email(raw_token):
    """Use a verification link. Returns the user, or None if the link is wrong, used or expired."""
    token = _find_usable_token(raw_token, EmailToken.PURPOSE_VERIFY_EMAIL)
    if token is None or not _claim_token(token):
        db.session.rollback()
        return None

    user = token.user
    if user.email_verified_at is None:
        user.email_verified_at = utc_now()
    db.session.commit()
    return user


def reset_password(raw_token, new_password):
    """Use a password-reset link to set a new password.

    Returns the user, or None if the link is wrong, used or expired.
    Raises ValidationError if the new password is not acceptable. In that case the
    link is NOT used up, so the person can try again with a better password.
    """
    token = _find_usable_token(raw_token, EmailToken.PURPOSE_RESET_PASSWORD)
    if token is None:
        return None

    user = token.user
    problem = validation.password_error(new_password, user.email)
    if problem:
        raise ValidationError({"password": problem})

    if not _claim_token(token):
        db.session.rollback()
        return None

    user.set_password(new_password)
    db.session.commit()
    return user


# --------------------------------------------------------------------- helpers

def _find_user_by_email(cleaned_email):
    return db.session.scalar(select(User).where(User.email == cleaned_email))


def _hash_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _find_usable_token(raw_token, purpose):
    """Find the token row for a raw token, if it is the right kind, unused and not expired."""
    if not isinstance(raw_token, str) or not raw_token or len(raw_token) > 200:
        return None
    token = db.session.scalar(
        select(EmailToken).where(
            EmailToken.token_hash == _hash_token(raw_token),
            EmailToken.purpose == purpose,
        )
    )
    if token is None or token.is_used or token.is_expired():
        return None
    return token


def _claim_token(token):
    """Mark the token as used. Returns False if someone else used it a moment ago."""
    result = db.session.execute(
        update(EmailToken)
        .where(EmailToken.id == token.id, EmailToken.used_at.is_(None))
        .values(used_at=utc_now())
    )
    return result.rowcount == 1


def _get_dummy_hash():
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = generate_password_hash("a-password-nobody-will-ever-use")
    return _dummy_hash