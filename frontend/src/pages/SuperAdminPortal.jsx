/**
 * SuperAdminPortal.jsx
 * Comprehensive system administration dashboard
 * Access: Super Admin role only (arjuna@mddrc.com.my or role=super_admin)
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { axiosInstance } from '../App';
import { toast } from 'sonner';
import AdminFeeSettingsCard from '../components/admin/AdminFeeSettingsCard';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Textarea } from '../components/ui/textarea';
import { 
  Shield, Users, Building2, FileText, CreditCard, 
  Settings, BarChart3, Download, RefreshCw, Search,
  Edit, Trash2, Lock, Unlock, Eye, AlertTriangle,
  CheckCircle, XCircle, Activity, Database, Clock,
  DollarSign, BookOpen, Loader2, UserCog, FileSpreadsheet,
  ArrowLeft, LogOut
} from 'lucide-react';

const SuperAdminPortal = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Dashboard stats
  const [stats, setStats] = useState(null);
  
  // Users
  const [users, setUsers] = useState([]);
  const [userSearch, setUserSearch] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserDialog, setShowUserDialog] = useState(false);
  const [userAction, setUserAction] = useState({ type: '', reason: '' });
  
  // Sessions
  const [sessions, setSessions] = useState([]);
  const [sessionFilter, setSessionFilter] = useState({ status: '', year: 2026 });
  const [selectedSession, setSelectedSession] = useState(null);
  
  // Invoices
  const [invoices, setInvoices] = useState([]);
  const [invoiceFilter, setInvoiceFilter] = useState({ status: '', year: 2026 });
  
  // Quotations
  const [quotations, setQuotations] = useState([]);
  
  // Audit Log
  const [auditLogs, setAuditLogs] = useState([]);
  
  // Settings
  const [systemSettings, setSystemSettings] = useState(null);
  
  // Session Data Entry
  const [selectedSessionForData, setSelectedSessionForData] = useState(null);
  const [sessionParticipants, setSessionParticipants] = useState([]);
  const [sessionTests, setSessionTests] = useState([]);
  const [attendanceData, setAttendanceData] = useState({});
  const [testResultsData, setTestResultsData] = useState({});
  
  // Edit Dialogs
  const [editUserDialog, setEditUserDialog] = useState({ open: false, user: null });
  const [editSessionDialog, setEditSessionDialog] = useState({ open: false, session: null });
  const [editInvoiceDialog, setEditInvoiceDialog] = useState({ open: false, invoice: null });
  const [editJournalDialog, setEditJournalDialog] = useState({ open: false, entry: null });

  // Payment Reversal
  const [reversalPayments, setReversalPayments] = useState([]);
  const [reversalPreview, setReversalPreview] = useState(null);
  const [reversalStep, setReversalStep] = useState(0); // 0=list, 1=preview, 2=reason, 3=confirm
  const [reversalReason, setReversalReason] = useState('');
  const [reversalExecuting, setReversalExecuting] = useState(false);
  const [reversalHistory, setReversalHistory] = useState([]);
  const [reversalResult, setReversalResult] = useState(null);
  const [reversalSearch, setReversalSearch] = useState('');

  // Quotation & Invoice Reversal (lightweight one-step flow)
  const [reversalSubTab, setReversalSubTab] = useState('payments'); // 'payments' | 'invoices' | 'quotations'
  const [quotationsForReversal, setQuotationsForReversal] = useState([]);
  const [invoicesForReversal, setInvoicesForReversal] = useState([]);
  const [quotationReversalHistory, setQuotationReversalHistory] = useState([]);
  const [invoiceReversalHistory, setInvoiceReversalHistory] = useState([]);
  const [genericReverseDialog, setGenericReverseDialog] = useState({ open: false, kind: null, item: null, preview: null, reason: '', loading: false });

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get('/superadmin/dashboard');
      setStats(response.data);
    } catch (error) {
      if (error.response?.status === 403) {
        toast.error('Access Denied: Super Admin privileges required');
      } else {
        toast.error('Failed to load dashboard');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (userSearch) params.append('search', userSearch);
      const response = await axiosInstance.get(`/superadmin/users?${params}`);
      setUsers(response.data.users || []);
    } catch (error) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const loadSessions = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (sessionFilter.status) params.append('status', sessionFilter.status);
      if (sessionFilter.year) params.append('year', sessionFilter.year);
      const response = await axiosInstance.get(`/superadmin/sessions?${params}`);
      setSessions(response.data.sessions || []);
    } catch (error) {
      toast.error('Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  const loadInvoices = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (invoiceFilter.status) params.append('status', invoiceFilter.status);
      if (invoiceFilter.year) params.append('year', invoiceFilter.year);
      const response = await axiosInstance.get(`/superadmin/invoices?${params}`);
      setInvoices(response.data.invoices || []);
    } catch (error) {
      toast.error('Failed to load invoices');
    } finally {
      setLoading(false);
    }
  };

  const loadQuotations = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get('/superadmin/quotations');
      setQuotations(response.data.quotations || []);
    } catch (error) {
      toast.error('Failed to load quotations');
    } finally {
      setLoading(false);
    }
  };

  const loadAuditLog = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get('/superadmin/audit-log?limit=100');
      setAuditLogs(response.data.logs || []);
    } catch (error) {
      toast.error('Failed to load audit log');
    } finally {
      setLoading(false);
    }
  };

  const loadSettings = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get('/superadmin/settings');
      setSystemSettings(response.data);
    } catch (error) {
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  // Payment Reversal Functions
  const loadReversalPayments = async () => {
    setLoading(true);
    try {
      const [paymentsRes, historyRes] = await Promise.all([
        axiosInstance.get('/superadmin/payments-for-reversal'),
        axiosInstance.get('/superadmin/payment-reversals')
      ]);
      setReversalPayments(paymentsRes.data || []);
      setReversalHistory(historyRes.data || []);
    } catch (error) {
      toast.error('Failed to load payments');
    } finally {
      setLoading(false);
    }
  };

  const handlePreviewReversal = async (paymentId) => {
    setLoading(true);
    try {
      const response = await axiosInstance.get(`/superadmin/payment-reversal/preview/${paymentId}`);
      setReversalPreview(response.data);
      setReversalStep(1);
      setReversalReason('');
      setReversalResult(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load preview');
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteReversal = async () => {
    if (reversalReason.length < 10) {
      toast.error('Reason must be at least 10 characters');
      return;
    }
    setReversalExecuting(true);
    try {
      const response = await axiosInstance.post('/superadmin/payment-reversal/execute', {
        payment_id: reversalPreview.payment.id,
        reason: reversalReason,
        confirm: true
      });
      setReversalResult(response.data);
      setReversalStep(3);
      toast.success('Payment reversed successfully');
      loadReversalPayments(); // refresh
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Reversal failed');
    } finally {
      setReversalExecuting(false);
    }
  };

  // Quotation Reversal loaders
  const loadQuotationReversals = async () => {
    try {
      const [listRes, histRes] = await Promise.all([
        axiosInstance.get('/superadmin/quotations-for-reversal'),
        axiosInstance.get('/superadmin/quotation-reversals')
      ]);
      setQuotationsForReversal(listRes.data || []);
      setQuotationReversalHistory(histRes.data || []);
    } catch (e) {
      toast.error('Failed to load quotation reversals');
    }
  };

  const loadInvoiceReversals = async () => {
    try {
      const [listRes, histRes] = await Promise.all([
        axiosInstance.get('/superadmin/invoices-for-reversal'),
        axiosInstance.get('/superadmin/invoice-reversals')
      ]);
      setInvoicesForReversal(listRes.data || []);
      setInvoiceReversalHistory(histRes.data || []);
    } catch (e) {
      toast.error('Failed to load invoice reversals');
    }
  };

  // Open the lightweight reverse dialog (kind: 'quotation' | 'invoice')
  const openGenericReverse = async (kind, item) => {
    try {
      const url = kind === 'quotation'
        ? `/superadmin/quotation-reversal/preview/${item.id}`
        : `/superadmin/invoice-reversal/preview/${item.id}`;
      const { data } = await axiosInstance.get(url);
      setGenericReverseDialog({ open: true, kind, item, preview: data, reason: '', loading: false });
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load preview');
    }
  };

  const executeGenericReverse = async () => {
    const { kind, item, reason } = genericReverseDialog;
    if (reason.length < 10) { toast.error('Reason must be at least 10 characters'); return; }
    setGenericReverseDialog(prev => ({ ...prev, loading: true }));
    try {
      const url = kind === 'quotation' ? '/superadmin/quotation-reversal/execute' : '/superadmin/invoice-reversal/execute';
      const payload = kind === 'quotation'
        ? { quotation_id: item.id, reason, confirm: true }
        : { invoice_id: item.id, reason, confirm: true };
      const { data } = await axiosInstance.post(url, payload);
      toast.success(data.message || `${kind} reversed successfully`);
      setGenericReverseDialog({ open: false, kind: null, item: null, preview: null, reason: '', loading: false });
      if (kind === 'quotation') loadQuotationReversals(); else loadInvoiceReversals();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Reversal failed');
      setGenericReverseDialog(prev => ({ ...prev, loading: false }));
    }
  };

  // User Actions
  const handleToggleUserActive = async (userId) => {
    const reason = prompt('Enter reason for this action (min 5 characters):');
    if (!reason || reason.length < 5) {
      toast.error('Reason is required (min 5 characters)');
      return;
    }
    try {
      await axiosInstance.post(`/superadmin/users/${userId}/toggle-active?reason=${encodeURIComponent(reason)}`);
      toast.success('User status updated');
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update user');
    }
  };

  const handleResetPassword = async (userId) => {
    const newPassword = prompt('Enter new password (min 6 characters):');
    if (!newPassword || newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    const reason = prompt('Enter reason for password reset:');
    if (!reason || reason.length < 5) {
      toast.error('Reason is required');
      return;
    }
    try {
      await axiosInstance.post(`/superadmin/users/${userId}/reset-password?new_password=${encodeURIComponent(newPassword)}&reason=${encodeURIComponent(reason)}`);
      toast.success('Password reset successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset password');
    }
  };

  const handleChangeUserRole = async (userId, newRole) => {
    const reason = prompt('Enter reason for role change:');
    if (!reason || reason.length < 5) {
      toast.error('Reason is required');
      return;
    }
    try {
      await axiosInstance.put(`/superadmin/users/${userId}?reason=${encodeURIComponent(reason)}`, { role: newRole });
      toast.success('User role updated');
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    }
  };

  // Session Actions
  const handleFixSessionStatus = async (sessionId, newStatus) => {
    const reason = prompt('Enter reason for status change:');
    if (!reason || reason.length < 5) {
      toast.error('Reason is required');
      return;
    }
    try {
      await axiosInstance.post(`/superadmin/sessions/${sessionId}/fix-status?new_status=${newStatus}&reason=${encodeURIComponent(reason)}`);
      toast.success('Session status updated');
      loadSessions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update session');
    }
  };

  // Invoice Actions
  const handleVoidInvoice = async (invoiceId) => {
    const reason = prompt('Enter reason for voiding invoice (min 10 characters):');
    if (!reason || reason.length < 10) {
      toast.error('Reason must be at least 10 characters');
      return;
    }
    try {
      await axiosInstance.post(`/superadmin/invoices/${invoiceId}/void?reason=${encodeURIComponent(reason)}`);
      toast.success('Invoice voided');
      loadInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to void invoice');
    }
  };

  // Export
  const handleExport = async (collection) => {
    try {
      const response = await axiosInstance.get(`/superadmin/export/${collection}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${collection}_export.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success(`${collection} exported`);
    } catch (error) {
      toast.error('Export failed');
    }
  };

  // Edit User (Full Edit)
  const handleSaveUser = async () => {
    if (!editUserDialog.user) return;
    const reason = prompt('Enter reason for changes:');
    if (!reason || reason.length < 5) {
      toast.error('Reason is required');
      return;
    }
    try {
      await axiosInstance.put(`/superadmin/users/${editUserDialog.user.id}?reason=${encodeURIComponent(reason)}`, editUserDialog.user);
      toast.success('User updated');
      setEditUserDialog({ open: false, user: null });
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update user');
    }
  };

  // Edit Session (Full Edit)
  const handleSaveSession = async () => {
    if (!editSessionDialog.session) return;
    const reason = prompt('Enter reason for changes:');
    if (!reason || reason.length < 5) {
      toast.error('Reason is required');
      return;
    }
    try {
      await axiosInstance.put(`/superadmin/sessions/${editSessionDialog.session.id}?reason=${encodeURIComponent(reason)}`, editSessionDialog.session);
      toast.success('Session updated');
      setEditSessionDialog({ open: false, session: null });
      loadSessions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update session');
    }
  };

  // Edit Invoice (Full Edit)
  const handleSaveInvoice = async () => {
    if (!editInvoiceDialog.invoice) return;
    const reason = prompt('Enter reason for changes:');
    if (!reason || reason.length < 5) {
      toast.error('Reason is required');
      return;
    }
    try {
      await axiosInstance.put(`/superadmin/invoices/${editInvoiceDialog.invoice.id}?reason=${encodeURIComponent(reason)}`, editInvoiceDialog.invoice);
      toast.success('Invoice updated');
      setEditInvoiceDialog({ open: false, invoice: null });
      loadInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update invoice');
    }
  };

  // Fix Unknown Journal Entry
  const handleFixJournalEntry = async () => {
    if (!editJournalDialog.entry) return;
    const reason = prompt('Enter reason for changes:');
    if (!reason || reason.length < 5) {
      toast.error('Reason is required');
      return;
    }
    try {
      await axiosInstance.put(`/superadmin/journal-entries/${editJournalDialog.entry.id}?reason=${encodeURIComponent(reason)}`, {
        description: editJournalDialog.entry.description
      });
      toast.success('Journal entry updated');
      setEditJournalDialog({ open: false, entry: null });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update journal entry');
    }
  };

  // Session Data Entry Functions
  const loadSessionData = async (sessionId) => {
    setLoading(true);
    try {
      // Load session with participants
      const sessionRes = await axiosInstance.get(`/sessions/${sessionId}`);
      setSelectedSessionForData(sessionRes.data);
      
      // Load participants for this session
      const participantsRes = await axiosInstance.get(`/sessions/${sessionId}/participants`);
      setSessionParticipants(participantsRes.data.participants || participantsRes.data || []);
      
      // Load tests for this session's program
      if (sessionRes.data.program_id) {
        try {
          const testsRes = await axiosInstance.get(`/tests/program/${sessionRes.data.program_id}`);
          setSessionTests(testsRes.data || []);
        } catch {
          setSessionTests([]);
        }
      }
      
      // Initialize attendance data from existing
      const attData = {};
      (participantsRes.data.participants || participantsRes.data || []).forEach(p => {
        attData[p.id] = {
          present: p.attendance?.present ?? true,
          day1: p.attendance?.day1 ?? true,
          day2: p.attendance?.day2 ?? true
        };
      });
      setAttendanceData(attData);
      
      // Initialize test results data
      const testData = {};
      (participantsRes.data.participants || participantsRes.data || []).forEach(p => {
        testData[p.id] = {
          pre_test_score: p.pre_test_score || p.test_results?.find(t => t.test_type === 'pre')?.score || '',
          post_test_score: p.post_test_score || p.test_results?.find(t => t.test_type === 'post')?.score || ''
        };
      });
      setTestResultsData(testData);
      
      toast.success('Session data loaded');
    } catch (error) {
      toast.error('Failed to load session data');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const saveAttendance = async (participantId) => {
    try {
      const data = attendanceData[participantId];
      await axiosInstance.post(`/sessions/${selectedSessionForData.id}/participants/${participantId}/attendance`, data);
      toast.success('Attendance saved');
    } catch (error) {
      toast.error('Failed to save attendance');
    }
  };

  const saveTestResult = async (participantId, testType) => {
    const score = parseFloat(testResultsData[participantId]?.[`${testType}_test_score`]);
    if (isNaN(score) || score < 0 || score > 100) {
      toast.error('Score must be between 0 and 100');
      return;
    }
    
    try {
      // Get test for this program and type
      const test = sessionTests.find(t => t.test_type === testType || t.test_type === `${testType}_test`);
      if (!test) {
        toast.error(`No ${testType} test found for this program`);
        return;
      }
      
      // Use super admin submit endpoint
      await axiosInstance.post('/tests/super-admin-submit', {
        test_id: test.id,
        session_id: selectedSessionForData.id,
        participant_id: participantId,
        score: score,
        passed: score >= 70
      });
      toast.success(`${testType.toUpperCase()} test result saved`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save test result');
    }
  };

  const saveBulkAttendance = async () => {
    setLoading(true);
    try {
      for (const participantId of Object.keys(attendanceData)) {
        await axiosInstance.post(`/sessions/${selectedSessionForData.id}/participants/${participantId}/attendance`, attendanceData[participantId]);
      }
      toast.success('All attendance saved');
    } catch (error) {
      toast.error('Failed to save attendance');
    } finally {
      setLoading(false);
    }
  };

  const formatMoney = (amount) => {
    return new Intl.NumberFormat('en-MY', { style: 'currency', currency: 'MYR' }).format(amount || 0);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-MY');
  };

  const roles = ['admin', 'super_admin', 'finance', 'marketing', 'trainer', 'coordinator', 'pic_supervisor', 'participant'];

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/admin')}
              className="flex items-center gap-2"
              data-testid="back-to-admin-button"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Admin
            </Button>
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-red-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Super Admin Portal</h1>
                <Badge className="bg-red-600 text-xs">Restricted Access</Badge>
              </div>
            </div>
          </div>
          <Button
            data-testid="superadmin-logout-button"
            onClick={handleLogout}
            variant="outline"
            className="flex items-center gap-2"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </Button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="dashboard" className="flex items-center gap-1">
            <BarChart3 className="w-4 h-4" /> Dashboard
          </TabsTrigger>
          <TabsTrigger value="users" className="flex items-center gap-1" onClick={loadUsers}>
            <Users className="w-4 h-4" /> Users
          </TabsTrigger>
          <TabsTrigger value="sessions" className="flex items-center gap-1" onClick={loadSessions}>
            <Activity className="w-4 h-4" /> Sessions
          </TabsTrigger>
          <TabsTrigger value="invoices" className="flex items-center gap-1" onClick={loadInvoices}>
            <FileText className="w-4 h-4" /> Invoices
          </TabsTrigger>
          <TabsTrigger value="quotations" className="flex items-center gap-1" onClick={loadQuotations}>
            <FileSpreadsheet className="w-4 h-4" /> Quotations
          </TabsTrigger>
          <TabsTrigger value="session-data" className="flex items-center gap-1">
            <Activity className="w-4 h-4" /> Session Data
          </TabsTrigger>
          <TabsTrigger value="reversals" className="flex items-center gap-1" onClick={loadReversalPayments}>
            <RefreshCw className="w-4 h-4" /> Reversals
          </TabsTrigger>
          <TabsTrigger value="audit" className="flex items-center gap-1" onClick={loadAuditLog}>
            <Clock className="w-4 h-4" /> Audit Log
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-1" onClick={loadSettings}>
            <Settings className="w-4 h-4" /> Settings
          </TabsTrigger>
          <TabsTrigger value="export" className="flex items-center gap-1">
            <Download className="w-4 h-4" /> Export
          </TabsTrigger>
        </TabsList>

        {/* Dashboard Tab */}
        <TabsContent value="dashboard">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : stats ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-500">Total Users</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{stats.users?.total || 0}</div>
                  <div className="text-xs text-gray-500 mt-2">
                    {Object.entries(stats.users?.by_role || {}).map(([role, count]) => (
                      <span key={role} className="mr-2">{role}: {count}</span>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-500">Sessions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{stats.sessions?.total || 0}</div>
                  <div className="text-xs text-gray-500 mt-2">
                    <Badge className="mr-1 bg-green-100 text-green-700">{stats.sessions?.completed || 0} Completed</Badge>
                    <Badge className="bg-yellow-100 text-yellow-700">{stats.sessions?.ongoing || 0} Ongoing</Badge>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-500">Invoices</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{stats.invoices?.total || 0}</div>
                  <div className="text-xs text-gray-500 mt-2">
                    <Badge className="mr-1 bg-blue-100 text-blue-700">{stats.invoices?.issued || 0} Issued</Badge>
                    <Badge className="bg-green-100 text-green-700">{stats.invoices?.paid || 0} Paid</Badge>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-500">Quotations</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{stats.quotations?.total || 0}</div>
                  <div className="text-xs text-gray-500 mt-2">
                    <Badge className="mr-1 bg-green-100 text-green-700">{stats.quotations?.accepted || 0} Accepted</Badge>
                    <Badge className="bg-blue-100 text-blue-700">{stats.quotations?.sent || 0} Sent</Badge>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-500">Companies</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{stats.companies || 0}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-500">Programs</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{stats.programs || 0}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-500">Payments</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{stats.payments || 0}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-gray-500">Journal Entries</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{stats.journal_entries || 0}</div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="py-12 text-center">
                <AlertTriangle className="w-12 h-12 mx-auto text-yellow-500 mb-4" />
                <h3 className="text-lg font-semibold">Access Denied</h3>
                <p className="text-gray-500">You need Super Admin privileges to access this portal.</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Users Tab */}
        <TabsContent value="users">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>User Management</CardTitle>
                <div className="flex gap-2">
                  <Input 
                    placeholder="Search users..."
                    value={userSearch}
                    onChange={(e) => setUserSearch(e.target.value)}
                    className="w-64"
                  />
                  <Button onClick={loadUsers}>
                    <Search className="w-4 h-4 mr-1" /> Search
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map(user => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">{user.full_name}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <Select 
                          value={user.role} 
                          onValueChange={(value) => handleChangeUserRole(user.id, value)}
                        >
                          <SelectTrigger className="w-32">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {roles.map(role => (
                              <SelectItem key={role} value={role}>{role}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <Badge className={user.is_active !== false ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                          {user.is_active !== false ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDate(user.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setEditUserDialog({ open: true, user: {...user} })} title="Edit User">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleToggleUserActive(user.id)} title={user.is_active !== false ? 'Lock User' : 'Unlock User'}>
                            {user.is_active !== false ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleResetPassword(user.id)} title="Reset Password">
                            <UserCog className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sessions Tab */}
        <TabsContent value="sessions">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Session Management</CardTitle>
                <div className="flex gap-2">
                  <Select value={sessionFilter.status || "all"} onValueChange={(v) => setSessionFilter(prev => ({ ...prev, status: v === "all" ? "" : v }))}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="All Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="ongoing">Ongoing</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="archived">Archived</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button onClick={loadSessions}>
                    <RefreshCw className="w-4 h-4 mr-1" /> Refresh
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Session Name</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead>Start Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Invoice</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map(session => (
                    <TableRow key={session.id}>
                      <TableCell className="font-medium">{session.name}</TableCell>
                      <TableCell>{session.company_name}</TableCell>
                      <TableCell>{session.start_date}</TableCell>
                      <TableCell>
                        <Badge className={
                          session.completion_status === 'completed' ? 'bg-green-100 text-green-700' :
                          session.completion_status === 'ongoing' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-gray-100 text-gray-700'
                        }>
                          {session.completion_status || 'ongoing'}
                        </Badge>
                      </TableCell>
                      <TableCell>{session.invoice_number || '-'}</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setEditSessionDialog({ open: true, session: {...session} })} title="Edit Session">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Select 
                            value="select_action" 
                            onValueChange={(value) => {
                              if (value !== "select_action") {
                                handleFixSessionStatus(session.id, value);
                              }
                            }}
                          >
                            <SelectTrigger className="w-28">
                              <SelectValue placeholder="Status" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="select_action">Fix Status</SelectItem>
                              <SelectItem value="ongoing">Set Ongoing</SelectItem>
                              <SelectItem value="completed">Set Completed</SelectItem>
                              <SelectItem value="archived">Set Archived</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Invoices Tab */}
        <TabsContent value="invoices">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Invoice Management</CardTitle>
                <div className="flex gap-2">
                  <Select value={invoiceFilter.status || "all"} onValueChange={(v) => setInvoiceFilter(prev => ({ ...prev, status: v === "all" ? "" : v }))}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="All Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="auto_draft">Draft</SelectItem>
                      <SelectItem value="issued">Issued</SelectItem>
                      <SelectItem value="partial">Partial</SelectItem>
                      <SelectItem value="paid">Paid</SelectItem>
                      <SelectItem value="voided">Voided</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button onClick={loadInvoices}>
                    <RefreshCw className="w-4 h-4 mr-1" /> Refresh
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Invoice #</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoices.map(invoice => (
                    <TableRow key={invoice.id}>
                      <TableCell className="font-mono">{invoice.invoice_number}</TableCell>
                      <TableCell>{invoice.bill_to_name || invoice.company_name}</TableCell>
                      <TableCell>{formatMoney(invoice.total_amount)}</TableCell>
                      <TableCell>
                        <Badge className={
                          invoice.status === 'paid' ? 'bg-green-100 text-green-700' :
                          invoice.status === 'issued' ? 'bg-blue-100 text-blue-700' :
                          invoice.status === 'voided' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-700'
                        }>
                          {invoice.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDate(invoice.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => setEditInvoiceDialog({ open: true, invoice: {...invoice} })} title="Edit Invoice">
                            <Edit className="w-4 h-4" />
                          </Button>
                          {invoice.status !== 'voided' && (
                            <Button variant="ghost" size="sm" onClick={() => handleVoidInvoice(invoice.id)} title="Void Invoice">
                              <XCircle className="w-4 h-4 text-red-500" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Quotations Tab */}
        <TabsContent value="quotations">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Quotation Management</CardTitle>
                <Button onClick={loadQuotations}>
                  <RefreshCw className="w-4 h-4 mr-1" /> Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Quotation #</TableHead>
                    <TableHead>Client</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {quotations.map(quote => (
                    <TableRow key={quote.id}>
                      <TableCell className="font-mono">{quote.quotation_number}</TableCell>
                      <TableCell>{quote.client_name || '-'}</TableCell>
                      <TableCell>{formatMoney(quote.total_amount)}</TableCell>
                      <TableCell>
                        <Badge className={
                          quote.status === 'accepted' ? 'bg-green-100 text-green-700' :
                          quote.status === 'sent' ? 'bg-blue-100 text-blue-700' :
                          quote.status === 'draft' ? 'bg-gray-100 text-gray-700' :
                          'bg-yellow-100 text-yellow-700'
                        }>
                          {quote.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatDate(quote.created_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Session Data Entry Tab */}
        <TabsContent value="session-data">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  Session Data Entry (Attendance, Test Results, Feedback)
                </CardTitle>
              </div>
              <CardDescription>
                Select a session to enter attendance, pre/post test results, and feedback data
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Session Selector */}
              <div className="mb-6">
                <Label className="mb-2 block">Select Session</Label>
                <div className="flex gap-2">
                  <Select 
                    value={selectedSessionForData?.id || ''} 
                    onValueChange={(sessionId) => sessionId && loadSessionData(sessionId)}
                  >
                    <SelectTrigger className="w-full max-w-md">
                      <SelectValue placeholder="Choose a session..." />
                    </SelectTrigger>
                    <SelectContent>
                      {sessions.map(session => (
                        <SelectItem key={session.id} value={session.id}>
                          {session.name} - {session.company_name} ({formatDate(session.start_date)})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button variant="outline" onClick={loadSessions}>
                    <RefreshCw className="w-4 h-4 mr-1" /> Load Sessions
                  </Button>
                </div>
              </div>

              {/* Session Data Entry Form */}
              {selectedSessionForData && (
                <div className="space-y-6">
                  {/* Session Info */}
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-lg">{selectedSessionForData.name}</h3>
                    <p className="text-sm text-gray-600">
                      Company: {selectedSessionForData.company_name} | 
                      Date: {formatDate(selectedSessionForData.start_date)} | 
                      Participants: {sessionParticipants.length}
                    </p>
                  </div>

                  {/* Attendance & Test Results Table */}
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <h4 className="font-semibold">Participant Data</h4>
                      <Button onClick={saveBulkAttendance} disabled={loading}>
                        {loading ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-1" />}
                        Save All Attendance
                      </Button>
                    </div>
                    
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Participant Name</TableHead>
                          <TableHead>IC Number</TableHead>
                          <TableHead className="text-center">Attendance</TableHead>
                          <TableHead className="text-center">Pre-Test Score</TableHead>
                          <TableHead className="text-center">Post-Test Score</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sessionParticipants.map(participant => (
                          <TableRow key={participant.id}>
                            <TableCell className="font-medium">{participant.full_name}</TableCell>
                            <TableCell>{participant.ic_number || '-'}</TableCell>
                            <TableCell className="text-center">
                              <input
                                type="checkbox"
                                checked={attendanceData[participant.id]?.present ?? true}
                                onChange={(e) => setAttendanceData(prev => ({
                                  ...prev,
                                  [participant.id]: { ...prev[participant.id], present: e.target.checked }
                                }))}
                                className="w-5 h-5"
                              />
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <Input
                                  type="number"
                                  min="0"
                                  max="100"
                                  placeholder="0-100"
                                  className="w-20 text-center"
                                  value={testResultsData[participant.id]?.pre_test_score || ''}
                                  onChange={(e) => setTestResultsData(prev => ({
                                    ...prev,
                                    [participant.id]: { ...prev[participant.id], pre_test_score: e.target.value }
                                  }))}
                                />
                                <Button 
                                  size="sm" 
                                  variant="outline"
                                  onClick={() => saveTestResult(participant.id, 'pre')}
                                >
                                  Save
                                </Button>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                <Input
                                  type="number"
                                  min="0"
                                  max="100"
                                  placeholder="0-100"
                                  className="w-20 text-center"
                                  value={testResultsData[participant.id]?.post_test_score || ''}
                                  onChange={(e) => setTestResultsData(prev => ({
                                    ...prev,
                                    [participant.id]: { ...prev[participant.id], post_test_score: e.target.value }
                                  }))}
                                />
                                <Button 
                                  size="sm" 
                                  variant="outline"
                                  onClick={() => saveTestResult(participant.id, 'post')}
                                >
                                  Save
                                </Button>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Button 
                                size="sm" 
                                variant="ghost"
                                onClick={() => saveAttendance(participant.id)}
                              >
                                <CheckCircle className="w-4 h-4 text-green-600" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {sessionParticipants.length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                      No participants found for this session. Add participants first.
                    </div>
                  )}
                </div>
              )}

              {!selectedSessionForData && (
                <div className="text-center py-12 text-gray-500">
                  <Activity className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p>Select a session above to enter attendance, test results, and feedback data.</p>
                  <p className="text-sm mt-2">Click "Load Sessions" first if the dropdown is empty.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Log Tab */}
        {/* Payment Reversals Tab */}
        <TabsContent value="reversals">
          <div className="space-y-4">
            {/* Sub-tabs: Payments | Invoices | Quotations */}
            <div className="flex gap-2 border-b pb-2">
              <Button
                variant={reversalSubTab === 'payments' ? 'default' : 'outline'}
                size="sm"
                onClick={() => { setReversalSubTab('payments'); loadReversalPayments(); }}
                data-testid="reversal-subtab-payments"
                className={reversalSubTab === 'payments' ? 'bg-red-600 hover:bg-red-700' : ''}
              >
                Payments
              </Button>
              <Button
                variant={reversalSubTab === 'invoices' ? 'default' : 'outline'}
                size="sm"
                onClick={() => { setReversalSubTab('invoices'); loadInvoiceReversals(); }}
                data-testid="reversal-subtab-invoices"
                className={reversalSubTab === 'invoices' ? 'bg-red-600 hover:bg-red-700' : ''}
              >
                Invoices
              </Button>
              <Button
                variant={reversalSubTab === 'quotations' ? 'default' : 'outline'}
                size="sm"
                onClick={() => { setReversalSubTab('quotations'); loadQuotationReversals(); }}
                data-testid="reversal-subtab-quotations"
                className={reversalSubTab === 'quotations' ? 'bg-red-600 hover:bg-red-700' : ''}
              >
                Quotations
              </Button>
            </div>

          {reversalSubTab === 'payments' && (
          <div className="space-y-6">
            {/* Step indicator */}
            {reversalStep > 0 && (
              <div className="flex items-center gap-2 mb-4">
                <Button variant="outline" size="sm" onClick={() => { setReversalStep(0); setReversalPreview(null); setReversalResult(null); }}>
                  <ArrowLeft className="w-4 h-4 mr-1" /> Back to Payments
                </Button>
                <div className="flex items-center gap-1 text-sm text-gray-500 ml-4">
                  <span className={`px-2 py-1 rounded ${reversalStep >= 1 ? 'bg-red-100 text-red-800 font-semibold' : 'bg-gray-100'}`}>1. Review</span>
                  <span className="text-gray-300">&rarr;</span>
                  <span className={`px-2 py-1 rounded ${reversalStep >= 2 ? 'bg-red-100 text-red-800 font-semibold' : 'bg-gray-100'}`}>2. Reason</span>
                  <span className="text-gray-300">&rarr;</span>
                  <span className={`px-2 py-1 rounded ${reversalStep >= 3 ? 'bg-green-100 text-green-800 font-semibold' : 'bg-gray-100'}`}>3. Complete</span>
                </div>
              </div>
            )}

            {/* Step 0: Payment List */}
            {reversalStep === 0 && (
              <>
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between flex-wrap gap-3">
                      <div>
                        <CardTitle className="flex items-center gap-2">
                          <RefreshCw className="w-5 h-5 text-red-600" />
                          Payment Reversal
                        </CardTitle>
                        <CardDescription>Select a payment to reverse. This will void all linked credit notes and journal entries.</CardDescription>
                      </div>
                      <div className="flex gap-2">
                        <Input
                          placeholder="Search by company, receipt..."
                          value={reversalSearch}
                          onChange={(e) => setReversalSearch(e.target.value)}
                          className="w-64"
                          data-testid="reversal-search"
                        />
                        <Button variant="outline" onClick={loadReversalPayments}>
                          <RefreshCw className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {loading ? (
                      <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
                    ) : (
                      <div className="overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Receipt #</TableHead>
                              <TableHead>Company</TableHead>
                              <TableHead>Invoice</TableHead>
                              <TableHead className="text-right">Amount (RM)</TableHead>
                              <TableHead>Date</TableHead>
                              <TableHead>Method</TableHead>
                              <TableHead className="text-center">Action</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {reversalPayments
                              .filter(p => {
                                if (!reversalSearch) return true;
                                const s = reversalSearch.toLowerCase();
                                return (p.company_name || '').toLowerCase().includes(s) ||
                                  (p.receipt_number || '').toLowerCase().includes(s) ||
                                  (p.invoice_number || '').toLowerCase().includes(s) ||
                                  (p.payment_method || '').toLowerCase().includes(s);
                              })
                              .map(payment => (
                              <TableRow key={payment.id}>
                                <TableCell className="font-mono text-sm">{payment.receipt_number || '-'}</TableCell>
                                <TableCell className="max-w-[200px] truncate">{payment.company_name || '-'}</TableCell>
                                <TableCell className="font-mono text-sm">{payment.invoice_number || '-'}</TableCell>
                                <TableCell className="text-right font-semibold">{(payment.amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                                <TableCell className="text-sm">{payment.payment_date || '-'}</TableCell>
                                <TableCell className="text-sm">{payment.payment_method || '-'}</TableCell>
                                <TableCell className="text-center">
                                  <Button
                                    size="sm"
                                    variant="destructive"
                                    onClick={() => handlePreviewReversal(payment.id)}
                                    data-testid={`reverse-btn-${payment.id}`}
                                  >
                                    <AlertTriangle className="w-3 h-3 mr-1" /> Reverse
                                  </Button>
                                </TableCell>
                              </TableRow>
                            ))}
                            {reversalPayments.length === 0 && (
                              <TableRow>
                                <TableCell colSpan={7} className="text-center py-8 text-gray-400">No active payments found</TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Reversal History */}
                {reversalHistory.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Clock className="w-4 h-4" /> Reversal History
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Date</TableHead>
                            <TableHead>Company</TableHead>
                            <TableHead>Receipt #</TableHead>
                            <TableHead className="text-right">Amount</TableHead>
                            <TableHead>Reversed By</TableHead>
                            <TableHead>Reason</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {reversalHistory.map(r => (
                            <TableRow key={r.id} className="text-sm">
                              <TableCell>{r.reversed_at ? new Date(r.reversed_at).toLocaleDateString('en-MY') : '-'}</TableCell>
                              <TableCell>{r.company_name || '-'}</TableCell>
                              <TableCell className="font-mono">{r.receipt_number || '-'}</TableCell>
                              <TableCell className="text-right">RM {(r.payment_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                              <TableCell>{r.reversed_by_name || '-'}</TableCell>
                              <TableCell className="max-w-[250px] truncate">{r.reason || '-'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                )}
              </>
            )}

            {/* Step 1: Preview */}
            {reversalStep === 1 && reversalPreview && (
              <div className="space-y-4">
                <Card className="border-red-200 bg-red-50/30">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-red-800">
                      <AlertTriangle className="w-5 h-5" />
                      Reversal Impact Preview
                    </CardTitle>
                    <CardDescription className="text-red-700">Review everything that will be affected before proceeding.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Payment Info */}
                    <div>
                      <h4 className="font-semibold text-sm text-gray-700 mb-2 uppercase tracking-wide">Payment to Reverse</h4>
                      <div className="bg-white rounded-lg p-4 border grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <p className="text-xs text-gray-500">Receipt #</p>
                          <p className="font-mono font-semibold">{reversalPreview.payment.receipt_number || '-'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Amount</p>
                          <p className="font-bold text-lg text-red-700">RM {(reversalPreview.payment.amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Date</p>
                          <p className="font-medium">{reversalPreview.payment.payment_date || '-'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Method</p>
                          <p className="font-medium">{reversalPreview.payment.payment_method || '-'}</p>
                        </div>
                      </div>
                    </div>

                    {/* Invoice Info */}
                    {reversalPreview.invoice && (
                      <div>
                        <h4 className="font-semibold text-sm text-gray-700 mb-2 uppercase tracking-wide">Linked Invoice</h4>
                        <div className="bg-white rounded-lg p-4 border grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div>
                            <p className="text-xs text-gray-500">Invoice #</p>
                            <p className="font-mono font-semibold">{reversalPreview.invoice.invoice_number}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Company</p>
                            <p className="font-medium">{reversalPreview.invoice.company_name}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Total Amount</p>
                            <p className="font-medium">RM {(reversalPreview.invoice.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500">Status Change</p>
                            <p className="font-bold">{reversalPreview.summary.invoice_status_change}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Credit Notes to Void */}
                    {reversalPreview.linked_credit_notes.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-sm text-gray-700 mb-2 uppercase tracking-wide">
                          Credit Notes to be Voided ({reversalPreview.linked_credit_notes.length})
                        </h4>
                        <div className="bg-white rounded-lg border overflow-hidden">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>CN #</TableHead>
                                <TableHead className="text-right">Amount</TableHead>
                                <TableHead>%</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Reason</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {reversalPreview.linked_credit_notes.map(cn => (
                                <TableRow key={cn.id}>
                                  <TableCell className="font-mono text-sm">{cn.cn_number}</TableCell>
                                  <TableCell className="text-right font-semibold">RM {(cn.amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                                  <TableCell>{cn.percentage}%</TableCell>
                                  <TableCell><Badge variant="outline">{cn.status}</Badge></TableCell>
                                  <TableCell className="text-sm">{cn.reason || '-'}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}

                    {/* Journal Entries to Void */}
                    {reversalPreview.linked_journal_entries.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-sm text-gray-700 mb-2 uppercase tracking-wide">
                          Journal Entries to be Voided ({reversalPreview.linked_journal_entries.length})
                        </h4>
                        <div className="bg-white rounded-lg border overflow-hidden">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Journal #</TableHead>
                                <TableHead>Description</TableHead>
                                <TableHead className="text-right">Amount</TableHead>
                                <TableHead>Status</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {reversalPreview.linked_journal_entries.map(je => (
                                <TableRow key={je.id}>
                                  <TableCell className="font-mono text-sm">{je.journal_no}</TableCell>
                                  <TableCell className="text-sm max-w-[300px] truncate">{je.description}</TableCell>
                                  <TableCell className="text-right">RM {(je.total_debit || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                                  <TableCell><Badge variant="outline">{je.status}</Badge></TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}

                    {/* Summary */}
                    <div className="bg-red-100 border border-red-300 rounded-lg p-4">
                      <h4 className="font-bold text-red-900 mb-2">Summary of Changes</h4>
                      <ul className="text-sm text-red-800 space-y-1">
                        <li>Payment of <strong>RM {(reversalPreview.summary.payment_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</strong> will be marked as <strong>REVERSED</strong></li>
                        <li><strong>{reversalPreview.summary.credit_notes_to_void}</strong> credit note(s) totalling <strong>RM {(reversalPreview.summary.credit_notes_total || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</strong> will be <strong>VOIDED</strong></li>
                        <li><strong>{reversalPreview.summary.journals_to_void}</strong> journal entry/entries will be <strong>VOIDED</strong></li>
                        <li>Invoice status: <strong>{reversalPreview.summary.invoice_status_change}</strong></li>
                      </ul>
                    </div>

                    <div className="flex justify-end gap-3">
                      <Button variant="outline" onClick={() => { setReversalStep(0); setReversalPreview(null); }}>
                        Cancel
                      </Button>
                      <Button
                        className="bg-red-600 hover:bg-red-700"
                        onClick={() => setReversalStep(2)}
                        data-testid="proceed-to-reason"
                      >
                        Proceed to Enter Reason
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Step 2: Reason & Confirm */}
            {reversalStep === 2 && reversalPreview && (
              <Card className="border-red-200">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-red-800">
                    <Shield className="w-5 h-5" />
                    Confirm Payment Reversal
                  </CardTitle>
                  <CardDescription>
                    Reversing payment {reversalPreview.payment.receipt_number} — RM {(reversalPreview.payment.amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}
                    {reversalPreview.invoice && ` for ${reversalPreview.invoice.company_name}`}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-sm font-semibold">
                      Reason for Reversal <span className="text-red-500">*</span>
                    </Label>
                    <p className="text-xs text-gray-500 mb-2">Minimum 10 characters. This will be permanently recorded in the audit log.</p>
                    <Textarea
                      value={reversalReason}
                      onChange={(e) => setReversalReason(e.target.value)}
                      placeholder="E.g., HRDF only approved RM 1,800 instead of RM 3,000. Need to reverse the RM 3K payment and re-record correct amount."
                      rows={4}
                      className="w-full"
                      data-testid="reversal-reason-input"
                    />
                    <p className="text-xs text-gray-400 mt-1">{reversalReason.length}/10 characters minimum</p>
                  </div>

                  <div className="bg-amber-50 border border-amber-300 rounded-lg p-4">
                    <p className="text-amber-900 text-sm font-semibold flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      This action cannot be undone
                    </p>
                    <p className="text-amber-800 text-xs mt-1">
                      The payment, {reversalPreview.summary.credit_notes_to_void} credit note(s), and {reversalPreview.summary.journals_to_void} journal entry/entries will be voided permanently.
                    </p>
                  </div>

                  <div className="flex justify-end gap-3">
                    <Button variant="outline" onClick={() => setReversalStep(1)}>
                      Back to Review
                    </Button>
                    <Button
                      className="bg-red-600 hover:bg-red-700"
                      onClick={handleExecuteReversal}
                      disabled={reversalReason.length < 10 || reversalExecuting}
                      data-testid="confirm-reversal-btn"
                    >
                      {reversalExecuting ? (
                        <><Loader2 className="w-4 h-4 mr-1 animate-spin" /> Executing...</>
                      ) : (
                        <><AlertTriangle className="w-4 h-4 mr-1" /> Execute Reversal</>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Step 3: Success */}
            {reversalStep === 3 && reversalResult && (
              <Card className="border-green-200 bg-green-50/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-green-800">
                    <CheckCircle className="w-5 h-5" />
                    Reversal Complete
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="bg-white rounded-lg p-4 border space-y-3">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                      <div>
                        <p className="text-xs text-gray-500">Payment Reversed</p>
                        <p className="font-bold text-lg text-red-700">{reversalResult.summary.payment_reversed}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Credit Notes Voided</p>
                        <p className="font-bold text-lg">{reversalResult.summary.credit_notes_voided}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Journals Voided</p>
                        <p className="font-bold text-lg">{reversalResult.summary.journals_voided}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Invoice Status</p>
                        <p className="font-bold text-lg">{reversalResult.summary.invoice_status}</p>
                      </div>
                    </div>
                    <hr />
                    <div>
                      <p className="text-sm font-semibold text-gray-700 mb-2">Actions Taken:</p>
                      <ul className="text-sm text-gray-600 space-y-1">
                        {reversalResult.actions_taken.map((action, i) => (
                          <li key={i} className="flex items-center gap-2">
                            <CheckCircle className="w-3 h-3 text-green-600 flex-shrink-0" />
                            {action}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="text-xs text-gray-400 mt-2">Reversal ID: {reversalResult.reversal_id}</div>
                  </div>
                  <div className="flex justify-end">
                    <Button onClick={() => { setReversalStep(0); setReversalPreview(null); setReversalResult(null); }}>
                      Back to Payments
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
          )}

          {reversalSubTab === 'invoices' && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <RefreshCw className="w-5 h-5 text-red-600" /> Invoice Reversal
                      </CardTitle>
                      <CardDescription>Revert an issued invoice back to draft. Cannot reverse if active payments exist.</CardDescription>
                    </div>
                    <Button variant="outline" onClick={loadInvoiceReversals}><RefreshCw className="w-4 h-4" /></Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {invoicesForReversal.length === 0 ? (
                    <p className="text-center py-6 text-gray-500">No invoices available for reversal.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Invoice #</TableHead>
                            <TableHead>Company</TableHead>
                            <TableHead className="text-right">Amount (RM)</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Active Payments</TableHead>
                            <TableHead className="text-center">Action</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {invoicesForReversal.map(inv => (
                            <TableRow key={inv.id}>
                              <TableCell className="font-mono text-sm">{inv.invoice_number || '-'}</TableCell>
                              <TableCell className="max-w-[200px] truncate">{inv.company_name || inv.bill_to_name || '-'}</TableCell>
                              <TableCell className="text-right font-semibold">{(inv.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                              <TableCell><span className="px-2 py-0.5 text-xs rounded bg-gray-100">{inv.status}</span></TableCell>
                              <TableCell>{inv.active_payment_count > 0 ? <span className="text-amber-700 font-medium">{inv.active_payment_count}</span> : <span className="text-gray-400">0</span>}</TableCell>
                              <TableCell className="text-center">
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  disabled={inv.active_payment_count > 0}
                                  onClick={() => openGenericReverse('invoice', inv)}
                                  data-testid={`reverse-invoice-btn-${inv.id}`}
                                  title={inv.active_payment_count > 0 ? 'Reverse the payment(s) first' : 'Reverse invoice'}
                                >
                                  <AlertTriangle className="w-3 h-3 mr-1" /> Reverse
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>

              {invoiceReversalHistory.length > 0 && (
                <Card>
                  <CardHeader><CardTitle className="text-base">Invoice Reversal History</CardTitle></CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Date</TableHead>
                            <TableHead>Invoice #</TableHead>
                            <TableHead>Company</TableHead>
                            <TableHead className="text-right">Amount (RM)</TableHead>
                            <TableHead>Reversed By</TableHead>
                            <TableHead>Reason</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {invoiceReversalHistory.map(r => (
                            <TableRow key={r.id}>
                              <TableCell className="text-sm">{(r.reversed_at || '').slice(0, 16).replace('T', ' ')}</TableCell>
                              <TableCell className="font-mono text-sm">{r.invoice_number || '-'}</TableCell>
                              <TableCell className="max-w-[200px] truncate">{r.company_name || '-'}</TableCell>
                              <TableCell className="text-right">{(r.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                              <TableCell>{r.reversed_by_name || '-'}</TableCell>
                              <TableCell className="max-w-[300px] truncate text-sm text-gray-600">{r.reason}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {reversalSubTab === 'quotations' && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <RefreshCw className="w-5 h-5 text-red-600" /> Quotation Reversal
                      </CardTitle>
                      <CardDescription>Undo an accepted quotation and delete its draft session. Cannot reverse if invoice or participants exist on the linked session.</CardDescription>
                    </div>
                    <Button variant="outline" onClick={loadQuotationReversals}><RefreshCw className="w-4 h-4" /></Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {quotationsForReversal.length === 0 ? (
                    <p className="text-center py-6 text-gray-500">No accepted quotations available for reversal.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Quotation #</TableHead>
                            <TableHead>Client</TableHead>
                            <TableHead>Programme</TableHead>
                            <TableHead className="text-right">Amount (RM)</TableHead>
                            <TableHead>Linked Session</TableHead>
                            <TableHead className="text-center">Action</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {quotationsForReversal.map(q => (
                            <TableRow key={q.id}>
                              <TableCell className="font-mono text-sm">{q.quotation_number || '-'}</TableCell>
                              <TableCell className="max-w-[200px] truncate">{q.client_name || '-'}</TableCell>
                              <TableCell className="max-w-[200px] truncate">{q.programme_name || '-'}</TableCell>
                              <TableCell className="text-right font-semibold">{(q.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                              <TableCell className="text-sm text-gray-600">{q.linked_session ? <span className="text-xs">{q.linked_session.name} <span className="text-gray-400">({q.linked_session.status})</span></span> : <span className="text-gray-400">none</span>}</TableCell>
                              <TableCell className="text-center">
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => openGenericReverse('quotation', q)}
                                  data-testid={`reverse-quotation-btn-${q.id}`}
                                >
                                  <AlertTriangle className="w-3 h-3 mr-1" /> Reverse
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>

              {quotationReversalHistory.length > 0 && (
                <Card>
                  <CardHeader><CardTitle className="text-base">Quotation Reversal History</CardTitle></CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Date</TableHead>
                            <TableHead>Quotation #</TableHead>
                            <TableHead>Client</TableHead>
                            <TableHead className="text-right">Amount (RM)</TableHead>
                            <TableHead>Reversed By</TableHead>
                            <TableHead>Reason</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {quotationReversalHistory.map(r => (
                            <TableRow key={r.id}>
                              <TableCell className="text-sm">{(r.reversed_at || '').slice(0, 16).replace('T', ' ')}</TableCell>
                              <TableCell className="font-mono text-sm">{r.quotation_number || '-'}</TableCell>
                              <TableCell className="max-w-[200px] truncate">{r.client_name || '-'}</TableCell>
                              <TableCell className="text-right">{(r.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                              <TableCell>{r.reversed_by_name || '-'}</TableCell>
                              <TableCell className="max-w-[300px] truncate text-sm text-gray-600">{r.reason}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          </div>
        </TabsContent>

        {/* Audit Log Tab */}
        <TabsContent value="audit">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Audit Log</CardTitle>
                <Button onClick={loadAuditLog}>
                  <RefreshCw className="w-4 h-4 mr-1" /> Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Entity</TableHead>
                    <TableHead>Performed By</TableHead>
                    <TableHead>Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditLogs.map(log => (
                    <TableRow key={log.id}>
                      <TableCell className="text-sm">{new Date(log.timestamp).toLocaleString()}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{log.action}</Badge>
                      </TableCell>
                      <TableCell>{log.entity_type}</TableCell>
                      <TableCell>{log.performed_by_name || log.performed_by_email}</TableCell>
                      <TableCell className="max-w-xs truncate">{log.reason || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <AdminFeeSettingsCard />
          <div className="mt-6" />
          <Card>
            <CardHeader>
              <CardTitle>System Settings</CardTitle>
            </CardHeader>
            <CardContent>
              {systemSettings ? (
                <div className="space-y-6">
                  <div>
                    <h3 className="font-semibold mb-2">Company Settings</h3>
                    <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
                      {JSON.stringify(systemSettings.company_settings, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <h3 className="font-semibold mb-2">Accounting Settings</h3>
                    <pre className="bg-gray-100 p-4 rounded text-sm overflow-auto">
                      {JSON.stringify(systemSettings.accounting_settings, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">Click refresh to load settings</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Export Tab */}
        <TabsContent value="export">
          <Card>
            <CardHeader>
              <CardTitle>Data Export</CardTitle>
              <CardDescription>Export system data to CSV format</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {['users', 'sessions', 'invoices', 'payments', 'quotations', 'companies', 'programs', 'journal_entries'].map(collection => (
                  <Button key={collection} variant="outline" onClick={() => handleExport(collection)}>
                    <Download className="w-4 h-4 mr-2" />
                    Export {collection.replace('_', ' ')}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Edit User Dialog */}
      <Dialog open={editUserDialog.open} onOpenChange={(open) => setEditUserDialog({ open, user: open ? editUserDialog.user : null })}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-red-600" />
              Edit User (God Mode)
            </DialogTitle>
            <DialogDescription>
              Full edit access. Changes are logged in audit trail.
            </DialogDescription>
          </DialogHeader>
          {editUserDialog.user && (
            <div className="space-y-4">
              <div>
                <Label>Full Name</Label>
                <Input 
                  value={editUserDialog.user.full_name || ''} 
                  onChange={(e) => setEditUserDialog(prev => ({ ...prev, user: { ...prev.user, full_name: e.target.value }}))}
                />
              </div>
              <div>
                <Label>Email</Label>
                <Input 
                  value={editUserDialog.user.email || ''} 
                  onChange={(e) => setEditUserDialog(prev => ({ ...prev, user: { ...prev.user, email: e.target.value }}))}
                />
              </div>
              <div>
                <Label>Role</Label>
                <Select 
                  value={editUserDialog.user.role || ''} 
                  onValueChange={(value) => setEditUserDialog(prev => ({ ...prev, user: { ...prev.user, role: value }}))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {roles.map(role => (
                      <SelectItem key={role} value={role}>{role}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Phone</Label>
                <Input 
                  value={editUserDialog.user.phone || ''} 
                  onChange={(e) => setEditUserDialog(prev => ({ ...prev, user: { ...prev.user, phone: e.target.value }}))}
                />
              </div>
              <div>
                <Label>IC Number</Label>
                <Input 
                  value={editUserDialog.user.ic_number || ''} 
                  onChange={(e) => setEditUserDialog(prev => ({ ...prev, user: { ...prev.user, ic_number: e.target.value }}))}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditUserDialog({ open: false, user: null })}>Cancel</Button>
            <Button onClick={handleSaveUser} className="bg-red-600 hover:bg-red-700">
              <CheckCircle className="w-4 h-4 mr-1" /> Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Session Dialog */}
      <Dialog open={editSessionDialog.open} onOpenChange={(open) => setEditSessionDialog({ open, session: open ? editSessionDialog.session : null })}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-red-600" />
              Edit Session (God Mode)
            </DialogTitle>
            <DialogDescription>
              Full edit access. Changes are logged in audit trail.
            </DialogDescription>
          </DialogHeader>
          {editSessionDialog.session && (
            <div className="space-y-4">
              <div>
                <Label>Company Name</Label>
                <Input 
                  value={editSessionDialog.session.company_name || ''} 
                  onChange={(e) => setEditSessionDialog(prev => ({ ...prev, session: { ...prev.session, company_name: e.target.value }}))}
                  placeholder="Company name shown in header"
                />
              </div>
              <div>
                <Label>Session Name</Label>
                <Input 
                  value={editSessionDialog.session.name || ''} 
                  onChange={(e) => setEditSessionDialog(prev => ({ ...prev, session: { ...prev.session, name: e.target.value }}))}
                />
              </div>
              <div>
                <Label>Status</Label>
                <Select 
                  value={editSessionDialog.session.status || ''} 
                  onValueChange={(value) => setEditSessionDialog(prev => ({ ...prev, session: { ...prev.session, status: value }}))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ongoing">Ongoing</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="archived">Archived</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Start Date</Label>
                <Input 
                  type="date"
                  value={editSessionDialog.session.start_date?.split('T')[0] || ''} 
                  onChange={(e) => setEditSessionDialog(prev => ({ ...prev, session: { ...prev.session, start_date: e.target.value }}))}
                />
              </div>
              <div>
                <Label>Total Pax</Label>
                <Input 
                  type="number"
                  value={editSessionDialog.session.total_pax || ''} 
                  onChange={(e) => setEditSessionDialog(prev => ({ ...prev, session: { ...prev.session, total_pax: parseInt(e.target.value) || 0 }}))}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditSessionDialog({ open: false, session: null })}>Cancel</Button>
            <Button onClick={handleSaveSession} className="bg-red-600 hover:bg-red-700">
              <CheckCircle className="w-4 h-4 mr-1" /> Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Invoice Dialog */}
      <Dialog open={editInvoiceDialog.open} onOpenChange={(open) => setEditInvoiceDialog({ open, invoice: open ? editInvoiceDialog.invoice : null })}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-red-600" />
              Edit Invoice (God Mode)
            </DialogTitle>
            <DialogDescription>
              Full edit access. Changes are logged in audit trail.
            </DialogDescription>
          </DialogHeader>
          {editInvoiceDialog.invoice && (
            <div className="space-y-4">
              <div>
                <Label>Invoice Number</Label>
                <Input 
                  value={editInvoiceDialog.invoice.invoice_number || ''} 
                  onChange={(e) => setEditInvoiceDialog(prev => ({ ...prev, invoice: { ...prev.invoice, invoice_number: e.target.value }}))}
                />
              </div>
              <div>
                <Label>Bill To Name</Label>
                <Input 
                  value={editInvoiceDialog.invoice.bill_to_name || ''} 
                  onChange={(e) => setEditInvoiceDialog(prev => ({ ...prev, invoice: { ...prev.invoice, bill_to_name: e.target.value }}))}
                />
              </div>
              <div>
                <Label>Status</Label>
                <Select 
                  value={editInvoiceDialog.invoice.status || ''} 
                  onValueChange={(value) => setEditInvoiceDialog(prev => ({ ...prev, invoice: { ...prev.invoice, status: value }}))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto_draft">Draft</SelectItem>
                    <SelectItem value="issued">Issued</SelectItem>
                    <SelectItem value="partial">Partial</SelectItem>
                    <SelectItem value="paid">Paid</SelectItem>
                    <SelectItem value="voided">Voided</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Total Amount (RM)</Label>
                <Input 
                  type="number"
                  step="0.01"
                  value={editInvoiceDialog.invoice.total_amount || ''} 
                  onChange={(e) => setEditInvoiceDialog(prev => ({ ...prev, invoice: { ...prev.invoice, total_amount: parseFloat(e.target.value) || 0 }}))}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditInvoiceDialog({ open: false, invoice: null })}>Cancel</Button>
            <Button onClick={handleSaveInvoice} className="bg-red-600 hover:bg-red-700">
              <CheckCircle className="w-4 h-4 mr-1" /> Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Journal Entry Dialog */}
      <Dialog open={editJournalDialog.open} onOpenChange={(open) => setEditJournalDialog({ open, entry: open ? editJournalDialog.entry : null })}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-red-600" />
              Fix Journal Entry Description
            </DialogTitle>
            <DialogDescription>
              Fix "Unknown" or incorrect descriptions in journal entries.
            </DialogDescription>
          </DialogHeader>
          {editJournalDialog.entry && (
            <div className="space-y-4">
              <div>
                <Label>Journal Number</Label>
                <Input value={editJournalDialog.entry.journal_no || ''} disabled />
              </div>
              <div>
                <Label>Description</Label>
                <Textarea 
                  value={editJournalDialog.entry.description || ''} 
                  onChange={(e) => setEditJournalDialog(prev => ({ ...prev, entry: { ...prev.entry, description: e.target.value }}))}
                  rows={3}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditJournalDialog({ open: false, entry: null })}>Cancel</Button>
            <Button onClick={handleFixJournalEntry} className="bg-red-600 hover:bg-red-700">
              <CheckCircle className="w-4 h-4 mr-1" /> Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Generic Reverse Dialog (Quotation / Invoice) */}
      <Dialog open={genericReverseDialog.open} onOpenChange={(open) => !genericReverseDialog.loading && setGenericReverseDialog(prev => ({ ...prev, open }))}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="w-5 h-5" />
              Reverse {genericReverseDialog.kind === 'quotation' ? 'Quotation' : 'Invoice'}
            </DialogTitle>
            <DialogDescription>
              This action is logged and cannot be undone automatically.
            </DialogDescription>
          </DialogHeader>
          {genericReverseDialog.preview && (
            <div className="space-y-3">
              {genericReverseDialog.kind === 'quotation' ? (
                <div className="bg-gray-50 p-3 rounded text-sm">
                  <p><strong>Quotation:</strong> {genericReverseDialog.preview.quotation?.quotation_number}</p>
                  <p><strong>Client:</strong> {genericReverseDialog.preview.quotation?.client_name}</p>
                  <p><strong>Amount:</strong> RM {(genericReverseDialog.preview.quotation?.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</p>
                  {genericReverseDialog.preview.linked_session && (
                    <p className="mt-1 text-amber-700">
                      Linked session <strong>{genericReverseDialog.preview.linked_session.name}</strong> will be <strong>{genericReverseDialog.preview.linked_session.will_be_deleted ? 'deleted' : 'kept (blocked)'}</strong>.
                    </p>
                  )}
                </div>
              ) : (
                <div className="bg-gray-50 p-3 rounded text-sm">
                  <p><strong>Invoice:</strong> {genericReverseDialog.preview.invoice?.invoice_number}</p>
                  <p><strong>Company:</strong> {genericReverseDialog.preview.invoice?.company_name}</p>
                  <p><strong>Amount:</strong> RM {(genericReverseDialog.preview.invoice?.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</p>
                  <p className="text-amber-700 mt-1">{genericReverseDialog.preview.summary?.journals_to_void} journal entry(s) will be voided.</p>
                </div>
              )}
              {(genericReverseDialog.preview.blockers || []).length > 0 && (
                <div className="bg-red-50 border border-red-200 p-3 rounded text-sm text-red-700">
                  <p className="font-semibold mb-1">Cannot reverse:</p>
                  <ul className="list-disc pl-5">
                    {genericReverseDialog.preview.blockers.map((b, i) => <li key={i}>{b}</li>)}
                  </ul>
                </div>
              )}
              <div>
                <Label>Reason for reversal * <span className="text-xs text-gray-500">(min 10 chars)</span></Label>
                <Textarea
                  value={genericReverseDialog.reason}
                  onChange={(e) => setGenericReverseDialog(prev => ({ ...prev, reason: e.target.value }))}
                  rows={3}
                  placeholder="Explain why this is being reversed (will be permanently logged)"
                  data-testid="generic-reverse-reason"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setGenericReverseDialog({ open: false, kind: null, item: null, preview: null, reason: '', loading: false })} disabled={genericReverseDialog.loading}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={executeGenericReverse}
              disabled={genericReverseDialog.loading || !genericReverseDialog.preview?.can_reverse || genericReverseDialog.reason.length < 10}
              data-testid="generic-reverse-confirm"
            >
              {genericReverseDialog.loading ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <AlertTriangle className="w-4 h-4 mr-1" />}
              Confirm Reversal
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      </main>
    </div>
  );
};

export default SuperAdminPortal;
