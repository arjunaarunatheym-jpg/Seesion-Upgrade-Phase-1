/**
 * Print Invoice utility - generates printable invoice PDF
 */

export const printInvoice = (invoice, companySettings, logoUrl) => {
  const formatCurrency = (amount) => {
    return `RM ${(amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-MY', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const companyName = companySettings?.company_name || 'MDDRC SDN BHD';
  const companyAddress = companySettings?.address || '';
  const companyPhone = companySettings?.phone || '';
  const companyEmail = companySettings?.email || '';
  const companyReg = companySettings?.registration_no || '';

  const printWindow = window.open('', '_blank');
  
  const lineItemsHtml = (invoice.line_items || []).map((item, idx) => `
    <tr>
      <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">${idx + 1}</td>
      <td style="padding: 10px; border-bottom: 1px solid #eee;">${item.description || 'Training Fee'}</td>
      <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">${item.quantity || 1}</td>
      <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">${formatCurrency(item.unit_price)}</td>
      <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">${formatCurrency(item.amount)}</td>
    </tr>
  `).join('');

  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Invoice ${invoice.invoice_number}</title>
      <style>
        @page { size: A4; margin: 15mm; }
        @media print { 
          body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; font-size: 12px; color: #333; line-height: 1.5; }
        .invoice-container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 30px; border-bottom: 3px solid #2563eb; padding-bottom: 20px; }
        .company-info { flex: 1; }
        .company-name { font-size: 24px; font-weight: bold; color: #1e40af; margin-bottom: 8px; }
        .company-details { font-size: 11px; color: #666; }
        .logo { max-width: 120px; max-height: 80px; }
        .invoice-title { text-align: right; }
        .invoice-title h1 { font-size: 32px; color: #2563eb; margin-bottom: 5px; }
        .invoice-number { font-size: 14px; font-weight: bold; color: #333; }
        .invoice-meta { display: flex; justify-content: space-between; margin-bottom: 30px; }
        .bill-to, .invoice-details { width: 48%; }
        .section-title { font-size: 11px; font-weight: bold; color: #666; text-transform: uppercase; margin-bottom: 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
        .bill-to-name { font-size: 16px; font-weight: bold; color: #333; margin-bottom: 5px; }
        .bill-to-address { font-size: 11px; color: #666; }
        .detail-row { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 12px; }
        .detail-label { color: #666; }
        .detail-value { font-weight: bold; }
        .items-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        .items-table th { background: #2563eb; color: white; padding: 12px 10px; text-align: left; font-size: 11px; text-transform: uppercase; }
        .items-table th:first-child { border-radius: 4px 0 0 0; }
        .items-table th:last-child { border-radius: 0 4px 0 0; }
        .totals { width: 300px; margin-left: auto; }
        .total-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
        .total-row.grand-total { background: #f0f9ff; padding: 12px; border-radius: 4px; font-size: 16px; font-weight: bold; color: #1e40af; border: 2px solid #2563eb; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; }
        .bank-details { background: #f8fafc; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
        .bank-title { font-weight: bold; margin-bottom: 10px; }
        .terms { font-size: 10px; color: #666; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; text-transform: uppercase; }
        .status-issued { background: #dcfce7; color: #166534; }
        .status-paid { background: #dbeafe; color: #1e40af; }
        .status-approved { background: #e0e7ff; color: #3730a3; }
      </style>
    </head>
    <body>
      <div class="invoice-container">
        <div class="header">
          <div class="company-info">
            ${logoUrl ? `<img src="${logoUrl}" class="logo" alt="Logo" />` : ''}
            <div class="company-name">${companyName}</div>
            <div class="company-details">
              ${companyAddress ? companyAddress + '<br>' : ''}
              ${companyReg ? 'Reg No: ' + companyReg + '<br>' : ''}
              ${companyPhone ? 'Tel: ' + companyPhone + '<br>' : ''}
              ${companyEmail ? 'Email: ' + companyEmail : ''}
            </div>
          </div>
          <div class="invoice-title">
            <h1>INVOICE</h1>
            <div class="invoice-number">${invoice.invoice_number}</div>
            <div style="margin-top: 10px;">
              <span class="status-badge status-${invoice.status}">${invoice.status}</span>
            </div>
          </div>
        </div>

        <div class="invoice-meta">
          <div class="bill-to">
            <div class="section-title">Bill To</div>
            <div class="bill-to-name">${invoice.company_name || 'N/A'}</div>
            <div class="bill-to-address">
              ${invoice.company_address || ''}
            </div>
          </div>
          <div class="invoice-details">
            <div class="section-title">Invoice Details</div>
            <div class="detail-row">
              <span class="detail-label">Invoice Date:</span>
              <span class="detail-value">${formatDate(invoice.invoice_date || invoice.created_at)}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Due Date:</span>
              <span class="detail-value">${formatDate(invoice.due_date)}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Session:</span>
              <span class="detail-value">${invoice.session_name || 'N/A'}</span>
            </div>
          </div>
        </div>

        <table class="items-table">
          <thead>
            <tr>
              <th style="width: 8%; text-align: center;">No.</th>
              <th style="width: 42%;">Description</th>
              <th style="width: 12%; text-align: center;">Qty</th>
              <th style="width: 19%; text-align: right;">Unit Price</th>
              <th style="width: 19%; text-align: right;">Amount</th>
            </tr>
          </thead>
          <tbody>
            ${lineItemsHtml || `
              <tr>
                <td style="padding: 10px; text-align: center;">1</td>
                <td style="padding: 10px;">Training Fee - ${invoice.session_name || 'Training'}</td>
                <td style="padding: 10px; text-align: center;">1</td>
                <td style="padding: 10px; text-align: right;">${formatCurrency(invoice.subtotal || invoice.total_amount)}</td>
                <td style="padding: 10px; text-align: right;">${formatCurrency(invoice.subtotal || invoice.total_amount)}</td>
              </tr>
            `}
          </tbody>
        </table>

        <div class="totals">
          <div class="total-row">
            <span>Subtotal:</span>
            <span>${formatCurrency(invoice.subtotal || invoice.total_amount)}</span>
          </div>
          ${invoice.tax_amount > 0 ? `
            <div class="total-row">
              <span>Tax (${invoice.tax_rate || 6}%):</span>
              <span>${formatCurrency(invoice.tax_amount)}</span>
            </div>
          ` : ''}
          <div class="total-row grand-total">
            <span>Total:</span>
            <span>${formatCurrency(invoice.total_amount)}</span>
          </div>
        </div>

        <div class="footer">
          <div class="bank-details">
            <div class="bank-title">Payment Details</div>
            <div>Bank: ${companySettings?.bank_name || 'Maybank'}</div>
            <div>Account Name: ${companySettings?.bank_account_name || companyName}</div>
            <div>Account No: ${companySettings?.bank_account_no || 'N/A'}</div>
          </div>
          <div class="terms">
            <strong>Terms & Conditions:</strong><br>
            ${companySettings?.invoice_terms || 'Payment is due within 30 days of invoice date. Please include the invoice number as payment reference.'}
          </div>
        </div>
      </div>
      <script>
        window.onload = function() { window.print(); }
      </script>
    </body>
    </html>
  `);
  
  printWindow.document.close();
};
