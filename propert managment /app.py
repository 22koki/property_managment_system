from flask import Flask, render_template, request
from datetime import datetime

app = Flask(__name__)

# Dummy database (replace with a real database in production)
properties = {}
owners = {}
tenants = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_receipt', methods=['POST'])
def generate_receipt():
    tenant_name = request.form['tenant_name']
    amount_received = request.form['amount_received']
    property_name = request.form['property_name']
    month_of = request.form['month_of']
    receipt_date = datetime.now().strftime("%Y-%m-%d")

    # Create receipt
    receipt = {
        'receipt_date': receipt_date,
        'tenant_name': tenant_name,
        'amount_received': amount_received,
        'property_name': property_name,
        'month_of': month_of,
    }

    return render_template('receipt.html', receipt=receipt)

if __name__ == '__main__':
    app.run(debug=True)
