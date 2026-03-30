from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    # User accounts control login, role-based access, and ownership/audit links
    # for supplies and stock transactions.
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_path = db.Column(db.String(255), nullable=True)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    supplies_created = db.relationship(
        "Supply",
        back_populates="creator",
        lazy=True,
        foreign_keys="Supply.created_by",
    )
    transactions_performed = db.relationship(
        "StockTransaction",
        back_populates="performer",
        lazy=True,
        foreign_keys="StockTransaction.performed_by",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class Supply(db.Model):
    # Supply is the current-state record for an inventory item. Quantity changes
    # are persisted through StockTransaction records instead of manual edits.
    __tablename__ = "supplies"

    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(150), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True, index=True)
    unit = db.Column(db.String(50), nullable=False)
    current_quantity = db.Column(db.Integer, nullable=False, default=0)
    minimum_quantity = db.Column(db.Integer, nullable=False, default=0)
    location = db.Column(db.String(120), nullable=True, index=True)
    photo_path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="in_stock", index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    creator = db.relationship("User", back_populates="supplies_created")
    transactions = db.relationship(
        "StockTransaction",
        back_populates="supply",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="StockTransaction.created_at.desc()",
    )

    @property
    def is_low_stock(self):
        return 0 < self.current_quantity <= self.minimum_quantity

    @property
    def status_label(self):
        return {
            "in_stock": "In stock",
            "low_stock": "Low stock",
            "out_of_stock": "Out of stock",
        }.get(self.status, self.status.replace("_", " ").title())


class StockTransaction(db.Model):
    # Stock transactions form the audit trail for every stock-in and stock-out
    # movement and preserve the before/after quantities for reporting.
    __tablename__ = "stock_transactions"

    id = db.Column(db.Integer, primary_key=True)
    supply_id = db.Column(db.Integer, db.ForeignKey("supplies.id"), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    previous_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    performed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    supply = db.relationship("Supply", back_populates="transactions")
    performer = db.relationship("User", back_populates="transactions_performed")
