from flask import Flask, jsonify, make_response, render_template, request, redirect, url_for, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, Property, Unit, Tenant, Invoice, MaintenanceRequest, Receipt, Admin

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://127.0.0.1:5500"}}, supports_credentials=True)
CORS(app, resources={r"/properties/*": {"origins": "http://127.0.0.1:5500"}})

 # Allow requests from any origin

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

# Login and Dashboard routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.password == password:
            login_user(admin)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    properties = Property.query.all()
    tenants = Tenant.query.all()
    invoices = Invoice.query.all()
    return render_template('dashboard.html', properties=properties, tenants=tenants, invoices=invoices)

# Generate Invoice with Auto-fill
@app.route('/generate_invoice/<int:tenant_id>', methods=['POST'])
@login_required
def generate_invoice(tenant_id):
    tenant = Tenant.query.get(tenant_id)
    unit = tenant.unit
    property_ = tenant.property  # Get the associated property for the tenant

    if not unit or not property_:
        return jsonify({"success": False, "message": "No unit or property assigned to this tenant"})

    water_bill = request.json.get('water_bill')  # Use request.json for JSON data

    # Calculate the total amount
    total_amount = unit.rent_price + property_.security_fee + property_.garbage_fee + float(water_bill)

    # Create a new invoice and add it to the database
    invoice = Invoice(
        tenant_id=tenant.id,
        rent=unit.rent_price,
        security_fee=property_.security_fee,
        garbage_fee=property_.garbage_fee,
        water_bill=water_bill,
        total_amount=total_amount
    )
    db.session.add(invoice)
    db.session.commit()

    return jsonify({"success": True, "invoice": invoice.id})  # Send back the generated invoice data



    # Pass tenant, unit, and property data to the template for auto-filling
    return render_template('generate_invoice.html', tenant=tenant, unit=unit, property_=property_)


# CRUD Operations for Properties
# CRUD Operations
@app.route('/properties', methods=['GET'])
def get_properties():
    properties = Property.query.all()
    return jsonify([
        {
            'id': prop.id,
            'name': prop.name,
            'owner': prop.owner,
            'location': prop.location,
            'property_type': prop.property_type,
            'price': prop.price,
            'description': prop.description,
            'available_units': Unit.query.filter_by(property_id=prop.id).count()
        }
        for prop in properties
    ])

@app.route('/properties', methods=['POST'])
def add_property():
    data = request.get_json()
    new_property = Property(
        name=data['name'],
        owner=data['owner'],
        location=data['location'],
        property_type=data['property_type'],
        price=data['price'],
        description=data.get('description', ''),
        security_fee=data.get('security_fee', 500),
        garbage_fee=data.get('garbage_fee', 200)
    )
    db.session.add(new_property)
    db.session.commit()
    return jsonify({'message': 'Property added successfully', 'id': new_property.id}), 201

@app.route('/properties/<int:property_id>', methods=['GET'])
def get_property(property_id):
    property = Property.query.get_or_404(property_id)
    return jsonify({
        'id': property.id,
        'name': property.name,
        'owner': property.owner,
        'location': property.location,
        'property_type': property.property_type,
        'price': property.price,
        'description': property.description,
        'available_units': Unit.query.filter_by(property_id=property.id).count()
    })

@app.route('/properties/<int:property_id>', methods=['PUT'])
def update_property(property_id):
    property = Property.query.get_or_404(property_id)
    data = request.get_json()

    property.name = data['name']
    property.owner = data['owner']
    property.location = data['location']
    property.property_type = data['property_type']
    property.price = data['price']
    property.description = data.get('description', property.description)
    property.security_fee = data.get('security_fee', property.security_fee)
    property.garbage_fee = data.get('garbage_fee', property.garbage_fee)

    db.session.commit()
    return jsonify({'message': 'Property updated successfully'}), 200
@app.route('/properties/<int:property_id>', methods=['DELETE', 'OPTIONS'])
def delete_property(property_id):
    if request.method == 'OPTIONS':
        # For handling CORS preflight
        return '', 200

    property_to_delete = Property.query.get_or_404(property_id)
    
    # ✅ Actually delete the property
    db.session.delete(property_to_delete)
    db.session.commit()
    
    return {'message': f'Property {property_id} deleted successfully'}, 200

# CRUD Operations for Units
@app.route('/units', methods=['POST'])
def add_unit():
    data = request.get_json()
    if not data or 'unit_no' not in data:
        return jsonify({"error": "Missing unit_no"}), 400

    if 'property_id' not in data:
        return jsonify({"error": "Missing property_id"}), 400

    rent_price = float(str(data.get('rent_price', 0)).replace(',', ''))
    unit = Unit(
        unit_no=data['unit_no'],
        rent_price=rent_price,
        description=data.get('description', ''),
        available=True,
        property_id=data['property_id']
    )
    db.session.add(unit)
    db.session.commit()
    return jsonify({'message': 'Unit added successfully'}), 201

