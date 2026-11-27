"""Tests for checking what an owner types into a listing (no database needed)."""

from datetime import date
from types import SimpleNamespace

from app.services import listing_options as options
from app.services import listing_validation as v

TODAY = date(2026, 11, 26)


def complete_form(**overrides):
    values = {
        "title": "Spacious 1BHK near the metro",
        "property_type": "1BHK",
        "monthly_rent": "18,500",
        "security_deposit": "₹55,500",
        "electricity_bill": "separate",
        "water_bill": "included",
        "address_line": "Flat 4B, Lotus Residency",
        "locality": "Kothanur",
        "city": "Bengaluru",
        "postal_code": "560 077",
        "description": "A bright, well-ventilated flat close to shops and public transport.",
        "available_from": "2026-12-15",
    }
    values.update(overrides)
    return values


# ------------------------------------------------------------------------ text

def test_blank_values_mean_not_filled_in_yet_and_are_not_errors():
    cleaned, errors = v.clean_listing_fields({}, today=TODAY)

    assert errors == {}
    assert all(value is None for value in cleaned.values())
    assert set(cleaned) == set(options.FIELD_LABELS)


def test_titles_are_tidied_and_length_checked():
    assert v.clean_text("  Spacious   1BHK \n near  metro ", "title", options.TITLE_LENGTH) == (
        "Spacious 1BHK near metro", None,
    )
    assert v.clean_text("x" * 80, "title", options.TITLE_LENGTH)[1] is None
    for bad in ["Too short", "x" * 81]:
        assert "10 to 80 characters" in v.clean_text(bad, "title", options.TITLE_LENGTH)[1], bad


def test_control_characters_are_refused():
    assert "not allowed" in v.clean_text("Nice flat\x00here", "title", options.TITLE_LENGTH)[1]


def test_descriptions_keep_paragraphs_but_tidy_line_endings_and_gaps():
    raw = "First paragraph here, long enough.\r\n\r\n\r\n\r\nSecond paragraph.\t\tDone.  "

    value, error = v.clean_text(raw, "description", options.DESCRIPTION_LENGTH, single_line=False)

    assert error is None
    assert value == "First paragraph here, long enough.\n\nSecond paragraph.  Done."


def test_description_length_limits():
    for bad in ["x" * 19, "x" * 2001]:
        assert "20 to 2000" in v.clean_text(bad, "description", options.DESCRIPTION_LENGTH, single_line=False)[1]
    assert v.clean_text("x" * 20, "description", options.DESCRIPTION_LENGTH, single_line=False)[1] is None
    assert v.clean_text("x" * 2000, "description", options.DESCRIPTION_LENGTH, single_line=False)[1] is None


# ----------------------------------------------------------------------- money

def test_rupee_amounts_are_understood_in_many_spellings():
    for text in ["18500", "18,500", "₹18,500", "₹ 18,500", "Rs. 18500", "rs18500", "INR 18,500", "18500/-", " 18 500 "]:
        assert v.clean_rupees(text, "monthly rent", options.RENT_RANGE) == (18500, None), text
    assert v.clean_rupees(18500, "monthly rent", options.RENT_RANGE) == (18500, None)
    assert v.clean_rupees("₹1,25,000", "monthly rent", options.RENT_RANGE) == (125000, None)


def test_rupee_amounts_that_are_not_whole_numbers_are_refused():
    for bad in ["18500.50", "18,500.00", "abc", "-500", "1e5", "٣٠٠٠٠", True, "₹"]:
        value, error = v.clean_rupees(bad, "monthly rent", options.RENT_RANGE)
        assert value is None and error, repr(bad)


def test_rent_must_be_in_the_allowed_range_and_the_message_says_so():
    for bad in [499, 1_000_001, "10,00,001"]:
        value, error = v.clean_rupees(bad, "monthly rent", options.RENT_RANGE)
        assert value is None
        assert "₹500" in error and "₹10,00,000" in error, bad
    assert v.clean_rupees(500, "monthly rent", options.RENT_RANGE)[1] is None
    assert v.clean_rupees(1_000_000, "monthly rent", options.RENT_RANGE)[1] is None


