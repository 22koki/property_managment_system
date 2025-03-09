from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from models import db, Property, Unit  # Import models

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///property_mgmt.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)
CORS(app)  # Enable CORS for all routes

# 🏠 Get all properties
@app.route('/properties', methods=['GET'])
def get_properties():
    properties = Property.query.all()
    return jsonify([prop.to_dict() for prop in properties])



# 📍 Get a specific property
@app.route('/properties/<int:property_id>', methods=['GET'])
def get_property(property_id):
    prop = Property.query.get(property_id)
    if not prop:
        return jsonify({"error": "Property not found"}), 404
    return jsonify(prop.to_dict())

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

    # Assuming a database model `Unit` exists
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

    db.session.delete(unit)
    db.session.commit()
    return jsonify({"message": "Unit deleted successfully"})

# 🏁 Run Flask app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✅ Tables created successfully!")
    app.run(debug=True)
