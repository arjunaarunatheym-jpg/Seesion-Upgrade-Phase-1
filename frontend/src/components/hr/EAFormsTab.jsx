/**
 * EAFormsTab Component - Extracted from HRModule
 * Generates EA Forms (Borang EA) for annual tax filing
 */
import { useState } from 'react';
import { axiosInstance } from '../../App';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { FileText, Search, Printer, Loader2 } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const EAFormsTab = ({ staff, companySettings }) => {
  const [selectedStaff, setSelectedStaff] = useState(null);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [eaFormData, setEaFormData] = useState(null);
  const [loading, setLoading] = useState(false);

  const years = [];
  const currentYear = new Date().getFullYear();
  for (let y = currentYear; y >= currentYear - 5; y--) {
    years.push(y);
  }

  const loadEAForm = async () => {
    if (!selectedStaff) {
      toast.error('Please select a staff member');
      return;
    }
    setLoading(true);
    try {
      const response = await axiosInstance.get(`/hr/ea-form/${selectedStaff}/${selectedYear}`);
      setEaFormData(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No EA Form data available for this period');
      setEaFormData(null);
    } finally {
      setLoading(false);
    }
  };

  const getMonthName = (month) => new Date(2000, month - 1).toLocaleString('default', { month: 'long' });
  const formatCurrency = (val) => `RM ${(val || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}`;

  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    const logoUrl = companySettings?.logo_url;
    const companyName = companySettings?.company_name || 'MDDRC SDN BHD';
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>EA Form (Borang EA) - ${selectedYear}</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
          .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 20px; }
          .logo-img { max-height: 60px; margin-bottom: 10px; }
          .company-name { font-size: 20px; font-weight: bold; }
          .form-title { font-size: 18px; font-weight: bold; margin: 20px 0; text-align: center; background: #e0e0e0; padding: 10px; }
          .section { margin-bottom: 20px; }
          .section-title { font-weight: bold; background: #f5f5f5; padding: 8px; margin-bottom: 10px; border-left: 4px solid #333; }
          .row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dotted #ccc; }
          .label { color: #555; }
          .value { font-weight: bold; }
          .total-row { background: #e8f5e9; padding: 10px; font-weight: bold; margin-top: 10px; }
          table { width: 100%; border-collapse: collapse; margin: 10px 0; }
          th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 12px; }
          th { background: #f5f5f5; }
          .text-right { text-align: right; }
          .footer { margin-top: 40px; font-size: 11px; color: #666; text-align: center; border-top: 1px solid #ccc; padding-top: 20px; }
          @media print { body { padding: 20px; } }
        </style>
      </head>
      <body>
        <div class="header">
          ${logoUrl ? `<img src="${logoUrl}" class="logo-img" alt="Logo" />` : ''}
          <div class="company-name">${companyName}</div>
          <div>Penyata Pendapatan Tahunan / Annual Remuneration Statement</div>
        </div>
        
        <div class="form-title">BORANG EA / EA FORM - ${selectedYear}</div>
        
        <div class="section">
          <div class="section-title">A. BUTIR-BUTIR PEKERJA / EMPLOYEE PARTICULARS</div>
          <div class="row"><span class="label">Name:</span><span class="value">${eaFormData?.employee_details?.full_name || '-'}</span></div>
          <div class="row"><span class="label">NRIC:</span><span class="value">${eaFormData?.employee_details?.nric || '-'}</span></div>
          <div class="row"><span class="label">Employee No:</span><span class="value">${eaFormData?.employee_details?.employee_id || '-'}</span></div>
          <div class="row"><span class="label">Designation:</span><span class="value">${eaFormData?.employee_details?.designation || '-'}</span></div>
          <div class="row"><span class="label">EPF No:</span><span class="value">${eaFormData?.employee_details?.epf_number || '-'}</span></div>
          <div class="row"><span class="label">Tax No:</span><span class="value">${eaFormData?.employee_details?.tax_number || '-'}</span></div>
        </div>
        
        <div class="section">
          <div class="section-title">B. PENDAPATAN KASAR TAHUNAN / ANNUAL GROSS INCOME</div>
          <div class="row"><span class="label">Basic Salary / Gaji Pokok:</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.basic_salary)}</span></div>
          <div class="row"><span class="label">Allowances / Elaun:</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.allowances)}</span></div>
          <div class="row"><span class="label">Overtime / Kerja Lebih Masa:</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.overtime)}</span></div>
          <div class="row"><span class="label">Bonus:</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.bonus)}</span></div>
          <div class="row"><span class="label">Commission / Komisen:</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.commission)}</span></div>
          <div class="total-row"><span>JUMLAH PENDAPATAN KASAR / TOTAL GROSS INCOME:</span><span style="float:right;">${formatCurrency(eaFormData?.annual_totals?.gross_salary)}</span></div>
        </div>
        
        <div class="section">
          <div class="section-title">C. POTONGAN / DEDUCTIONS</div>
          <div class="row"><span class="label">EPF (Employee) / KWSP (Pekerja):</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.epf_employee)}</span></div>
          <div class="row"><span class="label">SOCSO (Employee) / PERKESO (Pekerja):</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.socso_employee)}</span></div>
          <div class="row"><span class="label">EIS (Employee) / SIP (Pekerja):</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.eis_employee)}</span></div>
          <div class="row"><span class="label">PCB/MTD / Potongan Cukai Bulanan:</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.pcb)}</span></div>
        </div>
        
        <div class="section">
          <div class="section-title">D. CARUMAN MAJIKAN / EMPLOYER CONTRIBUTIONS</div>
          <div class="row"><span class="label">EPF (Employer) / KWSP (Majikan):</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.epf_employer)}</span></div>
          <div class="row"><span class="label">SOCSO (Employer) / PERKESO (Majikan):</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.socso_employer)}</span></div>
          <div class="row"><span class="label">EIS (Employer) / SIP (Majikan):</span><span class="value">${formatCurrency(eaFormData?.annual_totals?.eis_employer)}</span></div>
        </div>
        
        <div class="section">
          <div class="section-title">E. PECAHAN BULANAN / MONTHLY BREAKDOWN</div>
          <table>
            <thead>
              <tr>
                <th>Bulan/Month</th>
                <th class="text-right">Kasar/Gross</th>
                <th class="text-right">EPF</th>
                <th class="text-right">SOCSO</th>
                <th class="text-right">EIS</th>
                <th class="text-right">PCB</th>
                <th class="text-right">Bersih/Nett</th>
              </tr>
            </thead>
            <tbody>
              ${(eaFormData?.monthly_breakdown || []).map(m => `
                <tr>
                  <td>${getMonthName(m.month)}</td>
                  <td class="text-right">${formatCurrency(m.gross_salary)}</td>
                  <td class="text-right">${formatCurrency(m.epf_employee)}</td>
                  <td class="text-right">${formatCurrency(m.socso_employee)}</td>
                  <td class="text-right">${formatCurrency(m.eis_employee)}</td>
                  <td class="text-right">${formatCurrency(m.pcb)}</td>
                  <td class="text-right">${formatCurrency(m.nett_pay)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        
        <div class="footer">
          <p>Penyata ini dijana oleh sistem dan tidak memerlukan tandatangan.</p>
          <p>This statement is computer-generated and does not require a signature.</p>
          <p>Tarikh/Date: ${new Date().toLocaleDateString('en-MY')}</p>
        </div>
        
        <script>window.onload = function() { window.print(); }</script>
      </body>
      </html>
    `);
    printWindow.document.close();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5" />
          EA Forms (Borang EA)
        </CardTitle>
        <CardDescription>Generate annual remuneration statements for tax filing</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Selection Controls */}
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-[200px]">
            <Label>Select Staff Member</Label>
            <Select value={selectedStaff || ''} onValueChange={setSelectedStaff}>
              <SelectTrigger><SelectValue placeholder="Choose staff..." /></SelectTrigger>
              <SelectContent>
                {staff.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.full_name} ({s.employee_id || 'No ID'})</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="w-32">
            <Label>Year</Label>
            <Select value={selectedYear.toString()} onValueChange={(v) => setSelectedYear(parseInt(v))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {years.map((y) => (
                  <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={loadEAForm} disabled={loading || !selectedStaff} className="bg-blue-600 hover:bg-blue-700">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Search className="w-4 h-4 mr-2" />}
            Generate EA Form
          </Button>
        </div>

        {/* EA Form Display */}
        {eaFormData && (
          <div className="space-y-6 border rounded-lg p-6 bg-white">
            {/* Header */}
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-xl font-bold">Borang EA / EA Form - {selectedYear}</h3>
                <p className="text-gray-500">Annual Remuneration Statement</p>
              </div>
              <Button onClick={handlePrint} className="bg-green-600 hover:bg-green-700">
                <Printer className="w-4 h-4 mr-2" /> Print EA Form
              </Button>
            </div>

            {/* Employee Details */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-semibold mb-3 text-gray-700">A. Employee Particulars</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                <div><span className="text-gray-500">Name:</span> <span className="font-medium">{eaFormData.employee_details?.full_name}</span></div>
                <div><span className="text-gray-500">NRIC:</span> <span className="font-medium">{eaFormData.employee_details?.nric || '-'}</span></div>
                <div><span className="text-gray-500">Employee ID:</span> <span className="font-medium">{eaFormData.employee_details?.employee_id || '-'}</span></div>
                <div><span className="text-gray-500">Designation:</span> <span className="font-medium">{eaFormData.employee_details?.designation || '-'}</span></div>
                <div><span className="text-gray-500">EPF No:</span> <span className="font-medium">{eaFormData.employee_details?.epf_number || '-'}</span></div>
                <div><span className="text-gray-500">Tax No:</span> <span className="font-medium">{eaFormData.employee_details?.tax_number || '-'}</span></div>
              </div>
            </div>

            {/* Annual Summary */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                <h4 className="font-semibold text-green-700 mb-3">B. Annual Gross Income</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span>Basic Salary</span><span className="font-medium">{formatCurrency(eaFormData.annual_totals?.basic_salary)}</span></div>
                  <div className="flex justify-between"><span>Allowances</span><span className="font-medium">{formatCurrency(eaFormData.annual_totals?.allowances)}</span></div>
                  <div className="flex justify-between"><span>Overtime</span><span className="font-medium">{formatCurrency(eaFormData.annual_totals?.overtime)}</span></div>
                  <div className="flex justify-between"><span>Bonus</span><span className="font-medium">{formatCurrency(eaFormData.annual_totals?.bonus)}</span></div>
                  <div className="flex justify-between"><span>Commission</span><span className="font-medium">{formatCurrency(eaFormData.annual_totals?.commission)}</span></div>
                  <div className="flex justify-between font-bold border-t pt-2 mt-2 text-green-700">
                    <span>Total Gross Income</span><span>{formatCurrency(eaFormData.annual_totals?.gross_salary)}</span>
                  </div>
                </div>
              </div>
              
              <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                <h4 className="font-semibold text-red-700 mb-3">C. Annual Deductions (Employee)</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span>EPF (KWSP)</span><span className="font-medium">{formatCurrency(eaFormData.annual_totals?.epf_employee)}</span></div>
                  <div className="flex justify-between"><span>SOCSO (PERKESO)</span><span className="font-medium">{formatCurrency(eaFormData.annual_totals?.socso_employee)}</span></div>
                  <div className="flex justify-between"><span>EIS (SIP)</span><span className="font-medium">{formatCurrency(eaFormData.annual_totals?.eis_employee)}</span></div>
                  <div className="flex justify-between"><span>PCB/MTD (Tax)</span><span className="font-medium">{formatCurrency(eaFormData.annual_totals?.pcb)}</span></div>
                </div>
              </div>
            </div>

            {/* Employer Contributions */}
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <h4 className="font-semibold text-blue-700 mb-3">D. Employer Contributions</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center p-2 bg-white rounded">
                  <div className="text-gray-500">EPF (Employer)</div>
                  <div className="font-bold text-blue-600">{formatCurrency(eaFormData.annual_totals?.epf_employer)}</div>
                </div>
                <div className="text-center p-2 bg-white rounded">
                  <div className="text-gray-500">SOCSO (Employer)</div>
                  <div className="font-bold text-blue-600">{formatCurrency(eaFormData.annual_totals?.socso_employer)}</div>
                </div>
                <div className="text-center p-2 bg-white rounded">
                  <div className="text-gray-500">EIS (Employer)</div>
                  <div className="font-bold text-blue-600">{formatCurrency(eaFormData.annual_totals?.eis_employer)}</div>
                </div>
              </div>
            </div>

            {/* Monthly Breakdown */}
            <div>
              <h4 className="font-semibold mb-3">E. Monthly Breakdown</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm border">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="p-2 text-left">Month</th>
                      <th className="p-2 text-right">Gross</th>
                      <th className="p-2 text-right">EPF</th>
                      <th className="p-2 text-right">SOCSO</th>
                      <th className="p-2 text-right">EIS</th>
                      <th className="p-2 text-right">PCB</th>
                      <th className="p-2 text-right">Nett</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(eaFormData.monthly_breakdown || []).map((m, idx) => (
                      <tr key={idx} className="border-t">
                        <td className="p-2">{getMonthName(m.month)}</td>
                        <td className="p-2 text-right">{formatCurrency(m.gross_salary)}</td>
                        <td className="p-2 text-right">{formatCurrency(m.epf_employee)}</td>
                        <td className="p-2 text-right">{formatCurrency(m.socso_employee)}</td>
                        <td className="p-2 text-right">{formatCurrency(m.eis_employee)}</td>
                        <td className="p-2 text-right">{formatCurrency(m.pcb)}</td>
                        <td className="p-2 text-right font-medium">{formatCurrency(m.nett_pay)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="text-xs text-gray-500 bg-yellow-50 p-3 rounded border border-yellow-200">
              <strong>Note:</strong> This is a summary for reference. Please obtain the official EA Form (C.P.8A) from HR before filing your income tax with LHDN.
            </div>
          </div>
        )}

        {!eaFormData && !loading && (
          <div className="text-center py-12 text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>Select a staff member and year, then click &quot;Generate EA Form&quot;</p>
            <p className="text-sm mt-2">EA Forms summarize annual income and deductions for tax purposes</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { EAFormsTab };
