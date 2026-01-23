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
  BookOpen, Printer, FileSpreadsheet
} from 'lucide-react';
import { CEOPnLTab } from './ledger/CEOPnLTab';
import { GeneralLedgerTab } from './ledger/GeneralLedgerTab';

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
  const [activeTab, setActiveTab] = useState('overview');
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
                  <td class="text-right debit">${e.debit > 0 ? e.debit.toLocaleString('en-MY', { minimumFractionDigits: 2 }) : ''}</td>
                  <td class="text-right credit">${e.credit > 0 ? e.credit.toLocaleString('en-MY', { minimumFractionDigits: 2 }) : ''}</td>
                </tr>
              `).join('')}
            </tbody>
            <tfoot>
              <tr class="totals-row">
                <td colspan="6" class="text-right">TOTALS:</td>
                <td class="text-right">${generalLedger.totals?.total_debit?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                <td class="text-right">${generalLedger.totals?.total_credit?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
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
                  <td class="text-right">${tb.debit > 0 ? tb.debit.toLocaleString('en-MY', { minimumFractionDigits: 2 }) : '-'}</td>
                  <td class="text-right">${tb.credit > 0 ? tb.credit.toLocaleString('en-MY', { minimumFractionDigits: 2 }) : '-'}</td>
                  <td class="text-right" style="font-weight: bold; ${tb.net >= 0 ? 'color: #dc2626;' : 'color: #16a34a;'}">${tb.net.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
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

  const formatCurrency = (val) => `RM ${(val || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}`;

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
          <TabsTrigger value="overview">Monthly Overview</TabsTrigger>
          <TabsTrigger value="ceo-pnl" className="text-blue-600">
            <Briefcase className="w-4 h-4 mr-1" />
            CEO P&L
          </TabsTrigger>
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
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-blue-600" />
                CEO P&L View - {selectedYear}
              </CardTitle>
              <CardDescription>Profitability by programme with margins and insights</CardDescription>
            </CardHeader>
            <CardContent>
              {!programmeData ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Programme Breakdown Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-blue-50">
                          <th className="text-left p-3 font-semibold">Programme</th>
                          <th className="text-center p-3 font-semibold">Sessions</th>
                          <th className="text-right p-3 font-semibold text-green-600">Revenue</th>
                          <th className="text-right p-3 font-semibold text-red-600">Direct Costs</th>
                          <th className="text-right p-3 font-semibold text-blue-600">Gross Profit</th>
                          <th className="text-center p-3 font-semibold">Margin %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(programmeData?.programmes || []).map((prog) => (
                          <React.Fragment key={prog.programme_id}>
                            <tr 
                              className="border-b hover:bg-gray-50 cursor-pointer"
                              onClick={() => toggleRow(prog.programme_id)}
                            >
                              <td className="p-3 font-medium flex items-center gap-2">
                                {expandedRows[prog.programme_id] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                                {prog.programme_name}
                              </td>
                              <td className="p-3 text-center">
                                <Badge variant="outline">{prog.session_count}</Badge>
                              </td>
                              <td className="p-3 text-right text-green-600">{formatCurrency(prog.income)}</td>
                              <td className="p-3 text-right text-red-600">{formatCurrency(prog.expenses.total)}</td>
                              <td className={`p-3 text-right font-semibold ${prog.gross_profit >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>
                                {formatCurrency(prog.gross_profit)}
                              </td>
                              <td className="p-3 text-center">
                                <Badge className={prog.gross_margin_pct >= 30 ? 'bg-green-100 text-green-700' : prog.gross_margin_pct >= 15 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}>
                                  {prog.gross_margin_pct}%
                                </Badge>
                              </td>
                            </tr>
                            {expandedRows[prog.programme_id] && (
                              <tr className="bg-gray-50">
                                <td colSpan={6} className="p-4">
                                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                    <div className="bg-white p-3 rounded border">
                                      <p className="text-gray-500 text-xs">Trainer Fees</p>
                                      <p className="font-semibold">{formatCurrency(prog.expenses.trainer_fees)}</p>
                                    </div>
                                    <div className="bg-white p-3 rounded border">
                                      <p className="text-gray-500 text-xs">Coordinator Fees</p>
                                      <p className="font-semibold">{formatCurrency(prog.expenses.coordinator_fees)}</p>
                                    </div>
                                    <div className="bg-white p-3 rounded border">
                                      <p className="text-gray-500 text-xs">Marketing Commission</p>
                                      <p className="font-semibold">{formatCurrency(prog.expenses.marketing_commissions)}</p>
                                    </div>
                                    <div className="bg-white p-3 rounded border">
                                      <p className="text-gray-500 text-xs">Session Expenses</p>
                                      <p className="font-semibold">{formatCurrency(prog.expenses.session_expenses)}</p>
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </React.Fragment>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="bg-blue-100 font-bold">
                          <td className="p-3" colSpan={2}>PROGRAMME TOTAL</td>
                          <td className="p-3 text-right text-green-700">{formatCurrency(programmeData?.summary?.total_programme_income)}</td>
                          <td className="p-3 text-right text-red-700">{formatCurrency(programmeData?.summary?.total_direct_costs)}</td>
                          <td className="p-3 text-right text-blue-700">{formatCurrency(programmeData?.summary?.gross_profit)}</td>
                          <td className="p-3 text-center">
                            <Badge className="bg-blue-600 text-white">{programmeData?.summary?.gross_margin_pct}%</Badge>
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>

                  {/* Summary Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <Card className="bg-green-50 border-green-200">
                      <CardContent className="pt-4">
                        <p className="text-xs text-green-600 font-medium">Total Revenue</p>
                        <p className="text-xl font-bold text-green-700">{formatCurrency(programmeData?.summary?.total_income)}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          Programme: {formatCurrency(programmeData?.summary?.total_programme_income)} | 
                          Other: {formatCurrency(programmeData?.summary?.other_income)}
                        </p>
                      </CardContent>
                    </Card>

                    <Card className="bg-red-50 border-red-200">
                      <CardContent className="pt-4">
                        <p className="text-xs text-red-600 font-medium">Total Expenses</p>
                        <p className="text-xl font-bold text-red-700">{formatCurrency(programmeData?.summary?.total_expenses)}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          Direct: {formatCurrency(programmeData?.summary?.total_direct_costs)} | 
                          Overhead: {formatCurrency(programmeData?.summary?.overhead?.total)}
                        </p>
                      </CardContent>
                    </Card>

                    <Card className="bg-blue-50 border-blue-200">
                      <CardContent className="pt-4">
                        <p className="text-xs text-blue-600 font-medium">Net Profit</p>
                        <p className={`text-xl font-bold ${programmeData?.summary?.net_profit >= 0 ? 'text-blue-700' : 'text-orange-700'}`}>
                          {formatCurrency(programmeData?.summary?.net_profit)}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          Net Margin: {programmeData?.summary?.net_margin_pct}%
                        </p>
                      </CardContent>
                    </Card>

                    <Card className="bg-purple-50 border-purple-200">
                      <CardContent className="pt-4">
                        <p className="text-xs text-purple-600 font-medium">Overhead Breakdown</p>
                        <div className="text-xs mt-1 space-y-1">
                          <div className="flex justify-between">
                            <span>Payroll:</span>
                            <span className="font-semibold">{formatCurrency(programmeData?.summary?.overhead?.payroll)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Petty Cash:</span>
                            <span className="font-semibold">{formatCurrency(programmeData?.summary?.overhead?.petty_cash)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Manual:</span>
                            <span className="font-semibold">{formatCurrency(programmeData?.summary?.overhead?.manual)}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* General Ledger Tab */}
        <TabsContent value="general-ledger">
          <Card>
            <CardHeader className="flex flex-row items-start justify-between flex-wrap gap-4">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-emerald-600" />
                  General Ledger - {selectedYear}
                </CardTitle>
                <CardDescription>Double-entry journal with trial balance</CardDescription>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <Select value={selectedMonth?.toString() || 'all'} onValueChange={(v) => setSelectedMonth(v === 'all' ? null : parseInt(v))}>
                  <SelectTrigger className="w-36">
                    <SelectValue placeholder="All Months" />
                  </SelectTrigger>
                  <SelectContent>
                    {months.map((m) => (
                      <SelectItem key={m.value || 'all'} value={m.value?.toString() || 'all'}>{m.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="outline" onClick={handlePrintGL} disabled={!generalLedger}>
                  <Printer className="w-4 h-4 mr-2" /> Print
                </Button>
                <Button variant="outline" onClick={handleDownloadGL} disabled={!generalLedger} className="text-emerald-600 border-emerald-300 hover:bg-emerald-50">
                  <FileSpreadsheet className="w-4 h-4 mr-2" /> Download CSV
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {!generalLedger ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Status Badge */}
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-500">
                      {generalLedger.entries?.length || 0} journal entries
                    </p>
                    <Badge className={generalLedger.totals?.is_balanced ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                      {generalLedger.totals?.is_balanced ? '✓ Balanced' : '✗ Unbalanced'}
                    </Badge>
                  </div>

                  {/* Journal Entries Table */}
                  <div className="overflow-x-auto border rounded-lg">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-emerald-50 border-b">
                          <th className="text-center p-2 font-semibold w-16">#</th>
                          <th className="text-left p-2 font-semibold w-24">Date</th>
                          <th className="text-left p-2 font-semibold w-24">Reference</th>
                          <th className="text-left p-2 font-semibold w-20">Account</th>
                          <th className="text-left p-2 font-semibold">Account Name</th>
                          <th className="text-left p-2 font-semibold">Description</th>
                          <th className="text-right p-2 font-semibold w-24 text-red-600">Debit</th>
                          <th className="text-right p-2 font-semibold w-24 text-green-600">Credit</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(generalLedger.entries || []).slice(0, 200).map((entry, idx) => (
                          <tr key={idx} className={`border-b hover:bg-gray-50 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}`}>
                            <td className="p-2 text-center text-gray-400">{entry.entry_id}</td>
                            <td className="p-2">{entry.date}</td>
                            <td className="p-2 font-mono text-xs">{entry.reference}</td>
                            <td className="p-2 font-mono">{entry.account_code}</td>
                            <td className="p-2">{entry.account_name}</td>
                            <td className="p-2 text-gray-600">{entry.description}</td>
                            <td className="p-2 text-right text-red-600 font-mono">
                              {entry.debit > 0 ? formatCurrency(entry.debit) : ''}
                            </td>
                            <td className="p-2 text-right text-green-600 font-mono">
                              {entry.credit > 0 ? formatCurrency(entry.credit) : ''}
                            </td>
                          </tr>
                        ))}
                        {generalLedger.entries?.length > 200 && (
                          <tr className="bg-yellow-50">
                            <td colSpan={8} className="p-3 text-center text-yellow-700">
                              Showing first 200 of {generalLedger.entries.length} entries. Download CSV for full data.
                            </td>
                          </tr>
                        )}
                      </tbody>
                      <tfoot>
                        <tr className="bg-emerald-600 text-white font-bold">
                          <td colSpan={6} className="p-3 text-right">TOTALS:</td>
                          <td className="p-3 text-right">{formatCurrency(generalLedger.totals?.total_debit)}</td>
                          <td className="p-3 text-right">{formatCurrency(generalLedger.totals?.total_credit)}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>

                  {/* Trial Balance */}
                  <div>
                    <h4 className="font-semibold text-emerald-700 mb-3 flex items-center gap-2">
                      <BarChart3 className="w-4 h-4" /> Trial Balance
                    </h4>
                    <div className="overflow-x-auto border rounded-lg">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-gray-100 border-b">
                            <th className="text-left p-2 font-semibold">Account Code</th>
                            <th className="text-left p-2 font-semibold">Account Name</th>
                            <th className="text-left p-2 font-semibold">Type</th>
                            <th className="text-right p-2 font-semibold text-red-600">Debit</th>
                            <th className="text-right p-2 font-semibold text-green-600">Credit</th>
                            <th className="text-right p-2 font-semibold">Net</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(generalLedger.trial_balance || []).map((tb) => (
                            <tr key={tb.account_code} className="border-b hover:bg-gray-50">
                              <td className="p-2 font-mono">{tb.account_code}</td>
                              <td className="p-2">{tb.account_name}</td>
                              <td className="p-2">
                                <Badge variant="outline" className={
                                  tb.account_type === 'Asset' ? 'border-blue-300 text-blue-600' :
                                  tb.account_type === 'Liability' ? 'border-purple-300 text-purple-600' :
                                  tb.account_type === 'Income' ? 'border-green-300 text-green-600' :
                                  'border-red-300 text-red-600'
                                }>{tb.account_type}</Badge>
                              </td>
                              <td className="p-2 text-right font-mono text-red-600">
                                {tb.debit > 0 ? formatCurrency(tb.debit) : '-'}
                              </td>
                              <td className="p-2 text-right font-mono text-green-600">
                                {tb.credit > 0 ? formatCurrency(tb.credit) : '-'}
                              </td>
                              <td className={`p-2 text-right font-mono font-semibold ${tb.net >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                                {formatCurrency(Math.abs(tb.net))} {tb.net >= 0 ? 'DR' : 'CR'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
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
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5 text-purple-600" />
                Trainer & Coordinator Sub-ledger - {selectedYear}
              </CardTitle>
              <CardDescription>Earnings breakdown by trainer and coordinator</CardDescription>
            </CardHeader>
            <CardContent>
              {!trainerSubledger ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Trainers */}
                  <div>
                    <h4 className="font-semibold text-purple-700 mb-3 flex items-center gap-2">
                      <Users className="w-4 h-4" /> Trainers
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b bg-purple-50">
                            <th className="text-left p-3">Name</th>
                            <th className="text-right p-3">Earned</th>
                            <th className="text-right p-3">Paid</th>
                            <th className="text-right p-3">Balance</th>
                            <th className="w-10"></th>
                          </tr>
                        </thead>
                        <tbody>
                          {(trainerSubledger?.trainers || []).map((t) => (
                            <React.Fragment key={t.user_id}>
                              <tr className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => toggleRow(`trainer-${t.user_id}`)}>
                                <td className="p-3 font-medium flex items-center gap-2">
                                  {expandedRows[`trainer-${t.user_id}`] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                                  {t.name}
                                </td>
                                <td className="p-3 text-right text-green-600">{formatCurrency(t.total_earned)}</td>
                                <td className="p-3 text-right text-blue-600">{formatCurrency(t.total_paid)}</td>
                                <td className={`p-3 text-right font-semibold ${t.balance > 0 ? 'text-orange-600' : 'text-gray-600'}`}>
                                  {formatCurrency(t.balance)}
                                </td>
                                <td className="p-3">
                                  <Badge variant="outline">{t.sessions?.length || 0}</Badge>
                                </td>
                              </tr>
                              {expandedRows[`trainer-${t.user_id}`] && t.sessions?.length > 0 && (
                                <tr className="bg-gray-50">
                                  <td colSpan={5} className="p-4">
                                    <div className="text-xs space-y-2 max-h-40 overflow-y-auto">
                                      {t.sessions.slice(0, 10).map((s, idx) => (
                                        <div key={idx} className="flex justify-between items-center bg-white p-2 rounded border">
                                          <span>{s.date} - {s.programme}</span>
                                          <div className="flex items-center gap-2">
                                            <span className="font-semibold">{formatCurrency(s.amount)}</span>
                                            <Badge className={s.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}>
                                              {s.status}
                                            </Badge>
                                          </div>
                                        </div>
                                      ))}
                                      {t.sessions.length > 10 && <p className="text-gray-500 text-center">...and {t.sessions.length - 10} more</p>}
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr className="bg-purple-100 font-bold">
                            <td className="p-3">TOTAL</td>
                            <td className="p-3 text-right text-green-700">{formatCurrency(trainerSubledger?.totals?.trainer_earned)}</td>
                            <td className="p-3 text-right text-blue-700">{formatCurrency(trainerSubledger?.totals?.trainer_paid)}</td>
                            <td className="p-3 text-right text-orange-700">{formatCurrency(trainerSubledger?.totals?.trainer_balance)}</td>
                            <td></td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>

                  {/* Coordinators */}
                  <div>
                    <h4 className="font-semibold text-blue-700 mb-3 flex items-center gap-2">
                      <UserCheck className="w-4 h-4" /> Coordinators
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b bg-blue-50">
                            <th className="text-left p-3">Name</th>
                            <th className="text-right p-3">Earned</th>
                            <th className="text-right p-3">Paid</th>
                            <th className="text-right p-3">Balance</th>
                            <th className="w-10"></th>
                          </tr>
                        </thead>
                        <tbody>
                          {(trainerSubledger?.coordinators || []).map((c) => (
                            <React.Fragment key={c.user_id}>
                              <tr className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => toggleRow(`coord-${c.user_id}`)}>
                                <td className="p-3 font-medium flex items-center gap-2">
                                  {expandedRows[`coord-${c.user_id}`] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                                  {c.name}
                                </td>
                                <td className="p-3 text-right text-green-600">{formatCurrency(c.total_earned)}</td>
                                <td className="p-3 text-right text-blue-600">{formatCurrency(c.total_paid)}</td>
                                <td className={`p-3 text-right font-semibold ${c.balance > 0 ? 'text-orange-600' : 'text-gray-600'}`}>
                                  {formatCurrency(c.balance)}
                                </td>
                                <td className="p-3">
                                  <Badge variant="outline">{c.sessions?.length || 0}</Badge>
                                </td>
                              </tr>
                              {expandedRows[`coord-${c.user_id}`] && c.sessions?.length > 0 && (
                                <tr className="bg-gray-50">
                                  <td colSpan={5} className="p-4">
                                    <div className="text-xs space-y-2 max-h-40 overflow-y-auto">
                                      {c.sessions.slice(0, 10).map((s, idx) => (
                                        <div key={idx} className="flex justify-between items-center bg-white p-2 rounded border">
                                          <span>{s.date} - {s.programme}</span>
                                          <div className="flex items-center gap-2">
                                            <span className="font-semibold">{formatCurrency(s.amount)}</span>
                                            <Badge className={s.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}>
                                              {s.status}
                                            </Badge>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr className="bg-blue-100 font-bold">
                            <td className="p-3">TOTAL</td>
                            <td className="p-3 text-right text-green-700">{formatCurrency(trainerSubledger?.totals?.coordinator_earned)}</td>
                            <td className="p-3 text-right text-blue-700">{formatCurrency(trainerSubledger?.totals?.coordinator_paid)}</td>
                            <td className="p-3 text-right text-orange-700">{formatCurrency(trainerSubledger?.totals?.coordinator_balance)}</td>
                            <td></td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Marketing Sub-ledger Tab */}
        <TabsContent value="marketing-subledger">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-pink-600" />
                Marketing Commission Sub-ledger - {selectedYear}
              </CardTitle>
              <CardDescription>Commission breakdown by marketer</CardDescription>
            </CardHeader>
            <CardContent>
              {!marketingSubledger ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-6 h-6 animate-spin text-pink-600" />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-pink-50">
                        <th className="text-left p-3">Marketer</th>
                        <th className="text-right p-3">Commission</th>
                        <th className="text-right p-3">Paid</th>
                        <th className="text-right p-3">Balance</th>
                        <th className="w-10"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {(marketingSubledger?.marketers || []).map((m) => (
                        <React.Fragment key={m.user_id}>
                          <tr className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => toggleRow(`mkt-${m.user_id}`)}>
                            <td className="p-3 font-medium flex items-center gap-2">
                              {expandedRows[`mkt-${m.user_id}`] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                              {m.name}
                            </td>
                            <td className="p-3 text-right text-green-600">{formatCurrency(m.total_commission)}</td>
                            <td className="p-3 text-right text-blue-600">{formatCurrency(m.total_paid)}</td>
                            <td className={`p-3 text-right font-semibold ${m.balance > 0 ? 'text-orange-600' : 'text-gray-600'}`}>
                              {formatCurrency(m.balance)}
                            </td>
                            <td className="p-3">
                              <Badge variant="outline">{m.clients?.length || 0}</Badge>
                            </td>
                          </tr>
                          {expandedRows[`mkt-${m.user_id}`] && m.clients?.length > 0 && (
                            <tr className="bg-gray-50">
                              <td colSpan={5} className="p-4">
                                <div className="text-xs space-y-2 max-h-40 overflow-y-auto">
                                  {m.clients.slice(0, 10).map((c, idx) => (
                                    <div key={idx} className="flex justify-between items-center bg-white p-2 rounded border">
                                      <span>{c.date} - {c.client} ({c.programme})</span>
                                      <div className="flex items-center gap-2">
                                        <span className="text-gray-500">{c.commission_rate}%</span>
                                        <span className="font-semibold">{formatCurrency(c.amount)}</span>
                                        <Badge className={c.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}>
                                          {c.status}
                                        </Badge>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="bg-pink-100 font-bold">
                        <td className="p-3">TOTAL</td>
                        <td className="p-3 text-right text-green-700">{formatCurrency(marketingSubledger?.totals?.total_commission)}</td>
                        <td className="p-3 text-right text-blue-700">{formatCurrency(marketingSubledger?.totals?.total_paid)}</td>
                        <td className="p-3 text-right text-orange-700">{formatCurrency(marketingSubledger?.totals?.total_balance)}</td>
                        <td></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Payroll Sub-ledger Tab */}
        <TabsContent value="payroll-subledger">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-blue-600" />
                Staff Payroll Register - {selectedYear}
              </CardTitle>
              <CardDescription>Payroll breakdown by employee</CardDescription>
            </CardHeader>
            <CardContent>
              {!payrollSubledger ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-blue-50">
                        <th className="text-left p-3">Employee</th>
                        <th className="text-right p-3">Gross</th>
                        <th className="text-right p-3">EPF</th>
                        <th className="text-right p-3">SOCSO</th>
                        <th className="text-right p-3">EIS</th>
                        <th className="text-right p-3">Net</th>
                        <th className="w-10"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {(payrollSubledger?.employees || []).map((e) => (
                        <React.Fragment key={e.staff_id}>
                          <tr className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => toggleRow(`emp-${e.staff_id}`)}>
                            <td className="p-3 font-medium flex items-center gap-2">
                              {expandedRows[`emp-${e.staff_id}`] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                              <div>
                                <p>{e.name}</p>
                                <p className="text-xs text-gray-500">{e.designation}</p>
                              </div>
                            </td>
                            <td className="p-3 text-right">{formatCurrency(e.total_gross)}</td>
                            <td className="p-3 text-right text-red-600">{formatCurrency(e.total_epf)}</td>
                            <td className="p-3 text-right text-red-600">{formatCurrency(e.total_socso)}</td>
                            <td className="p-3 text-right text-red-600">{formatCurrency(e.total_eis)}</td>
                            <td className="p-3 text-right font-semibold text-green-600">{formatCurrency(e.total_net)}</td>
                            <td className="p-3">
                              <Badge variant="outline">{e.months?.length || 0}mo</Badge>
                            </td>
                          </tr>
                          {expandedRows[`emp-${e.staff_id}`] && e.months?.length > 0 && (
                            <tr className="bg-gray-50">
                              <td colSpan={7} className="p-4">
                                <div className="text-xs overflow-x-auto">
                                  <table className="w-full">
                                    <thead>
                                      <tr className="text-gray-500">
                                        <th className="text-left p-1">Month</th>
                                        <th className="text-right p-1">Gross</th>
                                        <th className="text-right p-1">EPF</th>
                                        <th className="text-right p-1">SOCSO</th>
                                        <th className="text-right p-1">EIS</th>
                                        <th className="text-right p-1">Net</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {e.months.map((m, idx) => (
                                        <tr key={idx} className="border-t">
                                          <td className="p-1">{m.month_name}</td>
                                          <td className="p-1 text-right">{formatCurrency(m.gross)}</td>
                                          <td className="p-1 text-right">{formatCurrency(m.epf)}</td>
                                          <td className="p-1 text-right">{formatCurrency(m.socso)}</td>
                                          <td className="p-1 text-right">{formatCurrency(m.eis)}</td>
                                          <td className="p-1 text-right font-semibold">{formatCurrency(m.net)}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="bg-blue-100 font-bold">
                        <td className="p-3">TOTAL</td>
                        <td className="p-3 text-right">{formatCurrency(payrollSubledger?.totals?.total_gross)}</td>
                        <td className="p-3 text-right text-red-700">{formatCurrency(payrollSubledger?.totals?.total_epf)}</td>
                        <td className="p-3 text-right text-red-700">{formatCurrency(payrollSubledger?.totals?.total_socso)}</td>
                        <td className="p-3 text-right text-red-700">{formatCurrency(payrollSubledger?.totals?.total_eis)}</td>
                        <td className="p-3 text-right text-green-700">{formatCurrency(payrollSubledger?.totals?.total_net)}</td>
                        <td></td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
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
