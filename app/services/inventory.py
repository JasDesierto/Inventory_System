from datetime import datetime

from sqlalchemy import case, desc, func, or_

from ..extensions import db
from ..models import StockTransaction, Supply


class InventoryError(ValueError):
    pass


def _normalize_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _to_int(value, field_name, minimum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise InventoryError(f"{field_name} must be a whole number.") from exc
    if minimum is not None and parsed < minimum:
        comparator = "greater than zero" if minimum == 1 else f"at least {minimum}"
        raise InventoryError(f"{field_name} must be {comparator}.")
    return parsed


def _status_for(quantity, minimum_quantity):
    if quantity <= 0:
        return "out_of_stock"
    if quantity <= minimum_quantity:
        return "low_stock"
    return "in_stock"


def add_new_supply(
    *,
    item_name,
    description,
    category,
    unit,
    quantity,
    minimum_quantity,
    location,
    photo_path,
    remarks,
    created_by,
):
    item_name = _normalize_text(item_name)
    description = _normalize_text(description)
    category = _normalize_text(category)
    unit = _normalize_text(unit)
    location = _normalize_text(location)
    photo_path = _normalize_text(photo_path)
    remarks = _normalize_text(remarks)
    quantity = _to_int(quantity, "Quantity", minimum=1)
    minimum_quantity = _to_int(minimum_quantity or 0, "Minimum quantity", minimum=0)

    if not item_name:
        raise InventoryError("Item name is required.")
    if not description:
        raise InventoryError("Description is required.")
    if not unit:
        raise InventoryError("Unit of measure is required.")
    if not photo_path:
        raise InventoryError("A supply photo is required for stock logging.")

    duplicate = (
        Supply.query.filter(func.lower(Supply.item_name) == item_name.lower())
        .filter(func.lower(Supply.unit) == unit.lower())
        .filter(
            func.lower(func.coalesce(Supply.location, "")) == (location or "").lower()
        )
        .first()
    )
    if duplicate:
        raise InventoryError(
            "A matching supply already exists. Use the restock workflow instead of creating a duplicate item."
        )

    supply = Supply(
        item_name=item_name,
        description=description,
        category=category,
        unit=unit,
        current_quantity=quantity,
        minimum_quantity=minimum_quantity,
        location=location,
        photo_path=photo_path,
        status=_status_for(quantity, minimum_quantity),
        created_by=created_by.id,
    )
    db.session.add(supply)
    db.session.flush()

    transaction = StockTransaction(
        supply_id=supply.id,
        transaction_type="in",
        quantity=quantity,
        previous_quantity=0,
        new_quantity=quantity,
        remarks=remarks or "Initial stock entry",
        performed_by=created_by.id,
    )
    db.session.add(transaction)
    db.session.commit()
    return supply


def restock_supply(*, supply_id, quantity, photo_path, remarks, performed_by):
    quantity = _to_int(quantity, "Restock quantity", minimum=1)
    photo_path = _normalize_text(photo_path)
    remarks = _normalize_text(remarks)

    if not photo_path:
        raise InventoryError("A supply photo is required when logging new stock.")

    supply = Supply.query.get(supply_id)
    if not supply:
        raise InventoryError("The selected supply does not exist.")

    previous_quantity = supply.current_quantity
    new_quantity = previous_quantity + quantity

    supply.current_quantity = new_quantity
    supply.photo_path = photo_path
    supply.status = _status_for(new_quantity, supply.minimum_quantity)

    transaction = StockTransaction(
        supply_id=supply.id,
        transaction_type="in",
        quantity=quantity,
        previous_quantity=previous_quantity,
        new_quantity=new_quantity,
        remarks=remarks or "Restocked",
        performed_by=performed_by.id,
    )
    db.session.add(transaction)
    db.session.commit()
    return supply


def issue_supply(*, supply_id, quantity, remarks, performed_by):
    quantity = _to_int(quantity, "Issue quantity", minimum=1)
    remarks = _normalize_text(remarks)

    supply = Supply.query.get(supply_id)
    if not supply:
        raise InventoryError("The selected supply does not exist.")
    if quantity > supply.current_quantity:
        raise InventoryError("Issue quantity cannot exceed the current stock level.")

    previous_quantity = supply.current_quantity
    new_quantity = previous_quantity - quantity

    supply.current_quantity = new_quantity
    supply.status = _status_for(new_quantity, supply.minimum_quantity)

    transaction = StockTransaction(
        supply_id=supply.id,
        transaction_type="out",
        quantity=quantity,
        previous_quantity=previous_quantity,
        new_quantity=new_quantity,
        remarks=remarks or "Issued from inventory",
        performed_by=performed_by.id,
    )
    db.session.add(transaction)
    db.session.commit()
    return supply


def delete_supply(*, supply_id):
    supply = Supply.query.get(supply_id)
    if not supply:
        raise InventoryError("The selected supply does not exist.")

    deleted_supply = {
        "item_name": supply.item_name,
        "photo_path": supply.photo_path,
    }
    db.session.delete(supply)
    db.session.commit()
    return deleted_supply


def search_supplies(
    *,
    query_text=None,
    category=None,
    location=None,
    low_stock=False,
    out_of_stock=False,
    limit=None,
):
    query = Supply.query
    query_text = _normalize_text(query_text)
    category = _normalize_text(category)
    location = _normalize_text(location)

    if query_text:
        like_value = f"%{query_text}%"
        query = query.filter(
            or_(
                Supply.item_name.ilike(like_value),
                Supply.description.ilike(like_value),
                Supply.category.ilike(like_value),
                Supply.location.ilike(like_value),
            )
        )

    if category:
        query = query.filter(Supply.category == category)
    if location:
        query = query.filter(Supply.location == location)

    low_stock_condition = (Supply.current_quantity > 0) & (
        Supply.current_quantity <= Supply.minimum_quantity
    )
    out_of_stock_condition = Supply.current_quantity == 0

    if low_stock and out_of_stock:
        query = query.filter(or_(low_stock_condition, out_of_stock_condition))
    elif low_stock:
        query = query.filter(low_stock_condition)
    elif out_of_stock:
        query = query.filter(out_of_stock_condition)

    status_rank = case(
        (Supply.current_quantity == 0, 0),
        (Supply.current_quantity <= Supply.minimum_quantity, 1),
        else_=2,
    )

    query = query.order_by(status_rank.asc(), Supply.item_name.asc())
    if limit:
        query = query.limit(limit)
    return query.all()


def get_dashboard_summary(limit_recent=8):
    total_items = db.session.query(func.count(Supply.id)).scalar() or 0
    total_stock_units = db.session.query(func.coalesce(func.sum(Supply.current_quantity), 0)).scalar() or 0
    low_stock_count = (
        db.session.query(func.count(Supply.id))
        .filter(Supply.current_quantity > 0, Supply.current_quantity <= Supply.minimum_quantity)
        .scalar()
        or 0
    )
    out_of_stock_count = (
        db.session.query(func.count(Supply.id))
        .filter(Supply.current_quantity == 0)
        .scalar()
        or 0
    )
    recent_transactions = (
        StockTransaction.query.order_by(StockTransaction.created_at.desc())
        .limit(limit_recent)
        .all()
    )
    return {
        "total_items": total_items,
        "total_stock_units": total_stock_units,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "recent_transactions": recent_transactions,
    }


def get_low_stock_items(limit=10):
    return (
        Supply.query.filter(
            Supply.current_quantity > 0,
            Supply.current_quantity <= Supply.minimum_quantity,
        )
        .order_by(Supply.current_quantity.asc(), Supply.item_name.asc())
        .limit(limit)
        .all()
    )


def get_top_issued_items(limit=5):
    issued_total = func.coalesce(func.sum(StockTransaction.quantity), 0).label("issued_total")
    rows = (
        db.session.query(Supply, issued_total)
        .join(StockTransaction, StockTransaction.supply_id == Supply.id)
        .filter(StockTransaction.transaction_type == "out")
        .group_by(Supply.id)
        .order_by(desc("issued_total"), Supply.item_name.asc())
        .limit(limit)
        .all()
    )
    return [{"supply": supply, "issued_total": total} for supply, total in rows]


def get_recent_stock_movement(limit=12):
    return (
        StockTransaction.query.order_by(StockTransaction.created_at.desc())
        .limit(limit)
        .all()
    )


def get_monthly_stock_out_totals(months=6):
    current = datetime.utcnow()
    month_starts = []
    year = current.year
    month = current.month
    for _ in range(months):
        month_starts.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    month_starts.reverse()

    labels = [f"{year}-{month:02d}" for year, month in month_starts]
    rows = (
        db.session.query(
            func.strftime("%Y-%m", StockTransaction.created_at).label("month_key"),
            func.coalesce(func.sum(StockTransaction.quantity), 0).label("total_quantity"),
        )
        .filter(StockTransaction.transaction_type == "out")
        .group_by("month_key")
        .all()
    )
    row_map = {month_key: total_quantity for month_key, total_quantity in rows}
    return [
        {"label": label, "total": int(row_map.get(label, 0) or 0)}
        for label in labels
    ]
