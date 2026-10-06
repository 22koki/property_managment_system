import os

from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_migrate import Migrate
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import db, Property, Unit, Tenant, Invoice, MaintenanceRequest, Receipt, Admin

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me-before-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Allow the legacy static frontend and local React development servers.
CORS(
    app,
    resources={r"/*": {"origins": [
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]}},
    supports_credentials=True,
)

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))


def verify_admin_password(admin, password):
    """Verify modern password hashes while upgrading legacy plaintext passwords."""
    stored = admin.password or ""
    is_hash = stored.startswith(("pbkdf2:", "scrypt:"))

    if is_hash:
        return check_password_hash(stored, password)

    if stored == password:
        admin.password = generate_password_hash(password)
        db.session.commit()
        return True

    return False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(username=username).first()

        if admin and verify_admin_password(admin, password):
            login_user(admin)
            return redirect(url_for("dashboard"))

        flash("Invalid credentials", "danger")

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "properties": Property.query.count(),
        "tenants": Tenant.query.count(),
        "pending_invoices": Invoice.query.filter(Invoice.status != "Paid").count(),
        "maintenance": MaintenanceRequest.query.filter(MaintenanceRequest.status != "Completed").count(),
        "available_units": Unit.query.filter_by(available=True).count(),
        "occupied_units": Unit.query.filter_by(available=False).count(),
    }

    recent_invoices = Invoice.query.order_by(Invoice.id.desc()).limit(5).all()
    recent_maintenance = MaintenanceRequest.query.order_by(MaintenanceRequest.id.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_invoices=recent_invoices,
        recent_maintenance=recent_maintenance,
    )


# Page routes for the legacy Jinja UI.
@app.route("/properties-page")
@login_required
def properties_page():
    return render_template("view_properties.html")


@app.route("/add-property")
@login_required
def add_property_page():
    return render_template("add_propert.html")


@app.route("/add-unit")
@login_required
def add_unit_page():
    return render_template("add_unit.html")


@app.route("/add-tenant")
@login_required
def add_tenant_page():
    return render_template("add_tenant.html")


@app.route("/tenants-page")
@login_required
def tenants_page():
    return render_template("view_tenants.html")


@app.route("/invoice")
@login_required
def invoice_page():
    return render_template("invoice.html")


@app.route("/receipts-page")
@login_required
def receipts_page():
    return render_template("receipts.html")


@app.route("/statement")
@login_required
def statement_page():
    return render_template("statement.html")


@app.route("/bills")
@login_required
def bills_page():
    return render_template("view_bills.html")


@app.route("/maintenance")
@login_required
def maintenance_page():
    return render_template("maintenance_requests.html")


@app.route("/generate_invoice/<int:tenant_id>", methods=["POST"])
@login_required
def generate_invoice(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)

    if not tenant:
        return jsonify({"success": False, "message": "Tenant not found"}), 404

    unit = tenant.unit
    property_ = tenant.property

    if not unit or not property_:
        return jsonify({
            "success": False,
            "message": "No unit or property assigned to this tenant",
        }), 400

    payload = request.get_json(silent=True) or {}
    try:
        water_bill = float(payload.get("water_bill", 0) or 0)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid water bill"}), 400

    total_amount = (
        float(unit.rent_price)
        + float(property_.security_fee)
        + float(property_.garbage_fee)
        + water_bill
    )

    invoice = Invoice(
        tenant_id=tenant.id,
        rent=unit.rent_price,
        security_fee=property_.security_fee,
        garbage_fee=property_.garbage_fee,
        water_bill=water_bill,
        total_amount=total_amount,
        status="Pending",
    )
    db.session.add(invoice)
    db.session.commit()

    return jsonify({
        "success": True,
        "invoice": {
            "id": invoice.id,
            "tenant_name": tenant.name,
            "tenant_email": tenant.email,
            "water_bill": water_bill,
            "rent": invoice.rent,
            "security_fee": invoice.security_fee,
            "garbage_fee": invoice.garbage_fee,
            "total_amount": invoice.total_amount,
            "status": invoice.status,
        },
    }), 201


