"""Tests for the Property model and its database rules (real PostgreSQL test database)."""

import time

from sqlalchemy.exc import DataError, IntegrityError

from app.extensions import db
from app.models import Property
from app.services import listing_options as options
from tests.property_helpers import make_property


def save_owner(user_factory, **overrides):
    owner = user_factory(role="owner", **overrides)
    db.session.add(owner)
    db.session.commit()
    return owner


def refused(property_):
    """True if the database refuses to save this listing (a broken rule or a value too long)."""
    db.session.add(property_)
    try:
        db.session.commit()
    except (DataError, IntegrityError):
        db.session.rollback()
        return True
    return False

def test_a_bare_draft_can_be_saved_with_sensible_defaults(app, user_factory):
    owner = save_owner(user_factory)
    listing = Property(owner_id=owner.id)

    db.session.add(listing)
    db.session.commit()

    assert listing.id is not None
    assert listing.status == "draft"
    assert listing.is_draft is True
    assert listing.moderation_status == "approved"
    assert listing.created_at is not None
    assert listing.first_published_at is None
    assert listing.monthly_rent is None


def test_a_partly_filled_draft_can_be_saved(app, user_factory):
    owner = save_owner(user_factory)

    assert not refused(Property(owner_id=owner.id, title="A half written listing", monthly_rent=15000))


def test_a_complete_listing_can_be_published(app, user_factory):
    owner = save_owner(user_factory)

    assert not refused(make_property(owner, status="published"))


def test_a_listing_that_is_not_a_draft_must_have_every_required_detail(app, user_factory):
    owner = save_owner(user_factory)

    for field in options.REQUIRED_TO_PUBLISH:
        assert refused(make_property(owner, status="published", **{field: None})), field


def test_wrong_values_are_refused_by_the_database(app, user_factory):
    owner = save_owner(user_factory)
    bad_values = [
        {"property_type": "villa"},
        {"monthly_rent": 499},
        {"monthly_rent": 1_000_001},
        {"security_deposit": -1},
        {"maintenance_charge": -1},
        {"area_sqft": 49},
        {"floor_number": -1},
        {"total_floors": 0},
        {"postal_code": "012345"},
        {"postal_code": "12345"},
        {"postal_code": "ABCDEF"},
        {"title": "Too short"},
        {"title": "x" * 81},
        {"description": "x" * 19},
        {"description": "x" * 2001},
        {"electricity_bill": "maybe"},
        {"water_bill": "maybe"},
        {"status": "bogus"},
        {"moderation_status": "bogus"},
        {"latitude": 91},
        {"longitude": 181},
    ]

    for overrides in bad_values:
        assert refused(make_property(owner, **overrides)), overrides


def test_values_at_the_edges_of_the_limits_are_accepted(app, user_factory):
    owner = save_owner(user_factory)
    good_values = [
        {"monthly_rent": 500},
        {"monthly_rent": 1_000_000},
        {"security_deposit": 0},
        {"maintenance_charge": 0},
        {"area_sqft": 50},
        {"area_sqft": 20_000},
        {"title": "x" * 10},
        {"title": "x" * 80},
        {"description": "x" * 20},
        {"description": "x" * 2000},
        {"postal_code": "100001"},
        {"floor_number": 0, "total_floors": 1},
        {"latitude": -90, "longitude": -180},
        {"latitude": 90, "longitude": 180},
    ]

    for overrides in good_values:
        assert not refused(make_property(owner, **overrides)), overrides


def test_the_floor_cannot_be_above_the_top_floor(app, user_factory):
    owner = save_owner(user_factory)

    assert refused(make_property(owner, floor_number=5, total_floors=4))
    assert not refused(make_property(owner, floor_number=4, total_floors=4))


def test_kitchen_answers_follow_the_1rk_rules(app, user_factory):
    owner = save_owner(user_factory)

    # Only a 1RK has kitchen answers.
    assert refused(make_property(owner, property_type="2BHK", kitchen_available=True))
    assert refused(Property(owner_id=owner.id, kitchen_available=True))  # no type chosen yet
    # A kitchen type needs a kitchen.
    assert refused(make_property(owner, property_type="1RK", kitchen_available=False, kitchen_type="integrated"))
    assert refused(make_property(owner, property_type="1RK", kitchen_type="integrated"))
    # A published 1RK needs the answers.
    assert refused(make_property(owner, property_type="1RK", status="published"))
    assert refused(make_property(owner, property_type="1RK", status="published", kitchen_available=True))
    # Valid combinations.
    assert not refused(
        make_property(owner, property_type="1RK", status="published", kitchen_available=True, kitchen_type="integrated")
    )
    assert not refused(make_property(owner, property_type="1RK", status="published", kitchen_available=False))
    assert not refused(make_property(owner, property_type="1RK", kitchen_available=True))  # draft: type may come later


def test_deleting_an_owner_deletes_their_listings(app, user_factory):
    owner = save_owner(user_factory)
    db.session.add_all([make_property(owner), make_property(owner, title="Another lovely home here")])
    db.session.commit()

    db.session.delete(owner)
    db.session.commit()

    assert db.session.scalar(db.select(db.func.count(Property.id))) == 0


def test_an_owner_can_list_their_own_listings(app, user_factory):
    owner = save_owner(user_factory)
    other = save_owner(user_factory, email="grace@example.com", name="Grace Hopper")
    db.session.add_all([make_property(owner), make_property(owner), make_property(other)])
    db.session.commit()

    assert len(owner.properties) == 2
    assert len(other.properties) == 1
    assert all(item.owner is owner for item in owner.properties)


def test_the_room_count_follows_the_home_type():
    expected = {"1RK": 1, "1BHK": 1, "2BHK": 2, "3BHK": 3}

    for home_type, rooms in expected.items():
        assert Property(property_type=home_type).bedroom_count == rooms
    assert Property().bedroom_count is None


def test_updated_at_changes_when_a_listing_is_edited(app, user_factory):
    owner = save_owner(user_factory)
    listing = make_property(owner)
    db.session.add(listing)
    db.session.commit()
    first = listing.updated_at

    time.sleep(0.05)
    listing.monthly_rent = 19000
    db.session.commit()

    assert listing.updated_at > first