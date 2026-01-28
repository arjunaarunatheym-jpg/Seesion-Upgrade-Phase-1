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
  Send, FileCheck, XCircle, Phone, Mail, MapPin, User, Printer
} from 'lucide-react';
import MyEarnings from '../components/MyEarnings';
import { DashboardTab } from '../components/marketing/DashboardTab';
import { ClientsTab } from '../components/marketing/ClientsTab';
import { QuotationsTab } from '../components/marketing/QuotationsTab';

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
    pricing_type: 'per_pax',
    num_participants: 1,
    rate_per_pax: 0,
    group_price: 0,
    sst_percent: 0,
    validity_days: 30,
    description_items: [],
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
    training_date: '',
    venue: ''
  });
  
  // PDF download loading state
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, clientsRes, quotationsRes, programmesRes, termsRes, settingsRes, descItemsRes] = await Promise.all([
        axiosInstance.get('/marketing/stats'),
        axiosInstance.get('/marketing/clients'),
        axiosInstance.get('/marketing/quotations'),
        axiosInstance.get('/marketing/programmes'),
        axiosInstance.get('/marketing/default-terms'),
        axiosInstance.get('/finance/company-settings'),
        axiosInstance.get('/marketing/description-items')
      ]);
      
      setStats(statsRes.data || {});
      setClients(clientsRes.data || []);
      setQuotations(quotationsRes.data || []);
      setProgrammes(programmesRes.data || []);
      setDefaultTerms(termsRes.data?.terms || '');
      setCompanySettings(settingsRes.data);
      setDescriptionItems(descItemsRes.data || []);
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
      
      if (editingQuotation) {
        await axiosInstance.put(`/marketing/quotations/${editingQuotation.id}`, quotationForm);
        toast.success('Quotation updated successfully');
      } else {
        const payload = {
          ...quotationForm,
          terms_conditions: quotationForm.terms_conditions || defaultTerms
        };
        await axiosInstance.post('/marketing/quotations', payload);
        toast.success('Quotation created successfully');
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
      pricing_type: 'per_pax',
      num_participants: 1,
      rate_per_pax: 0,
      group_price: 0,
      sst_percent: 0,
      validity_days: 30,
      description_items: [],
      custom_description: '',
      remarks: '',
      terms_conditions: ''
    });
  };

  const openEditQuotation = (quotation) => {
    setEditingQuotation(quotation);
    setQuotationForm({
      client_id: quotation.client_id || '',
      programme_id: quotation.programme_id || '',
      pricing_type: quotation.pricing_type || 'per_pax',
      num_participants: quotation.num_participants || 1,
      rate_per_pax: quotation.rate_per_pax || 0,
      group_price: quotation.group_price || 0,
      sst_percent: quotation.sst_percent || 0,
      validity_days: quotation.validity_days || 30,
      description_items: quotation.description_items || [],
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
      setAcceptForm({ training_date: '', venue: '' });
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
    if (!acceptForm.training_date || !acceptForm.venue) {
      toast.error('Please enter training date and venue');
      return;
    }
    
    try {
      await axiosInstance.post(`/marketing/quotations/${acceptingQuotation.id}/client-response`, {
        response: 'accepted',
        training_date: acceptForm.training_date,
        venue: acceptForm.venue
      });
      toast.success('Quotation marked as accepted');
      setShowAcceptDialog(false);
      setAcceptingQuotation(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update');
    }
  };

  const handleDownloadPdf = async (quotationId) => {
    setDownloadingPdf(true);
    try {
      const response = await axiosInstance.get(`/marketing/quotations/${quotationId}/download-pdf`, {
        responseType: 'blob'
      });
      
      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Get filename from quotation
      const quotation = quotations.find(q => q.id === quotationId);
      const filename = quotation?.quotation_number?.replace(/\//g, '_') || 'quotation';
      link.download = `Quotation_${filename}.pdf`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('PDF downloaded successfully');
    } catch (error) {
      console.error('PDF download error:', error);
      toast.error(error.response?.data?.detail || 'Failed to download PDF');
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
  const generatePDF = (quotation) => {
    const client = quotation.client || {};
    const printWindow = window.open('', '_blank');
    
    const html = `
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
      ${companySettings?.logo_url ? `<img src="${companySettings.logo_url}" class="logo" />` : ''}
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
        <td style="text-align: center;">${quotation.num_participants}</td>
        <td style="text-align: right;">${quotation.rate_per_pax?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
        <td style="text-align: right;">${quotation.subtotal?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
      </tr>
      ${quotation.remarks ? `<tr><td colspan="4" style="font-size: 12px; color: #666;"><em>Remarks: ${quotation.remarks}</em></td></tr>` : ''}
      <tr class="amount-row">
        <td colspan="3" style="text-align: right;">Subtotal</td>
        <td style="text-align: right;">RM ${quotation.subtotal?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
      </tr>
      ${quotation.sst_percent > 0 ? `
      <tr class="amount-row">
        <td colspan="3" style="text-align: right;">SST (${quotation.sst_percent}%)</td>
        <td style="text-align: right;">RM ${quotation.sst_amount?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
      </tr>
      ` : ''}
      <tr class="amount-row total-row">
        <td colspan="3" style="text-align: right;">TOTAL</td>
        <td style="text-align: right;">RM ${quotation.total_amount?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
      </tr>
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
      <p>Prepared by: ${quotation.marketer?.full_name || ''}</p>
    </div>
    <div class="signature-box">
      <p>Approved by: ${quotation.approver?.full_name || ''}</p>
    </div>
  </div>
  
  <script>window.onload = function() { window.print(); }</script>
</body>
</html>
    `;
    
    printWindow.document.write(html);
    printWindow.document.close();
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
          <TabsList className="mb-4 sm:mb-6 flex flex-wrap gap-1">
            <TabsTrigger value="dashboard" data-testid="dashboard-tab" className="text-xs sm:text-sm px-2 sm:px-3">
              <BarChart3 className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> <span className="hidden sm:inline">Dashboard</span><span className="sm:hidden">Home</span>
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
          </TabsList>

          {/* Dashboard Tab */}
          <TabsContent value="dashboard">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Clients</p>
                      <p className="text-2xl font-bold text-blue-600">{stats.clients || 0}</p>
                    </div>
                    <Building className="w-8 h-8 text-blue-200" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Pending Approval</p>
                      <p className="text-2xl font-bold text-yellow-600">{stats.pending_approval || 0}</p>
                    </div>
                    <Clock className="w-8 h-8 text-yellow-200" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Accepted</p>
                      <p className="text-2xl font-bold text-green-600">{stats.accepted || 0}</p>
                    </div>
                    <CheckCircle className="w-8 h-8 text-green-200" />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-600">Accepted Value</p>
                      <p className="text-xl font-bold text-emerald-600">{formatCurrency(stats.total_accepted_value)}</p>
                    </div>
                    <DollarSign className="w-8 h-8 text-emerald-200" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Quick Actions */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="flex gap-3">
                <Button onClick={() => { resetQuotationForm(); setEditingQuotation(null); setShowQuotationDialog(true); }}>
                  <Plus className="w-4 h-4 mr-2" /> New Quotation
                </Button>
                <Button variant="outline" onClick={() => { setEditingClient(null); setClientForm({ company_name: '', company_address: '', contact_person: '', contact_phone: '', contact_email: '', notes: '' }); setShowClientDialog(true); }}>
                  <Building className="w-4 h-4 mr-2" /> Add Client
                </Button>
              </CardContent>
            </Card>

            {/* Recent Quotations */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Quotations</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {quotations.slice(0, 5).map(q => (
                    <div key={q.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100">
                      <div>
                        <p className="font-medium">{q.quotation_number}</p>
                        <p className="text-sm text-gray-600">{q.client_name} - {formatCurrency(q.total_amount)}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {getStatusBadge(q.status)}
                        <Button variant="ghost" size="sm" onClick={() => viewQuotationDetails(q.id)}>
                          <Eye className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                  {quotations.length === 0 && (
                    <p className="text-center text-gray-500 py-8">No quotations yet. Create your first one!</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Clients Tab */}
          <TabsContent value="clients">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>My Clients</CardTitle>
                    <CardDescription>Manage your client list</CardDescription>
                  </div>
                  <Button onClick={() => { setEditingClient(null); setClientForm({ company_name: '', company_address: '', contact_person: '', contact_phone: '', contact_email: '', notes: '' }); setShowClientDialog(true); }}>
                    <Plus className="w-4 h-4 mr-2" /> Add Client
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                    <Input
                      placeholder="Search clients..."
                      value={clientSearch}
                      onChange={(e) => setClientSearch(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
                
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {filteredClients.map(client => (
                    <Card key={client.id} className="border">
                      <CardContent className="p-4">
                        <div className="flex justify-between items-start mb-2">
                          <h3 className="font-semibold text-gray-900">{client.company_name}</h3>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="sm" onClick={() => openEditClient(client)}>
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteClient(client.id)} className="text-red-600">
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                        <div className="space-y-1 text-sm text-gray-600">
                          <p className="flex items-center gap-2"><User className="w-3 h-3" /> {client.contact_person}</p>
                          <p className="flex items-center gap-2"><Phone className="w-3 h-3" /> {client.contact_phone}</p>
                          <p className="flex items-center gap-2"><Mail className="w-3 h-3" /> {client.contact_email}</p>
                          {client.company_address && (
                            <p className="flex items-start gap-2"><MapPin className="w-3 h-3 mt-1" /> {client.company_address}</p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
                
                {filteredClients.length === 0 && (
                  <p className="text-center text-gray-500 py-8">No clients found. Add your first client!</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Quotations Tab */}
          <TabsContent value="quotations">
            <Card>
              <CardHeader>
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <CardTitle className="text-lg sm:text-xl">Quotations</CardTitle>
                    <CardDescription className="text-xs sm:text-sm">Manage your quotations</CardDescription>
                  </div>
                  <div className="flex gap-2 w-full sm:w-auto">
                    <Select value={quotationFilter} onValueChange={setQuotationFilter}>
                      <SelectTrigger className="w-full sm:w-40 text-xs sm:text-sm">
                        <SelectValue placeholder="Filter" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Status</SelectItem>
                        <SelectItem value="draft">Draft</SelectItem>
                        <SelectItem value="pending_approval">Pending</SelectItem>
                        <SelectItem value="approved">Approved</SelectItem>
                        <SelectItem value="rejected">Rejected</SelectItem>
                        <SelectItem value="sent">Sent</SelectItem>
                        <SelectItem value="accepted">Accepted</SelectItem>
                        <SelectItem value="declined">Declined</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button onClick={() => { resetQuotationForm(); setEditingQuotation(null); setShowQuotationDialog(true); }} className="text-xs sm:text-sm whitespace-nowrap">
                      <Plus className="w-3 h-3 sm:w-4 sm:h-4 mr-1" /> <span className="hidden sm:inline">New </span>Quotation
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="px-2 sm:px-6">
                <div className="overflow-x-auto -mx-2 sm:mx-0">
                  <table className="w-full text-xs sm:text-sm min-w-[600px]">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th className="text-left p-2 sm:p-3">Quote No</th>
                        <th className="text-left p-2 sm:p-3">Client</th>
                        <th className="text-left p-2 sm:p-3 hidden sm:table-cell">Programme</th>
                        <th className="text-right p-2 sm:p-3">Amount</th>
                        <th className="text-center p-2 sm:p-3">Status</th>
                        <th className="text-center p-2 sm:p-3">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredQuotations.map(q => (
                        <tr key={q.id} className="border-b hover:bg-gray-50">
                          <td className="p-2 sm:p-3 font-medium text-xs">{q.quotation_number}</td>
                          <td className="p-2 sm:p-3 max-w-[100px] truncate">{q.client_name}</td>
                          <td className="p-2 sm:p-3 max-w-[150px] truncate hidden sm:table-cell">{q.programme_name}</td>
                          <td className="p-2 sm:p-3 text-right whitespace-nowrap">{formatCurrency(q.total_amount)}</td>
                          <td className="p-2 sm:p-3 text-center">{getStatusBadge(q.status)}</td>
                          <td className="p-2 sm:p-3">
                            <div className="flex justify-center gap-0.5 sm:gap-1">
                              <Button variant="ghost" size="sm" onClick={() => viewQuotationDetails(q.id)} title="View" className="h-7 w-7 sm:h-8 sm:w-8 p-0">
                                <Eye className="w-3 h-3 sm:w-4 sm:h-4" />
                              </Button>
                              
                              {q.status === 'draft' && (
                                <>
                                  <Button variant="ghost" size="sm" onClick={() => openEditQuotation(q)} title="Edit" className="h-7 w-7 sm:h-8 sm:w-8 p-0">
                                    <Edit className="w-3 h-3 sm:w-4 sm:h-4" />
                                  </Button>
                                  <Button variant="ghost" size="sm" onClick={() => handleSubmitForApproval(q.id)} title="Submit for Approval" className="text-yellow-600 h-7 w-7 sm:h-8 sm:w-8 p-0">
                                    <Send className="w-3 h-3 sm:w-4 sm:h-4" />
                                  </Button>
                                </>
                              )}
                              
                              {q.status === 'rejected' && (
                                <Button variant="ghost" size="sm" onClick={() => openEditQuotation(q)} title="Revise" className="h-7 w-7 sm:h-8 sm:w-8 p-0">
                                  <Edit className="w-3 h-3 sm:w-4 sm:h-4" />
                                </Button>
                              )}
                              
                              {q.status === 'approved' && (
                                <>
                                  <Button variant="ghost" size="sm" onClick={() => handleDownloadPdf(q.id)} title="Download PDF" className="text-blue-600 h-7 w-7 sm:h-8 sm:w-8 p-0" disabled={downloadingPdf}>
                                    <Download className="w-3 h-3 sm:w-4 sm:h-4" />
                                  </Button>
                                  <Button variant="ghost" size="sm" onClick={() => handleMarkSent(q.id)} title="Mark as Sent" className="text-green-600 h-7 w-7 sm:h-8 sm:w-8 p-0">
                                    <Send className="w-3 h-3 sm:w-4 sm:h-4" />
                                  </Button>
                                </>
                              )}
                              
                              {q.status === 'sent' && (
                                <>
                                  <Button variant="ghost" size="sm" onClick={() => handleDownloadPdf(q.id)} title="Download PDF" className="text-blue-600 h-7 w-7 sm:h-8 sm:w-8 p-0" disabled={downloadingPdf}>
                                    <Download className="w-3 h-3 sm:w-4 sm:h-4" />
                                  </Button>
                                  <Button variant="ghost" size="sm" onClick={() => handleClientResponse(q.id, 'accepted')} title="Client Accepted" className="text-green-600 h-7 w-7 sm:h-8 sm:w-8 p-0">
                                    <CheckCircle className="w-3 h-3 sm:w-4 sm:h-4" />
                                  </Button>
                                  <Button variant="ghost" size="sm" onClick={() => handleClientResponse(q.id, 'declined')} title="Client Declined" className="text-red-600 h-7 w-7 sm:h-8 sm:w-8 p-0">
                                    <XCircle className="w-3 h-3 sm:w-4 sm:h-4" />
                                  </Button>
                                </>
                              )}
                              
                              {q.status === 'accepted' && (
                                <Button variant="ghost" size="sm" onClick={() => handleDownloadPdf(q.id)} title="Download Final PDF" className="text-emerald-600 h-7 w-7 sm:h-8 sm:w-8 p-0" disabled={downloadingPdf}>
                                  <Download className="w-3 h-3 sm:w-4 sm:h-4" />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                
                {filteredQuotations.length === 0 && (
                  <p className="text-center text-gray-500 py-6 sm:py-8 text-sm">No quotations found.</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Earnings Tab */}
          <TabsContent value="earnings">
            <MyEarnings user={user} />
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
                    {clients.map(c => (
                      <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {clients.length === 0 && <p className="text-xs text-red-500 mt-1">Please add a client first</p>}
              </div>
              <div>
                <Label>Programme *</Label>
                <Select value={quotationForm.programme_id} onValueChange={v => setQuotationForm({...quotationForm, programme_id: v})}>
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
                  <Input type="number" min="1" value={quotationForm.num_participants} onChange={e => setQuotationForm({...quotationForm, num_participants: parseInt(e.target.value) || 1})} />
                </div>
                <div>
                  <Label>Rate per Pax (RM) *</Label>
                  <Input type="number" min="0" step="0.01" value={quotationForm.rate_per_pax} onChange={e => setQuotationForm({...quotationForm, rate_per_pax: parseFloat(e.target.value) || 0})} />
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Max Participants (for reference)</Label>
                  <Input type="number" min="1" value={quotationForm.num_participants} onChange={e => setQuotationForm({...quotationForm, num_participants: parseInt(e.target.value) || 1})} />
                </div>
                <div>
                  <Label>Group Price (RM) *</Label>
                  <Input type="number" min="0" step="0.01" value={quotationForm.group_price} onChange={e => setQuotationForm({...quotationForm, group_price: parseFloat(e.target.value) || 0})} />
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>SST (%)</Label>
                <Input type="number" min="0" max="100" value={quotationForm.sst_percent} onChange={e => setQuotationForm({...quotationForm, sst_percent: parseFloat(e.target.value) || 0})} />
              </div>
              <div>
                <Label>Validity (Days)</Label>
                <Input type="number" min="1" value={quotationForm.validity_days} onChange={e => setQuotationForm({...quotationForm, validity_days: parseInt(e.target.value) || 30})} />
              </div>
            </div>
            
            {/* Calculated amounts */}
            <div className="bg-gray-50 p-3 rounded-lg">
              {(() => {
                const subtotal = quotationForm.pricing_type === 'per_group' 
                  ? quotationForm.group_price 
                  : quotationForm.num_participants * quotationForm.rate_per_pax;
                const sst = subtotal * quotationForm.sst_percent / 100;
                const total = subtotal + sst;
                return (
                  <>
                    <div className="flex justify-between text-sm">
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

            {/* Description Items (if any exist) */}
            {descriptionItems.length > 0 && (
              <div className="border rounded-lg p-3">
                <Label className="font-semibold">Include in Quotation</Label>
                <div className="mt-2 space-y-2 max-h-40 overflow-y-auto">
                  {descriptionItems.map(item => (
                    <label key={item.id} className="flex items-start gap-2 cursor-pointer p-2 hover:bg-gray-50 rounded">
                      <input
                        type="checkbox"
                        checked={quotationForm.description_items.includes(item.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setQuotationForm({...quotationForm, description_items: [...quotationForm.description_items, item.id]});
                          } else {
                            setQuotationForm({...quotationForm, description_items: quotationForm.description_items.filter(id => id !== item.id)});
                          }
                        }}
                        className="w-4 h-4 mt-1"
                      />
                      <div>
                        <span className="font-medium">{item.name}</span>
                        <p className="text-xs text-gray-500">{item.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
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
                  <p className="font-medium">{viewQuotation.programme_name}</p>
                  <p className="text-sm">
                    {viewQuotation.pricing_type === 'per_group' 
                      ? `Group price: ${formatCurrency(viewQuotation.group_price)}`
                      : `${viewQuotation.num_participants} pax @ ${formatCurrency(viewQuotation.rate_per_pax)}`
                    }
                  </p>
                  <p className="text-sm font-bold mt-2">Total: {formatCurrency(viewQuotation.total_amount)}</p>
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
                <p className="text-sm"><strong>Valid Until:</strong> {new Date(viewQuotation.valid_until).toLocaleDateString()}</p>
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
          <DialogFooter>
            {viewQuotation && ['approved', 'sent', 'accepted'].includes(viewQuotation.status) && (
              <Button onClick={() => handleDownloadPdf(viewQuotation.id)} disabled={downloadingPdf}>
                <Download className="w-4 h-4 mr-2" /> {downloadingPdf ? 'Downloading...' : 'Download PDF Package'}
              </Button>
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
            <div>
              <Label htmlFor="training_date">Training Date *</Label>
              <Input
                id="training_date"
                type="date"
                value={acceptForm.training_date}
                onChange={(e) => setAcceptForm({...acceptForm, training_date: e.target.value})}
                required
              />
            </div>
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
    </div>
  );
};

export default MarketingDashboard;
