import React, { useRef } from 'react';
import { downloadPdf } from '../utils/htmlToPdf';
import { Button } from './ui/button';
import { X, Download } from 'lucide-react';

const PayAdvicePrint = ({ payAdvice, companySettings, onClose }) => {
  const printRef = useRef(null);
  
  const primaryColor = companySettings?.primary_color || '#1e40af';
  const secondaryColor = companySettings?.secondary_color || '#16a34a';
  const logoUrl = companySettings?.logo_url || '';
  
  // Build full logo URL - ensure it's always constructed properly
  const fullLogoUrl = logoUrl ? `${process.env.REACT_APP_BACKEND_URL || ''}${logoUrl}` : '';
  
  // Get the display period - PAYMENT month
  const getDisplayPeriod = () => {
    // Use period_name directly - it now contains the payment month
    if (payAdvice?.period_name) return payAdvice.period_name.toUpperCase();
    // Fallback calculation
    if (payAdvice?.month && payAdvice?.year) {
      const monthName = new Date(2000, payAdvice.month - 1).toLocaleString('default', { month: 'long' });
      return `${monthName.toUpperCase()} ${payAdvice.year}`;
    }
    return 'N/A';
  };
  
  // Get training period for reference
  const getTrainingPeriod = () => {
    if (payAdvice?.training_period_name) return payAdvice.training_period_name;
    return null;
  };

  // Build company info
  const getCompanyInfo = () => {
    const parts = [];
    if (companySettings?.company_reg_no) parts.push(`(${companySettings.company_reg_no})`);
    if (companySettings?.address_line1) parts.push(companySettings.address_line1);
    if (companySettings?.city) parts.push(companySettings.city);
    if (companySettings?.postcode) parts.push(companySettings.postcode);
    if (companySettings?.state) parts.push(companySettings.state);
    return parts.join(' • ');
  };
  
  const getContactInfo = () => {
    const parts = [];
    if (companySettings?.phone) parts.push(`Tel: ${companySettings.phone}`);
    if (companySettings?.email) parts.push(companySettings.email);
    return parts.join(' • ');
  };

  const handlePrint = () => {
        // Build the print HTML with inline logo
    const logoHtml = fullLogoUrl ? `<img src="${fullLogoUrl}" style="width:70px;height:auto;" crossorigin="anonymous" />` : '';
    
    const _pdfHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Pay Advice - ${payAdvice?.full_name || 'Staff'} - ${getDisplayPeriod()}</title>
          <style>
            @page { size: A4; margin: 10mm; }
            @media print { body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: Arial, sans-serif; font-size: 9px; line-height: 1.3; padding: 8px; }
            
            .header { display: flex; align-items: flex-start; gap: 10px; padding-bottom: 8px; border-bottom: 2px solid ${primaryColor}; margin-bottom: 8px; }
            .header img { width: 70px; height: auto; }
            .company-name { font-size: 11px; font-weight: bold; color: ${primaryColor}; margin-bottom: 2px; }
            .company-info { font-size: 8px; color: #444; line-height: 1.4; }
            
            .doc-title { text-align: center; font-size: 11px; font-weight: bold; color: ${primaryColor}; background: #f0f4f8; padding: 5px; margin-bottom: 8px; border-left: 3px solid ${secondaryColor}; }
            
            .info-table { width: 100%; margin-bottom: 8px; background: #f9fafb; border: 1px solid #e5e7eb; }
            .info-table td { padding: 4px 8px; font-size: 9px; }
            .info-label { font-weight: bold; color: #666; }
            
            table.session-table { width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: 8px; }
            table.session-table th, table.session-table td { border: 1px solid #ddd; padding: 4px; text-align: left; }
            table.session-table th { background: ${primaryColor}; color: white; }
            table.session-table tr:nth-child(even) { background: #f9fafb; }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            
            .summary { background: ${secondaryColor}; color: white; padding: 10px; text-align: center; margin: 8px 0; }
            .summary .label { font-size: 10px; }
            .summary .amount { font-size: 20px; font-weight: bold; }
            
            .bank-box { background: #f0f4f8; padding: 6px; border-left: 2px solid ${primaryColor}; margin-bottom: 8px; font-size: 8px; }
            
            .sig-table { width: 100%; margin-top: 15px; }
            .sig-table td { width: 50%; text-align: center; padding: 0 20px; }
            .sig-line { border-bottom: 1px solid #000; height: 30px; margin-bottom: 3px; }
            .sig-label { font-size: 8px; }
            
            .footer { text-align: center; font-size: 7px; color: #666; margin-top: 10px; }
          </style>
        </head>
        <body>
          <div class="header">
            ${logoHtml}
            <div>
              <div class="company-name">${companySettings?.company_name || 'MALAYSIAN DEFENSIVE DRIVING AND RIDING CENTRE SDN BHD'}</div>
              <div class="company-info">${getCompanyInfo()}<br/>${getContactInfo()}</div>
            </div>
          </div>
          
          <div class="doc-title">PAY ADVICE - ${getDisplayPeriod()}</div>
          
          <table class="info-table">
            <tr>
              <td><span class="info-label">Name:</span> ${payAdvice.full_name}</td>
              <td><span class="info-label">Payment Period:</span> <strong>${getDisplayPeriod()}</strong></td>
            </tr>
            <tr>
              <td><span class="info-label">NRIC:</span> ${payAdvice.id_number || '-'}</td>
              <td><span class="info-label">Email:</span> ${payAdvice.email || '-'}</td>
            </tr>
            ${getTrainingPeriod() ? `<tr><td colspan="2"><span class="info-label">Training Period:</span> ${getTrainingPeriod()}</td></tr>` : ''}
          </table>
          
          <table class="session-table">
            <thead>
              <tr>
                <th style="width:25px">No</th>
                <th>Company</th>
                <th>Training Session</th>
                <th style="width:60px">Date</th>
                <th style="width:50px">Role</th>
                <th style="width:70px" class="text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              ${(payAdvice.session_details || []).map((s, i) => `
                <tr>
                  <td class="text-center">${i + 1}</td>
                  <td>${s.company_name}</td>
                  <td>${s.session_name}</td>
                  <td>${s.session_date || '-'}</td>
                  <td style="text-transform:capitalize">${s.role}</td>
                  <td class="text-right">${(s.amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                </tr>
              `).join('')}
            </tbody>
            <tfoot>
              <tr style="background:#e5e7eb;font-weight:bold">
                <td colspan="5" class="text-right">GROSS TOTAL</td>
                <td class="text-right">RM ${(payAdvice.gross_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
              </tr>
              ${payAdvice.deductions > 0 ? `
                <tr>
                  <td colspan="5" class="text-right">Less: Deductions</td>
                  <td class="text-right">(RM ${(payAdvice.deductions || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })})</td>
                </tr>
              ` : ''}
            </tfoot>
          </table>
          
          <div class="summary">
            <div class="label">NETT PAYMENT</div>
            <div class="amount">RM ${(payAdvice.nett_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</div>
          </div>
          
          ${(payAdvice.bank_name || payAdvice.bank_account) ? `
            <div class="bank-box">
              <strong style="color:${primaryColor}">Payment:</strong> ${payAdvice.bank_name || '-'} | Acc: ${payAdvice.bank_account || '-'}
            </div>
          ` : ''}
          
          <table class="sig-table">
            <tr>
              <td><div class="sig-line"></div><div class="sig-label">Prepared By</div></td>
              <td><div class="sig-line"></div><div class="sig-label">Received By</div></td>
            </tr>
          </table>
          
          <div class="footer">This document is computer-generated. For enquiries, please contact HR department.</div>
        </body>
      </html>
    `;
    downloadPdf(_pdfHtml, 'PayAdvice');
  };

  const formatCurrency = (val) => `RM ${(val || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}`;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[95vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b p-2 flex justify-between items-center z-10">
          <h2 className="text-base font-bold">Pay Advice Preview</h2>
          <div className="flex gap-2">
            <Button size="sm" onClick={handlePrint} style={{ backgroundColor: secondaryColor }}>
              <Download className="w-4 h-4 mr-1" /> Print / Download
            </Button>
            <Button size="sm" variant="outline" onClick={onClose}><X className="w-4 h-4" /></Button>
          </div>
        </div>

        <div ref={printRef} className="p-3 text-xs">
          {/* Header */}
          <div className="flex items-start gap-3 pb-2 mb-2" style={{ borderBottom: `2px solid ${primaryColor}` }}>
            {fullLogoUrl && (
              <img src={fullLogoUrl} alt="Logo" style={{ width: '70px', height: 'auto' }} />
            )}
            <div className="flex-1">
              <div style={{ fontSize: '11px', fontWeight: 'bold', color: primaryColor }}>
                {companySettings?.company_name || 'MALAYSIAN DEFENSIVE DRIVING AND RIDING CENTRE SDN BHD'}
              </div>
              <div style={{ fontSize: '8px', color: '#444' }}>
                {getCompanyInfo()}<br/>{getContactInfo()}
              </div>
            </div>
          </div>

          {/* Document Title */}
          <div className="text-center py-1 mb-2" style={{ fontSize: '11px', fontWeight: 'bold', color: primaryColor, background: '#f0f4f8', borderLeft: `3px solid ${secondaryColor}` }}>
            PAY ADVICE - {getDisplayPeriod()}
          </div>

          {/* Recipient Info Table */}
          <table className="w-full mb-2" style={{ background: '#f9fafb', border: '1px solid #e5e7eb' }}>
            <tbody>
              <tr>
                <td className="p-1" style={{ fontSize: '9px' }}><span className="font-bold text-gray-600">Name:</span> {payAdvice.full_name}</td>
                <td className="p-1" style={{ fontSize: '9px' }}><span className="font-bold text-gray-600">Payment Period:</span> <strong>{getDisplayPeriod()}</strong></td>
              </tr>
              <tr>
                <td className="p-1" style={{ fontSize: '9px' }}><span className="font-bold text-gray-600">NRIC:</span> {payAdvice.id_number || '-'}</td>
                <td className="p-1" style={{ fontSize: '9px' }}><span className="font-bold text-gray-600">Email:</span> {payAdvice.email || '-'}</td>
              </tr>
              {getTrainingPeriod() && (
                <tr>
                  <td colSpan="2" className="p-1" style={{ fontSize: '9px' }}><span className="font-bold text-gray-600">Training Period:</span> {getTrainingPeriod()}</td>
                </tr>
              )}
            </tbody>
          </table>

          {/* Session Details Table */}
          <table className="w-full mb-2" style={{ fontSize: '8px', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: primaryColor, color: 'white' }}>
                <th className="border p-1 text-center" style={{ width: '25px' }}>No</th>
                <th className="border p-1">Company</th>
                <th className="border p-1">Training Session</th>
                <th className="border p-1" style={{ width: '60px' }}>Date</th>
                <th className="border p-1" style={{ width: '50px' }}>Role</th>
                <th className="border p-1 text-right" style={{ width: '70px' }}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {payAdvice.session_details?.map((session, idx) => (
                <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="border p-1 text-center">{idx + 1}</td>
                  <td className="border p-1">{session.company_name}</td>
                  <td className="border p-1">{session.session_name}</td>
                  <td className="border p-1">{session.session_date || '-'}</td>
                  <td className="border p-1 capitalize">{session.role}</td>
                  <td className="border p-1 text-right">{(session.amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-gray-200 font-bold">
                <td colSpan="5" className="border p-1 text-right">GROSS TOTAL</td>
                <td className="border p-1 text-right">{formatCurrency(payAdvice.gross_amount)}</td>
              </tr>
            </tfoot>
          </table>

          {/* Nett Amount */}
          <div className="text-center py-2 my-2" style={{ background: secondaryColor, color: 'white' }}>
            <div style={{ fontSize: '10px' }}>NETT PAYMENT</div>
            <div style={{ fontSize: '18px', fontWeight: 'bold' }}>{formatCurrency(payAdvice.nett_amount)}</div>
          </div>

          {/* Bank Info */}
          {(payAdvice.bank_name || payAdvice.bank_account) && (
            <div className="p-2 mb-2" style={{ background: '#f0f4f8', borderLeft: `2px solid ${primaryColor}`, fontSize: '8px' }}>
              <span className="font-bold" style={{ color: primaryColor }}>Payment: </span>
              {payAdvice.bank_name || '-'} | Acc: {payAdvice.bank_account || '-'}
            </div>
          )}

          {/* Signature Section */}
          <table className="w-full mt-4">
            <tbody>
              <tr>
                <td className="text-center px-5">
                  <div style={{ borderBottom: '1px solid #000', height: '25px', marginBottom: '2px' }}></div>
                  <div style={{ fontSize: '8px' }}>Prepared By</div>
                </td>
                <td className="text-center px-5">
                  <div style={{ borderBottom: '1px solid #000', height: '25px', marginBottom: '2px' }}></div>
                  <div style={{ fontSize: '8px' }}>Received By</div>
                </td>
              </tr>
            </tbody>
          </table>

          {/* Footer */}
          <div className="text-center mt-3" style={{ fontSize: '7px', color: '#666' }}>
            This document is computer-generated. For enquiries, please contact HR department.
          </div>
        </div>
      </div>
    </div>
  );
};

export default PayAdvicePrint;
