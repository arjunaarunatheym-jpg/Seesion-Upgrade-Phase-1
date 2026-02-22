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
  Download, ChevronDown, ChevronRight, Building2
} from 'lucide-react';

const AccountingTab = () => {
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
            <Badge variant="outline" className="bg-green-50 text-green-700">
              Active
            </Badge>
          </div>
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
        <TabsContent value="balance-sheet" className="mt-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Balance Sheet</CardTitle>
                <div className="flex gap-2 items-center">
                  <Select value={bsPeriod.month.toString()} onValueChange={(v) => setBsPeriod(prev => ({ ...prev, month: parseInt(v) }))}>
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
                    value={bsPeriod.year} 
                    onChange={(e) => setBsPeriod(prev => ({ ...prev, year: parseInt(e.target.value) }))}
                    className="w-24"
                  />
                  <Button onClick={loadBalanceSheet} disabled={loading}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4 mr-1" />}
                    Generate
                  </Button>
                  {balanceSheet && (
                    <Button variant="outline" onClick={exportBalanceSheetToExcel} disabled={loading}>
                      <Download className="w-4 h-4 mr-1" /> Excel
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {balanceSheet ? (
                <div className="grid grid-cols-2 gap-6">
                  {/* Assets */}
                  <div>
                    <h3 className="font-bold text-lg mb-3 pb-2 border-b">ASSETS</h3>
                    {balanceSheet.assets?.accounts?.map(acc => (
                      <div key={acc.account_code} className="flex justify-between py-1">
                        <span>{acc.account_name}</span>
                        <span className="font-mono">{formatMoney(acc.balance)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between py-2 mt-2 border-t font-bold">
                      <span>Total Assets</span>
                      <span className="font-mono">{formatMoney(balanceSheet.assets?.total)}</span>
                    </div>
                  </div>
                  
                  {/* Liabilities & Equity */}
                  <div>
                    <h3 className="font-bold text-lg mb-3 pb-2 border-b">LIABILITIES</h3>
                    {balanceSheet.liabilities?.accounts?.map(acc => (
                      <div key={acc.account_code} className="flex justify-between py-1">
                        <span>{acc.account_name}</span>
                        <span className="font-mono">{formatMoney(acc.balance)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between py-2 mt-2 border-t font-semibold">
                      <span>Total Liabilities</span>
                      <span className="font-mono">{formatMoney(balanceSheet.liabilities?.total)}</span>
                    </div>
                    
                    <h3 className="font-bold text-lg mb-3 pb-2 border-b mt-6">EQUITY</h3>
                    {balanceSheet.equity?.accounts?.map(acc => (
                      <div key={acc.account_code} className="flex justify-between py-1">
                        <span>{acc.account_name}</span>
                        <span className="font-mono">{formatMoney(acc.balance)}</span>
                      </div>
                    ))}
                    <div className="flex justify-between py-1">
                      <span className="italic">Current Year Earnings</span>
                      <span className="font-mono">{formatMoney(balanceSheet.equity?.current_year_earnings)}</span>
                    </div>
                    <div className="flex justify-between py-2 mt-2 border-t font-semibold">
                      <span>Total Equity</span>
                      <span className="font-mono">{formatMoney(balanceSheet.equity?.total)}</span>
                    </div>
                    
                    <div className="flex justify-between py-3 mt-4 border-t-2 font-bold text-lg">
                      <span>Total Liabilities + Equity</span>
                      <span className="font-mono">{formatMoney(balanceSheet.total_liabilities_equity)}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
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
