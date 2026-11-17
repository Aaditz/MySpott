"""The User model: every person with a MySpott account (seeker, owner or admin)."""

import hashlib
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    ROLE_SEEKER = "seeker"
    ROLE_OWNER = "owner"
    ROLE_ADMIN = "admin"

    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_SEEKER)
    account_status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE)
    email_verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    whatsapp_e164 = db.Column(db.String(16), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.CheckConstraint("role IN ('seeker', 'owner', 'admin')", name="role_valid"),
        db.CheckConstraint(
            "account_status IN ('active', 'suspended')", name="account_status_valid"
        ),
    )

    @validates("email")
    def _normalise_email(self, key, value):
        """Store emails trimmed and lowercase so 'Ada@x.com' and 'ada@x.com' are the same."""
        return value.strip().lower() if value else value

    def set_password(self, password):
        """Store a secure hash of the password. The plain password is never saved."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ------------------------------------------------------------ login cookies

    @property
    def session_fingerprint(self):
        """A short fingerprint of the current password hash.

        It is stored in the login cookie next to the user id. When the password changes,
        the fingerprint changes too, so every login cookie issued before the change stops
        working at once, on every device. It cannot be turned back into the password.
        """
        return hashlib.sha256(self.password_hash.encode("utf-8")).hexdigest()[:16]

    def get_id(self):
        """What Flask-Login keeps in the login cookie: 'user id:fingerprint'."""
        return f"{self.id}:{self.session_fingerprint}"

    @staticmethod
    def parse_session_id(session_id):
        """Split the cookie text back into (user id, fingerprint).

        Returns None for anything that does not look exactly right.
        """
        if not isinstance(session_id, str) or session_id.count(":") != 1:
            return None
        user_id, fingerprint = session_id.split(":")
        if not user_id.isascii() or not user_id.isdigit() or len(user_id) > 18 or not fingerprint:
            return None
        return int(user_id), fingerprint

    @property
    def is_active(self):
        """Flask-Login refuses to log in a user whose is_active is False (suspended accounts)."""
        return self.account_status == self.STATUS_ACTIVE

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None

    def __repr__(self):
        # Only the id: emails are personal data and should not end up in logs.
        return f"<User id={self.id}>"