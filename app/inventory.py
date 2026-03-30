from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from .constants import SUPPLY_CATEGORIES, display_supply_category
from .decorators import role_required
from .extensions import db
from .models import StockTransaction, Supply, User
from .security import validate_password_strength
from .services import (
    InventoryError,
    add_new_supply,
    delete_supply,
    get_dashboard_summary,
    get_low_stock_items,
    get_monthly_stock_out_totals,
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


def _user_avatar_url(user):
    if user.avatar_path:
        return photo_url_for(user.avatar_path)
    return url_for("static", filename="media/dilg-logo.png")


def _user_initials(user):
    parts = [part[:1].upper() for part in (user.full_name or "").split() if part]
    return "".join(parts[:2]) or (user.username[:2].upper() if user.username else "U")


def _inventory_audit_owner(*, exclude_user_id=None):
    # Inventory records are intentionally owned by an admin account so history
    # remains attributable even if staff users are deleted later.
    admins = User.query.filter_by(role="admin").order_by(User.created_at.asc(), User.id.asc()).all()
    if exclude_user_id is not None:
        admins = [admin for admin in admins if admin.id != exclude_user_id]

    if not admins:
        return None

    return admins[0]


def _profile_user_directory(admin_user):
    # The profile page doubles as a lightweight user-management screen for
    # admins, so it precomputes counts and deletion rules for each account.
    admin_count = User.query.filter_by(role="admin").count()
    audit_owner = _inventory_audit_owner()
    rows = (
        db.session.query(
            User,
            func.count(func.distinct(Supply.id)).label("supply_count"),
            func.count(func.distinct(StockTransaction.id)).label("transaction_count"),
        )
        .outerjoin(Supply, Supply.created_by == User.id)
        .outerjoin(StockTransaction, StockTransaction.performed_by == User.id)
        .group_by(User.id)
        .order_by((User.role == "admin").desc(), User.created_at.asc(), User.full_name.asc())
        .all()
    )

    directory = []
    for user, supply_count, transaction_count in rows:
        delete_reason = None
        if user.id == admin_user.id:
            delete_reason = "Signed in with this account."
        elif user.is_admin and admin_count <= 1:
            delete_reason = "This is the only admin account."

        directory.append(
            {
                "user": user,
                "avatar_url": _user_avatar_url(user),
                "initials": _user_initials(user),
                "created_label": user.created_at.strftime("%d %b %Y"),
                "supply_count": supply_count,
                "transaction_count": transaction_count,
                "can_delete": delete_reason is None,
                "delete_reason": delete_reason,
                "is_audit_owner": bool(audit_owner and audit_owner.id == user.id),
                "will_transfer_history": bool(supply_count or transaction_count),
            }
        )

    return {
        "users": directory,
        "total_users": len(directory),
        "admin_users": sum(1 for entry in directory if entry["user"].is_admin),
        "deletable_users": sum(1 for entry in directory if entry["can_delete"]),
    }


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
        "category": display_supply_category(supply.category),
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


def _stock_card_payload(supply):
    # Stock cards are built from the transaction ledger in oldest-to-newest
    # order so the printable form reads chronologically.
    transactions = (
        StockTransaction.query.filter_by(supply_id=supply.id)
        .order_by(StockTransaction.created_at.asc(), StockTransaction.id.asc())
        .all()
    )
    ledger_rows = []
    for transaction in transactions:
        is_receipt = transaction.transaction_type == "in"
        ledger_rows.append(
            {
                "id": transaction.id,
                "date": transaction.created_at.strftime("%B %d, %Y"),
                "reference": f'{"RCPT" if is_receipt else "ISS"}-{transaction.id:05d}',
                "receipt_quantity": transaction.quantity if is_receipt else "",
                "issue_quantity": transaction.quantity if not is_receipt else "",
                "office": transaction.remarks or "",
                "balance_quantity": transaction.new_quantity,
                "days_to_consume": "",
                "transaction_type": transaction.transaction_type,
                "timestamp": transaction.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        )

    return {
        **_supply_payload(supply),
        "entity_name": "DILG IX - LGCDD",
        "appendix_label": "Appendix 58",
        "stock_no": "",
        "reorder_point": supply.minimum_quantity,
        "ledger_rows": ledger_rows,
    }


def _distinct_values(column):
    # Filter dropdowns should only show non-empty values that actually exist in
    # the current catalog.
    return [
        value
        for (value,) in db.session.query(column)
        .filter(column.isnot(None), column != "")
        .distinct()
        .order_by(column.asc())
        .all()
    ]


def _month_start(anchor=None, offset=0):
    # Analytics compares month windows repeatedly, so month-boundary handling is
    # centralized here.
    anchor = anchor or datetime.utcnow()
    year = anchor.year
    month = anchor.month + offset
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return datetime(year, month, 1)


def _percent_change(current, previous):
    if previous == 0:
        return 100.0 if current else 0.0
    return ((current - previous) / previous) * 100.0


@inventory_bp.route("/uploads/<path:filename>")
@login_required
def uploaded_photo(filename):
    # Protected uploads are served only to authenticated users.
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename, max_age=0)


@inventory_bp.route("/dashboard")
@login_required
def dashboard():
    # Dashboard combines service-layer summaries with a few route-specific
    # counts for today's activity cards.
    today_key = datetime.utcnow().date().isoformat()
    summary = get_dashboard_summary(limit_recent=5)
    low_stock_items = get_low_stock_items(limit=5)
    top_issued = get_top_issued_items(limit=3)
    stock_changes_today = (
        db.session.query(func.count(StockTransaction.id))
        .filter(func.date(StockTransaction.created_at) == today_key)
        .scalar()
        or 0
    )
    newly_out_today = (
        db.session.query(func.count(func.distinct(StockTransaction.supply_id)))
        .filter(
            StockTransaction.transaction_type == "out",
            StockTransaction.new_quantity == 0,
            func.date(StockTransaction.created_at) == today_key,
        )
        .scalar()
        or 0
    )
    quick_insights = [
        {
            "value": summary["low_stock_count"],
            "label": "Low stock items",
            "tone": "warning",
        },
        {
            "value": summary["out_of_stock_count"],
            "label": "Out of stock",
            "tone": "danger",
        },
        {
            "value": stock_changes_today,
            "label": "Stock changes today",
            "tone": "neutral",
        },
        {
            "value": newly_out_today,
            "label": "Newly out today",
            "tone": "neutral",
        },
    ]
    return render_template(
        "dashboard.html",
        summary=summary,
        low_stock_items=low_stock_items,
        top_issued=top_issued,
        quick_insights=quick_insights,
    )


@inventory_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile_view():
    # Profile POST actions are multiplexed through a single form endpoint so the
    # account page can manage details, password, avatar, and admin-only user
    # maintenance from one screen.
    if request.method == "POST":
        action = request.form.get("profile_action", "").strip()

        if action == "details":
            full_name = request.form.get("full_name", "").strip()
            if not full_name:
                flash("Name is required.", "danger")
            elif len(full_name) < 2:
                flash("Name must be at least 2 characters long.", "danger")
            else:
                current_user.full_name = full_name
                db.session.commit()
                flash("Profile name updated.", "success")
            return redirect(url_for("inventory.profile_view"))

        if action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")
            password_error = validate_password_strength(new_password)

            if not current_user.check_password(current_password):
                flash("Current password is incorrect.", "danger")
            elif password_error:
                flash(password_error, "danger")
            elif new_password != confirm_password:
                flash("New password and confirmation do not match.", "danger")
            elif current_password == new_password:
                flash("Choose a different password from the current one.", "warning")
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash("Password updated.", "success")
            return redirect(url_for("inventory.profile_view"))

        if action == "avatar":
            previous_avatar_path = current_user.avatar_path
            try:
                avatar_path = save_uploaded_image(request.files.get("avatar"))
            except UploadError as exc:
                flash(str(exc), "danger")
                return redirect(url_for("inventory.profile_view"))

            current_user.avatar_path = avatar_path
            db.session.commit()

            if previous_avatar_path and previous_avatar_path != avatar_path:
                delete_uploaded_image(previous_avatar_path)

            flash("Profile image updated.", "success")
            return redirect(url_for("inventory.profile_view"))

        if action == "delete_user":
            if not current_user.is_admin:
                abort(403)

            user_id = request.form.get("user_id", type=int)
            target_user = db.session.get(User, user_id) if user_id else None
            if not target_user:
                flash("That account no longer exists.", "warning")
                return redirect(url_for("inventory.profile_view"))

            if target_user.id == current_user.id:
                flash("You cannot delete the account that is currently signed in.", "warning")
                return redirect(url_for("inventory.profile_view"))

            remaining_admin_count = User.query.filter_by(role="admin").count() - (1 if target_user.is_admin else 0)
            if target_user.is_admin and remaining_admin_count < 1:
                flash("You cannot remove the only admin account.", "danger")
                return redirect(url_for("inventory.profile_view"))

            audit_owner = _inventory_audit_owner(exclude_user_id=target_user.id)
            if not audit_owner:
                flash("No admin account is available to retain inventory history.", "danger")
                return redirect(url_for("inventory.profile_view"))

            avatar_path = target_user.avatar_path
            deleted_name = target_user.full_name
            linked_supply_count = Supply.query.filter_by(created_by=target_user.id).count()
            linked_transaction_count = StockTransaction.query.filter_by(performed_by=target_user.id).count()
            # Historical records are transferred before deletion so analytics,
            # stock cards, and audit history remain intact.
            Supply.query.filter_by(created_by=target_user.id).update({"created_by": audit_owner.id})
            StockTransaction.query.filter_by(performed_by=target_user.id).update({"performed_by": audit_owner.id})
            db.session.delete(target_user)
            db.session.commit()

            if avatar_path:
                delete_uploaded_image(avatar_path)

            if linked_supply_count or linked_transaction_count:
                flash(
                    f"{deleted_name} was deleted. Linked inventory history was reassigned to {audit_owner.full_name}.",
                    "success",
                )
            else:
                flash(f"{deleted_name} was deleted.", "success")
            return redirect(url_for("inventory.profile_view"))

        flash("That profile action is not available.", "warning")
        return redirect(url_for("inventory.profile_view"))

    user_directory = _profile_user_directory(current_user) if current_user.is_admin else None
    return render_template(
        "inventory/profile.html",
        avatar_url=_user_avatar_url(current_user),
        user_initials=_user_initials(current_user),
        user_directory=user_directory,
    )


@inventory_bp.route("/inventory")
@login_required
def inventory_list():
    # The initial page render includes both server-rendered markup and a JSON
    # payload that the browser uses for preview and filtering interactions.
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
        categories=SUPPLY_CATEGORIES,
        locations=_distinct_values(Supply.location),
    )


