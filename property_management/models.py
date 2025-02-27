from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/property_mgmt'
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    phone = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
class Property(db.Model):
    __tablename__ = 'properties'
    property_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    owner = db.Column(db.String, nullable=False)
    location = db.Column(db.String, nullable=False)
    property_type = db.Column(db.String, nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    available_units = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String, nullable=True)

# Create all tables (if not created)
with app.app_context():
    db.create_all()


class Unit(db.Model):
    __tablename__ = 'units'
    unit_id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.property_id', ondelete='CASCADE'), nullable=False)
    unit_number = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    rent_amount = db.Column(db.Numeric(10,2), nullable=False)

class Tenant(db.Model):
    __tablename__ = 'tenants'
    tenant_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    phone = db.Column(db.String, nullable=False)

class Lease(db.Model):
    __tablename__ = 'leases'
    lease_id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.tenant_id', ondelete='CASCADE'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.unit_id', ondelete='CASCADE'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    rent_amount = db.Column(db.Numeric(10,2), nullable=False)

class Payment(db.Model):
    __tablename__ = 'payments'
    payment_id = db.Column(db.Integer, primary_key=True)
    lease_id = db.Column(db.Integer, db.ForeignKey('leases.lease_id', ondelete='CASCADE'), nullable=False)
    amount_paid = db.Column(db.Numeric(10,2), nullable=False)
    payment_date = db.Column(db.DateTime, default=db.func.current_timestamp())

class MaintenanceRequest(db.Model):
    __tablename__ = 'maintenance_requests'
    request_id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.tenant_id', ondelete='CASCADE'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.unit_id', ondelete='CASCADE'), nullable=False)
    request_details = db.Column(db.String, nullable=False)
    status = db.Column(db.String, default='pending')
    request_date = db.Column(db.DateTime, default=db.func.current_timestamp())

# Create all tables
with app.app_context():
    db.create_all()
