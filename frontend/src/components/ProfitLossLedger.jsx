import React, { useState, useEffect } from 'react';
import { axiosInstance } from '../App';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { 
  TrendingUp, TrendingDown, DollarSign, Calendar, Plus, Trash2, 
  Loader2, Download, PieChart, BarChart3, ArrowUpRight, ArrowDownRight,
  Users, Briefcase, UserCheck, Building2, ChevronDown, ChevronRight,
  BookOpen, Printer, FileSpreadsheet, FileText
} from 'lucide-react';
import { CEOPnLTab } from './ledger/CEOPnLTab';
import { YoYComparisonTab } from './ledger/YoYComparisonTab';
import { AuditorPnLTab } from './ledger/AuditorPnLTab';
import { ARAgingTab } from './ledger/ARAgingTab';
import { GeneralLedgerTab } from './ledger/GeneralLedgerTab';
import { TrainerSubledgerTab } from './ledger/TrainerSubledgerTab';
import { MarketingSubledgerTab } from './ledger/MarketingSubledgerTab';
import { PayrollSubledgerTab } from './ledger/PayrollSubledgerTab';

const ProfitLossLedger = () => {
  const [loading, setLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [programmeData, setProgrammeData] = useState(null);
  const [trainerSubledger, setTrainerSubledger] = useState(null);
  const [marketingSubledger, setMarketingSubledger] = useState(null);
  const [payrollSubledger, setPayrollSubledger] = useState(null);
  const [generalLedger, setGeneralLedger] = useState(null);
  const [companySettings, setCompanySettings] = useState(null);
  const [activeTab, setActiveTab] = useState('auditor-pnl');
  const [expandedRows, setExpandedRows] = useState({});
  
  // Manual entry states
  const [showIncomeDialog, setShowIncomeDialog] = useState(false);
  const [showExpenseDialog, setShowExpenseDialog] = useState(false);
  const [manualIncome, setManualIncome] = useState([]);
  const [manualExpenses, setManualExpenses] = useState([]);
  const [entryForm, setEntryForm] = useState({
    description: '',
    amount: '',
    category: '',
    date: new Date().toISOString().split('T')[0],
    notes: ''
  });

  const years = [];
  const currentYear = new Date().getFullYear();
  for (let y = currentYear; y >= currentYear - 5; y--) {
    years.push(y);
  }

  const months = [
    { value: null, label: 'All Months' },
    { value: 1, label: 'January' }, { value: 2, label: 'February' }, { value: 3, label: 'March' },
    { value: 4, label: 'April' }, { value: 5, label: 'May' }, { value: 6, label: 'June' },
    { value: 7, label: 'July' }, { value: 8, label: 'August' }, { value: 9, label: 'September' },
    { value: 10, label: 'October' }, { value: 11, label: 'November' }, { value: 12, label: 'December' }
  ];

  const expenseCategories = [
    'Office Supplies', 'Transport', 'Utilities', 'Professional Services',
    'Marketing', 'Insurance', 'Maintenance', 'Equipment', 'Other'
  ];

  const incomeCategories = [
    'Training Fees', 'Consultation', 'Grants', 'Sponsorship', 'Other Income'
  ];

  useEffect(() => {
    loadData();
    // Load company settings for print
    axiosInstance.get('/company-settings').then(res => setCompanySettings(res.data)).catch(() => {});
  }, [selectedYear]);

  useEffect(() => {
    // Load sub-ledger data when those tabs are activated
    if (activeTab === 'ceo-pnl' && !programmeData) {
      loadProgrammeData();
    } else if (activeTab === 'trainer-subledger' && !trainerSubledger) {
      loadTrainerSubledger();
    } else if (activeTab === 'marketing-subledger' && !marketingSubledger) {
      loadMarketingSubledger();
    } else if (activeTab === 'payroll-subledger' && !payrollSubledger) {
      loadPayrollSubledger();
    } else if (activeTab === 'general-ledger') {
      loadGeneralLedger();
    }
  }, [activeTab, selectedMonth]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [reportRes, incomeRes, expenseRes] = await Promise.all([
        axiosInstance.get(`/finance/profit-loss?year=${selectedYear}`),
        axiosInstance.get(`/finance/manual-income?year=${selectedYear}`),
        axiosInstance.get(`/finance/manual-expenses?year=${selectedYear}`)
      ]);
      setReportData(reportRes.data);
      setManualIncome(incomeRes.data);
      setManualExpenses(expenseRes.data);
      
      // Reset sub-ledger data when year changes
      setProgrammeData(null);
      setTrainerSubledger(null);
      setMarketingSubledger(null);
      setPayrollSubledger(null);
      setGeneralLedger(null);
    } catch (error) {
      toast.error('Failed to load profit/loss data');
    } finally {
      setLoading(false);
    }
  };

  const loadGeneralLedger = async () => {
    try {
      let url = `/finance/general-ledger?year=${selectedYear}`;
      if (selectedMonth) url += `&month=${selectedMonth}`;
      const res = await axiosInstance.get(url);
      setGeneralLedger(res.data);
    } catch (error) {
      toast.error('Failed to load general ledger');
    }
  };

  const loadProgrammeData = async () => {
    try {
      const res = await axiosInstance.get(`/finance/profit-loss/by-programme?year=${selectedYear}`);
      setProgrammeData(res.data);
    } catch (error) {
      toast.error('Failed to load programme breakdown');
    }
  };

  const loadTrainerSubledger = async () => {
    try {
      const res = await axiosInstance.get(`/finance/subledger/trainers?year=${selectedYear}`);
      setTrainerSubledger(res.data);
    } catch (error) {
      toast.error('Failed to load trainer sub-ledger');
    }
  };

  const loadMarketingSubledger = async () => {
    try {
      const res = await axiosInstance.get(`/finance/subledger/marketing?year=${selectedYear}`);
      setMarketingSubledger(res.data);
    } catch (error) {
      toast.error('Failed to load marketing sub-ledger');
    }
  };

  const loadPayrollSubledger = async () => {
    try {
      const res = await axiosInstance.get(`/finance/subledger/payroll?year=${selectedYear}`);
      setPayrollSubledger(res.data);
    } catch (error) {
      toast.error('Failed to load payroll sub-ledger');
    }
  };

  // Print General Ledger
  const handlePrintGL = () => {
    if (!generalLedger) return;
    
    const monthLabel = selectedMonth 
      ? months.find(m => m.value === selectedMonth)?.label 
      : 'Full Year';
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>General Ledger - ${selectedYear} ${monthLabel}</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 20px; font-size: 11px; }
            h1 { text-align: center; color: #1e40af; margin-bottom: 5px; }
            h2 { text-align: center; color: #6b7280; margin-top: 0; font-weight: normal; }
            .header-info { text-align: center; margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
            th { background: #1e40af; color: white; padding: 8px 6px; text-align: left; font-weight: 600; }
            td { padding: 6px; border-bottom: 1px solid #e5e7eb; }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .debit { color: #dc2626; }
            .credit { color: #16a34a; }
            .entry-group { background: #f9fafb; }
            .totals-row { background: #1e40af; color: white; font-weight: bold; }
            .totals-row td { padding: 10px 6px; }
            .section-title { font-size: 14px; font-weight: bold; color: #1e40af; margin: 20px 0 10px; border-bottom: 2px solid #1e40af; padding-bottom: 5px; }
            .balanced { color: #16a34a; font-weight: bold; }
            .unbalanced { color: #dc2626; font-weight: bold; }
            .trial-balance th { background: #059669; }
            @media print { 
              body { margin: 0; } 
              .no-print { display: none; }
              @page { size: A4 landscape; margin: 10mm; }
            }
          </style>
        </head>
        <body>
          <h1>GENERAL LEDGER</h1>
          <h2>${selectedYear} - ${monthLabel}</h2>
          <div class="header-info">
            <p>Generated: ${new Date().toLocaleString('en-MY')}</p>
          </div>
          
          <div class="section-title">Journal Entries</div>
          <table>
            <thead>
              <tr>
                <th style="width: 60px;">Entry #</th>
                <th style="width: 80px;">Date</th>
                <th style="width: 80px;">Reference</th>
                <th style="width: 70px;">Account</th>
                <th>Account Name</th>
                <th>Description</th>
                <th class="text-right" style="width: 90px;">Debit (RM)</th>
                <th class="text-right" style="width: 90px;">Credit (RM)</th>
              </tr>
            </thead>
            <tbody>
              ${(generalLedger.entries || []).map(e => `
                <tr>
                  <td class="text-center">${e.entry_id}</td>
                  <td>${e.date}</td>
                  <td>${e.reference}</td>
                  <td>${e.account_code}</td>
                  <td>${e.account_name}</td>
                  <td>${e.description}</td>
                  <td class="text-right debit">${e.debit > 0 ? e.debit.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : ''}</td>
                  <td class="text-right credit">${e.credit > 0 ? e.credit.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : ''}</td>
                </tr>
              `).join('')}
            </tbody>
            <tfoot>
              <tr class="totals-row">
                <td colspan="6" class="text-right">TOTALS:</td>
                <td class="text-right">${generalLedger.totals?.total_debit?.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td class="text-right">${generalLedger.totals?.total_credit?.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              </tr>
              <tr>
                <td colspan="8" class="text-center ${generalLedger.totals?.is_balanced ? 'balanced' : 'unbalanced'}">
                  ${generalLedger.totals?.is_balanced ? '✓ BALANCED' : '✗ UNBALANCED'}
                </td>
              </tr>
            </tfoot>
          </table>
          
          <div class="section-title">Trial Balance</div>
          <table class="trial-balance">
            <thead>
              <tr>
                <th>Account Code</th>
                <th>Account Name</th>
                <th>Type</th>
                <th class="text-right">Debit (RM)</th>
                <th class="text-right">Credit (RM)</th>
                <th class="text-right">Net (RM)</th>
              </tr>
            </thead>
            <tbody>
              ${(generalLedger.trial_balance || []).map(tb => `
                <tr>
                  <td>${tb.account_code}</td>
                  <td>${tb.account_name}</td>
                  <td>${tb.account_type}</td>
                  <td class="text-right">${tb.debit > 0 ? tb.debit.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}</td>
                  <td class="text-right">${tb.credit > 0 ? tb.credit.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}</td>
                  <td class="text-right" style="font-weight: bold; ${tb.net >= 0 ? 'color: #dc2626;' : 'color: #16a34a;'}">${tb.net.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
          
          <script>window.onload = function() { window.print(); }</script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  // Download GL as CSV
  const handleDownloadGL = () => {
    if (!generalLedger) return;
    
    const monthLabel = selectedMonth 
      ? months.find(m => m.value === selectedMonth)?.label 
      : 'Full_Year';
    
    // Build CSV content
    let csv = 'Entry #,Date,Reference,Account Code,Account Name,Description,Debit,Credit\n';
    
    for (const e of generalLedger.entries || []) {
      csv += `${e.entry_id},${e.date},${e.reference},${e.account_code},"${e.account_name}","${e.description}",${e.debit || ''},${e.credit || ''}\n`;
    }
    
    csv += `\n,,,,,TOTALS:,${generalLedger.totals?.total_debit || 0},${generalLedger.totals?.total_credit || 0}\n`;
    csv += `\n\nTRIAL BALANCE\n`;
    csv += 'Account Code,Account Name,Type,Debit,Credit,Net\n';
    
    for (const tb of generalLedger.trial_balance || []) {
      csv += `${tb.account_code},"${tb.account_name}",${tb.account_type},${tb.debit || ''},${tb.credit || ''},${tb.net || ''}\n`;
    }
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `General_Ledger_${selectedYear}_${monthLabel}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleAddIncome = async () => {
    if (!entryForm.description || !entryForm.amount) {
      toast.error('Please fill in description and amount');
      return;
    }
    try {
      await axiosInstance.post('/finance/manual-income', {
        ...entryForm,
        amount: parseFloat(entryForm.amount),
        category: entryForm.category || 'Other Income'
      });
      toast.success('Income entry added');
      setShowIncomeDialog(false);
      resetForm();
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add income');
    }
  };

  const handleAddExpense = async () => {
    if (!entryForm.description || !entryForm.amount) {
      toast.error('Please fill in description and amount');
      return;
    }
    try {
      await axiosInstance.post('/finance/manual-expense', {
        ...entryForm,
        amount: parseFloat(entryForm.amount),
        category: entryForm.category || 'Other'
      });
      toast.success('Expense entry added');
      setShowExpenseDialog(false);
      resetForm();
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add expense');
    }
  };

  const handleDeleteIncome = async (id) => {
    if (!confirm('Delete this income entry?')) return;
    try {
      await axiosInstance.delete(`/finance/manual-income/${id}`);
      toast.success('Entry deleted');
      loadData();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const handleDeleteExpense = async (id) => {
    if (!confirm('Delete this expense entry?')) return;
    try {
      await axiosInstance.delete(`/finance/manual-expense/${id}`);
      toast.success('Entry deleted');
      loadData();
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const resetForm = () => {
    setEntryForm({
      description: '',
      amount: '',
      category: '',
      date: new Date().toISOString().split('T')[0],
      notes: ''
    });
  };

  const toggleRow = (id) => {
    setExpandedRows(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const formatCurrency = (val) => `RM ${(val || 0).toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const ytd = reportData?.ytd_summary || {};
  const expBreakdown = reportData?.expense_breakdown || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-blue-600" />
            Profit & Loss Ledger
          </h2>
          <p className="text-gray-500">Track income, expenses, and profitability</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedYear.toString()} onValueChange={(v) => setSelectedYear(parseInt(v))}>
            <SelectTrigger className="w-32">
              <Calendar className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {years.map((y) => (
                <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* YTD Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <CardContent className="pt-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-green-600 font-medium">Total Income (YTD)</p>
                <p className="text-2xl font-bold text-green-700">{formatCurrency(ytd.total_income)}</p>
              </div>
              <ArrowUpRight className="w-8 h-8 text-green-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-red-50 to-red-100 border-red-200">
          <CardContent className="pt-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-red-600 font-medium">Total Expenses (YTD)</p>
                <p className="text-2xl font-bold text-red-700">{formatCurrency(ytd.total_expenses)}</p>
              </div>
              <ArrowDownRight className="w-8 h-8 text-red-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card className={`bg-gradient-to-br ${ytd.net_profit >= 0 ? 'from-blue-50 to-blue-100 border-blue-200' : 'from-orange-50 to-orange-100 border-orange-200'}`}>
          <CardContent className="pt-6">
            <div className="flex justify-between items-start">
              <div>
                <p className={`text-sm font-medium ${ytd.net_profit >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>Net Profit (YTD)</p>
                <p className={`text-2xl font-bold ${ytd.net_profit >= 0 ? 'text-blue-700' : 'text-orange-700'}`}>
                  {formatCurrency(ytd.net_profit)}
                </p>
              </div>
              {ytd.net_profit >= 0 ? (
                <TrendingUp className="w-8 h-8 text-blue-500 opacity-50" />
              ) : (
                <TrendingDown className="w-8 h-8 text-orange-500 opacity-50" />
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
          <CardContent className="pt-6">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-purple-600 font-medium">Profit Margin</p>
                <p className="text-2xl font-bold text-purple-700">{ytd.profit_margin || 0}%</p>
              </div>
              <PieChart className="w-8 h-8 text-purple-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex flex-wrap gap-1 h-auto w-full justify-start bg-gray-100 p-2 rounded-lg">
          <TabsTrigger value="auditor-pnl" className="text-indigo-600">
            <FileText className="w-4 h-4 mr-1" />
            P&L Statement
          </TabsTrigger>
          <TabsTrigger value="ceo-pnl" className="text-blue-600">
            <Briefcase className="w-4 h-4 mr-1" />
            P&L by Programme
          </TabsTrigger>
          <TabsTrigger value="yoy-comparison" className="text-purple-600">
            <TrendingUp className="w-4 h-4 mr-1" />
            YoY Comparison
          </TabsTrigger>
          <TabsTrigger value="ar-aging" className="text-rose-600">
            <Calendar className="w-4 h-4 mr-1" />
            Receivables Aging
          </TabsTrigger>
          <TabsTrigger value="overview">Monthly Overview</TabsTrigger>
          <TabsTrigger value="general-ledger" className="text-emerald-600">
            <BookOpen className="w-4 h-4 mr-1" />
            General Ledger
          </TabsTrigger>
          <TabsTrigger value="expenses">Expense Breakdown</TabsTrigger>
          <TabsTrigger value="trainer-subledger">
            <Users className="w-4 h-4 mr-1" />
            Trainers
          </TabsTrigger>
          <TabsTrigger value="marketing-subledger">
            <UserCheck className="w-4 h-4 mr-1" />
            Marketing
          </TabsTrigger>
          <TabsTrigger value="payroll-subledger">
            <Building2 className="w-4 h-4 mr-1" />
            Payroll
          </TabsTrigger>
          <TabsTrigger value="manual-income">Manual Income</TabsTrigger>
          <TabsTrigger value="manual-expenses">Manual Expenses</TabsTrigger>
        </TabsList>

        {/* Monthly Overview Tab */}
        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Monthly P&L Comparison - {selectedYear}</CardTitle>
              <CardDescription>Month-by-month income, expenses, and net profit</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="text-left p-3 font-semibold">Month</th>
                      <th className="text-right p-3 font-semibold text-green-600">Income</th>
                      <th className="text-right p-3 font-semibold text-red-600">Expenses</th>
                      <th className="text-right p-3 font-semibold text-blue-600">Net Profit</th>
                      <th className="text-center p-3 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(reportData?.monthly_breakdown || []).map((month) => (
                      <tr key={month.month} className="border-b hover:bg-gray-50">
                        <td className="p-3 font-medium">{month.month_name}</td>
                        <td className="p-3 text-right text-green-600">{formatCurrency(month.income.total)}</td>
                        <td className="p-3 text-right text-red-600">{formatCurrency(month.expenses.total)}</td>
                        <td className={`p-3 text-right font-semibold ${month.net_profit >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>
                          {formatCurrency(month.net_profit)}
                        </td>
                        <td className="p-3 text-center">
                          {month.net_profit > 0 ? (
                            <Badge className="bg-green-100 text-green-700">Profit</Badge>
                          ) : month.net_profit < 0 ? (
                            <Badge className="bg-red-100 text-red-700">Loss</Badge>
                          ) : (
                            <Badge variant="outline">Break-even</Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-gray-100 font-bold">
                      <td className="p-3">TOTAL (YTD)</td>
                      <td className="p-3 text-right text-green-700">{formatCurrency(ytd.total_income)}</td>
                      <td className="p-3 text-right text-red-700">{formatCurrency(ytd.total_expenses)}</td>
                      <td className={`p-3 text-right ${ytd.net_profit >= 0 ? 'text-blue-700' : 'text-orange-700'}`}>
                        {formatCurrency(ytd.net_profit)}
                      </td>
                      <td className="p-3 text-center">
                        <Badge className={ytd.net_profit >= 0 ? 'bg-green-600' : 'bg-red-600'}>
                          {ytd.profit_margin}% Margin
                        </Badge>
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* CEO P&L Tab - Programme Breakdown */}
        <TabsContent value="ceo-pnl">
          <CEOPnLTab
            selectedYear={selectedYear}
            programmeData={programmeData}
            expandedRows={expandedRows}
            toggleRow={toggleRow}
            formatCurrency={formatCurrency}
            companySettings={companySettings}
          />
        </TabsContent>

        {/* Auditor P&L Tab */}
        <TabsContent value="auditor-pnl">
          <AuditorPnLTab selectedYear={selectedYear} companySettings={companySettings} />
        </TabsContent>

        {/* Year-over-Year Comparison Tab */}
        <TabsContent value="yoy-comparison">
          <YoYComparisonTab
            selectedYear={selectedYear}
            companySettings={companySettings}
          />
        </TabsContent>

        {/* AR Aging Tab */}
        <TabsContent value="ar-aging">
          <ARAgingTab formatCurrency={formatCurrency} companySettings={companySettings} />
        </TabsContent>


        {/* General Ledger Tab */}
        <TabsContent value="general-ledger">
          <GeneralLedgerTab
            selectedYear={selectedYear}
            selectedMonth={selectedMonth}
            setSelectedMonth={setSelectedMonth}
            generalLedger={generalLedger}
            months={months}
            formatCurrency={formatCurrency}
            handlePrintGL={handlePrintGL}
            handleDownloadGL={handleDownloadGL}
          />
        </TabsContent>

        {/* Expense Breakdown Tab */}
        <TabsContent value="expenses">
          <Card>
            <CardHeader>
              <CardTitle>Expense Breakdown - {selectedYear}</CardTitle>
              <CardDescription>Expenses by category</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(expBreakdown).map(([category, amount]) => {
                  const labels = {
                    payroll: 'Staff Payroll',
                    session_workers: 'Trainers & Coordinators',
                    marketing_commissions: 'Marketing Commissions',
                    session_expenses: 'Session Expenses (F&B, etc)',
                    petty_cash: 'Petty Cash',
                    manual: 'Manual Entries'
                  };
                  const colors = {
                    payroll: 'bg-blue-100 text-blue-700 border-blue-200',
                    session_workers: 'bg-purple-100 text-purple-700 border-purple-200',
                    marketing_commissions: 'bg-pink-100 text-pink-700 border-pink-200',
                    session_expenses: 'bg-orange-100 text-orange-700 border-orange-200',
                    petty_cash: 'bg-green-100 text-green-700 border-green-200',
                    manual: 'bg-gray-100 text-gray-700 border-gray-200'
                  };
                  const percentage = ytd.total_expenses > 0 ? ((amount / ytd.total_expenses) * 100).toFixed(1) : 0;
                  
                  return (
                    <div key={category} className={`p-4 rounded-lg border ${colors[category] || 'bg-gray-50'}`}>
                      <div className="flex justify-between items-start mb-2">
                        <span className="font-medium text-sm">{labels[category] || category}</span>
                        <Badge variant="outline">{percentage}%</Badge>
                      </div>
                      <p className="text-xl font-bold">{formatCurrency(amount)}</p>
                      <div className="mt-2 h-2 bg-white/50 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-current opacity-50 rounded-full transition-all"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trainer Sub-ledger Tab */}
        <TabsContent value="trainer-subledger">
          <TrainerSubledgerTab
            selectedYear={selectedYear}
            trainerSubledger={trainerSubledger}
            expandedRows={expandedRows}
            toggleRow={toggleRow}
            formatCurrency={formatCurrency}
          />
        </TabsContent>

        {/* Marketing Sub-ledger Tab */}
        <TabsContent value="marketing-subledger">
          <MarketingSubledgerTab
            selectedYear={selectedYear}
            marketingSubledger={marketingSubledger}
            expandedRows={expandedRows}
            toggleRow={toggleRow}
            formatCurrency={formatCurrency}
          />
        </TabsContent>

        {/* Payroll Sub-ledger Tab */}
        <TabsContent value="payroll-subledger">
          <PayrollSubledgerTab
            selectedYear={selectedYear}
            payrollSubledger={payrollSubledger}
            expandedRows={expandedRows}
            toggleRow={toggleRow}
            formatCurrency={formatCurrency}
          />
        </TabsContent>

        {/* Manual Income Tab */}
        <TabsContent value="manual-income">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Manual Income Entries</CardTitle>
                <CardDescription>One-off income not from invoices</CardDescription>
              </div>
              <Button onClick={() => setShowIncomeDialog(true)} className="bg-green-600 hover:bg-green-700">
                <Plus className="w-4 h-4 mr-2" /> Add Income
              </Button>
            </CardHeader>
            <CardContent>
              {manualIncome.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <DollarSign className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No manual income entries for {selectedYear}</p>
                  <p className="text-sm">Click &quot;Add Income&quot; to record additional revenue</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {manualIncome.map((entry) => (
                    <div key={entry.id} className="flex items-center justify-between p-4 bg-green-50 rounded-lg border border-green-200">
                      <div>
                        <p className="font-medium">{entry.description}</p>
                        <p className="text-sm text-gray-500">{entry.date} • {entry.category}</p>
                        {entry.notes && <p className="text-xs text-gray-400 mt-1">{entry.notes}</p>}
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-green-600">{formatCurrency(entry.amount)}</span>
                        <Button size="sm" variant="ghost" onClick={() => handleDeleteIncome(entry.id)}>
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Manual Expenses Tab */}
        <TabsContent value="manual-expenses">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Manual Expense Entries</CardTitle>
                <CardDescription>Additional expenses not captured elsewhere</CardDescription>
              </div>
              <Button onClick={() => setShowExpenseDialog(true)} className="bg-red-600 hover:bg-red-700">
                <Plus className="w-4 h-4 mr-2" /> Add Expense
              </Button>
            </CardHeader>
            <CardContent>
              {manualExpenses.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <DollarSign className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No manual expense entries for {selectedYear}</p>
                  <p className="text-sm">Click &quot;Add Expense&quot; to record additional costs</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {manualExpenses.map((entry) => (
                    <div key={entry.id} className="flex items-center justify-between p-4 bg-red-50 rounded-lg border border-red-200">
                      <div>
                        <p className="font-medium">{entry.description}</p>
                        <p className="text-sm text-gray-500">{entry.date} • {entry.category}</p>
                        {entry.notes && <p className="text-xs text-gray-400 mt-1">{entry.notes}</p>}
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-bold text-red-600">{formatCurrency(entry.amount)}</span>
                        <Button size="sm" variant="ghost" onClick={() => handleDeleteExpense(entry.id)}>
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Add Income Dialog */}
      <Dialog open={showIncomeDialog} onOpenChange={setShowIncomeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Manual Income</DialogTitle>
            <DialogDescription>Record a one-off income entry</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Description *</Label>
              <Input 
                value={entryForm.description}
                onChange={(e) => setEntryForm({ ...entryForm, description: e.target.value })}
                placeholder="e.g., Sponsorship from ABC Corp"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Amount (RM) *</Label>
                <Input 
                  type="number"
                  value={entryForm.amount}
                  onChange={(e) => setEntryForm({ ...entryForm, amount: e.target.value })}
                  placeholder="0.00"
                />
              </div>
              <div>
                <Label>Date *</Label>
                <Input 
                  type="date"
                  value={entryForm.date}
                  onChange={(e) => setEntryForm({ ...entryForm, date: e.target.value })}
                />
              </div>
            </div>
            <div>
              <Label>Category</Label>
              <Select value={entryForm.category} onValueChange={(v) => setEntryForm({ ...entryForm, category: v })}>
                <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                <SelectContent>
                  {incomeCategories.map((cat) => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Notes</Label>
              <Input 
                value={entryForm.notes}
                onChange={(e) => setEntryForm({ ...entryForm, notes: e.target.value })}
                placeholder="Additional notes (optional)"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setShowIncomeDialog(false); resetForm(); }}>Cancel</Button>
              <Button onClick={handleAddIncome} className="bg-green-600 hover:bg-green-700">Add Income</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Add Expense Dialog */}
      <Dialog open={showExpenseDialog} onOpenChange={setShowExpenseDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Manual Expense</DialogTitle>
            <DialogDescription>Record a one-off expense entry</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Description *</Label>
              <Input 
                value={entryForm.description}
                onChange={(e) => setEntryForm({ ...entryForm, description: e.target.value })}
                placeholder="e.g., Equipment repair"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Amount (RM) *</Label>
                <Input 
                  type="number"
                  value={entryForm.amount}
                  onChange={(e) => setEntryForm({ ...entryForm, amount: e.target.value })}
                  placeholder="0.00"
                />
              </div>
              <div>
                <Label>Date *</Label>
                <Input 
                  type="date"
                  value={entryForm.date}
                  onChange={(e) => setEntryForm({ ...entryForm, date: e.target.value })}
                />
              </div>
            </div>
            <div>
              <Label>Category</Label>
              <Select value={entryForm.category} onValueChange={(v) => setEntryForm({ ...entryForm, category: v })}>
                <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                <SelectContent>
                  {expenseCategories.map((cat) => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Notes</Label>
              <Input 
                value={entryForm.notes}
                onChange={(e) => setEntryForm({ ...entryForm, notes: e.target.value })}
                placeholder="Additional notes (optional)"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setShowExpenseDialog(false); resetForm(); }}>Cancel</Button>
              <Button onClick={handleAddExpense} className="bg-red-600 hover:bg-red-700">Add Expense</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProfitLossLedger;
