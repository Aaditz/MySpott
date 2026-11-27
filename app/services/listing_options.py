"""The fixed choices and limits for listings.

One place, used by the database, the forms and the checks, so they can never disagree.
Pure Python: nothing here needs the database or the web framework.
"""

PROPERTY_TYPES = ("1RK", "1BHK", "2BHK", "3BHK")
PROPERTY_TYPE_LABELS = {"1RK": "1 RK", "1BHK": "1 BHK", "2BHK": "2 BHK", "3BHK": "3 BHK"}
# Rooms to ask photos for later (Phase 6).
BEDROOMS = {"1RK": 1, "1BHK": 1, "2BHK": 2, "3BHK": 3}

BILL_OPTIONS = ("included", "separate")
KITCHEN_TYPES = ("integrated", "separate")

STATUS_DRAFT = "draft"
STATUSES = ("draft", "published", "paused", "rented", "removed")
MODERATION_STATUSES = ("approved", "pending", "hidden")

# (smallest, largest). Text lengths count characters, money is whole rupees.
TITLE_LENGTH = (10, 80)
DESCRIPTION_LENGTH = (20, 2000)
ADDRESS_LENGTH = (1, 150)
LOCALITY_LENGTH = (2, 100)
CITY_LENGTH = (2, 80)
RENT_RANGE = (500, 1_000_000)
DEPOSIT_RANGE = (0, 10_000_000)
MAINTENANCE_RANGE = (0, 100_000)
AREA_RANGE = (50, 20_000)  # square feet
FLOOR_RANGE = (0, 100)  # 0 means the ground floor
TOTAL_FLOORS_RANGE = (1, 100)
POSTAL_CODE_PATTERN = r"^[1-9][0-9]{5}$"  # six digits, not starting with 0

# Everything an owner must have filled in before a listing can leave "draft".
REQUIRED_TO_PUBLISH = (
    "title",
    "property_type",
    "monthly_rent",
    "security_deposit",
    "electricity_bill",
    "water_bill",
    "address_line",
    "locality",
    "city",
    "postal_code",
    "description",
    "available_from",
)

# Words for messages such as "Please fill in: monthly rent, PIN code".
FIELD_LABELS = {
    "title": "title",
    "property_type": "home type",
    "kitchen_available": "whether there is a kitchen",
    "kitchen_type": "kitchen type",
    "monthly_rent": "monthly rent",
    "security_deposit": "security deposit",
    "electricity_bill": "electricity bill",
    "water_bill": "water bill",
    "maintenance_charge": "maintenance charges",
    "floor_number": "floor",
    "total_floors": "floors in the building",
    "area_sqft": "area",
    "address_line": "house or building name or number",
    "locality": "locality",
    "city": "city",
    "postal_code": "PIN code",
    "description": "description",
    "available_from": "available-from date",
}


def _quoted(values):
    return ", ".join(f"'{value}'" for value in values)


def check_rules():
    """The database CHECK rules, as {name: SQL}. The Property model builds its table from these.

    Most details may be empty while a listing is a draft; the last rule makes sure a listing
    that is no longer a draft is complete. (If you add a home type, update PROPERTY_TYPES and
    make a new migration so the database learns about it.)
    """
    complete = " AND ".join(f"{name} IS NOT NULL" for name in REQUIRED_TO_PUBLISH)
    return {
        "type_valid": f"property_type IS NULL OR property_type IN ({_quoted(PROPERTY_TYPES)})",
        "status_valid": f"status IN ({_quoted(STATUSES)})",
        "moderation_status_valid": f"moderation_status IN ({_quoted(MODERATION_STATUSES)})",
        "electricity_bill_valid": f"electricity_bill IS NULL OR electricity_bill IN ({_quoted(BILL_OPTIONS)})",
        "water_bill_valid": f"water_bill IS NULL OR water_bill IN ({_quoted(BILL_OPTIONS)})",
        "kitchen_type_valid": f"kitchen_type IS NULL OR kitchen_type IN ({_quoted(KITCHEN_TYPES)})",
        "title_length": f"title IS NULL OR char_length(title) BETWEEN {TITLE_LENGTH[0]} AND {TITLE_LENGTH[1]}",
        "description_length": (
            f"description IS NULL OR char_length(description) BETWEEN "
            f"{DESCRIPTION_LENGTH[0]} AND {DESCRIPTION_LENGTH[1]}"
        ),
        "rent_range": f"monthly_rent IS NULL OR monthly_rent BETWEEN {RENT_RANGE[0]} AND {RENT_RANGE[1]}",
        "deposit_range": (
            f"security_deposit IS NULL OR security_deposit BETWEEN {DEPOSIT_RANGE[0]} AND {DEPOSIT_RANGE[1]}"
        ),
        "maintenance_range": (
            f"maintenance_charge IS NULL OR maintenance_charge BETWEEN "
            f"{MAINTENANCE_RANGE[0]} AND {MAINTENANCE_RANGE[1]}"
        ),
        "area_range": f"area_sqft IS NULL OR area_sqft BETWEEN {AREA_RANGE[0]} AND {AREA_RANGE[1]}",
        "floor_range": f"floor_number IS NULL OR floor_number BETWEEN {FLOOR_RANGE[0]} AND {FLOOR_RANGE[1]}",
        "total_floors_range": (
            f"total_floors IS NULL OR total_floors BETWEEN {TOTAL_FLOORS_RANGE[0]} AND {TOTAL_FLOORS_RANGE[1]}"
        ),
        "floor_within_building": "floor_number IS NULL OR total_floors IS NULL OR floor_number <= total_floors",
        "postal_code_format": f"postal_code IS NULL OR postal_code ~ '{POSTAL_CODE_PATTERN}'",
        "latitude_range": "latitude IS NULL OR latitude BETWEEN -90 AND 90",
        "longitude_range": "longitude IS NULL OR longitude BETWEEN -180 AND 180",
        # Kitchen questions only exist for a 1RK, and a kitchen type only for a kitchen that exists.
        "kitchen_only_for_1rk": (
            "COALESCE(property_type, '') = '1RK' OR (kitchen_available IS NULL AND kitchen_type IS NULL)"
        ),
        "kitchen_type_needs_kitchen": "kitchen_type IS NULL OR kitchen_available IS TRUE",
        "non_drafts_are_complete": (
            f"status = 'draft' OR ({complete} "
            "AND (property_type <> '1RK' OR kitchen_available IS NOT NULL) "
            "AND (kitchen_available IS NOT TRUE OR kitchen_type IS NOT NULL))"
        ),
    }