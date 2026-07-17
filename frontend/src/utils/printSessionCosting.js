import { downloadPdf } from './htmlToPdf';

/**
 * Print Session Costing utility — generates a printable PDF of the full costing breakdown.
 * Used by Finance for record keeping alongside the invoice.
 *
 * Expects the JSON response from GET /api/finance/session/{session_id}/costing.
 */
export const printSessionCosting = async (costing, companySettings = {}) => {
  const fmt = (v) =>
    (Math.round(((v || 0) + Number.EPSILON) * 100) / 100)
      .toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const now = new Date().toLocaleString('en-MY', {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  });

  const s = costing || {};
  const companyName = (s.company_name || companySettings.company_name || 'MDDRC');
  const sessionName = s.session_name || 'Untitled Session';
  const startDate = s.start_date || '-';
  const endDate = s.end_date && s.end_date !== s.start_date ? ` — ${s.end_date}` : '';
  const invoiceCount = s.invoice_count || 0;

  const trainerRows = (s.trainer_fees || []).map(f => `
    <tr>
      <td>${f.trainer_name || 'Unknown'}</td>
      <td style="text-transform:capitalize">${f.role || '-'}</td>
      <td class="right">RM ${fmt(f.fee_amount)}</td>
      <td>${f.remark || '-'}</td>
    </tr>`).join('');

  const expenseRows = (s.expenses || []).map(e => `
    <tr>
      <td>${e.description || '-'}</td>
      <td style="text-transform:capitalize">${(e.category || '').replace(/_/g,' ')}</td>
      <td class="right">RM ${fmt(e.estimated_amount)}</td>
      <td class="right">RM ${fmt(e.actual_amount)}</td>
      <td>${e.remark || '-'}</td>
    </tr>`).join('');

  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Session Costing - ${sessionName}</title>
      <style>
        * { box-sizing: border-box; }
        body { font-family: Arial, Helvetica, sans-serif; color:#111; margin: 24px; font-size: 11px; }
        h1 { margin: 0 0 4px 0; font-size: 20px; color:#0f766e; }
        h2 { margin: 20px 0 8px; font-size: 13px; color:#0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 3px; }
        .meta { color: #555; font-size: 10px; margin-bottom: 12px; }
        .box { border: 1px solid #ddd; border-radius: 4px; padding: 10px; margin-bottom: 10px; }
        .grid { display:grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 4px; }
        th, td { padding: 5px 7px; border-bottom: 1px solid #eee; text-align: left; }
        th { background: #f5f5f5; font-weight: bold; }
        td.right, th.right { text-align: right; }
        .summary-row { display:flex; justify-content:space-between; padding: 4px 0; }
        .summary-row strong { color:#0f766e; }
        .final { background: #ecfdf5; padding: 10px; border-radius: 4px; margin-top: 12px; border: 2px solid #10b981; }
        .final .row { display:flex; justify-content:space-between; font-size: 14px; font-weight: bold; }
        .footer { margin-top: 20px; font-size: 9px; color:#999; border-top: 1px dashed #ccc; padding-top: 8px; text-align:center; }
      </style>
    </head>
    <body>
      <h1>Session Costing Report</h1>
      <div class="meta">
        <strong>${sessionName}</strong> &nbsp;|&nbsp; ${companyName} &nbsp;|&nbsp; ${startDate}${endDate}
        <br>Generated: ${now}
      </div>

      <div class="grid">
        <div class="box">
          <div class="summary-row"><span>Invoice(s)</span><strong>${invoiceCount}</strong></div>
          <div class="summary-row"><span>Invoice Total</span><strong>RM ${fmt(s.invoice_total)}</strong></div>
          <div class="summary-row"><span>Tax Amount</span><span>RM ${fmt(s.tax_amount)}</span></div>
          <div class="summary-row"><span>Gross Revenue</span><strong>RM ${fmt(s.gross_revenue)}</strong></div>
        </div>
        <div class="box">
          <div class="summary-row"><span>Trainer(s)</span><strong>${s.trainer_count || 0}</strong></div>
          <div class="summary-row"><span>Participant(s)</span><strong>${s.participant_count || 0}</strong></div>
          <div class="summary-row"><span>Expected Participants</span><span>${s.expected_participants || 0}</span></div>
        </div>
      </div>

      <h2>Trainer Fees — RM ${fmt(s.trainer_fees_total)}</h2>
      <table>
        <thead><tr><th>Trainer</th><th>Role</th><th class="right">Fee</th><th>Remark</th></tr></thead>
        <tbody>${trainerRows || '<tr><td colspan="4" style="text-align:center;color:#999">No trainer fees</td></tr>'}</tbody>
      </table>

      <h2>Coordinator Fee — RM ${fmt(s.coordinator_fee_total)}</h2>
      <div class="box">
        ${s.coordinator_fee ? `
          <div class="summary-row"><span>Coordinator</span><strong>${s.coordinator_fee.coordinator_name || '-'}</strong></div>
          <div class="summary-row"><span>Days</span><span>${s.coordinator_fee.num_days || 1}</span></div>
          <div class="summary-row"><span>Rate/Day</span><span>RM ${fmt(s.coordinator_fee.rate_per_day)}</span></div>
          <div class="summary-row"><span>Total</span><strong>RM ${fmt(s.coordinator_fee.total_fee)}</strong></div>
        ` : '<div style="color:#999;text-align:center">No coordinator fee</div>'}
      </div>

      <h2>Expenses — Estimated RM ${fmt(s.cash_expenses_estimated)} | Actual RM ${fmt(s.cash_expenses_actual)}</h2>
      <table>
        <thead><tr><th>Description</th><th>Category</th><th class="right">Estimated</th><th class="right">Actual</th><th>Remark</th></tr></thead>
        <tbody>${expenseRows || '<tr><td colspan="5" style="text-align:center;color:#999">No expenses recorded</td></tr>'}</tbody>
      </table>

      <h2>Marketing Commission — RM ${fmt(s.marketing_amount)}</h2>
      <div class="box">
        ${s.marketing ? `
          <div class="summary-row"><span>Marketing Person</span><strong>${s.marketing.marketing_user_name || '-'}</strong></div>
          <div class="summary-row"><span>Type</span><span style="text-transform:capitalize">${s.marketing.commission_type || '-'}</span></div>
          ${s.marketing.commission_type === 'percentage'
            ? `<div class="summary-row"><span>Rate</span><span>${s.marketing.commission_rate || 0}%</span></div>`
            : `<div class="summary-row"><span>Fixed Amount</span><span>RM ${fmt(s.marketing.fixed_amount)}</span></div>`}
          <div class="summary-row"><span>Calculated Amount</span><strong>RM ${fmt(s.marketing_amount)}</strong></div>
        ` : '<div style="color:#999;text-align:center">No marketing commission assigned</div>'}
      </div>

      <div class="final">
        <div class="row"><span>Gross Revenue</span><span>RM ${fmt(s.gross_revenue)}</span></div>
        <div class="row"><span>Total Expenses</span><span>- RM ${fmt(s.total_expenses)}</span></div>
        <div class="row" style="border-top:2px solid #0f766e;padding-top:6px;margin-top:4px;font-size:16px">
          <span>Net Profit</span>
          <span style="color:${(s.final_profit || 0) >= 0 ? '#059669' : '#dc2626'}">
            RM ${fmt(s.final_profit)} (${(s.profit_percentage || 0).toFixed(2)}%)
          </span>
        </div>
      </div>

      <div class="footer">
        Confidential — Internal Financial Record | Generated by MDDRC Training Portal
      </div>
    </body>
    </html>
  `;

  const safeName = (sessionName || 'costing').replace(/[^a-zA-Z0-9]+/g, '_').substring(0, 60);
  downloadPdf(html, `SessionCosting_${safeName}`);
};
