"""Tests for rupee amounts and floor descriptions (no database needed)."""

from app.services.formatting import describe_floor, format_inr, ordinal


def test_rupees_use_indian_digit_grouping():
    expected = {
        0: "₹0",
        5: "₹5",
        999: "₹999",
        1000: "₹1,000",
        18500: "₹18,500",
        99999: "₹99,999",
        100000: "₹1,00,000",
        125000: "₹1,25,000",
        1000000: "₹10,00,000",
        10000000: "₹1,00,00,000",
    }
    for amount, text in expected.items():
        assert format_inr(amount) == text, amount


def test_a_missing_amount_shows_nothing():
    assert format_inr(None) == ""


def test_amounts_that_make_no_sense_are_refused():
    for bad in [True, 18.5, "18500", -1]:
        try:
            format_inr(bad)
        except (TypeError, ValueError):
            continue
        raise AssertionError(f"{bad!r} should have been refused")


def test_ordinal_numbers():
    expected = {
        1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 10: "10th", 11: "11th", 12: "12th", 13: "13th",
        21: "21st", 22: "22nd", 23: "23rd", 101: "101st", 111: "111th", 112: "112th",
    }
    for number, text in expected.items():
        assert ordinal(number) == text, number


def test_floors_are_described_in_words():
    assert describe_floor(3, 4) == "3rd floor out of 4 floors"
    assert describe_floor(0, 4) == "Ground floor out of 4 floors"
    assert describe_floor(0, 1) == "Ground floor out of 1 floor"
    assert describe_floor(2, None) == "2nd floor"
    assert describe_floor(0, None) == "Ground floor"
    assert describe_floor(None, 5) == "Building has 5 floors"
    assert describe_floor(None, 1) == "Building has 1 floor"
    assert describe_floor(None, None) == ""