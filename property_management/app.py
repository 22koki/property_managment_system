import os
import calendar
import smtplib
from email.message import EmailMessage

from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from datetime import datetime, date, timedelta
from flask_migrate import Migrate
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import db, Property, Unit, Tenant, Tenancy, Invoice, MaintenanceRequest, Receipt, Admin

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


def add_months(value, months=1):
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def send_invoice_email(invoice):
    """Send an invoice email when SMTP environment variables are configured."""
    tenant = invoice.tenant
    if not tenant or not tenant.email:
        return False

    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", username)
    port = int(os.getenv("SMTP_PORT", "587"))

    if not all([host, username, password, sender]):
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Zuripo Invoice #{invoice.id} - {invoice.billing_period or 'Rent'}"
    msg["From"] = sender
    msg["To"] = tenant.email
    msg.set_content(
        f"Hello {tenant.name},\n\n"
        f"Your {invoice.invoice_type.lower()} invoice has been generated.\n"
        f"Amount due: KSh {invoice.total_amount:,.2f}\n"
        f"Due date: {invoice.due_date.isoformat() if invoice.due_date else 'Not set'}\n"
        f"Invoice number: {invoice.id}\n\n"
        "Thank you,\nZuripo Property Specialists"
    )

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        app.logger.warning("Invoice email failed for invoice %s: %s", invoice.id, exc)
        return False


def create_tenancy_invoice(tenancy, invoice_date=None, include_security=False, water_bill=0, invoice_type="Monthly Rent"):
    invoice_date = invoice_date or date.today()
    tenant = tenancy.tenant
    unit = tenancy.unit
    property_ = unit.property
    billing_period = invoice_date.strftime("%Y-%m")

    existing = Invoice.query.filter_by(
        tenancy_id=tenancy.id,
        billing_period=billing_period,
        invoice_type=invoice_type,
    ).first()
    if existing:
        return existing, False

    security_fee = float(property_.security_fee or 0) if include_security else 0.0
    rent = float(unit.rent_price or 0)
    garbage = float(property_.garbage_fee or 0)
    water = float(water_bill or 0)
    due_date = invoice_date + timedelta(days=7)

    invoice = Invoice(
        tenant_id=tenant.id,
        tenancy_id=tenancy.id,
        rent=rent,
        security_fee=security_fee,
        garbage_fee=garbage,
        water_bill=water,
        total_amount=rent + security_fee + garbage + water,
        status="Pending",
        issued_at=datetime.combine(invoice_date, datetime.min.time()),
        due_date=due_date,
        billing_period=billing_period,
        invoice_type=invoice_type,
    )
    db.session.add(invoice)
    db.session.flush()
    return invoice, True


def assign_tenant_to_unit(tenant, unit, start_date=None, include_security=True):
    start_date = start_date or date.today()

    if not unit.available and unit.tenant_id != tenant.id:
        raise ValueError("Selected unit is already occupied")

    current = Tenancy.query.filter_by(tenant_id=tenant.id, active=True).first()
    if current:
        current.active = False
        current.end_date = start_date
        if current.unit:
            current.unit.available = True
            current.unit.tenant_id = None

    unit.available = False
    unit.tenant_id = tenant.id
    tenant.property_id = unit.property_id

    tenancy = Tenancy(
        tenant_id=tenant.id,
        unit_id=unit.id,
        start_date=start_date,
        active=True,
        auto_invoice=True,
        next_invoice_date=add_months(start_date, 1),
        last_invoice_date=start_date,
    )
    db.session.add(tenancy)
    db.session.flush()

    invoice, created = create_tenancy_invoice(
        tenancy,
        invoice_date=start_date,
        include_security=include_security,
        invoice_type="Move-in" if include_security else "Monthly Rent",
    )
    db.session.commit()
    if created:
        send_invoice_email(invoice)
    return tenancy, invoice


def bootstrap_missing_tenancies(today=None):
    """Create lifecycle records for occupants that pre-date the tenancy feature."""
    today = today or date.today()
    created = 0
    occupied_units = Unit.query.filter(Unit.tenant_id.isnot(None)).all()

    for unit in occupied_units:
        exists = Tenancy.query.filter_by(
            tenant_id=unit.tenant_id,
            unit_id=unit.id,
            active=True,
        ).first()
        if exists:
            continue

        db.session.add(Tenancy(
            tenant_id=unit.tenant_id,
            unit_id=unit.id,
            start_date=today,
            active=True,
            auto_invoice=True,
            last_invoice_date=today,
            next_invoice_date=add_months(today, 1),
        ))
        created += 1

    if created:
        db.session.commit()
    return created


def run_due_invoices(today=None):
    today = today or date.today()
    bootstrap_missing_tenancies(today)
    generated = []
    tenancies = Tenancy.query.filter_by(active=True, auto_invoice=True).all()

    for tenancy in tenancies:
        while tenancy.next_invoice_date and tenancy.next_invoice_date <= today:
            invoice_date = tenancy.next_invoice_date
            invoice, created = create_tenancy_invoice(
                tenancy,
                invoice_date=invoice_date,
                include_security=False,
                invoice_type="Monthly Rent",
            )
            tenancy.last_invoice_date = invoice_date
            tenancy.next_invoice_date = add_months(invoice_date, 1)
            if created:
                generated.append(invoice)

    db.session.commit()
    for invoice in generated:
        send_invoice_email(invoice)
    return generated