# CRUD Operations for Properties
@app.route("/properties", methods=["GET"])
def get_properties():
    properties = Property.query.all()
    return jsonify([
        {
            "id": prop.id,
            "name": prop.name,
            "owner": prop.owner,
            "location": prop.location,
            "property_type": prop.property_type,
            "price": prop.price,
            "description": prop.description,
            "security_fee": prop.security_fee,
            "garbage_fee": prop.garbage_fee,
            "available_units": Unit.query.filter_by(property_id=prop.id, available=True).count(),
            "total_units": Unit.query.filter_by(property_id=prop.id).count(),
        }
        for prop in properties
    ])


@app.route("/properties", methods=["POST"])
@login_required
def add_property():
    data = request.get_json(silent=True) or {}
    required = ["name", "owner", "location", "property_type", "price"]
    missing = [field for field in required if data.get(field) in (None, "")]

    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    new_property = Property(
        name=data["name"],
        owner=data["owner"],
        location=data["location"],
        property_type=data["property_type"],
        price=float(data["price"]),
        description=data.get("description", ""),
        security_fee=float(data.get("security_fee", 500) or 0),
        garbage_fee=float(data.get("garbage_fee", 200) or 0),
    )
    db.session.add(new_property)
    db.session.commit()
    return jsonify({"message": "Property added successfully", "id": new_property.id}), 201


@app.route("/properties/<int:property_id>", methods=["GET"])
def get_property(property_id):
    property_ = db.session.get(Property, property_id)
    if not property_:
        return jsonify({"error": "Property not found"}), 404

    return jsonify({
        "id": property_.id,
        "name": property_.name,
        "owner": property_.owner,
        "location": property_.location,
        "property_type": property_.property_type,
        "price": property_.price,
        "description": property_.description,
        "security_fee": property_.security_fee,
        "garbage_fee": property_.garbage_fee,
        "available_units": Unit.query.filter_by(property_id=property_.id, available=True).count(),
        "total_units": Unit.query.filter_by(property_id=property_.id).count(),
    })


@app.route("/properties/<int:property_id>", methods=["PUT"])
@login_required
def update_property(property_id):
    property_ = db.session.get(Property, property_id)
    if not property_:
        return jsonify({"error": "Property not found"}), 404

    data = request.get_json(silent=True) or {}
    for field in ["name", "owner", "location", "property_type", "description"]:
        if field in data:
            setattr(property_, field, data[field])

    for field in ["price", "security_fee", "garbage_fee"]:
        if field in data:
            setattr(property_, field, float(data[field]))

    db.session.commit()
    return jsonify({"message": "Property updated successfully"})


@app.route("/properties/<int:property_id>", methods=["DELETE", "OPTIONS"])
@login_required
def delete_property(property_id):
    if request.method == "OPTIONS":
        return "", 200

    property_to_delete = db.session.get(Property, property_id)
    if not property_to_delete:
        return jsonify({"error": "Property not found"}), 404

    db.session.delete(property_to_delete)
    db.session.commit()
    return jsonify({"message": f"Property {property_id} deleted successfully"})


# CRUD Operations for Units
@app.route("/units", methods=["POST"])
@login_required
def add_unit():
    data = request.get_json(silent=True) or {}

    if not data.get("unit_no"):
        return jsonify({"error": "Missing unit_no"}), 400
    if not data.get("property_id"):
        return jsonify({"error": "Missing property_id"}), 400

    property_ = db.session.get(Property, int(data["property_id"]))
    if not property_:
        return jsonify({"error": "Property not found"}), 404

    if Unit.query.filter_by(unit_no=data["unit_no"]).first():
        return jsonify({"error": "Unit number already exists"}), 409

    rent_price = float(str(data.get("rent_price", 0)).replace(",", ""))
    unit = Unit(
        unit_no=data["unit_no"],
        rent_price=rent_price,
        description=data.get("description", ""),
        available=True,
        property_id=property_.id,
    )
    db.session.add(unit)
    db.session.commit()
    return jsonify({"message": "Unit added successfully", "id": unit.id}), 201


