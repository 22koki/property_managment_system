from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///property_mgmt.db'  # Change if using PostgreSQL or MySQL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)  # Enable CORS for all routes


# Define the Property Model
class Property(db.Model):
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
            "description": self.description
        }


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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensures tables exist before running
    app.run(debug=True)


