from .inventory import (
    InventoryError,
    add_new_supply,
    delete_supply,
    get_dashboard_summary,
    get_low_stock_items,
    get_monthly_stock_out_totals,
    get_recent_stock_movement,
    get_top_issued_items,
    issue_supply,
    restock_supply,
    search_supplies,
)

# Re-export the inventory service helpers so route modules can import from
# `app.services` without coupling to the file layout.
__all__ = [
    "InventoryError",
    "add_new_supply",
    "delete_supply",
    "restock_supply",
    "issue_supply",
    "search_supplies",
    "get_dashboard_summary",
    "get_low_stock_items",
    "get_top_issued_items",
    "get_recent_stock_movement",
    "get_monthly_stock_out_totals",
]
