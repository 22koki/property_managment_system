from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///properties.db'  # Use your preferred database

app.config['SECRET_KEY'] = 'your_secret_key'
# Serve static files from the 'static' directory automatically
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    properties = db.relationship('Property', backref='owner', lazy=True)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=False)
    units = db.relationship('Unit', backref='property', lazy=True)
    billings = db.relationship('Billing', backref='related_property', lazy=True)

class Unit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_number = db.Column(db.String(50), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    tenants = db.relationship('Tenant', backref='unit', lazy=True)

class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False)
    billings = db.relationship('Billing', backref='related_tenant', lazy=True)

class Billing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    amount_due = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    is_paid = db.Column(db.Boolean, default=False)

    tenant = db.relationship('Tenant', backref='tenant_billings')
    property = db.relationship('Property', backref='billing_records')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    billing_id = db.Column(db.Integer, db.ForeignKey('billing.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)

    billing = db.relationship('Billing', backref='payments')

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    description = db.Column(db.String(250), nullable=False)
    request_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), default='Pending')  # e.g., Pending, In Progress, Completed

    tenant = db.relationship('Tenant', backref='maintenance_requests')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):  # Check hashed password
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))

        flash('Login failed. Check your username and password.', 'danger')
        
    return render_template('login.html')  # Ensure you have this template created

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate input
        if not username or not password:
            flash('Username and password are required!', 'danger')
            return redirect(url_for('register'))

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        # Hash the password before storing
        hashed_password = generate_password_hash(password)

        # Create a new user
        new_user = User(username=username, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()  # Rollback if there is an error
            print(f'Error during registration: {e}')  # Log the error
            flash('Internal Server Error! Please try again.', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')

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
    billing.is_paid = True  # Update the billing status to 'Paid'

    # Optionally add a payment record
    payment = Payment(billing_id=bill_id, amount_paid=billing.amount_due)
    db.session.add(payment)
    db.session.commit()
    flash('Payment recorded successfully!', 'success')
    return redirect(url_for('index'))
@app.route('/view_properties', methods=['GET'])
@login_required
def view_properties():
    properties = Property.query.all()  # Fetch all properties from the database
    return render_template('view_properties.html', properties=properties)  # Ensure this template exists


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
