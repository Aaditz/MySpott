"""The Property model: one home that an owner lists for rent.

In the app people see these as "listings"; the table keeps the SRS name, `properties`.
"""

from app.extensions import db
from app.models.user import utc_now
from app.services import listing_options as options


class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Most details may be empty while the listing is a draft (see options.check_rules()).
    title = db.Column(db.String(80))
    property_type = db.Column(db.String(10))
    kitchen_available = db.Column(db.Boolean)  # only asked for a 1RK
    kitchen_type = db.Column(db.String(12))  # only when the 1RK has a kitchen

    monthly_rent = db.Column(db.Integer)  # whole rupees
    security_deposit = db.Column(db.Integer)  # whole rupees
    electricity_bill = db.Column(db.String(10))  # included / separate
    water_bill = db.Column(db.String(10))  # included / separate
    maintenance_charge = db.Column(db.Integer)  # whole rupees per month, optional

    floor_number = db.Column(db.SmallInteger)  # 0 is the ground floor
    total_floors = db.Column(db.SmallInteger)
    area_sqft = db.Column(db.Integer)

    address_line = db.Column(db.String(150))  # house or building name or number
    locality = db.Column(db.String(100))
    city = db.Column(db.String(80))
    postal_code = db.Column(db.String(6))
    description = db.Column(db.Text)
    available_from = db.Column(db.Date)

    # Filled in when the map pin is chosen (Phase 9).
    latitude = db.Column(db.Numeric(9, 6))
    longitude = db.Column(db.Numeric(9, 6))

    status = db.Column(db.String(10), nullable=False, default=options.STATUS_DRAFT)
    moderation_status = db.Column(db.String(10), nullable=False, default="approved")
    first_published_at = db.Column(db.DateTime(timezone=True))
    expires_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    owner = db.relationship(
        "User",
        backref=db.backref("properties", cascade="all, delete-orphan", passive_deletes=True),
    )

    __table_args__ = tuple(
        db.CheckConstraint(sql, name=name) for name, sql in options.check_rules().items()
    ) + (db.Index("ix_properties_search", "city", "property_type", "monthly_rent"),)

    @property
    def is_draft(self):
        return self.status == options.STATUS_DRAFT

    @property
    def bedroom_count(self):
        """How many rooms to show photos for (1 for a 1RK, 3 for a 3BHK)."""
        return options.BEDROOMS.get(self.property_type)

    def __repr__(self):
        return f"<Property id={self.id}>"