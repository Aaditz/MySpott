"""Tests that the listing choices and the database rules agree with each other."""

from app.services import listing_options as options


def test_every_home_type_has_a_label_and_a_room_count():
    assert set(options.PROPERTY_TYPE_LABELS) == set(options.PROPERTY_TYPES)
    assert set(options.BEDROOMS) == set(options.PROPERTY_TYPES)
    assert options.PROPERTY_TYPES == ("1RK", "1BHK", "2BHK", "3BHK")


def test_every_required_detail_has_words_for_messages():
    for name in options.REQUIRED_TO_PUBLISH:
        assert name in options.FIELD_LABELS, name


def test_the_database_rules_mention_every_choice():
    rules = options.check_rules()

    for value in options.PROPERTY_TYPES:
        assert f"'{value}'" in rules["type_valid"], value
    for value in options.STATUSES:
        assert f"'{value}'" in rules["status_valid"], value
    for value in options.BILL_OPTIONS:
        assert f"'{value}'" in rules["electricity_bill_valid"], value
        assert f"'{value}'" in rules["water_bill_valid"], value
    for value in options.KITCHEN_TYPES:
        assert f"'{value}'" in rules["kitchen_type_valid"], value


def test_a_listing_that_is_not_a_draft_must_have_every_required_detail():
    rule = options.check_rules()["non_drafts_are_complete"]

    for name in options.REQUIRED_TO_PUBLISH:
        assert f"{name} IS NOT NULL" in rule, name


def test_the_limits_in_the_rules_match_the_limits_in_the_options():
    rules = options.check_rules()

    assert f"BETWEEN {options.RENT_RANGE[0]} AND {options.RENT_RANGE[1]}" in rules["rent_range"]
    assert f"BETWEEN {options.TITLE_LENGTH[0]} AND {options.TITLE_LENGTH[1]}" in rules["title_length"]
    assert options.POSTAL_CODE_PATTERN in rules["postal_code_format"]