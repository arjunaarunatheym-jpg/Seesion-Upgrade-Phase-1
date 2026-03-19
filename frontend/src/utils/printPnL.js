/**
 * Print P&L Statement utility - generates a formal, branded Profit & Loss Statement
 * Uses the same header/color scheme as invoices for consistency
 */

export const printPnLStatement = async (pnlData, companySettings, logoUrl) => {
  const settings = companySettings || {};
  const primaryColor = settings.primary_color || '#1a365d';
  const secondaryColor = settings.secondary_color || '#4472C4';
  const tagline = settings.tagline || 'Towards a Nation of Safe Drivers';
  const year = pnlData?.year || new Date().getFullYear();
  const summary = pnlData?.summary || {};
  const programmes = pnlData?.programmes || [];

  const fmt = (val) => `RM ${(val || 0).toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const headerCustomFields = (settings.invoice_custom_fields || [])
    .filter(f => f.position === 'Header' || f.position === 'header')
    .map(f => ` &bull; ${f.label}: ${f.value}`)
    .join('');

  const printWindow = window.open('', '_blank');
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>P&L Statement ${year}</title>
      <style>
        @page { size: A4; margin: 15mm; }
        @media print { 
          body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
          font-family: Arial, sans-serif; 
          font-size: 11px;
          padding: 25px; 
          max-width: 210mm;
          margin: 0 auto; 
          line-height: 1.5;
          color: #333;
        }
        
        .header { 
          display: flex;
          align-items: center;
          gap: 20px;
          padding-bottom: 15px;
          border-bottom: 3px solid ${primaryColor};
          margin-bottom: 20px;
        }
        .logo-img { width: 100px; height: auto; flex-shrink: 0; }
        .company-details { flex: 1; }
        .company-name { font-size: 18px; font-weight: bold; color: ${primaryColor}; margin-bottom: 5px; }
        .company-info { font-size: 11px; color: #444; line-height: 1.5; }
        
        .doc-title { 
          font-size: 20px; font-weight: bold; text-align: center; 
          color: ${primaryColor}; margin: 15px 0; padding: 10px;
          background: #f0f4f8;
        }
        .doc-subtitle {
          text-align: center; font-size: 13px; color: #555; margin-bottom: 20px;
        }
        
        .section { margin-bottom: 16px; }
        .section-title { 
          font-size: 13px; font-weight: bold; color: ${primaryColor};
          padding: 8px 12px; background: #f0f4f8;
          border-left: 4px solid ${secondaryColor};
          margin-bottom: 8px;
        }
        
        table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
        th { 
          background: ${secondaryColor}; color: white; font-weight: bold; 
          font-size: 10px; text-transform: uppercase;
          padding: 8px 12px; text-align: left;
        }
        td { padding: 6px 12px; font-size: 11px; border-bottom: 1px solid #eee; }
        .text-right { text-align: right; }
        .indent { padding-left: 30px; color: #555; }
        .bold { font-weight: bold; }
        
        .subtotal-row td { 
          border-top: 2px solid #ddd; font-weight: bold; 
          padding-top: 8px; padding-bottom: 8px;
        }
        .total-row td { 
          background: ${secondaryColor}; color: white; font-weight: bold; 
          font-size: 13px; padding: 10px 12px;
        }
        .profit-row td {
          background: ${primaryColor}; color: white; font-weight: bold; 
          font-size: 14px; padding: 12px;
        }
        .gross-row td {
          background: #e8f5e9; font-weight: bold; color: #2e7d32;
          padding: 8px 12px; border-top: 2px solid #4caf50;
        }
        .loss { color: #dc2626; }
        .gain { color: #16a34a; }
        
        .programme-table { margin-bottom: 12px; }
        .programme-table th { background: ${primaryColor}; font-size: 9px; }
        .programme-table td { font-size: 10px; padding: 5px 8px; }
        
        .footer { 
          margin-top: 30px; font-size: 9px; color: #777;
          padding-top: 12px; border-top: 1px solid #ddd;
          text-align: center;
        }
        .tagline { 
          font-style: italic; color: ${primaryColor}; font-size: 12px; 
          text-align: center; margin-top: 15px;
          padding-top: 12px; border-top: 1px solid #eee;
        }
        .summary-cards {
          display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;
          margin-bottom: 20px;
        }
        .summary-card {
          padding: 12px; border-radius: 6px; text-align: center;
        }
        .summary-card .label { font-size: 9px; text-transform: uppercase; font-weight: bold; margin-bottom: 4px; }
        .summary-card .value { font-size: 18px; font-weight: bold; }
        .card-income { background: #e8f5e9; border: 1px solid #a5d6a7; }
        .card-income .label { color: #2e7d32; }
        .card-income .value { color: #1b5e20; }
        .card-expense { background: #fce4ec; border: 1px solid #ef9a9a; }
        .card-expense .label { color: #c62828; }
        .card-expense .value { color: #b71c1c; }
        .card-profit { background: #e3f2fd; border: 1px solid #90caf9; }
        .card-profit .label { color: #1565c0; }
        .card-profit .value { color: #0d47a1; }
      </style>
    </head>
    <body>
      <!-- Company Header (same as invoice) -->
      <div class="header">
        ${logoUrl ? `<img src="${logoUrl}" class="logo-img" alt="Logo" />` : ''}
        <div class="company-details">
          <div class="company-name">${settings.company_name || 'MDDRC SDN BHD'}</div>
          <div class="company-info">
            ${settings.company_reg_no ? `(${settings.company_reg_no})` : ''}
            ${settings.address_line1 ? ` &bull; ${settings.address_line1}` : ''}${settings.address_line2 ? `, ${settings.address_line2}` : ''}<br>
            ${settings.city || ''}${settings.postcode ? ` ${settings.postcode}` : ''}${settings.state ? `, ${settings.state}` : ''}
            ${settings.phone ? ` &bull; Tel: ${settings.phone}` : ''}${settings.email ? ` &bull; ${settings.email}` : ''}
            ${headerCustomFields}
          </div>
        </div>
      </div>
      
      <div class="doc-title">PROFIT & LOSS STATEMENT</div>
      <div class="doc-subtitle">For the Financial Year Ended 31 December ${year}</div>
      
      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="summary-card card-income">
          <div class="label">Total Revenue</div>
          <div class="value">${fmt(summary.total_income)}</div>
        </div>
        <div class="summary-card card-expense">
          <div class="label">Total Expenses</div>
          <div class="value">${fmt(summary.total_expenses)}</div>
        </div>
        <div class="summary-card card-profit">
          <div class="label">Net Profit</div>
          <div class="value ${(summary.net_profit || 0) >= 0 ? 'gain' : 'loss'}">${fmt(summary.net_profit)}</div>
        </div>
      </div>

      <!-- Main P&L Table -->
      <table>
        <thead>
          <tr>
            <th style="width: 65%;">Description</th>
            <th class="text-right" style="width: 35%;">Amount (RM)</th>
          </tr>
        </thead>
        <tbody>
          <!-- REVENUE -->
          <tr><td colspan="2" class="section-title" style="border-left: 4px solid ${secondaryColor}; background: #f0f4f8;">REVENUE</td></tr>
          <tr>
            <td class="indent">Training Programme Income</td>
            <td class="text-right">${fmt(summary.total_programme_income)}</td>
          </tr>
          ${(summary.other_income || 0) > 0 ? `
          <tr>
            <td class="indent">Other Income</td>
            <td class="text-right">${fmt(summary.other_income)}</td>
          </tr>
          ` : ''}
          <tr class="subtotal-row">
            <td>Total Revenue</td>
            <td class="text-right">${fmt(summary.total_income)}</td>
          </tr>
          
          <!-- DIRECT COSTS -->
          <tr><td colspan="2" class="section-title" style="border-left: 4px solid #ef5350; background: #fce4ec;">DIRECT COSTS (Cost of Sales)</td></tr>
          ${programmes.map(p => `
          <tr>
            <td class="indent">${p.programme_name || 'Other'}</td>
            <td class="text-right">${fmt(p.expenses?.total)}</td>
          </tr>
          `).join('')}
          <tr class="subtotal-row">
            <td>Total Direct Costs</td>
            <td class="text-right loss">${fmt(summary.total_direct_costs)}</td>
          </tr>
          
          <!-- GROSS PROFIT -->
          <tr class="gross-row">
            <td>GROSS PROFIT (${summary.gross_margin_pct || 0}%)</td>
            <td class="text-right">${fmt(summary.gross_profit)}</td>
          </tr>
          
          <!-- OPERATING EXPENSES -->
          <tr><td colspan="2" class="section-title" style="border-left: 4px solid #ff9800; background: #fff3e0;">OPERATING EXPENSES (Overhead)</td></tr>
          ${(summary.overhead?.payroll || 0) > 0 ? `
          <tr>
            <td class="indent">Staff Salaries & Statutory</td>
            <td class="text-right">${fmt(summary.overhead?.payroll)}</td>
          </tr>
          ` : ''}
          ${(summary.overhead?.petty_cash || 0) > 0 ? `
          <tr>
            <td class="indent">Petty Cash Expenses</td>
            <td class="text-right">${fmt(summary.overhead?.petty_cash)}</td>
          </tr>
          ` : ''}
          ${(summary.overhead?.manual || 0) > 0 ? `
          <tr>
            <td class="indent">Other Operating Expenses</td>
            <td class="text-right">${fmt(summary.overhead?.manual)}</td>
          </tr>
          ` : ''}
          <tr class="subtotal-row">
            <td>Total Operating Expenses</td>
            <td class="text-right loss">${fmt(summary.overhead?.total)}</td>
          </tr>
          
          <!-- NET PROFIT -->
          <tr class="profit-row">
            <td>NET PROFIT ${summary.net_margin_pct ? `(${summary.net_margin_pct}%)` : ''}</td>
            <td class="text-right">${fmt(summary.net_profit)}</td>
          </tr>
        </tbody>
      </table>
      
      <!-- Programme Breakdown Detail -->
      ${programmes.length > 0 ? `
      <div class="section">
        <div class="section-title">PROGRAMME-WISE BREAKDOWN</div>
        <table class="programme-table">
          <thead>
            <tr>
              <th>Programme</th>
              <th class="text-right">Revenue</th>
              <th class="text-right">Trainer Fees</th>
              <th class="text-right">Coordinator Fees</th>
              <th class="text-right">Marketing Comm.</th>
              <th class="text-right">Session Exp.</th>
              <th class="text-right">Total Cost</th>
              <th class="text-right">Gross Profit</th>
              <th class="text-right">Margin %</th>
            </tr>
          </thead>
          <tbody>
            ${programmes.map(p => `
            <tr>
              <td>${p.programme_name || 'Other'}</td>
              <td class="text-right">${fmt(p.income)}</td>
              <td class="text-right">${fmt(p.expenses?.trainer_fees)}</td>
              <td class="text-right">${fmt(p.expenses?.coordinator_fees)}</td>
              <td class="text-right">${fmt(p.expenses?.marketing_commissions)}</td>
              <td class="text-right">${fmt(p.expenses?.session_expenses)}</td>
              <td class="text-right">${fmt(p.expenses?.total)}</td>
              <td class="text-right ${(p.gross_profit || 0) >= 0 ? 'gain' : 'loss'}">${fmt(p.gross_profit)}</td>
              <td class="text-right">${p.gross_margin_pct || 0}%</td>
            </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      ` : ''}
      
      <div class="footer">
        <p>This statement is system-generated by ${settings.company_name || 'MDDRC'} Training Management System.</p>
        <p>Generated on: ${new Date().toLocaleString('en-MY')}</p>
      </div>
      
      <div class="tagline">"${tagline}"</div>
      
      <script>
        window.onload = function() { 
          setTimeout(function() { window.print(); }, 500);
        };
      </script>
    </body>
    </html>
  `);
  printWindow.document.close();
};
