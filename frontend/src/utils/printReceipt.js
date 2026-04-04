import { downloadPdf } from './htmlToPdf';

/**
 * Print Receipt utility - generates PDF payment receipt download
 * Follows the same branding pattern as printInvoice.js
 */

export const printReceipt = async (payment, companySettings, axiosInstance) => {
  const settings = companySettings || {};
  
  const primaryColor = settings.primary_color || '#1a365d';
  const secondaryColor = settings.secondary_color || '#4472C4';
  const tagline = settings.tagline || 'Towards a Nation of Safe Drivers';
  
  // Build logo URL - use backend URL for API-served logos
  let logoUrl = '';
  if (settings.logo_url) {
    if (settings.logo_url.startsWith('http')) {
      logoUrl = settings.logo_url;
    } else {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || window.location.origin;
      logoUrl = `${backendUrl}${settings.logo_url.startsWith('/') ? '' : '/'}${settings.logo_url}`;
    }
  }

  // Fetch invoice data for bill_to info and credit notes
  let billToName = payment.company_name || '-';
  let creditNotes = [];
  if (axiosInstance && payment.invoice_id) {
    try {
      const invRes = await axiosInstance.get(`/finance/invoices/${payment.invoice_id}`);
      const inv = invRes.data;
      billToName = inv.bill_to_name || inv.company_name || payment.company_name || '-';
      // Fetch credit notes for this invoice
      try {
        const cnRes = await axiosInstance.get('/finance/credit-notes');
        creditNotes = (cnRes.data || []).filter(cn => cn.invoice_id === payment.invoice_id);
      } catch (e) { /* ignore */ }
    } catch (e) { /* ignore */ }
  }

  const paymentMethodLabel = {
    'bank_transfer': 'Bank Transfer',
    'cash': 'Cash',
    'cheque': 'Cheque',
    'online': 'Online Payment',
    'credit_card': 'Credit Card',
  }[payment.payment_method] || payment.payment_method || '-';

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Receipt - ${payment.invoice_number || 'Payment'}</title>
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
        .company-details { flex: 1; }
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
        
        .receipt-title { 
          font-size: 22px; 
          font-weight: bold; 
          text-align: center; 
          color: ${primaryColor}; 
          margin: 15px 0;
          padding: 10px;
          background: #f0f4f8;
          text-transform: uppercase;
          letter-spacing: 2px;
        }
        
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
        
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; font-size: 11px; }
        th { background: ${secondaryColor}; color: white; font-weight: bold; font-size: 10px; text-transform: uppercase; }
        .text-right { text-align: right; }
        
        .amount-box { 
          background: ${secondaryColor}; 
          color: white; 
          padding: 15px 20px; 
          border-radius: 4px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 16px;
          font-weight: bold;
          margin-bottom: 20px;
        }
        
        .notes-box {
          padding: 12px;
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 4px;
          margin-bottom: 20px;
          font-size: 11px;
        }
        
        .signature-section {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 40px;
          margin-top: 60px;
          font-size: 11px;
        }
        .signature-line {
          border-top: 1px solid #333;
          padding-top: 8px;
          text-align: center;
        }
        
        .footer { 
          margin-top: 40px; 
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

        .watermark {
          text-align: center;
          color: #e0e0e0;
          font-size: 48px;
          font-weight: bold;
          letter-spacing: 8px;
          margin: 10px 0;
          text-transform: uppercase;
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
          </div>
        </div>
      </div>

      <!-- Title -->
      <div class="receipt-title">Official Receipt</div>

      <!-- Receipt Details -->
      <div class="details-grid">
        <div class="detail-box">
          <div class="detail-label">Receipt For</div>
          <div class="detail-value" style="font-weight: bold;">${billToName}</div>
        </div>
        <div class="detail-box">
          <div class="detail-label">Invoice Number</div>
          <div class="detail-value" style="font-weight: bold;">${payment.invoice_number || '-'}</div>
          <div class="detail-label" style="margin-top: 6px;">Payment Date</div>
          <div class="detail-value">${payment.payment_date || '-'}</div>
        </div>
      </div>

      <!-- Payment Details Table -->
      <table>
        <thead>
          <tr>
            <th>Description</th>
            <th>Payment Method</th>
            <th>Reference No.</th>
            <th class="text-right" style="width: 120px;">Amount (RM)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Payment for ${payment.invoice_number || 'Invoice'}</td>
            <td>${paymentMethodLabel}</td>
            <td>${payment.reference_number || '-'}</td>
            <td class="text-right" style="font-weight: bold;">${Number(payment.amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
          </tr>
          ${payment.deduction_amount > 0 ? `
          <tr>
            <td colspan="3" style="color: #dc2626;">Less: Deduction</td>
            <td class="text-right" style="color: #dc2626;">-${Number(payment.deduction_amount).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
          </tr>
          ` : ''}
        </tbody>
      </table>

      <!-- Total Amount -->
      <div class="amount-box">
        <span>TOTAL RECEIVED</span>
        <span>RM ${Number(payment.amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</span>
      </div>

      ${payment.notes ? `
      <div class="notes-box">
        <div class="detail-label">Notes</div>
        <div>${payment.notes}</div>
      </div>
      ` : ''}

      ${creditNotes.length > 0 ? `
      <div class="notes-box" style="border-color: #fca5a5; background: #fef2f2;">
        <div class="detail-label" style="color: #dc2626;">Credit Note(s) Applied</div>
        ${creditNotes.map(cn => `<div style="margin-top: 4px;">${cn.cn_number} — RM ${Number(cn.amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })} (${cn.reason || 'Deduction'})</div>`).join('')}
      </div>
      ` : ''}

      <!-- Signature Section -->
      <div class="signature-section">
        <div>
          <div class="signature-line">
            <strong>Received By</strong><br>
            ${settings.company_name || 'MDDRC SDN BHD'}
          </div>
        </div>
        <div>
          <div class="signature-line">
            <strong>Authorized Signatory</strong><br>
            Date: ${payment.payment_date || '-'}
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="footer">
        <p>This is a computer-generated receipt. No signature is required.</p>
        <p>Generated on: ${new Date().toLocaleDateString('en-MY', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</p>
      </div>
      
      <div class="tagline">"${tagline}"</div>
    </body>
    </html>
  `;
  
  downloadPdf(html, `Receipt_${payment.receipt_number || payment.id?.substring(0,8) || 'payment'}`);
};