@app.cli.command("billing-run")
def billing_run():
    generated = run_due_invoices()
    print(f"Generated {len(generated)} invoice(s).")


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
            return redirect(url_for("workspace"))

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

    total_billed = db.session.query(db.func.coalesce(db.func.sum(Invoice.total_amount), 0)).scalar()
    total_paid = db.session.query(db.func.coalesce(db.func.sum(Receipt.amount_paid), 0)).scalar()
    stats["total_billed"] = float(total_billed or 0)
    stats["total_paid"] = float(total_paid or 0)
    stats["arrears"] = max(stats["total_billed"] - stats["total_paid"], 0)

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
    return redirect(url_for("workspace") + "#properties")


@app.route("/add-property")
@login_required
def add_property_page():
    return redirect(url_for("workspace") + "#properties")


@app.route("/add-unit")
@login_required
def add_unit_page():
    return redirect(url_for("workspace") + "#units")


@app.route("/add-tenant")
@login_required
def add_tenant_page():
    return redirect(url_for("workspace") + "#tenants")


@app.route("/tenants-page")
@login_required
def tenants_page():
    return redirect(url_for("workspace") + "#tenants")


@app.route("/invoice")
@login_required
def invoice_page():
    return redirect(url_for("workspace") + "#billing")


@app.route("/receipts-page")
@login_required
def receipts_page():
    return redirect(url_for("workspace") + "#payments")


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
    return redirect(url_for("workspace") + "#maintenance")


@app.route("/workspace")
@login_required
def workspace():
    run_due_invoices()
    return render_template("workspace.html")


@app.route("/api/summary")
@login_required
def api_summary():
    run_due_invoices()
    total_billed = float(db.session.query(db.func.coalesce(db.func.sum(Invoice.total_amount), 0)).scalar() or 0)
    total_paid = float(db.session.query(db.func.coalesce(db.func.sum(Receipt.amount_paid), 0)).scalar() or 0)
    return jsonify({
        "properties": Property.query.count(),
        "units": Unit.query.count(),
        "available_units": Unit.query.filter_by(available=True).count(),
        "occupied_units": Unit.query.filter_by(available=False).count(),
        "tenants": Tenant.query.count(),
        "open_invoices": Invoice.query.filter(Invoice.status != "Paid").count(),
        "maintenance_open": MaintenanceRequest.query.filter(MaintenanceRequest.status != "Completed").count(),
        "total_billed": total_billed,
        "total_paid": total_paid,
        "arrears": max(total_billed - total_paid, 0),
    })


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

    include_security = bool(payload.get("include_security_fee", False))
    security_fee = float(property_.security_fee or 0) if include_security else 0.0
    total_amount = (
        float(unit.rent_price)
        + security_fee
        + float(property_.garbage_fee)
        + water_bill
    )

    due_date = None
    if payload.get("due_date"):
        try:
            due_date = datetime.strptime(payload["due_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "message": "Invalid due date"}), 400

    invoice = Invoice(
        tenant_id=tenant.id,
        rent=unit.rent_price,
        security_fee=security_fee,
        garbage_fee=property_.garbage_fee,
        water_bill=water_bill,
        total_amount=total_amount,
        status="Pending",
        due_date=due_date,
        tenancy_id=next((x.id for x in tenant.tenancies if x.active), None),
        billing_period=date.today().strftime("%Y-%m"),
        invoice_type="Manual Invoice",
    )
    db.session.add(invoice)
    db.session.commit()
    email_sent = send_invoice_email(invoice)

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
            "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "email_sent": email_sent,
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

    if "unit_no" in data and data["unit_no"] != unit.unit_no:
        duplicate = Unit.query.filter(Unit.unit_no == data["unit_no"], Unit.id != unit.id).first()
        if duplicate:
            return jsonify({"error": "Unit number already exists"}), 409
        unit.unit_no = data["unit_no"]

    if "rent_price" in data:
        unit.rent_price = float(data["rent_price"])
    if "description" in data:
        unit.description = data["description"]

    if "property_id" in data and int(data["property_id"]) != unit.property_id:
        if not unit.available:
            return jsonify({"error": "Vacate the unit before moving it to another property"}), 409
        property_ = db.session.get(Property, int(data["property_id"]))
        if not property_:
            return jsonify({"error": "Property not found"}), 404
        unit.property_id = property_.id

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
            "tenant_name": unit.tenant.name if unit.tenant else None,
            "property_name": unit.property.name if unit.property else None,
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

    start_date = date.today()
    if data.get("start_date"):
        try:
            start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid move-in date"}), 400

    tenancy, invoice = assign_tenant_to_unit(
        tenant,
        unit,
        start_date=start_date,
        include_security=True,
    )

    return jsonify({
        "message": "Tenant added and assigned successfully",
        "id": tenant.id,
        "tenancy_id": tenancy.id,
        "invoice_id": invoice.id,
    }), 201


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
            "active_tenancy_id": next((x.id for x in tenant.tenancies if x.active), None),
            "move_in_date": next((x.start_date.isoformat() for x in tenant.tenancies if x.active), None),
            "next_invoice_date": next((x.next_invoice_date.isoformat() if x.next_invoice_date else None for x in tenant.tenancies if x.active), None),
            "auto_invoice": next((x.auto_invoice for x in tenant.tenancies if x.active), False),
        }
        for tenant in tenants
    ])


