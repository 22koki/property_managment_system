from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    properties = db.relationship('Property', back_populates='owner', lazy=True)

    def __repr__(self):
        return f'<Owner {self.name}>'

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=False)
    units = db.relationship('Unit', back_populates='property', lazy=True)
    billings = db.relationship('Billing', back_populates='property_ref', lazy=True)  # Changed to property_ref

    owner = db.relationship('Owner', back_populates='properties')

    def __repr__(self):
        return f'<Property {self.name}, Owner ID: {self.owner_id}>'

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_number = db.Column(db.String(50), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    tenants = db.relationship('Tenant', back_populates='unit', lazy=True)

    property = db.relationship('Property', back_populates='units')

    def __repr__(self):
        return f'<Unit {self.unit_number}, Property ID: {self.property_id}>'

class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False)
    billings = db.relationship('Billing', back_populates='tenant', lazy=True)
    maintenance_requests = db.relationship('Maintenance', back_populates='tenant', lazy=True)

    unit = db.relationship('Unit', back_populates='tenants')

    def __repr__(self):
        return f'<Tenant {self.name}, Unit ID: {self.unit_id}>'

class Billing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    amount_due = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    is_paid = db.Column(db.Boolean, default=False)

    tenant = db.relationship('Tenant', back_populates='billings')
    property_ref = db.relationship('Property', back_populates='billings')  # Changed to property_ref
    payments = db.relationship('Payment', back_populates='billing', lazy=True)

    def __repr__(self):
        return f'<Billing {self.id}, Amount Due: {self.amount_due}, Tenant ID: {self.tenant_id}>'

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    description = db.Column(db.String(250), nullable=False)
    request_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default='Pending')  # e.g., Pending, In Progress, Completed

    tenant = db.relationship('Tenant', back_populates='maintenance_requests')

    def __repr__(self):
        return f'<Maintenance Request {self.id}, Tenant ID: {self.tenant_id}, Status: {self.status}>'

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    billing_id = db.Column(db.Integer, db.ForeignKey('billing.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, default=datetime.utcnow)

    billing = db.relationship('Billing', back_populates='payments')

    def __repr__(self):
        return f'<Payment {self.id}, Amount Paid: {self.amount_paid}, Billing ID: {self.billing_id}>'
