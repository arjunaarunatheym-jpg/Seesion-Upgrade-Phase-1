/**
 * AccountingTab.jsx
 * Main Accounting section with COA, Journal Entries, Trial Balance, General Ledger, Balance Sheet
 */
import React, { useState, useEffect } from 'react';
import { axiosInstance } from '../../App';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Textarea } from '../ui/textarea';
import { 
  BookOpen, FileText, Calculator, BarChart3, 
  Plus, RefreshCw, Check, X, Eye, Loader2,
  ArrowUpRight, ArrowDownRight, Calendar, Filter,
  Download, ChevronDown, ChevronRight, Building2, Printer
} from 'lucide-react';

const AccountingTab = ({ companySettings }) => {
  const [activeSubTab, setActiveSubTab] = useState('coa');
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);
  
  // Chart of Accounts state
  const [accounts, setAccounts] = useState([]);
  const [groupedAccounts, setGroupedAccounts] = useState({});
  const [showAddAccount, setShowAddAccount] = useState(false);
  const [newAccount, setNewAccount] = useState({
    account_code: '',
    account_name: '',
    account_type: 'Expense',
    account_category: '',
    description: '',
    normal_balance: 'debit'
  });
  
  // Journal Entries state
  const [journalEntries, setJournalEntries] = useState([]);
  const [showJournalDialog, setShowJournalDialog] = useState(false);
  const [selectedJournal, setSelectedJournal] = useState(null);
  const [journalFilter, setJournalFilter] = useState({ year: 2026, month: null, status: null });
  const [newJournal, setNewJournal] = useState({
    date: new Date().toISOString().split('T')[0],
    description: '',
    lines: [
      { account_code: '', debit: 0, credit: 0, memo: '' },
      { account_code: '', debit: 0, credit: 0, memo: '' }
    ]
  });
  
  // Trial Balance state
  const [trialBalance, setTrialBalance] = useState(null);
  const [tbPeriod, setTbPeriod] = useState({ year: 2026, month: new Date().getMonth() + 1 });
  
  // General Ledger state
  const [generalLedger, setGeneralLedger] = useState(null);
  const [glAccount, setGlAccount] = useState('');
  const [glPeriod, setGlPeriod] = useState({ year: 2026, month: null });
  
  // Balance Sheet state
  const [balanceSheet, setBalanceSheet] = useState(null);
  const [bsPeriod, setBsPeriod] = useState({ year: 2026, month: new Date().getMonth() + 1 });
  
  // Accounting P&L state
  const [accountingPL, setAccountingPL] = useState(null);
  const [plPeriod, setPlPeriod] = useState({ year: 2026, month: null });
  
  // Periods state
  const [periods, setPeriods] = useState([]);
  
  // Backfill state
  const [backfillRunning, setBackfillRunning] = useState(false);
  const [backfillResult, setBackfillResult] = useState(null);

  // Check if initialized
  useEffect(() => {
    checkInitialized();
  }, []);

  const checkInitialized = async () => {
    try {
      const response = await axiosInstance.get('/accounting/settings');
      if (response.data && !response.data.message) {
        setInitialized(true);
        loadAccounts();
        loadPeriods();
      }
    } catch (error) {
      setInitialized(false);
    }
  };

  const initializeAccounting = async () => {
    setLoading(true);
    try {
      await axiosInstance.post('/accounting/initialize');
      toast.success('Accounting system initialized successfully');
      setInitialized(true);
      loadAccounts();
      loadPeriods();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to initialize');
    } finally {
      setLoading(false);
    }
  };

  // Load functions
  const loadAccounts = async () => {
    try {
      const response = await axiosInstance.get('/accounting/chart-of-accounts');
      setAccounts(response.data.accounts || []);
      setGroupedAccounts(response.data.grouped || {});
    } catch (error) {
      console.error('Failed to load accounts:', error);
    }
  };

  const loadJournalEntries = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (journalFilter.year) params.append('year', journalFilter.year);
      if (journalFilter.month) params.append('month', journalFilter.month);
      if (journalFilter.status) params.append('status', journalFilter.status);
      
      const response = await axiosInstance.get(`/accounting/journal-entries?${params}`);
      setJournalEntries(response.data.entries || []);
    } catch (error) {
      toast.error('Failed to load journal entries');
    } finally {
      setLoading(false);
    }
  };

  const loadTrialBalance = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get(`/accounting/trial-balance?year=${tbPeriod.year}&month=${tbPeriod.month}`);
      setTrialBalance(response.data);
    } catch (error) {
      toast.error('Failed to load trial balance');
    } finally {
      setLoading(false);
    }
  };

  const loadGeneralLedger = async () => {
    if (!glAccount) {
      toast.error('Please select an account');
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams({ year: glPeriod.year });
      if (glPeriod.month) params.append('month', glPeriod.month);
      
      const response = await axiosInstance.get(`/accounting/general-ledger/${glAccount}?${params}`);
      setGeneralLedger(response.data);
    } catch (error) {
      toast.error('Failed to load general ledger');
    } finally {
      setLoading(false);
    }
  };

  const loadBalanceSheet = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get(`/accounting/balance-sheet?year=${bsPeriod.year}&month=${bsPeriod.month}`);
      setBalanceSheet(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load balance sheet');
    } finally {
      setLoading(false);
    }
  };

  const loadAccountingPL = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ year: plPeriod.year });
      if (plPeriod.month) params.append('month', plPeriod.month);
      
      const response = await axiosInstance.get(`/accounting/profit-loss?${params}`);
      setAccountingPL(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load P&L');
    } finally {
      setLoading(false);
    }
  };

  const loadPeriods = async () => {
    try {
      const response = await axiosInstance.get('/accounting/periods?year=2026');
      setPeriods(response.data.periods || []);
    } catch (error) {
      console.error('Failed to load periods:', error);
    }
  };

  const runBackfill = async () => {
    setBackfillRunning(true);
    setBackfillResult(null);
    try {
      const response = await axiosInstance.post('/accounting/backfill');
      setBackfillResult(response.data);
      const created = response.data.results;
      const totalCreated = (created.invoices?.created || 0) + (created.payments?.created || 0) + (created.credit_notes?.created || 0);
      if (totalCreated > 0) {
        toast.success(`Synced ${totalCreated} journal entries from historical transactions`);
      } else {
        toast.info('All transactions are already synced. No new entries created.');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to run backfill');
    } finally {
      setBackfillRunning(false);
    }
  };

  // Actions
  const createAccount = async () => {
    try {
      await axiosInstance.post('/accounting/chart-of-accounts', newAccount);
      toast.success('Account created');
      setShowAddAccount(false);
      setNewAccount({
        account_code: '',
        account_name: '',
        account_type: 'Expense',
        account_category: '',
        description: '',
        normal_balance: 'debit'
      });
      loadAccounts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create account');
    }
  };

  const createJournalEntry = async () => {
    // Validate balanced
    const totalDebit = newJournal.lines.reduce((sum, l) => sum + (parseFloat(l.debit) || 0), 0);
    const totalCredit = newJournal.lines.reduce((sum, l) => sum + (parseFloat(l.credit) || 0), 0);
    
    if (Math.abs(totalDebit - totalCredit) > 0.01) {
      toast.error(`Entry not balanced. Debit: ${totalDebit.toFixed(2)}, Credit: ${totalCredit.toFixed(2)}`);
      return;
    }
    
    try {
      const response = await axiosInstance.post('/accounting/journal-entries', newJournal);
      toast.success('Journal entry created');
      setShowJournalDialog(false);
      loadJournalEntries();
      
      // Ask to post
      if (response.data.journal_entry?.id) {
        const shouldPost = window.confirm('Journal entry created as draft. Post it now?');
        if (shouldPost) {
          await axiosInstance.post(`/accounting/journal-entries/${response.data.journal_entry.id}/post`);
          toast.success('Journal entry posted');
          loadJournalEntries();
        }
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create journal entry');
    }
  };

  const postJournal = async (journalId) => {
    try {
      await axiosInstance.post(`/accounting/journal-entries/${journalId}/post`);
      toast.success('Journal entry posted');
      loadJournalEntries();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to post');
    }
  };

  const addJournalLine = () => {
    setNewJournal(prev => ({
      ...prev,
      lines: [...prev.lines, { account_code: '', debit: 0, credit: 0, memo: '' }]
    }));
  };

  const updateJournalLine = (index, field, value) => {
    setNewJournal(prev => ({
      ...prev,
      lines: prev.lines.map((line, i) => 
        i === index ? { ...line, [field]: value } : line
      )
    }));
  };

  const removeJournalLine = (index) => {
    if (newJournal.lines.length <= 2) {
      toast.error('Minimum 2 lines required');
      return;
    }
    setNewJournal(prev => ({
      ...prev,
      lines: prev.lines.filter((_, i) => i !== index)
    }));
  };

  const formatMoney = (amount) => {
    return new Intl.NumberFormat('en-MY', { style: 'currency', currency: 'MYR' }).format(amount || 0);
  };

  // Export functions
  const exportJournalEntriesToExcel = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (journalFilter.year) params.append('year', journalFilter.year);
      if (journalFilter.month) params.append('month', journalFilter.month);
      
      const response = await axiosInstance.get(`/accounting/journal-entries/export/excel?${params}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `journal_entries_${journalFilter.year}_${journalFilter.month || 'all'}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Journal entries exported');
    } catch (error) {
      toast.error('Failed to export journal entries');
    } finally {
      setLoading(false);
    }
  };

  const exportTrialBalanceToExcel = async () => {
    try {
      setLoading(true);
      const response = await axiosInstance.get(`/accounting/trial-balance/export/excel?year=${tbPeriod.year}&month=${tbPeriod.month}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `trial_balance_${tbPeriod.year}_${tbPeriod.month}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Trial balance exported');
    } catch (error) {
      toast.error('Failed to export trial balance');
    } finally {
      setLoading(false);
    }
  };

  const exportPLToExcel = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ year: plPeriod.year });
      if (plPeriod.month) params.append('month', plPeriod.month);
      
      const response = await axiosInstance.get(`/accounting/profit-loss/export/excel?${params}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `profit_loss_${plPeriod.year}_${plPeriod.month || 'all'}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('P&L exported');
    } catch (error) {
      toast.error('Failed to export P&L');
    } finally {
      setLoading(false);
    }
  };

  const exportBalanceSheetToExcel = async () => {
    try {
      setLoading(true);
      const response = await axiosInstance.get(`/accounting/balance-sheet/export/excel?year=${bsPeriod.year}&month=${bsPeriod.month}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `balance_sheet_${bsPeriod.year}_${bsPeriod.month}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Balance sheet exported');
    } catch (error) {
      toast.error('Failed to export balance sheet');
    } finally {
      setLoading(false);
    }
  };

  const printBalanceSheet = () => {
    if (!balanceSheet) return;
    const settings = companySettings || {};
    const primaryColor = settings.primary_color || '#1a365d';
    const tagline = settings.tagline || 'Towards a Nation of Safe Drivers';
    let logoUrl = '';
    if (settings.logo_url) {
      logoUrl = settings.logo_url.startsWith('http') ? settings.logo_url 
        : `${process.env.REACT_APP_BACKEND_URL}${settings.logo_url.startsWith('/') ? '' : '/'}${settings.logo_url}`;
    }
    const fmt = (v) => `RM ${(v || 0).toLocaleString('en-MY', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    const renderRows = (accounts) => (accounts || []).map(a => 
      `<tr><td style="padding:6px 8px;color:#666;font-family:monospace;font-size:11px;">${a.account_code}</td><td style="padding:6px 8px;">${a.account_name}</td><td style="padding:6px 8px;text-align:right;font-family:monospace;">${fmt(a.balance)}</td></tr>`
    ).join('');
    
    const w = window.open('', '_blank');
    w.document.write(`<!DOCTYPE html><html><head><title>Balance Sheet - ${balanceSheet.period}</title>
    <style>
      @page { size: A4 portrait; margin: 15mm; }
      @media print { body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } }
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; color: #333; }
      .header { text-align: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid ${primaryColor}; }
      .header h1 { color: ${primaryColor}; font-size: 18px; margin: 8px 0 4px; }
      .header h2 { font-size: 14px; color: #555; }
      .header p { font-size: 11px; color: #777; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
      .section h3 { font-size: 13px; font-weight: bold; padding: 6px 0; border-bottom: 1px solid #ccc; margin-bottom: 4px; color: ${primaryColor}; }
      table { width: 100%; border-collapse: collapse; }
      .total-row td { font-weight: bold; border-top: 2px solid #333; padding: 8px; }
      .subtotal-row td { font-weight: 600; border-top: 1px solid #999; padding: 6px 8px; }
      .grand-total td { font-weight: bold; font-size: 14px; border-top: 3px double #333; padding: 10px 8px; }
      .badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 10px; font-weight: 600; }
      .balanced { background: #dcfce7; color: #166534; }
      .unbalanced { background: #fee2e2; color: #991b1b; }
      .footer { text-align: center; margin-top: 20px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 10px; color: #999; }
    </style></head><body>
    <div class="header">
      ${logoUrl ? `<img src="${logoUrl}" style="height:50px;margin-bottom:8px;" />` : ''}
      <h1>${settings.company_name || 'Company'}</h1>
      <h2>Balance Sheet</h2>
      <p>${balanceSheet.period} &nbsp; <span class="badge ${balanceSheet.is_balanced ? 'balanced' : 'unbalanced'}">${balanceSheet.is_balanced ? 'Balanced' : 'UNBALANCED'}</span></p>
    </div>
    <div class="grid">
      <div class="section">
        <h3>ASSETS</h3>
        <table>${renderRows(balanceSheet.assets?.accounts)}
          <tr class="total-row"><td></td><td>Total Assets</td><td style="text-align:right;font-family:monospace;">${fmt(balanceSheet.assets?.total)}</td></tr>
        </table>
      </div>
      <div class="section">
        <h3>LIABILITIES</h3>
        <table>${renderRows(balanceSheet.liabilities?.accounts)}
          <tr class="subtotal-row"><td></td><td>Total Liabilities</td><td style="text-align:right;font-family:monospace;">${fmt(balanceSheet.liabilities?.total)}</td></tr>
        </table>
        <h3 style="margin-top:20px;">EQUITY</h3>
        <table>${renderRows(balanceSheet.equity?.accounts)}
          <tr><td></td><td style="padding:6px 8px;font-style:italic;">Current Year Earnings</td><td style="padding:6px 8px;text-align:right;font-family:monospace;">${fmt(balanceSheet.equity?.current_year_earnings)}</td></tr>
          <tr class="subtotal-row"><td></td><td>Total Equity</td><td style="text-align:right;font-family:monospace;">${fmt(balanceSheet.equity?.total)}</td></tr>
          <tr class="grand-total"><td></td><td>Total Liabilities + Equity</td><td style="text-align:right;font-family:monospace;">${fmt(balanceSheet.total_liabilities_equity)}</td></tr>
        </table>
      </div>
    </div>
    <div class="footer">Generated on ${new Date().toLocaleString('en-MY')} | ${settings.company_name || ''}</div>
    </body></html>`);
    w.document.close();
    setTimeout(() => w.print(), 400);
  };

  const months = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' }
  ];

  // Not initialized view
  if (!initialized) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="w-5 h-5" />
            Accounting Engine
          </CardTitle>
          <CardDescription>
            Double-entry accounting system for accurate financial reporting
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center py-12">
          <BookOpen className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-semibold mb-2">Accounting System Not Initialized</h3>
          <p className="text-gray-500 mb-6">
            Initialize the accounting system to create the Chart of Accounts and enable journal entries.
          </p>
          <Button onClick={initializeAccounting} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
            Initialize Accounting System
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="w-5 h-5" />
                Accounting Engine
              </CardTitle>
              <CardDescription>Double-entry accounting with full audit trail</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={runBackfill} 
                disabled={backfillRunning}
                data-testid="backfill-sync-btn"
              >
                {backfillRunning ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-1" />}
                Sync Historical Transactions
              </Button>
              <Badge variant="outline" className="bg-green-50 text-green-700">
                Active
              </Badge>
            </div>
          </div>
          {backfillResult && (
            <div className="mt-3 p-3 bg-blue-50 rounded-lg text-sm" data-testid="backfill-result">
              <p className="font-semibold text-blue-800 mb-1">{backfillResult.message}</p>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs text-blue-700">
                {Object.entries(backfillResult.results || {}).map(([key, val]) => (
                  val.found > 0 && (
                    <div key={key}>
                      <span className="font-medium capitalize">{key.replace(/_/g, ' ')}:</span>
                      <span className="ml-1">{val.created} new, {val.skipped} synced</span>
                      {(val.errors?.length > 0) && (
                        <span className="text-red-600 block">{val.errors.length} error(s)</span>
                      )}
                    </div>
                  )
                ))}
              </div>
            </div>
          )}
        </CardHeader>
      </Card>

      <Tabs value={activeSubTab} onValueChange={setActiveSubTab}>
        <TabsList className="grid grid-cols-6 w-full">
          <TabsTrigger value="coa" className="text-xs">Chart of Accounts</TabsTrigger>
          <TabsTrigger value="journals" className="text-xs">Journal Entries</TabsTrigger>
          <TabsTrigger value="trial-balance" className="text-xs">Trial Balance</TabsTrigger>
          <TabsTrigger value="general-ledger" className="text-xs">General Ledger</TabsTrigger>
          <TabsTrigger value="balance-sheet" className="text-xs">Balance Sheet</TabsTrigger>
          <TabsTrigger value="pl" className="text-xs">P&L</TabsTrigger>
        </TabsList>

        {/* Chart of Accounts */}
        <TabsContent value="coa" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Chart of Accounts</CardTitle>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={async () => {
                    // Fetch trial balance for actual amounts
                    let trialData = {};
                    try {
                      const tbRes = await axiosInstance.get('/finance/trial-balance?year=' + new Date().getFullYear());
                      (tbRes.data?.accounts || []).forEach(a => { trialData[a.account_code] = a; });
                    } catch (e) { /* proceed without balances */ }
                    const fmt = (v) => v ? `RM ${Math.abs(v).toLocaleString('en-MY', {minimumFractionDigits:2, maximumFractionDigits:2})}` : '-';

                    const settings = companySettings || {};
                    const primaryColor = settings.primary_color || '#1a365d';
                    const secondaryColor = settings.secondary_color || '#4472C4';
                    const tagline = settings.tagline || 'Towards a Nation of Safe Drivers';
                    let logoUrl = '';
                    if (settings.logo_url) {
                      logoUrl = settings.logo_url.startsWith('http') ? settings.logo_url 
                        : `${process.env.REACT_APP_BACKEND_URL}${settings.logo_url.startsWith('/') ? '' : '/'}${settings.logo_url}`;
                    }
                    const headerCustomFields = (settings.invoice_custom_fields || [])
                      .filter(f => f.position === 'Header' || f.position === 'header')
                      .map(f => ` &bull; ${f.label}: ${f.value}`)
                      .join('');
                    const types = ['Asset', 'Liability', 'Equity', 'Income', 'Expense'];
                    const typeColors = { Asset: '#2563eb', Liability: '#dc2626', Equity: '#7c3aed', Income: '#16a34a', Expense: '#ea580c' };
                    const w = window.open('', '_blank');
                    w.document.write(`<!DOCTYPE html><html><head><title>Chart of Accounts — Trial Balance</title>
                    <style>
                      @page { size: A4 landscape; margin: 12mm; }
                      @media print { body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } }
                      * { box-sizing: border-box; margin: 0; padding: 0; }
                      body { font-family: Arial, sans-serif; font-size: 10px; padding: 20px; margin: 0 auto; line-height: 1.4; color: #333; }
                      .header { display: flex; align-items: center; gap: 20px; padding-bottom: 12px; border-bottom: 3px solid ${primaryColor}; margin-bottom: 15px; }
                      .logo-img { width: 80px; height: auto; }
                      .company-details { flex: 1; }
                      .company-name { font-size: 16px; font-weight: bold; color: ${primaryColor}; margin-bottom: 3px; }
                      .company-info { font-size: 10px; color: #444; line-height: 1.4; }
                      .doc-title { font-size: 18px; font-weight: bold; text-align: center; color: ${primaryColor}; margin: 10px 0; padding: 8px; background: #f0f4f8; }
                      .doc-subtitle { text-align: center; color: #666; font-size: 10px; margin-bottom: 12px; }
                      .section-title { font-size: 12px; font-weight: bold; padding: 6px 10px; margin: 12px 0 4px; border-left: 4px solid; }
                      table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
                      th { background: ${secondaryColor}; color: white; font-weight: bold; font-size: 9px; text-transform: uppercase; padding: 5px 8px; text-align: left; }
                      th.num { text-align: right; }
                      td { padding: 4px 8px; font-size: 9px; border-bottom: 1px solid #eee; }
                      td.num { text-align: right; font-family: monospace; }
                      td.has-val { font-weight: bold; }
                      .code { font-family: monospace; font-weight: bold; }
                      .stotal td { font-weight: bold; background: #f8f9fa; border-top: 2px solid #999; padding: 5px 8px; }
                      .gtotal td { font-weight: bold; font-size: 10px; background: #e8edf3; border-top: 3px double #333; padding: 7px 8px; }
                      .footer { margin-top: 20px; font-size: 8px; color: #777; padding-top: 10px; border-top: 1px solid #ddd; text-align: center; }
                      .tagline { font-style: italic; color: ${primaryColor}; font-size: 11px; text-align: center; margin-top: 10px; }
                    </style></head><body>
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
                    <div class="doc-title">CHART OF ACCOUNTS — TRIAL BALANCE</div>
                    <div class="doc-subtitle">For the Year ${new Date().getFullYear()} &bull; Generated: ${new Date().toLocaleString('en-MY')}</div>
                    ${types.map(type => {
                      const accs = (groupedAccounts[type] || []);
                      if (accs.length === 0) return '';
                      let sDr = 0, sCr = 0;
                      const rows = accs.map(a => {
                        const tb = trialData[a.account_code] || {};
                        const dr = tb.debit_balance || 0;
                        const cr = tb.credit_balance || 0;
                        sDr += dr; sCr += cr;
                        return '<tr>' +
                          '<td class="code">' + a.account_code + '</td>' +
                          '<td>' + a.account_name + '</td>' +
                          '<td style="color:#666;">' + (a.account_category || '-') + '</td>' +
                          '<td class="num' + (dr > 0 ? ' has-val' : '') + '">' + (dr > 0 ? fmt(dr) : '-') + '</td>' +
                          '<td class="num' + (cr > 0 ? ' has-val' : '') + '">' + (cr > 0 ? fmt(cr) : '-') + '</td>' +
                          '</tr>';
                      }).join('');
                      return '<div class="section-title" style="border-color:' + typeColors[type] + ';color:' + typeColors[type] + ';">' + type.toUpperCase() + ' (' + accs.length + ' accounts)</div>' +
                        '<table><thead><tr><th style="width:12%;">Code</th><th style="width:36%;">Account Name</th><th style="width:22%;">Category</th><th class="num" style="width:15%;">Debit (RM)</th><th class="num" style="width:15%;">Credit (RM)</th></tr></thead><tbody>' +
                        rows +
                        '<tr class="stotal"><td colspan="3" style="text-align:right;color:' + typeColors[type] + ';">' + type + ' Total</td><td class="num">' + (sDr > 0 ? fmt(sDr) : '-') + '</td><td class="num">' + (sCr > 0 ? fmt(sCr) : '-') + '</td></tr>' +
                        '</tbody></table>';
                    }).join('')}
                    <table><tbody><tr class="gtotal">
                      <td colspan="3" style="text-align:right;width:70%;">GRAND TOTAL</td>
                      <td class="num" style="width:15%;">${fmt(Object.values(trialData).reduce((s,a) => s + (a.debit_balance||0), 0))}</td>
                      <td class="num" style="width:15%;">${fmt(Object.values(trialData).reduce((s,a) => s + (a.credit_balance||0), 0))}</td>
                    </tr></tbody></table>
                    <div class="footer">
                      <p>Chart of Accounts with Trial Balance — ${settings.company_name || 'MDDRC'} Training Management System</p>
                    </div>
                    <div class="tagline">"${tagline}"</div>
                    <script>window.onload = function() { setTimeout(function() { window.print(); }, 500); };</script>
                    </body></html>`);
                    w.document.close();
                  }} data-testid="print-coa-btn">
                    <Printer className="w-4 h-4 mr-1" /> Print COA
                  </Button>
                  <Button variant="outline" size="sm" onClick={loadAccounts}>
                    <RefreshCw className="w-4 h-4 mr-1" /> Refresh
                  </Button>
                  <Button size="sm" onClick={() => setShowAddAccount(true)}>
                    <Plus className="w-4 h-4 mr-1" /> Add Account
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {['Asset', 'Liability', 'Equity', 'Income', 'Expense'].map(type => (
                  <div key={type}>
                    <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
                      <Badge variant={
                        type === 'Asset' ? 'default' :
                        type === 'Liability' ? 'secondary' :
                        type === 'Equity' ? 'outline' :
                        type === 'Income' ? 'default' : 'destructive'
                      } className={
                        type === 'Asset' ? 'bg-blue-500' :
                        type === 'Liability' ? 'bg-red-500 text-white' :
                        type === 'Equity' ? 'bg-purple-500 text-white' :
                        type === 'Income' ? 'bg-green-500' : 'bg-orange-500'
                      }>
                        {type}
                      </Badge>
                      <span className="text-gray-500">({(groupedAccounts[type] || []).length} accounts)</span>
                    </h3>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-24">Code</TableHead>
                          <TableHead>Account Name</TableHead>
                          <TableHead>Category</TableHead>
                          <TableHead className="w-24">Normal</TableHead>
                          <TableHead className="w-20">Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(groupedAccounts[type] || []).map(account => (
                          <TableRow key={account.account_code}>
                            <TableCell className="font-mono font-semibold">{account.account_code}</TableCell>
                            <TableCell>{account.account_name}</TableCell>
                            <TableCell className="text-gray-500">{account.account_category}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className="text-xs">
                                {account.normal_balance}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {account.is_active ? (
                                <Badge className="bg-green-100 text-green-700">Active</Badge>
                              ) : (
                                <Badge variant="secondary">Inactive</Badge>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Journal Entries */}
        <TabsContent value="journals" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Journal Entries</CardTitle>
                <div className="flex gap-2">
                  <Select value={journalFilter.month?.toString() || 'all'} onValueChange={(v) => setJournalFilter(prev => ({ ...prev, month: v === 'all' ? null : parseInt(v) }))}>
                    <SelectTrigger className="w-32">
                      <SelectValue placeholder="Month" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Months</SelectItem>
                      {months.map(m => (
                        <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button variant="outline" size="sm" onClick={loadJournalEntries}>
                    <RefreshCw className="w-4 h-4 mr-1" /> Load
                  </Button>
                  <Button variant="outline" size="sm" onClick={exportJournalEntriesToExcel}>
                    <Download className="w-4 h-4 mr-1" /> Excel
                  </Button>
                  <Button variant="outline" size="sm" className="text-orange-600 border-orange-300" onClick={async () => {
                    try {
                      const res = await axiosInstance.get('/accounting/migrate-journal-references');
                      const d = res.data;
                      if (d.updated > 0) {
                        toast.success(`Updated ${d.updated} of ${d.total_found} references to invoice numbers`);
                        loadJournalEntries();
                      } else if (d.total_found === 0) {
                        toast.info('No entries found needing reference migration. All references may already be up to date.');
                      } else {
                        toast.info(`Found ${d.total_found} entries but could not update. ${d.skipped_no_session || 0} missing session link, ${d.skipped_no_invoice || 0} missing invoice.`);
                      }
                    } catch (e) {
                      toast.error(e.response?.data?.detail || 'Migration failed');
                    }
                  }}>
                    Fix References
                  </Button>
                  <Button variant="outline" size="sm" className="text-blue-600 border-blue-300" onClick={async () => {
                    try {
                      const res = await axiosInstance.get('/accounting/diagnose-journal-references');
                      const d = res.data;
                      const msg = `Total entries: ${d.total_journal_entries}\nWith invoice ref: ${d.with_invoice_ref}\nTF/CF/MC needing fix: ${d.tf_cf_mc_needing_fix}\nMissing source_id: ${d.tf_cf_mc_missing_source_id}`;
                      alert(msg + '\n\nSample needing fix:\n' + (d.sample_needing_fix || []).map(s => `${s.ref} (${s.module})`).join('\n'));
                    } catch (e) {
                      toast.error(e.response?.data?.detail || 'Diagnose failed');
                    }
                  }}>
                    Diagnose Refs
                  </Button>
                  <Button size="sm" onClick={() => {
                    setNewJournal({
                      date: new Date().toISOString().split('T')[0],
                      description: '',
                      lines: [
                        { account_code: '', debit: 0, credit: 0, memo: '' },
                        { account_code: '', debit: 0, credit: 0, memo: '' }
                      ]
                    });
                    setShowJournalDialog(true);
                  }}>
                    <Plus className="w-4 h-4 mr-1" /> New Entry
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto text-gray-400" />
                </div>
              ) : journalEntries.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No journal entries found. Click "Load" to fetch entries.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Journal #</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Source</TableHead>
                      <TableHead className="text-right">Debit</TableHead>
                      <TableHead className="text-right">Credit</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {journalEntries.map(entry => (
                      <TableRow key={entry.id}>
                        <TableCell className="font-mono">{entry.journal_no}</TableCell>
                        <TableCell>{entry.date}</TableCell>
                        <TableCell className="max-w-xs truncate">{entry.description}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {entry.source_module}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono">{formatMoney(entry.total_debit)}</TableCell>
                        <TableCell className="text-right font-mono">{formatMoney(entry.total_credit)}</TableCell>
                        <TableCell>
                          <Badge className={
                            entry.status === 'posted' ? 'bg-green-100 text-green-700' :
                            entry.status === 'draft' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          }>
                            {entry.status}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm" onClick={() => setSelectedJournal(entry)}>
                              <Eye className="w-4 h-4" />
                            </Button>
                            {entry.status === 'draft' && (
                              <Button variant="ghost" size="sm" onClick={() => postJournal(entry.id)}>
                                <Check className="w-4 h-4 text-green-600" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trial Balance */}
        <TabsContent value="trial-balance" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Trial Balance</CardTitle>
                <div className="flex gap-2 items-center">
                  <Select value={tbPeriod.month.toString()} onValueChange={(v) => setTbPeriod(prev => ({ ...prev, month: parseInt(v) }))}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {months.map(m => (
                        <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input 
                    type="number" 
                    value={tbPeriod.year} 
                    onChange={(e) => setTbPeriod(prev => ({ ...prev, year: parseInt(e.target.value) }))}
                    className="w-24"
                  />
                  <Button onClick={loadTrialBalance} disabled={loading}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4 mr-1" />}
                    Generate
                  </Button>
                  {trialBalance && (
                    <Button variant="outline" onClick={exportTrialBalanceToExcel} disabled={loading}>
                      <Download className="w-4 h-4 mr-1" /> Excel
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {trialBalance ? (
                <div className="space-y-4">
                  <div className="text-center mb-4">
                    <h3 className="font-semibold">Trial Balance</h3>
                    <p className="text-sm text-gray-500">As of {trialBalance.period}</p>
                  </div>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Code</TableHead>
                        <TableHead>Account</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead className="text-right">Debit</TableHead>
                        <TableHead className="text-right">Credit</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {trialBalance.trial_balance?.map(row => (
                        <TableRow key={row.account_code}>
                          <TableCell className="font-mono">{row.account_code}</TableCell>
                          <TableCell>{row.account_name}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">{row.account_type}</Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {row.debit_balance > 0 ? formatMoney(row.debit_balance) : '-'}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {row.credit_balance > 0 ? formatMoney(row.credit_balance) : '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                      <TableRow className="font-bold bg-gray-50">
                        <TableCell colSpan={3}>TOTAL</TableCell>
                        <TableCell className="text-right font-mono">{formatMoney(trialBalance.totals?.total_debit)}</TableCell>
                        <TableCell className="text-right font-mono">{formatMoney(trialBalance.totals?.total_credit)}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                  <div className="text-center">
                    <Badge className={trialBalance.totals?.is_balanced ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                      {trialBalance.totals?.is_balanced ? '✓ Balanced' : '✗ Not Balanced'}
                    </Badge>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  Select a period and click "Generate" to view the trial balance.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* General Ledger */}
        <TabsContent value="general-ledger" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">General Ledger</CardTitle>
                <div className="flex gap-2 items-center">
                  <Select value={glAccount} onValueChange={setGlAccount}>
                    <SelectTrigger className="w-64">
                      <SelectValue placeholder="Select Account" />
                    </SelectTrigger>
                    <SelectContent>
                      {accounts.map(acc => (
                        <SelectItem key={acc.account_code} value={acc.account_code}>
                          {acc.account_code} - {acc.account_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select value={glPeriod.month?.toString() || 'all'} onValueChange={(v) => setGlPeriod(prev => ({ ...prev, month: v === 'all' ? null : parseInt(v) }))}>
                    <SelectTrigger className="w-32">
                      <SelectValue placeholder="Month" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Full Year</SelectItem>
                      {months.map(m => (
                        <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button onClick={loadGeneralLedger} disabled={loading || !glAccount}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4 mr-1" />}
                    View
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {generalLedger ? (
                <div className="space-y-4">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h3 className="font-semibold">{generalLedger.account?.account_code} - {generalLedger.account?.account_name}</h3>
                    <p className="text-sm text-gray-500">
                      {generalLedger.account?.account_type} | {generalLedger.account?.account_category}
                    </p>
                  </div>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Journal #</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead className="text-right">Debit</TableHead>
                        <TableHead className="text-right">Credit</TableHead>
                        <TableHead className="text-right">Balance</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <TableRow className="bg-blue-50">
                        <TableCell colSpan={5} className="font-semibold">Opening Balance</TableCell>
                        <TableCell className="text-right font-mono font-semibold">
                          {formatMoney(generalLedger.opening_balance)}
                        </TableCell>
                      </TableRow>
                      {generalLedger.entries?.map((entry, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{entry.date}</TableCell>
                          <TableCell className="font-mono">{entry.journal_no}</TableCell>
                          <TableCell className="max-w-xs truncate">{entry.description}</TableCell>
                          <TableCell className="text-right font-mono">
                            {entry.debit > 0 ? formatMoney(entry.debit) : '-'}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {entry.credit > 0 ? formatMoney(entry.credit) : '-'}
                          </TableCell>
                          <TableCell className="text-right font-mono">{formatMoney(entry.balance)}</TableCell>
                        </TableRow>
                      ))}
                      <TableRow className="font-bold bg-gray-100">
                        <TableCell colSpan={3}>TOTALS / CLOSING</TableCell>
                        <TableCell className="text-right font-mono">{formatMoney(generalLedger.totals?.period_debit)}</TableCell>
                        <TableCell className="text-right font-mono">{formatMoney(generalLedger.totals?.period_credit)}</TableCell>
                        <TableCell className="text-right font-mono">{formatMoney(generalLedger.totals?.closing_balance)}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  Select an account and click "View" to see the general ledger.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Balance Sheet */}
        <TabsContent value="balance-sheet" className="mt-4" data-testid="balance-sheet-tab-content">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-lg" data-testid="balance-sheet-title">Balance Sheet</CardTitle>
                  {balanceSheet && (
                    <Badge 
                      data-testid="balance-sheet-status-badge"
                      variant={balanceSheet.is_balanced ? 'default' : 'destructive'}
                      className={balanceSheet.is_balanced ? 'bg-green-100 text-green-800 border-green-300' : ''}
                    >
                      {balanceSheet.is_balanced ? 'Balanced' : 'Unbalanced'}
                    </Badge>
                  )}
                </div>
                <div className="flex gap-2 items-center">
                  <Select data-testid="bs-month-select" value={bsPeriod.month.toString()} onValueChange={(v) => setBsPeriod(prev => ({ ...prev, month: parseInt(v) }))}>
                    <SelectTrigger className="w-32" data-testid="bs-month-trigger">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {months.map(m => (
                        <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input 
                    type="number" 
                    value={bsPeriod.year} 
                    onChange={(e) => setBsPeriod(prev => ({ ...prev, year: parseInt(e.target.value) }))}
                    className="w-24"
                    data-testid="bs-year-input"
                  />
                  <Button onClick={loadBalanceSheet} disabled={loading} data-testid="bs-generate-btn">
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4 mr-1" />}
                    Generate
                  </Button>
                  {balanceSheet && (
                    <>
                      <Button variant="outline" onClick={exportBalanceSheetToExcel} disabled={loading} data-testid="bs-export-excel-btn">
                        <Download className="w-4 h-4 mr-1" /> Excel
                      </Button>
                      <Button variant="outline" onClick={() => printBalanceSheet()} disabled={loading} data-testid="bs-print-btn">
                        <Printer className="w-4 h-4 mr-1" /> Print
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent data-testid="balance-sheet-content">
              {balanceSheet ? (
                <div>
                  <div className="text-center mb-4">
                    <p className="text-sm text-muted-foreground" data-testid="bs-period-label">{balanceSheet.period}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-6" data-testid="balance-sheet-grid">
                    {/* Assets */}
                    <div data-testid="bs-assets-section">
                      <h3 className="font-bold text-lg mb-3 pb-2 border-b">ASSETS</h3>
                      {balanceSheet.assets?.accounts?.map(acc => (
                        <div key={acc.account_code} className="flex justify-between py-1 hover:bg-gray-50 px-1 rounded" data-testid={`bs-asset-${acc.account_code}`}>
                          <span className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground font-mono">{acc.account_code}</span>
                            <span>{acc.account_name}</span>
                          </span>
                          <span className="font-mono">{formatMoney(acc.balance)}</span>
                        </div>
                      ))}
                      {(!balanceSheet.assets?.accounts || balanceSheet.assets.accounts.length === 0) && (
                        <p className="text-sm text-muted-foreground py-2 italic">No asset accounts with balances</p>
                      )}
                      <div className="flex justify-between py-2 mt-2 border-t-2 border-gray-800 font-bold" data-testid="bs-total-assets">
                        <span>Total Assets</span>
                        <span className="font-mono">{formatMoney(balanceSheet.assets?.total)}</span>
                      </div>
                    </div>
                    
                    {/* Liabilities & Equity */}
                    <div data-testid="bs-liabilities-equity-section">
                      <h3 className="font-bold text-lg mb-3 pb-2 border-b">LIABILITIES</h3>
                      {balanceSheet.liabilities?.accounts?.map(acc => (
                        <div key={acc.account_code} className="flex justify-between py-1 hover:bg-gray-50 px-1 rounded" data-testid={`bs-liability-${acc.account_code}`}>
                          <span className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground font-mono">{acc.account_code}</span>
                            <span>{acc.account_name}</span>
                          </span>
                          <span className="font-mono">{formatMoney(acc.balance)}</span>
                        </div>
                      ))}
                      {(!balanceSheet.liabilities?.accounts || balanceSheet.liabilities.accounts.length === 0) && (
                        <p className="text-sm text-muted-foreground py-2 italic">No liability accounts with balances</p>
                      )}
                      <div className="flex justify-between py-2 mt-2 border-t font-semibold" data-testid="bs-total-liabilities">
                        <span>Total Liabilities</span>
                        <span className="font-mono">{formatMoney(balanceSheet.liabilities?.total)}</span>
                      </div>
                      
                      <h3 className="font-bold text-lg mb-3 pb-2 border-b mt-6">EQUITY</h3>
                      {balanceSheet.equity?.accounts?.map(acc => (
                        <div key={acc.account_code} className="flex justify-between py-1 hover:bg-gray-50 px-1 rounded" data-testid={`bs-equity-${acc.account_code}`}>
                          <span className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground font-mono">{acc.account_code}</span>
                            <span>{acc.account_name}</span>
                          </span>
                          <span className="font-mono">{formatMoney(acc.balance)}</span>
                        </div>
                      ))}
                      <div className="flex justify-between py-1 hover:bg-gray-50 px-1 rounded" data-testid="bs-current-year-earnings">
                        <span className="italic">Current Year Earnings</span>
                        <span className="font-mono">{formatMoney(balanceSheet.equity?.current_year_earnings)}</span>
                      </div>
                      <div className="flex justify-between py-2 mt-2 border-t font-semibold" data-testid="bs-total-equity">
                        <span>Total Equity</span>
                        <span className="font-mono">{formatMoney(balanceSheet.equity?.total)}</span>
                      </div>
                      
                      <div className="flex justify-between py-3 mt-4 border-t-2 border-gray-800 font-bold text-lg" data-testid="bs-total-liabilities-equity">
                        <span>Total Liabilities + Equity</span>
                        <span className="font-mono">{formatMoney(balanceSheet.total_liabilities_equity)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500" data-testid="bs-empty-state">
                  Select a period and click "Generate" to view the balance sheet.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* P&L */}
        <TabsContent value="pl" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Profit & Loss Statement</CardTitle>
                <div className="flex gap-2 items-center">
                  <Select value={plPeriod.month?.toString() || 'all'} onValueChange={(v) => setPlPeriod(prev => ({ ...prev, month: v === 'all' ? null : parseInt(v) }))}>
                    <SelectTrigger className="w-32">
                      <SelectValue placeholder="Period" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Full Year</SelectItem>
                      {months.map(m => (
                        <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input 
                    type="number" 
                    value={plPeriod.year} 
                    onChange={(e) => setPlPeriod(prev => ({ ...prev, year: parseInt(e.target.value) }))}
                    className="w-24"
                  />
                  <Button onClick={loadAccountingPL} disabled={loading}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4 mr-1" />}
                    Generate
                  </Button>
                  {accountingPL && (
                    <Button variant="outline" onClick={exportPLToExcel} disabled={loading}>
                      <Download className="w-4 h-4 mr-1" /> Excel
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {accountingPL ? (
                <div className="space-y-6">
                  <div className="text-center">
                    <h3 className="font-semibold">Profit & Loss Statement</h3>
                    <p className="text-sm text-gray-500">{accountingPL.period}</p>
                  </div>
                  
                  {/* Revenue */}
                  <div>
                    <h4 className="font-bold text-green-700 mb-2">REVENUE</h4>
                    {accountingPL.revenue?.accounts?.map(acc => (
                      <div key={acc.account_code} className="flex justify-between py-1 pl-4">
                        <span>{acc.account_name}</span>
                        <span className="font-mono">{formatMoney(acc.amount)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between py-2 mt-1 border-t font-semibold text-green-700">
                      <span>Total Revenue</span>
                      <span className="font-mono">{formatMoney(accountingPL.revenue?.total)}</span>
                    </div>
                  </div>
                  
                  {/* Expenses */}
                  <div>
                    <h4 className="font-bold text-red-700 mb-2">EXPENSES</h4>
                    {accountingPL.expenses?.accounts?.map(acc => (
                      <div key={acc.account_code} className="flex justify-between py-1 pl-4">
                        <span>{acc.account_name}</span>
                        <span className="font-mono">{formatMoney(acc.amount)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between py-2 mt-1 border-t font-semibold text-red-700">
                      <span>Total Expenses</span>
                      <span className="font-mono">{formatMoney(accountingPL.expenses?.total)}</span>
                    </div>
                  </div>
                  
                  {/* Net Profit */}
                  <div className={`flex justify-between py-3 border-t-2 font-bold text-lg ${accountingPL.net_profit >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                    <span>NET {accountingPL.net_profit >= 0 ? 'PROFIT' : 'LOSS'}</span>
                    <span className="font-mono">{formatMoney(Math.abs(accountingPL.net_profit))}</span>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  Select a period and click "Generate" to view the P&L statement.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Add Account Dialog */}
      <Dialog open={showAddAccount} onOpenChange={setShowAddAccount}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Account</DialogTitle>
            <DialogDescription>Create a new account in the Chart of Accounts</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Account Code</Label>
                <Input 
                  value={newAccount.account_code}
                  onChange={(e) => setNewAccount(prev => ({ ...prev, account_code: e.target.value }))}
                  placeholder="e.g., 5700"
                />
              </div>
              <div>
                <Label>Account Type</Label>
                <Select value={newAccount.account_type} onValueChange={(v) => setNewAccount(prev => ({ ...prev, account_type: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Asset">Asset</SelectItem>
                    <SelectItem value="Liability">Liability</SelectItem>
                    <SelectItem value="Equity">Equity</SelectItem>
                    <SelectItem value="Income">Income</SelectItem>
                    <SelectItem value="Expense">Expense</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Account Name</Label>
              <Input 
                value={newAccount.account_name}
                onChange={(e) => setNewAccount(prev => ({ ...prev, account_name: e.target.value }))}
                placeholder="e.g., Insurance Expense"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Category</Label>
                <Input 
                  value={newAccount.account_category}
                  onChange={(e) => setNewAccount(prev => ({ ...prev, account_category: e.target.value }))}
                  placeholder="e.g., Operating Expense"
                />
              </div>
              <div>
                <Label>Normal Balance</Label>
                <Select value={newAccount.normal_balance} onValueChange={(v) => setNewAccount(prev => ({ ...prev, normal_balance: v }))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="debit">Debit</SelectItem>
                    <SelectItem value="credit">Credit</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label>Description (Optional)</Label>
              <Textarea 
                value={newAccount.description}
                onChange={(e) => setNewAccount(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Account description..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddAccount(false)}>Cancel</Button>
            <Button onClick={createAccount}>Create Account</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* New Journal Entry Dialog */}
      <Dialog open={showJournalDialog} onOpenChange={setShowJournalDialog}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Create Journal Entry</DialogTitle>
            <DialogDescription>Enter debits and credits. Entry must be balanced.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Date</Label>
                <Input 
                  type="date"
                  value={newJournal.date}
                  onChange={(e) => setNewJournal(prev => ({ ...prev, date: e.target.value }))}
                />
              </div>
              <div>
                <Label>Description</Label>
                <Input 
                  value={newJournal.description}
                  onChange={(e) => setNewJournal(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Journal entry description"
                />
              </div>
            </div>
            
            <div>
              <div className="flex justify-between items-center mb-2">
                <Label>Journal Lines</Label>
                <Button variant="outline" size="sm" onClick={addJournalLine}>
                  <Plus className="w-4 h-4 mr-1" /> Add Line
                </Button>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Account</TableHead>
                    <TableHead className="w-32">Debit</TableHead>
                    <TableHead className="w-32">Credit</TableHead>
                    <TableHead>Memo</TableHead>
                    <TableHead className="w-10"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {newJournal.lines.map((line, idx) => (
                    <TableRow key={idx}>
                      <TableCell>
                        <Select value={line.account_code} onValueChange={(v) => updateJournalLine(idx, 'account_code', v)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select..." />
                          </SelectTrigger>
                          <SelectContent>
                            {accounts.map(acc => (
                              <SelectItem key={acc.account_code} value={acc.account_code}>
                                {acc.account_code} - {acc.account_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <Input 
                          type="number"
                          step="0.01"
                          value={line.debit || ''}
                          onChange={(e) => updateJournalLine(idx, 'debit', parseFloat(e.target.value) || 0)}
                        />
                      </TableCell>
                      <TableCell>
                        <Input 
                          type="number"
                          step="0.01"
                          value={line.credit || ''}
                          onChange={(e) => updateJournalLine(idx, 'credit', parseFloat(e.target.value) || 0)}
                        />
                      </TableCell>
                      <TableCell>
                        <Input 
                          value={line.memo}
                          onChange={(e) => updateJournalLine(idx, 'memo', e.target.value)}
                          placeholder="Memo"
                        />
                      </TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" onClick={() => removeJournalLine(idx)}>
                          <X className="w-4 h-4 text-red-500" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="bg-gray-50 font-semibold">
                    <TableCell>TOTAL</TableCell>
                    <TableCell className="font-mono">
                      {formatMoney(newJournal.lines.reduce((sum, l) => sum + (parseFloat(l.debit) || 0), 0))}
                    </TableCell>
                    <TableCell className="font-mono">
                      {formatMoney(newJournal.lines.reduce((sum, l) => sum + (parseFloat(l.credit) || 0), 0))}
                    </TableCell>
                    <TableCell colSpan={2}>
                      {Math.abs(
                        newJournal.lines.reduce((sum, l) => sum + (parseFloat(l.debit) || 0), 0) -
                        newJournal.lines.reduce((sum, l) => sum + (parseFloat(l.credit) || 0), 0)
                      ) < 0.01 ? (
                        <Badge className="bg-green-100 text-green-700">Balanced</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700">Not Balanced</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowJournalDialog(false)}>Cancel</Button>
            <Button onClick={createJournalEntry}>Create Entry</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Journal Entry Dialog */}
      <Dialog open={!!selectedJournal} onOpenChange={() => setSelectedJournal(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Journal Entry: {selectedJournal?.journal_no}</DialogTitle>
          </DialogHeader>
          {selectedJournal && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="text-gray-500">Date:</span> {selectedJournal.date}</div>
                <div><span className="text-gray-500">Status:</span> <Badge>{selectedJournal.status}</Badge></div>
                <div><span className="text-gray-500">Source:</span> {selectedJournal.source_module}</div>
                <div><span className="text-gray-500">Reference:</span> {selectedJournal.source_reference || '-'}</div>
              </div>
              <div>
                <span className="text-gray-500">Description:</span>
                <p className="mt-1">{selectedJournal.description}</p>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Account</TableHead>
                    <TableHead>Memo</TableHead>
                    <TableHead className="text-right">Debit</TableHead>
                    <TableHead className="text-right">Credit</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {selectedJournal.lines?.map((line, idx) => (
                    <TableRow key={idx}>
                      <TableCell>
                        <span className="font-mono">{line.account_code}</span> - {line.account_name}
                      </TableCell>
                      <TableCell className="text-gray-500">{line.memo}</TableCell>
                      <TableCell className="text-right font-mono">
                        {line.debit > 0 ? formatMoney(line.debit) : '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {line.credit > 0 ? formatMoney(line.credit) : '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="font-bold bg-gray-50">
                    <TableCell colSpan={2}>TOTAL</TableCell>
                    <TableCell className="text-right font-mono">{formatMoney(selectedJournal.total_debit)}</TableCell>
                    <TableCell className="text-right font-mono">{formatMoney(selectedJournal.total_credit)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AccountingTab;