@app.route('/units/<int:unit_id>', methods=['PUT'])
def update_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    data = request.get_json()
    unit.unit_no = data.get('unit_no', unit.unit_no)
    unit.rent_price = data.get('rent_price', unit.rent_price)
    unit.description = data.get('description', unit.description)
    unit.available = data.get('available', unit.available)
    db.session.commit()
    return jsonify({'message': 'Unit updated successfully'})

@app.route('/units/<int:unit_id>', methods=['DELETE'])
def delete_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    db.session.delete(unit)
    db.session.commit()
    return jsonify({'message': 'Unit deleted successfully'})
@app.route('/units', methods=['GET'])
def get_all_units():
    units = Unit.query.all()
    units_data = [
        {
            'id': unit.id,
            'unit_no': unit.unit_no,
            'rent_price': unit.rent_price,
            'description': unit.description or 'No description provided',
            'available': unit.available,
            'property_id': unit.property_id
        }
        for unit in units
    ]
    return jsonify(units_data)
@app.route('/properties/<property_id>/available_units')
def get_available_units(property_id):
    units = Unit.query.filter_by(property_id=property_id, available=True).all()
    units_data = [
        {
            'id': unit.id,
            'unit_no': unit.unit_no,
            'rent_price': unit.rent_price,
            'description': unit.description or 'No description provided',
            'available': unit.available
        }
        for unit in units
    ]
    return jsonify(units_data)
@app.route('/units/<int:unit_id>/occupy', methods=['POST'])
def occupy_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    if not unit.available:
        return jsonify({"error": "Unit is already occupied"}), 400

    tenant_id = request.json.get('tenant_id')
    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({"error": "Invalid tenant ID"}), 400

    unit.available = False
    unit.tenant_id = tenant_id  # Assign tenant to the unit

    db.session.commit()
    return jsonify({"message": "Unit marked as occupied"}), 200
# Add Tenant
@app.route('/tenants', methods=['POST'])
def add_tenant():
    data = request.get_json()

    unit = Unit.query.filter_by(unit_no=data['unit_no'], property_id=data['property_id']).first()
    property = Property.query.get(data['property_id'])

    if unit is None or property is None:
        return jsonify({"error": "Invalid unit or property ID"}), 400

    tenant = Tenant(
        name=data['name'],
        email=data['email'],
        phone_no=data['phone_no'],
        property_id=property.id,
        unit=unit
    )
    db.session.add(tenant)

    # Mark unit as occupied
    unit.available = False
    unit.tenant_id = tenant.id  # assuming your Unit model has tenant_id

    db.session.commit()
    return jsonify({"message": "Tenant added successfully"}), 201

# Get All Tenants
@app.route('/tenants', methods=['GET'])
def get_tenants():
    tenants = Tenant.query.all()
    tenants_data = []
    for tenant in tenants:
        tenant_info = {
            "id": tenant.id,
            "name": tenant.name,
            "email": tenant.email,
            "phone_no": tenant.phone_no,
            "unit": tenant.unit.unit_no if tenant.unit else None,
            "property": tenant.property.name if tenant.property else None  # ✅ Accessing property name
        }
        tenants_data.append(tenant_info)
    return jsonify(tenants_data)


# Get Tenant by Name (for autofill)
@app.route('/tenant_by_name/<tenant_name>', methods=['GET'])
def get_tenant_by_name(tenant_name):
    tenant = Tenant.query.filter_by(name=tenant_name).first()
    if tenant:
        unit = tenant.unit
        property = tenant.property
        return jsonify({
            'tenant_name': tenant.name,
            'tenant_email': tenant.email,
            'tenant_phone': tenant.phone_no,
            'unit_no': unit.unit_no if unit else None,
            'property_name': property.name if property else None,
            'property_location': property.location if property else None,
            'rent_price': unit.rent_price if unit else 0,
            'security_fee': property.security_fee if property else 0,
            'garbage_fee': property.garbage_fee if property else 0
        })
    else:
        return jsonify({'error': 'Tenant not found'}), 404

# Vacate Unit by unit_no
@app.route('/units/<unit_no>/vacate', methods=['POST'])
def vacate_unit(unit_no):
    unit = Unit.query.filter_by(unit_no=unit_no).first()
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    if unit.available:
        return jsonify({"error": "Unit is already available"}), 400

    unit.available = True
    unit.tenant_id = None

    db.session.commit()
    return jsonify({"message": "Unit marked as available"}), 200

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
