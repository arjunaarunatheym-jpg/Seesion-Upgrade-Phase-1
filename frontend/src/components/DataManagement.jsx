import { useState, useEffect } from "react";
import { axiosInstance } from "../App";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Search, Edit, Trash2, Filter, Database, History, FileText, CreditCard, Settings, Download, Ban, Calendar, Hash, RefreshCw } from "lucide-react";
import SuperAdminPanel from "./SuperAdminPanel";
import { InvoiceManagementTab } from "./data-management/InvoiceManagementTab";
import { CreditNoteManagementTab } from "./data-management/CreditNoteManagementTab";

const DataManagement = ({ user }) => {
  const [activeMainTab, setActiveMainTab] = useState("sessions-data");
  
  // Show Super Admin Panel for arjuna@mddrc.com.my
  const isSuperAdmin = user && user.email === "arjuna@mddrc.com.my";
  const isFinance = user && user.role === "finance";
  const hasFinanceAccess = isSuperAdmin || isFinance || user?.role === "admin";

  // Filter state for Sessions Data
  const [sessions, setSessions] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [programs, setPrograms] = useState([]);
  
  const [filters, setFilters] = useState({
    sessionId: "all",
    companyId: "all",
    programId: "all",
    startDate: "",
    endDate: ""
  });

  // Data state
  const [testResults, setTestResults] = useState([]);
  const [feedback, setFeedback] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [checklists, setChecklists] = useState([]);
  
  const [loading, setLoading] = useState(false);

  // Dialog state
  const [editDialog, setEditDialog] = useState({ open: false, type: null, data: null });
  const [deleteDialog, setDeleteDialog] = useState({ open: false, type: null, id: null });
  const [auditDialog, setAuditDialog] = useState({ open: false, type: null, id: null, logs: [] });

  // Invoice Management State
  const [invoices, setInvoices] = useState([]);
  const [invoiceSearch, setInvoiceSearch] = useState("");
  const [invoiceStatusFilter, setInvoiceStatusFilter] = useState("all");
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [editNumberDialog, setEditNumberDialog] = useState({ open: false, invoice: null });
  const [voidDialog, setVoidDialog] = useState({ open: false, invoice: null });
  const [backdateDialog, setBackdateDialog] = useState({ open: false, invoice: null });
  const [overrideDialog, setOverrideDialog] = useState({ open: false, invoice: null });
  const [editPaidDialog, setEditPaidDialog] = useState({ open: false, invoice: null });
  const [deleteInvoiceDialog, setDeleteInvoiceDialog] = useState({ open: false, invoice: null });

  // Payment Management State
  const [payments, setPayments] = useState([]);
  const [deletePaymentDialog, setDeletePaymentDialog] = useState({ open: false, payment: null });

  // Credit Note Management State
  const [creditNotes, setCreditNotes] = useState([]);
  const [cnSearch, setCnSearch] = useState("");
  const [cnStatusFilter, setCnStatusFilter] = useState("all");
  const [editCnDialog, setEditCnDialog] = useState({ open: false, cn: null });
  const [backdateCnDialog, setBackdateCnDialog] = useState({ open: false, cn: null });
  const [voidCnDialog, setVoidCnDialog] = useState({ open: false, cn: null });
  const [editCnNumberDialog, setEditCnNumberDialog] = useState({ open: false, cn: null });

  // Settings State
  const [sequenceForm, setSequenceForm] = useState({ year: new Date().getFullYear(), month: new Date().getMonth() + 1, sequence: 1, reason: "" });

  // Audit Trail State
  const [auditTrail, setAuditTrail] = useState([]);
  const [auditFilters, setAuditFilters] = useState({ entityType: "all", startDate: "", endDate: "" });

  // Form states
  const [editNumberForm, setEditNumberForm] = useState({ year: 2026, month: 1, sequence: 1, reason: "" });
  const [voidForm, setVoidForm] = useState({ reason: "" });
  const [backdateForm, setBackdateForm] = useState({ newDate: "", reason: "" });
  const [overrideForm, setOverrideForm] = useState({ totalAmount: 0, reason: "" });
  const [editPaidForm, setEditPaidForm] = useState({ billToName: "", billToAddress: "", totalAmount: 0, reason: "" });
  const [deletePaymentForm, setDeletePaymentForm] = useState({ reason: "" });

  // Credit Note Form states
  const [editCnForm, setEditCnForm] = useState({ companyName: "", reason: "", description: "", amount: 0, percentage: 4, editReason: "" });
  const [backdateCnForm, setBackdateCnForm] = useState({ newDate: "", reason: "" });
  const [voidCnForm, setVoidCnForm] = useState({ reason: "" });
  const [editCnNumberForm, setEditCnNumberForm] = useState({ year: 2026, month: 1, sequence: 1, reason: "" });

  useEffect(() => {
    loadFiltersData();
  }, []);

  useEffect(() => {
    if (activeMainTab === "invoice-management" && hasFinanceAccess) {
      loadInvoices();
    } else if (activeMainTab === "payment-management" && hasFinanceAccess) {
      loadPayments();
    } else if (activeMainTab === "creditnote-management" && hasFinanceAccess) {
      loadCreditNotes();
    } else if (activeMainTab === "audit-trail" && hasFinanceAccess) {
      loadAuditTrail();
    }
  }, [activeMainTab]);

  const loadFiltersData = async () => {
    try {
      const [sessionsRes, companiesRes, programsRes] = await Promise.all([
        axiosInstance.get("/sessions"),
        axiosInstance.get("/companies"),
        axiosInstance.get("/programs")
      ]);
      setSessions(sessionsRes.data);
      setCompanies(companiesRes.data);
      setPrograms(programsRes.data);
    } catch (error) {
      console.error("Failed to load filter data:", error);
    }
  };

  const loadInvoices = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (invoiceStatusFilter && invoiceStatusFilter !== "all") params.append("status", invoiceStatusFilter);
      if (invoiceSearch) params.append("search", invoiceSearch);
      
      const response = await axiosInstance.get(`/finance/admin/invoices?${params}`);
      setInvoices(response.data);
    } catch (error) {
      toast.error("Failed to load invoices");
    } finally {
      setLoading(false);
    }
  };

  const loadPayments = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get("/finance/admin/payments");
      setPayments(response.data);
    } catch (error) {
      toast.error("Failed to load payments");
    } finally {
      setLoading(false);
    }
  };

  const loadCreditNotes = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get("/finance/credit-notes");
      let filtered = response.data;
      if (cnSearch) {
        const search = cnSearch.toLowerCase();
        filtered = filtered.filter(cn => 
          cn.cn_number?.toLowerCase().includes(search) ||
          cn.company_name?.toLowerCase().includes(search) ||
          cn.invoice_number?.toLowerCase().includes(search)
        );
      }
      if (cnStatusFilter && cnStatusFilter !== "all") {
        filtered = filtered.filter(cn => cn.status === cnStatusFilter);
      }
      setCreditNotes(filtered);
    } catch (error) {
      toast.error("Failed to load credit notes");
    } finally {
      setLoading(false);
    }
  };

  const loadAuditTrail = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (auditFilters.entityType && auditFilters.entityType !== "all") params.append("entity_type", auditFilters.entityType);
      if (auditFilters.startDate) params.append("start_date", auditFilters.startDate);
      if (auditFilters.endDate) params.append("end_date", auditFilters.endDate);
      
      const response = await axiosInstance.get(`/finance/admin/audit-trail?${params}`);
      setAuditTrail(response.data);
    } catch (error) {
      toast.error("Failed to load audit trail");
    } finally {
      setLoading(false);
    }
  };

  // Invoice Management Actions
  const handleEditInvoiceNumber = async () => {
    try {
      await axiosInstance.put(`/finance/admin/invoices/${editNumberDialog.invoice.id}/number`, {
        year: parseInt(editNumberForm.year),
        month: parseInt(editNumberForm.month),
        sequence: parseInt(editNumberForm.sequence),
        reason: editNumberForm.reason
      });
      toast.success("Invoice number updated successfully");
      setEditNumberDialog({ open: false, invoice: null });
      setEditNumberForm({ year: 2026, month: 1, sequence: 1, reason: "" });
      loadInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update invoice number");
    }
  };

  const handleVoidInvoice = async () => {
    try {
      await axiosInstance.post(`/finance/admin/invoices/${voidDialog.invoice.id}/void`, {
        reason: voidForm.reason
      });
      toast.success("Invoice voided successfully");
      setVoidDialog({ open: false, invoice: null });
      setVoidForm({ reason: "" });
      loadInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to void invoice");
    }
  };

  const handleBackdateInvoice = async () => {
    try {
      await axiosInstance.put(`/finance/admin/invoices/${backdateDialog.invoice.id}/backdate`, {
        new_date: backdateForm.newDate,
        reason: backdateForm.reason
      });
      toast.success("Invoice backdated successfully");
      setBackdateDialog({ open: false, invoice: null });
      setBackdateForm({ newDate: "", reason: "" });
      loadInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to backdate invoice");
    }
  };

  const handleOverrideValidation = async () => {
    try {
      await axiosInstance.put(`/finance/admin/invoices/${overrideDialog.invoice.id}/override`, {
        total_amount: parseFloat(overrideForm.totalAmount),
        reason: overrideForm.reason,
        skip_validation: true
      });
      toast.success("Invoice amount overridden successfully");
      setOverrideDialog({ open: false, invoice: null });
      setOverrideForm({ totalAmount: 0, reason: "" });
      loadInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to override invoice");
    }
  };

  const handleEditPaidInvoice = async () => {
    try {
      await axiosInstance.put(`/finance/admin/invoices/${editPaidDialog.invoice.id}/edit-paid`, {
        bill_to_name: editPaidForm.billToName || null,
        bill_to_address: editPaidForm.billToAddress || null,
        total_amount: editPaidForm.totalAmount ? parseFloat(editPaidForm.totalAmount) : null,
        reason: editPaidForm.reason
      });
      toast.success("Paid invoice updated successfully");
      setEditPaidDialog({ open: false, invoice: null });
      setEditPaidForm({ billToName: "", billToAddress: "", totalAmount: 0, reason: "" });
      loadInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update paid invoice");
    }
  };

  // Payment Management Actions
  const handleDeletePayment = async () => {
    try {
      await axiosInstance.delete(`/finance/admin/payments/${deletePaymentDialog.payment.id}`, {
        data: { reason: deletePaymentForm.reason }
      });
      toast.success("Payment deleted successfully");
      setDeletePaymentDialog({ open: false, payment: null });
      setDeletePaymentForm({ reason: "" });
      loadPayments();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete payment");
    }
  };

  // Credit Note Management Actions
  const handleEditCreditNote = async () => {
    try {
      await axiosInstance.put(`/finance/admin/credit-notes/${editCnDialog.cn.id}/edit`, {
        company_name: editCnForm.companyName || undefined,
        reason: editCnForm.reason || undefined,
        description: editCnForm.description || undefined,
        amount: editCnForm.amount || undefined,
        percentage: editCnForm.percentage || undefined,
        edit_reason: editCnForm.editReason
      });
      toast.success("Credit note updated successfully");
      setEditCnDialog({ open: false, cn: null });
      setEditCnForm({ companyName: "", reason: "", description: "", amount: 0, percentage: 4, editReason: "" });
      loadCreditNotes();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update credit note");
    }
  };

  const handleBackdateCreditNote = async () => {
    try {
      await axiosInstance.put(`/finance/admin/credit-notes/${backdateCnDialog.cn.id}/backdate`, {
        new_date: backdateCnForm.newDate,
        reason: backdateCnForm.reason
      });
      toast.success("Credit note backdated successfully");
      setBackdateCnDialog({ open: false, cn: null });
      setBackdateCnForm({ newDate: "", reason: "" });
      loadCreditNotes();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to backdate credit note");
    }
  };

  const handleVoidCreditNote = async () => {
    try {
      await axiosInstance.put(`/finance/admin/credit-notes/${voidCnDialog.cn.id}/void?reason=${encodeURIComponent(voidCnForm.reason)}`);
      toast.success("Credit note voided successfully");
      setVoidCnDialog({ open: false, cn: null });
      setVoidCnForm({ reason: "" });
      loadCreditNotes();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to void credit note");
    }
  };

  const handleEditCnNumber = async () => {
    try {
      await axiosInstance.put(`/finance/admin/credit-notes/${editCnNumberDialog.cn.id}/number?year=${editCnNumberForm.year}&month=${editCnNumberForm.month}&sequence=${editCnNumberForm.sequence}&reason=${encodeURIComponent(editCnNumberForm.reason)}`);
      toast.success("Credit note number updated successfully");
      setEditCnNumberDialog({ open: false, cn: null });
      setEditCnNumberForm({ year: 2026, month: 1, sequence: 1, reason: "" });
      loadCreditNotes();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update credit note number");
    }
  };

  // Settings Actions
  const handleResetSequence = async () => {
    try {
      await axiosInstance.post("/finance/admin/sequence/reset", {
        year: parseInt(sequenceForm.year),
        month: parseInt(sequenceForm.month),
        new_sequence: parseInt(sequenceForm.sequence),
        reason: sequenceForm.reason
      });
      toast.success("Sequence reset successfully");
      setSequenceForm({ year: new Date().getFullYear(), month: new Date().getMonth() + 1, sequence: 1, reason: "" });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to reset sequence");
    }
  };

  // Audit Trail Export
  const handleExportAuditTrail = async () => {
    try {
      const params = new URLSearchParams();
      if (auditFilters.startDate) params.append("start_date", auditFilters.startDate);
      if (auditFilters.endDate) params.append("end_date", auditFilters.endDate);
      
      const response = await axiosInstance.get(`/finance/admin/audit-trail/export?${params}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Audit_Trail_${new Date().toISOString().slice(0,10)}.xlsx`;
      link.click();
      window.URL.revokeObjectURL(url);
      
      toast.success("Audit trail exported!");
    } catch (error) {
      toast.error("Failed to export audit trail");
    }
  };

  // Sessions Data Management Functions (existing)
  const buildQueryString = () => {
    const params = new URLSearchParams();
    if (filters.sessionId && filters.sessionId !== "all") params.append("session_id", filters.sessionId);
    if (filters.companyId && filters.companyId !== "all") params.append("company_id", filters.companyId);
    if (filters.programId && filters.programId !== "all") params.append("program_id", filters.programId);
    if (filters.startDate) params.append("start_date", filters.startDate);
    if (filters.endDate) params.append("end_date", filters.endDate);
    return params.toString();
  };

  const loadTestResults = async () => {
    setLoading(true);
    try {
      const query = buildQueryString();
      const response = await axiosInstance.get(`/admin/data-management/test-results?${query}`);
      setTestResults(response.data);
    } catch (error) {
      toast.error("Failed to load test results");
    } finally {
      setLoading(false);
    }
  };

  const loadFeedback = async () => {
    setLoading(true);
    try {
      const query = buildQueryString();
      const response = await axiosInstance.get(`/admin/data-management/feedback?${query}`);
      setFeedback(response.data);
    } catch (error) {
      toast.error("Failed to load feedback");
    } finally {
      setLoading(false);
    }
  };

  const loadAttendance = async () => {
    setLoading(true);
    try {
      const query = buildQueryString();
      const response = await axiosInstance.get(`/admin/data-management/attendance?${query}`);
      setAttendance(response.data);
    } catch (error) {
      toast.error("Failed to load attendance");
    } finally {
      setLoading(false);
    }
  };

  const loadChecklists = async () => {
    setLoading(true);
    try {
      const query = buildQueryString();
      const response = await axiosInstance.get(`/admin/data-management/checklists?${query}`);
      setChecklists(response.data);
    } catch (error) {
      toast.error("Failed to load checklists");
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (type, data) => {
    setEditDialog({ open: true, type, data: { ...data } });
  };

  const handleDelete = (type, id) => {
    setDeleteDialog({ open: true, type, id });
  };

  const confirmDelete = async () => {
    const { type, id } = deleteDialog;
    try {
      await axiosInstance.delete(`/admin/data-management/${type}/${id}`);
      toast.success(`${type} deleted successfully`);
      setDeleteDialog({ open: false, type: null, id: null });
      
      if (type === "test-results") loadTestResults();
      else if (type === "feedback") loadFeedback();
      else if (type === "attendance") loadAttendance();
      else if (type === "checklists") loadChecklists();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to delete ${type}`);
    }
  };

  const saveEdit = async () => {
    const { type, data } = editDialog;
    try {
      let endpoint = "";
      let payload = {};

      if (type === "test-results") {
        endpoint = `/admin/data-management/test-results/${data.id}`;
        payload = { score: parseFloat(data.score), passed: data.passed };
      } else if (type === "feedback") {
        endpoint = `/admin/data-management/feedback/${data.id}`;
        payload = { responses: data.responses };
      } else if (type === "attendance") {
        endpoint = `/admin/data-management/attendance/${data.id}`;
        payload = { clock_in: data.clock_in, clock_out: data.clock_out };
      } else if (type === "checklists") {
        endpoint = `/admin/data-management/checklists/${data.id}`;
        payload = { items: data.items };
      }

      await axiosInstance.put(endpoint, payload);
      toast.success(`${type} updated successfully`);
      setEditDialog({ open: false, type: null, data: null });

      if (type === "test-results") loadTestResults();
      else if (type === "feedback") loadFeedback();
      else if (type === "attendance") loadAttendance();
      else if (type === "checklists") loadChecklists();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to update ${type}`);
    }
  };

  const viewAuditLog = async (type, id) => {
    try {
      const response = await axiosInstance.get(`/admin/data-management/audit-logs/${type}/${id}`);
      setAuditDialog({ open: true, type, id, logs: response.data });
    } catch (error) {
      toast.error("Failed to load audit logs");
    }
  };

  const getInvoiceStatusBadge = (status) => {
    const statusColors = {
      auto_draft: "bg-gray-500",
      finance_review: "bg-yellow-500",
      approved: "bg-blue-500",
      issued: "bg-purple-500",
      paid: "bg-green-500",
      cancelled: "bg-red-500",
      voided: "bg-red-700"
    };
    return <Badge className={statusColors[status] || "bg-gray-400"}>{status?.toUpperCase() || "UNKNOWN"}</Badge>;
  };

  const FilterSection = () => (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Filter className="h-5 w-5" />
          Search Filters
        </CardTitle>
        <CardDescription>Filter data by session, company, program, or date range</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <Label>Session</Label>
            <Select value={filters.sessionId} onValueChange={(value) => setFilters({ ...filters, sessionId: value })}>
              <SelectTrigger>
                <SelectValue placeholder="All Sessions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sessions</SelectItem>
                {sessions.map(s => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label>Company</Label>
            <Select value={filters.companyId} onValueChange={(value) => setFilters({ ...filters, companyId: value })}>
              <SelectTrigger>
                <SelectValue placeholder="All Companies" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Companies</SelectItem>
                {companies.map(c => (
                  <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label>Program</Label>
            <Select value={filters.programId} onValueChange={(value) => setFilters({ ...filters, programId: value })}>
              <SelectTrigger>
                <SelectValue placeholder="All Programs" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Programs</SelectItem>
                {programs.map(p => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label>Start Date</Label>
            <Input
              type="date"
              value={filters.startDate}
              onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
            />
          </div>

          <div>
            <Label>End Date</Label>
            <Input
              type="date"
              value={filters.endDate}
              onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
            />
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <Button onClick={() => setFilters({ sessionId: "all", companyId: "all", programId: "all", startDate: "", endDate: "" })} variant="outline">
            Clear Filters
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  // Sessions Data Management Tab (existing functionality)
  const SessionsDataTab = () => (
    <div className="space-y-4">
      <FilterSection />
      
      <Tabs defaultValue="test-results" className="space-y-4">
        <TabsList className="flex flex-wrap gap-1 h-auto p-1">
          <TabsTrigger value="test-results" className="text-xs sm:text-sm px-2 sm:px-3 py-2">
            <span className="hidden sm:inline">Test Scores</span>
            <span className="sm:hidden">Tests</span>
          </TabsTrigger>
          <TabsTrigger value="feedback" className="text-xs sm:text-sm px-2 sm:px-3 py-2">Feedback</TabsTrigger>
          <TabsTrigger value="attendance" className="text-xs sm:text-sm px-2 sm:px-3 py-2">
            <span className="hidden sm:inline">Attendance</span>
            <span className="sm:hidden">Attend</span>
          </TabsTrigger>
          <TabsTrigger value="checklists" className="text-xs sm:text-sm px-2 sm:px-3 py-2">
            <span className="hidden sm:inline">Checklists</span>
            <span className="sm:hidden">Checks</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="test-results" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle>Test Scores Management</CardTitle>
                  <CardDescription>View, edit, and delete participant test results</CardDescription>
                </div>
                <Button onClick={loadTestResults} disabled={loading}>
                  <Search className="mr-2 h-4 w-4" />
                  {loading ? "Loading..." : "Search"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {testResults.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">No test results found. Apply filters and click Search.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Participant</TableHead>
                      <TableHead>Session</TableHead>
                      <TableHead>Test Type</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Result</TableHead>
                      <TableHead>Submitted</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {testResults.map((result) => (
                      <TableRow key={result.id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{result.participant_name}</div>
                            <div className="text-sm text-muted-foreground">{result.participant_ic}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div>
                            <div>{result.session_name}</div>
                            <div className="text-sm text-muted-foreground">{result.company_name}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{result.test_type || "N/A"}</Badge>
                        </TableCell>
                        <TableCell className="font-semibold">{result.score?.toFixed(1)}%</TableCell>
                        <TableCell>
                          <Badge variant={result.passed ? "default" : "destructive"}>
                            {result.passed ? "PASS" : "FAIL"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm">{new Date(result.submitted_at).toLocaleString()}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant="ghost" onClick={() => viewAuditLog("test_result", result.id)}>
                              <History className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => handleEdit("test-results", result)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => handleDelete("test-results", result.id)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
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

        <TabsContent value="feedback" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle>Feedback Management</CardTitle>
                  <CardDescription>View, edit, and delete participant feedback</CardDescription>
                </div>
                <Button onClick={loadFeedback} disabled={loading}>
                  <Search className="mr-2 h-4 w-4" />
                  {loading ? "Loading..." : "Search"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {feedback.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">No feedback found. Apply filters and click Search.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Participant</TableHead>
                      <TableHead>Session</TableHead>
                      <TableHead>Company</TableHead>
                      <TableHead>Responses</TableHead>
                      <TableHead>Submitted</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {feedback.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{item.participant_name}</div>
                            <div className="text-sm text-muted-foreground">{item.participant_ic}</div>
                          </div>
                        </TableCell>
                        <TableCell>{item.session_name}</TableCell>
                        <TableCell>{item.company_name}</TableCell>
                        <TableCell>{item.responses?.length || 0} responses</TableCell>
                        <TableCell className="text-sm">{new Date(item.submitted_at).toLocaleString()}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant="ghost" onClick={() => viewAuditLog("feedback", item.id)}>
                              <History className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => handleEdit("feedback", item)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => handleDelete("feedback", item.id)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
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

        <TabsContent value="attendance" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle>Attendance Management</CardTitle>
                  <CardDescription>View, edit, and delete attendance records</CardDescription>
                </div>
                <Button onClick={loadAttendance} disabled={loading}>
                  <Search className="mr-2 h-4 w-4" />
                  {loading ? "Loading..." : "Search"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {attendance.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">No attendance records found. Apply filters and click Search.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Participant</TableHead>
                      <TableHead>Session</TableHead>
                      <TableHead>Clock In</TableHead>
                      <TableHead>Clock Out</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {attendance.map((record) => (
                      <TableRow key={record.id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{record.participant_name}</div>
                            <div className="text-sm text-muted-foreground">{record.participant_ic}</div>
                          </div>
                        </TableCell>
                        <TableCell>{record.session_name}</TableCell>
                        <TableCell className="text-sm">{record.clock_in || "N/A"}</TableCell>
                        <TableCell className="text-sm">{record.clock_out || "N/A"}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant="ghost" onClick={() => viewAuditLog("attendance", record.id)}>
                              <History className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => handleEdit("attendance", record)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => handleDelete("attendance", record.id)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
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

        <TabsContent value="checklists" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle>Checklist Management</CardTitle>
                  <CardDescription>View, edit, and delete vehicle checklists</CardDescription>
                </div>
                <Button onClick={loadChecklists} disabled={loading}>
                  <Search className="mr-2 h-4 w-4" />
                  {loading ? "Loading..." : "Search"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {checklists.length === 0 ? (
                <p className="text-center py-8 text-muted-foreground">No checklists found. Apply filters and click Search.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Participant</TableHead>
                      <TableHead>Session</TableHead>
                      <TableHead>Trainer</TableHead>
                      <TableHead>Items</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {checklists.map((checklist) => (
                      <TableRow key={checklist.id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{checklist.participant_name}</div>
                            <div className="text-sm text-muted-foreground">{checklist.participant_ic}</div>
                          </div>
                        </TableCell>
                        <TableCell>{checklist.session_name}</TableCell>
                        <TableCell>{checklist.trainer_name}</TableCell>
                        <TableCell>{checklist.items?.length || 0} items</TableCell>
                        <TableCell className="text-sm">{new Date(checklist.created_at).toLocaleString()}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant="ghost" onClick={() => viewAuditLog("checklist", checklist.id)}>
                              <History className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => handleEdit("checklists", checklist)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => handleDelete("checklists", checklist.id)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
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
      </Tabs>
    </div>
  );

  // Invoice Management Tab
  // Payment Management Tab
  const PaymentManagementTab = () => (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="h-5 w-5" />
                Payment Management
              </CardTitle>
              <CardDescription>View and delete payment records</CardDescription>
            </div>
            <Button onClick={loadPayments} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {payments.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">No payments found.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice #</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>Reference</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.map((payment) => (
                  <TableRow key={payment.id}>
                    <TableCell className="font-mono text-sm">{payment.invoice_number}</TableCell>
                    <TableCell>{payment.company_name}</TableCell>
                    <TableCell className="font-semibold">RM {payment.amount?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{payment.payment_method}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{payment.reference_number || "N/A"}</TableCell>
                    <TableCell className="text-sm">{payment.payment_date}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setDeletePaymentForm({ reason: "" });
                          setDeletePaymentDialog({ open: true, payment });
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );

  // Credit Note Management Tab
  // Settings Tab
  const SettingsTab = () => (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Invoice Sequence Settings
          </CardTitle>
          <CardDescription>Reset invoice sequence counter for a specific month/year</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <Label>Year</Label>
              <Input
                type="number"
                value={sequenceForm.year}
                onChange={(e) => setSequenceForm({ ...sequenceForm, year: e.target.value })}
                min="2020"
                max="2100"
              />
            </div>
            <div>
              <Label>Month</Label>
              <Select value={String(sequenceForm.month)} onValueChange={(v) => setSequenceForm({ ...sequenceForm, month: parseInt(v) })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[...Array(12)].map((_, i) => (
                    <SelectItem key={i+1} value={String(i+1)}>
                      {new Date(2000, i, 1).toLocaleString('default', { month: 'long' })}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>New Sequence Number</Label>
              <Input
                type="number"
                value={sequenceForm.sequence}
                onChange={(e) => setSequenceForm({ ...sequenceForm, sequence: e.target.value })}
                min="1"
              />
            </div>
          </div>
          <div>
            <Label>Reason for Reset *</Label>
            <Textarea
              placeholder="Explain why the sequence needs to be reset..."
              value={sequenceForm.reason}
              onChange={(e) => setSequenceForm({ ...sequenceForm, reason: e.target.value })}
            />
          </div>
          <Button onClick={handleResetSequence} disabled={!sequenceForm.reason}>
            Reset Sequence Counter
          </Button>
          <p className="text-sm text-muted-foreground">
            Next invoice for {sequenceForm.year}/{String(sequenceForm.month).padStart(2, '0')} will be: 
            <span className="font-mono ml-2">INV/MDDRC/{sequenceForm.year}/{String(sequenceForm.month).padStart(2, '0')}/{String(sequenceForm.sequence).padStart(4, '0')}</span>
          </p>
        </CardContent>
      </Card>
    </div>
  );

  // Audit Trail Tab
  const AuditTrailTab = () => (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center flex-wrap gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                Finance Audit Trail
              </CardTitle>
              <CardDescription>Complete history of all financial changes</CardDescription>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Select value={auditFilters.entityType} onValueChange={(v) => setAuditFilters({ ...auditFilters, entityType: v })}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="invoice">Invoice</SelectItem>
                  <SelectItem value="payment">Payment</SelectItem>
                  <SelectItem value="sequence">Sequence</SelectItem>
                </SelectContent>
              </Select>
              <Input
                type="date"
                value={auditFilters.startDate}
                onChange={(e) => setAuditFilters({ ...auditFilters, startDate: e.target.value })}
                className="w-36"
              />
              <Input
                type="date"
                value={auditFilters.endDate}
                onChange={(e) => setAuditFilters({ ...auditFilters, endDate: e.target.value })}
                className="w-36"
              />
              <Button onClick={loadAuditTrail} disabled={loading}>
                <Search className="h-4 w-4 mr-2" />
                Search
              </Button>
              <Button onClick={handleExportAuditTrail} variant="outline">
                <Download className="h-4 w-4 mr-2" />
                Export Excel
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {auditTrail.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">No audit trail entries found.</p>
          ) : (
            <div className="space-y-3">
              {auditTrail.map((log) => (
                <Card key={log.id} className="p-4">
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={log.action?.includes("Void") ? "destructive" : log.action?.includes("Delete") ? "destructive" : "default"}>
                          {log.action}
                        </Badge>
                        <span className="font-medium">{log.record_reference}</span>
                      </div>
                      {log.field_changed && (
                        <p className="text-sm text-muted-foreground">
                          <span className="font-medium">Field:</span> {log.field_changed}
                          {log.from_value && log.to_value && (
                            <span> • <span className="text-red-500">{log.from_value}</span> → <span className="text-green-500">{log.to_value}</span></span>
                          )}
                        </p>
                      )}
                      <p className="text-sm">
                        <span className="font-medium">By:</span> {log.changed_by_name} ({log.changed_by_email})
                      </p>
                      <p className="text-sm text-muted-foreground">
                        <span className="font-medium">Reason:</span> {log.reason}
                      </p>
                    </div>
                    <p className="text-sm text-muted-foreground whitespace-nowrap">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : "N/A"}
                    </p>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Database className="h-6 w-6" />
          Data Management
        </h2>
        <p className="text-muted-foreground">Manage all training and finance data with full audit trail</p>
      </div>

      {/* Main Tab Navigation */}
      <Tabs value={activeMainTab} onValueChange={setActiveMainTab} className="space-y-4">
        <TabsList className={`flex flex-wrap gap-1 h-auto p-1 ${hasFinanceAccess ? "" : ""}`}>
          <TabsTrigger value="sessions-data" className="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm px-2 sm:px-3 py-2">
            <Database className="h-3 w-3 sm:h-4 sm:w-4" />
            <span className="hidden sm:inline">Sessions Data</span>
            <span className="sm:hidden">Data</span>
          </TabsTrigger>
          {hasFinanceAccess && (
            <>
              <TabsTrigger value="invoice-management" className="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm px-2 sm:px-3 py-2">
                <FileText className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="hidden sm:inline">Invoices</span>
                <span className="sm:hidden">Inv</span>
              </TabsTrigger>
              <TabsTrigger value="creditnote-management" className="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm px-2 sm:px-3 py-2">
                <FileText className="h-3 w-3 sm:h-4 sm:w-4 text-red-600" />
                <span className="hidden sm:inline">Credit Notes</span>
                <span className="sm:hidden">CN</span>
              </TabsTrigger>
              <TabsTrigger value="payment-management" className="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm px-2 sm:px-3 py-2">
                <CreditCard className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="hidden sm:inline">Payments</span>
                <span className="sm:hidden">Pay</span>
              </TabsTrigger>
              <TabsTrigger value="settings" className="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm px-2 sm:px-3 py-2">
                <Settings className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="hidden sm:inline">Settings</span>
                <span className="sm:hidden">Set</span>
              </TabsTrigger>
              <TabsTrigger value="audit-trail" className="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm px-2 sm:px-3 py-2">
                <History className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="hidden sm:inline">Audit Trail</span>
                <span className="sm:hidden">Audit</span>
              </TabsTrigger>
            </>
          )}
        </TabsList>

        <TabsContent value="sessions-data">
          {isSuperAdmin ? <SuperAdminPanel /> : <SessionsDataTab />}
        </TabsContent>

        {hasFinanceAccess && (
          <>
            <TabsContent value="invoice-management">
              <InvoiceManagementTab
                invoices={invoices}
                invoiceSearch={invoiceSearch}
                setInvoiceSearch={setInvoiceSearch}
                invoiceStatusFilter={invoiceStatusFilter}
                setInvoiceStatusFilter={setInvoiceStatusFilter}
                loading={loading}
                loadInvoices={loadInvoices}
                getInvoiceStatusBadge={getInvoiceStatusBadge}
                setEditNumberForm={setEditNumberForm}
                setEditNumberDialog={setEditNumberDialog}
                setBackdateForm={setBackdateForm}
                setBackdateDialog={setBackdateDialog}
                setOverrideForm={setOverrideForm}
                setOverrideDialog={setOverrideDialog}
                setEditPaidForm={setEditPaidForm}
                setEditPaidDialog={setEditPaidDialog}
                setVoidForm={setVoidForm}
                setVoidDialog={setVoidDialog}
              />
            </TabsContent>
            <TabsContent value="creditnote-management">
              <CreditNoteManagementTab
                creditNotes={creditNotes}
                cnSearch={cnSearch}
                setCnSearch={setCnSearch}
                cnStatusFilter={cnStatusFilter}
                setCnStatusFilter={setCnStatusFilter}
                loading={loading}
                loadCreditNotes={loadCreditNotes}
                setEditCnNumberForm={setEditCnNumberForm}
                setEditCnNumberDialog={setEditCnNumberDialog}
                setBackdateCnForm={setBackdateCnForm}
                setBackdateCnDialog={setBackdateCnDialog}
                setEditCnForm={setEditCnForm}
                setEditCnDialog={setEditCnDialog}
                setVoidCnForm={setVoidCnForm}
                setVoidCnDialog={setVoidCnDialog}
              />
            </TabsContent>
            <TabsContent value="payment-management">
              <PaymentManagementTab />
            </TabsContent>
            <TabsContent value="settings">
              <SettingsTab />
            </TabsContent>
            <TabsContent value="audit-trail">
              <AuditTrailTab />
            </TabsContent>
          </>
        )}
      </Tabs>

      {/* Edit Invoice Number Dialog */}
      <Dialog open={editNumberDialog.open} onOpenChange={(open) => setEditNumberDialog({ ...editNumberDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Invoice Number</DialogTitle>
            <DialogDescription>
              Change the invoice number for: {editNumberDialog.invoice?.invoice_number}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Year</Label>
                <Input
                  type="number"
                  value={editNumberForm.year}
                  onChange={(e) => setEditNumberForm({ ...editNumberForm, year: e.target.value })}
                />
              </div>
              <div>
                <Label>Month</Label>
                <Input
                  type="number"
                  value={editNumberForm.month}
                  onChange={(e) => setEditNumberForm({ ...editNumberForm, month: e.target.value })}
                  min="1"
                  max="12"
                />
              </div>
              <div>
                <Label>Sequence</Label>
                <Input
                  type="number"
                  value={editNumberForm.sequence}
                  onChange={(e) => setEditNumberForm({ ...editNumberForm, sequence: e.target.value })}
                  min="1"
                />
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              New number: <span className="font-mono">INV/MDDRC/{editNumberForm.year}/{String(editNumberForm.month).padStart(2, '0')}/{String(editNumberForm.sequence).padStart(4, '0')}</span>
            </p>
            <div>
              <Label>Reason for Change *</Label>
              <Textarea
                placeholder="Explain why the invoice number needs to be changed..."
                value={editNumberForm.reason}
                onChange={(e) => setEditNumberForm({ ...editNumberForm, reason: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditNumberDialog({ open: false, invoice: null })}>Cancel</Button>
            <Button onClick={handleEditInvoiceNumber} disabled={!editNumberForm.reason}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Void Invoice Dialog */}
      <Dialog open={voidDialog.open} onOpenChange={(open) => setVoidDialog({ ...voidDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-destructive">Void Invoice</DialogTitle>
            <DialogDescription>
              This will void invoice: {voidDialog.invoice?.invoice_number}. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div>
            <Label>Reason for Voiding *</Label>
            <Textarea
              placeholder="Explain why this invoice needs to be voided..."
              value={voidForm.reason}
              onChange={(e) => setVoidForm({ reason: e.target.value })}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVoidDialog({ open: false, invoice: null })}>Cancel</Button>
            <Button variant="destructive" onClick={handleVoidInvoice} disabled={!voidForm.reason}>Void Invoice</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Backdate Invoice Dialog */}
      <Dialog open={backdateDialog.open} onOpenChange={(open) => setBackdateDialog({ ...backdateDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Backdate Invoice</DialogTitle>
            <DialogDescription>
              Change the date for invoice: {backdateDialog.invoice?.invoice_number}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>New Invoice Date</Label>
              <Input
                type="date"
                value={backdateForm.newDate}
                onChange={(e) => setBackdateForm({ ...backdateForm, newDate: e.target.value })}
              />
            </div>
            <div>
              <Label>Reason for Backdating *</Label>
              <Textarea
                placeholder="Explain why this invoice needs to be backdated..."
                value={backdateForm.reason}
                onChange={(e) => setBackdateForm({ ...backdateForm, reason: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBackdateDialog({ open: false, invoice: null })}>Cancel</Button>
            <Button onClick={handleBackdateInvoice} disabled={!backdateForm.newDate || !backdateForm.reason}>Backdate Invoice</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Override Validation Dialog */}
      <Dialog open={overrideDialog.open} onOpenChange={(open) => setOverrideDialog({ ...overrideDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Override Invoice Amount</DialogTitle>
            <DialogDescription>
              Override the amount for invoice: {overrideDialog.invoice?.invoice_number} (skips validation)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>New Total Amount (RM)</Label>
              <Input
                type="number"
                value={overrideForm.totalAmount}
                onChange={(e) => setOverrideForm({ ...overrideForm, totalAmount: e.target.value })}
                step="0.01"
              />
            </div>
            <div>
              <Label>Reason for Override *</Label>
              <Textarea
                placeholder="Explain why the amount needs to be overridden..."
                value={overrideForm.reason}
                onChange={(e) => setOverrideForm({ ...overrideForm, reason: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOverrideDialog({ open: false, invoice: null })}>Cancel</Button>
            <Button onClick={handleOverrideValidation} disabled={!overrideForm.reason}>Override Amount</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Paid Invoice Dialog */}
      <Dialog open={editPaidDialog.open} onOpenChange={(open) => setEditPaidDialog({ ...editPaidDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Paid Invoice</DialogTitle>
            <DialogDescription>
              Modify details of paid invoice: {editPaidDialog.invoice?.invoice_number}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Bill To Name</Label>
              <Input
                value={editPaidForm.billToName}
                onChange={(e) => setEditPaidForm({ ...editPaidForm, billToName: e.target.value })}
              />
            </div>
            <div>
              <Label>Bill To Address</Label>
              <Textarea
                value={editPaidForm.billToAddress}
                onChange={(e) => setEditPaidForm({ ...editPaidForm, billToAddress: e.target.value })}
              />
            </div>
            <div>
              <Label>Total Amount (RM)</Label>
              <Input
                type="number"
                value={editPaidForm.totalAmount}
                onChange={(e) => setEditPaidForm({ ...editPaidForm, totalAmount: e.target.value })}
                step="0.01"
              />
            </div>
            <div>
              <Label>Reason for Edit *</Label>
              <Textarea
                placeholder="Explain why this paid invoice needs to be edited..."
                value={editPaidForm.reason}
                onChange={(e) => setEditPaidForm({ ...editPaidForm, reason: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditPaidDialog({ open: false, invoice: null })}>Cancel</Button>
            <Button onClick={handleEditPaidInvoice} disabled={!editPaidForm.reason}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Payment Dialog */}
      <AlertDialog open={deletePaymentDialog.open} onOpenChange={(open) => setDeletePaymentDialog({ ...deletePaymentDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Payment Record?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete this payment record for RM {deletePaymentDialog.payment?.amount?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}.
              The invoice status may be updated as a result.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-4">
            <Label>Reason for Deletion *</Label>
            <Textarea
              placeholder="Explain why this payment needs to be deleted..."
              value={deletePaymentForm.reason}
              onChange={(e) => setDeletePaymentForm({ reason: e.target.value })}
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeletePayment} 
              disabled={!deletePaymentForm.reason}
              className="bg-destructive text-destructive-foreground"
            >
              Delete Payment
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Existing Edit Dialog */}
      <Dialog open={editDialog.open} onOpenChange={(open) => setEditDialog({ ...editDialog, open })}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit {editDialog.type?.replace("-", " ")}</DialogTitle>
            <DialogDescription>Make changes to the record. This action will be logged in the audit trail.</DialogDescription>
          </DialogHeader>

          {editDialog.type === "test-results" && editDialog.data && (
            <div className="space-y-4">
              <div>
                <Label>Score (%)</Label>
                <Input
                  type="number"
                  value={editDialog.data.score}
                  onChange={(e) => setEditDialog({ ...editDialog, data: { ...editDialog.data, score: e.target.value } })}
                  min="0"
                  max="100"
                  step="0.1"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editDialog.data.passed}
                  onChange={(e) => setEditDialog({ ...editDialog, data: { ...editDialog.data, passed: e.target.checked } })}
                  className="h-4 w-4"
                />
                <Label>Passed</Label>
              </div>
            </div>
          )}

          {editDialog.type === "attendance" && editDialog.data && (
            <div className="space-y-4">
              <div>
                <Label>Clock In</Label>
                <Input
                  type="datetime-local"
                  value={editDialog.data.clock_in ? new Date(editDialog.data.clock_in).toISOString().slice(0, 16) : ""}
                  onChange={(e) => setEditDialog({ ...editDialog, data: { ...editDialog.data, clock_in: e.target.value } })}
                />
              </div>
              <div>
                <Label>Clock Out</Label>
                <Input
                  type="datetime-local"
                  value={editDialog.data.clock_out ? new Date(editDialog.data.clock_out).toISOString().slice(0, 16) : ""}
                  onChange={(e) => setEditDialog({ ...editDialog, data: { ...editDialog.data, clock_out: e.target.value } })}
                />
              </div>
            </div>
          )}

          {editDialog.type === "feedback" && editDialog.data && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">Feedback responses: {editDialog.data.responses?.length || 0} items</p>
              <div className="max-h-96 overflow-y-auto space-y-2">
                {editDialog.data.responses?.map((response, index) => (
                  <div key={index} className="border p-3 rounded">
                    <Label className="font-semibold">{response.question}</Label>
                    <Textarea
                      value={response.answer}
                      onChange={(e) => {
                        const newResponses = [...editDialog.data.responses];
                        newResponses[index].answer = e.target.value;
                        setEditDialog({ ...editDialog, data: { ...editDialog.data, responses: newResponses } });
                      }}
                      className="mt-2"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {editDialog.type === "checklists" && editDialog.data && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">Checklist items: {editDialog.data.items?.length || 0} items</p>
              <p className="text-sm text-yellow-600">Note: Editing checklist items is complex. Contact support if you need to modify specific items.</p>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialog({ open: false, type: null, data: null })}>
              Cancel
            </Button>
            <Button onClick={saveEdit}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialog.open} onOpenChange={(open) => setDeleteDialog({ ...deleteDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete this {deleteDialog.type?.replace("-", " ")} from the database.
              This action cannot be undone and will be logged in the audit trail.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground">
              Delete Permanently
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Audit Log Dialog */}
      <Dialog open={auditDialog.open} onOpenChange={(open) => setAuditDialog({ ...auditDialog, open })}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Audit Trail
            </DialogTitle>
            <DialogDescription>Complete history of all changes made to this record</DialogDescription>
          </DialogHeader>

          <div className="max-h-96 overflow-y-auto space-y-3">
            {auditDialog.logs.length === 0 ? (
              <p className="text-center py-4 text-muted-foreground">No audit logs found</p>
            ) : (
              auditDialog.logs.map((log) => (
                <div key={log.id} className="border p-4 rounded-lg space-y-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <Badge variant={log.action === "delete" ? "destructive" : log.action === "update" ? "default" : "secondary"}>
                        {log.action.toUpperCase()}
                      </Badge>
                      <p className="text-sm font-medium mt-1">{log.user_email}</p>
                    </div>
                    <p className="text-sm text-muted-foreground">{new Date(log.timestamp).toLocaleString()}</p>
                  </div>
                  {log.changes_summary && (
                    <p className="text-sm text-muted-foreground">{log.changes_summary}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Credit Note Edit Number Dialog */}
      <Dialog open={editCnNumberDialog.open} onOpenChange={(open) => setEditCnNumberDialog({ ...editCnNumberDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Credit Note Number</DialogTitle>
            <DialogDescription>
              Change the CN number for: {editCnNumberDialog.cn?.cn_number}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Year</Label>
                <Input type="number" value={editCnNumberForm.year} onChange={(e) => setEditCnNumberForm({ ...editCnNumberForm, year: parseInt(e.target.value) || 2026 })} />
              </div>
              <div>
                <Label>Month</Label>
                <Input type="number" min={1} max={12} value={editCnNumberForm.month} onChange={(e) => setEditCnNumberForm({ ...editCnNumberForm, month: parseInt(e.target.value) || 1 })} />
              </div>
              <div>
                <Label>Sequence</Label>
                <Input type="number" min={1} value={editCnNumberForm.sequence} onChange={(e) => setEditCnNumberForm({ ...editCnNumberForm, sequence: parseInt(e.target.value) || 1 })} />
              </div>
            </div>
            <div>
              <Label>New CN Number Preview</Label>
              <p className="text-sm font-mono p-2 bg-muted rounded">CN/MDDRC/{editCnNumberForm.year}/{String(editCnNumberForm.month).padStart(2, '0')}/{String(editCnNumberForm.sequence).padStart(4, '0')}</p>
            </div>
            <div>
              <Label>Reason for Change (required)</Label>
              <Textarea placeholder="Explain why this CN number needs to be changed..." value={editCnNumberForm.reason} onChange={(e) => setEditCnNumberForm({ ...editCnNumberForm, reason: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditCnNumberDialog({ open: false, cn: null })}>Cancel</Button>
            <Button onClick={handleEditCnNumber} disabled={!editCnNumberForm.reason}>Update Number</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Credit Note Backdate Dialog */}
      <Dialog open={backdateCnDialog.open} onOpenChange={(open) => setBackdateCnDialog({ ...backdateCnDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Backdate Credit Note</DialogTitle>
            <DialogDescription>
              Change the date for CN: {backdateCnDialog.cn?.cn_number}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div>
              <Label>New Date</Label>
              <Input type="date" value={backdateCnForm.newDate} onChange={(e) => setBackdateCnForm({ ...backdateCnForm, newDate: e.target.value })} />
            </div>
            <div>
              <Label>Reason for Backdating (required)</Label>
              <Textarea placeholder="Explain why this credit note needs to be backdated..." value={backdateCnForm.reason} onChange={(e) => setBackdateCnForm({ ...backdateCnForm, reason: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBackdateCnDialog({ open: false, cn: null })}>Cancel</Button>
            <Button onClick={handleBackdateCreditNote} disabled={!backdateCnForm.newDate || !backdateCnForm.reason}>Backdate CN</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Credit Note Edit Dialog */}
      <Dialog open={editCnDialog.open} onOpenChange={(open) => setEditCnDialog({ ...editCnDialog, open })}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Credit Note Details</DialogTitle>
            <DialogDescription>
              Modify details for CN: {editCnDialog.cn?.cn_number}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div>
              <Label>Company Name</Label>
              <Input value={editCnForm.companyName} onChange={(e) => setEditCnForm({ ...editCnForm, companyName: e.target.value })} />
            </div>
            <div>
              <Label>Reason</Label>
              <Input value={editCnForm.reason} onChange={(e) => setEditCnForm({ ...editCnForm, reason: e.target.value })} />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea value={editCnForm.description} onChange={(e) => setEditCnForm({ ...editCnForm, description: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Amount (RM)</Label>
                <Input type="number" step="0.01" value={editCnForm.amount} onChange={(e) => setEditCnForm({ ...editCnForm, amount: parseFloat(e.target.value) || 0 })} />
              </div>
              <div>
                <Label>Percentage (%)</Label>
                <Input type="number" step="0.1" value={editCnForm.percentage} onChange={(e) => setEditCnForm({ ...editCnForm, percentage: parseFloat(e.target.value) || 0 })} />
              </div>
            </div>
            <div>
              <Label>Reason for Edit (required)</Label>
              <Textarea placeholder="Explain why this credit note needs to be edited..." value={editCnForm.editReason} onChange={(e) => setEditCnForm({ ...editCnForm, editReason: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditCnDialog({ open: false, cn: null })}>Cancel</Button>
            <Button onClick={handleEditCreditNote} disabled={!editCnForm.editReason}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Credit Note Void Dialog */}
      <Dialog open={voidCnDialog.open} onOpenChange={(open) => setVoidCnDialog({ ...voidCnDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600">Void Credit Note</DialogTitle>
            <DialogDescription>
              This will permanently void CN: {voidCnDialog.cn?.cn_number}. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div>
              <Label>Reason for Voiding (required)</Label>
              <Textarea placeholder="Explain why this credit note needs to be voided..." value={voidCnForm.reason} onChange={(e) => setVoidCnForm({ ...voidCnForm, reason: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVoidCnDialog({ open: false, cn: null })}>Cancel</Button>
            <Button variant="destructive" onClick={handleVoidCreditNote} disabled={!voidCnForm.reason}>Void Credit Note</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DataManagement;
