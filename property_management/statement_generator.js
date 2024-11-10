function addActivityRow() {
    const row = document.createElement('div');
    row.classList.add('activity-row');
    row.innerHTML = `
        <input type="date" class="activity-date" required>
        <input type="text" class="activity-ref" placeholder="Ref" required>
        <input type="text" class="activity-desc" placeholder="Description" required>
        <input type="number" class="activity-debit" placeholder="Debit" required>
        <input type="number" class="activity-credit" placeholder="Credit" required>
    `;
    document.getElementById('activityTable').appendChild(row);
}

function generatePreview() {
    // Get input values
    const companyName = document.getElementById('companyName').value;
    const companyAddress = document.getElementById('companyAddress').value;
    const companyPhone = document.getElementById('companyPhone').value;
    const companyEmail = document.getElementById('companyEmail').value;
    const tenantName = document.getElementById('tenantName').value;
    const tenantLocation = document.getElementById('tenantLocation').value;
    const tenantPhone = document.getElementById('tenantPhone').value;
    const tenantEmail = document.getElementById('tenantEmail').value;
    const propertyLocation = document.getElementById('propertyLocation').value;
    const propertyOwner = document.getElementById('propertyOwner').value;
    const bankName = document.getElementById('bankName').value;
    const accountNumber = document.getElementById('accountNumber').value;
    const mpesaPaybill = document.getElementById('mpesaPaybill').value;
    const mpesaAccount = document.getElementById('mpesaAccount').value;

    // Create table rows for account activity
    let activityRows = '';
    document.querySelectorAll('.activity-row').forEach(row => {
        const date = row.querySelector('.activity-date').value;
        const ref = row.querySelector('.activity-ref').value;
        const desc = row.querySelector('.activity-desc').value;
        const debit = row.querySelector('.activity-debit').value;
        const credit = row.querySelector('.activity-credit').value;
        activityRows += `<tr><td>${date}</td><td>${ref}</td><td>${desc}</td><td>${debit}</td><td>${credit}</td></tr>`;
    });

    // Populate statement preview
    document.getElementById('statementPreview').innerHTML = `
        <h2>${companyName}</h2>
        <p>${companyAddress}</p>
        <p>${companyPhone}</p>
        <p>${companyEmail}</p>
        <h3>Tenant Information</h3>
        <p>${tenantName}</p>
        <p>${tenantLocation}</p>
        <p>${tenantPhone}</p>
        <p>${tenantEmail}</p>
        <h3>Property Information</h3>
        <p>${propertyLocation}</p>
        <p>${propertyOwner}</p>
        <table><tr><th>Date</th><th>Ref</th><th>Description</th><th>Debit</th><th>Credit</th></tr>${activityRows}</table>
        <h4>Please Make Payment To:</h4>
        <p>${bankName}</p><p>A/c No: ${accountNumber}</p>
        <h4>Via M-Pesa:</h4>
        <p>Paybill: ${mpesaPaybill}</p><p>Account: ${mpesaAccount}</p>
    `;
    document.getElementById('statementPreview').style.display = 'block';
}

// Convert preview to PDF
function downloadPDF() {
    const element = document.getElementById('statementPreview');
    html2pdf().from(element).save('Rental_Billing_Statement.pdf');
}
