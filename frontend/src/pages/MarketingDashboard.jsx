import React, { useState, useEffect, useRef } from 'react';
import { axiosInstance } from '../App';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { 
  DollarSign, Calendar, TrendingUp, LogOut, RefreshCw, Wallet,
  Building, Clock, CheckCircle, FileText, Search, Eye, Download,
  Users, ChevronDown, ChevronRight, BarChart3, Plus, Edit, Trash2,
  Send, FileCheck, XCircle, Phone, Mail, MapPin, User, Printer, Target,
  CalendarDays, Briefcase
} from 'lucide-react';
import MyEarnings from '../components/MyEarnings';
import MyPayroll from '../components/MyPayroll';
import { downloadPdf } from '../utils/htmlToPdf';
import { DigitalSignatureManager } from "../components/shared/DigitalSignatureManager";
import { DashboardTab } from '../components/marketing/DashboardTab';
import { ClientsTab } from '../components/marketing/ClientsTab';
import { QuotationsTab } from '../components/marketing/QuotationsTab';
import { LeadPipelineTab } from '../components/marketing/LeadPipelineTab';
import { PipelineStatsCard } from '../components/marketing/PipelineStatsCard';
import AdminFeePayoutsPanel from '../components/admin/AdminFeePayoutsPanel';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const MarketingDashboard = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  
  // Stats
  const [stats, setStats] = useState({});
  
  // Clients
  const [clients, setClients] = useState([]);
  const [showClientDialog, setShowClientDialog] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [clientForm, setClientForm] = useState({
    company_name: '',
    company_address: '',
    contact_person: '',
    contact_phone: '',
    contact_email: '',
    notes: ''
  });
  
  // Quotations
  const [quotations, setQuotations] = useState([]);
  const [programmes, setProgrammes] = useState([]);
  const [defaultTerms, setDefaultTerms] = useState('');
  const [descriptionItems, setDescriptionItems] = useState([]);
  const [showQuotationDialog, setShowQuotationDialog] = useState(false);
  const [editingQuotation, setEditingQuotation] = useState(null);
  const [quotationForm, setQuotationForm] = useState({
    client_id: '',
    programme_id: '',
    programme_name: '',
    pricing_type: 'per_pax',
    num_participants: 1,
    rate_per_pax: 0,
    group_price: 0,
    sst_percent: 0,
    validity_days: 30,
    description_items: [],
    selected_items: [], // [{item_id: string, quantity: number, unit_price: number}]
    custom_description: '',
    remarks: '',
    terms_conditions: ''
  });
  
  // View quotation detail
  const [viewQuotation, setViewQuotation] = useState(null);
  const [showViewDialog, setShowViewDialog] = useState(false);
  
  // Company settings for PDF
  const [companySettings, setCompanySettings] = useState(null);
  
  // Search/filter
  const [clientSearch, setClientSearch] = useState('');
  const [quotationFilter, setQuotationFilter] = useState('all');
  
  // Accept quotation dialog (requires training date and venue)
  const [showAcceptDialog, setShowAcceptDialog] = useState(false);
  const [acceptingQuotation, setAcceptingQuotation] = useState(null);
  const [acceptForm, setAcceptForm] = useState({
    date_mode: 'single', // 'single' | 'range' | 'multiple'
    training_date: '',
    end_date: '',
    training_dates: [''], // for multiple non-consecutive dates
    venue: ''
  });
  
  // Discount dialog for negotiation
  const [showDiscountDialog, setShowDiscountDialog] = useState(false);
  const [discountingQuotation, setDiscountingQuotation] = useState(null);
  const [discountForm, setDiscountForm] = useState({
    discount_type: 'percentage',
    discount_value: 0,
    reason: ''
  });
  
  // PDF download loading state
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  
  // Lead Pipeline state
  const [leads, setLeads] = useState([]);
  const [pipelineStats, setPipelineStats] = useState({});
  const [reminders, setReminders] = useState({ overdue: [], upcoming: [], overdue_count: 0, upcoming_count: 0 });
  const [currentLeadId, setCurrentLeadId] = useState(null); // Track lead when creating quotation from lead
  
  // My Sessions state
  const [mySessions, setMySessions] = useState({ current: [], past: [] });
  const [sessionViewMode, setSessionViewMode] = useState('current'); // 'current' or 'past'

  useEffect(() => {
    loadData();
  }, []);

  // Poll quotations every 10 seconds for real-time status updates
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const [quotationsRes, statsRes] = await Promise.all([
          axiosInstance.get('/marketing/quotations'),
          axiosInstance.get('/marketing/stats').catch(() => null),
        ]);
        setQuotations(quotationsRes.data || []);
        if (statsRes?.data) setStats(statsRes.data);
      } catch (err) {
        // Silent fail - don't disrupt user with polling errors
      }
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, clientsRes, quotationsRes, programmesRes, termsRes, settingsRes, descItemsRes, leadsRes, pipelineStatsRes, remindersRes, mySessionsRes] = await Promise.all([
        axiosInstance.get('/marketing/stats'),
        axiosInstance.get('/marketing/clients'),
        axiosInstance.get('/marketing/quotations'),
        axiosInstance.get('/marketing/programmes'),
        axiosInstance.get('/marketing/default-terms'),
        axiosInstance.get('/finance/company-settings'),
        axiosInstance.get('/marketing/description-items'),
        axiosInstance.get('/marketing/leads').catch(() => ({ data: [] })),
        axiosInstance.get('/marketing/stats/pipeline').catch(() => ({ data: {} })),
        axiosInstance.get('/marketing/leads/reminders/pending').catch(() => ({ data: { overdue: [], upcoming: [], overdue_count: 0, upcoming_count: 0 } })),
        axiosInstance.get('/sessions/my-marketing-sessions').catch(() => ({ data: { current: [], past: [] } })),
      ]);
      
      setStats(statsRes.data || {});
      setClients(clientsRes.data || []);
      setQuotations(quotationsRes.data || []);
      setProgrammes(programmesRes.data || []);
      setDefaultTerms(termsRes.data?.terms || '');
      setCompanySettings(settingsRes.data);
      setDescriptionItems(descItemsRes.data || []);
      setLeads(leadsRes.data || []);
      setPipelineStats(pipelineStatsRes.data || {});
      setReminders(remindersRes.data || { overdue: [], upcoming: [], overdue_count: 0, upcoming_count: 0 });
      setMySessions(mySessionsRes.data || { current: [], past: [] });
    } catch (error) {
      console.error('Failed to load data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  // Client functions
  const handleSaveClient = async () => {
    try {
      if (!clientForm.company_name || !clientForm.contact_person || !clientForm.contact_phone || !clientForm.contact_email) {
        toast.error('Please fill in all required fields');
        return;
      }
      
      if (editingClient) {
        await axiosInstance.put(`/marketing/clients/${editingClient.id}`, clientForm);
        toast.success('Client updated successfully');
      } else {
        await axiosInstance.post('/marketing/clients', clientForm);
        toast.success('Client created successfully');
      }
      
      setShowClientDialog(false);
      setEditingClient(null);
      setClientForm({ company_name: '', company_address: '', contact_person: '', contact_phone: '', contact_email: '', notes: '' });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save client');
    }
  };

  const handleDeleteClient = async (clientId) => {
    if (!confirm('Are you sure you want to delete this client?')) return;
    try {
      await axiosInstance.delete(`/marketing/clients/${clientId}`);
      toast.success('Client deleted');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete client');
    }
  };

  const openEditClient = (client) => {
    setEditingClient(client);
    setClientForm({
      company_name: client.company_name || '',
      company_address: client.company_address || '',
      contact_person: client.contact_person || '',
      contact_phone: client.contact_phone || '',
      contact_email: client.contact_email || '',
      notes: client.notes || ''
    });
    setShowClientDialog(true);
  };

  // Quotation functions
  const handleSaveQuotation = async () => {
    try {
      // Validate based on pricing type
      if (!quotationForm.client_id || !quotationForm.programme_id) {
        toast.error('Please select client and programme');
        return;
      }
      
      if (quotationForm.pricing_type === 'per_pax' && !quotationForm.rate_per_pax) {
        toast.error('Please enter rate per pax');
        return;
      }
      
      if (quotationForm.pricing_type === 'per_group' && !quotationForm.group_price) {
        toast.error('Please enter group price');
        return;
      }
      
      // Calculate financial values before sending
      const trainingSubtotal = quotationForm.pricing_type === 'per_group' 
        ? Number(quotationForm.group_price) || 0
        : (Number(quotationForm.num_participants) || 0) * (Number(quotationForm.rate_per_pax) || 0);
      // Add priced items (vehicle rental, etc.)
      const pricedItemsTotal = (quotationForm.selected_items || []).reduce((sum, si) => {
        const item = descriptionItems.find(d => d.id === si.item_id);
        if (item?.has_pricing && si.unit_price > 0) {
          return sum + (si.unit_price * (si.quantity || 1));
        }
        return sum;
      }, 0);
      const subtotal = trainingSubtotal + pricedItemsTotal;
      const sst_amount = subtotal * (Number(quotationForm.sst_percent) || 0) / 100;
      const total_amount = subtotal + sst_amount;
      
      if (editingQuotation) {
        const updatePayload = {
          ...quotationForm,
          subtotal,
          sst_amount,
          sst_percentage: Number(quotationForm.sst_percent) || 0,
          total_amount
        };
        await axiosInstance.put(`/marketing/quotations/${editingQuotation.id}`, updatePayload);
        toast.success('Quotation updated successfully');
      } else {
        const payload = {
          ...quotationForm,
          subtotal,
          sst_amount,
          sst_percentage: Number(quotationForm.sst_percent) || 0,
          total_amount,
          terms_conditions: quotationForm.terms_conditions || defaultTerms,
          lead_id: currentLeadId || undefined
        };
        const response = await axiosInstance.post('/marketing/quotations', payload);
        toast.success('Quotation created successfully');
        
        // If this quotation was created from a lead, link it back
        if (currentLeadId && response.data?.quotation?.id) {
          try {
            await axiosInstance.put(`/marketing/leads/${currentLeadId}/link-quotation?quotation_id=${response.data.quotation.id}`);
          } catch (linkError) {
            console.warn('Failed to link quotation to lead:', linkError);
          }
        }
      }
      
      setShowQuotationDialog(false);
      setEditingQuotation(null);
      resetQuotationForm();
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save quotation');
    }
  };

  const resetQuotationForm = () => {
    setQuotationForm({
      client_id: '',
      programme_id: '',
      programme_name: '',
      pricing_type: 'per_pax',
      num_participants: 1,
      rate_per_pax: 0,
      group_price: 0,
      sst_percent: 0,
      validity_days: 30,
      description_items: [],
      selected_items: [],
      custom_description: '',
      remarks: '',
      terms_conditions: ''
    });
    setCurrentLeadId(null);
  };

  // Handle creating quotation from lead (auto-creates client)
  const handleCreateQuotationFromLead = (leadData) => {
    resetQuotationForm();
    setEditingQuotation(null);
    setCurrentLeadId(leadData.lead_id);
    
    // Pre-fill client_id from the auto-created client
    setQuotationForm(prev => ({
      ...prev,
      client_id: leadData.client_id
    }));
    
    // Switch to quotations tab and open dialog
    setActiveTab('quotations');
    setShowQuotationDialog(true);
    toast.success('Client created from lead. Now create your quotation.');
  };

  const openEditQuotation = (quotation) => {
    setEditingQuotation(quotation);
    setQuotationForm({
      client_id: quotation.client_id || '',
      programme_id: quotation.programme_id || '',
      programme_name: quotation.programme_name || '',
      pricing_type: quotation.pricing_type || 'per_pax',
      num_participants: quotation.num_participants || 1,
      rate_per_pax: quotation.rate_per_pax || 0,
      group_price: quotation.group_price || 0,
      sst_percent: quotation.sst_percent || 0,
      validity_days: quotation.validity_days || 30,
      description_items: quotation.description_items || [],
      selected_items: quotation.selected_items || [],
      custom_description: quotation.custom_description || '',
      remarks: quotation.remarks || '',
      terms_conditions: quotation.terms_conditions || ''
    });
    setShowQuotationDialog(true);
  };

  const handleSubmitForApproval = async (quotationId) => {
    try {
      await axiosInstance.post(`/marketing/quotations/${quotationId}/submit`);
      toast.success('Quotation submitted for approval');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit');
    }
  };

  const handleMarkSent = async (quotationId) => {
    try {
      await axiosInstance.post(`/marketing/quotations/${quotationId}/mark-sent`);
      toast.success('Quotation marked as sent');
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update');
    }
  };

  const handleClientResponse = async (quotationId, response) => {
    if (response === 'accepted') {
      // Open dialog to capture training date and venue
      const quotation = quotations.find(q => q.id === quotationId);
      setAcceptingQuotation(quotation);
      setAcceptForm({ date_mode: 'single', training_date: '', end_date: '', training_dates: [''], venue: '' });
      setShowAcceptDialog(true);
      return;
    }
    
    // For declined, send directly
    try {
      await axiosInstance.post(`/marketing/quotations/${quotationId}/client-response`, { response });
      toast.success(`Quotation marked as ${response}`);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update');
    }
  };

  const handleAcceptQuotation = async () => {
    const { date_mode, training_date, end_date, training_dates, venue } = acceptForm;
    if (!venue) {
      toast.error('Please enter venue');
      return;
    }
    // Validate dates based on mode
    let payloadDates = {};
    if (date_mode === 'single') {
      if (!training_date) { toast.error('Please enter training date'); return; }
      payloadDates = { training_date, end_date: training_date };
    } else if (date_mode === 'range') {
      if (!training_date || !end_date) { toast.error('Please enter start and end dates'); return; }
      if (end_date < training_date) { toast.error('End date must be on or after start date'); return; }
      payloadDates = { training_date, end_date };
    } else {
      const cleanDates = (training_dates || []).map(d => (d || '').trim()).filter(Boolean);
      const uniq = Array.from(new Set(cleanDates));
      if (uniq.length < 2) { toast.error('Please enter at least 2 separate training dates'); return; }
      uniq.sort();
      payloadDates = { training_date: uniq[0], end_date: uniq[uniq.length - 1], training_dates: uniq };
    }
    
    try {
      await axiosInstance.post(`/marketing/quotations/${acceptingQuotation.id}/client-response`, {
        response: 'accepted',
        ...payloadDates,
        venue
      });
      toast.success('Quotation marked as accepted');
      setShowAcceptDialog(false);
      setAcceptingQuotation(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update');
    }
  };

  const handleApplyDiscount = async () => {
    if (!discountForm.discount_value || discountForm.discount_value <= 0) {
      toast.error('Please enter a valid discount amount');
      return;
    }
    
    try {
      await axiosInstance.post(`/marketing/quotations/${discountingQuotation.id}/apply-discount`, discountForm);
      toast.success('Discount applied successfully');
      setShowDiscountDialog(false);
      setDiscountingQuotation(null);
      setDiscountForm({ discount_type: 'percentage', discount_value: 0, reason: '' });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to apply discount');
    }
  };

  const handleDownloadPdf = async (quotationId) => {
    setDownloadingPdf(true);
    try {
      const response = await axiosInstance.get(`/marketing/quotations/${quotationId}/download-pdf`, {
        responseType: 'blob',
        timeout: 60000
      });

      // Guard: if backend returned JSON error with blob responseType, parse it
      const ct = response.headers?.['content-type'] || '';
      if (!ct.includes('pdf')) {
        try {
          const txt = await response.data.text();
          const obj = JSON.parse(txt);
          throw new Error(obj.detail || 'Server did not return a PDF');
        } catch (_) {
          throw new Error('Server did not return a PDF');
        }
      }

      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);

      // Get filename from quotation
      const quotation = quotations.find(q => q.id === quotationId);
      const filename = quotation?.quotation_number?.replace(/\//g, '_') || 'quotation';
      const downloadName = `Quotation_${filename}.pdf`;

      // Detect iframed / mobile contexts where programmatic <a download> is blocked
      const inIframe = (() => { try { return window.self !== window.top; } catch (_) { return true; } })();
      const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

      if (isMobile || inIframe) {
        // Open in a new tab – user can then Save/Share from browser
        const win = window.open(url, '_blank');
        if (!win) {
          // Popup blocked – last-resort inline navigate
          window.location.href = url;
        }
        toast.success('PDF opened in a new tab. Use the browser menu to save it.');
      } else {
        const link = document.createElement('a');
        link.href = url;
        link.download = downloadName;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        toast.success('PDF downloaded successfully');
      }

      // Cleanup after a delay to allow the new tab to load the blob
      setTimeout(() => window.URL.revokeObjectURL(url), 30000);
    } catch (error) {
      console.error('PDF download error:', error);
      // Try to extract JSON error if the response was a blob
      let msg = error.response?.data?.detail || error.message || 'Failed to download PDF';
      if (error.response?.data && typeof error.response.data.text === 'function') {
        try {
          const txt = await error.response.data.text();
          const obj = JSON.parse(txt);
          msg = obj.detail || msg;
        } catch (_) { /* ignore */ }
      }
      toast.error(msg);
    } finally {
      setDownloadingPdf(false);
    }
  };

  const viewQuotationDetails = async (quotationId) => {
    try {
      const res = await axiosInstance.get(`/marketing/quotations/${quotationId}`);
      setViewQuotation(res.data);
      setShowViewDialog(true);
    } catch (error) {
      toast.error('Failed to load quotation details');
    }
  };

  // PDF Generation
  const buildQuotationHtml = (quotation) => {
    const client = quotation.client || {};
    const marketerSig = quotation.marketer?.digital_signature || '';
    const approverSig = quotation.approver?.digital_signature || '';

    return `
<!DOCTYPE html>
<html>
<head>
  <title>Quotation ${quotation.quotation_number}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: Arial, sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #1e40af; padding-bottom: 20px; margin-bottom: 20px; }
    .logo-section { flex: 1; }
    .logo { max-height: 80px; }
    .company-info { text-align: right; font-size: 12px; color: #666; }
    .company-name { font-size: 16px; font-weight: bold; color: #1e40af; margin-bottom: 5px; }
    .title { text-align: center; font-size: 24px; font-weight: bold; color: #1e40af; margin: 20px 0; }
    .meta { display: flex; justify-content: space-between; margin-bottom: 20px; }
    .meta-box { background: #f8f9fa; padding: 15px; border-radius: 5px; width: 48%; }
    .meta-box h3 { font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 10px; }
    .meta-box p { margin: 3px 0; font-size: 13px; }
    .client-box { background: #e8f4fd; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
    th { background: #1e40af; color: white; }
    .amount-row td { font-weight: bold; }
    .total-row { background: #f8f9fa; }
    .total-row td { font-size: 16px; }
    .terms { margin-top: 30px; font-size: 12px; }
    .terms h3 { font-size: 14px; margin-bottom: 10px; }
    .terms ol { padding-left: 20px; }
    .terms li { margin: 5px 0; }
    .footer { margin-top: 40px; display: flex; justify-content: space-between; }
    .signature-box { width: 45%; }
    .signature-box p { margin-top: 50px; border-top: 1px solid #333; padding-top: 5px; font-size: 12px; }
    .validity { background: #fff3cd; padding: 10px; border-radius: 5px; text-align: center; margin: 20px 0; }
    @media print { body { padding: 0; } }
  </style>
</head>
<body>
  <div class="header">
    <div class="logo-section">
      ${companySettings?.logo_url ? `<img src="${companySettings.logo_url.startsWith('/') ? API_URL + companySettings.logo_url : companySettings.logo_url}" class="logo" />` : ''}
      <div class="company-name">${companySettings?.company_name || 'Malaysian Defensive Driving and Riding Centre Sdn Bhd'}</div>
    </div>
    <div class="company-info">
      <p>${companySettings?.address || ''}</p>
      <p>Reg No: ${companySettings?.registration_number || ''}</p>
      <p>Tel: ${companySettings?.phone || ''}</p>
      <p>Email: ${companySettings?.email || ''}</p>
    </div>
  </div>
  
  <div class="title">QUOTATION</div>
  
  <div class="meta">
    <div class="meta-box">
      <h3>Quotation Details</h3>
      <p><strong>No:</strong> ${quotation.quotation_number}</p>
      <p><strong>Date:</strong> ${new Date(quotation.created_at).toLocaleDateString('en-MY', { day: 'numeric', month: 'long', year: 'numeric' })}</p>
      <p><strong>Valid Until:</strong> ${new Date(quotation.valid_until).toLocaleDateString('en-MY', { day: 'numeric', month: 'long', year: 'numeric' })}</p>
    </div>
    <div class="meta-box client-box">
      <h3>To</h3>
      <p><strong>${client.company_name || ''}</strong></p>
      <p>${client.company_address || ''}</p>
      <p>Attn: ${client.contact_person || ''}</p>
      <p>Tel: ${client.contact_phone || ''}</p>
      <p>Email: ${client.contact_email || ''}</p>
    </div>
  </div>
  
  <table>
    <thead>
      <tr>
        <th>Description</th>
        <th style="width: 100px; text-align: center;">Qty (pax)</th>
        <th style="width: 120px; text-align: right;">Rate (RM)</th>
        <th style="width: 120px; text-align: right;">Amount (RM)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>${quotation.programme_name || ''}</td>
        <td style="text-align: center;">${quotation.pricing_type === 'per_group' ? '1 group' : quotation.num_participants}</td>
        <td style="text-align: right;">${quotation.pricing_type === 'per_group' ? (quotation.group_price || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 }) : quotation.rate_per_pax?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
        <td style="text-align: right;">${(() => {
          const fee = quotation.pricing_type === 'per_group' 
            ? (quotation.group_price || 0) 
            : (quotation.rate_per_pax || 0) * (quotation.num_participants || 0);
          return fee.toLocaleString('en-MY', { minimumFractionDigits: 2 });
        })()}</td>
      </tr>
      ${(quotation.selected_items || []).filter(si => si.unit_price > 0).map(si => {
        const item = descriptionItems.find(d => d.id === si.item_id);
        return `<tr>
          <td>${item?.name || 'Add-on Item'}</td>
          <td style="text-align: center;">${si.quantity || 1}</td>
          <td style="text-align: right;">${(si.unit_price || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
          <td style="text-align: right;">${((si.unit_price || 0) * (si.quantity || 1)).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
        </tr>`;
      }).join('')}
      ${quotation.remarks ? `<tr><td colspan="4" style="font-size: 12px; color: #666;"><em>Remarks: ${quotation.remarks}</em></td></tr>` : ''}
      ${(() => {
        const trainingFee = quotation.pricing_type === 'per_group'
          ? (quotation.group_price || 0)
          : (quotation.rate_per_pax || 0) * (quotation.num_participants || 0);
        const addonTotal = (quotation.selected_items || []).filter(si => si.unit_price > 0).reduce((s, si) => s + ((si.unit_price || 0) * (si.quantity || 1)), 0);
        const sub = trainingFee + addonTotal;
        const sst = sub * (quotation.sst_percent || 0) / 100;
        const discount = quotation.discount_amount || 0;
        const total = sub + sst - discount;
        return `
      <tr class="amount-row">
        <td colspan="3" style="text-align: right;">Subtotal</td>
        <td style="text-align: right;">RM ${sub.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
      </tr>
      ${quotation.sst_percent > 0 ? `
      <tr class="amount-row">
        <td colspan="3" style="text-align: right;">SST (${quotation.sst_percent}%)</td>
        <td style="text-align: right;">RM ${sst.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
      </tr>` : ''}
      ${discount > 0 ? `
      <tr class="amount-row">
        <td colspan="3" style="text-align: right;">Discount</td>
        <td style="text-align: right; color: #e65100;">-RM ${discount.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
      </tr>` : ''}
      <tr class="amount-row total-row">
        <td colspan="3" style="text-align: right;">TOTAL</td>
        <td style="text-align: right;">RM ${total.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
      </tr>`;
      })()}
    </tbody>
  </table>
  
  <div class="validity">
    <strong>This quotation is valid until ${new Date(quotation.valid_until).toLocaleDateString('en-MY', { day: 'numeric', month: 'long', year: 'numeric' })}</strong>
  </div>
  
  <div class="terms">
    <h3>Terms & Conditions:</h3>
    <ol>
      ${(quotation.terms_conditions || '').split('\n').filter(t => t.trim()).map(t => `<li>${t.replace(/^\d+\.\s*/, '')}</li>`).join('')}
    </ol>
  </div>
  
  <div class="footer">
    <div class="signature-box">
      ${marketerSig ? `<img src="${marketerSig}" style="max-height:50px;max-width:150px;margin-bottom:4px;" /><br>` : ''}
      <p>Prepared by: ${quotation.marketer?.full_name || quotation.marketer_name || ''}</p>
    </div>
    <div class="signature-box">
      ${approverSig ? `<img src="${approverSig}" style="max-height:50px;max-width:150px;margin-bottom:4px;" /><br>` : ''}
      <p>Approved by: ${quotation.approver?.full_name || ''}</p>
    </div>
  </div>
</body>
</html>
    `;
  };

  const generatePDF = (quotation) => {
    const html = buildQuotationHtml(quotation);
    downloadPdf(html, `Quotation_${quotation.quotation_number?.replace(/\//g, '_') || 'draft'}`);
  };

  // Word (DOCX) Generation — reuses the same HTML as the PDF for consistent layout
  const generateWord = async (quotation) => {
    try {
      const { asBlob } = await import('html-docx-js-typescript');
      const html = buildQuotationHtml(quotation);
      const blob = await asBlob(html);
      const url = URL.createObjectURL(blob);
      const filename = `Quotation_${quotation.quotation_number?.replace(/\//g, '_') || 'draft'}.docx`;
      const inIframe = (() => { try { return window.self !== window.top; } catch (_) { return true; } })();
      if (inIframe || /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
        const w = window.open(url, '_blank');
        if (!w) window.location.href = url;
        toast.success('Word document opened. Use the browser menu to save it.');
      } else {
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        toast.success('Word document downloaded');
      }
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (err) {
      console.error(err);
      toast.error('Failed to generate Word document');
    }
  };

  // Filter quotations
  const filteredQuotations = quotations.filter(q => {
    if (quotationFilter === 'all') return true;
    return q.status === quotationFilter;
  });

  // Filter clients
  const filteredClients = clients.filter(c => {
    if (!clientSearch) return true;
    const search = clientSearch.toLowerCase();
    return c.company_name?.toLowerCase().includes(search) ||
           c.contact_person?.toLowerCase().includes(search);
  });

  // Status badge colors
  const getStatusBadge = (status) => {
    const colors = {
      draft: 'bg-gray-500',
      pending_approval: 'bg-yellow-500',
      approved: 'bg-green-500',
      rejected: 'bg-red-500',
      sent: 'bg-blue-500',
      accepted: 'bg-emerald-600',
      declined: 'bg-red-600'
    };
    const labels = {
      draft: 'Draft',
      pending_approval: 'Pending Approval',
      approved: 'Approved',
      rejected: 'Rejected',
      sent: 'Sent',
      accepted: 'Accepted',
      declined: 'Declined'
    };
    return <Badge className={`${colors[status] || 'bg-gray-500'} text-white`}>{labels[status] || status}</Badge>;
  };

  const formatCurrency = (amount) => `RM ${(amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 sm:py-4">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Marketing Portal</h1>
              <p className="text-xs sm:text-sm text-gray-600">Welcome, {user.full_name}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {/* Calendar button for all staff */}
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => window.location.href = '/calendar'}
                className="bg-indigo-50 border-indigo-300 text-indigo-700 hover:bg-indigo-100 text-xs sm:text-sm"
              >
                <CalendarDays className="w-3 h-3 sm:w-4 sm:h-4 mr-1" /> 
                <span className="hidden sm:inline">Calendar</span>
              </Button>
              {/* Back button for coordinators/trainers */}
              {(user.role === 'coordinator' || user.role === 'trainer' || user.role === 'supervisor') && (
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => window.location.href = `/${user.role}`}
                  className="bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100 text-xs sm:text-sm"
                >
                  <Users className="w-3 h-3 sm:w-4 sm:h-4 mr-1" /> 
                  <span className="hidden sm:inline">Back to </span>{user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                </Button>
              )}
              {user.role === 'admin' && (
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => window.location.href = '/admin'}
                  className="bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100 text-xs sm:text-sm"
                >
                  <Users className="w-3 h-3 sm:w-4 sm:h-4 mr-1" /> <span className="hidden sm:inline">Back to </span>Admin
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={loadData} className="text-xs sm:text-sm">
                <RefreshCw className="w-3 h-3 sm:w-4 sm:h-4 mr-1" /> <span className="hidden sm:inline">Refresh</span>
              </Button>
              <Button variant="outline" size="sm" onClick={onLogout} className="text-xs sm:text-sm">
                <LogOut className="w-3 h-3 sm:w-4 sm:h-4 mr-1" /> <span className="hidden sm:inline">Logout</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-4 sm:mb-6 flex gap-1 overflow-x-auto scrollbar-hide">
            <TabsTrigger value="dashboard" data-testid="dashboard-tab" className="text-xs sm:text-sm px-2 sm:px-3">
              <BarChart3 className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> <span className="hidden sm:inline">Dashboard</span><span className="sm:hidden">Home</span>
            </TabsTrigger>
            <TabsTrigger value="leads" data-testid="leads-tab" className="text-xs sm:text-sm px-2 sm:px-3">
              <Target className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> Leads
              {reminders.overdue_count > 0 && (
                <Badge variant="destructive" className="ml-1 text-xs px-1">{reminders.overdue_count}</Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="clients" data-testid="clients-tab" className="text-xs sm:text-sm px-2 sm:px-3">
              <Building className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> Clients
            </TabsTrigger>
            <TabsTrigger value="quotations" data-testid="quotations-tab" className="text-xs sm:text-sm px-2 sm:px-3">
              <FileText className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> Quotations
            </TabsTrigger>
            <TabsTrigger value="earnings" data-testid="earnings-tab" className="text-xs sm:text-sm px-2 sm:px-3">
              <Wallet className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> Earnings
            </TabsTrigger>
            <TabsTrigger value="my-payroll" data-testid="my-payroll-tab" className="text-xs sm:text-sm px-2 sm:px-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white">
              <DollarSign className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> Payroll
            </TabsTrigger>
            <TabsTrigger value="sessions" data-testid="sessions-tab" className="text-xs sm:text-sm px-2 sm:px-3">
              <Briefcase className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> My Sessions
              {mySessions.current.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs px-1">{mySessions.current.length}</Badge>
              )}
            </TabsTrigger>
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard">
            {loading ? (
              <div className="space-y-6" data-testid="marketing-loading">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[1,2,3,4].map(i => <div key={i} className="border rounded-lg p-4 space-y-2"><div className="h-4 w-20 bg-gray-200 animate-pulse rounded" /><div className="h-8 w-16 bg-gray-200 animate-pulse rounded" /></div>)}
                </div>
                <div className="space-y-3">
                  {[1,2,3].map(i => <div key={i} className="h-20 bg-gray-200 animate-pulse rounded-lg" />)}
                </div>
              </div>
            ) : (
            <>
            {/* Pipeline Stats Summary */}
            <div className="mb-6">
              <PipelineStatsCard
                stats={pipelineStats}
                reminders={reminders}
                formatCurrency={formatCurrency}
                onViewReminders={() => setActiveTab('leads')}
              />
            </div>
            <DashboardTab
              stats={stats}
              quotations={quotations}
              formatCurrency={formatCurrency}
              getStatusBadge={getStatusBadge}
              onNewQuotation={() => { resetQuotationForm(); setEditingQuotation(null); setShowQuotationDialog(true); }}
              onAddClient={() => { setEditingClient(null); setClientForm({ company_name: '', company_address: '', contact_person: '', contact_phone: '', contact_email: '', notes: '' }); setShowClientDialog(true); }}
              onViewQuotation={viewQuotationDetails}
            />
            </>
            )}
          </TabsContent>

          {/* Leads Tab */}
          <TabsContent value="leads">
            <LeadPipelineTab
              leads={leads}
              onRefresh={loadData}
              formatCurrency={formatCurrency}
              isAdmin={user?.role === 'admin' || user?.role === 'super_admin'}
              onCreateQuotation={handleCreateQuotationFromLead}
              quotations={quotations}
              onViewQuotation={viewQuotationDetails}
              onApplyDiscount={(q) => { setDiscountingQuotation(q); setShowDiscountDialog(true); }}
              onDownloadPdf={handleDownloadPdf}
              onClientResponse={handleClientResponse}
              onMarkSent={handleMarkSent}
              getStatusBadge={getStatusBadge}
            />
          </TabsContent>

          {/* Clients Tab */}
          <TabsContent value="clients">
            <ClientsTab
              clients={clients}
              clientSearch={clientSearch}
              setClientSearch={setClientSearch}
              onAddClient={() => { setEditingClient(null); setClientForm({ company_name: '', company_address: '', contact_person: '', contact_phone: '', contact_email: '', notes: '' }); setShowClientDialog(true); }}
              onEditClient={openEditClient}
              onDeleteClient={handleDeleteClient}
            />
          </TabsContent>

          {/* Quotations Tab */}
          <TabsContent value="quotations">
            <QuotationsTab
              quotations={quotations}
              quotationFilter={quotationFilter}
              setQuotationFilter={setQuotationFilter}
              formatCurrency={formatCurrency}
              getStatusBadge={getStatusBadge}
              onNewQuotation={() => { resetQuotationForm(); setEditingQuotation(null); setShowQuotationDialog(true); }}
              onViewQuotation={viewQuotationDetails}
              onEditQuotation={openEditQuotation}
              onSubmitForApproval={handleSubmitForApproval}
              onDownloadPdf={handleDownloadPdf}
              onMarkSent={handleMarkSent}
              onClientResponse={handleClientResponse}
              onApplyDiscount={(q) => { setDiscountingQuotation(q); setShowDiscountDialog(true); }}
              downloadingPdf={downloadingPdf}
            />
          </TabsContent>

          {/* Earnings Tab */}
          <TabsContent value="earnings">
            <div className="space-y-6">
              <AdminFeePayoutsPanel />
              <MyEarnings user={user} />
            </div>
          </TabsContent>

          {/* My Payroll Tab */}
          <TabsContent value="my-payroll">
            <div className="space-y-6">
              <MyPayroll />
              <DigitalSignatureManager user={user} />
            </div>
          </TabsContent>

          {/* My Sessions Tab */}
          <TabsContent value="sessions" data-testid="my-sessions-content">
            <Card>
              <CardHeader>
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
                  <div>
                    <CardTitle className="text-lg">My Sessions</CardTitle>
                    <CardDescription>Training sessions from your deals</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant={sessionViewMode === 'current' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setSessionViewMode('current')}
                      data-testid="current-sessions-btn"
                    >
                      <Clock className="w-4 h-4 mr-1" /> Current ({mySessions.current.length})
                    </Button>
                    <Button
                      variant={sessionViewMode === 'past' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setSessionViewMode('past')}
                      data-testid="past-sessions-btn"
                    >
                      <CheckCircle className="w-4 h-4 mr-1" /> Past ({mySessions.past.length})
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {(() => {
                  const sessionList = sessionViewMode === 'current' ? mySessions.current : mySessions.past;
                  if (sessionList.length === 0) {
                    return (
                      <div className="text-center py-12 text-gray-500">
                        <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        <p className="font-medium">No {sessionViewMode} sessions</p>
                        <p className="text-sm mt-1">
                          {sessionViewMode === 'current'
                            ? 'Sessions will appear here when your quotations are accepted'
                            : 'Completed sessions from your deals will appear here'}
                        </p>
                      </div>
                    );
                  }
                  return (
                    <div className="space-y-3">
                      {sessionList.map(session => (
                        <div
                          key={session.id}
                          data-testid={`session-card-${session.id}`}
                          className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                        >
                          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2">
                            <div className="flex-1 min-w-0">
                              <h4 className="font-semibold text-gray-900 truncate">
                                {session.company_name || session.name || 'Unnamed Session'}
                              </h4>
                              <p className="text-sm text-gray-600 mt-0.5">
                                {session.program_name || 'Programme not set'}
                              </p>
                              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-gray-500">
                                <span className="flex items-center gap-1">
                                  <Calendar className="w-3 h-3" />
                                  {session.training_dates && session.training_dates.length > 1
                                    ? session.training_dates.join(', ')
                                    : (
                                      <>
                                        {session.start_date || 'Date TBD'}
                                        {session.end_date && session.end_date !== session.start_date && ` — ${session.end_date}`}
                                      </>
                                    )
                                  }
                                </span>
                                <span className="flex items-center gap-1">
                                  <MapPin className="w-3 h-3" />
                                  {session.location || 'Venue TBD'}
                                </span>
                                <span className="flex items-center gap-1">
                                  <Users className="w-3 h-3" />
                                  {session.participant_count || 0} pax
                                </span>
                              </div>
                              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 text-xs text-gray-500">
                                {session.coordinator_name && (
                                  <span className="flex items-center gap-1">
                                    <User className="w-3 h-3" />
                                    Coordinator: {session.coordinator_name}
                                  </span>
                                )}
                                {session.trainer_names?.length > 0 && (
                                  <span className="flex items-center gap-1">
                                    <User className="w-3 h-3" />
                                    Trainer: {session.trainer_names.join(', ')}
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex flex-col items-end gap-1">
                              <Badge
                                variant="secondary"
                                className={
                                  session.completion_status === 'completed' ? 'bg-green-100 text-green-800' :
                                  session.status === 'draft' ? 'bg-gray-100 text-gray-700' :
                                  'bg-blue-100 text-blue-800'
                                }
                              >
                                {session.completion_status === 'completed' ? 'Completed' :
                                 session.status === 'draft' ? 'Draft' : 'Ongoing'}
                              </Badge>
                              {session.invoice_status && (
                                <Badge variant="outline" className="text-xs">
                                  Invoice: {session.invoice_status}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Client Dialog */}
      <Dialog open={showClientDialog} onOpenChange={setShowClientDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingClient ? 'Edit Client' : 'Add New Client'}</DialogTitle>
            <DialogDescription>Enter client details</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Company Name *</Label>
              <Input value={clientForm.company_name} onChange={e => setClientForm({...clientForm, company_name: e.target.value})} />
            </div>
            <div>
              <Label>Company Address *</Label>
              <Textarea value={clientForm.company_address} onChange={e => setClientForm({...clientForm, company_address: e.target.value})} rows={2} />
            </div>
            <div>
              <Label>Contact Person *</Label>
              <Input value={clientForm.contact_person} onChange={e => setClientForm({...clientForm, contact_person: e.target.value})} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Phone *</Label>
                <Input value={clientForm.contact_phone} onChange={e => setClientForm({...clientForm, contact_phone: e.target.value})} />
              </div>
              <div>
                <Label>Email *</Label>
                <Input type="email" value={clientForm.contact_email} onChange={e => setClientForm({...clientForm, contact_email: e.target.value})} />
              </div>
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea value={clientForm.notes} onChange={e => setClientForm({...clientForm, notes: e.target.value})} rows={2} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowClientDialog(false)}>Cancel</Button>
            <Button onClick={handleSaveClient}>{editingClient ? 'Update' : 'Create'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Quotation Dialog */}
      <Dialog open={showQuotationDialog} onOpenChange={setShowQuotationDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{editingQuotation ? 'Edit Quotation' : 'Create New Quotation'}</DialogTitle>
            <DialogDescription>Enter quotation details</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 max-h-[65vh] overflow-y-auto pr-2">
            {/* Client & Programme */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Client *</Label>
                <Select value={quotationForm.client_id} onValueChange={v => setQuotationForm({...quotationForm, client_id: v})}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select client" />
                  </SelectTrigger>
                  <SelectContent>
                    <div className="p-2 border-b">
                      <Input 
                        placeholder="Search clients..." 
                        className="h-8"
                        onChange={(e) => {
                          const searchVal = e.target.value.toLowerCase();
                          // Filter is handled by showing/hiding items
                          document.querySelectorAll('[data-client-item]').forEach(item => {
                            const name = item.getAttribute('data-client-name')?.toLowerCase() || '';
                            item.style.display = name.includes(searchVal) ? '' : 'none';
                          });
                        }}
                      />
                    </div>
                    {clients.map(c => (
                      <SelectItem 
                        key={c.id} 
                        value={c.id}
                        data-client-item
                        data-client-name={c.company_name}
                      >
                        {c.company_name}
                        {c.contact_person && <span className="text-xs text-gray-500 ml-2">({c.contact_person})</span>}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {clients.length === 0 && <p className="text-xs text-red-500 mt-1">Please add a client first or create from Leads</p>}
              </div>
              <div>
                <Label>Programme *</Label>
                <Select value={quotationForm.programme_id} onValueChange={v => {
                  const selectedProgramme = programmes.find(p => p.id === v);
                  setQuotationForm({
                    ...quotationForm, 
                    programme_id: v,
                    programme_name: selectedProgramme?.name || ''
                  });
                }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select programme" />
                  </SelectTrigger>
                  <SelectContent>
                    {programmes.map(p => (
                      <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Pricing Type Selection */}
            <div className="bg-blue-50 p-3 rounded-lg">
              <Label className="text-blue-900 font-semibold">Pricing Type *</Label>
              <div className="flex gap-4 mt-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="pricing_type"
                    value="per_pax"
                    checked={quotationForm.pricing_type === 'per_pax'}
                    onChange={() => setQuotationForm({...quotationForm, pricing_type: 'per_pax'})}
                    className="w-4 h-4"
                  />
                  <span>Per Pax (Rate × Participants)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="pricing_type"
                    value="per_group"
                    checked={quotationForm.pricing_type === 'per_group'}
                    onChange={() => setQuotationForm({...quotationForm, pricing_type: 'per_group'})}
                    className="w-4 h-4"
                  />
                  <span>Per Group (Fixed Price)</span>
                </label>
              </div>
            </div>

            {/* Pricing Fields based on type */}
            {quotationForm.pricing_type === 'per_pax' ? (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>No. of Participants</Label>
                  <Input type="number" min="1" value={quotationForm.num_participants} onFocus={e => e.target.select()} onChange={e => setQuotationForm({...quotationForm, num_participants: parseInt(e.target.value) || 1})} />
                </div>
                <div>
                  <Label>Rate per Pax (RM) *</Label>
                  <Input type="number" min="0" step="0.01" value={quotationForm.rate_per_pax} onFocus={e => e.target.select()} onChange={e => setQuotationForm({...quotationForm, rate_per_pax: parseFloat(e.target.value) || 0})} />
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Max Participants (for reference)</Label>
                  <Input type="number" min="1" value={quotationForm.num_participants} onFocus={e => e.target.select()} onChange={e => setQuotationForm({...quotationForm, num_participants: parseInt(e.target.value) || 1})} />
                </div>
                <div>
                  <Label>Group Price (RM) *</Label>
                  <Input type="number" min="0" step="0.01" value={quotationForm.group_price} onFocus={e => e.target.select()} onChange={e => setQuotationForm({...quotationForm, group_price: parseFloat(e.target.value) || 0})} />
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>SST (%)</Label>
                <Input type="number" min="0" max="100" value={quotationForm.sst_percent} onFocus={e => e.target.select()} onChange={e => setQuotationForm({...quotationForm, sst_percent: parseFloat(e.target.value) || 0})} />
              </div>
              <div>
                <Label>Validity (Days)</Label>
                <Input type="number" min="1" value={quotationForm.validity_days} onFocus={e => e.target.select()} onChange={e => setQuotationForm({...quotationForm, validity_days: parseInt(e.target.value) || 30})} />
              </div>
            </div>
            
            {/* Calculated amounts */}
            <div className="bg-gray-50 p-3 rounded-lg">
              {(() => {
                const trainingSubtotal = quotationForm.pricing_type === 'per_group' 
                  ? quotationForm.group_price 
                  : quotationForm.num_participants * quotationForm.rate_per_pax;
                const pricedItemsTotal = (quotationForm.selected_items || []).reduce((sum, si) => {
                  const item = descriptionItems.find(d => d.id === si.item_id);
                  if (item?.has_pricing && si.unit_price > 0) {
                    return sum + (si.unit_price * (si.quantity || 1));
                  }
                  return sum;
                }, 0);
                const subtotal = trainingSubtotal + pricedItemsTotal;
                const sst = subtotal * quotationForm.sst_percent / 100;
                const total = subtotal + sst;
                return (
                  <>
                    <div className="flex justify-between text-sm">
                      <span>Training Fee:</span>
                      <span>{formatCurrency(trainingSubtotal)}</span>
                    </div>
                    {pricedItemsTotal > 0 && (
                      <div className="flex justify-between text-sm text-blue-700">
                        <span>Add-on Items:</span>
                        <span>{formatCurrency(pricedItemsTotal)}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-sm font-medium border-t mt-1 pt-1">
                      <span>Subtotal:</span>
                      <span>{formatCurrency(subtotal)}</span>
                    </div>
                    {quotationForm.sst_percent > 0 && (
                      <div className="flex justify-between text-sm">
                        <span>SST ({quotationForm.sst_percent}%):</span>
                        <span>{formatCurrency(sst)}</span>
                      </div>
                    )}
                    <div className="flex justify-between font-bold border-t mt-2 pt-2">
                      <span>Total:</span>
                      <span>{formatCurrency(total)}</span>
                    </div>
                  </>
                );
              })()}
            </div>

            {/* Inclusions & Exclusions Selection */}
            {descriptionItems.length > 0 && (
              <div className="border rounded-lg p-3 space-y-4">
                <Label className="font-semibold">Inclusions & Exclusions</Label>
                
                {/* Inclusions - handle both singular and plural category names */}
                {descriptionItems.filter(i => i.category === 'inclusion' || i.category === 'inclusions').length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-green-700 mb-2">✓ Inclusions</p>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {descriptionItems.filter(i => i.category === 'inclusion' || i.category === 'inclusions').map(item => {
                        const selectedItem = quotationForm.selected_items.find(s => s.item_id === item.id);
                        const isSelected = !!selectedItem;
                        return (
                          <div key={item.id} className="flex flex-wrap items-center gap-2 p-2 hover:bg-gray-50 rounded">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setQuotationForm({
                                    ...quotationForm, 
                                    selected_items: [...quotationForm.selected_items, { 
                                      item_id: item.id, 
                                      quantity: 1, 
                                      unit_price: item.default_unit_price || 0 
                                    }]
                                  });
                                } else {
                                  setQuotationForm({
                                    ...quotationForm, 
                                    selected_items: quotationForm.selected_items.filter(s => s.item_id !== item.id)
                                  });
                                }
                              }}
                              className="w-4 h-4"
                            />
                            <span className="flex-1 text-sm">{item.name}</span>
                            {item.has_quantity && isSelected && (
                              <div className="flex items-center gap-1">
                                <span className="text-xs text-gray-500">Qty:</span>
                                <input
                                  type="number"
                                  min="1"
                                  value={selectedItem?.quantity || 1}
                                  onChange={(e) => {
                                    const qty = parseInt(e.target.value) || 1;
                                    setQuotationForm({
                                      ...quotationForm,
                                      selected_items: quotationForm.selected_items.map(s => 
                                        s.item_id === item.id ? { ...s, quantity: qty } : s
                                      )
                                    });
                                  }}
                                  className="w-16 text-sm border rounded px-2 py-1"
                                />
                              </div>
                            )}
                            {item.has_pricing && isSelected && (
                              <div className="flex items-center gap-1">
                                <span className="text-xs text-gray-500">RM/unit:</span>
                                <input
                                  type="number"
                                  min="0"
                                  step="0.01"
                                  value={selectedItem?.unit_price || 0}
                                  onFocus={e => e.target.select()}
                                  onChange={(e) => {
                                    const price = parseFloat(e.target.value) || 0;
                                    setQuotationForm({
                                      ...quotationForm,
                                      selected_items: quotationForm.selected_items.map(s => 
                                        s.item_id === item.id ? { ...s, unit_price: price } : s
                                      )
                                    });
                                  }}
                                  className="w-24 text-sm border rounded px-2 py-1"
                                  data-testid={`item-price-${item.id}`}
                                />
                                {selectedItem?.unit_price > 0 && selectedItem?.quantity > 0 && (
                                  <span className="text-xs font-medium text-blue-700 ml-1">
                                    = RM {((selectedItem.unit_price || 0) * (selectedItem.quantity || 1)).toLocaleString('en-MY', {minimumFractionDigits: 2})}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                
                {/* Exclusions - handle both singular and plural category names */}
                {descriptionItems.filter(i => i.category === 'exclusion' || i.category === 'exclusions').length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-red-700 mb-2">✗ Exclusions</p>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {descriptionItems.filter(i => i.category === 'exclusion' || i.category === 'exclusions').map(item => {
                        const selectedItem = quotationForm.selected_items.find(s => s.item_id === item.id);
                        const isSelected = !!selectedItem;
                        return (
                          <div key={item.id} className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setQuotationForm({
                                    ...quotationForm, 
                                    selected_items: [...quotationForm.selected_items, { item_id: item.id, quantity: 1 }]
                                  });
                                } else {
                                  setQuotationForm({
                                    ...quotationForm, 
                                    selected_items: quotationForm.selected_items.filter(s => s.item_id !== item.id)
                                  });
                                }
                              }}
                              className="w-4 h-4"
                            />
                            <span className="flex-1 text-sm">{item.name}</span>
                            {item.has_quantity && isSelected && (
                              <input
                                type="number"
                                min="1"
                                value={selectedItem?.quantity || 1}
                                onChange={(e) => {
                                  const qty = parseInt(e.target.value) || 1;
                                  setQuotationForm({
                                    ...quotationForm,
                                    selected_items: quotationForm.selected_items.map(s => 
                                      s.item_id === item.id ? { ...s, quantity: qty } : s
                                    )
                                  });
                                }}
                                className="w-16 text-sm border rounded px-2 py-1"
                              />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div>
              <Label>Custom Description (optional)</Label>
              <Textarea 
                value={quotationForm.custom_description} 
                onChange={e => setQuotationForm({...quotationForm, custom_description: e.target.value})} 
                rows={2} 
                placeholder="Additional description to include..." 
              />
            </div>
            
            <div>
              <Label>Remarks (internal notes)</Label>
              <Textarea value={quotationForm.remarks} onChange={e => setQuotationForm({...quotationForm, remarks: e.target.value})} rows={2} placeholder="Internal notes..." />
            </div>
            <div>
              <Label>Terms & Conditions</Label>
              <Textarea 
                value={quotationForm.terms_conditions || defaultTerms} 
                onChange={e => setQuotationForm({...quotationForm, terms_conditions: e.target.value})} 
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowQuotationDialog(false)}>Cancel</Button>
            <Button onClick={handleSaveQuotation}>{editingQuotation ? 'Update' : 'Create'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Quotation Dialog */}
      <Dialog open={showViewDialog} onOpenChange={setShowViewDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Quotation Details</DialogTitle>
          </DialogHeader>
          {viewQuotation && (
            <div className="space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xl font-bold">{viewQuotation.quotation_number}</p>
                  <p className="text-gray-600">Created: {new Date(viewQuotation.created_at).toLocaleDateString()}</p>
                </div>
                {getStatusBadge(viewQuotation.status)}
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 p-3 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-2">Client</h4>
                  <p className="font-medium">{viewQuotation.client?.company_name}</p>
                  <p className="text-sm">{viewQuotation.client?.contact_person}</p>
                  <p className="text-sm">{viewQuotation.client?.contact_phone}</p>
                  <p className="text-sm">{viewQuotation.client?.contact_email}</p>
                </div>
                <div className="bg-green-50 p-3 rounded-lg">
                  <h4 className="font-semibold text-green-900 mb-2">Programme</h4>
                  <p className="font-medium">{viewQuotation.programme_name || 'Not specified'}</p>
                  <p className="text-sm">
                    {viewQuotation.pricing_type === 'per_group' 
                      ? `Group price: ${formatCurrency(viewQuotation.group_price || 0)}`
                      : `${viewQuotation.num_participants || '-'} pax @ ${formatCurrency(viewQuotation.rate_per_pax || 0)}`
                    }
                  </p>
                  <p className="text-sm font-bold mt-2">Total: {formatCurrency(viewQuotation.total_amount)}</p>
                  {/* Show priced addon items */}
                  {(viewQuotation.selected_items || []).some(s => s.unit_price > 0) && (
                    <div className="mt-2 pt-2 border-t border-green-200 space-y-1">
                      {viewQuotation.selected_items.filter(s => s.unit_price > 0).map((s, idx) => {
                        const item = descriptionItems.find(d => d.id === s.item_id);
                        return (
                          <p key={idx} className="text-xs text-green-800">
                            + {item?.name || 'Add-on'}: {s.quantity} x {formatCurrency(s.unit_price)} = {formatCurrency(s.unit_price * s.quantity)}
                          </p>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
              
              {/* Training details if accepted */}
              {viewQuotation.status === 'accepted' && viewQuotation.training_date && (
                <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                  <h4 className="font-semibold text-emerald-900 mb-2">Training Details</h4>
                  <p className="text-sm"><strong>Date:</strong> {viewQuotation.training_date}</p>
                  <p className="text-sm"><strong>Venue:</strong> {viewQuotation.venue}</p>
                </div>
              )}
              
              <div className="bg-yellow-50 p-3 rounded-lg">
                <p className="text-sm"><strong>Valid Until:</strong> {
                  (() => {
                    if (viewQuotation.valid_until) {
                      return new Date(viewQuotation.valid_until).toLocaleDateString();
                    }
                    // Calculate from created_at + validity_days
                    const created = new Date(viewQuotation.created_at);
                    const validDays = viewQuotation.validity_days || 30;
                    const validUntil = new Date(created.getTime() + validDays * 24 * 60 * 60 * 1000);
                    return validUntil.toLocaleDateString();
                  })()
                }</p>
              </div>
              
              {viewQuotation.admin_remarks && (
                <div className="bg-red-50 p-3 rounded-lg">
                  <h4 className="font-semibold text-red-900 mb-1">Admin Remarks</h4>
                  <p className="text-sm">{viewQuotation.admin_remarks}</p>
                </div>
              )}
              
              {/* Status History */}
              <div>
                <h4 className="font-semibold mb-2">Status History</h4>
                <div className="space-y-2">
                  {(viewQuotation.status_history || []).map((h, i) => (
                    <div key={i} className="flex justify-between text-sm border-l-2 border-gray-300 pl-3">
                      <span>{h.status.replace('_', ' ').toUpperCase()} - {h.by_name}</span>
                      <span className="text-gray-500">{new Date(h.at).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          <DialogFooter className="flex-wrap gap-2">
            {viewQuotation && ['approved', 'sent', 'accepted'].includes(viewQuotation.status) && (
              <>
                <Button onClick={() => handleDownloadPdf(viewQuotation.id)} disabled={downloadingPdf}>
                  <Download className="w-4 h-4 mr-2" /> {downloadingPdf ? 'Downloading...' : 'Download PDF'}
                </Button>
                <Button variant="outline" onClick={() => generateWord(viewQuotation)}>
                  <FileText className="w-4 h-4 mr-2" /> Download Word
                </Button>
              </>
            )}
            <Button variant="outline" onClick={() => setShowViewDialog(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Accept Quotation Dialog - capture training date and venue */}
      <Dialog open={showAcceptDialog} onOpenChange={setShowAcceptDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Mark Quotation as Accepted</DialogTitle>
            <DialogDescription>
              Enter the confirmed training date and venue for this quotation.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {acceptingQuotation && (
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="font-medium">{acceptingQuotation.quotation_number}</p>
                <p className="text-sm text-gray-600">{acceptingQuotation.client_name} - {acceptingQuotation.programme_name}</p>
                <p className="text-sm font-bold">{formatCurrency(acceptingQuotation.total_amount)}</p>
              </div>
            )}

            {/* Date Mode Selector */}
            <div>
              <Label>Training Schedule *</Label>
              <div className="grid grid-cols-3 gap-2 mt-1.5">
                <Button
                  type="button"
                  variant={acceptForm.date_mode === 'single' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setAcceptForm({ ...acceptForm, date_mode: 'single' })}
                  data-testid="date-mode-single"
                  className={acceptForm.date_mode === 'single' ? 'bg-green-600 hover:bg-green-700' : ''}
                >
                  Single Day
                </Button>
                <Button
                  type="button"
                  variant={acceptForm.date_mode === 'range' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setAcceptForm({ ...acceptForm, date_mode: 'range' })}
                  data-testid="date-mode-range"
                  className={acceptForm.date_mode === 'range' ? 'bg-green-600 hover:bg-green-700' : ''}
                >
                  Date Range
                </Button>
                <Button
                  type="button"
                  variant={acceptForm.date_mode === 'multiple' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setAcceptForm({ ...acceptForm, date_mode: 'multiple', training_dates: acceptForm.training_dates.length < 2 ? ['', ''] : acceptForm.training_dates })}
                  data-testid="date-mode-multiple"
                  className={acceptForm.date_mode === 'multiple' ? 'bg-green-600 hover:bg-green-700' : ''}
                >
                  Multiple Dates
                </Button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {acceptForm.date_mode === 'single' && 'Use this for a one-day programme.'}
                {acceptForm.date_mode === 'range' && 'Use this for back-to-back multi-day programmes.'}
                {acceptForm.date_mode === 'multiple' && 'Use this when training days are split across separate, non-consecutive dates.'}
              </p>
            </div>

            {/* Single Date */}
            {acceptForm.date_mode === 'single' && (
              <div>
                <Label htmlFor="training_date">Training Date *</Label>
                <Input
                  id="training_date"
                  type="date"
                  value={acceptForm.training_date}
                  onChange={(e) => setAcceptForm({ ...acceptForm, training_date: e.target.value })}
                  data-testid="single-training-date-input"
                  required
                />
              </div>
            )}

            {/* Date Range */}
            {acceptForm.date_mode === 'range' && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="start_date">Start Date *</Label>
                  <Input
                    id="start_date"
                    type="date"
                    value={acceptForm.training_date}
                    onChange={(e) => setAcceptForm({ ...acceptForm, training_date: e.target.value })}
                    data-testid="range-start-date-input"
                  />
                </div>
                <div>
                  <Label htmlFor="end_date">End Date *</Label>
                  <Input
                    id="end_date"
                    type="date"
                    value={acceptForm.end_date}
                    onChange={(e) => setAcceptForm({ ...acceptForm, end_date: e.target.value })}
                    data-testid="range-end-date-input"
                  />
                </div>
              </div>
            )}

            {/* Multiple Non-Consecutive Dates */}
            {acceptForm.date_mode === 'multiple' && (
              <div className="space-y-2">
                <Label>Training Dates *</Label>
                {acceptForm.training_dates.map((d, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-12">Day {idx + 1}</span>
                    <Input
                      type="date"
                      value={d}
                      onChange={(e) => {
                        const next = [...acceptForm.training_dates];
                        next[idx] = e.target.value;
                        setAcceptForm({ ...acceptForm, training_dates: next });
                      }}
                      data-testid={`multi-date-input-${idx}`}
                    />
                    {acceptForm.training_dates.length > 2 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          const next = acceptForm.training_dates.filter((_, i) => i !== idx);
                          setAcceptForm({ ...acceptForm, training_dates: next });
                        }}
                        data-testid={`multi-date-remove-${idx}`}
                      >
                        ×
                      </Button>
                    )}
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setAcceptForm({ ...acceptForm, training_dates: [...acceptForm.training_dates, ''] })}
                  data-testid="multi-date-add-btn"
                >
                  + Add another date
                </Button>
              </div>
            )}

            <div>
              <Label htmlFor="venue">Venue / Location *</Label>
              <Input
                id="venue"
                placeholder="Enter training venue"
                value={acceptForm.venue}
                onChange={(e) => setAcceptForm({...acceptForm, venue: e.target.value})}
                required
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAcceptDialog(false)}>Cancel</Button>
            <Button onClick={handleAcceptQuotation} className="bg-green-600 hover:bg-green-700">
              <CheckCircle className="w-4 h-4 mr-2" /> Confirm Acceptance
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Apply Discount Dialog - for negotiation */}
      <Dialog open={showDiscountDialog} onOpenChange={setShowDiscountDialog}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Apply Discount (Negotiation)</DialogTitle>
            <DialogDescription>
              Apply a discount to this quotation for negotiation purposes.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {discountingQuotation && (
              <div className="bg-gray-50 p-3 rounded-lg">
                <p className="font-medium">{discountingQuotation.quotation_number}</p>
                <p className="text-sm text-gray-600">{discountingQuotation.client_name}</p>
                <p className="text-sm">Original Subtotal: <strong>{formatCurrency(discountingQuotation.subtotal || discountingQuotation.total_amount)}</strong></p>
                <p className="text-sm">Current Total: <strong>{formatCurrency(discountingQuotation.total_amount)}</strong></p>
                {discountingQuotation.discount_amount > 0 && (
                  <p className="text-sm text-orange-600">Existing Discount: {formatCurrency(discountingQuotation.discount_amount)} ({discountingQuotation.discount_percentage}%)</p>
                )}
              </div>
            )}
            <div>
              <Label>Discount Type</Label>
              <Select value={discountForm.discount_type} onValueChange={(v) => setDiscountForm({...discountForm, discount_type: v})}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="percentage">Percentage (%)</SelectItem>
                  <SelectItem value="fixed">Fixed Amount (RM)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Discount Value {discountForm.discount_type === 'percentage' ? '(%)' : '(RM)'}</Label>
              <Input
                type="number"
                min="0"
                step={discountForm.discount_type === 'percentage' ? '1' : '0.01'}
                max={discountForm.discount_type === 'percentage' ? '100' : undefined}
                value={discountForm.discount_value}
                onFocus={e => e.target.select()}
                onChange={(e) => setDiscountForm({...discountForm, discount_value: parseFloat(e.target.value) || 0})}
                placeholder={discountForm.discount_type === 'percentage' ? 'e.g. 10' : 'e.g. 500'}
              />
            </div>
            <div>
              <Label>Reason (Optional)</Label>
              <Input
                placeholder="e.g. Bulk order discount, Loyal customer"
                value={discountForm.reason}
                onChange={(e) => setDiscountForm({...discountForm, reason: e.target.value})}
              />
            </div>
            {discountForm.discount_value > 0 && discountingQuotation && (
              <div className="bg-green-50 p-3 rounded-lg border border-green-200">
                <p className="text-sm font-medium text-green-900">Preview:</p>
                <p className="text-sm">
                  Discount: {discountForm.discount_type === 'percentage' 
                    ? `${discountForm.discount_value}% = ${formatCurrency((discountingQuotation.subtotal || discountingQuotation.total_amount) * discountForm.discount_value / 100)}`
                    : formatCurrency(discountForm.discount_value)
                  }
                </p>
                <p className="text-sm font-bold">
                  New Total: {formatCurrency(
                    discountForm.discount_type === 'percentage'
                      ? (discountingQuotation.subtotal || discountingQuotation.total_amount) * (1 - discountForm.discount_value / 100)
                      : (discountingQuotation.subtotal || discountingQuotation.total_amount) - discountForm.discount_value
                  )}
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDiscountDialog(false)}>Cancel</Button>
            <Button onClick={handleApplyDiscount} className="bg-purple-600 hover:bg-purple-700">
              Apply Discount
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MarketingDashboard;
