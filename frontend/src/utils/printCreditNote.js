/**
 * Print Credit Note utility - generates printable credit note PDF
 */

export const printCreditNote = (creditNote, companySettings) => {
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
  
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Credit Note ${creditNote.cn_number}</title>
      <style>
        @page { size: A4; margin: 15mm; }
        @media print { 
          body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; font-size: 12px; color: #333; line-height: 1.5; }
        .cn-container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 30px; border-bottom: 3px solid #dc2626; padding-bottom: 20px; }
        .company-info { flex: 1; }
        .company-name { font-size: 24px; font-weight: bold; color: #1e40af; margin-bottom: 8px; }
        .company-details { font-size: 11px; color: #666; }
        .cn-title { text-align: right; }
        .cn-title h1 { font-size: 28px; color: #dc2626; margin-bottom: 5px; }
        .cn-number { font-size: 14px; font-weight: bold; color: #333; }
        .cn-meta { display: flex; justify-content: space-between; margin-bottom: 30px; }
        .bill-to, .cn-details { width: 48%; }
        .section-title { font-size: 11px; font-weight: bold; color: #666; text-transform: uppercase; margin-bottom: 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
        .bill-to-name { font-size: 16px; font-weight: bold; color: #333; margin-bottom: 5px; }
        .detail-row { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 12px; }
        .detail-label { color: #666; }
        .detail-value { font-weight: bold; }
        .reason-box { background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 20px; margin-bottom: 30px; }
        .reason-title { font-weight: bold; color: #dc2626; margin-bottom: 10px; }
        .amount-box { background: #fee2e2; border: 2px solid #dc2626; border-radius: 8px; padding: 20px; text-align: center; max-width: 300px; margin-left: auto; }
        .amount-label { font-size: 14px; color: #666; margin-bottom: 5px; }
        .amount-value { font-size: 28px; font-weight: bold; color: #dc2626; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 10px; color: #666; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; text-transform: uppercase; background: #fee2e2; color: #dc2626; }
      </style>
    </head>
    <body>
      <div class="cn-container">
        <div class="header">
          <div class="company-info">
            <div class="company-name">${companyName}</div>
            <div class="company-details">
              ${companyAddress ? companyAddress + '<br>' : ''}
              ${companyReg ? 'Reg No: ' + companyReg + '<br>' : ''}
              ${companyPhone ? 'Tel: ' + companyPhone + '<br>' : ''}
              ${companyEmail ? 'Email: ' + companyEmail : ''}
            </div>
          </div>
          <div class="cn-title">
            <h1>CREDIT NOTE</h1>
            <div class="cn-number">${creditNote.cn_number}</div>
            <div style="margin-top: 10px;">
              <span class="status-badge">${creditNote.status}</span>
            </div>
          </div>
        </div>

        <div class="cn-meta">
          <div class="bill-to">
            <div class="section-title">Issued To</div>
            <div class="bill-to-name">${creditNote.company_name || 'N/A'}</div>
          </div>
          <div class="cn-details">
            <div class="section-title">Credit Note Details</div>
            <div class="detail-row">
              <span class="detail-label">Date:</span>
              <span class="detail-value">${formatDate(creditNote.created_at)}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Original Invoice:</span>
              <span class="detail-value">${creditNote.invoice_number || 'N/A'}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Session:</span>
              <span class="detail-value">${creditNote.session_name || 'N/A'}</span>
            </div>
          </div>
        </div>

        <div class="reason-box">
          <div class="reason-title">Reason for Credit Note</div>
          <div>${creditNote.reason || 'No reason provided'}</div>
        </div>

        <div class="amount-box">
          <div class="amount-label">Credit Amount</div>
          <div class="amount-value">${formatCurrency(creditNote.amount)}</div>
        </div>

        <div class="footer">
          <p>This credit note has been issued to adjust the original invoice amount as stated above.</p>
          <p style="margin-top: 10px;">Generated on ${new Date().toLocaleDateString('en-MY')}</p>
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