@inventory_bp.route("/inventory/add", methods=["GET", "POST"])
@login_required
def add_supply_view():
    if request.method == "POST":
        photo_path = None
        try:
            # New supplies are attributed to the audit owner rather than the
            # currently signed-in user to keep long-term record ownership stable.
            audit_owner = _inventory_audit_owner()
            if not audit_owner:
                raise InventoryError("No admin account is available to own inventory records.")
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
                created_by=audit_owner,
            )
            flash(f"{supply.item_name} was added to inventory.", "success")
            return redirect(url_for("inventory.supply_detail", supply_id=supply.id))
        except (UploadError, InventoryError) as exc:
            # If validation fails after an image was saved, remove the file so
            # the uploads directory does not accumulate orphaned photos.
            if photo_path:
                delete_uploaded_image(photo_path)
            flash(str(exc), "danger")

    return render_template("inventory/add_supply.html", categories=SUPPLY_CATEGORIES)


@inventory_bp.route("/inventory/restock", methods=["GET", "POST"])
@login_required
def restock_supply_view():
    # This screen is the stock-in workflow: pick an existing item, preview the
    # resulting balance, then delegate the update to the service layer.
    selected_supply_id = request.args.get("supply_id", type=int)
    if request.method == "POST":
        try:
            audit_owner = _inventory_audit_owner()
            if not audit_owner:
                raise InventoryError("No admin account is available to own inventory records.")
            supply = restock_supply(
                supply_id=request.form.get("supply_id", type=int),
                category=request.form.get("category"),
                quantity=request.form.get("quantity"),
                remarks=request.form.get("remarks"),
                performed_by=audit_owner,
            )
            flash(f"{supply.item_name} was restocked successfully.", "success")
            return redirect(url_for("inventory.supply_detail", supply_id=supply.id))
        except InventoryError as exc:
            flash(str(exc), "danger")
            selected_supply_id = request.form.get("supply_id", type=int)

    supplies = search_supplies(limit=200)
    supply_payloads = [_supply_payload(supply) for supply in supplies]
    return render_template(
        "inventory/restock_supply.html",
        categories=SUPPLY_CATEGORIES,
        supplies=supplies,
        supplies_json=supply_payloads,
        selected_supply_id=selected_supply_id,
    )