@app.route("/units/<int:unit_id>", methods=["PUT"])
@login_required
def update_unit(unit_id):
    unit = db.session.get(Unit, unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    data = request.get_json(silent=True) or {}
    unit.unit_no = data.get("unit_no", unit.unit_no)
    unit.rent_price = float(data.get("rent_price", unit.rent_price))
    unit.description = data.get("description", unit.description)
    unit.available = data.get("available", unit.available)
    db.session.commit()
    return jsonify({"message": "Unit updated successfully"})


@app.route("/units/<int:unit_id>", methods=["DELETE"])
@login_required
def delete_unit(unit_id):
    unit = db.session.get(Unit, unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    db.session.delete(unit)
    db.session.commit()
    return jsonify({"message": "Unit deleted successfully"})


@app.route("/units", methods=["GET"])
def get_all_units():
    units = Unit.query.all()
    return jsonify([
        {
            "id": unit.id,
            "unit_no": unit.unit_no,
            "rent_price": unit.rent_price,
            "description": unit.description or "No description provided",
            "available": unit.available,
            "property_id": unit.property_id,
            "tenant_id": unit.tenant_id,
        }
        for unit in units
    ])


@app.route("/properties/<int:property_id>/available_units")
def get_available_units(property_id):
    units = Unit.query.filter_by(property_id=property_id, available=True).all()
    return jsonify([
        {
            "id": unit.id,
            "unit_no": unit.unit_no,
            "rent_price": unit.rent_price,
            "description": unit.description or "No description provided",
            "available": unit.available,
        }
        for unit in units
    ])


@app.route("/units/<int:unit_id>/occupy", methods=["POST"])
@login_required
def occupy_unit(unit_id):
    unit = db.session.get(Unit, unit_id)
    if not unit:
        return jsonify({"error": "Unit not found"}), 404
    if not unit.available:
        return jsonify({"error": "Unit is already occupied"}), 400

    payload = request.get_json(silent=True) or {}
    tenant = db.session.get(Tenant, payload.get("tenant_id"))
    if not tenant:
        return jsonify({"error": "Invalid tenant ID"}), 400

    if tenant.unit and tenant.unit.id != unit.id:
        return jsonify({"error": "Tenant is already assigned to another unit"}), 409

    unit.available = False
    unit.tenant_id = tenant.id
    tenant.property_id = unit.property_id
    db.session.commit()
    return jsonify({"message": "Unit marked as occupied"})


# Tenant operations
@app.route("/tenants", methods=["POST"])
@login_required
def add_tenant():
    data = request.get_json(silent=True) or {}
    required = ["name", "email", "phone_no", "unit_no", "property_id"]
    missing = [field for field in required if data.get(field) in (None, "")]

    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    unit = Unit.query.filter_by(
        unit_no=data["unit_no"],
        property_id=int(data["property_id"]),
    ).first()
    property_ = db.session.get(Property, int(data["property_id"]))

    if unit is None or property_ is None:
        return jsonify({"error": "Invalid unit or property ID"}), 400
    if not unit.available:
        return jsonify({"error": "Selected unit is already occupied"}), 409
    if Tenant.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "A tenant with this email already exists"}), 409

    tenant = Tenant(
        name=data["name"],
        email=data["email"],
        phone_no=data["phone_no"],
        property_id=property_.id,
    )
    db.session.add(tenant)
    db.session.flush()

    unit.available = False
    unit.tenant_id = tenant.id
    db.session.commit()

    return jsonify({"message": "Tenant added successfully", "id": tenant.id}), 201


@app.route("/tenants", methods=["GET"])
def get_tenants():
    tenants = Tenant.query.all()
    return jsonify([
        {
            "id": tenant.id,
            "name": tenant.name,
            "email": tenant.email,
            "phone_no": tenant.phone_no,
            "unit": tenant.unit.unit_no if tenant.unit else None,
            "unit_id": tenant.unit.id if tenant.unit else None,
            "property": tenant.property.name if tenant.property else None,
            "property_id": tenant.property_id,
        }
        for tenant in tenants
    ])


@app.route("/tenant_by_name/<tenant_name>", methods=["GET"])
def get_tenant_by_name(tenant_name):
    tenant = Tenant.query.filter_by(name=tenant_name).first()
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    unit = tenant.unit
    property_ = tenant.property
    return jsonify({
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "tenant_email": tenant.email,
        "tenant_phone": tenant.phone_no,
        "unit_no": unit.unit_no if unit else None,
        "property_name": property_.name if property_ else None,
        "property_location": property_.location if property_ else None,
        "rent_price": unit.rent_price if unit else 0,
        "security_fee": property_.security_fee if property_ else 0,
        "garbage_fee": property_.garbage_fee if property_ else 0,
    })


