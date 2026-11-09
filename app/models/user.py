"""The User model: every person with a MySpott account (seeker, owner or admin)."""

from datetime import datetime, timezone

from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
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

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None

    def __repr__(self):
        # Only the id: emails are personal data and should not end up in logs.
        return f"<User id={self.id}>"