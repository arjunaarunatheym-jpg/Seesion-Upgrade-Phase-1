import React, { useRef } from 'react';
import { downloadPdf } from '../utils/htmlToPdf';
import { Button } from './ui/button';
import { X, Download } from 'lucide-react';

const getMonthName = (month) => new Date(2000, month - 1).toLocaleString('default', { month: 'long' });
const formatCurrency = (val) => `RM ${(val || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}`;

const PayslipPrint = ({ payslip, companySettings, onClose }) => {
  const printRef = useRef(null);
  
  const primaryColor = companySettings?.primary_color || '#1e40af';
  const secondaryColor = companySettings?.secondary_color || '#16a34a';
  const logoUrl = companySettings?.logo_url || '';
  const showWatermark = companySettings?.show_watermark !== false;
  const watermarkOpacity = companySettings?.watermark_opacity || 0.08;
  
  const fullLogoUrl = logoUrl ? `${process.env.REACT_APP_BACKEND_URL || ''}${logoUrl}` : '';

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
    const printContent = printRef.current;
        const _pdfHtml = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Payslip - ${payslip.full_name} - ${payslip.period_name}</title>
          <style>
            @page { size: A4; margin: 8mm; }
            @media print { body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: Arial, sans-serif; font-size: 9px; line-height: 1.2; }
            
            .watermark { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); opacity: ${watermarkOpacity}; z-index: -1; }
            .watermark img { width: 280px; height: auto; }
            
            .payslip { border: 2px solid ${primaryColor}; }
            .header { display: flex; align-items: flex-start; gap: 10px; padding: 8px; border-bottom: 2px solid ${primaryColor}; }
            .logo-img { width: 70px; height: auto; }
            .company-name { font-size: 11px; font-weight: bold; color: ${primaryColor}; margin-bottom: 2px; }
            .company-info { font-size: 8px; color: #444; line-height: 1.3; }
            
            .doc-title { text-align: center; font-size: 11px; font-weight: bold; color: ${primaryColor}; background: #f0f4f8; padding: 4px; margin: 6px 8px; border-left: 3px solid ${secondaryColor}; }
            
            .emp-info { padding: 6px 8px; }
            .emp-box { background: #f9fafb; padding: 6px; border: 1px solid #e5e7eb; }
            .emp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 3px; font-size: 8px; }
            .emp-row { display: flex; }
            .emp-label { font-weight: bold; width: 80px; color: #666; }
            
            .ed-section { display: grid; grid-template-columns: 1fr 1fr; }
            .earnings, .deductions { padding: 6px 10px; font-size: 8px; }
            .earnings { border-right: 1px solid #ddd; }
            .section-title { font-weight: bold; font-size: 9px; margin-bottom: 5px; padding-bottom: 3px; border-bottom: 2px solid; }
            .earnings .section-title { color: ${secondaryColor}; border-color: ${secondaryColor}; }
            .deductions .section-title { color: #dc2626; border-color: #dc2626; }
            .item-row { display: flex; justify-content: space-between; padding: 2px 0; }
            .item-total { font-weight: bold; border-top: 1px solid #ddd; margin-top: 5px; padding-top: 5px; }
            
            .nett-pay { background: ${secondaryColor}; color: white; padding: 8px; text-align: center; }
            .nett-label { font-size: 9px; }
            .nett-amount { font-size: 18px; font-weight: bold; }
            
            .employer-section { padding: 6px 10px; background: ${primaryColor}08; border-top: 1px solid #ddd; font-size: 8px; }
            .employer-title { font-weight: bold; font-size: 9px; color: ${primaryColor}; margin-bottom: 4px; padding-bottom: 3px; border-bottom: 2px solid ${primaryColor}; }
            .employer-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
            
            .ytd-section { padding: 6px 10px; background: #fef9c3; border-top: 1px solid #ddd; font-size: 8px; }
            .ytd-title { font-weight: bold; font-size: 9px; color: #ca8a04; margin-bottom: 4px; padding-bottom: 3px; border-bottom: 2px solid #ca8a04; }
            .ytd-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
            .ytd-item { text-align: center; }
            .ytd-item-label { font-size: 7px; color: #666; }
            .ytd-item-value { font-weight: bold; }
            
            .footer { padding: 5px 10px; text-align: center; font-size: 7px; color: #666; border-top: 1px solid #ddd; }
          </style>
        </head>
        <body>
          ${showWatermark && fullLogoUrl ? `<div class="watermark"><img src="${fullLogoUrl}" alt="" /></div>` : ''}
          ${printContent.innerHTML}
        </body>
      </html>
    `;
    downloadPdf(_pdfHtml, 'Payslip');
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[95vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b p-2 flex justify-between items-center z-10">
          <h2 className="text-base font-bold">Payslip Preview</h2>
          <div className="flex gap-2">
            <Button size="sm" onClick={handlePrint} style={{ backgroundColor: secondaryColor }}>
              <Download className="w-4 h-4 mr-1" /> Download
            </Button>
            <Button size="sm" variant="outline" onClick={onClose}><X className="w-4 h-4" /></Button>
          </div>
        </div>

        <div ref={printRef} className="p-2 relative text-xs" style={{ minHeight: '500px' }}>
          {/* Single centered watermark */}
          {showWatermark && fullLogoUrl && (
            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', opacity: watermarkOpacity, zIndex: 0, pointerEvents: 'none' }}>
              <img src={fullLogoUrl} alt="" style={{ width: '200px', height: 'auto' }} />
            </div>
          )}
          
          <div className="payslip relative" style={{ border: `2px solid ${primaryColor}`, zIndex: 1 }}>
            {/* Compact Header */}
            <div className="header flex items-start gap-2 p-2" style={{ borderBottom: `2px solid ${primaryColor}` }}>
              {fullLogoUrl && (
                <img src={fullLogoUrl} alt="Logo" style={{ width: '60px', height: 'auto' }} />
              )}
              <div className="flex-1">
                <div className="company-name" style={{ fontSize: '10px', fontWeight: 'bold', color: primaryColor }}>
                  {companySettings?.company_name || 'MALAYSIAN DEFENSIVE DRIVING AND RIDING CENTRE SDN BHD'}
                </div>
                <div className="company-info" style={{ fontSize: '7px', color: '#444' }}>
                  {getCompanyInfo()}<br/>{getContactInfo()}
                </div>
              </div>
            </div>

            {/* Document Title */}
            <div className="doc-title text-center py-1 mx-2 my-1" style={{ fontSize: '10px', fontWeight: 'bold', color: primaryColor, background: '#f0f4f8', borderLeft: `3px solid ${secondaryColor}` }}>
              PAYSLIP - {getMonthName(payslip.month).toUpperCase()} {payslip.year}
            </div>

            {/* Employee Info */}
            <div className="emp-info px-2 pb-1">
              <div className="emp-box p-1" style={{ background: '#f9fafb', border: '1px solid #e5e7eb' }}>
                <div className="emp-grid grid grid-cols-2 gap-1" style={{ fontSize: '8px' }}>
                  <div className="flex"><span className="font-bold w-20 text-gray-600">Name:</span><span>{payslip.full_name}</span></div>
                  <div className="flex"><span className="font-bold w-20 text-gray-600">Department:</span><span>{payslip.department || '-'}</span></div>
                  <div className="flex"><span className="font-bold w-20 text-gray-600">NRIC:</span><span>{payslip.nric || '-'}</span></div>
                  <div className="flex"><span className="font-bold w-20 text-gray-600">EPF No:</span><span>{payslip.epf_number || '-'}</span></div>
                  <div className="flex"><span className="font-bold w-20 text-gray-600">Position:</span><span>{payslip.designation || '-'}</span></div>
                  <div className="flex"><span className="font-bold w-20 text-gray-600">SOCSO No:</span><span>{payslip.socso_number || '-'}</span></div>
                </div>
              </div>
            </div>

            {/* Earnings & Deductions - Side by Side */}
            <div className="ed-section grid grid-cols-2" style={{ fontSize: '8px' }}>
              <div className="earnings p-2" style={{ borderRight: '1px solid #ddd' }}>
                <div className="section-title" style={{ fontWeight: 'bold', fontSize: '9px', marginBottom: '4px', paddingBottom: '2px', borderBottom: `2px solid ${secondaryColor}`, color: secondaryColor }}>EARNINGS</div>
                <div className="item-row flex justify-between py-0.5"><span>Basic Salary</span><span>{formatCurrency(payslip.basic_salary)}</span></div>
                {payslip.fixed_allowance > 0 && <div className="item-row flex justify-between py-0.5"><span>Fixed Allowance</span><span>{formatCurrency(payslip.fixed_allowance)}</span></div>}
                {payslip.housing_allowance > 0 && <div className="item-row flex justify-between py-0.5"><span>Housing</span><span>{formatCurrency(payslip.housing_allowance)}</span></div>}
                {payslip.transport_allowance > 0 && <div className="item-row flex justify-between py-0.5"><span>Transport</span><span>{formatCurrency(payslip.transport_allowance)}</span></div>}
                {payslip.meal_allowance > 0 && <div className="item-row flex justify-between py-0.5"><span>Meal</span><span>{formatCurrency(payslip.meal_allowance)}</span></div>}
                {payslip.phone_allowance > 0 && <div className="item-row flex justify-between py-0.5"><span>Phone</span><span>{formatCurrency(payslip.phone_allowance)}</span></div>}
                {payslip.other_allowance > 0 && <div className="item-row flex justify-between py-0.5"><span>Other</span><span>{formatCurrency(payslip.other_allowance)}</span></div>}
                {payslip.commission > 0 && <div className="item-row flex justify-between py-0.5"><span>Commission</span><span>{formatCurrency(payslip.commission)}</span></div>}
                {payslip.incentives > 0 && <div className="item-row flex justify-between py-0.5"><span>Incentives</span><span>{formatCurrency(payslip.incentives)}</span></div>}
                {payslip.bonus > 0 && <div className="item-row flex justify-between py-0.5"><span>Bonus</span><span>{formatCurrency(payslip.bonus)}</span></div>}
                {payslip.annual_leave_pay > 0 && <div className="item-row flex justify-between py-0.5"><span>Annual Leave Pay</span><span>{formatCurrency(payslip.annual_leave_pay)}</span></div>}
                {payslip.overtime > 0 && <div className="item-row flex justify-between py-0.5"><span>Overtime</span><span>{formatCurrency(payslip.overtime)}</span></div>}
                <div className="item-total flex justify-between font-bold pt-1 mt-1" style={{ borderTop: '1px solid #ddd' }}><span>GROSS</span><span>{formatCurrency(payslip.gross_salary)}</span></div>
              </div>
              
              <div className="deductions p-2">
                <div className="section-title" style={{ fontWeight: 'bold', fontSize: '9px', marginBottom: '4px', paddingBottom: '2px', borderBottom: '2px solid #dc2626', color: '#dc2626' }}>DEDUCTIONS</div>
                <div className="item-row flex justify-between py-0.5"><span>EPF ({payslip.epf_employee_rate}%)</span><span>{formatCurrency(payslip.epf_employee)}</span></div>
                <div className="item-row flex justify-between py-0.5"><span>SOCSO</span><span>{formatCurrency(payslip.socso_employee)}</span></div>
                <div className="item-row flex justify-between py-0.5"><span>EIS/SIP</span><span>{formatCurrency(payslip.eis_employee)}</span></div>
                {payslip.pcb > 0 && <div className="item-row flex justify-between py-0.5"><span>CP39/PCB</span><span>{formatCurrency(payslip.pcb)}</span></div>}
                {payslip.cp38 > 0 && <div className="item-row flex justify-between py-0.5"><span>CP38</span><span>{formatCurrency(payslip.cp38)}</span></div>}
                {payslip.loan_deduction > 0 && <div className="item-row flex justify-between py-0.5"><span>Loan</span><span>{formatCurrency(payslip.loan_deduction)}</span></div>}
                {payslip.mid_month_advance > 0 && <div className="item-row flex justify-between py-0.5"><span>Mid-Month Adv</span><span>{formatCurrency(payslip.mid_month_advance)}</span></div>}
                {payslip.salary_adjustment > 0 && <div className="item-row flex justify-between py-0.5"><span>Salary Adj</span><span>{formatCurrency(payslip.salary_adjustment)}</span></div>}
                {payslip.unpaid_leave > 0 && <div className="item-row flex justify-between py-0.5"><span>Unpaid Leave</span><span>{formatCurrency(payslip.unpaid_leave)}</span></div>}
                {payslip.other_deductions > 0 && <div className="item-row flex justify-between py-0.5"><span>Other</span><span>{formatCurrency(payslip.other_deductions)}</span></div>}
                <div className="item-total flex justify-between font-bold pt-1 mt-1" style={{ borderTop: '1px solid #ddd' }}><span>TOTAL</span><span>{formatCurrency(payslip.total_deductions)}</span></div>
              </div>
            </div>

            {/* Nett Pay */}
            <div className="nett-pay text-center py-2" style={{ background: secondaryColor, color: 'white' }}>
              <div style={{ fontSize: '9px' }}>NETT PAY</div>
              <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{formatCurrency(payslip.nett_pay)}</div>
            </div>

            {/* Employer Contributions */}
            <div className="employer-section p-2" style={{ background: `${primaryColor}08`, borderTop: '1px solid #ddd', fontSize: '8px' }}>
              <div className="employer-title" style={{ fontWeight: 'bold', fontSize: '8px', color: primaryColor, marginBottom: '3px', paddingBottom: '2px', borderBottom: `1px solid ${primaryColor}` }}>EMPLOYER CONTRIBUTIONS</div>
              <div className="employer-grid grid grid-cols-3 gap-2">
                <div><strong>EPF:</strong> {formatCurrency(payslip.epf_employer)}</div>
                <div><strong>SOCSO:</strong> {formatCurrency(payslip.socso_employer)}</div>
                <div><strong>EIS:</strong> {formatCurrency(payslip.eis_employer)}</div>
              </div>
            </div>

            {/* YTD Section */}
            <div className="ytd-section p-2" style={{ background: '#fef9c3', borderTop: '1px solid #ddd', fontSize: '8px' }}>
              <div className="ytd-title" style={{ fontWeight: 'bold', fontSize: '8px', color: '#ca8a04', marginBottom: '3px', paddingBottom: '2px', borderBottom: '1px solid #ca8a04' }}>YTD ({payslip.year})</div>
              <div className="ytd-grid grid grid-cols-4 gap-2">
                <div className="ytd-item text-center"><div style={{ fontSize: '7px', color: '#666' }}>Gross</div><div className="font-bold">{formatCurrency(payslip.ytd_gross)}</div></div>
                <div className="ytd-item text-center"><div style={{ fontSize: '7px', color: '#666' }}>EPF(EE)</div><div className="font-bold">{formatCurrency(payslip.ytd_epf_employee)}</div></div>
                <div className="ytd-item text-center"><div style={{ fontSize: '7px', color: '#666' }}>EPF(ER)</div><div className="font-bold">{formatCurrency(payslip.ytd_epf_employer)}</div></div>
                <div className="ytd-item text-center"><div style={{ fontSize: '7px', color: '#666' }}>PCB</div><div className="font-bold">{formatCurrency(payslip.ytd_pcb)}</div></div>
              </div>
            </div>

            {/* Footer */}
            <div className="footer text-center py-1" style={{ fontSize: '7px', color: '#666', borderTop: '1px solid #ddd' }}>
              Computer-generated. Bank: {payslip.bank_name || '-'} | Acc: {payslip.bank_account || '-'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PayslipPrint;
