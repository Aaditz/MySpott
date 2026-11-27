"""Checks for the details an owner types into a listing. Pure Python, no database.

Everything arrives as text from a form (or as numbers from an app). A blank value means "not
filled in yet", which is fine for a draft. A value that is filled in but wrong gets a friendly
message. Whether a listing is complete enough to publish is a separate question:
see missing_for_publish().
"""

import re
from datetime import date, datetime, timedelta

from app.services import listing_options as options
from app.services.formatting import format_inr

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_RUPEE_PREFIX = re.compile(r"^(?:₹|rs\.?|inr)\s*", re.IGNORECASE)


def _blank(raw):
    return raw is None or (isinstance(raw, str) and raw.strip() == "")


def _characters_error(label, bounds):
    low, high = bounds
    return f"{label.capitalize()} must be {low} to {high} characters long."


# ------------------------------------------------------------------------ text

def clean_text(raw, label, bounds, single_line=True):
    """Tidy a piece of text and check its length. Returns (value, error)."""
    if _blank(raw):
        return None, None
    if not isinstance(raw, str):
        return None, f"Please enter the {label} as text."

    if single_line:
        text = " ".join(raw.split())  # one line, single spaces
    else:
        text = raw.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if _CONTROL_CHARACTERS.search(text):
        return None, f"The {label} contains characters that are not allowed."
    low, high = bounds
    if not low <= len(text) <= high:
        return None, _characters_error(label, bounds)
    return text, None


# --------------------------------------------------------------------- choices

def clean_choice(raw, label, allowed):
    """Accept one of the allowed words (any capitals). Returns (canonical value, error)."""
    if _blank(raw):
        return None, None
    text = str(raw).strip()
    for option in allowed:
        if text.lower() == option.lower():
            return option, None
    return None, f"Please choose the {label} from the list."


def clean_yes_no(raw, label):
    if isinstance(raw, bool):
        return raw, None
    if _blank(raw):
        return None, None
    text = str(raw).strip().lower()
    if text in ("yes", "true", "1", "y"):
        return True, None
    if text in ("no", "false", "0", "n"):
        return False, None
    return None, f"Please answer yes or no for {label}."


# --------------------------------------------------------------------- numbers

def _out_of_range(label, bounds, money):
    low, high = bounds
    if money:
        return f"{label.capitalize()} must be between {format_inr(low)} and {format_inr(high)}."
    return f"{label.capitalize()} must be between {low} and {high}."


def clean_rupees(raw, label, bounds):
    """'18,500', '₹18,500', 'Rs. 18500' or 18500 -> 18500. Returns (value, error)."""
    if _blank(raw):
        return None, None
    if isinstance(raw, bool):
        return None, f"Please enter {label} as a whole number of rupees."
    if isinstance(raw, int):
        value = raw
    else:
        text = _RUPEE_PREFIX.sub("", str(raw).strip())
        text = re.sub(r"/-$", "", text)
        text = text.replace(",", "").replace(" ", "")
        if "." in text:
            return None, f"Please enter {label} as a whole number of rupees, without decimals."
        if not (text.isascii() and text.isdigit()):
            return None, f"Please enter {label} as a whole number of rupees, for example 18500."
        value = int(text)

    if not bounds[0] <= value <= bounds[1]:
        return None, _out_of_range(label, bounds, money=True)
    return value, None


def clean_whole_number(raw, label, bounds):
    """'3' or 3 -> 3, for floors and area. Returns (value, error)."""
    if _blank(raw):
        return None, None
    if isinstance(raw, bool):
        return None, f"Please enter {label} as a whole number."
    if isinstance(raw, int):
        value = raw
    else:
        text = str(raw).strip()
        if not (text.isascii() and text.isdigit()):
            return None, f"Please enter {label} as a whole number."
        value = int(text)
    if not bounds[0] <= value <= bounds[1]:
        return None, _out_of_range(label, bounds, money=False)
    return value, None


def clean_postal_code(raw):
    if _blank(raw):
        return None, None
    text = str(raw).replace(" ", "")
    if not re.match(options.POSTAL_CODE_PATTERN, text):
        return None, "Please enter a 6-digit PIN code that does not start with 0."
    return text, None


