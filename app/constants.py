SUPPLY_CATEGORIES = (
    "Paper Products",
    "Writing Instruments",
    "Filing and Organization",
    "Desktop Supplies",
    "Adhesives and Tapes",
    "Mailing and Shipping",
    "Printing Supplies",
    "Notebooks and Forms",
    "Office Accessories",
    "Computer and Office Accessories",
    "Pantry and Janitorial Supplies",
    "Storage Supplies",
    "Tokens / Controlled Items",
    "Others",
)

LEGACY_CATEGORY_ALIASES = {
    "Presentation Supplies": "Office Accessories",
}


def normalize_supply_category(category):
    normalized = str(category or "").strip()
    if not normalized:
        return None
    return LEGACY_CATEGORY_ALIASES.get(normalized, normalized)


def display_supply_category(category):
    normalized = normalize_supply_category(category)
    return normalized or "Others"