def test_deposit_and_maintenance_may_be_zero_but_have_an_upper_limit():
    assert v.clean_rupees("0", "security deposit", options.DEPOSIT_RANGE) == (0, None)
    assert v.clean_rupees(0, "maintenance charges", options.MAINTENANCE_RANGE) == (0, None)
    assert v.clean_rupees(10_000_001, "security deposit", options.DEPOSIT_RANGE)[1]
    assert v.clean_rupees(100_001, "maintenance charges", options.MAINTENANCE_RANGE)[1]


# --------------------------------------------------------------------- choices

def test_choices_ignore_capitals_and_refuse_unknown_words():
    assert v.clean_choice("1bhk", "home type", options.PROPERTY_TYPES) == ("1BHK", None)
    assert v.clean_choice(" Included ", "bill", options.BILL_OPTIONS) == ("included", None)
    for bad in ["villa", "4BHK", "maybe"]:
        value, error = v.clean_choice(bad, "choice", options.PROPERTY_TYPES)
        assert value is None and error, bad


def test_yes_no_answers():
    for yes in ["yes", "Yes", "true", "1", True]:
        assert v.clean_yes_no(yes, "the kitchen") == (True, None), yes
    for no in ["no", "No", "false", "0", False]:
        assert v.clean_yes_no(no, "the kitchen") == (False, None), no
    assert v.clean_yes_no("", "the kitchen") == (None, None)
    assert v.clean_yes_no("perhaps", "the kitchen")[1]


# --------------------------------------------------------------- other details

def test_pin_codes_are_six_digits_not_starting_with_zero():
    assert v.clean_postal_code("560 077") == ("560077", None)
    assert v.clean_postal_code("100001") == ("100001", None)
    for bad in ["012345", "12345", "5600770", "ABCDEF", "56 00"]:
        value, error = v.clean_postal_code(bad)
        assert value is None and error, bad


def test_the_available_date_must_be_sensible():
    assert v.clean_date("2026-12-15", TODAY) == (date(2026, 12, 15), None)
    assert v.clean_date(date(2026, 11, 26), TODAY) == (date(2026, 11, 26), None)
    assert v.clean_date("2026-10-27", TODAY)[1] is None  # 30 days ago is fine
    assert v.clean_date("2027-11-26", TODAY)[1] is None  # one year ahead is fine
    for bad in ["2026-13-45", "tomorrow", "26-11-2026", "2026-10-26", "2027-11-27"]:
        value, error = v.clean_date(bad, TODAY)
        assert value is None and error, bad


def test_floors_and_area_are_whole_numbers_in_range():
    assert v.clean_whole_number("3", "the floor", options.FLOOR_RANGE) == (3, None)
    assert v.clean_whole_number("0", "the floor", options.FLOOR_RANGE) == (0, None)
    for bad in ["-1", "101", "abc", "2.5", True]:
        assert v.clean_whole_number(bad, "the floor", options.FLOOR_RANGE)[1], repr(bad)
    assert v.clean_whole_number("49", "the area", options.AREA_RANGE)[1]
    assert v.clean_whole_number("20001", "the area", options.AREA_RANGE)[1]
    assert v.clean_whole_number("1200", "the area", options.AREA_RANGE) == (1200, None)
    assert v.clean_whole_number("0", "the number of floors", options.TOTAL_FLOORS_RANGE)[1]


# ------------------------------------------------------------------- whole form

def test_a_complete_form_is_accepted_and_turned_into_proper_values():
    cleaned, errors = v.clean_listing_fields(complete_form(), today=TODAY)

    assert errors == {}
    assert cleaned["monthly_rent"] == 18500
    assert cleaned["security_deposit"] == 55500
    assert cleaned["postal_code"] == "560077"
    assert cleaned["available_from"] == date(2026, 12, 15)
    assert cleaned["electricity_bill"] == "separate"
    assert cleaned["kitchen_available"] is None


