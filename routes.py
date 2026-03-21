from flask import request, jsonify

try:
    from . import db
    from .models import Supply, StockTransaction
except ImportError:
    from __init__ import db
    from models import Supply, StockTransaction


def register_routes(app):
    @app.route("/")
    def home():
        return {"message": "Inventory System API is running"}

    @app.route("/supplies", methods=["GET"])
    def get_supplies():
        supplies = Supply.query.order_by(Supply.item_name.asc()).all()

        return jsonify(
            [
                {
                    "id": supply.id,
                    "item_name": supply.item_name,
                    "description": supply.description,
                    "unit": supply.unit,
                    "current_quantity": supply.current_quantity,
                    "minimum_quantity": supply.minimum_quantity,
                    "category": supply.category,
                    "location": supply.location,
                    "photo_path": supply.photo_path,
                    "status": supply.status,
                    "is_low_stock": supply.is_low_stock,
                }
                for supply in supplies
            ]
        )

    @app.route("/supplies/add", methods=["POST"])
    def add_supply():
        data = request.get_json()

        required_fields = ["item_name", "description", "unit", "quantity"]
        for field in required_fields:
            if field not in data or str(data[field]).strip() == "":
                return jsonify({"error": f"{field} is required"}), 400

        try:
            quantity = int(data["quantity"])
            minimum_quantity = int(data.get("minimum_quantity", 0))
        except ValueError:
            return jsonify({"error": "Quantity fields must be integers"}), 400

        if quantity <= 0:
            return jsonify({"error": "Quantity must be greater than zero"}), 400

        supply = Supply(
            item_name=data["item_name"].strip(),
            description=data["description"].strip(),
            unit=data["unit"].strip(),
            current_quantity=quantity,
            minimum_quantity=minimum_quantity,
            category=data.get("category"),
            location=data.get("location"),
            photo_path=data.get("photo_path"),
            status="active",
        )

        db.session.add(supply)
        db.session.flush()

        transaction = StockTransaction(
            supply_id=supply.id,
            transaction_type="in",
            quantity=quantity,
            previous_quantity=0,
            new_quantity=quantity,
            remarks=data.get("remarks"),
        )

        db.session.add(transaction)
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Supply added successfully",
                    "supply": {
                        "id": supply.id,
                        "item_name": supply.item_name,
                        "current_quantity": supply.current_quantity,
                    },
                }
            ),
            201,
        )
