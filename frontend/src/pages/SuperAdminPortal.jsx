/**
 * SuperAdminPortal.jsx
 * Comprehensive system administration dashboard
 * Access: Super Admin role only (arjuna@mddrc.com.my or role=super_admin)
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { axiosInstance } from '../App';
import { toast } from 'sonner';
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
                          <Button variant="ghost" size="sm" onClick={() => handleToggleUserActive(user.id)}>
                            {user.is_active !== false ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleResetPassword(user.id)}>
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
                  <Select value={sessionFilter.status} onValueChange={(v) => setSessionFilter(prev => ({ ...prev, status: v }))}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="All Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Status</SelectItem>
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
                        <Select 
                          value="" 
                          onValueChange={(value) => handleFixSessionStatus(session.id, value)}
                        >
                          <SelectTrigger className="w-32">
                            <SelectValue placeholder="Fix Status" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="ongoing">Set Ongoing</SelectItem>
                            <SelectItem value="completed">Set Completed</SelectItem>
                            <SelectItem value="archived">Set Archived</SelectItem>
                          </SelectContent>
                        </Select>
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
                  <Select value={invoiceFilter.status} onValueChange={(v) => setInvoiceFilter(prev => ({ ...prev, status: v }))}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="All Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Status</SelectItem>
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
                        {invoice.status !== 'voided' && (
                          <Button variant="ghost" size="sm" onClick={() => handleVoidInvoice(invoice.id)}>
                            <XCircle className="w-4 h-4 text-red-500" />
                          </Button>
                        )}
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
      </main>
    </div>
  );
};

export default SuperAdminPortal;
