import React, { useState, useEffect, useCallback } from 'react';
import { axiosInstance } from '../App';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { 
  DollarSign, Users, Truck, Calculator, Plus, Trash2, Save, 
  FileText, TrendingUp, User, Building2, Calendar, RefreshCw, FileX, Download
} from 'lucide-react';
import ClaimFormPrint from './ClaimFormPrint';

const SessionCosting = ({ session, onClose, onUpdate }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [costing, setCosting] = useState(null);
  const [expenseCategories, setExpenseCategories] = useState([]);
  const [invoiceId, setInvoiceId] = useState(null);
  const [creditNotes, setCreditNotes] = useState([]);
  const [showClaimForm, setShowClaimForm] = useState(false);
  const [companies, setCompanies] = useState([]);
  
  // Form states - Primary invoice
  const [invoiceData, setInvoiceData] = useState({
    pricing_type: 'lumpsum',
    lumpsum_amount: '',
    per_pax_rate: '',
    tax_rate: '', // Default blank - user can add if needed
  });
  
  // Additional invoices for multi-company sessions
  const [additionalInvoices, setAdditionalInvoices] = useState([]);
  
  const [trainerFees, setTrainerFees] = useState([]);
  const [coordinatorFee, setCoordinatorFee] = useState({ num_days: 1, daily_rate: 50 });
  const [expenses, setExpenses] = useState([]);
  const [marketing, setMarketing] = useState({
    marketing_user_id: '',
    commission_type: 'percentage',
    commission_rate: '',
    fixed_amount: '',
    create_new: false,
    full_name: '',
    id_number: '',
  });
  const [marketingUsers, setMarketingUsers] = useState([]);

  // Calculate total headcount (participants + trainers + coordinator) - use API data if available
  const getTotalHeadcount = useCallback(() => {
    if (costing?.total_headcount) {
      return costing.total_headcount;
    }
    const participantCount = costing?.pax || session?.participant_ids?.length || 0;
    const trainerCount = costing?.trainer_count || session?.trainer_assignments?.length || 0;
    const coordinatorCount = costing?.coordinator_count || (session?.coordinator_id ? 1 : 0);
    return participantCount + trainerCount + coordinatorCount;
  }, [costing, session]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [costingRes, categoriesRes, marketingUsersRes, invoicesRes, creditNotesRes, companiesRes] = await Promise.all([
        axiosInstance.get(`/finance/session/${session.id}/costing`),
        axiosInstance.get('/finance/expense-categories'),
        axiosInstance.get('/finance/marketing-users').catch(() => ({ data: [] })),
        axiosInstance.get('/finance/invoices').catch(() => ({ data: [] })),
        axiosInstance.get('/finance/credit-notes').catch(() => ({ data: [] })),
        axiosInstance.get('/companies').catch(() => ({ data: [] }))
      ]);
      
      const costingData = costingRes.data;
      setCosting(costingData);
      setExpenseCategories(categoriesRes.data);
      setMarketingUsers(marketingUsersRes.data);
      setCompanies(companiesRes.data);
      
      // Filter credit notes for this session
      const sessionCNs = creditNotesRes.data.filter(cn => cn.session_id === session.id);
      setCreditNotes(sessionCNs);
      
      // Find ALL invoices for this session
      const sessionInvoices = invoicesRes.data.filter(inv => inv.session_id === session.id);
      const primaryInvoice = sessionInvoices.find(inv => inv.company_id === session.company_id);
      const otherInvoices = sessionInvoices.filter(inv => inv.company_id !== session.company_id);
      
      if (primaryInvoice) {
        setInvoiceId(primaryInvoice.id);
        if (primaryInvoice.total_amount > 0) {
          setInvoiceData({
            pricing_type: primaryInvoice.pricing_type || 'lumpsum',
            lumpsum_amount: primaryInvoice.total_amount?.toString() || '',
            per_pax_rate: primaryInvoice.pricing_type === 'per_pax' ? 
              (primaryInvoice.total_amount / (costingData.pax || 1))?.toString() : '',
            tax_rate: primaryInvoice.tax_rate?.toString() || '6',
          });
        } else if (costingData.invoice_total > 0) {
          setInvoiceData({
            pricing_type: 'lumpsum',
            lumpsum_amount: costingData.invoice_total?.toString() || '',
            per_pax_rate: '',
            tax_rate: costingData.less_tax > 0 ? 
              ((costingData.less_tax / costingData.invoice_total) * 100).toFixed(1) : '6',
          });
        }
      }
      
      // Load additional invoices
      if (otherInvoices.length > 0) {
        setAdditionalInvoices(otherInvoices.map(inv => ({
          id: inv.id,
          invoice_number: inv.invoice_number,
          company_id: inv.company_id,
          company_name: companiesRes.data.find(c => c.id === inv.company_id)?.name || 'Unknown',
          amount: inv.total_amount?.toString() || '',
          tax_rate: inv.tax_rate?.toString() || '6',
          status: inv.status
        })));
      }
      
      // Initialize trainer fees
      if (costingData.trainer_fees?.length > 0) {
        setTrainerFees(costingData.trainer_fees.map(f => ({
          trainer_id: f.trainer_id,
          trainer_name: f.trainer_name || 'Unknown Trainer',
          role: f.role || 'trainer',
          fee_amount: f.fee_amount?.toString() || '',
          remark: f.remark || ''
        })));
      } else if (session.trainer_assignments?.length > 0) {
        setTrainerFees(session.trainer_assignments.map(ta => ({
          trainer_id: ta.trainer_id,
          trainer_name: ta.trainer_name || 'Unknown Trainer',
          role: ta.role,
          fee_amount: '',
          remark: ''
        })));
      }
      
      // Initialize coordinator fee
      if (costingData.coordinator_fee) {
        setCoordinatorFee({
          num_days: costingData.coordinator_fee.num_days || 1,
          daily_rate: costingData.coordinator_fee.daily_rate || 50
        });
      } else if (session.coordinator_id) {
        const start = new Date(session.start_date);
        const end = new Date(session.end_date);
        const days = Math.max(1, Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1);
        setCoordinatorFee({ num_days: days, daily_rate: 50 });
      }
      
      // Initialize expenses
      if (costingData.expenses?.length > 0) {
        setExpenses(costingData.expenses.map(e => ({
          ...e,
          estimated_amount: e.estimated_amount?.toString() || '',
          actual_amount: e.actual_amount?.toString() || ''
        })));
      }
      
      // Initialize marketing
      if (costingData.marketing) {
        setMarketing({
          marketing_user_id: costingData.marketing.marketing_user_id || '',
          commission_type: costingData.marketing.commission_type || 'percentage',
          commission_rate: costingData.marketing.commission_rate?.toString() || '',
          fixed_amount: costingData.marketing.fixed_amount?.toString() || '',
          create_new: false,
          full_name: '',
          id_number: ''
        });
      }
      
    } catch (error) {
      toast.error('Failed to load costing data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [session.id, session.coordinator_id, session.start_date, session.end_date, session.trainer_assignments, session.participant_ids]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Get invoice amount for calculations
  const getInvoiceAmount = () => {
    if (invoiceData.pricing_type === 'lumpsum') {
      return parseFloat(invoiceData.lumpsum_amount) || 0;
    } else {
      return (costing?.pax || 0) * (parseFloat(invoiceData.per_pax_rate) || 0);
    }
  };

  // Auto-calculate expense based on category
  const calculateExpenseAmount = (category) => {
    const cat = expenseCategories.find(c => c.id === category);
    if (!cat) return 0;
    
    const invoiceAmount = getInvoiceAmount();
    const headcount = getTotalHeadcount();
    
    if (cat.type === 'percentage' && cat.rate > 0) {
      return (invoiceAmount * cat.rate / 100).toFixed(2);
    } else if (cat.type === 'per_pax' && cat.rate > 0) {
      return (headcount * cat.rate).toFixed(2);
    }
    return '';
  };

  const addExpense = (categoryId = '') => {
    const cat = expenseCategories.find(c => c.id === categoryId);
    const autoAmount = categoryId ? calculateExpenseAmount(categoryId) : '';
    
    setExpenses([...expenses, {
      category: categoryId,
      description: cat?.description || '',
      expense_type: cat?.type || 'fixed',
      estimated_amount: autoAmount,
      actual_amount: '',
      remark: ''
    }]);
  };

  const removeExpense = (index) => {
    setExpenses(expenses.filter((_, i) => i !== index));
  };

  const updateExpense = (index, field, value) => {
    const updated = [...expenses];
    updated[index][field] = value;
    
    // Auto-calculate if category changed
    if (field === 'category') {
      const autoAmount = calculateExpenseAmount(value);
      if (autoAmount) {
        updated[index].estimated_amount = autoAmount;
        const cat = expenseCategories.find(c => c.id === value);
        updated[index].expense_type = cat?.type || 'fixed';
        updated[index].description = cat?.description || '';
      }
    }
    
    setExpenses(updated);
  };

  // Add all auto-calculated expenses
  const addAutoExpenses = () => {
    const autoCategories = expenseCategories.filter(c => c.type === 'percentage' || c.type === 'per_pax');
    const newExpenses = [];
    
    autoCategories.forEach(cat => {
      // Check if expense already exists
      if (!expenses.some(e => e.category === cat.id)) {
        const amount = calculateExpenseAmount(cat.id);
        if (amount && parseFloat(amount) > 0) {
          newExpenses.push({
            category: cat.id,
            description: cat.description || cat.name,
            expense_type: cat.type,
            estimated_amount: amount,
            actual_amount: '',
            remark: `Auto: ${cat.name}`
          });
        }
      }
    });
    
    if (newExpenses.length > 0) {
      setExpenses([...expenses, ...newExpenses]);
      toast.success(`Added ${newExpenses.length} auto-calculated expenses`);
    } else {
      toast.info('No new auto expenses to add');
    }
  };

  // Create Credit Note for HRDCorp deduction
  const createCreditNote = async () => {
    const invoiceAmount = getInvoiceAmount();
    if (!invoiceAmount || invoiceAmount <= 0) {
      toast.error('Please enter invoice amount first');
      return;
    }
    
    try {
      const response = await axiosInstance.post(`/finance/session/${session.id}/credit-note`, {
        reason: "HRDCorp Levy Deduction",
        description: "4% HRDCorp levy deducted from payment",
        percentage: 4,
        base_amount: invoiceAmount
      });
      
      toast.success(`Credit Note created: ${response.data.cn_number} (RM ${response.data.amount.toLocaleString()})`);
      await loadData(); // Reload to show the new CN
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create credit note');
    }
  };

  const saveAll = async () => {
    setSaving(true);
    try {
      const invoiceAmount = getInvoiceAmount();
      const taxRate = parseFloat(invoiceData.tax_rate) || 0;
      const taxAmount = invoiceAmount * taxRate / 100;
      
      // Save invoice (creates or updates)
      const invoicePayload = {
        pricing_type: invoiceData.pricing_type,
        line_items: invoiceData.pricing_type === 'lumpsum' 
          ? [{ description: 'Training Course Fee', quantity: 1, unit_price: invoiceAmount, amount: invoiceAmount }]
          : [{ description: 'Training Fee per Participant', quantity: costing?.pax || 0, unit_price: parseFloat(invoiceData.per_pax_rate) || 0, amount: invoiceAmount }],
        subtotal: invoiceAmount,
        tax_rate: taxRate,
        tax_amount: taxAmount,
        total_amount: invoiceAmount
      };
      
      // Use the new session-specific invoice endpoint that handles create/update
      await axiosInstance.post(`/finance/session/${session.id}/invoice`, invoicePayload);
      
      // Save trainer fees
      const validFees = trainerFees.filter(f => f.fee_amount && parseFloat(f.fee_amount) > 0);
      if (validFees.length > 0) {
        await axiosInstance.post(`/finance/session/${session.id}/trainer-fees`, validFees.map(f => ({
          ...f,
          fee_amount: parseFloat(f.fee_amount)
        })));
      }
      
      // Save coordinator fee
      if (session.coordinator_id && coordinatorFee.num_days > 0) {
        await axiosInstance.post(`/finance/session/${session.id}/coordinator-fee`, {
          coordinator_id: session.coordinator_id,
          num_days: parseInt(coordinatorFee.num_days),
          daily_rate: parseFloat(coordinatorFee.daily_rate)
        });
      }
      
      // Save expenses
      const validExpenses = expenses.filter(e => e.category && (e.estimated_amount || e.actual_amount));
      await axiosInstance.post(`/finance/session/${session.id}/expenses`, validExpenses.map(e => ({
        ...e,
        estimated_amount: parseFloat(e.estimated_amount) || 0,
        actual_amount: parseFloat(e.actual_amount) || 0
      })));
      
      // Save marketing
      if (marketing.marketing_user_id || marketing.create_new) {
        await axiosInstance.post(`/finance/session/${session.id}/marketing`, {
          marketing_user_id: marketing.marketing_user_id || null,
          commission_type: marketing.commission_type,
          commission_rate: parseFloat(marketing.commission_rate) || 0,
          fixed_amount: parseFloat(marketing.fixed_amount) || 0,
          create_new: marketing.create_new,
          full_name: marketing.full_name,
          id_number: marketing.id_number
        });
      }
      
      toast.success('Costing saved successfully');
      await loadData(); // Refresh to show updated data
      if (onUpdate) onUpdate();
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save costing');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  const calculateProfit = () => {
    const invoiceTotal = getInvoiceAmount();
    const taxRate = parseFloat(invoiceData.tax_rate) || 0;
    const taxAmount = invoiceTotal * taxRate / 100;
    const grossRevenue = invoiceTotal - taxAmount;
    
    const trainerTotal = trainerFees.reduce((sum, f) => sum + (parseFloat(f.fee_amount) || 0), 0);
    const coordTotal = (parseInt(coordinatorFee.num_days) || 0) * (parseFloat(coordinatorFee.daily_rate) || 0);
    const expensesTotal = expenses.reduce((sum, e) => 
      sum + (parseFloat(e.actual_amount) || parseFloat(e.estimated_amount) || 0), 0);
    
    const profitBeforeMarketing = grossRevenue - trainerTotal - coordTotal - expensesTotal;
    
    let marketingAmount = 0;
    if (marketing.commission_type === 'percentage') {
      marketingAmount = profitBeforeMarketing * (parseFloat(marketing.commission_rate) || 0) / 100;
    } else {
      marketingAmount = parseFloat(marketing.fixed_amount) || 0;
    }
    
    const finalProfit = profitBeforeMarketing - marketingAmount;
    const profitPct = grossRevenue > 0 ? (finalProfit / grossRevenue * 100) : 0;
    
    return { 
      invoiceTotal, taxAmount, taxRate, grossRevenue, 
      trainerTotal, coordTotal, expensesTotal, 
      profitBeforeMarketing, marketingAmount, finalProfit, profitPct 
    };
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p>Loading costing data...</p>
        </div>
      </div>
    );
  }

  const profit = calculateProfit();
  const headcount = getTotalHeadcount();

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg w-full max-w-5xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center z-10">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <DollarSign className="w-6 h-6 text-green-600" />
              Session Costing
            </h2>
            <p className="text-sm text-gray-500">{session.name}</p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={() => setShowClaimForm(true)}
              className="bg-green-50 border-green-200 hover:bg-green-100 text-green-700"
              data-testid="print-claim-form-btn"
            >
              <Download className="w-4 h-4 mr-2" />
              Download Claim Form
            </Button>
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={saveAll} disabled={saving} className="bg-green-600 hover:bg-green-700">
              <Save className="w-4 h-4 mr-2" />
              {saving ? 'Saving...' : 'Save All'}
            </Button>
          </div>
        </div>

        <div className="p-4 space-y-6">
          {/* Session Info */}
          <Card className="bg-blue-50">
            <CardContent className="pt-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div><Building2 className="w-4 h-4 inline mr-1" /> {costing?.company_name}</div>
                <div><Calendar className="w-4 h-4 inline mr-1" /> {costing?.training_dates}</div>
                <div><Users className="w-4 h-4 inline mr-1" /> {costing?.pax} Participants</div>
                <div><User className="w-4 h-4 inline mr-1" /> Total Headcount: {headcount}</div>
              </div>
            </CardContent>
          </Card>

          {/* Invoice / Revenue */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" />
                Invoice / Revenue
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Pricing Type</Label>
                  <Select value={invoiceData.pricing_type} onValueChange={(v) => setInvoiceData({...invoiceData, pricing_type: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="lumpsum">Lump Sum</SelectItem>
                      <SelectItem value="per_pax">Per Participant</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {invoiceData.pricing_type === 'lumpsum' ? (
                  <div>
                    <Label>Total Amount (RM)</Label>
                    <Input 
                      type="number" 
                      value={invoiceData.lumpsum_amount} 
                      onChange={(e) => setInvoiceData({...invoiceData, lumpsum_amount: e.target.value})}
                      placeholder="e.g. 8000"
                    />
                  </div>
                ) : (
                  <div>
                    <Label>Rate Per Participant (RM)</Label>
                    <Input 
                      type="number" 
                      value={invoiceData.per_pax_rate} 
                      onChange={(e) => setInvoiceData({...invoiceData, per_pax_rate: e.target.value})}
                      placeholder="e.g. 400"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Total: RM {((costing?.pax || 0) * (parseFloat(invoiceData.per_pax_rate) || 0)).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
              <div className="w-1/2">
                <Label>SST/Tax Rate (%)</Label>
                <Input 
                  type="number" 
                  value={invoiceData.tax_rate} 
                  onChange={(e) => setInvoiceData({...invoiceData, tax_rate: e.target.value})}
                  placeholder="e.g. 6"
                />
              </div>
              {profit.invoiceTotal > 0 && (
                <div className="text-sm text-blue-600 bg-blue-50 p-2 rounded">
                  Invoice: RM {profit.invoiceTotal.toLocaleString()} | Tax ({profit.taxRate}%): RM {profit.taxAmount.toLocaleString()} | Gross Revenue: RM {profit.grossRevenue.toLocaleString()}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Credit Notes Display (read-only) */}
          {creditNotes.length > 0 && (
            <Card className="bg-red-50 border-red-200">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-red-700">
                  <FileX className="w-5 h-5" />
                  Credit Notes
                </CardTitle>
                <CardDescription>Credit notes are managed in Finance Portal when recording payments</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {creditNotes.map((cn) => (
                    <div key={cn.id} className="flex justify-between items-center p-3 bg-white rounded-lg">
                      <div>
                        <p className="font-medium text-red-700">{cn.cn_number}</p>
                        <p className="text-sm text-gray-600">{cn.reason}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-red-600">- RM {cn.amount?.toLocaleString()}</p>
                        <Badge className={cn.status === 'approved' ? 'bg-green-500' : 'bg-yellow-500'}>
                          {cn.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Trainer Fees */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Users className="w-5 h-5 text-purple-600" />
                Trainer Fees
              </CardTitle>
              <CardDescription>Set custom fee for each trainer assigned to this session</CardDescription>
            </CardHeader>
            <CardContent>
              {trainerFees.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No trainers assigned to this session</p>
              ) : (
                <div className="space-y-3">
                  {trainerFees.map((fee, index) => (
                    <div key={index} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1">
                        <p className="font-medium">{fee.trainer_name}</p>
                        <Badge variant="outline" className="text-xs">{fee.role}</Badge>
                      </div>
                      <div className="w-32">
                        <Input 
                          type="number" 
                          value={fee.fee_amount} 
                          onChange={(e) => {
                            const updated = [...trainerFees];
                            updated[index].fee_amount = e.target.value;
                            setTrainerFees(updated);
                          }}
                          placeholder="Fee (RM)"
                        />
                      </div>
                      <div className="w-40">
                        <Input 
                          value={fee.remark || ''} 
                          onChange={(e) => {
                            const updated = [...trainerFees];
                            updated[index].remark = e.target.value;
                            setTrainerFees(updated);
                          }}
                          placeholder="Remark"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Coordinator Fee */}
          {session.coordinator_id && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <User className="w-5 h-5 text-pink-600" />
                  Coordinator Fee
                </CardTitle>
                <CardDescription>RM {coordinatorFee.daily_rate} per day</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <div>
                    <Label>Number of Days</Label>
                    <Input 
                      type="number" 
                      value={coordinatorFee.num_days} 
                      onChange={(e) => setCoordinatorFee({...coordinatorFee, num_days: parseInt(e.target.value) || 1})}
                      className="w-24"
                    />
                  </div>
                  <div>
                    <Label>Daily Rate (RM)</Label>
                    <Input 
                      type="number" 
                      value={coordinatorFee.daily_rate} 
                      onChange={(e) => setCoordinatorFee({...coordinatorFee, daily_rate: parseFloat(e.target.value) || 50})}
                      className="w-24"
                    />
                  </div>
                  <div className="pt-6">
                    <Badge className="bg-pink-100 text-pink-800">
                      Total: RM {((parseInt(coordinatorFee.num_days) || 0) * (parseFloat(coordinatorFee.daily_rate) || 0)).toLocaleString()}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Expenses */}
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Truck className="w-5 h-5 text-orange-600" />
                    Training Expenses
                  </CardTitle>
                  <CardDescription>
                    Estimated and actual expenses • Total headcount: {headcount} (for F&B calc)
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={addAutoExpenses} disabled={profit.invoiceTotal === 0}>
                    <Calculator className="w-4 h-4 mr-1" /> Auto-Add
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => addExpense()}>
                    <Plus className="w-4 h-4 mr-1" /> Add Expense
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {expenses.length === 0 ? (
                <div className="text-center py-4">
                  <p className="text-gray-500 mb-2">No expenses added yet</p>
                  <p className="text-xs text-gray-400">Click "Auto-Add" to add HRDCorp (4%), Wear & Tear (2%), Printing (1%), F&B (RM25/pax)</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {expenses.map((expense, index) => {
                    const cat = expenseCategories.find(c => c.id === expense.category);
                    return (
                      <div key={index} className="grid grid-cols-6 gap-2 items-center p-3 bg-gray-50 rounded-lg">
                        <div className="col-span-1">
                          <Select value={expense.category} onValueChange={(v) => updateExpense(index, 'category', v)}>
                            <SelectTrigger><SelectValue placeholder="Category" /></SelectTrigger>
                            <SelectContent>
                              {expenseCategories.map(cat => (
                                <SelectItem key={cat.id} value={cat.id}>
                                  {cat.name} {cat.rate > 0 ? `(${cat.type === 'percentage' ? cat.rate + '%' : 'RM' + cat.rate + '/pax'})` : ''}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <Input 
                          value={expense.description || ''} 
                          onChange={(e) => updateExpense(index, 'description', e.target.value)}
                          placeholder="Description"
                        />
                        <div>
                          <Input 
                            type="number"
                            value={expense.estimated_amount || ''} 
                            onChange={(e) => updateExpense(index, 'estimated_amount', e.target.value)}
                            placeholder="Estimated (RM)"
                            className={cat?.rate > 0 ? 'bg-yellow-50' : ''}
                          />
                          {cat?.rate > 0 && (
                            <p className="text-xs text-yellow-600 mt-1">Auto-calculated</p>
                          )}
                        </div>
                        <Input 
                          type="number"
                          value={expense.actual_amount || ''} 
                          onChange={(e) => updateExpense(index, 'actual_amount', e.target.value)}
                          placeholder="Actual (RM)"
                        />
                        <Input 
                          value={expense.remark || ''} 
                          onChange={(e) => updateExpense(index, 'remark', e.target.value)}
                          placeholder="Remark"
                        />
                        <Button variant="ghost" size="sm" onClick={() => removeExpense(index)}>
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Marketing Commission */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-600" />
                Marketing Commission
              </CardTitle>
              <CardDescription>Commission is calculated from PROFIT (not gross revenue)</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2">
                <input 
                  type="checkbox" 
                  id="create-new-marketing"
                  checked={marketing.create_new}
                  onChange={(e) => setMarketing({...marketing, create_new: e.target.checked, marketing_user_id: ''})}
                />
                <Label htmlFor="create-new-marketing">Create new marketing person</Label>
              </div>
              
              {marketing.create_new ? (
                <div className="grid grid-cols-2 gap-4 p-4 bg-blue-50 rounded-lg">
                  <div>
                    <Label>Full Name *</Label>
                    <Input 
                      value={marketing.full_name} 
                      onChange={(e) => setMarketing({...marketing, full_name: e.target.value})}
                      placeholder="Marketing person name"
                    />
                  </div>
                  <div>
                    <Label>IC Number *</Label>
                    <Input 
                      value={marketing.id_number} 
                      onChange={(e) => setMarketing({...marketing, id_number: e.target.value})}
                      placeholder="IC number"
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <Label>Select Marketing Person (from staff list)</Label>
                  <Select 
                    value={marketing.marketing_user_id || "none"} 
                    onValueChange={(v) => setMarketing({...marketing, marketing_user_id: v === "none" ? "" : v})}
                  >
                    <SelectTrigger><SelectValue placeholder="Select marketing person" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      {marketingUsers.map(user => (
                        <SelectItem key={user.id} value={user.id}>
                          {user.full_name} ({user.role}{user.additional_roles?.includes("marketing") ? " + Marketing" : ""})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {marketingUsers.length === 0 && (
                    <p className="text-xs text-gray-500 mt-1">No staff available. Use "Create new" option.</p>
                  )}
                </div>
              )}
              
              {(marketing.marketing_user_id || marketing.create_new) && (
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label>Commission Type</Label>
                    <Select 
                      value={marketing.commission_type} 
                      onValueChange={(v) => setMarketing({...marketing, commission_type: v})}
                    >
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="percentage">Percentage of Profit</SelectItem>
                        <SelectItem value="fixed">Fixed Amount</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {marketing.commission_type === 'percentage' ? (
                    <div>
                      <Label>Commission Rate (%)</Label>
                      <Input 
                        type="number"
                        value={marketing.commission_rate} 
                        onChange={(e) => setMarketing({...marketing, commission_rate: e.target.value})}
                        placeholder="e.g. 10"
                      />
                    </div>
                  ) : (
                    <div>
                      <Label>Fixed Amount (RM)</Label>
                      <Input 
                        type="number"
                        value={marketing.fixed_amount} 
                        onChange={(e) => setMarketing({...marketing, fixed_amount: e.target.value})}
                        placeholder="e.g. 500"
                      />
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Profit Summary */}
          <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Calculator className="w-5 h-5 text-green-600" />
                Profit Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 bg-white rounded-lg">
                  <p className="text-xs text-gray-500">Invoice Total</p>
                  <p className="text-lg font-bold">RM {profit.invoiceTotal.toLocaleString()}</p>
                </div>
                <div className="p-3 bg-white rounded-lg">
                  <p className="text-xs text-gray-500">Less Tax ({profit.taxRate}%)</p>
                  <p className="text-lg font-bold text-red-600">- RM {profit.taxAmount.toLocaleString()}</p>
                </div>
                <div className="p-3 bg-white rounded-lg">
                  <p className="text-xs text-gray-500">Gross Revenue</p>
                  <p className="text-lg font-bold text-blue-600">RM {profit.grossRevenue.toLocaleString()}</p>
                </div>
                <div className="p-3 bg-white rounded-lg">
                  <p className="text-xs text-gray-500">Trainer Fees</p>
                  <p className="text-lg font-bold text-purple-600">- RM {profit.trainerTotal.toLocaleString()}</p>
                </div>
                <div className="p-3 bg-white rounded-lg">
                  <p className="text-xs text-gray-500">Coordinator Fee</p>
                  <p className="text-lg font-bold text-pink-600">- RM {profit.coordTotal.toLocaleString()}</p>
                </div>
                <div className="p-3 bg-white rounded-lg">
                  <p className="text-xs text-gray-500">Expenses</p>
                  <p className="text-lg font-bold text-orange-600">- RM {profit.expensesTotal.toLocaleString()}</p>
                </div>
                <div className="p-3 bg-white rounded-lg">
                  <p className="text-xs text-gray-500">Marketing ({marketing.commission_type === 'percentage' ? `${marketing.commission_rate || 0}%` : 'Fixed'})</p>
                  <p className="text-lg font-bold text-green-600">- RM {profit.marketingAmount.toLocaleString()}</p>
                </div>
                <div className="p-3 bg-green-100 rounded-lg border-2 border-green-400">
                  <p className="text-xs text-green-700 font-medium">NET PROFIT</p>
                  <p className={`text-2xl font-bold ${profit.finalProfit >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                    RM {profit.finalProfit.toLocaleString()}
                  </p>
                  <p className="text-xs text-green-600">{profit.profitPct.toFixed(1)}% margin</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
      
      {/* Claim Form Print Modal */}
      {showClaimForm && (
        <ClaimFormPrint 
          session={session} 
          onClose={() => setShowClaimForm(false)} 
        />
      )}
    </div>
  );
};

export default SessionCosting;