def test_every_mistake_is_reported_at_once():
    cleaned, errors = v.clean_listing_fields(
        complete_form(title="Hi", monthly_rent="cheap", postal_code="1", available_from="soon"),
        today=TODAY,
    )

    assert set(errors) == {"title", "monthly_rent", "postal_code", "available_from"}
    assert cleaned["title"] is None and cleaned["monthly_rent"] is None
    assert cleaned["city"] == "Bengaluru"  # the good parts are kept


def test_kitchen_questions_only_apply_to_a_1rk():
    other, errors = v.clean_listing_fields(
        complete_form(property_type="2BHK", kitchen_available="yes", kitchen_type="separate"), today=TODAY
    )
    assert errors == {}
    assert other["kitchen_available"] is None and other["kitchen_type"] is None

    with_kitchen, errors = v.clean_listing_fields(
        complete_form(property_type="1RK", kitchen_available="yes", kitchen_type="integrated"), today=TODAY
    )
    assert errors == {}
    assert with_kitchen["kitchen_available"] is True and with_kitchen["kitchen_type"] == "integrated"

    no_kitchen, errors = v.clean_listing_fields(
        complete_form(property_type="1RK", kitchen_available="no", kitchen_type="separate"), today=TODAY
    )
    assert errors == {}
    assert no_kitchen["kitchen_available"] is False and no_kitchen["kitchen_type"] is None

    _, errors = v.clean_listing_fields(
        complete_form(property_type="1RK", kitchen_type="separate"), today=TODAY
    )
    assert "kitchen_available" in errors


def test_the_floor_cannot_be_above_the_top_floor():
    _, errors = v.clean_listing_fields(complete_form(floor_number="5", total_floors="4"), today=TODAY)
    assert "floor_number" in errors

    cleaned, errors = v.clean_listing_fields(complete_form(floor_number="3", total_floors="4"), today=TODAY)
    assert errors == {} and (cleaned["floor_number"], cleaned["total_floors"]) == (3, 4)

    cleaned, errors = v.clean_listing_fields(complete_form(floor_number="0", total_floors="1"), today=TODAY)
    assert errors == {}


# ------------------------------------------------------------------- publishing

def test_a_complete_listing_has_nothing_missing():
    cleaned, errors = v.clean_listing_fields(complete_form(), today=TODAY)

    assert errors == {}
    assert v.missing_for_publish(cleaned) == []


def test_an_empty_listing_is_missing_every_required_detail():
    assert v.missing_for_publish({}) == list(options.REQUIRED_TO_PUBLISH)


def test_blank_text_counts_as_missing():
    cleaned, _ = v.clean_listing_fields(complete_form(), today=TODAY)
    cleaned["city"] = "   "

    assert v.missing_for_publish(cleaned) == ["city"]


def test_a_1rk_needs_its_kitchen_answers_before_publishing():
    base = v.clean_listing_fields(complete_form(property_type="1RK"), today=TODAY)[0]

    assert v.missing_for_publish(base) == ["kitchen_available"]
    assert v.missing_for_publish({**base, "kitchen_available": True}) == ["kitchen_type"]
    assert v.missing_for_publish({**base, "kitchen_available": True, "kitchen_type": "separate"}) == []
    assert v.missing_for_publish({**base, "kitchen_available": False}) == []


def test_missing_details_can_be_read_from_a_property_like_object():
    listing = SimpleNamespace(**{name: "x" for name in options.REQUIRED_TO_PUBLISH})
    listing.property_type = "2BHK"
    assert v.missing_for_publish(listing) == []

    listing.monthly_rent = None
    assert v.missing_for_publish(listing) == ["monthly_rent"]