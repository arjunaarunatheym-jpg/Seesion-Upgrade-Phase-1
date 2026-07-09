import { downloadPdf } from './htmlToPdf';

/**
 * Print Invoice utility - generates PDF invoice download
 * Restored from original implementation with full company branding and details
 */

export const printInvoice = async (invoice, companySettings, logoUrl) => {
  // Auto-heal: if line_items don't match total_amount, recalculate before rendering
  const totalAmount = invoice.total_amount || 0;
  const taxAmount = invoice.tax_amount || 0;
  const expectedSubtotal = totalAmount - taxAmount;
  const lineItemsTotal = (invoice.line_items || []).reduce((sum, i) => sum + (i.amount || 0), 0);
  
  if (invoice.line_items?.length && Math.abs(lineItemsTotal - expectedSubtotal) > 0.01) {
    if (invoice.line_items.length === 1) {
      invoice.line_items[0].amount = expectedSubtotal;
      invoice.line_items[0].unit_price = expectedSubtotal / (invoice.line_items[0].quantity || 1);
    } else {
      const scale = lineItemsTotal > 0 ? expectedSubtotal / lineItemsTotal : 1;
      invoice.line_items.forEach(item => {
        item.amount = Math.round((item.amount || 0) * scale * 100) / 100;
        item.unit_price = Math.round((item.unit_price || 0) * scale * 100) / 100;
      });
    }
    invoice.subtotal = expectedSubtotal;
  }

  const settings = companySettings || {};
  
  // Styling variables from settings
  const primaryColor = settings.primary_color || '#1a365d';
  const secondaryColor = settings.secondary_color || '#4472C4';
  const tagline = settings.tagline || 'Towards a Nation of Safe Drivers';
  
  // Build custom fields HTML
  const headerCustomFields = (settings.invoice_custom_fields || [])
    .filter(f => f.position === 'Header' || f.position === 'header')
    .map(f => ` • ${f.label}: ${f.value}`)
    .join('');
  const footerCustomFields = (settings.invoice_custom_fields || [])
    .filter(f => f.position === 'Footer' || f.position === 'footer')
    .map(f => `<p><strong>${f.label}:</strong> ${f.value}</p>`)
    .join('');
  
  const html = `
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
        body { 
          font-family: Arial, sans-serif; 
          font-size: 12px;
          padding: 25px; 
          max-width: 210mm;
          margin: 0 auto; 
          line-height: 1.5;
        }
        
        /* Header with Logo */
        .header { 
          display: flex;
          align-items: center;
          gap: 20px;
          padding-bottom: 15px;
          border-bottom: 3px solid ${primaryColor};
          margin-bottom: 20px;
        }
        .logo-img { 
          width: 100px; 
          height: auto;
          flex-shrink: 0;
        }
        .company-details {
          flex: 1;
        }
        .company-name { 
          font-size: 18px; 
          font-weight: bold; 
          color: ${primaryColor};
          margin-bottom: 5px;
        }
        .company-info { 
          font-size: 11px; 
          color: #444;
          line-height: 1.5;
        }
        
        .invoice-title { 
          font-size: 22px; 
          font-weight: bold; 
          text-align: center; 
          color: ${primaryColor}; 
          margin: 15px 0;
          padding: 10px;
          background: #f0f4f8;
        }
        
        /* Details Grid */
        .details-grid { 
          display: grid; 
          grid-template-columns: 1fr 1fr; 
          gap: 15px; 
          margin-bottom: 20px;
        }
        .detail-box { 
          padding: 12px; 
          border: 1px solid #ddd; 
          border-radius: 4px;
          font-size: 11px;
        }
        .detail-label { 
          font-weight: bold; 
          font-size: 10px; 
          color: #666; 
          margin-bottom: 4px; 
          text-transform: uppercase;
        }
        .detail-value { font-size: 12px; margin-bottom: 4px; }
        
        /* Training Details */
        .training-box {
          padding: 12px;
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 4px;
          margin-bottom: 20px;
          font-size: 11px;
        }
        .training-box .detail-label { display: inline; }
        .training-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
        
        /* Table */
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; font-size: 11px; }
        th { background: ${secondaryColor}; color: white; font-weight: bold; font-size: 10px; text-transform: uppercase; }
        .text-right { text-align: right; }
        
        /* Totals */
        .totals { 
          width: 50%;
          margin-left: auto;
          font-size: 11px;
        }
        .total-row { 
          display: flex; 
          justify-content: space-between; 
          padding: 6px 0; 
          border-bottom: 1px solid #eee;
        }
        .grand-total { 
          font-size: 14px; 
          font-weight: bold; 
          background: ${secondaryColor}; 
          color: white; 
          padding: 12px 15px; 
          margin-top: 8px; 
          border-radius: 4px;
          display: flex;
          justify-content: space-between;
        }
        
        /* Footer */
        .footer { 
          margin-top: 30px; 
          font-size: 10px; 
          color: #555;
          padding-top: 15px;
          border-top: 1px solid #ddd;
        }
        .footer p { margin-bottom: 5px; }
        
        .tagline { 
          font-style: italic;
          color: ${primaryColor}; 
          font-size: 12px; 
          text-align: center; 
          margin-top: 15px;
          padding-top: 12px;
          border-top: 1px solid #eee;
        }
      </style>
    </head>
    <body>
      <!-- Header -->
      <div class="header">
        ${logoUrl ? `<img src="${logoUrl}" class="logo-img" alt="Logo" />` : ''}
        <div class="company-details">
          <div class="company-name">${settings.company_name || 'MDDRC SDN BHD'}</div>
          <div class="company-info">
            ${settings.company_reg_no ? `(${settings.company_reg_no})` : ''}
            ${settings.address_line1 ? ` • ${settings.address_line1}` : ''}${settings.address_line2 ? `, ${settings.address_line2}` : ''}<br>
            ${settings.city || ''}${settings.postcode ? ` ${settings.postcode}` : ''}${settings.state ? `, ${settings.state}` : ''}
            ${settings.phone ? ` • Tel: ${settings.phone}` : ''}${settings.email ? ` • ${settings.email}` : ''}
            ${headerCustomFields}
          </div>
        </div>
      </div>
      
      <div class="invoice-title">${invoice.document_type === 'proforma' ? 'PROFORMA INVOICE' : 'INVOICE'}</div>
      ${invoice.document_type === 'proforma' ? '<div style="text-align:center;color:#7c3aed;font-size:12px;font-weight:bold;margin-top:-8px;margin-bottom:12px;letter-spacing:1px;">NOT A TAX INVOICE — FOR REFERENCE / PO PURPOSES ONLY</div>' : ''}
      
      <div class="details-grid">
        <div class="detail-box">
          <div class="detail-label">Bill To:</div>
          <div class="detail-value" style="font-weight: bold;">${invoice.bill_to_name || invoice.company_name || '-'}</div>
          ${invoice.bill_to_address ? `<div class="detail-value">${invoice.bill_to_address}</div>` : ''}
          ${invoice.bill_to_reg_no ? `<div class="detail-value">Reg: ${invoice.bill_to_reg_no}</div>` : ''}
        </div>
        <div class="detail-box">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px;">
            <div><div class="detail-label">Invoice No:</div><div class="detail-value">${invoice.invoice_number}</div></div>
            <div><div class="detail-label">Date:</div><div class="detail-value">${invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString('en-MY') : (invoice.issued_at ? new Date(invoice.issued_at).toLocaleDateString('en-MY') : new Date().toLocaleDateString('en-MY'))}</div></div>
            ${invoice.your_reference ? `<div style="grid-column: span 2;"><div class="detail-label">Your Ref:</div><div class="detail-value">${invoice.your_reference}</div></div>` : ''}
          </div>
        </div>
      </div>
      
      <div class="training-box">
        <div class="training-grid">
          <div><span class="detail-label">Program:</span> ${invoice.programme_name || '-'}</div>
          <div><span class="detail-label">Company:</span> ${invoice.company_name || '-'}</div>
          <div><span class="detail-label">Training Date:</span> ${invoice.training_dates || '-'}</div>
          <div><span class="detail-label">Venue:</span> ${invoice.venue || '-'}</div>
        </div>
      </div>
      
      <table>
        <thead>
          <tr>
            <th style="width: 30px;">No</th>
            <th>Description</th>
            <th class="text-right" style="width: 50px;">Qty</th>
            <th class="text-right" style="width: 80px;">Price (RM)</th>
            <th class="text-right" style="width: 90px;">Total (RM)</th>
          </tr>
        </thead>
        <tbody>
          ${(invoice.line_items || []).map((item, idx) => `
            <tr>
              <td>${idx + 1}</td>
              <td>${item.description || '-'}</td>
              <td class="text-right">${item.quantity || 0}</td>
              <td class="text-right">${(item.unit_price || 0).toLocaleString('en-MY', {minimumFractionDigits: 2})}</td>
              <td class="text-right">${(item.amount || 0).toLocaleString('en-MY', {minimumFractionDigits: 2})}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
      
      <div class="totals">
        <div class="total-row"><span>Sub-Total:</span><span>RM ${(invoice.subtotal || 0).toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>
        ${invoice.mobilisation_fee ? `<div class="total-row"><span>Mobilisation Fee:</span><span>RM ${invoice.mobilisation_fee.toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>` : ''}
        ${invoice.rounding ? `<div class="total-row"><span>Rounding:</span><span>RM ${invoice.rounding.toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>` : ''}
        ${invoice.tax_amount ? `<div class="total-row"><span>Tax (${invoice.tax_rate || 0}%):</span><span>RM ${invoice.tax_amount.toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>` : ''}
        ${invoice.discount ? `<div class="total-row"><span>Discount:</span><span>- RM ${invoice.discount.toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>` : ''}
        <div class="grand-total"><span>GRAND TOTAL</span><span>RM ${(invoice.total_amount || 0).toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>
      </div>
      
      <div class="footer">
        ${invoice.document_type === 'proforma' ? '<p style="color:#7c3aed;font-weight:bold;border:1px solid #a78bfa;padding:6px;background:#f5f3ff;">This is a Proforma Invoice — a preliminary bill for planning purposes only. A tax invoice will be issued upon payment or purchase order confirmation.</p>' : ''}
        <p><strong>Payment Terms:</strong> ${settings.invoice_terms || 'Upon receipt of invoice'}</p>
        <p><strong>Bank:</strong> ${settings.bank_name || '-'} | <strong>Account:</strong> ${settings.bank_account_name || settings.company_name || '-'} | <strong>No:</strong> ${settings.bank_account_number || '-'}</p>
        <p>${settings.invoice_footer_note || 'Thank you for your business!'}</p>
        ${footerCustomFields}
      </div>
      
      <div class="tagline">"${tagline}"</div>
    </body>
    </html>
  `;
  const filePrefix = invoice.document_type === 'proforma' ? 'Proforma' : 'Invoice';
  downloadPdf(html, `${filePrefix}_${invoice.invoice_number || 'draft'}`);
};
