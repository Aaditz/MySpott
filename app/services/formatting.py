"""Turning numbers into the words people read. Pure Python."""

import re


def format_inr(amount):
    """18500 -> '₹18,500', 125000 -> '₹1,25,000' (Indian digit grouping). None -> ''."""
    if amount is None:
        return ""
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise TypeError("amount must be a whole number of rupees")
    if amount < 0:
        raise ValueError("amount cannot be negative")

    digits = str(amount)
    last_three, rest = digits[-3:], digits[:-3]
    if rest:
        rest = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", rest)
        return f"₹{rest},{last_three}"
    return f"₹{last_three}"


def ordinal(number):
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', 11 -> '11th', 21 -> '21st'."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _floors(count):
    return f"{count} floor" if count == 1 else f"{count} floors"


def describe_floor(floor_number, total_floors):
    """(3, 4) -> '3rd floor out of 4 floors'; (0, 4) -> 'Ground floor out of 4 floors'."""
    if floor_number is None and total_floors is None:
        return ""
    if floor_number is None:
        return f"Building has {_floors(total_floors)}"
    name = "Ground floor" if floor_number == 0 else f"{ordinal(floor_number)} floor"
    if total_floors is None:
        return name
    return f"{name} out of {_floors(total_floors)}"