def clean_date(raw, today=None):
    """'2026-12-01' or a date -> date, allowed from 30 days ago to one year ahead."""
    if _blank(raw):
        return None, None
    today = today or date.today()
    if isinstance(raw, datetime):
        value = raw.date()
    elif isinstance(raw, date):
        value = raw
    else:
        try:
            value = datetime.strptime(str(raw).strip(), "%Y-%m-%d").date()
        except ValueError:
            return None, "Please enter a valid available-from date."
    if not today - timedelta(days=30) <= value <= today + timedelta(days=365):
        return None, "The available-from date must be within the last 30 days or the next year."
    return value, None


# ------------------------------------------------------------------ whole form

def clean_listing_fields(raw, today=None):
    """Check everything an owner typed. Returns (cleaned values, errors).

    `cleaned` always has every field (None when it was left blank or was wrong).
    `errors` maps a field name to a friendly message, and is empty when nothing is wrong.
    """
    cleaned, errors = {}, {}

    def take(field, result):
        value, error = result
        cleaned[field] = value
        if error:
            errors[field] = error

    take("title", clean_text(raw.get("title"), "title", options.TITLE_LENGTH))
    take("property_type", clean_choice(raw.get("property_type"), "home type", options.PROPERTY_TYPES))
    take("kitchen_available", clean_yes_no(raw.get("kitchen_available"), "the kitchen"))
    take("kitchen_type", clean_choice(raw.get("kitchen_type"), "kitchen type", options.KITCHEN_TYPES))
    take("monthly_rent", clean_rupees(raw.get("monthly_rent"), "monthly rent", options.RENT_RANGE))
    take("security_deposit", clean_rupees(raw.get("security_deposit"), "security deposit", options.DEPOSIT_RANGE))
    take("electricity_bill", clean_choice(raw.get("electricity_bill"), "electricity bill option", options.BILL_OPTIONS))
    take("water_bill", clean_choice(raw.get("water_bill"), "water bill option", options.BILL_OPTIONS))
    take("maintenance_charge", clean_rupees(raw.get("maintenance_charge"), "maintenance charges", options.MAINTENANCE_RANGE))
    take("floor_number", clean_whole_number(raw.get("floor_number"), "the floor", options.FLOOR_RANGE))
    take("total_floors", clean_whole_number(raw.get("total_floors"), "the number of floors", options.TOTAL_FLOORS_RANGE))
    take("area_sqft", clean_whole_number(raw.get("area_sqft"), "the area", options.AREA_RANGE))
    take("address_line", clean_text(raw.get("address_line"), "house or building name or number", options.ADDRESS_LENGTH))
    take("locality", clean_text(raw.get("locality"), "locality", options.LOCALITY_LENGTH))
    take("city", clean_text(raw.get("city"), "city", options.CITY_LENGTH))
    take("postal_code", clean_postal_code(raw.get("postal_code")))
    take("description", clean_text(raw.get("description"), "description", options.DESCRIPTION_LENGTH, single_line=False))
    take("available_from", clean_date(raw.get("available_from"), today))

    # Kitchen answers only exist for a 1RK.
    if cleaned["property_type"] != "1RK":
        cleaned["kitchen_available"] = None
        cleaned["kitchen_type"] = None
        errors.pop("kitchen_available", None)
        errors.pop("kitchen_type", None)
    elif cleaned["kitchen_available"] is False:
        cleaned["kitchen_type"] = None  # no kitchen, so no kitchen type
        errors.pop("kitchen_type", None)
    elif cleaned["kitchen_available"] is None and cleaned["kitchen_type"] is not None:
        errors["kitchen_available"] = "Please say whether there is a kitchen before choosing its type."

    floor, total = cleaned["floor_number"], cleaned["total_floors"]
    if floor is not None and total is not None and floor > total:
        errors["floor_number"] = "The floor cannot be higher than the number of floors in the building."

    return cleaned, errors


def missing_for_publish(values):
    """Names of the details still missing before this listing can be published.

    `values` can be a dictionary or a Property. An empty list means it is complete.
    """
    get = values.get if isinstance(values, dict) else (lambda name: getattr(values, name, None))

    def empty(name):
        value = get(name)
        return value is None or (isinstance(value, str) and value.strip() == "")

    missing = [name for name in options.REQUIRED_TO_PUBLISH if empty(name)]
    if get("property_type") == "1RK":
        if get("kitchen_available") is None:
            missing.append("kitchen_available")
        elif get("kitchen_available") is True and empty("kitchen_type"):
            missing.append("kitchen_type")
    return missing