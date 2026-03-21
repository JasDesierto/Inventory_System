from datetime import datetime

try:
    from . import db
except ImportError:
    from __init__ import db


class Supply(db.Model):
    __tablename__ = "supplies"

    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    unit = db.Column(db.String(50), nullable=False)
    current_quantity = db.Column(db.Integer, nullable=False, default=0)
    minimum_quantity = db.Column(db.Integer, nullable=False, default=0)
    photo_path = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    transactions = db.relationship(
        "StockTransaction", backref="supply", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def is_low_stock(self):
        return self.current_quantity <= self.minimum_quantity


class StockTransaction(db.Model):
    __tablename__ = "stock_transactions"

    id = db.Column(db.Integer, primary_key=True)
    supply_id = db.Column(db.Integer, db.ForeignKey("supplies.id"), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # in / out
    quantity = db.Column(db.Integer, nullable=False)
    previous_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