@app.route("/tenants/<int:tenant_id>", methods=["PUT"])
@login_required
def update_tenant(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        tenant.name = data["name"].strip()
    if "email" in data:
        existing = Tenant.query.filter(Tenant.email == data["email"], Tenant.id != tenant.id).first()
        if existing:
            return jsonify({"error": "Another tenant already uses this email"}), 409
        tenant.email = data["email"].strip()
    if "phone_no" in data:
        tenant.phone_no = data["phone_no"].strip()

    active = Tenancy.query.filter_by(tenant_id=tenant.id, active=True).first()
    if active and "auto_invoice" in data:
        active.auto_invoice = bool(data["auto_invoice"])

    db.session.commit()
    return jsonify({"message": "Tenant updated successfully"})


@app.route("/tenants/<int:tenant_id>/assign", methods=["POST"])
@login_required
def assign_tenant(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    data = request.get_json(silent=True) or {}
    unit = db.session.get(Unit, data.get("unit_id"))
    if not unit:
        return jsonify({"error": "Unit not found"}), 404

    start_date = date.today()
    if data.get("start_date"):
        try:
            start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid move date"}), 400

    try:
        tenancy, invoice = assign_tenant_to_unit(
            tenant,
            unit,
            start_date=start_date,
            include_security=bool(data.get("include_security_fee", False)),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409

    return jsonify({
        "message": "Tenant assignment updated",
        "tenancy_id": tenancy.id,
        "invoice_id": invoice.id,
    })


@app.route("/tenants/<int:tenant_id>/vacate", methods=["POST"])
@login_required
def vacate_tenant(tenant_id):
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    active = Tenancy.query.filter_by(tenant_id=tenant.id, active=True).first()
    if not active:
        return jsonify({"error": "Tenant has no active tenancy"}), 400

    data = request.get_json(silent=True) or {}
    end_date = date.today()
    if data.get("end_date"):
        try:
            end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "Invalid move-out date"}), 400

    active.active = False
    active.end_date = end_date
    active.next_invoice_date = None
    active.unit.available = True
    active.unit.tenant_id = None
    tenant.property_id = None
    db.session.commit()

    return jsonify({"message": "Tenant moved out and unit is now available"})


@app.route("/tenancies", methods=["GET"])
@login_required
def get_tenancies():
    rows = Tenancy.query.order_by(Tenancy.id.desc()).all()
    return jsonify([
        {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "tenant_name": row.tenant.name if row.tenant else None,
            "unit_id": row.unit_id,
            "unit_no": row.unit.unit_no if row.unit else None,
            "property_name": row.unit.property.name if row.unit and row.unit.property else None,
            "start_date": row.start_date.isoformat(),
            "end_date": row.end_date.isoformat() if row.end_date else None,
            "active": row.active,
            "auto_invoice": row.auto_invoice,
            "next_invoice_date": row.next_invoice_date.isoformat() if row.next_invoice_date else None,
        }
        for row in rows
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

    tenant_id = unit.tenant_id
    if tenant_id:
        active = Tenancy.query.filter_by(tenant_id=tenant_id, unit_id=unit.id, active=True).first()
        if active:
            active.active = False
            active.end_date = date.today()
            active.next_invoice_date = None
        tenant = db.session.get(Tenant, tenant_id)
        if tenant:
            tenant.property_id = None

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
            "tenant_name": invoice.tenant.name if invoice.tenant else None,
            "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "amount_paid": float(sum(r.amount_paid for r in invoice.receipts)),
            "balance_due": max(float(invoice.total_amount) - float(sum(r.amount_paid for r in invoice.receipts)), 0),
            "billing_period": invoice.billing_period,
            "invoice_type": invoice.invoice_type,
            "tenancy_id": invoice.tenancy_id,
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
            "payment_method": receipt.payment_method,
            "transaction_reference": receipt.transaction_reference,
            "created_at": receipt.created_at.isoformat() if receipt.created_at else None,
            "tenant_name": receipt.invoice.tenant.name if receipt.invoice and receipt.invoice.tenant else None,
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
        payment_method=data.get("payment_method", "Cash"),
        transaction_reference=data.get("transaction_reference"),
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
            "payment_method": receipt.payment_method,
            "transaction_reference": receipt.transaction_reference,
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
            "tenant_name": item.tenant.name if item.tenant else None,
            "property_name": item.tenant.property.name if item.tenant and item.tenant.property else None,
            "unit_no": item.tenant.unit.unit_no if item.tenant and item.tenant.unit else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
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
