from flask import Flask, jsonify, make_response, render_template, request, redirect, url_for, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Import CO
from flask_cors import cross_origin
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, Property, Unit, Tenant, Invoice, MaintenanceRequest, Receipt, Admin

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow requests from any origin
  # Enable CORS for all routes
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)  # ✅ Keep only one instance of db.init_app(app)
migrate = Migrate(app, db)  # ✅ Move this after db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/generate_invoice/<int:tenant_id>')
@login_required
def generate_invoice(tenant_id):
    tenant = Tenant.query.get(tenant_id)
    unit = tenant.unit
    if not unit:
        flash('No unit assigned to this tenant', 'danger')
        return redirect(url_for('dashboard'))

    water_bill = request.args.get('water_bill', 0, type=float)
    total_amount = unit.rent_price + tenant.property.security_fee + tenant.property.garbage_fee + water_bill

    invoice = Invoice(tenant_id=tenant.id, rent=unit.rent_price, security_fee=tenant.property.security_fee,
                      garbage_fee=tenant.property.garbage_fee, water_bill=water_bill, total_amount=total_amount)
    db.session.add(invoice)
    db.session.commit()
    flash('Invoice generated successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/invoice_pdf/<int:invoice_id>')
@login_required
def invoice_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    rendered_html = render_template('invoice_pdf.html', invoice=invoice)
    pdf = HTML(string=rendered_html).write_pdf()
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=invoice_{invoice.id}.pdf'
    return response

# ➤ Add a new property
@app.route('/properties', methods=['GET', 'POST'])
def properties():
    if request.method == 'POST':
        data = request.get_json()
        new_property = Property(
            name=data['name'],
            owner=data['owner'],
            location=data['location'],
            property_type=data['property_type'],
            price=data['price'],
            description=data.get('description', ''),
            security_fee=data.get('security_fee', 500),
            garbage_fee=data.get('garbage_fee', 200),
            bedrooms=data.get('bedrooms', 0),  # Ensure bedrooms exist
            size=data.get('size', "N/A")  # Ensure size exists
        )
        db.session.add(new_property)
        db.session.commit()
        return jsonify({'message': 'Property added successfully'}), 201

    elif request.method == 'GET':
        properties = Property.query.all()
        return jsonify([
            {
                'property_id': prop.id,
                'name': prop.name,
                'owner': prop.owner,
                'location': prop.location,
                'property_type': prop.property_type,
                'price': prop.price,
                'description': prop.description,
                'available_units': Unit.query.filter_by(property_id=prop.id, available=True).count()
            }
            for prop in properties
        ])

# ➤ Update an existing property
@app.route('/properties/<int:property_id>', methods=['PUT'])
def update_property(property_id):
    property = Property.query.get_or_404(property_id)
    data = request.get_json()

    property.name = data['name']
    property.owner = data['owner']
    property.location = data['location']
    property.property_type = data['property_type']
    property.price = data['price']
    property.description = data.get('description', '')
    property.security_fee = data.get('security_fee', 500)
    property.garbage_fee = data.get('garbage_fee', 200)

    db.session.commit()
    return jsonify({'message': 'Property updated successfully'})
@app.route('/units', methods=['POST'])
def add_unit():
    try:
        data = request.get_json()
        print("Received Data:", data)  # Debugging output

        if not data or 'unit_no' not in data:
            return jsonify({"error": "Missing unit_no"}), 400

        if 'property_id' not in data:
            return jsonify({"error": "Missing property_id"}), 400

        # Convert rent_price to float and remove commas
        rent_price = float(str(data.get('rent_price', 0)).replace(',', ''))

        # Correct field names to match your database model
        unit = Unit(
            unit_no=data['unit_no'],  # ✅ Use unit_no instead of unit_number
            rent_price=rent_price,
            description=data.get('description', ''),
            available=bool(data.get('available', True)),
            property_id=data['property_id']
        )

        db.session.add(unit)
        db.session.commit()

        return jsonify({'message': 'Unit added successfully'}), 201

    except Exception as e:
        print("Error:", str(e))  # Debugging
        return jsonify({"error": str(e)}), 500


@app.route('/properties/<int:property_id>/available_units', methods=['GET'])
@cross_origin()
def get_available_units(property_id):
    units = Unit.query.filter(Unit.property_id == property_id, Unit.available == True).all()
    
    return jsonify([
        {
            'unit_id': unit.id,
            'unit_no': unit.unit_no,
            'rent_price': unit.rent_price,
            'description': unit.description or "N/A"
        }
        for unit in units
    ])
@app.route('/units/<int:id>', methods=['PUT'])
def update_unit(id):
    unit_to_update = Unit.query.get(id)  # Fetch from the database
    
    if not unit_to_update:
        return jsonify({"message": "Unit not found"}), 404

    # Get data from the request body
    data = request.get_json()

    # Update the unit fields
    unit_to_update.unit_no = data.get('unit_no', unit_to_update.unit_no)
    unit_to_update.rent_price = data.get('rent_price', unit_to_update.rent_price)
    unit_to_update.available = data.get('available', unit_to_update.available)
    unit_to_update.description = data.get('description', unit_to_update.description)

    db.session.commit()

    return jsonify({"message": "Unit updated successfully", "unit": {
        "unit_id": unit_to_update.id,
        "unit_no": unit_to_update.unit_no,
        "rent_price": unit_to_update.rent_price,
        "available": unit_to_update.available,
        "description": unit_to_update.description
    }}), 200




@app.route('/units/<int:unit_id>', methods=['DELETE'])
@cross_origin()
def delete_unit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    db.session.delete(unit)
    db.session.commit()
    return jsonify({'message': 'Unit deleted successfully'}), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