@inventory_bp.route("/inventory/issue", methods=["GET", "POST"])
@login_required
def issue_supply_view():
    # This mirrors restock, but only exposes items with available quantity and
    # routes the final validation through the issue service.
    selected_supply_id = request.args.get("supply_id", type=int)
    if request.method == "POST":
        try:
            audit_owner = _inventory_audit_owner()
            if not audit_owner:
                raise InventoryError("No admin account is available to own inventory records.")
            supply = issue_supply(
                supply_id=request.form.get("supply_id", type=int),
                quantity=request.form.get("quantity"),
                remarks=request.form.get("remarks"),
                performed_by=audit_owner,
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
    # Detail is the canonical per-item view; nearby screens link back here
    # after add, restock, and issue operations complete.
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
    # History is admin-only because it exposes the full transaction ledger
    # across every item and every user.
    transactions = StockTransaction.query.order_by(StockTransaction.created_at.desc()).all()
    return render_template("inventory/history.html", transactions=transactions)


@inventory_bp.route("/inventory/stock-card")
@login_required
def stock_card_view():
    # The stock-card page starts with lightweight supply data and lets the
    # browser fetch the full printable ledger on demand.
    selected_supply_id = request.args.get("supply_id", type=int)
    initial_category = request.args.get("category", "").strip()
    supplies = search_supplies()
    supply_payloads = [_supply_payload(supply) for supply in supplies]
    return render_template(
        "inventory/stock_card.html",
        categories=SUPPLY_CATEGORIES,
        supplies_json=supply_payloads,
        selected_supply_id=selected_supply_id,
        initial_category=initial_category,
    )


@inventory_bp.route("/analytics")
@login_required
@role_required("admin")
def analytics():
    # This view assembles read-heavy metrics for the analytics dashboard. Most
    # calculations stay here because they combine several overlapping business
    # rules that are specific to the report presentation.
    now = datetime.utcnow()
    current_month_start = _month_start(now)
    previous_month_start = _month_start(now, -1)
    next_month_start = _month_start(now, 1)
    last_30_days = now - timedelta(days=30)
    last_90_days = now - timedelta(days=90)

    supplies = Supply.query.order_by(Supply.item_name.asc()).all()
    low_stock_items = get_low_stock_items(limit=None)
    out_of_stock_items = Supply.query.filter_by(status="out_of_stock").order_by(Supply.item_name.asc()).all()
    recent_movement = (
        StockTransaction.query.options(
            joinedload(StockTransaction.supply),
            joinedload(StockTransaction.performer),
        )
        .order_by(StockTransaction.created_at.desc())
        .limit(8)
        .all()
    )
    monthly_out_totals = get_monthly_stock_out_totals(months=6)
    month_total_map = {item["label"]: item["total"] for item in monthly_out_totals}
    current_month_key = current_month_start.strftime("%Y-%m")
    previous_month_key = previous_month_start.strftime("%Y-%m")
    issued_this_month = int(month_total_map.get(current_month_key, 0) or 0)
    issued_last_month = int(month_total_map.get(previous_month_key, 0) or 0)
    prior_three_months = [item["total"] for item in monthly_out_totals[:-1][-3:]]
    prior_three_month_avg = (
        sum(prior_three_months) / len(prior_three_months)
        if prior_three_months
        else float(issued_last_month)
    )

    issued_total_recent = func.coalesce(func.sum(StockTransaction.quantity), 0).label("issued_total")
    top_issued_rows = (
        db.session.query(Supply, issued_total_recent)
        .join(StockTransaction, StockTransaction.supply_id == Supply.id)
        .filter(
            StockTransaction.transaction_type == "out",
            StockTransaction.created_at >= last_90_days,
        )
        .group_by(Supply.id)
        .order_by(issued_total_recent.desc(), Supply.item_name.asc())
        .limit(5)
        .all()
    )
    top_issued = (
        [{"supply": supply, "issued_total": int(total or 0)} for supply, total in top_issued_rows]
        or get_top_issued_items(limit=5)
    )

    out_transactions = (
        StockTransaction.query.options(joinedload(StockTransaction.supply))
        .filter(StockTransaction.transaction_type == "out")
        .order_by(StockTransaction.created_at.desc())
        .all()
    )
    supply_stats = defaultdict(
        lambda: {
            "issued_30": 0,
            "issued_90": 0,
            "issued_total": 0,
            "issue_events_30": 0,
            "issue_events_90": 0,
            "stockouts_90": 0,
            "stockouts_total": 0,
            "last_issue_at": None,
        }
    )
    low_stock_entries_this_month = 0
    low_stock_entries_last_month = 0
    stockout_hits_this_month = 0
    stockout_hits_last_month = 0

    for transaction in out_transactions:
        # Issue transactions drive consumption trends, stock-out frequency, and
        # "entered low stock" events for the KPI comparisons.
        stats = supply_stats[transaction.supply_id]
        stats["issued_total"] += transaction.quantity
        if stats["last_issue_at"] is None or transaction.created_at > stats["last_issue_at"]:
            stats["last_issue_at"] = transaction.created_at
        if transaction.created_at >= last_30_days:
            stats["issued_30"] += transaction.quantity
            stats["issue_events_30"] += 1
        if transaction.created_at >= last_90_days:
            stats["issued_90"] += transaction.quantity
            stats["issue_events_90"] += 1
        if transaction.new_quantity == 0:
            stats["stockouts_total"] += 1
            if transaction.created_at >= last_90_days:
                stats["stockouts_90"] += 1

        minimum_quantity = transaction.supply.minimum_quantity
        entered_low_stock = (
            transaction.previous_quantity > minimum_quantity
            and 0 < transaction.new_quantity <= minimum_quantity
        )
        reached_stock_out = transaction.new_quantity == 0
        if current_month_start <= transaction.created_at < next_month_start:
            if entered_low_stock:
                low_stock_entries_this_month += 1
            if reached_stock_out:
                stockout_hits_this_month += 1
        elif previous_month_start <= transaction.created_at < current_month_start:
            if entered_low_stock:
                low_stock_entries_last_month += 1
            if reached_stock_out:
                stockout_hits_last_month += 1

    total_items = len(supplies)
    low_stock_count = sum(1 for supply in supplies if supply.is_low_stock)
    out_of_stock_count = sum(1 for supply in supplies if supply.current_quantity == 0)
    healthy_count = max(total_items - low_stock_count - out_of_stock_count, 0)
    low_stock_rate = (low_stock_count / total_items * 100) if total_items else 0
    out_of_stock_rate = (out_of_stock_count / total_items * 100) if total_items else 0
    healthy_rate = (healthy_count / total_items * 100) if total_items else 0

    month_delta = issued_this_month - issued_last_month
    month_delta_pct = _percent_change(issued_this_month, issued_last_month)
    if issued_this_month and prior_three_month_avg and issued_this_month >= prior_three_month_avg * 1.25:
        issue_activity_signal = {
            "tone": "warning",
            "label": "Issue activity is elevated",
            "message": f"Issues this month are {month_delta_pct:+.0f}% versus last month and above the recent baseline.",
            "caption": f"Three-month average: {prior_three_month_avg:.0f} units",
        }
    elif issued_this_month and prior_three_month_avg and issued_this_month <= prior_three_month_avg * 0.75:
        issue_activity_signal = {
            "tone": "success",
            "label": "Issue activity has cooled",
            "message": "Outbound movement is running below the recent baseline, which lowers immediate replenishment pressure.",
            "caption": f"Three-month average: {prior_three_month_avg:.0f} units",
        }
    else:
        issue_activity_signal = {
            "tone": "neutral",
            "label": "Issue activity is steady",
            "message": "Monthly outbound movement is broadly in line with the recent pattern.",
            "caption": f"This month {issued_this_month:,} units, last month {issued_last_month:,}",
        }

    fast_movers = []
    for supply in supplies:
        stats = supply_stats[supply.id]
        if stats["issued_90"] <= 0:
            continue
        fast_movers.append(
            {
                "supply": supply,
                "issued_90": stats["issued_90"],
                "issued_30": stats["issued_30"],
            }
        )
    fast_movers.sort(key=lambda item: (-item["issued_90"], item["supply"].item_name.lower()))
    fast_movers = fast_movers[:3]

    slow_movers = []
    for supply in supplies:
        stats = supply_stats[supply.id]
        if stats["issued_90"] > 0 or supply.current_quantity == 0:
            continue
        slow_movers.append(
            {
                "supply": supply,
                "last_issue_at": stats["last_issue_at"],
                "status": (
                    "Never issued"
                    if stats["last_issue_at"] is None
                    else f"Last issue {stats['last_issue_at'].strftime('%d %b %Y')}"
                ),
            }
        )
    slow_movers.sort(
        key=lambda item: (
            item["last_issue_at"] is not None,
            item["last_issue_at"] or datetime.min,
            -item["supply"].current_quantity,
            item["supply"].item_name.lower(),
        )
    )
    slow_movers = slow_movers[:3]

    restock_priorities = []
    for supply in supplies:
        stats = supply_stats[supply.id]
        shortfall = max(supply.minimum_quantity - supply.current_quantity, 0)
        demand_pressure = stats["issued_30"] or stats["issued_90"]
        if not (
            supply.current_quantity == 0
            or supply.is_low_stock
            or stats["stockouts_90"] > 0
            or (demand_pressure > 0 and supply.current_quantity <= max(supply.minimum_quantity, 1) + stats["issued_30"])
        ):
            continue

        score = 0
        if supply.current_quantity == 0:
            score += 10
        elif supply.is_low_stock:
            score += 6
        else:
            score += 3
        score += min(shortfall, 5)
        score += min(demand_pressure / max(supply.minimum_quantity or 1, 1), 5)
        score += min(stats["stockouts_90"] * 2, 4)

        reasons = []
        if supply.current_quantity == 0:
            reasons.append("Out of stock")
        elif shortfall > 0:
            reasons.append(f"{shortfall} below minimum")
        elif supply.is_low_stock:
            reasons.append("At minimum threshold")
        if stats["issued_30"] > 0:
            reasons.append(f"{stats['issued_30']:,} issued in 30d")
        if stats["stockouts_90"] > 0:
            hit_label = "hit" if stats["stockouts_90"] == 1 else "hits"
            reasons.append(f"{stats['stockouts_90']} stock-out {hit_label} in 90d")

        restock_priorities.append(
            {
                "supply": supply,
                "score": score,
                "tone": "danger" if supply.current_quantity == 0 or stats["stockouts_90"] >= 2 else "warning",
                "issued_30": stats["issued_30"],
                "stockouts_90": stats["stockouts_90"],
                "summary": " | ".join(reasons[:2]) if reasons else "Monitor demand against the current stock level.",
            }
        )
    # Higher score means higher urgency; the remaining sort keys keep the list
    # deterministic for items with similar pressure.
    restock_priorities.sort(
        key=lambda item: (-item["score"], item["supply"].current_quantity, item["supply"].item_name.lower())
    )
    restock_priorities = restock_priorities[:5]
    critical_priority_count = sum(1 for item in restock_priorities if item["tone"] == "danger")

    attention_items = []
    for supply in low_stock_items:
        stats = supply_stats[supply.id]
        attention_items.append(
            {
                "supply": supply,
                "issued_30": stats["issued_30"],
                "summary": f"{supply.current_quantity:,} {supply.unit} left | minimum {supply.minimum_quantity:,}",
                "note": (
                    f"{stats['issued_30']:,} issued in the last 30 days"
                    if stats["issued_30"] > 0
                    else "Low stock based on the current on-hand balance"
                ),
            }
        )
    attention_items.sort(
        key=lambda item: (-(item["issued_30"] > 0), item["supply"].current_quantity, item["supply"].item_name.lower())
    )
    attention_items = attention_items[:4]

    unavailable_items = []
    for supply in out_of_stock_items:
        stats = supply_stats[supply.id]
        unavailable_items.append(
            {
                "supply": supply,
                "stockouts_total": stats["stockouts_total"],
                "stockouts_90": stats["stockouts_90"],
                "last_issue_at": stats["last_issue_at"],
                "note": (
                    f"{stats['stockouts_90']} stock-out hit(s) in the last 90 days"
                    if stats["stockouts_90"] > 0
                    else "No stock available to issue"
                ),
            }
        )
    unavailable_items.sort(
        key=lambda item: (-item["stockouts_90"], -item["stockouts_total"], item["supply"].item_name.lower())
    )
    unavailable_items = unavailable_items[:4]

    analytics_kpis = [
        {
            "label": "Issued this month",
            "value": f"{issued_this_month:,}",
            "detail": (
                f"{abs(month_delta):,} {'more' if month_delta > 0 else 'fewer'} units than last month"
                if month_delta
                else "Flat versus last month"
            ),
            "caption": f"Last month: {issued_last_month:,} units",
            "tone": issue_activity_signal["tone"],
        },
        {
            "label": "Low-stock items",
            "value": f"{low_stock_count:,}",
            "detail": f"{low_stock_entries_this_month} entered low stock this month vs {low_stock_entries_last_month} last month",
            "caption": f"{low_stock_rate:.1f}% of the catalog is below target",
            "tone": "warning" if low_stock_count else "success",
        },
        {
            "label": "Out-of-stock items",
            "value": f"{out_of_stock_count:,}",
            "detail": f"{stockout_hits_this_month} stock-out hits this month vs {stockout_hits_last_month} last month",
            "caption": f"{out_of_stock_rate:.1f}% of the catalog is unavailable",
            "tone": "danger" if out_of_stock_count else "success",
        },
        {
            "label": "Restock priority",
            "value": f"{len(restock_priorities):,}",
            "detail": f"{critical_priority_count} critical and {max(len(restock_priorities) - critical_priority_count, 0)} high-priority items",
            "caption": restock_priorities[0]["supply"].item_name if restock_priorities else "No urgent restocks",
            "tone": "danger" if critical_priority_count else "warning",
        },
    ]

    chart_data = {
        "monthlyOutTotals": monthly_out_totals,
        "topIssued": [
            {"label": row["supply"].item_name, "total": int(row["issued_total"])}
            for row in top_issued
        ],
    }
    return render_template(
        "inventory/analytics.html",
        analytics_kpis=analytics_kpis,
        attention_items=attention_items,
        fast_movers=fast_movers,
        healthy_rate=healthy_rate,
        issue_activity_signal=issue_activity_signal,
        issued_last_month=issued_last_month,
        issued_this_month=issued_this_month,
        low_stock_count=low_stock_count,
        low_stock_rate=low_stock_rate,
        month_delta=month_delta,
        out_of_stock_count=out_of_stock_count,
        out_of_stock_rate=out_of_stock_rate,
        restock_priorities=restock_priorities,
        slow_movers=slow_movers,
        top_issued=top_issued,
        unavailable_items=unavailable_items,
        recent_movement=recent_movement,
        chart_data=chart_data,
    )


@inventory_bp.route("/api/supplies")
@login_required
def supply_api():
    # This API backs the interactive inventory browser filters in the frontend.
    supplies = search_supplies(
        query_text=request.args.get("q"),
        category=request.args.get("category"),
        location=request.args.get("location"),
        low_stock=request.args.get("low_stock") == "1",
        out_of_stock=request.args.get("out_of_stock") == "1",
    )
    return jsonify([_supply_payload(supply) for supply in supplies])


@inventory_bp.route("/api/supplies/<int:supply_id>/stock-card")
@login_required
def supply_stock_card_api(supply_id):
    # The printable stock-card sheet is loaded separately so the page does not
    # render every ledger up front.
    supply = Supply.query.get_or_404(supply_id)
    return jsonify(_stock_card_payload(supply))
