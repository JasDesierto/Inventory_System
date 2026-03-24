SUPPLY_CATEGORIES = (
    "Paper Products",
    "Writing Instruments",
    "Filing and Organization",
    "Desktop Supplies",
    "Adhesives and Tapes",
    "Mailing and Shipping",
    "Printing Supplies",
    "Notebooks and Forms",
    "Presentation Supplies",
    "Computer and Office Accessories",
    "Pantry and Janitorial Supplies",
    "Storage Supplies",
    "Tokens / Controlled Items",
    "Others",
)


def display_supply_category(category):
    normalized = str(category or "").strip()
    return normalized or "Others"
