from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    security_fee = db.Column(db.Float, nullable=False, default=500)
    garbage_fee = db.Column(db.Float, nullable=False, default=200)
    units = db.relationship("Unit", backref="property", lazy=True, cascade="all, delete-orphan")


class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)
    unit_no = db.Column(db.String(50), nullable=False, unique=True)
    rent_price = db.Column(db.Float, nullable=False)
    available = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"), nullable=True)


class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    phone_no = db.Column(db.String(15), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=True)

    property = db.relationship("Property", backref="tenants", lazy=True)
    unit = db.relationship("Unit", backref="tenant", uselist=False)


class Tenancy(db.Model):
    """History of tenant move-ins, moves and move-outs."""

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("unit.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    auto_invoice = db.Column(db.Boolean, nullable=False, default=True)
    next_invoice_date = db.Column(db.Date, nullable=True)
    last_invoice_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    tenant = db.relationship("Tenant", backref="tenancies")
    unit = db.relationship("Unit", backref="tenancies")


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"), nullable=False)
    tenancy_id = db.Column(db.Integer, db.ForeignKey("tenancy.id"), nullable=True)
    rent = db.Column(db.Float, nullable=False)
    security_fee = db.Column(db.Float, nullable=False)
    garbage_fee = db.Column(db.Float, nullable=False)
    water_bill = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Pending", nullable=False)
    issued_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)
    billing_period = db.Column(db.String(7), nullable=True)
    invoice_type = db.Column(db.String(30), nullable=False, default="Monthly Rent")

    tenant = db.relationship("Tenant", backref="invoices")
    tenancy = db.relationship("Tenancy", backref="invoices")


class MaintenanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending", nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    tenant = db.relationship("Tenant", backref="maintenance_requests")


class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    balance_due = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(30), nullable=False, default="Cash")
    transaction_reference = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    invoice = db.relationship("Invoice", backref="receipts")


class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
