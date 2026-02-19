/**
 * Print Quotation utility - generates printable quotation PDF
 * Uses EXACT same header style as invoice for company document uniformity
 */

export const printQuotation = async (quotation, companySettings, logoUrl, templates = {}) => {
  const settings = companySettings || {};
  
  // Styling variables from settings - SAME as invoice
  const primaryColor = settings.primary_color || '#1a365d';
  const secondaryColor = settings.secondary_color || '#4472C4';
  const tagline = settings.tagline || 'Towards a Nation of Safe Drivers';
  
  // Get template content
  const pageContent = templates.page_content || '';
  const termsConditions = templates.terms_conditions || '';
  
  // Format currency
  const formatCurrency = (amount) => {
    return (amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 });
  };
  
  // Format date
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-MY', { day: 'numeric', month: 'long', year: 'numeric' });
  };
  
  // Process template content - replace placeholders
  const processContent = (content) => {
    if (!content) return '';
    return content
      .replace(/\{\{company_name\}\}/g, quotation.company_name || '-')
      .replace(/\{\{programme_name\}\}/g, quotation.programme_name || '-')
      .replace(/\{\{contact_person\}\}/g, quotation.contact_person || '-')
      .replace(/\{\{quotation_number\}\}/g, quotation.quotation_number || '-')
      .replace(/\{\{date\}\}/g, formatDate(quotation.created_at))
      .replace(/\{\{total_amount\}\}/g, formatCurrency(quotation.total_amount))
      .replace(/\{\{num_participants\}\}/g, quotation.num_participants || '-')
      .replace(/\{\{rate_per_pax\}\}/g, formatCurrency(quotation.rate_per_pax))
      .replace(/\{\{venue\}\}/g, quotation.venue || '-')
      .replace(/<b>/g, '<strong>').replace(/<\/b>/g, '</strong>')
      .replace(/<i>/g, '<em>').replace(/<\/i>/g, '</em>')
      .replace(/<u>/g, '<u>').replace(/<\/u>/g, '</u>')
      .replace(/<highlight>/g, '<mark>').replace(/<\/highlight>/g, '</mark>')
      .replace(/<pb>/g, '<div class="page-break"></div>')
      .replace(/<pagebreak>/g, '<div class="page-break"></div>')
      .replace(/<hr>/g, '<hr style="border: none; border-top: 1px solid #ddd; margin: 10px 0;">')
      .replace(/\n/g, '<br>');
  };
  
  const printWindow = window.open('', '_blank');
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Quotation ${quotation.quotation_number}</title>
      <style>
        @page { size: A4; margin: 15mm; }
        @media print { 
          body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
          .page-break { page-break-before: always; }
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
        
        /* Header with Logo - EXACTLY SAME AS INVOICE */
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
        
        .quotation-title { 
          font-size: 22px; 
          font-weight: bold; 
          text-align: center; 
          color: ${primaryColor}; 
          margin: 15px 0;
          padding: 10px;
          background: #f0f4f8;
        }
        
        /* Details Grid - SAME AS INVOICE */
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
        
        /* Table - SAME AS INVOICE */
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; font-size: 11px; }
        th { background: ${secondaryColor}; color: white; font-weight: bold; font-size: 10px; text-transform: uppercase; }
        .text-right { text-align: right; }
        
        /* Totals - SAME AS INVOICE */
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
        
        /* Content section */
        .content-section {
          margin: 20px 0;
          font-size: 11px;
          line-height: 1.6;
        }
        .content-section h3 {
          font-size: 13px;
          font-weight: bold;
          margin-bottom: 10px;
          color: ${primaryColor};
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
        
        .signature-section {
          margin-top: 40px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 40px;
        }
        .signature-box {
          text-align: center;
        }
        .signature-line {
          border-top: 1px solid #333;
          margin-top: 60px;
          padding-top: 5px;
        }
        
        .page-break { page-break-before: always; padding-top: 20px; }
        
        mark { background-color: yellow; padding: 0 2px; }
      </style>
    </head>
    <body>
      <!-- Header - EXACTLY SAME AS INVOICE -->
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
      
      <div class="quotation-title">QUOTATION</div>
      
      <div class="details-grid">
        <div class="detail-box">
          <div class="detail-label">To:</div>
          <div class="detail-value" style="font-weight: bold;">${quotation.company_name || '-'}</div>
          ${quotation.address ? `<div class="detail-value">${quotation.address}</div>` : ''}
          <div class="detail-value">Attn: ${quotation.contact_person || '-'}</div>
          ${quotation.contact_email ? `<div class="detail-value">${quotation.contact_email}</div>` : ''}
          ${quotation.contact_phone ? `<div class="detail-value">${quotation.contact_phone}</div>` : ''}
        </div>
        <div class="detail-box">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px;">
            <div><div class="detail-label">Quotation No:</div><div class="detail-value">${quotation.quotation_number}</div></div>
            <div><div class="detail-label">Date:</div><div class="detail-value">${formatDate(quotation.created_at)}</div></div>
            <div style="grid-column: span 2;"><div class="detail-label">Programme:</div><div class="detail-value">${quotation.programme_name || '-'}</div></div>
            <div><div class="detail-label">Valid Until:</div><div class="detail-value">${formatDate(quotation.valid_until)}</div></div>
          </div>
        </div>
      </div>
      
      <!-- Pricing Table -->
      <table>
        <thead>
          <tr>
            <th style="width: 30px;">No</th>
            <th>Description</th>
            <th class="text-right" style="width: 60px;">Qty</th>
            <th class="text-right" style="width: 100px;">Unit Price (RM)</th>
            <th class="text-right" style="width: 100px;">Amount (RM)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1</td>
            <td>${quotation.programme_name || 'Training Programme'}${quotation.pricing_type === 'per_pax' ? ' (Per Participant)' : ' (Group Rate)'}</td>
            <td class="text-right">${quotation.num_participants || 1}</td>
            <td class="text-right">${formatCurrency(quotation.pricing_type === 'per_pax' ? quotation.rate_per_pax : quotation.group_price)}</td>
            <td class="text-right">${formatCurrency(quotation.subtotal || quotation.total_amount)}</td>
          </tr>
          ${(quotation.discounts || []).map((d, i) => `
            <tr>
              <td>${i + 2}</td>
              <td>Discount: ${d.reason || 'Special Discount'}</td>
              <td class="text-right">-</td>
              <td class="text-right">-</td>
              <td class="text-right" style="color: red;">- ${formatCurrency(d.amount)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
      
      <div class="totals">
        <div class="total-row"><span>Sub-Total:</span><span>RM ${formatCurrency(quotation.subtotal || quotation.total_amount)}</span></div>
        ${(quotation.discounts || []).length > 0 ? `<div class="total-row"><span>Total Discount:</span><span style="color: red;">- RM ${formatCurrency((quotation.discounts || []).reduce((sum, d) => sum + (d.amount || 0), 0))}</span></div>` : ''}
        <div class="grand-total"><span>TOTAL</span><span>RM ${formatCurrency(quotation.total_amount)}</span></div>
      </div>
      
      <!-- Template Content -->
      ${pageContent ? `
        <div class="content-section">
          ${processContent(pageContent)}
        </div>
      ` : ''}
      
      <!-- Terms & Conditions -->
      ${termsConditions ? `
        <div class="content-section">
          <h3>Terms & Conditions</h3>
          ${processContent(termsConditions)}
        </div>
      ` : ''}
      
      <!-- Signature Section -->
      <div class="signature-section">
        <div class="signature-box">
          <div class="signature-line">
            <strong>Prepared By</strong><br>
            ${settings.company_name || 'MDDRC SDN BHD'}
          </div>
        </div>
        <div class="signature-box">
          <div class="signature-line">
            <strong>Accepted By</strong><br>
            ${quotation.company_name || 'Client'}
          </div>
        </div>
      </div>
      
      <div class="tagline">"${tagline}"</div>
    </body>
    </html>
  `);
  
  printWindow.document.close();
  
  // Wait for content to load then print
  printWindow.onload = () => {
    setTimeout(() => {
      printWindow.print();
    }, 500);
  };
};
