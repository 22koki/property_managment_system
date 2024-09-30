from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///properties.db'  # Use your preferred database
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)

class Billing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    amount_due = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    is_paid = db.Column(db.Boolean, default=False)

    tenant = db.relationship('Tenant', backref='billings')
    property = db.relationship('Property', backref='billings')

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    description = db.Column(db.String(250), nullable=False)
    request_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default='Pending')  # e.g., Pending, In Progress, Completed

    tenant = db.relationship('Tenant', backref='maintenance_requests')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    properties = Property.query.all()
    return render_template('index.html', properties=properties)

@app.route('/generate_invoice/<int:billing_id>', methods=['GET'])
@login_required
def generate_invoice(billing_id):
    billing = Billing.query.get(billing_id)
    if not billing:
        return "Billing record not found", 404

    # Create a PDF invoice
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, f"Invoice for Tenant: {billing.tenant.name}")
    p.drawString(100, 730, f"Property: {billing.property.name}")
    p.drawString(100, 710, f"Amount Due: KES {billing.amount_due}")
    p.drawString(100, 690, f"Due Date: {billing.due_date}")
    p.drawString(100, 670, f"Status: {'Paid' if billing.is_paid else 'Unpaid'}")
    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='invoice.pdf', mimetype='application/pdf')
@app.route('/add_property', methods=['GET', 'POST'])
@login_required
def add_property():
    if request.method == 'POST':
        property_name = request.form['property_name']
        owner_id = request.form['owner_id']
        new_property = Property(name=property_name, owner_id=owner_id)
        db.session.add(new_property)
        db.session.commit()
        flash('Property added successfully!', 'success')
        return redirect(url_for('index'))

    owners = Owner.query.all()
    return render_template('add_property.html', owners=owners)

@app.route('/add_unit', methods=['GET', 'POST'])
@login_required
def add_unit():
    if request.method == 'POST':
        unit_number = request.form['unit_number']
        property_id = request.form['property_id']
        new_unit = Unit(unit_number=unit_number, property_id=property_id)
        db.session.add(new_unit)
        db.session.commit()
        flash('Unit added successfully!', 'success')
        return redirect(url_for('index'))

    properties = Property.query.all()
    return render_template('add_unit.html', properties=properties)

@app.route('/add_tenant', methods=['GET', 'POST'])
@login_required
def add_tenant():
    if request.method == 'POST':
        tenant_name = request.form['tenant_name']
        unit_id = request.form['unit_id']
        new_tenant = Tenant(name=tenant_name, unit_id=unit_id)
        db.session.add(new_tenant)
        db.session.commit()
        flash('Tenant added successfully!', 'success')
        return redirect(url_for('index'))

    units = Unit.query.all()
    return render_template('add_tenant.html', units=units)




@app.route('/submit_maintenance', methods=['POST'])
@login_required
def submit_maintenance():
    description = request.form['description']
    new_request = Maintenance(tenant_id=current_user.id, description=description, request_date=datetime.now())
    db.session.add(new_request)
    db.session.commit()
    flash('Maintenance request submitted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/maintenance_requests', methods=['GET'])
@login_required
def maintenance_requests():
    requests = Maintenance.query.filter_by(tenant_id=current_user.id).all()
    return render_template('maintenance_requests.html', requests=requests)

@app.route('/pay_bill/<int:bill_id>', methods=['POST'])
@login_required
def pay_bill(bill_id):
    billing = Billing.query.get_or_404(bill_id)
    billing.payment_status = 'Paid'

    # Optionally add a payment record
    payment = Payment(billing_id=bill_id, amount_paid=billing.amount_due)
    db.session.add(payment)
    db.session.commit()
    flash('Payment recorded successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/view_bills/<int:tenant_id>', methods=['GET'])
@login_required
def view_bills(tenant_id):
    bills = Billing.query.filter_by(tenant_id=tenant_id).all()
    return render_template('view_bills.html', bills=bills)


#view properties
@app.route('/view_properties', methods=['GET'])
@login_required
def view_properties():
    properties = Property.query.all()  # Fetch all properties along with units and tenants
    return render_template('view_properties.html', properties=properties)


if __name__ == '__main__':
    db.create_all()  # Create the database tables
    app.run(debug=True)
