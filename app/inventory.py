from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from .decorators import role_required
from .extensions import db
from .models import StockTransaction, Supply
from .services import (
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
from .utils.uploads import (
    UploadError,
    delete_uploaded_image,
    photo_url_for,
    save_form_image,
    save_uploaded_image,
)

inventory_bp = Blueprint("inventory", __name__)


def _photo_url(photo_path):
    return photo_url_for(photo_path)


def _status_tone(status):
    return {
        "in_stock": "success",
        "low_stock": "warning",
        "out_of_stock": "danger",
    }.get(status, "neutral")


def _supply_payload(supply):
    # The frontend only gets the values it needs, plus a resolved photo URL that respects access control.
    return {
        "id": supply.id,
        "item_name": supply.item_name,
        "description": supply.description,
        "category": supply.category or "Uncategorized",
        "unit": supply.unit,
        "current_quantity": supply.current_quantity,
        "minimum_quantity": supply.minimum_quantity,
        "location": supply.location or "Unassigned",
        "photo_path": supply.photo_path,
        "photo_url": _photo_url(supply.photo_path),
        "status": supply.status,
        "status_label": supply.status_label,
        "status_tone": _status_tone(supply.status),
        "is_low_stock": supply.is_low_stock,
        "created_at": supply.created_at.strftime("%Y-%m-%d %H:%M"),
        "updated_at": supply.updated_at.strftime("%Y-%m-%d %H:%M"),
        "detail_url": url_for("inventory.supply_detail", supply_id=supply.id),
        "restock_url": url_for("inventory.restock_supply_view", supply_id=supply.id),
        "issue_url": url_for("inventory.issue_supply_view", supply_id=supply.id),
        "delete_url": (
            url_for("inventory.delete_supply_view", supply_id=supply.id)
            if current_user.is_authenticated and current_user.is_admin
            else None
        ),
    }


def _distinct_values(column):
    return [
        value
        for (value,) in db.session.query(column)
        .filter(column.isnot(None), column != "")
        .distinct()
        .order_by(column.asc())
        .all()
    ]


@inventory_bp.route("/uploads/<path:filename>")
@login_required
def uploaded_photo(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename, max_age=0)


@inventory_bp.route("/dashboard")
@login_required
def dashboard():
    summary = get_dashboard_summary()
    low_stock_items = get_low_stock_items(limit=6)
    top_issued = get_top_issued_items(limit=5)
    return render_template(
        "dashboard.html",
        summary=summary,
        low_stock_items=low_stock_items,
        top_issued=top_issued,
    )


@inventory_bp.route("/inventory")
@login_required
def inventory_list():
    filters = {
        "q": request.args.get("q", "").strip(),
        "category": request.args.get("category", "").strip(),
        "location": request.args.get("location", "").strip(),
        "low_stock": request.args.get("low_stock") == "1",
        "out_of_stock": request.args.get("out_of_stock") == "1",
    }
    supplies = search_supplies(
        query_text=filters["q"],
        category=filters["category"] or None,
        location=filters["location"] or None,
        low_stock=filters["low_stock"],
        out_of_stock=filters["out_of_stock"],
    )
    supply_payloads = [_supply_payload(supply) for supply in supplies]
    return render_template(
        "inventory/list.html",
        filters=filters,
        supplies=supplies,
        supplies_json=supply_payloads,
        categories=_distinct_values(Supply.category),
        locations=_distinct_values(Supply.location),
    )


@inventory_bp.route("/inventory/add", methods=["GET", "POST"])
@login_required
def add_supply_view():
    if request.method == "POST":
        photo_path = None
        try:
            photo_path = save_form_image(
                request.files.get("photo"),
                request.form.get("captured_photo_data"),
            )
            supply = add_new_supply(
                item_name=request.form.get("item_name"),
                description=request.form.get("description"),
                category=request.form.get("category"),
                unit=request.form.get("unit"),
                quantity=request.form.get("quantity"),
                minimum_quantity=request.form.get("minimum_quantity"),
                location=request.form.get("location"),
                photo_path=photo_path,
                remarks=request.form.get("remarks"),
                created_by=current_user,
            )
            flash(f"{supply.item_name} was added to inventory.", "success")
            return redirect(url_for("inventory.supply_detail", supply_id=supply.id))
        except (UploadError, InventoryError) as exc:
            if photo_path:
                delete_uploaded_image(photo_path)
            flash(str(exc), "danger")

    return render_template("inventory/add_supply.html")


@inventory_bp.route("/inventory/restock", methods=["GET", "POST"])
@login_required
def restock_supply_view():
    selected_supply_id = request.args.get("supply_id", type=int)
    if request.method == "POST":
        photo_path = None
        try:
            photo_path = save_uploaded_image(request.files.get("photo"))
            supply = restock_supply(
                supply_id=request.form.get("supply_id", type=int),
                quantity=request.form.get("quantity"),
                photo_path=photo_path,
                remarks=request.form.get("remarks"),
                performed_by=current_user,
            )
            flash(f"{supply.item_name} was restocked successfully.", "success")
            return redirect(url_for("inventory.supply_detail", supply_id=supply.id))
        except (UploadError, InventoryError) as exc:
            if photo_path:
                delete_uploaded_image(photo_path)
            flash(str(exc), "danger")
            selected_supply_id = request.form.get("supply_id", type=int)

    supplies = search_supplies(limit=200)
    supply_payloads = [_supply_payload(supply) for supply in supplies]
    return render_template(
        "inventory/restock_supply.html",
        supplies=supplies,
        supplies_json=supply_payloads,
        selected_supply_id=selected_supply_id,
    )


@inventory_bp.route("/inventory/issue", methods=["GET", "POST"])
@login_required
def issue_supply_view():
    selected_supply_id = request.args.get("supply_id", type=int)
    if request.method == "POST":
        try:
            supply = issue_supply(
                supply_id=request.form.get("supply_id", type=int),
                quantity=request.form.get("quantity"),
                remarks=request.form.get("remarks"),
                performed_by=current_user,
            )
            flash(f"{supply.item_name} was issued successfully.", "success")
            return redirect(url_for("inventory.supply_detail", supply_id=supply.id))
        except InventoryError as exc:
            flash(str(exc), "danger")
            selected_supply_id = request.form.get("supply_id", type=int)

    supplies = [supply for supply in search_supplies(limit=250) if supply.current_quantity > 0]
    supply_payloads = [_supply_payload(supply) for supply in supplies]
    return render_template(
        "inventory/issue_supply.html",
        supplies=supplies,
        supplies_json=supply_payloads,
        selected_supply_id=selected_supply_id,
    )


@inventory_bp.route("/inventory/<int:supply_id>")
@login_required
def supply_detail(supply_id):
    supply = Supply.query.get_or_404(supply_id)
    return render_template("inventory/detail.html", supply=supply, supply_json=_supply_payload(supply))


@inventory_bp.route("/inventory/<int:supply_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_supply_view(supply_id):
    deleted_supply = delete_supply(supply_id=supply_id)
    delete_uploaded_image(deleted_supply["photo_path"])
    flash(f'{deleted_supply["item_name"]} was deleted from inventory.', "success")
    return redirect(url_for("inventory.inventory_list"))


@inventory_bp.route("/inventory/history")
@login_required
@role_required("admin")
def transaction_history():
    transactions = StockTransaction.query.order_by(StockTransaction.created_at.desc()).all()
    return render_template("inventory/history.html", transactions=transactions)


@inventory_bp.route("/analytics")
@login_required
@role_required("admin")
def analytics():
    low_stock_items = get_low_stock_items(limit=8)
    out_of_stock_items = Supply.query.filter_by(status="out_of_stock").order_by(Supply.item_name.asc()).all()
    top_issued = get_top_issued_items(limit=6)
    recent_movement = get_recent_stock_movement(limit=10)
    monthly_out_totals = get_monthly_stock_out_totals(months=6)
    chart_data = {
        "monthlyOutTotals": monthly_out_totals,
        "topIssued": [
            {"label": row["supply"].item_name, "total": int(row["issued_total"])}
            for row in top_issued
        ],
    }
    return render_template(
        "inventory/analytics.html",
        low_stock_items=low_stock_items,
        out_of_stock_items=out_of_stock_items,
        top_issued=top_issued,
        recent_movement=recent_movement,
        chart_data=chart_data,
    )


@inventory_bp.route("/api/supplies")
@login_required
def supply_api():
    supplies = search_supplies(
        query_text=request.args.get("q"),
        category=request.args.get("category"),
        location=request.args.get("location"),
        low_stock=request.args.get("low_stock") == "1",
        out_of_stock=request.args.get("out_of_stock") == "1",
        limit=200,
    )
    return jsonify([_supply_payload(supply) for supply in supplies])
