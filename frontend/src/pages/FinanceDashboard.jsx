import React, { useState, useEffect } from 'react';
import { axiosInstance } from '../App';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { 
  DollarSign, FileText, CreditCard, TrendingUp, 
  CheckCircle, Clock, AlertCircle, LogOut, RefreshCw,
  Check, X, Plus, FileX, Receipt, Edit, Printer, Settings, Download, FileSpreadsheet, Users,
  BarChart3, Wallet, Lock, Unlock, RotateCcw, Globe, BookOpen
} from 'lucide-react';
import { FaFacebook, FaInstagram, FaTiktok, FaYoutube, FaTwitter, FaLinkedin } from 'react-icons/fa';
import HRModule from '../components/HRModule';
import ProfitLossLedger from '../components/ProfitLossLedger';
import PettyCash from '../components/PettyCash';
import { downloadPdf, downloadPdfLandscape } from '../utils/htmlToPdf';
import { DigitalSignatureManager } from '../components/shared/DigitalSignatureManager';
import { InvoicesTab } from '../components/finance/InvoicesTab';
import { PaymentsTab } from '../components/finance/PaymentsTab';
import AdminFeePayoutsPanel from '../components/admin/AdminFeePayoutsPanel';
import { CreditNotesTab } from '../components/finance/CreditNotesTab';
import { PayablesTab } from '../components/finance/PayablesTab';
import { AuditLogTab } from '../components/finance/AuditLogTab';
import { SettingsTab } from '../components/finance/SettingsTab';
import AccountingTab from '../components/finance/AccountingTab';
import { BalanceSheetTab } from '../components/finance/BalanceSheetTab';
import { KpiDrilldownDialog } from '../components/KpiDrilldown';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const FinanceDashboard = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dashboard, setDashboard] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [payments, setPayments] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const currentYear = new Date().getFullYear();
  const [selectedYear, setSelectedYear] = useState(currentYear);
  // Always include current year and 2 previous years, plus any years from data
  const [availableYears, setAvailableYears] = useState([currentYear, currentYear - 1, currentYear - 2]);
  
  // Company Settings State
  const [companySettings, setCompanySettings] = useState({
    company_name: 'MDDRC SDN BHD',
    company_reg_no: '',
    address_line1: '',
    address_line2: '',
    city: '',
    postcode: '',
    state: '',
    phone: '',
    email: '',
    website: '',
    logo_url: '',
    logo_filename: '',
    bank_name: '',
    bank_account_name: '',
    bank_account_number: '',
    invoice_terms: 'Upon receipt of invoice',
    invoice_footer_note: 'Thank you for your business!',
    // Document styling settings
    tagline: 'Towards a Nation of Safe Drivers',
    primary_color: '#1a365d',
    secondary_color: '#4472C4',
    header_font: 'Arial',
    body_font: 'Arial',
    logo_width: 150,
    logo_position: 'center',
    show_watermark: true,
    watermark_opacity: 0.08,
    tagline_font: 'Georgia',
    tagline_style: 'italic',
    // Indemnity form
    indemnity_form_url: '',
    indemnity_form_filename: ''
  });
  const [settingsLoading, setSettingsLoading] = useState(false);
  
  // Social Media Links State
  const [socialMediaLinks, setSocialMediaLinks] = useState([]);
  const [showSocialMediaModal, setShowSocialMediaModal] = useState(false);
  const [editingSocialMedia, setEditingSocialMedia] = useState(null);
  const [socialMediaForm, setSocialMediaForm] = useState({
    platform: '',
    url: '',
    icon: 'globe',
    is_active: true
  });
  
  // Payment form state
  const [paymentForm, setPaymentForm] = useState({
    invoice_id: '',
    amount: '',
    payment_date: new Date().toISOString().split('T')[0],
    payment_method: 'bank_transfer',
    reference_number: '',
    notes: '',
    create_cn: false,
    cn_percentage: '4',
    cn_reason: 'HRDCorp Levy Deduction'
  });
  const [pendingInvoices, setPendingInvoices] = useState([]);
  const [creditNotes, setCreditNotes] = useState([]);
  const [showCNDialog, setShowCNDialog] = useState(false);
  const [payables, setPayables] = useState({ trainer_fees: [], coordinator_fees: [], marketing_commissions: [], admin_fees: [] });
  const [payablesPeriods, setPayablesPeriods] = useState([]);
  const [payablesYear, setPayablesYear] = useState(new Date().getFullYear());
  const [payablesMonth, setPayablesMonth] = useState(new Date().getMonth() + 1);
  const [currentPeriodStatus, setCurrentPeriodStatus] = useState({ status: 'open', exists: false });
  const [reopenDialog, setReopenDialog] = useState({ open: false, reason: '' });
  
  // KPI Drill-down State
  const [drillOpen, setDrillOpen] = useState(false);
  const [drillData, setDrillData] = useState(null);
  const [drillLoading, setDrillLoading] = useState(false);

  const handleKpiCardClick = async (type) => {
    setDrillOpen(true);
    setDrillLoading(true);
    setDrillData(null);
    try {
      const res = await axiosInstance.get(`/admin/kpi-drilldown/${type}`);
      setDrillData(res.data);
    } catch (e) {
      setDrillData({ type: "error", title: "Error", items: [] });
    } finally {
      setDrillLoading(false);
    }
  };

  // Billing Parties State
  const [billingParties, setBillingParties] = useState([]);
  const [showBillingPartyModal, setShowBillingPartyModal] = useState(false);
  const [editingBillingParty, setEditingBillingParty] = useState(null);
  const [billingPartyForm, setBillingPartyForm] = useState({
    name: '',
    registration_no: '',
    address_line1: '',
    address_line2: '',
    city: '',
    postcode: '',
    state: '',
    country: 'Malaysia',
    phone: '',
    email: '',
    contact_person: ''
  });
  
  // Invoice Edit State
  const [editingInvoice, setEditingInvoice] = useState(null);
  const [editForm, setEditForm] = useState({
    bill_to_name: '',
    bill_to_address: '',
    bill_to_reg_no: '',
    your_reference: '',
    programme_name: '',
    training_dates: '',
    venue: '',
    pax: 0,
    line_items: [],
    subtotal: 0,
    mobilisation_fee: 0,
    rounding: 0,
    tax_rate: 0,
    tax_amount: 0,
    discount: 0,
    total_amount: 0
  });

  useEffect(() => {
    loadDashboard();
    loadInvoices();
    loadPendingInvoices();
    loadCreditNotes();
    loadPayables();
    loadCompanySettings();
    loadBillingParties();
  }, []);

  // Load payments when Payments tab is activated
  useEffect(() => {
    if (activeTab === 'payments') {
      loadPayments();
    }
  }, [activeTab]);

  // Reload dashboard when year changes
  useEffect(() => {
    loadDashboard(selectedYear);
    loadInvoices(selectedYear);
  }, [selectedYear]);

  const loadDashboard = async (year = selectedYear) => {
    try {
      const response = await axiosInstance.get(`/finance/dashboard${year ? `?year=${year}` : ''}`);
      setDashboard(response.data);
      // Merge available years from API with default years (current + 2 previous)
      if (response.data.available_years && response.data.available_years.length > 0) {
        const defaultYears = [currentYear, currentYear - 1, currentYear - 2];
        const mergedYears = [...new Set([...defaultYears, ...response.data.available_years])].sort((a, b) => b - a);
        setAvailableYears(mergedYears);
      }
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    }
  };

  const loadPayables = async () => {
    try {
      // Load all pending payables
      const [trainerRes, coordRes, commRes, adminFeeRes] = await Promise.all([
        axiosInstance.get('/finance/payables/trainer-fees'),
        axiosInstance.get('/finance/payables/coordinator-fees'),
        axiosInstance.get('/finance/payables/marketing-commissions'),
        axiosInstance.get('/finance/payables/admin-fees')
      ]);
      setPayables({
        trainer_fees: trainerRes.data || [],
        coordinator_fees: coordRes.data || [],
        marketing_commissions: commRes.data || [],
        admin_fees: adminFeeRes.data || []
      });
      
      // Load period status
      await loadPeriodStatus();
    } catch (error) {
      console.error('Failed to load payables:', error);
    }
  };

  const loadPeriodStatus = async () => {
    try {
      const response = await axiosInstance.get(`/finance/payables/period-status?year=${payablesYear}&month=${payablesMonth}`);
      setCurrentPeriodStatus(response.data);
    } catch (error) {
      console.error('Failed to load period status:', error);
    }
  };

  const loadPayablesPeriods = async () => {
    try {
      const response = await axiosInstance.get('/finance/payables/periods');
      setPayablesPeriods(response.data);
    } catch (error) {
      console.error('Failed to load periods:', error);
    }
  };

  const handleClosePeriod = async () => {
    try {
      // Always fetch fresh period status first
      const freshStatus = await axiosInstance.get(`/finance/payables/period-status?year=${payablesYear}&month=${payablesMonth}`);
      let periodId = freshStatus.data.period?.id;
      
      // If period doesn't exist, create it
      if (!freshStatus.data.exists) {
        const createRes = await axiosInstance.post('/finance/payables/periods', { year: payablesYear, month: payablesMonth });
        periodId = createRes.data.id;
      }
      
      // Now close the period
      if (periodId) {
        await axiosInstance.post(`/finance/payables/periods/${periodId}/close`);
        toast.success(`Period ${payablesYear}-${String(payablesMonth).padStart(2, '0')} closed successfully`);
        await loadPeriodStatus();
      } else {
        toast.error('Could not find or create period');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to close period');
    }
  };

  const handleReopenPeriod = async () => {
    // Open dialog instead of using window.prompt
    setReopenDialog({ open: true, reason: '' });
  };

  const confirmReopenPeriod = async () => {
    if (!reopenDialog.reason || reopenDialog.reason.trim().length < 5) {
      toast.error('Reason must be at least 5 characters');
      return;
    }
    
    try {
      if (currentPeriodStatus.period?.id) {
        await axiosInstance.post(`/finance/payables/periods/${currentPeriodStatus.period.id}/reopen?reason=${encodeURIComponent(reopenDialog.reason)}`);
        toast.success('Period reopened successfully');
        setReopenDialog({ open: false, reason: '' });
        await loadPeriodStatus();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reopen period');
    }
  };

  const handleExportPayablesExcel = async () => {
    try {
      const response = await axiosInstance.get(`/finance/payables/export-excel?year=${payablesYear}&month=${payablesMonth}`);
      const data = response.data;
      
      if (!data.data || Object.keys(data.data).length === 0) {
        toast.error('No payables data to export for this period');
        return;
      }
      
      // Generate Excel-like CSV content matching your format
      let csvContent = "NAME,INVOICE NUMBER,TRAINING DATE,POSITION,COMPANY,DETAILS,PRICE\n";
      
      // Sort entries by name
      const sortedNames = Object.keys(data.data).sort();
      
      sortedNames.forEach((name) => {
        const group = data.data[name];
        // Sort items by training date
        const sortedItems = [...group.items].sort((a, b) => {
          const dateA = a.training_date ? new Date(a.training_date) : new Date(0);
          const dateB = b.training_date ? new Date(b.training_date) : new Date(0);
          return dateA - dateB;
        });
        
        sortedItems.forEach((item, index) => {
          const trainingDate = item.training_date 
            ? new Date(item.training_date).toLocaleDateString('en-MY', { day: 'numeric', month: 'long', year: 'numeric' }) 
            : '-';
          // Name only on first row for each person
          const displayName = index === 0 ? name.toUpperCase() : '';
          csvContent += `"${displayName}","${item.invoice_number || '-'}","${trainingDate}","${item.position || '-'}","${item.company || '-'}","${item.details || '-'}","RM ${(item.amount || 0).toFixed(2)}"\n`;
        });
        // Add TOTAL row for this person
        csvContent += `"","","","","","TOTAL","RM ${(group.total || 0).toFixed(2)}"\n`;
      });
      
      // Add GRAND TOTAL row
      csvContent += `"GRAND TOTAL","","","","","","RM ${(data.grand_total || 0).toFixed(2)}"\n`;
      
      // Download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Payables_${data.period_name.replace(' ', '_')}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      toast.success(`Exported payables for ${data.period_name}`);
    } catch (error) {
      console.error('Export error:', error);
      toast.error(error.response?.data?.detail || 'Failed to export payables');
    }
  };

  const handleMarkPaid = async (type, id) => {
    // Check if period is closed
    if (currentPeriodStatus.status === 'closed') {
      toast.error('Cannot modify payables - period is closed');
      return;
    }
    
    try {
      let endpoint = '';
      if (type === 'trainer') endpoint = `/finance/trainer-fees/${id}/mark-paid`;
      else if (type === 'coordinator') endpoint = `/finance/coordinator-fees/${id}/mark-paid`;
      else if (type === 'marketing') endpoint = `/finance/income/commission/${id}/mark-paid`;
      
      await axiosInstance.post(endpoint);
      toast.success('Marked as paid successfully');
      loadPayables();
      loadDashboard();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark as paid');
    }
  };

  const handleBulkMarkPaid = async (type, items) => {
    try {
      let successCount = 0;
      for (const item of items) {
        if (item.status === 'paid') continue;
        let endpoint = '';
        if (type === 'trainer') endpoint = `/finance/trainer-fees/${item.id}/mark-paid`;
        else if (type === 'coordinator') endpoint = `/finance/coordinator-fees/${item.id}/mark-paid`;
        else if (type === 'marketing') endpoint = `/finance/income/commission/${item.id}/mark-paid`;
        
        await axiosInstance.post(endpoint);
        successCount++;
      }
      toast.success(`Marked ${successCount} items as paid`);
      loadPayables();
      loadDashboard();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark as paid');
    }
  };

  // Group payables by month based on session start_date
  const groupByMonth = (records) => {
    const groups = {};
    records.forEach(record => {
      // Get month from created_at or session date
      const dateStr = record.session_start_date || record.created_at;
      if (!dateStr) return;
      const date = new Date(dateStr);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      const monthLabel = date.toLocaleString('default', { month: 'long', year: 'numeric' });
      
      if (!groups[monthKey]) {
        groups[monthKey] = { label: monthLabel, records: [], total: 0 };
      }
      groups[monthKey].records.push(record);
      groups[monthKey].total += record.fee_amount || record.total_fee || record.calculated_amount || 0;
    });
    // Sort by month descending (newest first)
    return Object.entries(groups)
      .sort((a, b) => b[0].localeCompare(a[0]))
      .map(([key, value]) => ({ key, ...value }));
  };

  const loadInvoices = async (year = selectedYear) => {
    setLoading(true);
    try {
      const response = await axiosInstance.get(`/finance/invoices${year ? `?year=${year}` : ''}`);
      setInvoices(response.data);
    } catch (error) {
      toast.error('Failed to load invoices');
    } finally {
      setLoading(false);
    }
  };

  // Load company settings
  const loadCompanySettings = async () => {
    try {
      const response = await axiosInstance.get('/finance/company-settings');
      setCompanySettings(response.data);
      setSocialMediaLinks(response.data.social_media_links || []);
    } catch (error) {
      console.error('Failed to load company settings');
    }
  };

  // Social media link handlers
  const handleSaveSocialMedia = async () => {
    if (!socialMediaForm.platform.trim() || !socialMediaForm.url.trim()) {
      toast.error('Platform name and URL are required');
      return;
    }
    
    let updatedLinks = [...socialMediaLinks];
    if (editingSocialMedia !== null) {
      updatedLinks[editingSocialMedia] = socialMediaForm;
    } else {
      updatedLinks.push(socialMediaForm);
    }
    
    try {
      await axiosInstance.put('/finance/company-settings', {
        ...companySettings,
        social_media_links: updatedLinks
      });
      setSocialMediaLinks(updatedLinks);
      setShowSocialMediaModal(false);
      setEditingSocialMedia(null);
      setSocialMediaForm({ platform: '', url: '', icon: 'globe', is_active: true });
      toast.success('Social media link saved');
    } catch (error) {
      toast.error('Failed to save social media link');
    }
  };

  const handleDeleteSocialMedia = async (index) => {
    if (!window.confirm('Delete this social media link?')) return;
    const updatedLinks = socialMediaLinks.filter((_, i) => i !== index);
    try {
      await axiosInstance.put('/finance/company-settings', {
        ...companySettings,
        social_media_links: updatedLinks
      });
      setSocialMediaLinks(updatedLinks);
      toast.success('Social media link deleted');
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  // Load billing parties
  const loadBillingParties = async () => {
    try {
      const response = await axiosInstance.get('/finance/billing-parties');
      setBillingParties(response.data);
    } catch (error) {
      console.error('Failed to load billing parties');
    }
  };

  // Handle billing party form submit
  const handleBillingPartySubmit = async () => {
    if (!billingPartyForm.name.trim()) {
      toast.error('Name is required');
      return;
    }
    try {
      if (editingBillingParty) {
        await axiosInstance.put(`/finance/billing-parties/${editingBillingParty.id}`, billingPartyForm);
        toast.success('Billing party updated');
      } else {
        await axiosInstance.post('/finance/billing-parties', billingPartyForm);
        toast.success('Billing party created');
      }
      setShowBillingPartyModal(false);
      setEditingBillingParty(null);
      setBillingPartyForm({
        name: '', registration_no: '', address_line1: '', address_line2: '',
        city: '', postcode: '', state: '', country: 'Malaysia', phone: '', email: '', contact_person: ''
      });
      loadBillingParties();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save billing party');
    }
  };

  // Delete billing party
  const handleDeleteBillingParty = async (partyId) => {
    if (!window.confirm('Are you sure you want to delete this billing party?')) return;
    try {
      await axiosInstance.delete(`/finance/billing-parties/${partyId}`);
      toast.success('Billing party deleted');
      loadBillingParties();
    } catch (error) {
      toast.error('Failed to delete billing party');
    }
  };

  // Edit billing party
  const openEditBillingParty = (party) => {
    setEditingBillingParty(party);
    setBillingPartyForm({
      name: party.name || '',
      registration_no: party.registration_no || '',
      address_line1: party.address_line1 || '',
      address_line2: party.address_line2 || '',
      city: party.city || '',
      postcode: party.postcode || '',
      state: party.state || '',
      country: party.country || 'Malaysia',
      phone: party.phone || '',
      email: party.email || '',
      contact_person: party.contact_person || ''
    });
    setShowBillingPartyModal(true);
  };

  // Apply billing party to invoice form
  const applyBillingPartyToInvoice = (partyId) => {
    if (!partyId || partyId === 'none') {
      return; // Don't clear the form, just don't do anything
    }
    const party = billingParties.find(p => p.id === partyId);
    if (party) {
      const addressParts = [party.address_line1, party.address_line2, party.city, party.postcode, party.state, party.country]
        .filter(Boolean).join(', ');
      setEditForm({
        ...editForm,
        bill_to_name: party.name,
        bill_to_reg_no: party.registration_no || '',
        bill_to_address: addressParts
      });
    }
  };

  // Save company settings
  const handleSaveSettings = async () => {
    setSettingsLoading(true);
    try {
      await axiosInstance.put('/finance/company-settings', companySettings);
      toast.success('Company settings saved');
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSettingsLoading(false);
    }
  };

  // Print Receipt
  const handlePrintReceipt = async (payment) => {
    try {
      const response = await axiosInstance.get(`/finance/payments/${payment.id}/receipt`);
      const { receipt_number, invoice, company_settings: settings } = response.data;
      
      // Also get app settings for logo
      let logoUrl = settings?.logo_url;
      if (!logoUrl) {
        try {
          const appSettings = await axiosInstance.get('/settings');
          logoUrl = appSettings.data?.logo_url;
        } catch (e) {
          // Ignore error, use default
        }
      }
      
      const receiptHtml = `<!DOCTYPE html><html><head><title>Receipt ${receipt_number}</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
          .header { text-align: center; margin-bottom: 30px; }
          .logo-img { max-height: 80px; margin-bottom: 10px; }
          .logo-text { font-size: 24px; font-weight: bold; color: #1a365d; }
          .company-info { font-size: 12px; color: #666; margin-top: 5px; }
          .receipt-title { font-size: 20px; font-weight: bold; margin: 20px 0; text-align: center; background: #f0f0f0; padding: 10px; }
          .details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
          .detail-box { padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
          .detail-label { font-weight: bold; font-size: 12px; color: #666; margin-bottom: 5px; }
          .detail-value { font-size: 14px; }
          .amount-box { text-align: center; padding: 30px; background: #e8f5e9; border-radius: 10px; margin: 20px 0; }
          .amount { font-size: 32px; font-weight: bold; color: #2e7d32; }
          .footer { margin-top: 40px; font-size: 12px; color: #666; text-align: center; }
        </style></head><body>
          <div class="header">
            ${logoUrl ? `<img src="${logoUrl.startsWith('/') ? API_URL + logoUrl : logoUrl}" class="logo-img" alt="Logo" />` : ''}
            <div class="logo-text">${settings?.company_name || 'MDDRC SDN BHD'}</div>
            <div class="company-info">
              ${settings?.company_reg_no ? `(${settings.company_reg_no})` : ''}<br>
              ${settings?.address_line1 || ''} ${settings?.address_line2 || ''}<br>
              ${settings?.city || ''} ${settings?.postcode || ''} ${settings?.state || ''}<br>
              ${settings?.phone ? `Tel: ${settings.phone}` : ''} ${settings?.email ? `| Email: ${settings.email}` : ''}
            </div>
          </div>
          <div class="receipt-title">OFFICIAL RECEIPT</div>
          <div class="details-grid">
            <div class="detail-box">
              <div class="detail-label">Receipt No:</div>
              <div class="detail-value">${receipt_number}</div>
              <div class="detail-label" style="margin-top: 10px;">Date:</div>
              <div class="detail-value">${new Date(payment.payment_date).toLocaleDateString('en-MY')}</div>
            </div>
            <div class="detail-box">
              <div class="detail-label">Invoice No:</div>
              <div class="detail-value">${invoice?.invoice_number || payment.invoice_number || '-'}</div>
              <div class="detail-label" style="margin-top: 10px;">Payment Method:</div>
              <div class="detail-value">${payment.payment_method?.replace('_', ' ').toUpperCase() || '-'}</div>
            </div>
          </div>
          <div class="detail-box">
            <div class="detail-label">RECEIVED FROM:</div>
            <div class="detail-value" style="font-size: 16px; font-weight: bold;">${invoice?.bill_to_name || invoice?.company_name || '-'}</div>
            <div class="detail-value">${invoice?.programme_name || ''}</div>
          </div>
          <div class="amount-box">
            <div style="font-size: 14px; color: #666; margin-bottom: 10px;">Amount Received</div>
            <div class="amount">RM ${payment.amount?.toLocaleString('en-MY', {minimumFractionDigits: 2})}</div>
            ${payment.reference_number ? `<div style="font-size: 12px; color: #666; margin-top: 10px;">Ref: ${payment.reference_number}</div>` : ''}
          </div>
          ${payment.notes ? `<div class="detail-box"><div class="detail-label">Notes:</div><div class="detail-value">${payment.notes}</div></div>` : ''}
          <div class="footer">
            <p>This is a computer-generated receipt. No signature required.</p>
            <p>${settings?.invoice_footer_note || 'Thank you for your business!'}</p>
            ${(settings?.invoice_custom_fields || []).filter(f => f.position === 'Footer' || f.position === 'footer').map(f => `<p><strong>${f.label}:</strong> ${f.value}</p>`).join('')}
          </div>
        </body></html>`;
      downloadPdf(receiptHtml, `Receipt_${receipt_number}`);
    } catch (error) {
      toast.error('Failed to generate receipt');
    }
  };

  // Export invoices to Excel
  const handleExportInvoices = async () => {
    try {
      const response = await axiosInstance.get('/finance/invoices/export', {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `invoices_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Invoices exported successfully');
    } catch (error) {
      toast.error('Failed to export invoices');
    }
  };

  const loadPendingInvoices = async () => {
    try {
      const response = await axiosInstance.get('/finance/invoices');
      // Filter to show only issued invoices (ready for payment)
      const pending = response.data.filter(inv => inv.status === 'issued' || inv.status === 'approved');
      setPendingInvoices(pending);
    } catch (error) {
      console.error('Failed to load pending invoices');
    }
  };

  const loadCreditNotes = async () => {
    try {
      const response = await axiosInstance.get('/finance/credit-notes');
      setCreditNotes(response.data);
    } catch (error) {
      console.error('Failed to load credit notes');
    }
  };

  const loadAuditLogs = async () => {
    try {
      const response = await axiosInstance.get('/finance/audit-log?limit=50');
      setAuditLogs(response.data);
    } catch (error) {
      toast.error('Failed to load audit logs');
    }
  };

  const loadPayments = async () => {
    try {
      const response = await axiosInstance.get('/finance/payments');
      setPayments(response.data);
    } catch (error) {
      console.error('Failed to load payments');
    }
  };

  const handleApproveInvoice = async (invoiceId) => {
    try {
      await axiosInstance.post(`/finance/invoices/${invoiceId}/approve`);
      toast.success('Invoice approved');
      loadInvoices();
      loadDashboard();
      loadPendingInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve invoice');
    }
  };

  const handleIssueInvoice = async (invoiceId) => {
    try {
      await axiosInstance.post(`/finance/invoices/${invoiceId}/issue`);
      toast.success('Invoice issued');
      loadInvoices();
      loadDashboard();
      loadPendingInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to issue invoice');
    }
  };

  const handleCancelInvoice = async (invoiceId) => {
    const reason = prompt('Enter cancellation reason:');
    if (!reason) return;
    
    try {
      await axiosInstance.post(`/finance/invoices/${invoiceId}/cancel?reason=${encodeURIComponent(reason)}`);
      toast.success('Invoice cancelled');
      loadInvoices();
      loadDashboard();
      loadPendingInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel invoice');
    }
  };

  // Open edit dialog for an invoice - auto-populate from session
  const handleEditInvoice = async (invoice) => {
    // Try to get session details for auto-population
    let sessionData = null;
    if (invoice.session_id) {
      try {
        const response = await axiosInstance.get(`/sessions/${invoice.session_id}`);
        sessionData = response.data;
      } catch (e) {
        // Session might not exist, continue with invoice data
      }
    }
    
    setEditForm({
      bill_to_name: invoice.bill_to_name || invoice.company_name || '',
      bill_to_address: invoice.bill_to_address || '',
      bill_to_reg_no: invoice.bill_to_reg_no || '',
      your_reference: invoice.your_reference || '',
      // Auto-populate from session if available, otherwise use invoice data
      programme_name: invoice.programme_name || sessionData?.program_name || sessionData?.name || '',
      training_dates: invoice.training_dates || (sessionData ? `${sessionData.start_date}${sessionData.end_date && sessionData.end_date !== sessionData.start_date ? ' - ' + sessionData.end_date : ''}` : ''),
      venue: invoice.venue || sessionData?.venue || '',
      pax: invoice.pax || sessionData?.participant_ids?.length || sessionData?.pax || 0,
      line_items: invoice.line_items || [{description: '', quantity: 1, unit_price: 0, amount: 0}],
      subtotal: invoice.subtotal || 0,
      mobilisation_fee: invoice.mobilisation_fee || 0,
      rounding: invoice.rounding || 0,
      tax_rate: invoice.tax_rate || 0,
      tax_amount: invoice.tax_amount || 0,
      discount: invoice.discount || 0,
      total_amount: invoice.total_amount || 0
    });
    setEditingInvoice(invoice);
  };

  // Save invoice edits
  const handleSaveInvoice = async () => {
    try {
      await axiosInstance.put(`/finance/invoices/${editingInvoice.id}`, editForm);
      toast.success('Invoice updated');
      setEditingInvoice(null);
      loadInvoices();
      loadDashboard();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update invoice');
    }
  };

  // Add line item
  const addLineItem = () => {
    setEditForm({
      ...editForm,
      line_items: [...editForm.line_items, {description: '', quantity: 1, unit_price: 0, amount: 0}]
    });
  };

  // Update line item
  const updateLineItem = (index, field, value) => {
    const newItems = [...editForm.line_items];
    newItems[index][field] = value;
    
    // Calculate amount
    if (field === 'quantity' || field === 'unit_price') {
      newItems[index].amount = (newItems[index].quantity || 0) * (newItems[index].unit_price || 0);
    }
    
    // Recalculate subtotal
    const subtotal = newItems.reduce((sum, item) => sum + (item.amount || 0), 0);
    const totalBeforeTax = subtotal + (editForm.mobilisation_fee || 0) + (editForm.rounding || 0) - (editForm.discount || 0);
    const taxAmount = totalBeforeTax * (editForm.tax_rate || 0) / 100;
    const totalAmount = totalBeforeTax + taxAmount;
    
    setEditForm({
      ...editForm,
      line_items: newItems,
      subtotal,
      tax_amount: taxAmount,
      total_amount: totalAmount
    });
  };

  // Remove line item
  const removeLineItem = (index) => {
    const newItems = editForm.line_items.filter((_, i) => i !== index);
    const subtotal = newItems.reduce((sum, item) => sum + (item.amount || 0), 0);
    setEditForm({
      ...editForm,
      line_items: newItems,
      subtotal
    });
  };

  // Recalculate totals when fees change
  const recalculateTotals = (updates) => {
    const newForm = { ...editForm, ...updates };
    const subtotal = (newForm.line_items || []).reduce((sum, item) => sum + (item.amount || 0), 0);
    const totalBeforeTax = subtotal + (newForm.mobilisation_fee || 0) + (newForm.rounding || 0) - (newForm.discount || 0);
    const taxAmount = totalBeforeTax * (newForm.tax_rate || 0) / 100;
    const totalAmount = totalBeforeTax + taxAmount;
    
    setEditForm({
      ...newForm,
      subtotal,
      tax_amount: taxAmount,
      total_amount: totalAmount
    });
  };

  // Credit Note Workflow Functions
  const handleApproveCN = async (cnId) => {
    try {
      await axiosInstance.post(`/finance/credit-notes/${cnId}/approve`);
      toast.success('Credit note approved');
      loadCreditNotes();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve credit note');
    }
  };

  const handleIssueCN = async (cnId) => {
    try {
      await axiosInstance.post(`/finance/credit-notes/${cnId}/issue`);
      toast.success('Credit note issued');
      loadCreditNotes();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to issue credit note');
    }
  };

  // Print Payables Report
  const handlePrintPayables = async () => {
    let settings = companySettings;
    let logoUrl = companySettings.logo_url;
    
    if (!logoUrl) {
      try {
        const appSettings = await axiosInstance.get('/settings');
        logoUrl = appSettings.data?.logo_url;
      } catch (e) {}
    }
    
    const primaryColor = settings.primary_color || '#1a365d';
    const today = new Date().toLocaleDateString('en-MY', { year: 'numeric', month: 'long', day: 'numeric' });
    const monthNames = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const periodName = `${monthNames[payablesMonth]} ${payablesYear}`;
    
    // Filter payables by selected month/year
    const filterByMonth = (item) => {
      const sessionDate = item.session_start_date || item.session_date;
      if (!sessionDate) return false;
      const d = new Date(sessionDate);
      return d.getFullYear() === payablesYear && (d.getMonth() + 1) === payablesMonth;
    };
    
    const filteredTrainer = payables.trainer_fees.filter(f => f.status !== 'paid' && filterByMonth(f));
    const filteredCoord = payables.coordinator_fees.filter(f => f.status !== 'paid' && filterByMonth(f));
    const filteredMarketing = payables.marketing_commissions.filter(f => f.status !== 'paid' && filterByMonth(f));
    
    // Group all payables by person name
    const groupedData = {};
    
    filteredTrainer.forEach(item => {
      const name = (item.trainer_name || 'Unknown').toUpperCase();
      if (!groupedData[name]) groupedData[name] = { items: [], total: 0 };
      groupedData[name].items.push({
        invoice_number: item.invoice_number || '-',
        training_date: item.session_start_date || item.session_date,
        position: item.trainer_role || 'Trainer',
        company: item.company_name || '-',
        details: item.session_name || '-',
        amount: item.fee_amount || 0
      });
      groupedData[name].total += (item.fee_amount || 0);
    });
    
    filteredCoord.forEach(item => {
      const name = (item.coordinator_name || 'Unknown').toUpperCase();
      if (!groupedData[name]) groupedData[name] = { items: [], total: 0 };
      groupedData[name].items.push({
        invoice_number: item.invoice_number || '-',
        training_date: item.session_start_date || item.session_date,
        position: 'Coordinator',
        company: item.company_name || '-',
        details: item.session_name || '-',
        amount: item.total_fee || 0
      });
      groupedData[name].total += (item.total_fee || 0);
    });
    
    filteredMarketing.forEach(item => {
      const name = (item.marketer_name || item.marketing_user_name || item.user_name || 'Unknown').toUpperCase();
      if (!groupedData[name]) groupedData[name] = { items: [], total: 0 };
      groupedData[name].items.push({
        invoice_number: item.invoice_number || '-',
        training_date: item.session_start_date || item.session_date,
        position: 'Marketing',
        company: item.company_name || '-',
        details: item.session_name || '-',
        amount: item.calculated_amount || 0
      });
      groupedData[name].total += (item.calculated_amount || 0);
    });
    
    // Sort names alphabetically
    const sortedNames = Object.keys(groupedData).sort();
    
    // Build table rows matching Excel format
    let tableRows = '';
    let grandTotal = 0;
    
    sortedNames.forEach(name => {
      const group = groupedData[name];
      grandTotal += group.total;
      
      // Sort items by date
      group.items.sort((a, b) => new Date(a.training_date || 0) - new Date(b.training_date || 0));
      
      group.items.forEach((item, idx) => {
        const dateStr = item.training_date 
          ? new Date(item.training_date).toLocaleDateString('en-MY', { day: 'numeric', month: 'long', year: 'numeric' }) 
          : '-';
        tableRows += `
          <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: ${idx === 0 ? 'bold' : 'normal'};">${idx === 0 ? name : ''}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">${item.invoice_number}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">${dateStr}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">${item.position}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">${item.company}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">${item.details}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">RM ${item.amount.toLocaleString('en-MY', {minimumFractionDigits: 2})}</td>
          </tr>`;
      });
      
      // Add TOTAL row for this person
      tableRows += `
        <tr style="background: #f3f4f6;">
          <td colspan="6" style="padding: 8px; text-align: right; font-weight: bold;">TOTAL</td>
          <td style="padding: 8px; text-align: right; font-weight: bold;">RM ${group.total.toLocaleString('en-MY', {minimumFractionDigits: 2})}</td>
        </tr>`;
    });
    
    // Calculate summary totals
    const trainerTotal = filteredTrainer.reduce((sum, f) => sum + (f.fee_amount || 0), 0);
    const coordTotal = filteredCoord.reduce((sum, f) => sum + (f.total_fee || 0), 0);
    const marketingTotal = filteredMarketing.reduce((sum, f) => sum + (f.calculated_amount || 0), 0);
    
    const payablesHtml = `<!DOCTYPE html><html><head><title>Payables Report - ${periodName}</title>
        <style>
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { font-family: Arial, sans-serif; font-size: 10px; padding: 15px; max-width: 297mm; margin: 0 auto; line-height: 1.4; }
          .header { display: flex; align-items: center; gap: 15px; padding-bottom: 15px; border-bottom: 3px solid ${primaryColor}; margin-bottom: 15px; }
          .logo-img { width: 70px; height: auto; }
          .company-name { font-size: 14px; font-weight: bold; color: ${primaryColor}; }
          .company-info { font-size: 9px; color: #444; }
          .report-title { font-size: 16px; font-weight: bold; text-align: center; color: ${primaryColor}; margin: 15px 0; padding: 8px; background: #f8fafc; border-radius: 4px; }
          .report-period { text-align: center; font-size: 12px; color: #333; margin-bottom: 5px; font-weight: bold; }
          .report-date { text-align: center; font-size: 10px; color: #666; margin-bottom: 15px; }
          .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 15px; }
          .summary-card { padding: 10px; border-radius: 4px; text-align: center; }
          .summary-card.blue { background: #dbeafe; }
          .summary-card.green { background: #dcfce7; }
          .summary-card.purple { background: #f3e8ff; }
          .summary-card.yellow { background: #fef9c3; }
          .summary-label { font-size: 9px; color: #555; margin-bottom: 3px; }
          .summary-value { font-size: 12px; font-weight: bold; }
          table { width: 100%; border-collapse: collapse; font-size: 9px; }
          th { background: #1a365d; color: white; padding: 8px 6px; text-align: left; font-weight: 600; }
          th:last-child { text-align: right; }
          .grand-total { background: #1a365d; color: white; font-weight: bold; font-size: 11px; }
          .grand-total td { padding: 10px 8px; }
          .footer { margin-top: 20px; font-size: 8px; color: #666; border-top: 1px solid #ddd; padding-top: 10px; }
          .signature-area { margin-top: 25px; display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
          .signature-box { text-align: center; }
          .signature-line { border-top: 1px solid #333; width: 120px; margin: 25px auto 5px; }
        </style></head><body>
        <div class="header">
          ${logoUrl ? `<img src="${logoUrl.startsWith('/') ? API_URL + logoUrl : logoUrl}" class="logo-img" alt="Logo" />` : ''}
          <div>
            <div class="company-name">${settings.company_name || 'MDDRC SDN BHD'}</div>
            <div class="company-info">${settings.address_line1 || ''} ${settings.city || ''} ${settings.postcode || ''}</div>
          </div>
        </div>
        <div class="report-title">STAFF PAYABLES REPORT</div>
        <div class="report-period">${periodName}</div>
        <div class="report-date">Generated on ${today}</div>
        <div class="summary-grid">
          <div class="summary-card blue"><div class="summary-label">Trainer Fees</div><div class="summary-value">RM ${trainerTotal.toLocaleString('en-MY', {minimumFractionDigits: 2})}</div></div>
          <div class="summary-card green"><div class="summary-label">Coordinator Fees</div><div class="summary-value">RM ${coordTotal.toLocaleString('en-MY', {minimumFractionDigits: 2})}</div></div>
          <div class="summary-card purple"><div class="summary-label">Marketing Commission</div><div class="summary-value">RM ${marketingTotal.toLocaleString('en-MY', {minimumFractionDigits: 2})}</div></div>
          <div class="summary-card yellow"><div class="summary-label">TOTAL PAYABLE</div><div class="summary-value">RM ${grandTotal.toLocaleString('en-MY', {minimumFractionDigits: 2})}</div></div>
        </div>
        <table><thead><tr>
          <th style="width: 15%;">NAME</th><th style="width: 10%;">INVOICE NO</th><th style="width: 12%;">TRAINING DATE</th>
          <th style="width: 10%;">POSITION</th><th style="width: 18%;">COMPANY</th><th style="width: 20%;">DETAILS</th><th style="width: 15%;">PRICE</th>
        </tr></thead><tbody>
          ${tableRows}
          <tr class="grand-total"><td colspan="6" style="text-align: right; font-weight: bold;">GRAND TOTAL</td><td style="text-align: right; font-weight: bold;">RM ${grandTotal.toLocaleString('en-MY', {minimumFractionDigits: 2})}</td></tr>
        </tbody></table>
        <div class="signature-area">
          <div class="signature-box"><div class="signature-line"></div><div>Prepared By</div></div>
          <div class="signature-box"><div class="signature-line"></div><div>Approved By</div></div>
        </div>
        <div class="footer"><p>This report is computer generated.</p></div>
      </body></html>`;
    downloadPdfLandscape(payablesHtml, `Payables_Report_${periodName.replace(/\s/g, '_')}`);
  };

  // Print Credit Note
  const handlePrintCreditNote = async (cn) => {
    let settings = companySettings;
    let logoUrl = companySettings.logo_url;
    
    if (!logoUrl) {
      try {
        const appSettings = await axiosInstance.get('/settings');
        logoUrl = appSettings.data?.logo_url;
      } catch (e) {}
    }
    
    // Get the invoice to get bill_to details
    let billToName = cn.company_name || '-';
    if (cn.invoice_id) {
      try {
        const invRes = await axiosInstance.get(`/finance/invoices/${cn.invoice_id}`);
        const invoice = invRes.data;
        // Use bill_to_name if available, otherwise company_name from invoice
        billToName = invoice.bill_to_name || invoice.company_name || billToName;
      } catch (e) {
        console.log('Could not fetch invoice for bill_to');
      }
    }
    
    const primaryColor = settings.primary_color || '#1a365d';
    const secondaryColor = settings.secondary_color || '#dc2626';
    const tagline = settings.tagline || 'Towards a Nation of Safe Drivers';
    
    // Build custom fields HTML
    const headerCustomFields = (settings.invoice_custom_fields || [])
      .filter(f => f.position === 'Header' || f.position === 'header')
      .map(f => ` • ${f.label}: ${f.value}`)
      .join('');
    const footerCustomFields = (settings.invoice_custom_fields || [])
      .filter(f => f.position === 'Footer' || f.position === 'footer')
      .map(f => `<p><strong>${f.label}:</strong> ${f.value}</p>`)
      .join('');
    
    const cnHtml = `<!DOCTYPE html><html><head><title>Credit Note ${cn.cn_number}</title>
        <style>
          @page { size: A4; margin: 15mm; }
          @media print { 
            body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
          }
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { 
            font-family: Arial, sans-serif; 
            font-size: 12px;
            padding: 30px; 
            max-width: 210mm;
            margin: 0 auto; 
            line-height: 1.5;
          }
          
          .header { 
            display: flex;
            align-items: center;
            gap: 20px;
            padding-bottom: 20px;
            border-bottom: 3px solid ${secondaryColor};
            margin-bottom: 25px;
          }
          .logo-img { width: 100px; height: auto; flex-shrink: 0; }
          .company-details { flex: 1; }
          .company-name { font-size: 18px; font-weight: bold; color: ${primaryColor}; margin-bottom: 5px; }
          .company-info { font-size: 11px; color: #444; line-height: 1.5; }
          
          .cn-title { 
            font-size: 24px; 
            font-weight: bold; 
            text-align: center; 
            color: white; 
            background: ${secondaryColor};
            margin: 25px 0;
            padding: 15px;
            border-radius: 4px;
          }
          
          .details-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin-bottom: 30px;
          }
          .detail-box { 
            padding: 15px; 
            border: 1px solid #ddd; 
            border-radius: 4px;
            font-size: 11px;
          }
          .detail-label { 
            font-weight: bold; 
            font-size: 10px; 
            color: #666; 
            margin-bottom: 5px; 
            text-transform: uppercase;
          }
          .detail-value { font-size: 12px; margin-bottom: 5px; }
          
          .amount-box {
            text-align: center;
            padding: 40px;
            background: #fef2f2;
            border: 2px solid ${secondaryColor};
            border-radius: 8px;
            margin: 30px 0;
          }
          .amount-label { font-size: 16px; color: #666; margin-bottom: 15px; }
          .amount-value { font-size: 36px; font-weight: bold; color: ${secondaryColor}; }
          
          .reason-box {
            padding: 20px;
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 4px;
            margin-bottom: 30px;
          }
          
          .footer { 
            margin-top: 40px; 
            font-size: 10px; 
            color: #555;
            padding-top: 20px;
            border-top: 1px solid #ddd;
          }
          .footer p { margin-bottom: 5px; }
          
          .tagline { 
            font-style: italic;
            color: ${primaryColor}; 
            font-size: 12px; 
            text-align: center; 
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #eee;
          }
          
          .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            background: ${cn.status === 'issued' ? '#22c55e' : cn.status === 'approved' ? '#3b82f6' : '#eab308'};
            color: white;
          }
        </style>
      </head>
      <body>
        <div class="header">
          ${logoUrl ? `<img src="${logoUrl.startsWith('/') ? API_URL + logoUrl : logoUrl}" class="logo-img" alt="Logo" />` : ''}
          <div class="company-details">
            <div class="company-name">${settings.company_name || 'MDDRC SDN BHD'}</div>
            <div class="company-info">
              ${settings.company_reg_no ? `(${settings.company_reg_no})` : ''}
              ${settings.address_line1 ? ` • ${settings.address_line1}` : ''}${settings.address_line2 ? `, ${settings.address_line2}` : ''}<br>
              ${settings.city || ''}${settings.postcode ? ` ${settings.postcode}` : ''}${settings.state ? `, ${settings.state}` : ''}
              ${settings.phone ? ` • Tel: ${settings.phone}` : ''}${settings.email ? ` • ${settings.email}` : ''}
              ${headerCustomFields}
            </div>
          </div>
        </div>
        
        <div class="cn-title">CREDIT NOTE</div>
        
        <div class="details-grid">
          <div class="detail-box">
            <div class="detail-label">Credit Note To:</div>
            <div class="detail-value" style="font-weight: bold; font-size: 14px;">${billToName}</div>
            ${cn.session_name ? `<div class="detail-value">Session: ${cn.session_name}</div>` : ''}
          </div>
          <div class="detail-box">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
              <div><div class="detail-label">CN Number:</div><div class="detail-value" style="color: ${secondaryColor}; font-weight: bold;">${cn.cn_number}</div></div>
              <div><div class="detail-label">Date:</div><div class="detail-value">${cn.issued_at ? new Date(cn.issued_at).toLocaleDateString('en-MY') : new Date(cn.created_at).toLocaleDateString('en-MY')}</div></div>
              <div><div class="detail-label">Invoice Ref:</div><div class="detail-value">${cn.invoice_number || '-'}</div></div>
              <div><div class="detail-label">Status:</div><span class="status-badge">${cn.status}</span></div>
            </div>
          </div>
        </div>
        
        <div class="reason-box">
          <div class="detail-label">Reason / Description:</div>
          <div class="detail-value" style="font-size: 13px; margin-top: 8px;">${cn.reason || 'HRDCorp Levy Deduction'}</div>
          <div class="detail-value">${cn.description || ''}</div>
          ${cn.base_amount ? `<div class="detail-value" style="margin-top: 12px;">Base Amount: RM ${cn.base_amount?.toLocaleString('en-MY', {minimumFractionDigits: 2})} × ${cn.percentage || 4}%</div>` : ''}
        </div>
        
        <div class="amount-box">
          <div class="amount-label">Credit Note Amount</div>
          <div class="amount-value">- RM ${cn.amount?.toLocaleString('en-MY', {minimumFractionDigits: 2})}</div>
        </div>
        
        <div class="footer">
          <p>This credit note is issued in relation to the above-referenced invoice.</p>
          <p>${settings.invoice_footer_note || 'Thank you for your business!'}</p>
          ${footerCustomFields}
        </div>
        
        <div class="tagline">"${tagline}"</div>
      </body></html>`;
    downloadPdf(cnHtml, `CreditNote_${cn.cn_number?.replace(/\//g, '_') || 'draft'}`);
  };

  // Print invoice
  // Print invoice with company settings
  const handlePrintInvoice = async (invoice) => {
    // Get company settings for invoice
    let settings = companySettings;
    let logoUrl = companySettings.logo_url;
    
    // Also try to get app settings logo if not set
    if (!logoUrl) {
      try {
        const appSettings = await axiosInstance.get('/settings');
        logoUrl = appSettings.data?.logo_url;
      } catch (e) {
        // Ignore error, use default
      }
    }
    
    // Styling variables from settings
    const primaryColor = settings.primary_color || '#1a365d';
    const secondaryColor = settings.secondary_color || '#4472C4';
    const tagline = settings.tagline || 'Towards a Nation of Safe Drivers';
    
    // Build custom fields HTML
    const headerCustomFields = (settings.invoice_custom_fields || [])
      .filter(f => f.position === 'Header' || f.position === 'header')
      .map(f => ` • ${f.label}: ${f.value}`)
      .join('');
    const footerCustomFields = (settings.invoice_custom_fields || [])
      .filter(f => f.position === 'Footer' || f.position === 'footer')
      .map(f => `<p><strong>${f.label}:</strong> ${f.value}</p>`)
      .join('');
    
    const invoiceHtml = `<!DOCTYPE html><html><head><title>Invoice ${invoice.invoice_number}</title>
        <style>
          @page { size: A4; margin: 15mm; }
          @media print { 
            body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
          }
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { 
            font-family: Arial, sans-serif; 
            font-size: 12px;
            padding: 25px; 
            max-width: 210mm;
            margin: 0 auto; 
            line-height: 1.5;
          }
          
          /* Header with Logo */
          .header { 
            display: flex;
            align-items: center;
            gap: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid ${primaryColor};
            margin-bottom: 20px;
          }
          .logo-img { 
            width: 100px; 
            height: auto;
            flex-shrink: 0;
          }
          .company-details {
            flex: 1;
          }
          .company-name { 
            font-size: 18px; 
            font-weight: bold; 
            color: ${primaryColor};
            margin-bottom: 5px;
          }
          .company-info { 
            font-size: 11px; 
            color: #444;
            line-height: 1.5;
          }
          
          .invoice-title { 
            font-size: 22px; 
            font-weight: bold; 
            text-align: center; 
            color: ${primaryColor}; 
            margin: 15px 0;
            padding: 10px;
            background: #f0f4f8;
          }
          
          /* Details Grid */
          .details-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 15px; 
            margin-bottom: 20px;
          }
          .detail-box { 
            padding: 12px; 
            border: 1px solid #ddd; 
            border-radius: 4px;
            font-size: 11px;
          }
          .detail-label { 
            font-weight: bold; 
            font-size: 10px; 
            color: #666; 
            margin-bottom: 4px; 
            text-transform: uppercase;
          }
          .detail-value { font-size: 12px; margin-bottom: 4px; }
          
          /* Training Details */
          .training-box {
            padding: 12px;
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 11px;
          }
          .training-box .detail-label { display: inline; }
          .training-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
          
          /* Table */
          table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
          th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; font-size: 11px; }
          th { background: ${secondaryColor}; color: white; font-weight: bold; font-size: 10px; text-transform: uppercase; }
          .text-right { text-align: right; }
          
          /* Totals */
          .totals { 
            width: 50%;
            margin-left: auto;
            font-size: 11px;
          }
          .total-row { 
            display: flex; 
            justify-content: space-between; 
            padding: 6px 0; 
            border-bottom: 1px solid #eee;
          }
          .grand-total { 
            font-size: 14px; 
            font-weight: bold; 
            background: ${secondaryColor}; 
            color: white; 
            padding: 12px 15px; 
            margin-top: 8px; 
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
          }
          
          /* Footer */
          .footer { 
            margin-top: 30px; 
            font-size: 10px; 
            color: #555;
            padding-top: 15px;
            border-top: 1px solid #ddd;
          }
          .footer p { margin-bottom: 5px; }
          
          .tagline { 
            font-style: italic;
            color: ${primaryColor}; 
            font-size: 12px; 
            text-align: center; 
            margin-top: 15px;
            padding-top: 12px;
            border-top: 1px solid #eee;
          }
        </style>
      </head>
      <body>
        <!-- Header -->
        <div class="header">
          ${logoUrl ? `<img src="${logoUrl.startsWith('/') ? API_URL + logoUrl : logoUrl}" class="logo-img" alt="Logo" />` : ''}
          <div class="company-details">
            <div class="company-name">${settings.company_name || 'MDDRC SDN BHD'}</div>
            <div class="company-info">
              ${settings.company_reg_no ? `(${settings.company_reg_no})` : ''}
              ${settings.address_line1 ? ` • ${settings.address_line1}` : ''}${settings.address_line2 ? `, ${settings.address_line2}` : ''}<br>
              ${settings.city || ''}${settings.postcode ? ` ${settings.postcode}` : ''}${settings.state ? `, ${settings.state}` : ''}
              ${settings.phone ? ` • Tel: ${settings.phone}` : ''}${settings.email ? ` • ${settings.email}` : ''}
              ${headerCustomFields}
            </div>
          </div>
        </div>
        
        <div class="invoice-title">INVOICE</div>
        
        <div class="details-grid">
          <div class="detail-box">
            <div class="detail-label">Bill To:</div>
            <div class="detail-value" style="font-weight: bold;">${invoice.bill_to_name || invoice.company_name || '-'}</div>
            ${invoice.bill_to_address ? `<div class="detail-value">${invoice.bill_to_address}</div>` : ''}
            ${invoice.bill_to_reg_no ? `<div class="detail-value">Reg: ${invoice.bill_to_reg_no}</div>` : ''}
          </div>
          <div class="detail-box">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px;">
              <div><div class="detail-label">Invoice No:</div><div class="detail-value">${invoice.invoice_number}</div></div>
              <div><div class="detail-label">Date:</div><div class="detail-value">${invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString('en-MY') : (invoice.issued_at ? new Date(invoice.issued_at).toLocaleDateString('en-MY') : new Date().toLocaleDateString('en-MY'))}</div></div>
              ${invoice.your_reference ? `<div style="grid-column: span 2;"><div class="detail-label">Your Ref:</div><div class="detail-value">${invoice.your_reference}</div></div>` : ''}
            </div>
          </div>
        </div>
        
        <div class="training-box">
          <div class="training-grid">
            <div><span class="detail-label">Program:</span> ${invoice.programme_name || '-'}</div>
            <div><span class="detail-label">Company:</span> ${invoice.company_name || '-'}</div>
            <div><span class="detail-label">Training Date:</span> ${invoice.training_dates || '-'}</div>
            <div><span class="detail-label">Venue:</span> ${invoice.venue || '-'}</div>
          </div>
        </div>
        
        <table>
          <thead>
            <tr>
              <th style="width: 30px;">No</th>
              <th>Description</th>
              <th class="text-right" style="width: 50px;">Qty</th>
              <th class="text-right" style="width: 80px;">Price (RM)</th>
              <th class="text-right" style="width: 90px;">Total (RM)</th>
            </tr>
          </thead>
          <tbody>
            ${(invoice.line_items || []).map((item, idx) => `
              <tr>
                <td>${idx + 1}</td>
                <td>${item.description || '-'}</td>
                <td class="text-right">${item.quantity || 0}</td>
                <td class="text-right">${(item.unit_price || 0).toLocaleString('en-MY', {minimumFractionDigits: 2})}</td>
                <td class="text-right">${(item.amount || 0).toLocaleString('en-MY', {minimumFractionDigits: 2})}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        
        <div class="totals">
          <div class="total-row"><span>Sub-Total:</span><span>RM ${(invoice.subtotal || 0).toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>
          ${invoice.mobilisation_fee ? `<div class="total-row"><span>Mobilisation Fee:</span><span>RM ${invoice.mobilisation_fee.toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>` : ''}
          ${invoice.rounding ? `<div class="total-row"><span>Rounding:</span><span>RM ${invoice.rounding.toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>` : ''}
          ${invoice.tax_amount ? `<div class="total-row"><span>Tax (${invoice.tax_rate || 0}%):</span><span>RM ${invoice.tax_amount.toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>` : ''}
          ${invoice.discount ? `<div class="total-row"><span>Discount:</span><span>- RM ${invoice.discount.toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>` : ''}
          <div class="grand-total"><span>GRAND TOTAL</span><span>RM ${(invoice.total_amount || 0).toLocaleString('en-MY', {minimumFractionDigits: 2})}</span></div>
        </div>
        
        <div class="footer">
          <p><strong>Payment Terms:</strong> ${settings.invoice_terms || 'Upon receipt of invoice'}</p>
          <p><strong>Bank:</strong> ${settings.bank_name || '-'} | <strong>Account:</strong> ${settings.bank_account_name || settings.company_name || '-'} | <strong>No:</strong> ${settings.bank_account_number || '-'}</p>
          <p>${settings.invoice_footer_note || 'Thank you for your business!'}</p>
          ${footerCustomFields}
        </div>
        
        <div class="tagline">"${tagline}"</div>
      </body></html>`;
    downloadPdf(invoiceHtml, `Invoice_${invoice.invoice_number?.replace(/\//g, '_') || 'draft'}`);
  };

  const handleRecordPayment = async () => {
    if (!paymentForm.invoice_id) {
      toast.error('Please select an invoice');
      return;
    }
    if (!paymentForm.amount || parseFloat(paymentForm.amount) <= 0) {
      toast.error('Please enter a valid payment amount');
      return;
    }

    try {
      // Record the payment
      await axiosInstance.post('/finance/payments', {
        invoice_id: paymentForm.invoice_id,
        amount: parseFloat(paymentForm.amount),
        payment_date: paymentForm.payment_date,
        payment_method: paymentForm.payment_method,
        reference_number: paymentForm.reference_number,
        notes: paymentForm.notes
      });

      // If CN checkbox is checked, create and issue credit note
      if (paymentForm.create_cn) {
        const selectedInvoice = pendingInvoices.find(inv => inv.id === paymentForm.invoice_id);
        if (selectedInvoice) {
          // Create the credit note
          const cnResponse = await axiosInstance.post(`/finance/session/${selectedInvoice.session_id}/credit-note`, {
            reason: paymentForm.cn_reason,
            description: `${paymentForm.cn_percentage}% deduction`,
            percentage: parseFloat(paymentForm.cn_percentage),
            base_amount: selectedInvoice.total_amount
          });
          
          // Auto-issue the credit note since payment is received
          if (cnResponse.data.id) {
            await axiosInstance.post(`/finance/credit-notes/${cnResponse.data.id}/issue`);
          }
          toast.success('Credit Note created and issued');
        }
      }

      toast.success('Payment recorded successfully');
      
      // Reset form
      setPaymentForm({
        invoice_id: '',
        amount: '',
        payment_date: new Date().toISOString().split('T')[0],
        payment_method: 'bank_transfer',
        reference_number: '',
        notes: '',
        create_cn: false,
        cn_percentage: '4',
        cn_reason: 'HRDCorp Levy Deduction'
      });
      
      loadInvoices();
      loadDashboard();
      loadPendingInvoices();
      loadPayments();
      loadCreditNotes();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to record payment');
    }
  };

  const handleInvoiceSelect = (invoiceId) => {
    const selected = pendingInvoices.find(inv => inv.id === invoiceId);
    setPaymentForm({
      ...paymentForm,
      invoice_id: invoiceId,
      amount: selected?.total_amount?.toString() || ''
    });
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      auto_draft: { color: 'bg-gray-500', label: 'Draft' },
      draft: { color: 'bg-gray-500', label: 'Draft' },
      finance_review: { color: 'bg-yellow-500', label: 'Under Review' },
      approved: { color: 'bg-blue-500', label: 'Approved' },
      issued: { color: 'bg-purple-500', label: 'Issued' },
      paid: { color: 'bg-green-500', label: 'Paid' },
      cancelled: { color: 'bg-red-500', label: 'Cancelled' },
      voided: { color: 'bg-red-700', label: 'VOIDED' }
    };
    const config = statusConfig[status] || { color: 'bg-gray-400', label: status };
    return <Badge className={`${config.color} text-white`}>{config.label}</Badge>;
  };

  // Create replacement invoice for voided invoice
  const handleCreateReplacementInvoice = async (invoiceId) => {
    if (!window.confirm('Create a replacement invoice? This will generate a new invoice number and copy all data from the voided invoice.')) return;
    try {
      const response = await axiosInstance.post(`/finance/invoices/${invoiceId}/create-replacement`);
      toast.success(`Replacement invoice created: ${response.data.new_invoice_number}`);
      loadInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create replacement invoice');
    }
  };

  // Reverse voided invoice back to draft
  const handleReverseVoidedInvoice = async (invoiceId) => {
    if (!window.confirm('Reverse this voided invoice back to Draft status? This will clear all void information.')) return;
    try {
      const response = await axiosInstance.post(`/finance/invoices/${invoiceId}/reverse-void`);
      toast.success(`Invoice ${response.data.invoice_number} reversed to Draft`);
      loadInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reverse voided invoice');
    }
  };

  // Filter invoices based on status
  const filteredInvoices = statusFilter === 'all' 
    ? invoices 
    : statusFilter === 'pending' 
      ? invoices.filter(inv => !['paid', 'cancelled', 'voided'].includes(inv.status))
      : statusFilter === 'draft'
        ? invoices.filter(inv => ['auto_draft', 'finance_review', 'draft'].includes(inv.status))
        : invoices.filter(inv => inv.status === statusFilter);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 sm:py-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <div className="flex items-center gap-3">
            <DollarSign className="w-6 h-6 sm:w-8 sm:h-8 text-green-600" />
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-gray-900">Finance Portal</h1>
              <p className="text-xs sm:text-sm text-gray-500">Welcome, {user?.full_name}</p>
            </div>
          </div>
          <Button variant="outline" onClick={onLogout} size="sm">
            <LogOut className="w-4 h-4 sm:mr-2" />
            <span className="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6 flex gap-1 h-auto w-full justify-start bg-gray-100 p-2 rounded-lg overflow-x-auto scrollbar-hide md:flex-wrap">
            <TabsTrigger value="dashboard" className="flex-shrink-0 text-xs sm:text-sm">Dashboard</TabsTrigger>
            <TabsTrigger value="invoices" className="flex-shrink-0 text-xs sm:text-sm">Invoices</TabsTrigger>
            <TabsTrigger value="payables" className="flex-shrink-0 text-xs sm:text-sm">Payables</TabsTrigger>
            <TabsTrigger value="payments" className="flex-shrink-0 text-xs sm:text-sm">Payments</TabsTrigger>
            <TabsTrigger value="credit-notes" className="flex-shrink-0 text-xs sm:text-sm">Credit Notes</TabsTrigger>
            <TabsTrigger value="profit-loss" className="flex-shrink-0 text-xs sm:text-sm">
              <BarChart3 className="w-4 h-4 mr-1 hidden sm:inline" />
              P&L Ledger
            </TabsTrigger>
            <TabsTrigger value="balance-sheet" className="flex-shrink-0 text-xs sm:text-sm" data-testid="balance-sheet-tab">
              <Globe className="w-4 h-4 mr-1 hidden sm:inline" />
              Balance Sheet
            </TabsTrigger>
            <TabsTrigger value="petty-cash" className="flex-shrink-0 text-xs sm:text-sm">
              <Wallet className="w-4 h-4 mr-1 hidden sm:inline" />
              Petty Cash
            </TabsTrigger>
            <TabsTrigger value="hr" className="flex-shrink-0 text-xs sm:text-sm">
              <Users className="w-4 h-4 mr-1 hidden sm:inline" />
              HR & Payroll
            </TabsTrigger>
            <TabsTrigger value="audit" className="flex-shrink-0 text-xs sm:text-sm">Audit Log</TabsTrigger>
            <TabsTrigger value="accounting" className="flex-shrink-0 text-xs sm:text-sm">
              <BookOpen className="w-3 h-3 mr-1" />
              Accounting
            </TabsTrigger>
            <TabsTrigger value="settings" className="flex-shrink-0 text-xs sm:text-sm">
              <Settings className="w-4 h-4 mr-1 hidden sm:inline" />
              Settings
            </TabsTrigger>
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard">
            {/* Year Filter */}
            <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
              <div className="flex items-center gap-3">
                <Label className="text-sm font-medium text-gray-700">Financial Year:</Label>
                <Select value={selectedYear?.toString()} onValueChange={(val) => setSelectedYear(parseInt(val))}>
                  <SelectTrigger className="w-[140px]" data-testid="year-selector">
                    <SelectValue placeholder="Select Year" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableYears.map(year => (
                      <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="text-sm text-gray-500">
                Showing data for <span className="font-semibold text-gray-800">{selectedYear}</span>
              </div>
            </div>

            {!dashboard ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6" data-testid="finance-loading">
                {[1,2,3,4].map(i => (
                  <Card key={i} className="border">
                    <CardHeader className="pb-2"><div className="h-4 w-24 bg-gray-200 animate-pulse rounded" /></CardHeader>
                    <CardContent><div className="h-8 w-20 bg-gray-200 animate-pulse rounded mb-2" /><div className="h-3 w-32 bg-gray-200 animate-pulse rounded" /></CardContent>
                  </Card>
                ))}
              </div>
            ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
              <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200 cursor-pointer hover:shadow-md transition-shadow active:scale-[0.98]" onClick={() => handleKpiCardClick('total_invoices')} data-testid="fin-card-total">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-blue-700 flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    Total Invoices
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-blue-900">
                    {dashboard?.invoices?.total || 0}
                  </div>
                  <p className="text-sm text-blue-600">
                    RM {(dashboard?.financials?.total_issued || 0).toLocaleString()}
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200 cursor-pointer hover:shadow-md transition-shadow active:scale-[0.98]" onClick={() => handleKpiCardClick('collected')} data-testid="fin-card-collected">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-green-700 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    Collected
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-900">
                    RM {(dashboard?.financials?.total_collected || 0).toLocaleString()}
                  </div>
                  <p className="text-sm text-green-600">
                    {dashboard?.invoices?.paid || 0} invoices paid
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200 cursor-pointer hover:shadow-md transition-shadow active:scale-[0.98]" onClick={() => handleKpiCardClick('outstanding')} data-testid="fin-card-outstanding">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-orange-700 flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Outstanding
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-orange-900">
                    RM {(dashboard?.financials?.outstanding_receivables || 0).toLocaleString()}
                  </div>
                  <p className="text-sm text-orange-600">
                    {dashboard?.invoices?.issued || 0} pending
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200 cursor-pointer hover:shadow-md transition-shadow active:scale-[0.98]" onClick={() => handleKpiCardClick('payables')} data-testid="fin-card-payables">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-purple-700 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    Payables
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-purple-900">
                    RM {(dashboard?.payables?.pending_total || 0).toLocaleString()}
                  </div>
                  <p className="text-sm text-purple-600">
                    Staff payments pending
                  </p>
                </CardContent>
              </Card>
            </div>
            )}

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4 flex-wrap">
                  <Button onClick={() => setActiveTab('payments')} className="bg-green-600 hover:bg-green-700">
                    <CreditCard className="w-4 h-4 mr-2" />
                    Record Payment
                  </Button>
                  <Button variant="outline" onClick={() => setActiveTab('credit-notes')}>
                    <FileX className="w-4 h-4 mr-2" />
                    View Credit Notes
                  </Button>
                  <Button variant="outline" onClick={() => { loadInvoices(); loadDashboard(); }}>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Refresh Data
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Payables Tab - Pay staff fees with monthly grouping */}
          <TabsContent value="payables">
            <PayablesTab
              payables={payables}
              currentYear={currentYear}
              onRefresh={loadPayables}
            />
          </TabsContent>

          {/* Invoices Tab */}
          {/* Invoices Tab */}
          <TabsContent value="invoices">
            <InvoicesTab
              invoices={invoices}
              loading={loading}
              companySettings={companySettings}
              onRefresh={() => { loadInvoices(); loadDashboard(); }}
              onEditInvoice={handleEditInvoice}
              onRecordPayment={handleInvoiceSelect}
              setActiveTab={setActiveTab}
            />
          </TabsContent>

          {/* Payments Tab */}
          <TabsContent value="payments">
            <PaymentsTab
              invoices={invoices}
              payments={payments}
              companySettings={companySettings}
              onRefresh={() => { loadPayments(); loadInvoices(); loadDashboard(); }}
              selectedInvoiceId={paymentForm.invoice_id}
            />
          </TabsContent>

          {/* Credit Notes Tab */}
          <TabsContent value="credit-notes">
            <CreditNotesTab
              creditNotes={creditNotes}
              companySettings={companySettings}
              onRefresh={loadCreditNotes}
            />
          </TabsContent>

          {/* Profit & Loss Ledger Tab */}
          <TabsContent value="profit-loss">
            <ProfitLossLedger />
          </TabsContent>

          {/* Balance Sheet Tab */}
          <TabsContent value="balance-sheet">
            <BalanceSheetTab />
          </TabsContent>

          {/* Petty Cash Tab */}
          <TabsContent value="petty-cash">
            <PettyCash />
          </TabsContent>

          {/* HR & Payroll Tab */}
          <TabsContent value="hr">
            <HRModule />
          </TabsContent>

          {/* Audit Log Tab */}
          <TabsContent value="audit">
            <AuditLogTab />
          </TabsContent>

          {/* Company Settings Tab */}
          <TabsContent value="settings">
            <div className="space-y-6">
              <SettingsTab
                companySettings={companySettings}
                setCompanySettings={setCompanySettings}
                billingParties={billingParties}
                loadBillingParties={loadBillingParties}
                socialMediaLinks={socialMediaLinks}
                setSocialMediaLinks={setSocialMediaLinks}
              />
              <DigitalSignatureManager user={user} />
            </div>
          </TabsContent>

          {/* Accounting Tab */}
          <TabsContent value="accounting">
            <AccountingTab companySettings={companySettings} />
          </TabsContent>
        </Tabs>
      </main>

      {/* Edit Invoice Dialog */}
      <Dialog open={editingInvoice !== null} onOpenChange={(open) => !open && setEditingInvoice(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit className="w-5 h-5" />
              Edit Invoice: {editingInvoice?.invoice_number}
            </DialogTitle>
            <DialogDescription>
              Modify invoice details before approval/issuance
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            {/* Bill To Section */}
            <div className="p-4 bg-blue-50 rounded-lg space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="font-semibold text-blue-900">Bill To (M/S)</h3>
                {billingParties.length > 0 && (
                  <div className="flex items-center gap-2">
                    <Label className="text-xs text-blue-700 whitespace-nowrap">Quick Fill:</Label>
                    <Select onValueChange={applyBillingPartyToInvoice} data-testid="billing-party-select">
                      <SelectTrigger className="w-[200px] h-8 text-xs bg-white">
                        <SelectValue placeholder="Select billing party..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">-- Don't apply --</SelectItem>
                        {billingParties.map((party) => (
                          <SelectItem key={party.id} value={party.id}>{party.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Company/Organization Name</Label>
                  <Input
                    value={editForm.bill_to_name}
                    onChange={(e) => setEditForm({...editForm, bill_to_name: e.target.value})}
                    placeholder="e.g., HUMAN RESOURCES DEVELOPMENT CORPORATION"
                    data-testid="invoice-bill-to-name"
                  />
                </div>
                <div>
                  <Label>Co. Reg. No.</Label>
                  <Input
                    value={editForm.bill_to_reg_no}
                    onChange={(e) => setEditForm({...editForm, bill_to_reg_no: e.target.value})}
                    placeholder="Company registration number"
                    data-testid="invoice-bill-to-reg"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label>Address</Label>
                  <Input
                    value={editForm.bill_to_address}
                    onChange={(e) => setEditForm({...editForm, bill_to_address: e.target.value})}
                    placeholder="Full address"
                    data-testid="invoice-bill-to-address"
                  />
                </div>
                <div>
                  <Label>Your Reference</Label>
                  <Input
                    value={editForm.your_reference}
                    onChange={(e) => setEditForm({...editForm, your_reference: e.target.value})}
                    placeholder="Client's reference number"
                  />
                </div>
              </div>
            </div>

            {/* Training Details */}
            <div className="p-4 bg-green-50 rounded-lg space-y-4">
              <h3 className="font-semibold text-green-900">Training Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Program Name</Label>
                  <Input
                    value={editForm.programme_name}
                    onChange={(e) => setEditForm({...editForm, programme_name: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Training Dates</Label>
                  <Input
                    value={editForm.training_dates}
                    onChange={(e) => setEditForm({...editForm, training_dates: e.target.value})}
                    placeholder="e.g., 18th November 2025"
                  />
                </div>
                <div>
                  <Label>Venue</Label>
                  <Input
                    value={editForm.venue}
                    onChange={(e) => setEditForm({...editForm, venue: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Number of Participants</Label>
                  <Input
                    type="number"
                    value={editForm.pax}
                    onChange={(e) => setEditForm({...editForm, pax: parseInt(e.target.value) || 0})}
                  />
                </div>
              </div>
            </div>

            {/* Line Items */}
            <div className="p-4 bg-gray-50 rounded-lg space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="font-semibold text-gray-900">Line Items</h3>
                <Button type="button" variant="outline" size="sm" onClick={addLineItem}>
                  <Plus className="w-4 h-4 mr-1" /> Add Item
                </Button>
              </div>
              
              <div className="space-y-3">
                {editForm.line_items.map((item, idx) => (
                  <div key={idx} className="grid grid-cols-12 gap-2 items-end">
                    <div className="col-span-5">
                      {idx === 0 && <Label className="text-xs">Description</Label>}
                      <Input
                        value={item.description}
                        onChange={(e) => updateLineItem(idx, 'description', e.target.value)}
                        placeholder="Item description"
                      />
                    </div>
                    <div className="col-span-2">
                      {idx === 0 && <Label className="text-xs">Qty</Label>}
                      <Input
                        type="number"
                        value={item.quantity}
                        onChange={(e) => updateLineItem(idx, 'quantity', parseFloat(e.target.value) || 0)}
                      />
                    </div>
                    <div className="col-span-2">
                      {idx === 0 && <Label className="text-xs">Unit Price</Label>}
                      <Input
                        type="number"
                        value={item.unit_price}
                        onChange={(e) => updateLineItem(idx, 'unit_price', parseFloat(e.target.value) || 0)}
                      />
                    </div>
                    <div className="col-span-2">
                      {idx === 0 && <Label className="text-xs">Amount</Label>}
                      <Input
                        type="number"
                        value={item.amount}
                        disabled
                        className="bg-gray-100"
                      />
                    </div>
                    <div className="col-span-1">
                      {editForm.line_items.length > 1 && (
                        <Button 
                          type="button" 
                          variant="ghost" 
                          size="sm" 
                          className="text-red-600"
                          onClick={() => removeLineItem(idx)}
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Totals */}
            <div className="p-4 bg-purple-50 rounded-lg space-y-4">
              <h3 className="font-semibold text-purple-900">Totals</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <Label>Sub-Total (RM)</Label>
                  <Input
                    type="number"
                    value={editForm.subtotal}
                    disabled
                    className="bg-gray-100"
                  />
                </div>
                <div>
                  <Label>Mobilisation Fee (RM)</Label>
                  <Input
                    type="number"
                    value={editForm.mobilisation_fee}
                    onChange={(e) => recalculateTotals({mobilisation_fee: parseFloat(e.target.value) || 0})}
                  />
                </div>
                <div>
                  <Label>Rounding (RM)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={editForm.rounding}
                    onChange={(e) => recalculateTotals({rounding: parseFloat(e.target.value) || 0})}
                  />
                </div>
                <div>
                  <Label>Discount (RM)</Label>
                  <Input
                    type="number"
                    value={editForm.discount}
                    onChange={(e) => recalculateTotals({discount: parseFloat(e.target.value) || 0})}
                  />
                </div>
                <div>
                  <Label>Tax Rate (%)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={editForm.tax_rate}
                    onChange={(e) => recalculateTotals({tax_rate: parseFloat(e.target.value) || 0})}
                  />
                </div>
                <div>
                  <Label>Tax Amount (RM)</Label>
                  <Input
                    type="number"
                    value={editForm.tax_amount?.toFixed(2)}
                    disabled
                    className="bg-gray-100"
                  />
                </div>
                <div className="md:col-span-2">
                  <Label className="text-lg font-bold">Grand Total (RM)</Label>
                  <Input
                    type="number"
                    value={editForm.total_amount?.toFixed(2)}
                    disabled
                    className="bg-green-100 text-lg font-bold"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => setEditingInvoice(null)}>
              Cancel
            </Button>
            <Button onClick={handleSaveInvoice}>
              Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reopen Period Dialog */}
      <Dialog open={reopenDialog.open} onOpenChange={(open) => setReopenDialog({ ...reopenDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reopen Payables Period</DialogTitle>
            <DialogDescription>
              Enter a reason to reopen the period {payablesYear}-{String(payablesMonth).padStart(2, '0')}. This action will be logged.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="reopen-reason">Reason (required, minimum 5 characters)</Label>
            <textarea
              id="reopen-reason"
              className="w-full mt-2 p-3 border rounded-md min-h-[100px]"
              placeholder="Enter reason for reopening this period..."
              value={reopenDialog.reason}
              onChange={(e) => setReopenDialog({ ...reopenDialog, reason: e.target.value })}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setReopenDialog({ open: false, reason: '' })}>
              Cancel
            </Button>
            <Button onClick={confirmReopenPeriod} disabled={reopenDialog.reason.trim().length < 5}>
              Reopen Period
            </Button>
          </div>
        </DialogContent>
      </Dialog>
      <KpiDrilldownDialog open={drillOpen} onClose={() => setDrillOpen(false)} data={drillData} loading={drillLoading} />
    </div>
  );
};

export default FinanceDashboard;
