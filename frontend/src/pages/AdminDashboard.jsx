import { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { LogOut, Building2, Users, Calendar, MessageSquare, BookOpen, Plus, Trash2, Edit, UserPlus, UserCog, ClipboardList, ClipboardCheck, Settings as SettingsIcon, FileText, Download, Search, Book, Award, Eye, Upload, CheckCircle, XCircle, Clock, AlertCircle, DollarSign, Printer, Bold, Italic, Underline, List, Target } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import TestManagement from "./TestManagement";
import FeedbackManagement from "./FeedbackManagement";
import ChecklistManagement from "./ChecklistManagement";
import Settings from "./Settings";
import DataManagement from "../components/DataManagement";
import { useTheme } from "../context/ThemeContext";
import { SearchBar } from "../components/SearchBar";
import SessionCosting from "../components/SessionCosting";
import IndemnityFormPrint from "../components/IndemnityFormPrint";
import MyPayroll from "../components/MyPayroll";
import ProgramsTab from "../components/admin/ProgramsTab";
import CompaniesTab from "../components/admin/CompaniesTab";
import { FinanceOverviewTab } from "../components/admin/FinanceOverviewTab";
import { SessionsTab } from "../components/admin/SessionsTab";
import { StaffTab } from "../components/admin/StaffTab";
import { ReportsTab } from "../components/admin/ReportsTab";
import { PastTrainingTab } from "../components/admin/PastTrainingTab";
import { UsersTab } from "../components/admin/UsersTab";
import { CertificatesTab } from "../components/admin/CertificatesTab";
import { QuotationsTab } from "../components/admin/QuotationsTab";
import RichTextToolbar from "../components/RichTextToolbar";
import { AdminMarketingOverview } from "../components/marketing/AdminMarketingOverview";

const AdminDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { primaryColor, secondaryColor, companyName, logoUrl } = useTheme();
  
  // Helper function to format FastAPI validation errors
  const formatValidationError = (error) => {
    if (typeof error === 'string') return error;
    if (Array.isArray(error)) {
      // FastAPI validation errors are arrays of {type, loc, msg, input, ctx}
      return error.map(err => {
        const field = err.loc ? err.loc.join(' > ') : 'Unknown field';
        return `${field}: ${err.msg}`;
      }).join('; ');
    }
    if (typeof error === 'object' && error.detail) {
      return formatValidationError(error.detail);
    }
    return 'An error occurred';
  };
  
  const [companies, setCompanies] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [users, setUsers] = useState([]);
  const [activeTab, setActiveTab] = useState("programs");
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [costingSession, setCostingSession] = useState(null); // Session for costing modal
  const [financeSummary, setFinanceSummary] = useState({ invoices: [], totalInvoiced: 0, totalCollected: 0, totalOutstanding: 0, totalPayables: 0 });
  const currentYear = new Date().getFullYear();
  const [financeYear, setFinanceYear] = useState(currentYear);
  const [financeAvailableYears, setFinanceAvailableYears] = useState([currentYear, currentYear - 1, currentYear - 2]);
  
  // Search states
  const [companiesSearch, setCompaniesSearch] = useState("");
  const [programsSearch, setProgramsSearch] = useState("");
  const [sessionsSearch, setSessionsSearch] = useState("");
  const [usersSearch, setUsersSearch] = useState("");
  const [staffSearch, setStaffSearch] = useState("");
  const [filteredCompanies, setFilteredCompanies] = useState([]);
  const [filteredPrograms, setFilteredPrograms] = useState([]);
  const [filteredSessions, setFilteredSessions] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [filteredCoordinators, setFilteredCoordinators] = useState([]);
  const [filteredTrainers, setFilteredTrainers] = useState([]);
  const [filteredAssistantAdmins, setFilteredAssistantAdmins] = useState([]);
  
  // Sessions month filter - default to current month
  const [sessionsMonthFilter, setSessionsMonthFilter] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  
  // Indemnity records state
  const [indemnityRecords, setIndemnityRecords] = useState(null);
  const [indemnityDialogOpen, setIndemnityDialogOpen] = useState(false);
  const [printIndemnityRecord, setPrintIndemnityRecord] = useState(null);
  const [companySettings, setCompanySettings] = useState(null);
  
  // Bulk delete users state
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  
  // Checklist states
  const [checklistTemplates, setChecklistTemplates] = useState([]);
  const [checklistForm, setChecklistForm] = useState({ program_id: "", items: [""] });
  const [checklistDialogOpen, setChecklistDialogOpen] = useState(false);
  
  // Supervisor states
  const [supervisors, setSupervisors] = useState([]);
  const [supervisorForm, setSupervisorForm] = useState({
    email: "",
    password: "",
    full_name: "",
    company_id: ""
  });
  const [supervisorDialogOpen, setSupervisorDialogOpen] = useState(false);

  const [companyFormName, setCompanyFormName] = useState("");
  const [companyFormData, setCompanyFormData] = useState({
    name: '',
    registration_no: '',
    address_line1: '',
    address_line2: '',
    city: '',
    postcode: '',
    state: '',
    phone: '',
    email: '',
    contact_person: ''
  });
  const [companyDialogOpen, setCompanyDialogOpen] = useState(false);

  const [programForm, setProgramForm] = useState({ name: "", description: "", pass_percentage: 70 });
  const [programDialogOpen, setProgramDialogOpen] = useState(false);

  const [sessionForm, setSessionForm] = useState({
    program_id: "",
    company_id: "",
    location: "",
    venue_type: "client", // "mddrc" or "client" - affects F&B charges
    start_date: "",
    end_date: "",
    participants: [], // Participants to create/link
    supervisors: [], // Supervisors to create/link
    trainer_assignments: [],
    coordinator_id: "",
    // Marketing commission fields
    marketing_user_id: "",
    commission_type: "percentage",
    commission_rate: "",
    commission_fixed_amount: "",
    create_new_marketing: false, // Flag to create new marketing person
    new_marketing_name: "",
    new_marketing_id: "",
  });
  const [newParticipant, setNewParticipant] = useState({
    email: "",
    password: "",
    full_name: "",
    id_number: "",
    phone_number: "",
  });
  const [newSupervisor, setNewSupervisor] = useState({
    email: "",
    password: "",
    full_name: "",
    id_number: "",
    phone_number: "",
  });
  const [participantMatchStatus, setParticipantMatchStatus] = useState(null);
  const [supervisorMatchStatus, setSupervisorMatchStatus] = useState(null);
  const [newTrainerAssignment, setNewTrainerAssignment] = useState({
    trainer_id: "",
    role: "regular",
  });
  const [sessionDialogOpen, setSessionDialogOpen] = useState(false);
  const [editingSession, setEditingSession] = useState(null);

  
  // Reports Archive states
  const [allReports, setAllReports] = useState([]);
  const [loadingReports, setLoadingReports] = useState(false);
  const [reportsSearch, setReportsSearch] = useState("");
  const [filterCompany, setFilterCompany] = useState("all");
  const [filterProgram, setFilterProgram] = useState("all");
  const [filterStartDate, setFilterStartDate] = useState("");
  const [filterEndDate, setFilterEndDate] = useState("");
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportDetailsOpen, setReportDetailsOpen] = useState(false);
  const [marketingUsers, setMarketingUsers] = useState([]);


  // Certificates Repository states
  const [allCertificates, setAllCertificates] = useState([]);
  const [loadingCertificates, setLoadingCertificates] = useState(false);
  const [certificatesSearch, setCertificatesSearch] = useState("");
  const [filterCertSession, setFilterCertSession] = useState("all");
  const [filterCertProgram, setFilterCertProgram] = useState("all");

  
  // Password reset states
  const [resetPasswordUser, setResetPasswordUser] = useState(null);
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false);
  const [newPasswordForm, setNewPasswordForm] = useState({
    newPassword: "",
    confirmPassword: "",
  });
  const [editSessionDialogOpen, setEditSessionDialogOpen] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [bulkUploadSession, setBulkUploadSession] = useState(null);  // Session for standalone bulk upload

  const [trainerForm, setTrainerForm] = useState({
    email: "",
    password: "",
    full_name: "",
    id_number: "",
  });
  const [trainerDialogOpen, setTrainerDialogOpen] = useState(false);

  const [coordinatorForm, setCoordinatorForm] = useState({
    email: "",
    password: "",
    full_name: "",
    id_number: "",
    additional_roles: [],
  });
  const [coordinatorDialogOpen, setCoordinatorDialogOpen] = useState(false);

  const [assistantAdminForm, setAssistantAdminForm] = useState({
    email: "",
    password: "",
    full_name: "",
    id_number: "",
    additional_roles: [],
  });
  const [assistantAdminDialogOpen, setAssistantAdminDialogOpen] = useState(false);

  // Quotations state
  const [quotations, setQuotations] = useState([]);
  const [descriptionItems, setDescriptionItems] = useState([]);
  const [allClients, setAllClients] = useState([]);
  const [pendingQuotations, setPendingQuotations] = useState([]);
  const [quotationFilter, setQuotationFilter] = useState("pending_approval");
  const [approveDialogOpen, setApproveDialogOpen] = useState(false);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [selectedQuotation, setSelectedQuotation] = useState(null);
  const [rejectRemarks, setRejectRemarks] = useState("");
  const [viewQuotationDialog, setViewQuotationDialog] = useState(false);
  
  // PDF Templates state
  const [pdfTemplates, setPdfTemplates] = useState({
    cover_letter: "",
    terms_conditions_pages: ""
  });
  const [pdfTemplatesLoading, setPdfTemplatesLoading] = useState(false);
  const [showPdfTemplatesDialog, setShowPdfTemplatesDialog] = useState(false);
  const [showPdfPreview, setShowPdfPreview] = useState(false);
  
  // Refs for rich text toolbar
  const coverLetterRef = useRef(null);
  const termsRef = useRef(null);

  // Finance user form
  const [financeForm, setFinanceForm] = useState({
    email: "",
    password: "",
    full_name: "",
    id_number: "",
  });
  const [financeDialogOpen, setFinanceDialogOpen] = useState(false);

  // Edit states
  const [editingProgram, setEditingProgram] = useState(null);
  const [editProgramDialogOpen, setEditProgramDialogOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  const [editCompanyDialogOpen, setEditCompanyDialogOpen] = useState(false);
  const [editingStaff, setEditingStaff] = useState(null);
  const [editStaffDialogOpen, setEditStaffDialogOpen] = useState(false);
  const [editStaffForm, setEditStaffForm] = useState({
    full_name: "",
    email: "",
    id_number: "",
    additional_roles: [],
  });
  
  // Edit participant states
  const [editingParticipant, setEditingParticipant] = useState(null);
  const [editParticipantDialogOpen, setEditParticipantDialogOpen] = useState(false);
  const [editParticipantForm, setEditParticipantForm] = useState({
    full_name: "",
    id_number: "",
    phone_number: "",
  });
  
  // Delete confirmation states
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  // Past Training states
  const [pastTrainingSessions, setPastTrainingSessions] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [loadingPastTraining, setLoadingPastTraining] = useState(false);
  const [expandedPastSession, setExpandedPastSession] = useState(null);

  useEffect(() => {
    loadData();
    loadChecklistTemplates();
  }, []);

  // Check participant existence with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      checkUserExists(
        newParticipant.full_name,
        newParticipant.email,
        newParticipant.id_number,
        setParticipantMatchStatus
      );
    }, 500);
    return () => clearTimeout(timer);
  }, [newParticipant.full_name, newParticipant.email, newParticipant.id_number]);

  // Check supervisor existence with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      checkUserExists(
        newSupervisor.full_name,
        newSupervisor.email,
        newSupervisor.id_number,
        setSupervisorMatchStatus
      );
    }, 500);
    return () => clearTimeout(timer);
  }, [newSupervisor.full_name, newSupervisor.email, newSupervisor.id_number]);

  const loadData = async () => {
    try {
      // Add timestamp to prevent caching
      const timestamp = new Date().getTime();
      const [companiesRes, programsRes, sessionsRes, usersRes] = await Promise.all([
        axiosInstance.get(`/companies?_t=${timestamp}`),
        axiosInstance.get(`/programs?_t=${timestamp}`),
        axiosInstance.get(`/sessions?_t=${timestamp}`),
        axiosInstance.get(`/users?_t=${timestamp}`),
      ]);
      setCompanies(companiesRes.data);
      setPrograms(programsRes.data);
      setSessions(sessionsRes.data);
      setUsers(usersRes.data);
      
      // Initialize filtered lists
      setFilteredCompanies(companiesRes.data);
      setFilteredPrograms(programsRes.data);
      setFilteredSessions(sessionsRes.data);
      setFilteredUsers(usersRes.data);
      
      // Load marketing users for session creation
      try {
        const marketingRes = await axiosInstance.get(`/finance/marketing-users?_t=${timestamp}`);
        setMarketingUsers(marketingRes.data);
      } catch (e) {
        // Marketing users endpoint might fail if no finance access, ignore
        console.log('Marketing users not loaded:', e.message);
      }
      
      // Load quotations (admin sees all)
      try {
        const quotationsRes = await axiosInstance.get(`/marketing/quotations?_t=${timestamp}`);
        setQuotations(quotationsRes.data);
        setPendingQuotations(quotationsRes.data.filter(q => q.status === 'pending_approval'));
      } catch (e) {
        console.log('Quotations not loaded:', e.message);
      }
      
      // Load description items for quotations
      try {
        const descItemsRes = await axiosInstance.get(`/marketing/description-items?_t=${timestamp}`);
        setDescriptionItems(descItemsRes.data || []);
      } catch (e) {
        console.log('Description items not loaded:', e.message);
      }
      
      // Load all clients (admin only)
      try {
        const clientsRes = await axiosInstance.get(`/marketing/clients/all?_t=${timestamp}`);
        setAllClients(clientsRes.data || []);
      } catch (e) {
        console.log('All clients not loaded:', e.message);
      }
      
      // Load finance summary with year filter
      await loadFinanceSummaryByYear(financeYear);
    } catch (error) {
      toast.error("Failed to load data");
    }
  };

  // Load finance summary by year
  const loadFinanceSummaryByYear = async (year) => {
    try {
      const timestamp = Date.now();
      const dashboardRes = await axiosInstance.get(`/finance/dashboard?year=${year}&_t=${timestamp}`);
      const data = dashboardRes.data;
      
      // Set available years from API response
      if (data.available_years && data.available_years.length > 0) {
        const defaultYears = [currentYear, currentYear - 1, currentYear - 2];
        const mergedYears = [...new Set([...defaultYears, ...data.available_years])].sort((a, b) => b - a);
        setFinanceAvailableYears(mergedYears);
      }
      
      setFinanceSummary({
        invoices: [],
        totalInvoiced: data.financials?.total_issued || 0,
        totalCollected: data.financials?.total_collected || 0,
        totalOutstanding: data.financials?.outstanding_receivables || 0,
        totalPayables: data.payables?.pending_total || 0,
        invoiceCount: data.invoices?.total || 0
      });
    } catch (e) {
      console.log('Finance data not loaded:', e.message);
    }
  };

  // Reload finance when year changes
  useEffect(() => {
    loadFinanceSummaryByYear(financeYear);
  }, [financeYear]);

  // Quotation approval functions
  const handleApproveQuotation = async (quotationId) => {
    try {
      await axiosInstance.post(`/marketing/quotations/${quotationId}/approve`);
      toast.success('Quotation approved');
      loadData();
      setApproveDialogOpen(false);
      setSelectedQuotation(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to approve quotation');
    }
  };

  const handleRejectQuotation = async () => {
    if (!selectedQuotation) return;
    try {
      await axiosInstance.post(`/marketing/quotations/${selectedQuotation.id}/reject`, { remarks: rejectRemarks });
      toast.success('Quotation rejected');
      loadData();
      setRejectDialogOpen(false);
      setSelectedQuotation(null);
      setRejectRemarks('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject quotation');
    }
  };

  // PDF Templates management
  const loadPdfTemplates = async () => {
    try {
      const res = await axiosInstance.get('/marketing/pdf-templates');
      setPdfTemplates({
        cover_letter: res.data.cover_letter || "",
        terms_conditions_pages: res.data.terms_conditions_pages || ""
      });
    } catch (e) {
      console.log('PDF templates not loaded:', e.message);
    }
  };

  const savePdfTemplates = async () => {
    setPdfTemplatesLoading(true);
    try {
      await axiosInstance.put('/marketing/pdf-templates', pdfTemplates);
      toast.success('PDF templates saved successfully');
      setShowPdfTemplatesDialog(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save templates');
    } finally {
      setPdfTemplatesLoading(false);
    }
  };

  const filteredQuotations = quotations.filter(q => {
    if (quotationFilter === 'all') return true;
    return q.status === quotationFilter;
  });

  const getQuotationStatusBadge = (status) => {
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
      pending_approval: 'Pending',
      approved: 'Approved',
      rejected: 'Rejected',
      sent: 'Sent',
      accepted: 'Accepted',
      declined: 'Declined'
    };
    return <Badge className={`${colors[status] || 'bg-gray-500'} text-white`}>{labels[status] || status}</Badge>;
  };
  
  // Search filtering effects
  useEffect(() => {
    if (!companiesSearch) {
      setFilteredCompanies(companies);
    } else {
      const filtered = companies.filter(c =>
        c.name.toLowerCase().includes(companiesSearch.toLowerCase())
      );
      setFilteredCompanies(filtered);
    }
  }, [companiesSearch, companies]);
  
  useEffect(() => {
    if (!programsSearch) {
      setFilteredPrograms(programs);
    } else {
      const filtered = programs.filter(p =>
        p.name.toLowerCase().includes(programsSearch.toLowerCase()) ||
        (p.description && p.description.toLowerCase().includes(programsSearch.toLowerCase()))
      );
      setFilteredPrograms(filtered);
    }
  }, [programsSearch, programs]);
  
  useEffect(() => {
    let filtered = sessions;
    
    // Apply month filter first
    if (sessionsMonthFilter && sessionsMonthFilter !== "all") {
      filtered = filtered.filter(s => {
        // Check start_date or created_at for the month
        const sessionDate = s.start_date || s.created_at;
        if (sessionDate) {
          const dateStr = sessionDate.substring(0, 7); // Get YYYY-MM
          return dateStr === sessionsMonthFilter;
        }
        return false;
      });
    }
    
    // Then apply text search
    if (sessionsSearch) {
      filtered = filtered.filter(s =>
        s.name.toLowerCase().includes(sessionsSearch.toLowerCase()) ||
        (s.company_name && s.company_name.toLowerCase().includes(sessionsSearch.toLowerCase())) ||
        (s.program_name && s.program_name.toLowerCase().includes(sessionsSearch.toLowerCase())) ||
        (s.location && s.location.toLowerCase().includes(sessionsSearch.toLowerCase()))
      );
    }
    
    setFilteredSessions(filtered);
  }, [sessionsSearch, sessionsMonthFilter, sessions]);
  
  useEffect(() => {
    if (!usersSearch) {
      setFilteredUsers(users);
    } else {
      const filtered = users.filter(u =>
        u.full_name.toLowerCase().includes(usersSearch.toLowerCase()) ||
        (u.email && u.email.toLowerCase().includes(usersSearch.toLowerCase())) ||
        (u.id_number && u.id_number.toLowerCase().includes(usersSearch.toLowerCase()))
      );
      setFilteredUsers(filtered);
    }
  }, [usersSearch, users]);
  
  // Staff search filtering
  useEffect(() => {
    const coords = users.filter((u) => u.role === "coordinator");
    const trains = users.filter((u) => u.role === "trainer");
    const assistants = users.filter((u) => u.role === "assistant_admin");
    
    if (!staffSearch) {
      setFilteredCoordinators(coords);
      setFilteredTrainers(trains);
      setFilteredAssistantAdmins(assistants);
    } else {
      const searchLower = staffSearch.toLowerCase();
      setFilteredCoordinators(coords.filter(c =>
        c.full_name.toLowerCase().includes(searchLower) ||
        (c.email && c.email.toLowerCase().includes(searchLower)) ||
        (c.id_number && c.id_number.toLowerCase().includes(searchLower))
      ));
      setFilteredTrainers(trains.filter(t =>
        t.full_name.toLowerCase().includes(searchLower) ||
        (t.email && t.email.toLowerCase().includes(searchLower)) ||
        (t.id_number && t.id_number.toLowerCase().includes(searchLower))
      ));
      setFilteredAssistantAdmins(assistants.filter(a =>
        a.full_name.toLowerCase().includes(searchLower) ||
        (a.email && a.email.toLowerCase().includes(searchLower)) ||
        (a.id_number && a.id_number.toLowerCase().includes(searchLower))
      ));
    }
  }, [staffSearch, users]);

  const loadChecklistTemplates = async () => {
    try {
      const response = await axiosInstance.get("/checklist-templates");
      setChecklistTemplates(response.data);
    } catch (error) {
      console.error("Failed to load checklist templates:", error);
    }
  };

  // Check if user exists for real-time feedback
  const checkUserExists = async (full_name, email, id_number, setMatchStatus) => {
    if (!full_name && !email && !id_number) {
      setMatchStatus(null);
      return;
    }

    try {
      const response = await axiosInstance.post("/users/check-exists", null, {
        params: { full_name, email, id_number }
      });
      
      if (response.data.exists) {
        setMatchStatus({
          exists: true,
          user: response.data.user
        });
      } else {
        setMatchStatus({ exists: false });
      }
    } catch (error) {
      console.error("Error checking user existence:", error);
      setMatchStatus(null);
    }
  };

  // Supervisor functions removed - now created during session creation

  const handleCreateCompany = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/companies", companyFormData);
      toast.success("Company created successfully");
      setCompanyFormData({
        name: '', registration_no: '', address_line1: '', address_line2: '',
        city: '', postcode: '', state: '', phone: '', email: '', contact_person: ''
      });
      setCompanyDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create company");
    }
  };

  const handleCreateProgram = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/programs", programForm);
      toast.success("Program created successfully");
      setProgramForm({ name: "", description: "", pass_percentage: 70 });
      setProgramDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create program");
    }
  };

  const handleCreateTrainer = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/auth/register", {
        ...trainerForm,
        role: "trainer",
      });
      toast.success("Trainer created successfully");
      setTrainerForm({ email: "", password: "", full_name: "", id_number: "" });
      setTrainerDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create trainer");
    }
  };

  const handleCreateCoordinator = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/auth/register", {
        ...coordinatorForm,
        role: "coordinator",
      });
      toast.success("Coordinator created successfully");
      setCoordinatorForm({ email: "", password: "", full_name: "", id_number: "", additional_roles: [] });
      setCoordinatorDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create coordinator");
    }
  };

  const handleCreateAssistantAdmin = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/auth/register", {
        ...assistantAdminForm,
        role: "assistant_admin",
      });
      toast.success("Assistant Admin created successfully");
      setAssistantAdminForm({ email: "", password: "", full_name: "", id_number: "", additional_roles: [] });
      setAssistantAdminDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create assistant admin");
    }
  };

  const handleCreateFinance = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/auth/register", {
        ...financeForm,
        role: "finance",
      });
      toast.success("Finance user created successfully");
      setFinanceForm({ email: "", password: "", full_name: "", id_number: "" });
      setFinanceDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create finance user");
    }
  };

  const handleAddParticipant = () => {
    if (!newParticipant.full_name || !newParticipant.id_number) {
      toast.error("Please fill all required fields (name and ID number)");
      return;
    }
    // Set default password for new participants
    const participantWithDefaults = {
      ...newParticipant,
      password: "mddrc1", // Default password
      email: newParticipant.email || "" // Optional
    };
    setSessionForm({
      ...sessionForm,
      participants: [...sessionForm.participants, participantWithDefaults],
    });
    setNewParticipant({ email: "", password: "", full_name: "", id_number: "", phone_number: "" });
    setParticipantMatchStatus(null);
    
    if (participantMatchStatus?.exists) {
      toast.success(`✓ Existing participant "${newParticipant.full_name}" will be linked to this session`);
    } else {
      toast.success(`New participant "${newParticipant.full_name}" added (Login: IC number, Password: mddrc1)`);
    }
  };

  const handleAddSupervisor = () => {
    if (!newSupervisor.email || !newSupervisor.password || !newSupervisor.full_name || !newSupervisor.id_number) {
      toast.error("Please fill all required fields (name, email, password, ID number)");
      return;
    }
    setSessionForm({
      ...sessionForm,
      supervisors: [...sessionForm.supervisors, { ...newSupervisor }],
    });
    setNewSupervisor({ email: "", password: "", full_name: "", id_number: "", phone_number: "" });
    setSupervisorMatchStatus(null);
    
    if (supervisorMatchStatus?.exists) {
      toast.success(`✓ Existing supervisor "${newSupervisor.full_name}" will be linked to this session`);
    } else {
      toast.success(`New supervisor "${newSupervisor.full_name}" added to list`);
    }
  };

  const handleRemoveParticipant = (index) => {
    const updated = sessionForm.participants.filter((_, i) => i !== index);
    setSessionForm({ ...sessionForm, participants: updated });
  };

  const handleAddTrainerAssignment = () => {
    if (!newTrainerAssignment.trainer_id) {
      toast.error("Please select a trainer");
      return;
    }
    // Check if trainer already assigned
    if (sessionForm.trainer_assignments.some(t => t.trainer_id === newTrainerAssignment.trainer_id)) {
      toast.error("Trainer already assigned to this session");
      return;
    }
    setSessionForm({
      ...sessionForm,
      trainer_assignments: [...sessionForm.trainer_assignments, { ...newTrainerAssignment }],
    });
    setNewTrainerAssignment({ trainer_id: "", role: "regular" });
    toast.success("Trainer assigned");
  };

  const handleRemoveTrainerAssignment = (index) => {
    const updated = sessionForm.trainer_assignments.filter((_, i) => i !== index);
    setSessionForm({ ...sessionForm, trainer_assignments: updated });
  };

  const handleCreateSession = async (e) => {
    e.preventDefault();
    
    if (sessionForm.participants.length === 0) {
      toast.error("Please add at least one participant");
      return;
    }

    try {
      const program = programs.find(p => p.id === sessionForm.program_id);
      if (!program) {
        toast.error("Please select a program");
        return;
      }

      const response = await axiosInstance.post("/sessions", {
        name: program.name,
        program_id: sessionForm.program_id,
        company_id: sessionForm.company_id,
        location: sessionForm.location,
        start_date: sessionForm.start_date,
        end_date: sessionForm.end_date,
        participant_ids: [],  // No pre-selected participants
        participants: sessionForm.participants,
        supervisor_ids: [],  // No pre-selected supervisors
        supervisors: sessionForm.supervisors,
        trainer_assignments: sessionForm.trainer_assignments,
        coordinator_id: sessionForm.coordinator_id || null,
        // Marketing commission fields
        marketing_user_id: sessionForm.marketing_user_id || null,
        commission_type: sessionForm.commission_type || null,
        commission_rate: sessionForm.commission_rate ? parseFloat(sessionForm.commission_rate) : null,
        commission_fixed_amount: sessionForm.commission_fixed_amount ? parseFloat(sessionForm.commission_fixed_amount) : null,
      });

      // Show results of participant/supervisor matching
      let successMessage = `Session created successfully!`;
      if (response.data.participant_results && response.data.participant_results.length > 0) {
        const existingCount = response.data.participant_results.filter(p => p.is_existing).length;
        const newCount = response.data.participant_results.filter(p => !p.is_existing).length;
        if (existingCount > 0) {
          successMessage += ` Linked ${existingCount} existing participant(s).`;
        }
        if (newCount > 0) {
          successMessage += ` Created ${newCount} new participant(s).`;
        }
      }
      if (response.data.supervisor_results && response.data.supervisor_results.length > 0) {
        const existingCount = response.data.supervisor_results.filter(s => s.is_existing).length;
        const newCount = response.data.supervisor_results.filter(s => !s.is_existing).length;
        if (existingCount > 0) {
          successMessage += ` Linked ${existingCount} existing supervisor(s).`;
        }
        if (newCount > 0) {
          successMessage += ` Created ${newCount} new supervisor(s).`;
        }
      }

      toast.success(successMessage);
      setSessionForm({
        program_id: "",
        company_id: "",
        location: "",
        start_date: "",
        end_date: "",
        participants: [],
        supervisors: [],
        trainer_assignments: [],
        coordinator_id: "",
        marketing_user_id: "",
        commission_type: "percentage",
        commission_rate: "",
        commission_fixed_amount: "",
      });
      setSessionDialogOpen(false);
      loadData();
    } catch (error) {
      console.error("Session creation error:", error);
      const errorMessage = error.response?.data?.detail 
        ? formatValidationError(error.response.data.detail)
        : "Failed to create session";
      toast.error(errorMessage);
    }
  };

  const handleEditSession = (session) => {
    setEditingSession({
      ...session,
      newParticipants: [],
    });
    setEditSessionDialogOpen(true);
  };

  const handleAddParticipantToEdit = () => {
    if (!newParticipant.full_name || !newParticipant.id_number) {
      toast.error("Please fill required fields (name and ID number)");
      return;
    }
    // Set default password for new participants
    const participantWithDefaults = {
      ...newParticipant,
      password: "mddrc1", // Default password
      email: newParticipant.email || "" // Optional
    };
    setEditingSession({
      ...editingSession,
      newParticipants: [...(editingSession.newParticipants || []), participantWithDefaults],
    });
    setNewParticipant({ email: "", password: "", full_name: "", id_number: "", phone_number: "" });
  };

  const handleBulkUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      toast.error("Please upload an Excel file (.xlsx or .xls)");
      return;
    }

    if (!editingSession?.id) {
      toast.error("Please save the session first before uploading participants");
      return;
    }

    setUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axiosInstance.post(
        `/sessions/${editingSession.id}/participants/bulk-upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      const { total_uploaded, new_companies_created } = response.data;
      
      let message = `✓ Successfully uploaded ${total_uploaded} participant(s)!`;
      if (new_companies_created && new_companies_created.length > 0) {
        message += `\n✓ Created new companies: ${new_companies_created.join(', ')}`;
      }
      
      toast.success(message);
      setUploadDialogOpen(false);
      
      // Reload session data to show new participants
      loadData();
      
      // Reset file input
      event.target.value = '';
      
    } catch (error) {
      console.error('Bulk upload error:', error);
      const errorMessage = error.response?.data?.detail || "Failed to process Excel file";
      toast.error(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  // Standalone bulk upload for session cards (same as Coordinator/Assistant Admin)
  const handleStandaloneBulkUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      toast.error("Please upload an Excel file (.xlsx or .xls)");
      return;
    }

    if (!bulkUploadSession?.id) {
      toast.error("No session selected for upload");
      return;
    }

    setUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axiosInstance.post(
        `/sessions/${bulkUploadSession.id}/participants/bulk-upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      const { total_uploaded, new_companies_created } = response.data;
      
      let message = `✓ Successfully uploaded ${total_uploaded} participant(s)!`;
      if (new_companies_created && new_companies_created.length > 0) {
        message += `\n✓ Created new companies: ${new_companies_created.join(', ')}`;
      }
      
      toast.success(message);
      setBulkUploadSession(null);
      
      // Reload session data to show new participants
      loadData();
      
      // Reset file input
      event.target.value = '';
      
    } catch (error) {
      console.error('Bulk upload error:', error);
      const errorMessage = error.response?.data?.detail || "Failed to process Excel file";
      toast.error(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveNewParticipant = (index) => {
    const updated = editingSession.newParticipants.filter((_, i) => i !== index);
    setEditingSession({ ...editingSession, newParticipants: updated });
  };

  const handleUpdateSession = async () => {
    try {
      // Create new participants if any
      const newParticipantIds = [];
      if (editingSession.newParticipants && editingSession.newParticipants.length > 0) {
        for (const participant of editingSession.newParticipants) {
          // First check if user already exists by IC number
          try {
            const checkResponse = await axiosInstance.post("/users/check-exists", null, {
              params: { id_number: participant.id_number }
            });
            if (checkResponse.data.exists && checkResponse.data.user) {
              // User exists, use their ID
              newParticipantIds.push(checkResponse.data.user.id);
              toast.info(`Existing user "${participant.full_name}" linked to session`);
              continue;
            }
          } catch (checkErr) {
            // Check endpoint failed, proceed with registration attempt
            console.log("Check exists failed, attempting registration");
          }
          
          // User doesn't exist, register new one
          try {
            const response = await axiosInstance.post("/auth/register", {
              ...participant,
              role: "participant",
              company_id: editingSession.company_id,
              location: editingSession.location,
            });
            newParticipantIds.push(response.data.id);
          } catch (regErr) {
            // If registration fails due to existing user, extract their ID
            if (regErr.response?.data?.detail?.includes("already exists")) {
              // Try to find the user via users list
              const usersResp = await axiosInstance.get("/users");
              const existingUser = usersResp.data.find(u => u.id_number === participant.id_number);
              if (existingUser) {
                newParticipantIds.push(existingUser.id);
                toast.info(`Existing user "${participant.full_name}" linked to session`);
              } else {
                throw new Error(`User with IC ${participant.id_number} exists but could not be found`);
              }
            } else {
              throw regErr;
            }
          }
        }
      }

      // Update session with ALL fields including assistant coordinators
      await axiosInstance.put(`/sessions/${editingSession.id}`, {
        location: editingSession.location,
        start_date: editingSession.start_date,
        end_date: editingSession.end_date,
        participant_ids: [...editingSession.participant_ids, ...newParticipantIds],
        trainer_assignments: editingSession.trainer_assignments || [],
        coordinator_id: editingSession.coordinator_id || null,
        assistant_coordinator_ids: editingSession.assistant_coordinator_ids || [],
      });

      toast.success("Session updated successfully");
      setEditSessionDialogOpen(false);
      setEditingSession(null);
      setNewParticipant({ email: "", password: "", full_name: "", id_number: "" });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update session");
    }
  };

  const trainers = users.filter((u) => u.role === "trainer");
  const coordinators = users.filter((u) => u.role === "coordinator");
  const assistantAdmins = users.filter((u) => u.role === "assistant_admin");
  
  // All staff who can be assigned as session coordinator (includes coordinators, assistant admins, trainers)
  const allStaffForCoordinator = users.filter((u) => 
    ["coordinator", "assistant_admin", "trainer", "admin"].includes(u.role)
  );

  const getTrainerName = (trainerId) => {
    const trainer = trainers.find(t => t.id === trainerId);
    return trainer ? trainer.full_name : "Unknown";
  };

  const getCoordinatorName = (coordinatorId) => {
    // Search in all users, not just coordinators
    const user = users.find(u => u.id === coordinatorId);
    return user ? user.full_name : "Unknown";
  };

  // Edit/Delete handlers
  const handleEditProgram = (program) => {
    setEditingProgram({ ...program });
    setEditProgramDialogOpen(true);
  };

  const handleUpdateProgram = async () => {
    try {
      await axiosInstance.put(`/programs/${editingProgram.id}`, {
        name: editingProgram.name,
        description: editingProgram.description,
        pass_percentage: editingProgram.pass_percentage,
      });
      toast.success("Program updated successfully");
      setEditProgramDialogOpen(false);
      setEditingProgram(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update program");
    }
  };

  const handleEditCompany = (company) => {
    setEditingCompany({ ...company });
    setEditCompanyDialogOpen(true);
  };

  const handleUpdateCompany = async () => {
    try {
      await axiosInstance.put(`/companies/${editingCompany.id}`, {
        name: editingCompany.name,
        registration_no: editingCompany.registration_no,
        address_line1: editingCompany.address_line1,
        address_line2: editingCompany.address_line2,
        city: editingCompany.city,
        postcode: editingCompany.postcode,
        state: editingCompany.state,
        phone: editingCompany.phone,
        email: editingCompany.email,
        contact_person: editingCompany.contact_person
      });
      toast.success("Company updated successfully");
      setEditCompanyDialogOpen(false);
      setEditingCompany(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update company");
    }
  };

  const handleDeleteClick = (type, item) => {
    setDeleteTarget({ type, item });
    setDeleteConfirmOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    
    try {
      const { type, item } = deleteTarget;
      
      if (type === "program") {
        await axiosInstance.delete(`/programs/${item.id}`);
        toast.success("Program deleted successfully");
      } else if (type === "company") {
        await axiosInstance.delete(`/companies/${item.id}`);
        toast.success("Company deleted successfully");
      } else if (type === "session") {
        const response = await axiosInstance.delete(`/sessions/${item.id}`);
        const recordsDeleted = response.data?.records_deleted || 0;
        
        if (recordsDeleted === 0) {
          toast.warning("Session not found in database (may have been already deleted). Refreshing...", { duration: 3000 });
        } else {
          toast.success(`Session deleted successfully! ${recordsDeleted} related records removed.`, { duration: 4000 });
        }
      } else if (type === "trainer" || type === "coordinator" || type === "assistant_admin" || type === "user") {
        await axiosInstance.delete(`/users/${item.id}`);
        toast.success(`${type.replace('_', ' ')} deleted successfully`);
      }
      
      setDeleteConfirmOpen(false);
      setDeleteTarget(null);
      
      // Reload data to refresh the list
      await loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete item");
    }
  };

  const handleToggleUserStatus = async (userId, currentStatus) => {
    try {
      const endpoint = currentStatus ? "deactivate" : "activate";
      await axiosInstance.put(`/users/${userId}/${endpoint}`);
      toast.success(`User ${currentStatus ? 'deactivated' : 'activated'} successfully`);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update user status");
    }
  };

  // Bulk delete users
  const handleBulkDeleteUsers = async () => {
    if (selectedUsers.length === 0) return;
    
    try {
      let successCount = 0;
      let failCount = 0;
      
      for (const userId of selectedUsers) {
        try {
          await axiosInstance.delete(`/users/${userId}`);
          successCount++;
        } catch (error) {
          failCount++;
          console.error(`Failed to delete user ${userId}:`, error);
        }
      }
      
      if (successCount > 0) {
        toast.success(`Successfully deleted ${successCount} user(s)`);
      }
      if (failCount > 0) {
        toast.error(`Failed to delete ${failCount} user(s)`);
      }
      
      setSelectedUsers([]);
      setBulkDeleteDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error("Failed to delete users");
    }
  };

  // View Indemnity Records for a session
  const handleViewIndemnityRecords = async (session) => {
    try {
      const [recordsRes, settingsRes] = await Promise.all([
        axiosInstance.get(`/sessions/${session.id}/indemnity-records`),
        axiosInstance.get('/finance/company-settings').catch(() => ({ data: {} }))
      ]);
      setIndemnityRecords(recordsRes.data);
      setCompanySettings(settingsRes.data);
      setIndemnityDialogOpen(true);
    } catch (error) {
      toast.error("Failed to load indemnity records");
    }
  };

  // Export Indemnity Records
  const handleExportIndemnityRecords = async () => {
    if (!indemnityRecords?.session_id) return;
    
    try {
      const response = await axiosInstance.get(
        `/sessions/${indemnityRecords.session_id}/indemnity-records/export`,
        { responseType: 'blob' }
      );
      
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Indemnity_Records_${indemnityRecords.session_name || 'Session'}.xlsx`;
      link.click();
      window.URL.revokeObjectURL(url);
      
      toast.success("Indemnity records exported!");
    } catch (error) {
      toast.error("Failed to export indemnity records");
    }
  };

  const toggleUserSelection = (userId) => {
    setSelectedUsers(prev => 
      prev.includes(userId) 
        ? prev.filter(id => id !== userId) 
        : [...prev, userId]
    );
  };

  const toggleAllUsers = (userList) => {
    const userIds = userList.map(u => u.id);
    const allSelected = userIds.every(id => selectedUsers.includes(id));
    
    if (allSelected) {
      setSelectedUsers(prev => prev.filter(id => !userIds.includes(id)));
    } else {
      setSelectedUsers(prev => [...new Set([...prev, ...userIds])]);
    }
  };

  const handleEditStaff = (staff) => {
    setEditingStaff(staff);
    setEditStaffForm({
      full_name: staff.full_name,
      email: staff.email,
      id_number: staff.id_number,
      additional_roles: staff.additional_roles || [],
    });
    setEditStaffDialogOpen(true);
  };

  const handleUpdateStaff = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.put(`/users/${editingStaff.id}`, editStaffForm);
      toast.success(`${editingStaff.role.replace('_', ' ')} updated successfully`);
      setEditStaffDialogOpen(false);
      setEditingStaff(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update staff member");
    }
  };

  // Handle participant update
  const handleUpdateParticipant = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.put(`/users/${editingParticipant.id}`, editParticipantForm);
      toast.success("Participant updated successfully");
      setEditParticipantDialogOpen(false);
      setEditingParticipant(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update participant");
    }
  };

  const loadPastTraining = async () => {
    try {
      setLoadingPastTraining(true);
      const params = new URLSearchParams();
      if (selectedMonth && selectedYear) {
        params.append('month', selectedMonth);
        params.append('year', selectedYear);
      }
      const response = await axiosInstance.get(`/sessions/past-training?${params}`);
      setPastTrainingSessions(response.data);
    } catch (error) {
      toast.error("Failed to load past training sessions");
      setPastTrainingSessions([]);
    } finally {
      setLoadingPastTraining(false);
    }
  };

  const handlePastSessionClick = (session) => {
    setExpandedPastSession(expandedPastSession?.id === session.id ? null : session);
  };

  const generateYearOptions = () => {
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let year = currentYear; year >= currentYear - 10; year--) {
      years.push(year);
    }
    return years;
  };

  const generateMonthOptions = () => {
    return [
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
  };



  // Reports Archive functions
  const loadAllReports = async () => {
    setLoadingReports(true);
    try {
      const params = {};
      
      if (reportsSearch) params.search = reportsSearch;
      if (filterCompany && filterCompany !== "all") params.company_id = filterCompany;
      if (filterProgram && filterProgram !== "all") params.program_id = filterProgram;
      if (filterStartDate) params.start_date = filterStartDate;
      if (filterEndDate) params.end_date = filterEndDate;
      
      const response = await axiosInstance.get("/training-reports/admin/all", { params });
      setAllReports(response.data.reports || []);
    } catch (error) {
      console.error("Failed to load reports:", error);
      toast.error(error.response?.data?.detail || "Failed to load training reports");
    } finally {
      setLoadingReports(false);
    }
  };


  // Certificates Repository functions
  const loadAllCertificates = async () => {
    setLoadingCertificates(true);
    try {
      const response = await axiosInstance.get("/certificates/repository");
      setAllCertificates(response.data || []);
    } catch (error) {
      console.error("Failed to load certificates:", error);
      toast.error(error.response?.data?.detail || "Failed to load certificates");
    } finally {
      setLoadingCertificates(false);
    }
  };

  const handleDownloadCertificate = async (certificateUrl, participantName) => {
    try {
      // Extract session_id and participant_id from URL if needed, or use direct URL
      const response = await axiosInstance.get(certificateUrl, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `${participantName.replace(/\s+/g, '_')}_certificate.pdf`;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success("Certificate downloaded!");
    } catch (error) {
      toast.error("Failed to download certificate");
    }
  };


  const handleDownloadReportPDF = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/training-reports/${sessionId}/download-pdf`, {
        responseType: 'blob'
      });
      
      // Create blob with proper MIME type
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      
      // Create download link
      const link = document.createElement('a');
      link.href = url;
      link.download = `Training_Report_${sessionId}.pdf`;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
      
      toast.success("Report PDF downloaded!");
    } catch (error) {
      console.error("Download error:", error);
      toast.error(error.response?.data?.detail || "Failed to download report");
    }
  };

  const handleViewReportDetails = (report) => {
    setSelectedReport(report);
    setReportDetailsOpen(true);
  };

  // Load reports when Reports tab is selected
  useEffect(() => {
    if (activeTab === "reports" && allReports.length === 0) {
      loadAllReports();
    }
  }, [activeTab]);

  const handleCreateChecklistTemplate = async (e) => {
    e.preventDefault();
    if (!checklistForm.program_id || checklistForm.items.filter(i => i.trim()).length === 0) {
      toast.error("Please add a checklist item");
      return;
    }
    
    try {
      // Check if template exists for this program
      const existingTemplate = checklistTemplates.find(t => t.program_id === checklistForm.program_id);
      
      if (existingTemplate) {
        // Update existing template by adding new items
        const updatedItems = [...existingTemplate.items, ...checklistForm.items.filter(i => i.trim())];
        await axiosInstance.put(`/checklist-templates/${existingTemplate.id}`, {
          program_id: checklistForm.program_id,
          items: updatedItems
        });
        toast.success("Checklist item added successfully");
      } else {
        // Create new template
        await axiosInstance.post("/checklist-templates", {
          program_id: checklistForm.program_id,
          items: checklistForm.items.filter(i => i.trim())
        });
        toast.success("Checklist item added successfully");
      }
      
      setChecklistDialogOpen(false);
      setChecklistForm({ program_id: "", items: [""] });
      loadChecklistTemplates();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to add checklist item");
    }
  };

  const handleAddChecklistItem = () => {
    setChecklistForm({ ...checklistForm, items: [...checklistForm.items, ""] });
  };

  const handleRemoveChecklistItem = (index) => {
    const newItems = checklistForm.items.filter((_, i) => i !== index);
    setChecklistForm({ ...checklistForm, items: newItems });
  };

  const handleChecklistItemChange = (index, value) => {
    const newItems = [...checklistForm.items];
    newItems[index] = value;
    setChecklistForm({ ...checklistForm, items: newItems });
  };

  const handleDeleteChecklistTemplate = async (templateId) => {
    try {
      await axiosInstance.delete(`/checklist-templates/${templateId}`);
      toast.success("Checklist template deleted");
      loadChecklistTemplates();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete template");
    }
  };

  const handleDeleteChecklistItem = async (templateId, itemIndex) => {
    try {
      const template = checklistTemplates.find(t => t.id === templateId);
      if (!template) {
        toast.error("Template not found");
        return;
      }
      
      // Remove the item at the specified index
      const updatedItems = template.items.filter((_, idx) => idx !== itemIndex);
      
      // If no items left, delete the template
      if (updatedItems.length === 0) {
        await axiosInstance.delete(`/checklist-templates/${templateId}`);
        toast.success("Last item removed. Template deleted.");
      } else {
        // Update template with remaining items
        await axiosInstance.put(`/checklist-templates/${templateId}`, {
          program_id: template.program_id,
          items: updatedItems
        });
        toast.success("Checklist item deleted");
      }
      
      loadChecklistTemplates();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete checklist item");
    }
  };

  const handleResetUserPassword = async (e) => {
    e.preventDefault();
    
    if (newPasswordForm.newPassword !== newPasswordForm.confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    if (newPasswordForm.newPassword.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }

    try {
      await axiosInstance.post("/auth/reset-password", {
        email: resetPasswordUser.email,
        new_password: newPasswordForm.newPassword
      });
      
      toast.success(`Password reset successfully for ${resetPasswordUser.full_name}`);
      setResetPasswordDialogOpen(false);
      setResetPasswordUser(null);
      setNewPasswordForm({ newPassword: "", confirmPassword: "" });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to reset password");
    }
  };

  return (
    <div 
      className="min-h-screen"
      style={{
        background: `linear-gradient(to bottom right, ${primaryColor}10, ${secondaryColor}10, ${primaryColor}05)`
      }}
    >
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            {logoUrl && (
              <button
                onClick={() => navigate('/calendar')}
                className="hover:opacity-80 transition-opacity cursor-pointer"
              >
                <img 
                  src={logoUrl} 
                  alt={companyName}
                  className="h-10 w-auto object-contain"
                />
              </button>
            )}
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
              <p className="text-sm text-gray-600">Welcome, {user.full_name}</p>
            </div>
          </div>
          <Button
            data-testid="admin-logout-button"
            onClick={onLogout}
            variant="outline"
            className="flex items-center gap-2"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </Button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="flex flex-wrap w-full mb-8 h-auto justify-start gap-2 bg-gray-100 p-2 rounded-lg md:grid md:grid-cols-10">
            <TabsTrigger value="programs" data-testid="programs-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <BookOpen className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Programs</span>
              <span className="sm:hidden">Programs</span>
            </TabsTrigger>
            <TabsTrigger value="companies" data-testid="companies-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <Building2 className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Companies</span>
              <span className="sm:hidden">Companies</span>
            </TabsTrigger>
            <TabsTrigger value="sessions" data-testid="sessions-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <Calendar className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Sessions</span>
              <span className="sm:hidden">Sessions</span>
            </TabsTrigger>
            <TabsTrigger value="finance" data-testid="finance-tab" className="flex-1 min-w-[120px] md:min-w-0 bg-gradient-to-r from-green-500 to-emerald-500 text-white">
              <DollarSign className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Finance</span>
              <span className="sm:hidden">Finance</span>
            </TabsTrigger>
            <TabsTrigger value="staff" data-testid="staff-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <UserCog className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Staff</span>
              <span className="sm:hidden">Staff</span>
            </TabsTrigger>
            <TabsTrigger value="data-management" data-testid="data-management-tab" className="flex-1 min-w-[120px] md:min-w-0 bg-gradient-to-r from-purple-500 to-pink-500 text-white">
              <ClipboardList className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Data Management</span>
              <span className="sm:hidden">Data</span>
            </TabsTrigger>
            <TabsTrigger value="past-training" data-testid="past-training-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <FileText className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Past Training</span>
              <span className="sm:hidden">Past</span>
            </TabsTrigger>
            <TabsTrigger value="reports" data-testid="reports-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <FileText className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Reports</span>
              <span className="sm:hidden">Reports</span>
            </TabsTrigger>
            <TabsTrigger value="users" data-testid="users-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <Users className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">All Users</span>
              <span className="sm:hidden">Users</span>
            </TabsTrigger>
            <TabsTrigger value="settings" data-testid="settings-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <SettingsIcon className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Settings</span>
              <span className="sm:hidden">Settings</span>
            </TabsTrigger>
            <TabsTrigger value="quotations" data-testid="quotations-tab" className="flex-1 min-w-[120px] md:min-w-0 bg-gradient-to-r from-orange-500 to-amber-500 text-white">
              <FileText className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Quotations</span>
              <span className="sm:hidden">Quotes</span>
            </TabsTrigger>
            <TabsTrigger value="marketing-leads" data-testid="marketing-leads-tab" className="flex-1 min-w-[120px] md:min-w-0 bg-gradient-to-r from-teal-500 to-emerald-500 text-white">
              <Target className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Marketing Leads</span>
              <span className="sm:hidden">Leads</span>
            </TabsTrigger>
            <TabsTrigger value="my-payroll" data-testid="my-payroll-tab" className="flex-1 min-w-[120px] md:min-w-0 bg-gradient-to-r from-blue-500 to-cyan-500 text-white">
              <DollarSign className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">My Payroll</span>
              <span className="sm:hidden">Payroll</span>
            </TabsTrigger>
          </TabsList>

          {/* Programs Tab - Extracted to ProgramsTab component */}
          <TabsContent value="programs">
            <ProgramsTab
              programs={programs}
              filteredPrograms={filteredPrograms}
              onSearch={setProgramsSearch}
              onRefresh={loadData}
              onDeleteClick={handleDeleteClick}
            />
          </TabsContent>

          {/* Tests Tab */}
          {/* Companies Tab - Extracted to CompaniesTab component */}
          <TabsContent value="companies">
            <CompaniesTab
              companies={companies}
              filteredCompanies={filteredCompanies}
              onSearch={setCompaniesSearch}
              onRefresh={loadData}
              onDeleteClick={handleDeleteClick}
            />
          </TabsContent>

          {/* Sessions Tab */}
          <TabsContent value="sessions">
            <SessionsTab
              sessions={sessions}
              programs={programs}
              companies={companies}
              trainers={trainers}
              coordinators={coordinators}
              allStaffForCoordinator={allStaffForCoordinator}
              marketingUsers={marketingUsers}
              onRefresh={loadData}
              onDeleteClick={handleDeleteClick}
              onBulkUploadClick={setBulkUploadSession}
              onCostingClick={setCostingSession}
              onIndemnityClick={handleViewIndemnityRecords}
              getTrainerName={getTrainerName}
              getCoordinatorName={getCoordinatorName}
            />
          </TabsContent>


          {/* Reports Archive Tab */}
          <TabsContent value="reports">
            <ReportsTab
              companies={companies}
              programs={programs}
              isActive={activeTab === "reports"}
            />
          </TabsContent>

          {/* Finance Tab */}
          <TabsContent value="finance">
            <FinanceOverviewTab
              financeYear={financeYear}
              setFinanceYear={setFinanceYear}
              financeAvailableYears={financeAvailableYears}
              financeSummary={financeSummary}
            />
          </TabsContent>

          {/* Staff Tab - Unified Staff Management */}
          <TabsContent value="staff">
            <StaffTab
              users={users}
              onRefresh={loadData}
              onDeleteClick={handleDeleteClick}
            />
          </TabsContent>

          {/* Past Training Tab */}
          <TabsContent value="past-training">
            <PastTrainingTab />
          </TabsContent>

          {/* Trainers Tab */}
          {/* All Users Tab */}
          <TabsContent value="users">
            <UsersTab
              users={users}
              companies={companies}
              onRefresh={loadData}
              onDeleteClick={handleDeleteClick}
            />
          </TabsContent>

          {/* Feedback Tab */}
          {/* Checklist Templates Tab */}
          {/* Settings Tab */}
          <TabsContent value="settings">
            <Settings />
          </TabsContent>

          {/* Data Management Tab - Super Admin */}
          <TabsContent value="data-management">
            <DataManagement user={user} />
          </TabsContent>

          {/* Certificates Repository Tab */}
          <TabsContent value="certificates">
            <CertificatesTab
              sessions={sessions}
              programs={programs}
              isActive={activeTab === "certificates"}
            />
          </TabsContent>

          {/* Quotations Tab */}
          <TabsContent value="quotations">
            <QuotationsTab
              quotations={quotations}
              allClients={allClients}
              descriptionItems={descriptionItems}
              onRefresh={loadData}
              onViewQuotation={(q) => { setSelectedQuotation(q); setViewQuotationDialog(true); }}
              onRejectQuotation={(q) => { setSelectedQuotation(q); setRejectDialogOpen(true); }}
              onShowPdfTemplates={() => { loadPdfTemplates(); setShowPdfTemplatesDialog(true); }}
            />
          </TabsContent>

          {/* My Payroll Tab */}
          <TabsContent value="my-payroll">
            <MyPayroll />
          </TabsContent>

        </Tabs>
      </main>

      {/* Edit Program Dialog */}
      {editingProgram && (
        <Dialog open={editProgramDialogOpen} onOpenChange={setEditProgramDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Program</DialogTitle>
              <DialogDescription>Update program details</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Program Name</Label>
                <Input
                  value={editingProgram.name}
                  onChange={(e) => setEditingProgram({ ...editingProgram, name: e.target.value })}
                />
              </div>
              <div>
                <Label>Description</Label>
                <Textarea
                  value={editingProgram.description || ""}
                  onChange={(e) => setEditingProgram({ ...editingProgram, description: e.target.value })}
                />
              </div>
              <div>
                <Label>Pass Percentage (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={editingProgram.pass_percentage}
                  onChange={(e) => setEditingProgram({ ...editingProgram, pass_percentage: parseFloat(e.target.value) })}
                />
              </div>
              <Button onClick={handleUpdateProgram} className="w-full">
                Update Program
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Edit Company Dialog */}
      {editingCompany && (
        <Dialog open={editCompanyDialogOpen} onOpenChange={setEditCompanyDialogOpen}>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Edit Company</DialogTitle>
              <DialogDescription>Update company details</DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label>Company Name *</Label>
                  <Input
                    value={editingCompany.name || ''}
                    onChange={(e) => setEditingCompany({ ...editingCompany, name: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Registration No.</Label>
                  <Input
                    value={editingCompany.registration_no || ''}
                    onChange={(e) => setEditingCompany({ ...editingCompany, registration_no: e.target.value })}
                    placeholder="e.g., 1234567-A"
                  />
                </div>
                <div>
                  <Label>Contact Person</Label>
                  <Input
                    value={editingCompany.contact_person || ''}
                    onChange={(e) => setEditingCompany({ ...editingCompany, contact_person: e.target.value })}
                  />
                </div>
                <div className="col-span-2">
                  <Label>Address Line 1</Label>
                  <Input
                    value={editingCompany.address_line1 || ''}
                    onChange={(e) => setEditingCompany({ ...editingCompany, address_line1: e.target.value })}
                  />
                </div>
                <div className="col-span-2">
                  <Label>Address Line 2</Label>
                  <Input
                    value={editingCompany.address_line2 || ''}
                    onChange={(e) => setEditingCompany({ ...editingCompany, address_line2: e.target.value })}
                  />
                </div>
                <div>
                  <Label>City</Label>
                  <Input
                    value={editingCompany.city || ''}
                    onChange={(e) => setEditingCompany({ ...editingCompany, city: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Postcode</Label>
                  <Input
                    value={editingCompany.postcode || ''}
                    onChange={(e) => setEditingCompany({ ...editingCompany, postcode: e.target.value })}
                  />
                </div>
                <div>
                  <Label>State</Label>
                  <Input
                    value={editingCompany.state || ''}
                    onChange={(e) => setEditingCompany({ ...editingCompany, state: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Phone</Label>
                  <Input
                    value={editingCompany.phone || ''}
                    onChange={(e) => setEditingCompany({ ...editingCompany, phone: e.target.value })}
                  />
                </div>
                <div className="col-span-2">
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={editingCompany.email || ''}
                    onChange={(e) => setEditingCompany({ ...editingCompany, email: e.target.value })}
                  />
                </div>
              </div>
              <Button onClick={handleUpdateCompany} className="w-full">
                Update Company
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogDescription>
              {deleteTarget && (
                <>
                  Are you sure you want to delete this {deleteTarget.type}?
                  <br />
                  <strong>{deleteTarget.item.name || deleteTarget.item.full_name}</strong>
                  <br />
                  <span className="text-red-600">This action cannot be undone.</span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => {
                setDeleteConfirmOpen(false);
                setDeleteTarget(null);
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              className="flex-1"
              onClick={handleConfirmDelete}
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Session Dialog */}
      {editingSession && (
        <Dialog open={editSessionDialogOpen} onOpenChange={setEditSessionDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Edit Session</DialogTitle>
              <DialogDescription>
                Update session details and add participants
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Location</Label>
                <Input
                  value={editingSession.location}
                  onChange={(e) => setEditingSession({ ...editingSession, location: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={editingSession.start_date}
                    onChange={(e) => setEditingSession({ ...editingSession, start_date: e.target.value })}
                  />
                </div>
                <div>
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={editingSession.end_date}
                    onChange={(e) => setEditingSession({ ...editingSession, end_date: e.target.value })}
                  />
                </div>
              </div>

              {/* Change Coordinator */}
              <div>
                <Label>Session Coordinator</Label>
                <p className="text-xs text-gray-500 mb-2">Change the primary coordinator for this session</p>
                <Select
                  value={editingSession.coordinator_id || "none"}
                  onValueChange={(value) => setEditingSession({ ...editingSession, coordinator_id: value === "none" ? null : value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select coordinator" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No Coordinator</SelectItem>
                    {allStaffForCoordinator.map((staff) => (
                      <SelectItem key={staff.id} value={staff.id}>
                        {staff.full_name} ({staff.role.replace('_', ' ')})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {editingSession.coordinator_id && (
                  <p className="text-xs text-green-600 mt-1">
                    Current: {allStaffForCoordinator.find(s => s.id === editingSession.coordinator_id)?.full_name || 'Unknown'}
                  </p>
                )}
              </div>

              {/* Assistant Coordinators */}
              <div>
                <Label>Assistant Coordinators (can manage session if coordinator unavailable)</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {users.filter(s => s.role === 'trainer' || s.role === 'assistant_admin' || s.role === 'coordinator').map(s => (
                    <label key={s.id} className="flex items-center gap-2 text-sm border rounded px-2 py-1 cursor-pointer hover:bg-gray-50">
                      <input
                        type="checkbox"
                        checked={(editingSession.assistant_coordinator_ids || []).includes(s.id)}
                        onChange={(e) => {
                          const current = editingSession.assistant_coordinator_ids || [];
                          if (e.target.checked) {
                            setEditingSession({ ...editingSession, assistant_coordinator_ids: [...current, s.id] });
                          } else {
                            setEditingSession({ ...editingSession, assistant_coordinator_ids: current.filter(id => id !== s.id) });
                          }
                        }}
                      />
                      {s.full_name}
                      <span className="text-xs text-gray-500">({s.role})</span>
                    </label>
                  ))}
                </div>
                {(editingSession.assistant_coordinator_ids || []).length > 0 && (
                  <p className="text-xs text-gray-500 mt-1">
                    Selected: {(editingSession.assistant_coordinator_ids || []).length} assistant coordinator(s)
                  </p>
                )}
              </div>

              <div className="border-t pt-4">
                <h3 className="font-semibold mb-3">Add More Participants</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="edit-participant-name">Full Name</Label>
                    <Input
                      id="edit-participant-name"
                      value={newParticipant.full_name}
                      onChange={(e) => setNewParticipant({ ...newParticipant, full_name: e.target.value })}
                      placeholder="John Doe"
                    />
                  </div>
                  <div>
                    <Label htmlFor="edit-participant-id">ID Number</Label>
                    <Input
                      id="edit-participant-id"
                      value={newParticipant.id_number}
                      onChange={(e) => setNewParticipant({ ...newParticipant, id_number: e.target.value })}
                      placeholder="ID123456"
                    />
                  </div>
                  <div>
                    <Label htmlFor="edit-participant-email">Email</Label>
                    <Input
                      id="edit-participant-email"
                      type="email"
                      value={newParticipant.email}
                      onChange={(e) => setNewParticipant({ ...newParticipant, email: e.target.value })}
                      placeholder="john@example.com"
                    />
                  </div>
                  <div>
                    <Label htmlFor="edit-participant-password">Password</Label>
                    <Input
                      id="edit-participant-password"
                      type="password"
                      value={newParticipant.password}
                      onChange={(e) => setNewParticipant({ ...newParticipant, password: e.target.value })}
                      placeholder="Password"
                    />
                  </div>
                </div>
                <div className="flex gap-2 mt-3">
                  <Button
                    type="button"
                    onClick={handleAddParticipantToEdit}
                    variant="outline"
                    className="flex-1"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Participant
                  </Button>
                  
                  <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
                    <DialogTrigger asChild>
                      <Button variant="outline" className="flex-1">
                        <Upload className="w-4 h-4 mr-2" />
                        Bulk Upload
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Bulk Upload Participants</DialogTitle>
                        <DialogDescription>
                          Upload an Excel file (.xlsx or .xls) with participant data
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div className="bg-blue-50 p-4 rounded-lg space-y-2">
                          <p className="text-sm font-medium text-blue-900">Excel Format Required:</p>
                          <ul className="text-sm text-blue-700 space-y-1">
                            <li>• Column 1: <strong>Full Name</strong></li>
                            <li>• Column 2: <strong>IC</strong> (UPPERCASE, no dashes)</li>
                            <li>• Column 3: <strong>Company Name</strong></li>
                          </ul>
                          <p className="text-xs text-blue-600 mt-2">
                            Note: New companies will be created automatically if not found
                          </p>
                        </div>
                        
                        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                          <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                          <label className="cursor-pointer">
                            <span className="text-sm text-gray-600">
                              {uploading ? "Uploading..." : "Click to select Excel file"}
                            </span>
                            <Input
                              type="file"
                              accept=".xlsx,.xls"
                              onChange={handleBulkUpload}
                              disabled={uploading}
                              className="hidden"
                            />
                          </label>
                        </div>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>

                {editingSession.newParticipants && editingSession.newParticipants.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <Label className="text-sm">New Participants to Add ({editingSession.newParticipants.length})</Label>
                    {editingSession.newParticipants.map((participant, idx) => (
                      <div key={idx} className="flex justify-between items-center p-2 bg-green-50 rounded">
                        <div>
                          <p className="text-sm font-medium">{participant.full_name}</p>
                          <p className="text-xs text-gray-600">{participant.email} • ID: {participant.id_number}</p>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveNewParticipant(idx)}
                        >
                          <Trash2 className="w-4 h-4 text-red-600" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="border-t pt-4">
                <h3 className="font-semibold mb-3">Current Participants ({editingSession.participant_ids.length})</h3>
                {editingSession.participant_ids.length > 0 ? (
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {editingSession.participant_ids.map((pid) => {
                      const participant = users.find(u => u.id === pid);
                      if (!participant) return null;
                      return (
                        <div key={pid} className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                          <div>
                            <p className="font-medium text-sm">{participant.full_name}</p>
                            <p className="text-xs text-gray-600">
                              IC: {participant.id_number} {participant.phone_number && `• ${participant.phone_number}`}
                            </p>
                          </div>
                          <div className="flex gap-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setEditingParticipant(participant);
                                setEditParticipantForm({
                                  full_name: participant.full_name || "",
                                  id_number: participant.id_number || "",
                                  phone_number: participant.phone_number || "",
                                });
                                setEditParticipantDialogOpen(true);
                              }}
                            >
                              <Edit className="w-4 h-4 text-blue-600" />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                // Remove participant from session
                                const updated = editingSession.participant_ids.filter(id => id !== pid);
                                setEditingSession({ ...editingSession, participant_ids: updated });
                                toast.success(`${participant.full_name} will be removed from this session`);
                              }}
                            >
                              <Trash2 className="w-4 h-4 text-red-600" />
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No participants yet. Add some above.</p>
                )}
              </div>

              <Button onClick={handleUpdateSession} className="w-full">
                Update Session
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Reset Password Dialog */}
      <Dialog open={resetPasswordDialogOpen} onOpenChange={setResetPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              Set a new password for {resetPasswordUser?.full_name} ({resetPasswordUser?.email})
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleResetUserPassword} className="space-y-4">
            <div>
              <Label htmlFor="new-password">New Password</Label>
              <Input
                id="new-password"
                type="password"
                placeholder="Enter new password"
                value={newPasswordForm.newPassword}
                onChange={(e) => setNewPasswordForm({ ...newPasswordForm, newPassword: e.target.value })}
                required
                minLength={6}
              />
              <p className="text-xs text-gray-500 mt-1">Minimum 6 characters</p>
            </div>
            <div>
              <Label htmlFor="confirm-password">Confirm Password</Label>
              <Input
                id="confirm-password"
                type="password"
                placeholder="Confirm new password"
                value={newPasswordForm.confirmPassword}
                onChange={(e) => setNewPasswordForm({ ...newPasswordForm, confirmPassword: e.target.value })}
                required
                minLength={6}
              />
            </div>
            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                onClick={() => {
                  setResetPasswordDialogOpen(false);
                  setResetPasswordUser(null);
                  setNewPasswordForm({ newPassword: "", confirmPassword: "" });
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="flex-1"
                style={{ backgroundColor: primaryColor }}
              >
                Reset Password
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Participant Dialog */}
      <Dialog open={editParticipantDialogOpen} onOpenChange={setEditParticipantDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Participant</DialogTitle>
            <DialogDescription>
              Update participant details. Changes will apply across all trainings.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdateParticipant} className="space-y-4">
            <div>
              <Label htmlFor="edit-part-name">Full Name *</Label>
              <Input
                id="edit-part-name"
                data-testid="edit-participant-name"
                value={editParticipantForm.full_name}
                onChange={(e) => setEditParticipantForm({ ...editParticipantForm, full_name: e.target.value })}
                required
              />
            </div>
            <div>
              <Label htmlFor="edit-part-ic">IC Number *</Label>
              <Input
                id="edit-part-ic"
                data-testid="edit-participant-ic"
                value={editParticipantForm.id_number}
                onChange={(e) => setEditParticipantForm({ ...editParticipantForm, id_number: e.target.value })}
                required
              />
            </div>
            <div>
              <Label htmlFor="edit-part-phone">Phone Number</Label>
              <Input
                id="edit-part-phone"
                data-testid="edit-participant-phone"
                value={editParticipantForm.phone_number}
                onChange={(e) => setEditParticipantForm({ ...editParticipantForm, phone_number: e.target.value })}
              />
            </div>
            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                onClick={() => {
                  setEditParticipantDialogOpen(false);
                  setEditingParticipant(null);
                }}
              >
                Cancel
              </Button>
              <Button type="submit" className="flex-1" data-testid="save-participant-btn">
                Save Changes
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Bulk Delete Users Confirmation Dialog */}
      <Dialog open={bulkDeleteDialogOpen} onOpenChange={setBulkDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600">Delete {selectedUsers.length} Users?</DialogTitle>
            <DialogDescription>
              This action cannot be undone. Are you sure you want to permanently delete {selectedUsers.length} selected user(s)?
            </DialogDescription>
          </DialogHeader>
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-2">
            <p className="text-sm text-red-700">
              <strong>Warning:</strong> All associated data for these users will also be removed.
            </p>
          </div>
          <div className="flex gap-3 mt-4">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => setBulkDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              className="flex-1"
              onClick={handleBulkDeleteUsers}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete {selectedUsers.length} Users
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Session Costing Modal */}
      {costingSession && (
        <SessionCosting
          session={costingSession}
          onClose={() => setCostingSession(null)}
          onUpdate={() => {
            // Optionally reload sessions if needed
            setCostingSession(null);
          }}
        />
      )}

      {/* Standalone Bulk Upload Dialog */}
      <Dialog open={bulkUploadSession !== null} onOpenChange={(open) => !open && setBulkUploadSession(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bulk Upload Participants</DialogTitle>
            <DialogDescription>
              {bulkUploadSession && (
                <span>
                  Upload participants to: <strong>{bulkUploadSession.company_name || 'Session'}</strong> - {bulkUploadSession.name}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-blue-50 p-4 rounded-lg space-y-2">
              <p className="text-sm font-medium text-blue-900">Excel Format Required:</p>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Column 1: <strong>Full Name</strong></li>
                <li>• Column 2: <strong>IC</strong> (UPPERCASE, no dashes)</li>
                <li>• Column 3: <strong>Company Name</strong></li>
              </ul>
              <p className="text-xs text-blue-600 mt-2">
                Note: New companies will be created automatically if not found
              </p>
            </div>
            
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
              <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
              <label className="cursor-pointer">
                <span className="text-sm text-gray-600">
                  {uploading ? "Uploading..." : "Click to select Excel file"}
                </span>
                <Input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleStandaloneBulkUpload}
                  disabled={uploading}
                  className="hidden"
                />
              </label>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Indemnity Records Dialog */}
      <Dialog open={indemnityDialogOpen} onOpenChange={setIndemnityDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-purple-600" />
              Indemnity Records
            </DialogTitle>
            <DialogDescription>
              {indemnityRecords?.session_name} - {indemnityRecords?.company_name}
            </DialogDescription>
          </DialogHeader>
          
          {indemnityRecords && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <p className="text-sm text-gray-600">
                  Total: {indemnityRecords.total_participants} participants | 
                  Signed: {indemnityRecords.indemnity_records?.filter(r => r.indemnity_accepted).length || 0}
                </p>
                <Button onClick={handleExportIndemnityRecords} variant="outline" size="sm">
                  <Download className="w-4 h-4 mr-2" />
                  Export Excel
                </Button>
              </div>
              
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-purple-100">
                    <tr>
                      <th className="px-3 py-2 text-left">No</th>
                      <th className="px-3 py-2 text-left">Name</th>
                      <th className="px-3 py-2 text-left">IC Number</th>
                      <th className="px-3 py-2 text-center">Status</th>
                      <th className="px-3 py-2 text-left">Signed Name</th>
                      <th className="px-3 py-2 text-left">Signed Date</th>
                      <th className="px-3 py-2 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(indemnityRecords.indemnity_records || []).map((record, idx) => (
                      <tr key={record.id} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-3 py-2">{idx + 1}</td>
                        <td className="px-3 py-2 font-medium">{record.full_name}</td>
                        <td className="px-3 py-2">{record.id_number}</td>
                        <td className="px-3 py-2 text-center">
                          {record.indemnity_accepted ? (
                            <span className="inline-flex items-center px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                              ✓ Signed
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs">
                              ✗ Not Signed
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2">{record.indemnity_signed_name || '-'}</td>
                        <td className="px-3 py-2">{record.indemnity_signed_date || '-'}</td>
                        <td className="px-3 py-2 text-center">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2"
                            onClick={() => setPrintIndemnityRecord(record)}
                            data-testid={`print-indemnity-${record.id}`}
                          >
                            <Printer className="w-3 h-3 mr-1" />
                            Print
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Individual Indemnity Form Print Modal */}
      {printIndemnityRecord && (
        <IndemnityFormPrint
          record={printIndemnityRecord}
          sessionInfo={{
            session_name: indemnityRecords?.session_name,
            company_name: indemnityRecords?.company_name,
            training_date: indemnityRecords?.training_date,
            location: indemnityRecords?.location
          }}
          companySettings={companySettings}
          onClose={() => setPrintIndemnityRecord(null)}
        />
      )}

      {/* Quotation View Dialog */}
      <Dialog open={viewQuotationDialog} onOpenChange={setViewQuotationDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Quotation Details</DialogTitle>
          </DialogHeader>
          {selectedQuotation && (
            <div className="space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xl font-bold">{selectedQuotation.quotation_number}</p>
                  <p className="text-gray-600">Created: {new Date(selectedQuotation.created_at).toLocaleDateString()}</p>
                  <p className="text-gray-600">By: {selectedQuotation.marketer_name}</p>
                </div>
                {getQuotationStatusBadge(selectedQuotation.status)}
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 p-3 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-2">Client</h4>
                  <p className="font-medium">{selectedQuotation.client_name}</p>
                  <p className="text-sm">{selectedQuotation.contact_person}</p>
                </div>
                <div className="bg-green-50 p-3 rounded-lg">
                  <h4 className="font-semibold text-green-900 mb-2">Programme</h4>
                  <p className="font-medium">{selectedQuotation.programme_name}</p>
                  <p className="text-sm">{selectedQuotation.num_participants} pax @ RM {selectedQuotation.rate_per_pax?.toLocaleString()}</p>
                </div>
              </div>
              
              <div className="bg-gray-50 p-3 rounded-lg">
                <div className="flex justify-between"><span>Subtotal:</span><span>RM {selectedQuotation.subtotal?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</span></div>
                {selectedQuotation.sst_percent > 0 && (
                  <div className="flex justify-between"><span>SST ({selectedQuotation.sst_percent}%):</span><span>RM {selectedQuotation.sst_amount?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</span></div>
                )}
                <div className="flex justify-between font-bold border-t mt-2 pt-2"><span>Total:</span><span>RM {selectedQuotation.total_amount?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</span></div>
              </div>
              
              <div className="bg-yellow-50 p-3 rounded-lg">
                <p className="text-sm"><strong>Valid Until:</strong> {new Date(selectedQuotation.valid_until).toLocaleDateString()}</p>
              </div>
              
              {selectedQuotation.remarks && (
                <div className="bg-gray-50 p-3 rounded-lg">
                  <h4 className="font-semibold mb-1">Remarks</h4>
                  <p className="text-sm">{selectedQuotation.remarks}</p>
                </div>
              )}
            </div>
          )}
          <div className="flex justify-end gap-2 mt-4">
            {selectedQuotation?.status === 'pending_approval' && (
              <>
                <Button onClick={() => handleApproveQuotation(selectedQuotation.id)} className="bg-green-600 hover:bg-green-700">
                  <CheckCircle className="w-4 h-4 mr-2" /> Approve
                </Button>
                <Button variant="destructive" onClick={() => { setViewQuotationDialog(false); setRejectDialogOpen(true); }}>
                  <XCircle className="w-4 h-4 mr-2" /> Reject
                </Button>
              </>
            )}
            <Button variant="outline" onClick={() => setViewQuotationDialog(false)}>Close</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Quotation Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Quotation</DialogTitle>
            <DialogDescription>
              Please provide a reason for rejection. This will be visible to the marketer.
            </DialogDescription>
          </DialogHeader>
          <div>
            <Label>Rejection Remarks</Label>
            <Textarea 
              value={rejectRemarks} 
              onChange={(e) => setRejectRemarks(e.target.value)}
              placeholder="Reason for rejection..."
              rows={3}
            />
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => { setRejectDialogOpen(false); setRejectRemarks(''); }}>Cancel</Button>
            <Button variant="destructive" onClick={handleRejectQuotation}>Reject Quotation</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* PDF Templates Edit Dialog */}
      <Dialog open={showPdfTemplatesDialog} onOpenChange={setShowPdfTemplatesDialog}>
        <DialogContent className="max-w-4xl max-h-[95vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit PDF Templates</DialogTitle>
            <DialogDescription>
              Customize the content for quotation PDFs. Use placeholders: {"{{programme_name}}"}, {"{{company_name}}"}, {"{{contact_person}}"}, {"{{quotation_number}}"}
            </DialogDescription>
          </DialogHeader>
          
          {!showPdfPreview ? (
            <div className="space-y-6">
              <div>
                <Label className="text-lg font-semibold">Cover Letter (Page 1)</Label>
                <p className="text-sm text-gray-500 mb-2">
                  Content after the salutation. Company header and recipient are auto-generated.
                </p>
                <RichTextToolbar 
                  textareaRef={coverLetterRef}
                  value={pdfTemplates.cover_letter}
                  onChange={(val) => setPdfTemplates({ ...pdfTemplates, cover_letter: val })}
                />
                <Textarea
                  ref={coverLetterRef}
                  value={pdfTemplates.cover_letter}
                  onChange={(e) => setPdfTemplates({ ...pdfTemplates, cover_letter: e.target.value })}
                  placeholder="RE: QUOTATION FOR {{programme_name}}

Thank you for your interest in our training programmes. We are pleased to submit our quotation for the {{programme_name}} as per your request.

We trust our proposal meets your requirements and look forward to being of service to {{company_name}}."
                  rows={8}
                  className="font-mono text-sm rounded-t-none"
                />
              </div>
              
              <div>
                <Label className="text-lg font-semibold">Terms & Conditions (Pages 3+)</Label>
                <p className="text-sm text-gray-500 mb-2">
                  Enter your terms and conditions. Use clear numbering for sections (1., 1.1, 2., etc.)
                </p>
                <RichTextToolbar 
                  textareaRef={termsRef}
                  value={pdfTemplates.terms_conditions_pages}
                  onChange={(val) => setPdfTemplates({ ...pdfTemplates, terms_conditions_pages: val })}
                />
                <Textarea
                  ref={termsRef}
                  value={pdfTemplates.terms_conditions_pages}
                  onChange={(e) => setPdfTemplates({ ...pdfTemplates, terms_conditions_pages: e.target.value })}
                  placeholder="TERMS AND CONDITIONS

1. PAYMENT TERMS
1.1 Payment is due upon receipt of invoice.
1.2 A 50% deposit is required upon confirmation of training.
1.3 Full payment must be made before the training date.

2. CANCELLATION POLICY
2.1 Cancellation within 7 days of training will incur a 50% cancellation fee.
2.2 No refunds for cancellations made within 48 hours of training.

3. GENERAL CONDITIONS
3.1 All prices quoted are in Malaysian Ringgit (RM).
3.2 Prices are subject to SST where applicable.
3.3 This quotation is valid for 30 days from the date of issue.

4. LIABILITY
4.1 The training provider shall not be liable for any indirect damages.
4.2 Maximum liability is limited to the course fees paid."
                  rows={16}
                  className="font-mono text-sm rounded-t-none"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Content will be paginated automatically across multiple pages in the PDF.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-gray-100 p-4 rounded-lg">
                <h4 className="font-semibold mb-2">Cover Letter Preview</h4>
                <div className="bg-white p-4 border rounded whitespace-pre-wrap text-sm">
                  {pdfTemplates.cover_letter || "(No cover letter content)"}
                </div>
              </div>
              <div className="bg-gray-100 p-4 rounded-lg">
                <h4 className="font-semibold mb-2">Terms & Conditions Preview</h4>
                <div className="bg-white p-4 border rounded whitespace-pre-wrap text-sm">
                  {pdfTemplates.terms_conditions_pages || "(No terms content)"}
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter className="flex justify-between">
            <Button 
              variant="outline" 
              onClick={() => setShowPdfPreview(!showPdfPreview)}
            >
              <Eye className="w-4 h-4 mr-2" />
              {showPdfPreview ? 'Back to Edit' : 'Preview'}
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => { setShowPdfTemplatesDialog(false); setShowPdfPreview(false); }}>
                Cancel
              </Button>
              <Button onClick={savePdfTemplates} disabled={pdfTemplatesLoading}>
                {pdfTemplatesLoading ? 'Saving...' : 'Save Templates'}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};


export default AdminDashboard;
