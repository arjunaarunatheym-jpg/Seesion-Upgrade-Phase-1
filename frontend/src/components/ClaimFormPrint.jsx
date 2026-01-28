import React, { useState, useEffect, useRef } from 'react';
import { axiosInstance } from '../App';
import { Button } from './ui/button';
import { Printer, X, Loader2, Download } from 'lucide-react';
import { toast } from 'sonner';

const ClaimFormPrint = ({ session, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [costingData, setCostingData] = useState(null);
  const [companySettings, setCompanySettings] = useState(null);
  const printRef = useRef(null);

  useEffect(() => {
    loadData();
  }, [session.id]);

  const loadData = async () => {
    try {
      const [costingRes, settingsRes, invoicesRes] = await Promise.all([
        axiosInstance.get(`/finance/session/${session.id}/costing`),
        axiosInstance.get('/finance/company-settings'),
        axiosInstance.get('/finance/invoices')
      ]);
      
      setCostingData(costingRes.data);
      setCompanySettings(settingsRes.data);
      
      // Find ALL invoices for this session (multi-company support)
      const sessionInvoices = invoicesRes.data.filter(inv => inv.session_id === session.id);
      if (sessionInvoices.length > 0) {
        // Calculate combined totals from all invoices
        const combinedTotal = sessionInvoices.reduce((sum, inv) => sum + (inv.total_amount || 0), 0);
        const combinedTax = sessionInvoices.reduce((sum, inv) => sum + (inv.tax_amount || 0), 0);
        
        // Format invoice numbers for display
        const invoiceNumbers = sessionInvoices.map(inv => inv.invoice_number).join(', ');
        const primaryInvoice = sessionInvoices[0];
        
        setCostingData(prev => ({
          ...prev,
          invoice_number: invoiceNumbers,
          invoice_date: primaryInvoice.invoice_date || primaryInvoice.created_at,
          invoice_total: combinedTotal,
          less_tax: combinedTax,
          all_invoices: sessionInvoices // Store all invoices for detailed display
        }));
      }
    } catch (error) {
      toast.error('Failed to load claim form data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
    const printContent = printRef.current;
    const printWindow = window.open('', '_blank');
    
    const logoUrl = companySettings?.logo_url || '';
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Course Registration Form - ${session.name}</title>
          <style>
            @page { size: A4; margin: 12mm; }
            @media print { body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } }
            
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: Arial, sans-serif; font-size: 10px; line-height: 1.4; padding: 15px; }
            
            /* Header */
            .header { 
              display: flex; 
              align-items: center; 
              justify-content: center;
              margin-bottom: 15px; 
              border-bottom: 2px solid #1e40af; 
              padding-bottom: 12px;
              gap: 20px;
            }
            .logo { max-width: 100px; max-height: 60px; object-fit: contain; }
            .header-text { text-align: center; }
            .company-name { font-size: 14px; font-weight: bold; color: #1e40af; margin-bottom: 4px; }
            .form-title { font-size: 12px; font-weight: bold; background: #e5e7eb; padding: 4px 12px; display: inline-block; margin-top: 4px; }
            
            /* Sections */
            .section { margin-bottom: 12px; }
            .section-header { 
              background: #1e40af; 
              color: white; 
              padding: 5px 10px; 
              font-weight: bold; 
              font-size: 10px; 
            }
            
            /* Info Grid */
            .info-grid { 
              display: grid; 
              grid-template-columns: repeat(2, 1fr); 
              gap: 12px; 
              padding: 12px; 
              border: 1px solid #000; 
              border-top: none; 
            }
            .info-grid-3 { grid-template-columns: repeat(3, 1fr); }
            .info-item { }
            .info-label { 
              font-weight: bold; 
              font-size: 9px; 
              color: #333; 
              display: block; 
              margin-bottom: 4px; 
              text-transform: uppercase;
              letter-spacing: 0.5px;
            }
            .info-value { 
              border-bottom: 1px solid #ccc; 
              padding: 6px 8px; 
              min-height: 26px; 
              font-size: 11px;
              background: #fafafa;
              margin-top: 2px;
            }
            .info-full { grid-column: span 2; }
            
            /* Tables */
            table { width: 100%; border-collapse: collapse; font-size: 9px; margin-top: 0; }
            th, td { border: 1px solid #000; padding: 5px 6px; text-align: left; }
            th { background: #f3f4f6; font-weight: bold; font-size: 8px; }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .highlight { background: #fef9c3 !important; }
            .subtotal-row { background: #f3f4f6; font-weight: bold; }
            .total-row { background: #d1d5db; font-weight: bold; }
            .profit-row { background: #bbf7d0 !important; font-weight: bold; }
            
            /* Two Column Layout */
            .two-col { display: flex; gap: 12px; margin-bottom: 12px; }
            .col-left { flex: 1.2; }
            .col-right { flex: 0.8; }
            
            /* Costing Summary */
            .costing-table { width: 100%; }
            .costing-table td { padding: 5px 10px; border: 1px solid #000; }
            .costing-label { font-weight: bold; width: 55%; }
            .costing-value { text-align: right; width: 30%; }
            .costing-pct { text-align: right; width: 15%; }
            
            /* Acknowledgment */
            .ack-table { width: 100%; margin-top: 15px; }
            .ack-table td { padding: 10px; border: 1px solid #000; height: 50px; vertical-align: top; }
            .ack-label { font-weight: bold; width: 25%; }
            
            /* Footer */
            .footer { 
              margin-top: 15px; 
              text-align: center; 
              font-size: 8px; 
              color: #666; 
              border-top: 1px solid #ccc; 
              padding-top: 8px; 
            }
          </style>
        </head>
        <body>
          ${printContent.innerHTML}
        </body>
      </html>
    `);
    
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 250);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  const formatShortDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: '2-digit' });
  };

  const calculateDays = () => {
    if (!session.start_date || !session.end_date) return 1;
    const start = new Date(session.start_date);
    const end = new Date(session.end_date);
    return Math.max(1, Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p>Loading claim form data...</p>
        </div>
      </div>
    );
  }

  if (!costingData) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 text-center">
          <p className="text-red-600">Failed to load data</p>
          <Button onClick={onClose} className="mt-4">Close</Button>
        </div>
      </div>
    );
  }

  const days = calculateDays();
  const invoiceTotal = costingData.invoice_total || 0;
  const taxAmount = costingData.less_tax || 0;
  const grossRevenue = costingData.gross_revenue || 0;
  const trainerFeesTotal = costingData.trainer_fees_total || 0;
  const coordFeeTotal = costingData.coordinator_fee_total || 0;
  const cashExpenses = costingData.cash_expenses_actual || costingData.cash_expenses_estimated || 0;
  
  // Calculate marketing commission and profit the same way as Profit Summary
  // (based on profit AFTER expenses, not from stored values)
  const profitBeforeMarketing = grossRevenue - trainerFeesTotal - coordFeeTotal - cashExpenses;
  
  let marketingAmount = 0;
  if (costingData.marketing) {
    if (costingData.marketing.commission_type === 'percentage') {
      marketingAmount = profitBeforeMarketing * (costingData.marketing.commission_rate || 0) / 100;
    } else {
      marketingAmount = costingData.marketing.fixed_amount || 0;
    }
  }
  
  const totalExpenses = trainerFeesTotal + coordFeeTotal + cashExpenses + marketingAmount;
  const profit = grossRevenue - totalExpenses;
  const profitPct = grossRevenue > 0 ? (profit / grossRevenue * 100) : 0;
  const marketingName = costingData.marketing?.marketing_user_name || costingData.marketing?.full_name || 'N/A';

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-5xl max-h-[95vh] overflow-y-auto">
        {/* Action Bar */}
        <div className="sticky top-0 bg-white border-b p-3 flex justify-between items-center z-10">
          <h2 className="text-lg font-bold">Course Registration Form (Claim Form)</h2>
          <div className="flex gap-2">
            <Button onClick={handlePrint} className="bg-green-600 hover:bg-green-700">
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
            <Button variant="outline" onClick={onClose}>
              <X className="w-4 h-4 mr-2" />
              Close
            </Button>
          </div>
        </div>

        {/* Printable Content */}
        <div ref={printRef} className="p-6 bg-white" style={{ fontSize: '11px' }}>
          {/* Header - Logo + Company Name centered */}
          <div className="header">
            {companySettings?.logo_url && (
              <img src={companySettings.logo_url} alt="Logo" className="logo" />
            )}
            <div className="header-text">
              <div className="company-name">
                {companySettings?.company_name || 'MALAYSIAN DEFENSIVE DRIVING AND RIDING CENTRE SDN BHD'}
              </div>
              <div className="form-title">COURSE REGISTRATION FORM</div>
            </div>
          </div>

          {/* Course Particulars */}
          <div className="section">
            <div className="section-header" style={{ background: '#1e40af', color: 'white', padding: '5px 10px', fontWeight: 'bold', fontSize: '10px' }}>COURSE PARTICULARS</div>
            <div className="info-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px', padding: '15px', border: '1px solid #000', borderTop: 'none' }}>
              <div className="info-item" style={{ gridColumn: 'span 2' }}>
                <span className="info-label" style={{ fontWeight: 'bold', fontSize: '9px', color: '#333', display: 'block', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>CLIENT</span>
                <div className="info-value" style={{ borderBottom: '1px solid #ccc', padding: '8px 10px', minHeight: '28px', fontSize: '11px', background: '#f9fafb' }}>{costingData.company_name}</div>
              </div>
              <div className="info-item">
                <span className="info-label" style={{ fontWeight: 'bold', fontSize: '9px', color: '#333', display: 'block', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>TRAINING START</span>
                <div className="info-value" style={{ borderBottom: '1px solid #ccc', padding: '8px 10px', minHeight: '28px', fontSize: '11px', background: '#f9fafb' }}>{formatDate(session.start_date)}</div>
              </div>
              <div className="info-item">
                <span className="info-label" style={{ fontWeight: 'bold', fontSize: '9px', color: '#333', display: 'block', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>TRAINING END</span>
                <div className="info-value" style={{ borderBottom: '1px solid #ccc', padding: '8px 10px', minHeight: '28px', fontSize: '11px', background: '#f9fafb' }}>{formatDate(session.end_date)}</div>
              </div>
              <div className="info-item">
                <span className="info-label" style={{ fontWeight: 'bold', fontSize: '9px', color: '#333', display: 'block', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>TOTAL PARTICIPANTS</span>
                <div className="info-value" style={{ borderBottom: '1px solid #ccc', padding: '8px 10px', minHeight: '28px', fontSize: '11px', background: '#f9fafb' }}>{costingData.pax}</div>
              </div>
              <div className="info-item">
                <span className="info-label" style={{ fontWeight: 'bold', fontSize: '9px', color: '#333', display: 'block', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>NO. OF DAYS</span>
                <div className="info-value" style={{ borderBottom: '1px solid #ccc', padding: '8px 10px', minHeight: '28px', fontSize: '11px', background: '#f9fafb' }}>{days}</div>
              </div>
              <div className="info-item" style={{ gridColumn: 'span 2' }}>
                <span className="info-label" style={{ fontWeight: 'bold', fontSize: '9px', color: '#333', display: 'block', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>PROGRAM</span>
                <div className="info-value" style={{ borderBottom: '1px solid #ccc', padding: '8px 10px', minHeight: '28px', fontSize: '11px', background: '#f9fafb' }}>{session.name}</div>
              </div>
            </div>
          </div>

          {/* Invoicing and Trainers Side by Side */}
          <div className="two-col">
            {/* Invoicing */}
            <div className="col-left">
              <div className="section">
                <div className="section-header">INVOICING</div>
                <table>
                  <thead>
                    <tr>
                      <th colSpan="2">INV NO: {costingData.invoice_number || 'N/A'}</th>
                      <th colSpan="2" className="text-right">DATE: {formatShortDate(costingData.invoice_date)}</th>
                    </tr>
                    <tr>
                      <th style={{ width: '10%' }}>QTY</th>
                      <th style={{ width: '50%' }}>PARTICULARS</th>
                      <th style={{ width: '20%' }}>RM/UNIT</th>
                      <th style={{ width: '20%' }}>TOTAL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {costingData.all_invoices && costingData.all_invoices.length > 1 ? (
                      <>
                        {costingData.all_invoices.map((inv, idx) => (
                          <tr key={idx}>
                            <td className="text-center">1</td>
                            <td>{inv.company_name || session.name} ({inv.invoice_number})</td>
                            <td className="text-right">{(inv.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                            <td className="text-right">{(inv.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                          </tr>
                        ))}
                      </>
                    ) : (
                      <tr>
                        <td className="text-center">1</td>
                        <td>{session.name}</td>
                        <td className="text-right">{invoiceTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                        <td className="text-right">{invoiceTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                      </tr>
                    )}
                    <tr><td colSpan="4" style={{ height: '10px' }}></td></tr>
                    <tr className="subtotal-row">
                      <td colSpan="3" className="text-right">SUBTOTAL</td>
                      <td className="text-right">{invoiceTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                    </tr>
                    <tr>
                      <td colSpan="3" className="text-right">Tax (if applicable)</td>
                      <td className="text-right">{taxAmount.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                    </tr>
                    <tr className="total-row">
                      <td colSpan="3" className="text-right">TOTAL</td>
                      <td className="text-right">{invoiceTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Trainers */}
            <div className="col-right">
              <div className="section">
                <div className="section-header">TRAINERS</div>
                <table>
                  <thead>
                    <tr>
                      <th>NAME</th>
                      <th>ROLE</th>
                      <th>CLAIM (RM)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(costingData.trainer_fees || []).map((fee, idx) => (
                      <tr key={idx}>
                        <td>{fee.trainer_name}</td>
                        <td style={{ textTransform: 'capitalize' }}>{fee.role}</td>
                        <td className="text-right">{(fee.fee_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                      </tr>
                    ))}
                    {costingData.coordinator_fee && coordFeeTotal > 0 && (
                      <tr>
                        <td>{costingData.coordinator_fee.coordinator_name || 'Coordinator'}</td>
                        <td>Coordinator</td>
                        <td className="text-right">{coordFeeTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                      </tr>
                    )}
                    <tr><td colSpan="3" style={{ height: '20px' }}></td></tr>
                    <tr className="total-row">
                      <td colSpan="2" className="text-right">TOTAL</td>
                      <td className="text-right">{(trainerFeesTotal + coordFeeTotal).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Expenses */}
          <div className="section">
            <div className="section-header">EXPENSES</div>
            <table>
              <thead>
                <tr>
                  <th style={{ width: '35%' }}>DESCRIPTION</th>
                  <th style={{ width: '15%' }}>RATE</th>
                  <th style={{ width: '15%' }}>BASE</th>
                  <th style={{ width: '15%' }}>TOTAL (RM)</th>
                  <th style={{ width: '20%' }}>REMARKS</th>
                </tr>
              </thead>
              <tbody>
                {(costingData.expenses || []).map((expense, idx) => {
                  const amount = expense.actual_amount || expense.estimated_amount || 0;
                  return (
                    <tr key={idx}>
                      <td>{expense.description || expense.category}</td>
                      <td className="text-center">
                        {expense.expense_type === 'percentage' 
                          ? `${((amount / invoiceTotal) * 100).toFixed(0)}%`
                          : expense.expense_type === 'per_pax'
                          ? `RM${(amount / (costingData.total_headcount || 1)).toFixed(0)}/pax`
                          : 'Fixed'
                        }
                      </td>
                      <td className="text-center">
                        {expense.expense_type === 'percentage' 
                          ? invoiceTotal.toLocaleString()
                          : expense.expense_type === 'per_pax'
                          ? costingData.total_headcount
                          : '-'
                        }
                      </td>
                      <td className="text-right">{amount.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                      <td>{expense.remark || ''}</td>
                    </tr>
                  );
                })}
                {(costingData.expenses?.length || 0) === 0 && (
                  <tr><td colSpan="5" className="text-center" style={{ padding: '15px', color: '#666' }}>No expenses recorded</td></tr>
                )}
                <tr className="total-row">
                  <td colSpan="3" className="text-right">TOTAL EXPENSES</td>
                  <td className="text-right">{cashExpenses.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                  <td></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Costing Summary */}
          <div className="section">
            <div className="section-header">COSTING SUMMARY</div>
            <table className="costing-table">
              <tbody>
                <tr>
                  <td className="costing-label">TOTAL SALES</td>
                  <td className="costing-value">{invoiceTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                  <td className="costing-pct"></td>
                </tr>
                <tr>
                  <td className="costing-label">LESS GST 6%</td>
                  <td className="costing-value">{taxAmount.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                  <td className="costing-pct"></td>
                </tr>
                <tr style={{ background: '#dbeafe' }}>
                  <td className="costing-label">GROSS REVENUE</td>
                  <td className="costing-value" style={{ fontWeight: 'bold' }}>{grossRevenue.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                  <td className="costing-pct"></td>
                </tr>
                <tr>
                  <td className="costing-label">Cash Expenses</td>
                  <td className="costing-value">{cashExpenses.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                  <td className="costing-pct"></td>
                </tr>
                <tr>
                  <td className="costing-label">Trainers Claim</td>
                  <td className="costing-value">{(trainerFeesTotal + coordFeeTotal).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                  <td className="costing-pct"></td>
                </tr>
                <tr className="highlight">
                  <td className="costing-label">Marketing ({marketingName})</td>
                  <td className="costing-value">{marketingAmount.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                  <td className="costing-pct"></td>
                </tr>
                <tr style={{ background: '#fef3c7' }}>
                  <td className="costing-label">TOTAL EXPENSES</td>
                  <td className="costing-value" style={{ fontWeight: 'bold' }}>{totalExpenses.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                  <td className="costing-pct"></td>
                </tr>
                <tr className="profit-row">
                  <td className="costing-label" style={{ fontSize: '11px' }}>NET PROFIT</td>
                  <td className="costing-value" style={{ fontSize: '12px' }}>{profit.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                  <td className="costing-pct highlight" style={{ fontSize: '11px', fontWeight: 'bold' }}>{profitPct.toFixed(2)}%</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Acknowledgment */}
          <div className="section">
            <div className="section-header">ACKNOWLEDGMENT</div>
            <table className="ack-table">
              <tbody>
                <tr>
                  <td className="ack-label">Training Coordinator:</td>
                  <td></td>
                  <td style={{ width: '15%' }}>Sign:</td>
                  <td style={{ width: '20%' }}>Date:</td>
                </tr>
                <tr>
                  <td className="ack-label">Manager In Charge:</td>
                  <td></td>
                  <td>Sign:</td>
                  <td>Date:</td>
                </tr>
                <tr>
                  <td className="ack-label">Director:</td>
                  <td></td>
                  <td>Sign:</td>
                  <td>Date:</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div className="footer">
            {companySettings?.document_styling?.footer_tagline || 'Generated by Training Management System'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClaimFormPrint;
