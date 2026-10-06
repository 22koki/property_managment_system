from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

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


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"), nullable=False)
    rent = db.Column(db.Float, nullable=False)
    security_fee = db.Column(db.Float, nullable=False)
    garbage_fee = db.Column(db.Float, nullable=False)
    water_bill = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Pending", nullable=False)

    tenant = db.relationship("Tenant", backref="invoices")


class MaintenanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenant.id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending", nullable=False)

    tenant = db.relationship("Tenant", backref="maintenance_requests")


class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    balance_due = db.Column(db.Float, nullable=False)

    invoice = db.relationship("Invoice", backref="receipts")


class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