@app.route("/units/<unit_no>/vacate", methods=["POST"])
@login_required
def vacate_unit(unit_no):
    unit = Unit.query.filter_by(unit_no=unit_no).first()
    if not unit:
        return jsonify({"error": "Unit not found"}), 404
    if unit.available:
        return jsonify({"error": "Unit is already available"}), 400

    unit.available = True
    unit.tenant_id = None
    db.session.commit()
    return jsonify({"message": "Unit marked as available"})


# Invoice / receipt operations
@app.route("/invoices", methods=["GET"])
@login_required
def get_invoices():
    invoices = Invoice.query.order_by(Invoice.id.desc()).all()
    return jsonify([
        {
            "id": invoice.id,
            "tenant_id": invoice.tenant_id,
            "rent": invoice.rent,
            "security_fee": invoice.security_fee,
            "garbage_fee": invoice.garbage_fee,
            "water_bill": invoice.water_bill,
            "total_amount": invoice.total_amount,
            "status": invoice.status,
        }
        for invoice in invoices
    ])


@app.route("/receipts", methods=["GET"])
@login_required
def get_receipts():
    receipts = Receipt.query.order_by(Receipt.id.desc()).all()
    return jsonify([
        {
            "id": receipt.id,
            "invoice_id": receipt.invoice_id,
            "amount_paid": receipt.amount_paid,
            "balance_due": receipt.balance_due,
        }
        for receipt in receipts
    ])


@app.route("/receipts", methods=["POST"])
@login_required
def create_receipt():
    data = request.get_json(silent=True) or {}
    invoice = db.session.get(Invoice, data.get("invoice_id"))

    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    try:
        amount_paid = float(data.get("amount_paid", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid payment amount"}), 400

    if amount_paid <= 0:
        return jsonify({"error": "Payment amount must be greater than zero"}), 400

    already_paid = db.session.query(db.func.coalesce(db.func.sum(Receipt.amount_paid), 0)).filter(
        Receipt.invoice_id == invoice.id
    ).scalar()
    balance_before = max(float(invoice.total_amount) - float(already_paid), 0)

    if amount_paid > balance_before:
        return jsonify({"error": "Payment exceeds invoice balance"}), 400

    balance_due = max(balance_before - amount_paid, 0)
    receipt = Receipt(
        invoice_id=invoice.id,
        amount_paid=amount_paid,
        balance_due=balance_due,
    )
    db.session.add(receipt)

    invoice.status = "Paid" if balance_due == 0 else "Partially Paid"
    db.session.commit()

    return jsonify({
        "message": "Receipt recorded successfully",
        "receipt": {
            "id": receipt.id,
            "invoice_id": receipt.invoice_id,
            "amount_paid": receipt.amount_paid,
            "balance_due": receipt.balance_due,
            "invoice_status": invoice.status,
        },
    }), 201


# Maintenance operations
@app.route("/maintenance_requests", methods=["GET"])
@login_required
def get_maintenance_requests():
    requests_ = MaintenanceRequest.query.order_by(MaintenanceRequest.id.desc()).all()
    return jsonify([
        {
            "id": item.id,
            "tenant_id": item.tenant_id,
            "description": item.description,
            "status": item.status,
        }
        for item in requests_
    ])


@app.route("/maintenance_requests", methods=["POST"])
@login_required
def create_maintenance_request():
    data = request.get_json(silent=True) or {}
    tenant = db.session.get(Tenant, data.get("tenant_id"))

    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404
    if not data.get("description"):
        return jsonify({"error": "Description is required"}), 400

    maintenance = MaintenanceRequest(
        tenant_id=tenant.id,
        description=data["description"],
        status=data.get("status", "Pending"),
    )
    db.session.add(maintenance)
    db.session.commit()

    return jsonify({
        "message": "Maintenance request created",
        "id": maintenance.id,
    }), 201


@app.route("/maintenance_requests/<int:request_id>", methods=["PUT"])
@login_required
def update_maintenance_request(request_id):
    maintenance = db.session.get(MaintenanceRequest, request_id)
    if not maintenance:
        return jsonify({"error": "Maintenance request not found"}), 404

    data = request.get_json(silent=True) or {}
    if "description" in data:
        maintenance.description = data["description"]
    if "status" in data:
        maintenance.status = data["status"]

    db.session.commit()
    return jsonify({"message": "Maintenance request updated"})


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
