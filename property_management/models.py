import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Get absolute path of the project directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Use SQLite instead of PostgreSQL
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)  # ✅ Initialize db with app


class Property(db.Model):
    __tablename__ = 'properties'  # ✅ Explicit table name
    property_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    available_units = db.Column(db.Integer, nullable=False)
    size = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # ✅ Relationship with Unit model
    units = db.relationship('Unit', backref='property', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "property_id": self.property_id,
            "name": self.name,
            "owner": self.owner,
            "location": self.location,
            "property_type": self.property_type,
            "price": self.price,
            "bedrooms": self.bedrooms,
            "available_units": self.available_units,
            "size": self.size,
            "description": self.description,
            "units": [unit.to_dict() for unit in self.units]  # Include units in the response
        }


class Unit(db.Model):
    __tablename__ = "units"
    unit_id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(
        db.Integer, db.ForeignKey("properties.property_id", name="fk_unit_property"), nullable=False
    )
    tenant_id = db.Column(
        db.Integer, db.ForeignKey("tenants.tenant_id", name="fk_unit_tenant"), nullable=True
    )
    unit_number = db.Column(db.String(50), nullable=False)
    rent_price = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)

    # ❌ Removed duplicate relationship with Property

    # Relationship with Tenant (One-to-One)
    tenant = db.relationship("Tenant", back_populates="unit", uselist=False)

    def to_dict(self):
        return {
            "unit_id": self.unit_id,
            "property_id": self.property_id,
            "tenant_id": self.tenant_id,
            "unit_number": self.unit_number,
            "rent_price": self.rent_price,
            "is_available": self.is_available,
            "description": self.description,
            "tenant": self.tenant.to_dict() if self.tenant else None
        }


class Tenant(db.Model):
    __tablename__ = "tenants"
    tenant_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)

    # Relationship with Unit (One-to-One)
    unit = db.relationship('Unit', back_populates="tenant", uselist=False)

    def to_dict(self):
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
        }
