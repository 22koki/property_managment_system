from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from models import db, Property, Unit ,Tenant # Import models

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///property_mgmt.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)
from flask_cors import CORS
CORS(app) 

# 🏠 Get all properties and add a new property
@app.route('/properties', methods=['GET', 'POST'])
def manage_properties():
    if request.method == 'POST':
        data = request.get_json()

        # Ensure required fields are present
        if not all(field in data for field in ["name", "owner", "location"]):
            return jsonify({"error": "Missing required fields"}), 400

        # Create a new property
        new_property = Property(
            name=data["name"],
            owner=data["owner"],
            location=data["location"],
            property_type=data.get("property_type", "Unknown"),
            price=data.get("price", 0),
            bedrooms=data.get("bedrooms", 0),
            available_units=data.get("available_units", 0),
            size=data.get("size", "N/A"),
            description=data.get("description", "")
        )

        # Add to database
        db.session.add(new_property)
        db.session.commit()

        return jsonify({"message": "Property added successfully!", "property": new_property.to_dict()}), 201

    # Handle GET request (return properties)
    properties = Property.query.all()
    return jsonify([prop.to_dict() for prop in properties])


# 📍 Get a specific property
@app.route('/properties/<int:property_id>', methods=['GET'])
def get_property(property_id):
    prop = Property.query.get(property_id)
    if not prop:
        return jsonify({"error": "Property not found"}), 404
    return jsonify(prop.to_dict())
@app.route('/properties/available', methods=['GET'])
def get_available_properties():
    properties = Property.query.all()
    data = [
        {
            "property_id": prop.property_id,
            "name": prop.name,
            "location": prop.location,
            "available_units": [
                unit.to_dict() for unit in prop.units if unit.is_available
            ]
        }
        for prop in properties if any(unit.is_available for unit in prop.units)
    ]
    return jsonify(data)


# ✏️ Update a property
@app.route('/properties/<int:property_id>', methods=['PUT'])
def update_property(property_id):
    prop = Property.query.get(property_id)
    if not prop:
        return jsonify({"error": "Property not found"}), 404

    data = request.json
    for key, value in data.items():
        setattr(prop, key, value)

    db.session.commit()
    return jsonify({"message": "Property updated successfully!"})

# 🚀 Get available units for a property (FIXED)
@app.route('/properties/<int:property_id>/available_units', methods=['GET'])
def get_available_units(property_id):
    property_ = Property.query.get(property_id)
    if not property_:
        return jsonify({"error": "Property not found"}), 404

    return jsonify({"available_units": property_.available_units})


# 🏘️ Get units for a property
@app.route('/properties/<int:property_id>/units', methods=['GET'])
def get_units(property_id):
    property_exists = Property.query.get(property_id)
    if not property_exists:
        return jsonify({"error": "Invalid property ID"}), 404
    
    units = Unit.query.filter_by(property_id=property_id).all()
    return jsonify([unit.to_dict() for unit in units])

# ➕ Add a new unit
@app.route('/units', methods=['POST'])
def add_unit():
    if not request.is_json:  # ✅ Check if request contains JSON data
        return jsonify({"error": "Invalid content type. Use application/json"}), 415  

    data = request.get_json()  # ✅ Correct way to parse JSON data

    # Example validation
    required_fields = ["property_id", "unit_number", "rent_price", "is_available"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400  

    # Add new unit
    new_unit = Unit(
        property_id=data['property_id'],
        unit_number=data['unit_number'],
        rent_price=data['rent_price'],
        is_available=data['is_available'],
        description=data.get('description', "")
    )

    db.session.add(new_unit)
    db.session.commit()

    # 🔄 Update available_units in Property
    property_ = Property.query.get(data['property_id'])
    if property_:
        property_.available_units += 1
        db.session.commit()

    return jsonify({"message": "Unit added successfully", "unit": new_unit.to_dict()}), 201

# ✏️ Update a unit
@app.route('/units/<int:unit_id>', methods=['PUT'])
def update_unit(unit_id):
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    data = request.json
    for key, value in data.items():
        setattr(unit, key, value)

    db.session.commit()
    return jsonify({"message": "Unit updated successfully", "unit": unit.to_dict()})

# ❌ Delete a unit
@app.route('/units/<int:unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    property_id = unit.property_id  # Store property ID before deleting unit

    db.session.delete(unit)
    db.session.commit()

    # 🔄 Update available_units in Property
    property_ = Property.query.get(property_id)
    if property_:
        property_.available_units -= 1 if property_.available_units > 0 else 0
        db.session.commit()

    return jsonify({"message": "Unit deleted successfully"})

@app.route('/assign_tenant', methods=['POST'])
def assign_tenant():
    data = request.get_json()

    # Validate input
    required_fields = ["unit_id", "name", "email", "phone"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    unit = Unit.query.get(data["unit_id"])
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    if not unit.is_available:
        return jsonify({"error": "Unit is already occupied"}), 400

    # Create new tenant
    new_tenant = Tenant(
        name=data["name"],
        email=data["email"],
        phone=data["phone"]
    )
    db.session.add(new_tenant)
    db.session.commit()

    # Assign tenant to unit
    unit.tenant_id = new_tenant.tenant_id
    unit.is_available = False
    db.session.commit()

    return jsonify({"message": "Tenant assigned successfully!", "tenant": new_tenant.to_dict()})
@app.route('/remove_tenant/<int:unit_id>', methods=['DELETE'])
def remove_tenant(unit_id):
    unit = Unit.query.get(unit_id)
    if not unit or not unit.tenant_id:
        return jsonify({"error": "No tenant assigned to this unit"}), 404

    # Remove tenant
    tenant = Tenant.query.get(unit.tenant_id)
    db.session.delete(tenant)
    
    # Make unit available
    unit.tenant_id = None
    unit.is_available = True
    db.session.commit()

    return jsonify({"message": "Tenant removed, unit is now available!"})
@app.route('/tenants', methods=['GET'])
def get_tenants():
    tenants = Tenant.query.all()
    return jsonify([tenant.to_dict() for tenant in tenants])


# 🏁 Run Flask app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✅ Tables created successfully!")
    app.run(debug=True)
