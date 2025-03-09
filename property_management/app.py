from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from models import db, Property ,Unit # Import this is at the top


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///property_mgmt.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)  # Initialize SQLAlchemy with app
migrate = Migrate(app, db)


CORS(app)  # Enable CORS for all routes

# Define the Property Model



# Get all properties
@app.route('/properties', methods=['GET'])
def get_properties():
    properties = Property.query.all()
    return jsonify([prop.to_dict() for prop in properties])


# Add a new property
@app.route('/properties', methods=['POST'])
def add_property():
    data = request.json

    new_property = Property(
        name=data['name'],
        owner=data['owner'],
        location=data['location'],
        property_type=data['property_type'],
        price=data['price'],
        bedrooms=data['bedrooms'],
        available_units=data['available_units'],
        size=data['size'],
        description=data['description']
    )

    db.session.add(new_property)
    db.session.commit()

    return jsonify({"message": "Property added successfully!"}), 201
# Get a specific property by ID
@app.route('/properties/<int:property_id>', methods=['GET'])
def get_property(property_id):
    property = Property.query.get(property_id)
    if not property:
        return jsonify({"error": "Property not found"}), 404
    return jsonify(property.to_dict())


# Update an existing property
@app.route('/properties/<int:property_id>', methods=['PUT'])
def update_property(property_id):
    property = Property.query.get(property_id)
    if not property:
        return jsonify({"error": "Property not found"}), 404

    data = request.json
    property.name = data['name']
    property.owner = data['owner']
    property.location = data['location']
    property.property_type = data['property_type']
    property.price = data['price']
    property.bedrooms = data['bedrooms']
    property.available_units = data['available_units']
    property.size = data['size']
    property.description = data['description']

    db.session.commit()
    return jsonify({"message": "Property updated successfully!"})

# Get all properties (for dropdown selection)
@app.route('/properties', methods=['GET'])
def get_properties():
    properties = Property.query.all()
    return jsonify([{"property_id": p.property_id, "name": p.name} for p in properties])

# Get units for a selected property
@app.route('/properties/<int:property_id>/units', methods=['GET'])
def get_units(property_id):
    property_exists = Property.query.get(property_id)
    if not property_exists:
        return jsonify({"error": "Invalid property ID"}), 404
    
    units = Unit.query.filter_by(property_id=property_id).all()
    return jsonify([unit.to_dict() for unit in units])

# Add a new unit
@app.route('/units', methods=['POST'])
def add_unit():
    data = request.json
    new_unit = Unit(
        property_id=data['property_id'],
        unit_number=data['unit_number'],
        rent_price=data['rent_price'],
        is_available=data['is_available'],
        description=data.get('description', "")
    )
    db.session.add(new_unit)
    db.session.commit()
    return jsonify({"message": "Unit added successfully", "unit": new_unit.to_dict()}), 201

# Update an existing unit
@app.route('/units/<int:unit_id>', methods=['PUT'])
def update_unit(unit_id):
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    data = request.json
    unit.unit_number = data.get('unit_number', unit.unit_number)
    unit.rent_price = data.get('rent_price', unit.rent_price)
    unit.is_available = data.get('is_available', unit.is_available)
    unit.description = data.get('description', unit.description)

    db.session.commit()
    return jsonify({"message": "Unit updated successfully", "unit": unit.to_dict()})

# Delete a unit
@app.route('/units/<int:unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    unit = Unit.query.get(unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    db.session.delete(unit)
    db.session.commit()
    return jsonify({"message": "Unit deleted successfully"})
if __name__ == "__main__":
    with app.app_context():  # Ensure app context is active
        db.create_all()
        print("✅ Tables created successfully!")
    app.run(debug=True)

