"""One-time tokens sent by email (to verify an address or reset a password)."""

from app.extensions import db
from app.models.user import utc_now


class EmailToken(db.Model):
    __tablename__ = "email_tokens"

    PURPOSE_VERIFY_EMAIL = "verify_email"
    PURPOSE_RESET_PASSWORD = "reset_password"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    purpose = db.Column(db.String(30), nullable=False)
    # SHA-256 fingerprint (64 characters) of the emailed token. The token itself is never stored.
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    user = db.relationship(
        "User",
        backref=db.backref(
            "email_tokens", cascade="all, delete-orphan", passive_deletes=True
        ),
    )

    __table_args__ = (
        db.CheckConstraint(
            "purpose IN ('verify_email', 'reset_password')", name="purpose_valid"
        ),
    )

    @property
    def is_used(self):
        return self.used_at is not None

    def is_expired(self, now=None):
        return (now or utc_now()) >= self.expires_at