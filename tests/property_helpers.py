"""Helpers for tests that need listings."""

from datetime import date, timedelta

from app.models import Property


def complete_values(**overrides):
    """Every required detail of a valid listing. Tests override only what they care about."""
    values = {
        "title": "Spacious 1BHK near the metro",
        "property_type": "1BHK",
        "monthly_rent": 18500,
        "security_deposit": 55500,
        "electricity_bill": "separate",
        "water_bill": "included",
        "address_line": "Flat 4B, Lotus Residency",
        "locality": "Kothanur",
        "city": "Bengaluru",
        "postal_code": "560077",
        "description": "A bright, well-ventilated flat close to shops and public transport.",
        "available_from": date.today() + timedelta(days=14),
    }
    values.update(overrides)
    return values


def make_property(owner, **overrides):
    """An unsaved Property belonging to `owner`, complete unless a test says otherwise."""
    return Property(owner_id=owner.id, **complete_values(**overrides))