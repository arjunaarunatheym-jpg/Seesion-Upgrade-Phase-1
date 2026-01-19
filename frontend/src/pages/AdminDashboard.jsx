import { useState, useEffect, useMemo } from "react";
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
import { LogOut, Building2, Users, Calendar, MessageSquare, BookOpen, Plus, Trash2, Edit, UserPlus, UserCog, ClipboardList, ClipboardCheck, Settings as SettingsIcon, FileText, Download, Search, Book, Award, Eye, Upload, CheckCircle, XCircle, Clock, AlertCircle, DollarSign, Printer, Bold, Italic, Underline, List } from "lucide-react";
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
      const response = await axiosInstance.get("/checklists/templates");
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
        await axiosInstance.put(`/checklists/templates/${existingTemplate.id}`, {
          program_id: checklistForm.program_id,
          items: updatedItems
        });
        toast.success("Checklist item added successfully");
      } else {
        // Create new template
        await axiosInstance.post("/checklists/templates", {
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
      await axiosInstance.delete(`/checklists/templates/${templateId}`);
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
        await axiosInstance.delete(`/checklists/templates/${templateId}`);
        toast.success("Last item removed. Template deleted.");
      } else {
        // Update template with remaining items
        await axiosInstance.put(`/checklists/templates/${templateId}`, {
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
            <TabsTrigger value="my-payroll" data-testid="my-payroll-tab" className="flex-1 min-w-[120px] md:min-w-0 bg-gradient-to-r from-blue-500 to-cyan-500 text-white">
              <DollarSign className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">My Payroll</span>
              <span className="sm:hidden">Payroll</span>
            </TabsTrigger>
          </TabsList>

          {/* Programs Tab */}
          <TabsContent value="programs">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>Training Programs</CardTitle>
                    <CardDescription>Manage your training modules</CardDescription>
                  </div>
                  <Dialog open={programDialogOpen} onOpenChange={setProgramDialogOpen}>
                    <DialogTrigger asChild>
                      <Button data-testid="create-program-button">
                        <BookOpen className="w-4 h-4 mr-2" />
                        Add Program
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Create New Program</DialogTitle>
                        <DialogDescription>
                          Add a new training program/module
                        </DialogDescription>
                      </DialogHeader>
                      <form onSubmit={handleCreateProgram} className="space-y-4">
                        <div>
                          <Label htmlFor="program-name">Program Name *</Label>
                          <Input
                            id="program-name"
                            data-testid="program-name-input"
                            placeholder="e.g., Defensive Riding"
                            value={programForm.name}
                            onChange={(e) => setProgramForm({ ...programForm, name: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="program-description">Description (Optional)</Label>
                          <Textarea
                            id="program-description"
                            data-testid="program-description-input"
                            placeholder="Brief description of the program"
                            value={programForm.description}
                            onChange={(e) => setProgramForm({ ...programForm, description: e.target.value })}
                          />
                        </div>
                        <div>
                          <Label htmlFor="pass-percentage">Pass Percentage (%)</Label>
                          <Input
                            id="pass-percentage"
                            data-testid="pass-percentage-input"
                            type="number"
                            min="0"
                            max="100"
                            value={programForm.pass_percentage}
                            onChange={(e) => setProgramForm({ ...programForm, pass_percentage: parseFloat(e.target.value) })}
                            required
                          />
                        </div>
                        <Button data-testid="submit-program-button" type="submit" className="w-full">
                          Create Program
                        </Button>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <SearchBar
                    placeholder="Search programs by name or description..."
                    onSearch={setProgramsSearch}
                    className="max-w-md"
                  />
                </div>
                <div className="space-y-2">
                  {filteredPrograms.length === 0 ? (
                    <div className="text-center py-12">
                      <BookOpen className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                      <p className="text-gray-500">
                        {programsSearch ? "No programs match your search." : "No programs yet. Create your first training program!"}
                      </p>
                    </div>
                  ) : (
                    filteredPrograms.map((program) => (
                      <div key={program.id} className="mb-4">
                        <Card>
                          <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50">
                            <div className="flex justify-between items-start">
                              <div className="flex-1">
                                <CardTitle>{program.name}</CardTitle>
                                {program.description && (
                                  <CardDescription>{program.description}</CardDescription>
                                )}
                                <div className="flex gap-3 mt-2">
                                  <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                    Pass Mark: {program.pass_percentage}%
                                  </span>
                                  <span className="text-xs text-gray-500">
                                    Created: {new Date(program.created_at).toLocaleDateString()}
                                  </span>
                                </div>
                              </div>
                              <div className="flex gap-2 flex-wrap">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleEditProgram(program)}
                                >
                                  <Edit className="w-4 h-4 mr-1" />
                                  Edit
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => handleDeleteClick("program", program)}
                                >
                                  <Trash2 className="w-4 h-4 mr-1" />
                                  Delete
                                </Button>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent className="pt-4">
                            <div className="flex gap-2 flex-wrap">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => setSelectedProgram(selectedProgram?.id === program.id ? null : program)}
                              >
                                <ClipboardList className="w-4 h-4 mr-2" />
                                Manage Tests & Checklists
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  if (selectedProgram?.id === program.id) {
                                    setSelectedProgram(null);
                                  } else {
                                    setSelectedProgram(program);
                                    // Auto switch to feedback tab if needed
                                    setTimeout(() => {
                                      const feedbackTab = document.querySelector(`[data-program-id="${program.id}"] [value="feedback-form"]`);
                                      if (feedbackTab) feedbackTab.click();
                                    }, 100);
                                  }
                                }}
                              >
                                <MessageSquare className="w-4 h-4 mr-2" />
                                Manage Feedback Form
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                        
                        {/* Expandable Management Section */}
                        {selectedProgram?.id === program.id && (
                          <Card className="mt-2 border-l-4 border-blue-500">
                            <CardContent className="pt-6">
                              <Tabs defaultValue="tests" className="w-full" data-program-id={program.id}>
                                <TabsList className="grid w-full grid-cols-3 mb-4">
                                  <TabsTrigger value="tests">
                                    <ClipboardList className="w-4 h-4 mr-2" />
                                    Tests
                                  </TabsTrigger>
                                  <TabsTrigger value="checklists">
                                    <ClipboardCheck className="w-4 h-4 mr-2" />
                                    Checklists
                                  </TabsTrigger>
                                  <TabsTrigger value="feedback-form">
                                    <MessageSquare className="w-4 h-4 mr-2" />
                                    Feedback
                                  </TabsTrigger>
                                </TabsList>
                                
                                {/* Tests Tab */}
                                <TabsContent value="tests">
                                  <div className="mb-4">
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => setSelectedProgram(null)}
                                    >
                                      ← Back to Programs
                                    </Button>
                                  </div>
                                  <TestManagement program={program} />
                                </TabsContent>
                                
                                {/* Checklists Tab */}
                                <TabsContent value="checklists">
                                  <div className="mb-4">
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => setSelectedProgram(null)}
                                    >
                                      ← Back to Programs
                                    </Button>
                                  </div>
                                  <ChecklistManagement program={program} />
                                </TabsContent>
                                
                                {/* Feedback Tab */}
                                <TabsContent value="feedback-form">
                                  <div className="mb-4">
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => setSelectedProgram(null)}
                                    >
                                      ← Back to Programs
                                    </Button>
                                  </div>
                                  <FeedbackManagement program={program} />
                                </TabsContent>
                              </Tabs>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Tests Tab */}
          {/* Companies Tab */}
          <TabsContent value="companies">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>Companies</CardTitle>
                    <CardDescription>Manage training companies</CardDescription>
                  </div>
                  <Dialog open={companyDialogOpen} onOpenChange={setCompanyDialogOpen}>
                    <DialogTrigger asChild>
                      <Button data-testid="create-company-button">
                        <Building2 className="w-4 h-4 mr-2" />
                        Add Company
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Create New Company</DialogTitle>
                        <DialogDescription>
                          Add a new company to the system
                        </DialogDescription>
                      </DialogHeader>
                      <form onSubmit={handleCreateCompany} className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="col-span-2">
                            <Label htmlFor="company-name">Company Name *</Label>
                            <Input
                              id="company-name"
                              data-testid="company-name-input"
                              value={companyFormData.name}
                              onChange={(e) => setCompanyFormData({...companyFormData, name: e.target.value})}
                              required
                            />
                          </div>
                          <div>
                            <Label htmlFor="company-reg">Registration No.</Label>
                            <Input
                              id="company-reg"
                              data-testid="company-reg-input"
                              value={companyFormData.registration_no}
                              onChange={(e) => setCompanyFormData({...companyFormData, registration_no: e.target.value})}
                              placeholder="e.g., 1234567-A"
                            />
                          </div>
                          <div>
                            <Label htmlFor="company-contact">Contact Person</Label>
                            <Input
                              id="company-contact"
                              value={companyFormData.contact_person}
                              onChange={(e) => setCompanyFormData({...companyFormData, contact_person: e.target.value})}
                            />
                          </div>
                          <div className="col-span-2">
                            <Label htmlFor="company-address1">Address Line 1</Label>
                            <Input
                              id="company-address1"
                              value={companyFormData.address_line1}
                              onChange={(e) => setCompanyFormData({...companyFormData, address_line1: e.target.value})}
                            />
                          </div>
                          <div className="col-span-2">
                            <Label htmlFor="company-address2">Address Line 2</Label>
                            <Input
                              id="company-address2"
                              value={companyFormData.address_line2}
                              onChange={(e) => setCompanyFormData({...companyFormData, address_line2: e.target.value})}
                            />
                          </div>
                          <div>
                            <Label htmlFor="company-city">City</Label>
                            <Input
                              id="company-city"
                              value={companyFormData.city}
                              onChange={(e) => setCompanyFormData({...companyFormData, city: e.target.value})}
                            />
                          </div>
                          <div>
                            <Label htmlFor="company-postcode">Postcode</Label>
                            <Input
                              id="company-postcode"
                              value={companyFormData.postcode}
                              onChange={(e) => setCompanyFormData({...companyFormData, postcode: e.target.value})}
                            />
                          </div>
                          <div>
                            <Label htmlFor="company-state">State</Label>
                            <Input
                              id="company-state"
                              value={companyFormData.state}
                              onChange={(e) => setCompanyFormData({...companyFormData, state: e.target.value})}
                            />
                          </div>
                          <div>
                            <Label htmlFor="company-phone">Phone</Label>
                            <Input
                              id="company-phone"
                              value={companyFormData.phone}
                              onChange={(e) => setCompanyFormData({...companyFormData, phone: e.target.value})}
                            />
                          </div>
                          <div className="col-span-2">
                            <Label htmlFor="company-email">Email</Label>
                            <Input
                              id="company-email"
                              type="email"
                              value={companyFormData.email}
                              onChange={(e) => setCompanyFormData({...companyFormData, email: e.target.value})}
                            />
                          </div>
                        </div>
                        <Button data-testid="submit-company-button" type="submit" className="w-full">
                          Create Company
                        </Button>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <SearchBar
                    placeholder="Search companies by name..."
                    onSearch={setCompaniesSearch}
                    className="max-w-md"
                  />
                </div>
                <div className="space-y-2">
                  {filteredCompanies.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">
                      {companiesSearch ? "No companies match your search." : "No companies yet"}
                    </p>
                  ) : (
                    filteredCompanies.map((company) => (
                      <div
                        key={company.id}
                        data-testid={`company-item-${company.id}`}
                        className="p-4 bg-gray-50 rounded-lg flex justify-between items-center hover:bg-gray-100 transition-colors"
                      >
                        <div>
                          <h3 className="font-semibold text-gray-900">{company.name}</h3>
                          {company.registration_no && (
                            <p className="text-sm text-gray-600">Reg: {company.registration_no}</p>
                          )}
                          <p className="text-sm text-gray-500">
                            Created: {new Date(company.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            data-testid={`edit-company-${company.id}`}
                            size="sm"
                            variant="outline"
                            onClick={() => handleEditCompany(company)}
                          >
                            <Edit className="w-4 h-4 mr-1" />
                            Edit
                          </Button>
                          <Button
                            data-testid={`delete-company-${company.id}`}
                            size="sm"
                            variant="destructive"
                            onClick={() => handleDeleteClick("company", company)}
                          >
                            <Trash2 className="w-4 h-4 mr-1" />
                            Delete
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Sessions Tab */}
          <TabsContent value="sessions">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>Training Sessions</CardTitle>
                    <CardDescription>Create and manage sessions</CardDescription>
                  </div>
                  <Dialog open={sessionDialogOpen} onOpenChange={setSessionDialogOpen}>
                    <DialogTrigger asChild>
                      <Button data-testid="create-session-button" disabled={programs.length === 0 || companies.length === 0}>
                        <Calendar className="w-4 h-4 mr-2" />
                        Add Session
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                      <DialogHeader>
                        <DialogTitle>Create New Session</DialogTitle>
                        <DialogDescription>
                          Configure session details, participants, and trainers
                        </DialogDescription>
                      </DialogHeader>
                      <form onSubmit={handleCreateSession} className="space-y-6">
                        {/* Session Details */}
                        <div className="space-y-4">
                          <h3 className="font-semibold text-lg">Session Details</h3>
                          <div>
                            <Label htmlFor="session-program">Program/Module *</Label>
                            <Select
                              value={sessionForm.program_id}
                              onValueChange={(value) => setSessionForm({ ...sessionForm, program_id: value })}
                              required
                            >
                              <SelectTrigger data-testid="session-program-select">
                                <SelectValue placeholder="Select program" />
                              </SelectTrigger>
                              <SelectContent>
                                {programs.map((program) => (
                                  <SelectItem key={program.id} value={program.id}>
                                    {program.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label htmlFor="session-company">Company *</Label>
                            <Select
                              value={sessionForm.company_id}
                              onValueChange={(value) => setSessionForm({ ...sessionForm, company_id: value })}
                              required
                            >
                              <SelectTrigger data-testid="session-company-select">
                                <SelectValue placeholder="Select company" />
                              </SelectTrigger>
                              <SelectContent>
                                {companies.map((company) => (
                                  <SelectItem key={company.id} value={company.id}>
                                    {company.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label htmlFor="session-location">Location *</Label>
                            <Input
                              id="session-location"
                              data-testid="session-location-input"
                              value={sessionForm.location}
                              onChange={(e) => setSessionForm({ ...sessionForm, location: e.target.value })}
                              required
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <Label htmlFor="start-date">Start Date *</Label>
                              <Input
                                id="start-date"
                                data-testid="session-start-date-input"
                                type="date"
                                value={sessionForm.start_date}
                                onChange={(e) => setSessionForm({ ...sessionForm, start_date: e.target.value })}
                                required
                              />
                            </div>
                            <div>
                              <Label htmlFor="end-date">End Date *</Label>
                              <Input
                                id="end-date"
                                data-testid="session-end-date-input"
                                type="date"
                                value={sessionForm.end_date}
                                onChange={(e) => setSessionForm({ ...sessionForm, end_date: e.target.value })}
                                required
                              />
                            </div>
                          </div>
                        </div>

                        {/* Assign Trainers */}
                        <div className="space-y-4 border-t pt-4">
                          <h3 className="font-semibold text-lg">Assign Trainers</h3>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <Label>Select Trainer</Label>
                              <Select
                                value={newTrainerAssignment.trainer_id}
                                onValueChange={(value) => setNewTrainerAssignment({ ...newTrainerAssignment, trainer_id: value })}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="Select trainer" />
                                </SelectTrigger>
                                <SelectContent>
                                  {trainers.map((trainer) => (
                                    <SelectItem key={trainer.id} value={trainer.id}>
                                      {trainer.full_name}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <div>
                              <Label>Role for This Session</Label>
                              <Select
                                value={newTrainerAssignment.role}
                                onValueChange={(value) => setNewTrainerAssignment({ ...newTrainerAssignment, role: value })}
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="regular">Regular Trainer</SelectItem>
                                  <SelectItem value="chief">Chief Trainer</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                          </div>
                          <Button
                            type="button"
                            onClick={handleAddTrainerAssignment}
                            variant="outline"
                            className="w-full"
                          >
                            <Plus className="w-4 h-4 mr-2" />
                            Assign Trainer
                          </Button>
                          {sessionForm.trainer_assignments.length > 0 && (
                            <div className="space-y-2">
                              <Label className="text-sm text-gray-700">Assigned Trainers</Label>
                              {sessionForm.trainer_assignments.map((assignment, idx) => (
                                <div key={idx} className="flex justify-between items-center p-2 bg-blue-50 rounded">
                                  <span className="text-sm">
                                    {getTrainerName(assignment.trainer_id)} - <strong>{assignment.role === "chief" ? "Chief Trainer" : "Regular Trainer"}</strong>
                                  </span>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleRemoveTrainerAssignment(idx)}
                                  >
                                    <Trash2 className="w-4 h-4 text-red-600" />
                                  </Button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Assign Coordinator */}
                        <div className="space-y-4 border-t pt-4">
                          <h3 className="font-semibold text-lg">Assign Coordinator (Optional)</h3>
                          <p className="text-sm text-gray-500">Any staff member can be assigned as coordinator for this session</p>
                          <Select
                            value={sessionForm.coordinator_id}
                            onValueChange={(value) => setSessionForm({ ...sessionForm, coordinator_id: value })}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select coordinator" />
                            </SelectTrigger>
                            <SelectContent>
                              {allStaffForCoordinator.map((staff) => (
                                <SelectItem key={staff.id} value={staff.id}>
                                  {staff.full_name} ({staff.role.replace('_', ' ')})
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Marketing Commission */}
                        <div className="space-y-4 border-t pt-4">
                          <h3 className="font-semibold text-lg flex items-center gap-2">
                            <DollarSign className="w-5 h-5 text-green-600" />
                            Marketing Commission (Optional)
                          </h3>
                          
                          {/* Create New Marketing Person Checkbox */}
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              id="create-new-marketing"
                              checked={sessionForm.create_new_marketing}
                              onChange={(e) => setSessionForm({ 
                                ...sessionForm, 
                                create_new_marketing: e.target.checked,
                                marketing_user_id: e.target.checked ? "" : sessionForm.marketing_user_id 
                              })}
                            />
                            <Label htmlFor="create-new-marketing">Create new marketing person</Label>
                          </div>
                          
                          {sessionForm.create_new_marketing ? (
                            <div className="grid grid-cols-2 gap-4 p-4 bg-blue-50 rounded-lg">
                              <div>
                                <Label>Full Name *</Label>
                                <Input
                                  value={sessionForm.new_marketing_name}
                                  onChange={(e) => setSessionForm({ ...sessionForm, new_marketing_name: e.target.value })}
                                  placeholder="Marketing person name"
                                />
                              </div>
                              <div>
                                <Label>IC Number * (will be user ID)</Label>
                                <Input
                                  value={sessionForm.new_marketing_id}
                                  onChange={(e) => setSessionForm({ ...sessionForm, new_marketing_id: e.target.value })}
                                  placeholder="IC number (e.g. 890101-12-5678)"
                                />
                                <p className="text-xs text-gray-500 mt-1">Default password: mddrc1</p>
                              </div>
                            </div>
                          ) : (
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <Label>Marketing Person</Label>
                                <Select
                                  value={sessionForm.marketing_user_id || "none"}
                                  onValueChange={(value) => setSessionForm({ ...sessionForm, marketing_user_id: value === "none" ? "" : value })}
                                >
                                  <SelectTrigger>
                                    <SelectValue placeholder="Select marketing person" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="none">None</SelectItem>
                                    {marketingUsers.map((user) => (
                                      <SelectItem key={user.id} value={user.id}>
                                        {user.full_name} ({user.role}{user.additional_roles?.includes("marketing") ? " + Marketing" : ""})
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              <div>
                                <Label>Commission Type</Label>
                                <Select
                                  value={sessionForm.commission_type}
                                  onValueChange={(value) => setSessionForm({ ...sessionForm, commission_type: value })}
                                >
                                  <SelectTrigger>
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="percentage">Percentage (%)</SelectItem>
                                    <SelectItem value="fixed">Fixed Amount (RM)</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>
                          )}
                          
                          {(sessionForm.marketing_user_id || sessionForm.create_new_marketing) && (
                            <div className="grid grid-cols-2 gap-4">
                              {!sessionForm.create_new_marketing && (
                                <div>
                                  <Label>Commission Type</Label>
                                  <Select
                                    value={sessionForm.commission_type}
                                    onValueChange={(value) => setSessionForm({ ...sessionForm, commission_type: value })}
                                  >
                                    <SelectTrigger>
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="percentage">Percentage of Profit</SelectItem>
                                      <SelectItem value="fixed">Fixed Amount (RM)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>
                              )}
                              {sessionForm.create_new_marketing && (
                                <div>
                                  <Label>Commission Type</Label>
                                  <Select
                                    value={sessionForm.commission_type}
                                    onValueChange={(value) => setSessionForm({ ...sessionForm, commission_type: value })}
                                  >
                                    <SelectTrigger>
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="percentage">Percentage of Profit</SelectItem>
                                      <SelectItem value="fixed">Fixed Amount (RM)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>
                              )}
                              {sessionForm.commission_type === "percentage" ? (
                                <div>
                                  <Label>Commission Rate (%)</Label>
                                  <Input
                                    type="number"
                                    min="0"
                                    max="100"
                                    step="0.1"
                                    value={sessionForm.commission_rate}
                                    onChange={(e) => setSessionForm({ ...sessionForm, commission_rate: e.target.value })}
                                    placeholder="e.g. 10"
                                  />
                                  <p className="text-xs text-gray-500 mt-1">% of NET profit (after all expenses)</p>
                                </div>
                              ) : (
                                <div>
                                  <Label>Fixed Amount (RM)</Label>
                                  <Input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    value={sessionForm.commission_fixed_amount}
                                    onChange={(e) => setSessionForm({ ...sessionForm, commission_fixed_amount: e.target.value })}
                                    placeholder="e.g. 500"
                                  />
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Add Supervisor (Optional) */}
                        <div className="space-y-4 border-t pt-4">
                          <h3 className="font-semibold text-lg">Add Supervisor (Optional)</h3>
                          
                          {/* Match Status Indicator */}
                          {supervisorMatchStatus?.exists && (
                            <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-sm">
                              <p className="font-semibold text-blue-800">✓ Existing supervisor found</p>
                              <p className="text-blue-600 mt-1">
                                {supervisorMatchStatus.user.full_name} ({supervisorMatchStatus.user.email})
                                <br />
                                Will be linked to this session and data will be updated.
                              </p>
                            </div>
                          )}
                          
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <Label htmlFor="supervisor-name">Full Name</Label>
                              <Input
                                id="supervisor-name"
                                value={newSupervisor.full_name}
                                onChange={(e) => setNewSupervisor({ ...newSupervisor, full_name: e.target.value })}
                                placeholder="Supervisor Name"
                              />
                            </div>
                            <div>
                              <Label htmlFor="supervisor-id">ID Number</Label>
                              <Input
                                id="supervisor-id"
                                value={newSupervisor.id_number}
                                onChange={(e) => setNewSupervisor({ ...newSupervisor, id_number: e.target.value })}
                                placeholder="ID123456"
                              />
                            </div>
                            <div>
                              <Label htmlFor="supervisor-email">Email</Label>
                              <Input
                                id="supervisor-email"
                                type="email"
                                value={newSupervisor.email}
                                onChange={(e) => setNewSupervisor({ ...newSupervisor, email: e.target.value })}
                                placeholder="supervisor@example.com"
                              />
                            </div>
                            <div>
                              <Label htmlFor="supervisor-phone">Phone Number</Label>
                              <Input
                                id="supervisor-phone"
                                type="tel"
                                value={newSupervisor.phone_number}
                                onChange={(e) => setNewSupervisor({ ...newSupervisor, phone_number: e.target.value })}
                                placeholder="+1234567890"
                              />
                            </div>
                            <div className="col-span-2">
                              <Label htmlFor="supervisor-password">Password</Label>
                              <Input
                                id="supervisor-password"
                                type="password"
                                value={newSupervisor.password}
                                onChange={(e) => setNewSupervisor({ ...newSupervisor, password: e.target.value })}
                                placeholder="Password"
                              />
                            </div>
                          </div>
                          <Button
                            type="button"
                            onClick={handleAddSupervisor}
                            variant="outline"
                            className="w-full"
                          >
                            <Plus className="w-4 h-4 mr-2" />
                            {supervisorMatchStatus?.exists ? "Link Existing Supervisor" : "Add New Supervisor"}
                          </Button>

                          {/* Show added supervisors */}
                          {sessionForm.supervisors.length > 0 && (
                            <div className="space-y-2 border-t pt-4 mt-4">
                              <h4 className="font-semibold text-sm text-gray-700">
                                Supervisors to Add ({sessionForm.supervisors.length})
                              </h4>
                              {sessionForm.supervisors.map((sup, index) => (
                                <div
                                  key={index}
                                  className="flex justify-between items-center p-3 bg-purple-50 rounded-lg"
                                >
                                  <div>
                                    <p className="font-medium text-sm">{sup.full_name}</p>
                                    <p className="text-xs text-gray-600">
                                      {sup.email} • ID: {sup.id_number}
                                    </p>
                                  </div>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                      const updated = sessionForm.supervisors.filter((_, i) => i !== index);
                                      setSessionForm({ ...sessionForm, supervisors: updated });
                                    }}
                                  >
                                    <Trash2 className="w-4 h-4 text-red-600" />
                                  </Button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Add Participants */}
                        <div className="space-y-4 border-t pt-4">
                          <h3 className="font-semibold text-lg">Add Participants</h3>
                          <p className="text-sm text-gray-600">
                            Type participant details below. Login ID will be their IC number and default password is &quot;mddrc1&quot;. System will automatically link existing users if name or ID number matches.
                          </p>
                          
                          {/* Match Status Indicator */}
                          {participantMatchStatus?.exists && (
                            <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-sm">
                              <p className="font-semibold text-blue-800">✓ Existing participant found</p>
                              <p className="text-blue-600 mt-1">
                                {participantMatchStatus.user.full_name} ({participantMatchStatus.user.email})
                                <br />
                                Will be linked to this session and data will be updated.
                              </p>
                            </div>
                          )}

                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <Label htmlFor="participant-name">Full Name *</Label>
                              <Input
                                id="participant-name"
                                data-testid="participant-name-input"
                                value={newParticipant.full_name}
                                onChange={(e) => setNewParticipant({ ...newParticipant, full_name: e.target.value })}
                                placeholder="John Doe"
                              />
                            </div>
                            <div>
                              <Label htmlFor="participant-id">ID Number * (will be used as login ID)</Label>
                              <Input
                                id="participant-id"
                                data-testid="participant-id-input"
                                value={newParticipant.id_number}
                                onChange={(e) => setNewParticipant({ ...newParticipant, id_number: e.target.value })}
                                placeholder="990101-01-1234"
                              />
                            </div>
                            <div>
                              <Label htmlFor="participant-email">Email (optional)</Label>
                              <Input
                                id="participant-email"
                                data-testid="participant-email-input"
                                type="email"
                                value={newParticipant.email}
                                onChange={(e) => setNewParticipant({ ...newParticipant, email: e.target.value })}
                                placeholder="john@example.com (optional)"
                              />
                            </div>
                            <div>
                              <Label htmlFor="participant-phone">Phone Number (optional)</Label>
                              <Input
                                id="participant-phone"
                                data-testid="participant-phone-input"
                                type="tel"
                                value={newParticipant.phone_number}
                                onChange={(e) => setNewParticipant({ ...newParticipant, phone_number: e.target.value })}
                                placeholder="+60123456789 (optional)"
                              />
                            </div>
                          </div>
                          <p className="text-xs text-gray-500 bg-blue-50 p-2 rounded">
                            💡 Default login: IC number / password: mddrc1
                          </p>
                          <Button
                            type="button"
                            data-testid="add-participant-button"
                            onClick={handleAddParticipant}
                            variant="outline"
                            className="w-full"
                          >
                            <Plus className="w-4 h-4 mr-2" />
                            {participantMatchStatus?.exists ? "Link Existing Participant" : "Add New Participant"}
                          </Button>
                        </div>

                        {sessionForm.participants.length > 0 && (
                          <div className="space-y-2 border-t pt-4">
                            <h3 className="font-semibold text-sm text-gray-700">
                              Participants ({sessionForm.participants.length})
                            </h3>
                            {sessionForm.participants.map((participant, index) => (
                              <div
                                key={index}
                                data-testid={`participant-list-item-${index}`}
                                className="flex justify-between items-center p-3 bg-green-50 rounded-lg"
                              >
                                <div>
                                  <p className="font-medium text-sm">{participant.full_name}</p>
                                  <p className="text-xs text-gray-600">
                                    {participant.email} • ID: {participant.id_number}
                                  </p>
                                </div>
                                <Button
                                  type="button"
                                  data-testid={`remove-participant-${index}`}
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleRemoveParticipant(index)}
                                >
                                  <Trash2 className="w-4 h-4 text-red-600" />
                                </Button>
                              </div>
                            ))}
                          </div>
                        )}

                        <Button
                          data-testid="submit-session-button"
                          type="submit"
                          className="w-full"
                          disabled={sessionForm.participants.length === 0}
                        >
                          Create Session with {sessionForm.participants.length} Participant(s)
                        </Button>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                {programs.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-gray-500">Please create at least one program first</p>
                  </div>
                ) : companies.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-gray-500">Please create at least one company first</p>
                  </div>
                ) : (
                  <>
                    <div className="mb-4 flex flex-wrap gap-4 items-end">
                      <div className="flex-1 min-w-[200px]">
                        <SearchBar
                          placeholder="Search sessions by name, company, program, or location..."
                          onSearch={setSessionsSearch}
                          className="w-full"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <Label className="text-sm whitespace-nowrap">Month:</Label>
                        <Input
                          type="month"
                          value={sessionsMonthFilter}
                          onChange={(e) => setSessionsMonthFilter(e.target.value)}
                          className="w-40"
                        />
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSessionsMonthFilter("all")}
                          className={sessionsMonthFilter === "all" ? "bg-blue-100" : ""}
                        >
                          All
                        </Button>
                      </div>
                    </div>
                    {sessionsMonthFilter && sessionsMonthFilter !== "all" && (
                      <div className="mb-3 text-sm text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
                        Showing sessions for: <strong>{new Date(sessionsMonthFilter + '-01').toLocaleString('en-MY', { month: 'long', year: 'numeric' })}</strong>
                        {' '}({filteredSessions.length} session{filteredSessions.length !== 1 ? 's' : ''})
                      </div>
                    )}
                    <div className="space-y-3">
                      {filteredSessions.length === 0 ? (
                        <p className="text-gray-500 text-center py-8">
                          {sessionsSearch || sessionsMonthFilter !== "all" ? "No sessions match your filters." : "No sessions yet"}
                        </p>
                      ) : (
                        filteredSessions.map((session) => {
                        const company = companies.find((c) => c.id === session.company_id);
                        const program = programs.find((p) => p.id === session.program_id);
                        return (
                          <div
                            key={session.id}
                            data-testid={`session-item-${session.id}`}
                            className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg hover:shadow-md transition-shadow"
                          >
                            <div className="flex justify-between items-start">
                              <div>
                                <h3 className="font-semibold text-lg text-gray-900">{session.company_name || company?.name || "Unknown Company"}</h3>
                                <p className="text-base text-gray-700 mt-1">{session.program_name || program?.name || "Unknown Program"}</p>
                                <div className="mt-2 text-sm text-gray-600 space-y-1">
                                  <p>Session: {session.name}</p>
                                  <p>Location: {session.location}</p>
                                  <p>Duration: {session.start_date} to {session.end_date}</p>
                                  {session.trainer_assignments && session.trainer_assignments.length > 0 && (
                                    <p>Trainers: {session.trainer_assignments.map(t => `${getTrainerName(t.trainer_id)} (${t.role})`).join(", ")}</p>
                                  )}
                                  {session.coordinator_id && (
                                    <p>Coordinator: {getCoordinatorName(session.coordinator_id)}</p>
                                  )}
                                </div>
                              </div>
                              <div className="flex flex-col gap-2 items-end">
                                <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                                  {session.participant_ids.length} Participants
                                </span>
                                <div className="flex gap-2 flex-wrap justify-end">
                                  <Button
                                    data-testid={`bulk-upload-session-${session.id}`}
                                    size="sm"
                                    variant="outline"
                                    className="bg-purple-50 border-purple-200 hover:bg-purple-100 text-purple-700"
                                    onClick={() => setBulkUploadSession(session)}
                                  >
                                    <Upload className="w-4 h-4 mr-1" />
                                    Bulk Upload
                                  </Button>
                                  <Button
                                    data-testid={`costing-session-${session.id}`}
                                    size="sm"
                                    variant="outline"
                                    className="bg-green-50 border-green-200 hover:bg-green-100 text-green-700"
                                    onClick={() => setCostingSession(session)}
                                  >
                                    <DollarSign className="w-4 h-4 mr-1" />
                                    Costing
                                  </Button>
                                  <Button
                                    data-testid={`indemnity-session-${session.id}`}
                                    size="sm"
                                    variant="outline"
                                    className="bg-purple-50 border-purple-200 hover:bg-purple-100 text-purple-700"
                                    onClick={() => handleViewIndemnityRecords(session)}
                                  >
                                    <FileText className="w-4 h-4 mr-1" />
                                    Indemnity
                                  </Button>
                                  <Button
                                    data-testid={`edit-session-${session.id}`}
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleEditSession(session)}
                                  >
                                    <Edit className="w-4 h-4 mr-1" />
                                    Edit
                                  </Button>
                                  <Button
                                    data-testid={`delete-session-${session.id}`}
                                    size="sm"
                                    variant="destructive"
                                    onClick={() => handleDeleteClick("session", session)}
                                  >
                                    <Trash2 className="w-4 h-4 mr-1" />
                                    Delete
                                  </Button>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                        })
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>


          {/* Reports Archive Tab */}
          <TabsContent value="reports">
            <Card>
              <CardHeader>
                <CardTitle>Training Reports Archive</CardTitle>
                <CardDescription>
                  Search and access all submitted training reports
                </CardDescription>
              </CardHeader>
              <CardContent>
                {/* Search and Filters */}
                <div className="mb-6 space-y-4">
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <Input
                        placeholder="Search by session name, coordinator, company, program, location..."
                        value={reportsSearch}
                        onChange={(e) => setReportsSearch(e.target.value)}
                        className="w-full"
                      />
                    </div>
                    <Button onClick={loadAllReports} variant="outline">
                      <Search className="w-4 h-4 mr-2" />
                      Search
                    </Button>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Select value={filterCompany} onValueChange={setFilterCompany}>
                      <SelectTrigger>
                        <SelectValue placeholder="Filter by Company" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Companies</SelectItem>
                        {companies.map((company) => (
                          <SelectItem key={company.id} value={company.id}>
                            {company.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <Select value={filterProgram} onValueChange={setFilterProgram}>
                      <SelectTrigger>
                        <SelectValue placeholder="Filter by Program" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Programs</SelectItem>
                        {programs.map((program) => (
                          <SelectItem key={program.id} value={program.id}>
                            {program.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <Input
                      type="date"
                      placeholder="Start Date"
                      value={filterStartDate}
                      onChange={(e) => setFilterStartDate(e.target.value)}
                    />

                    <Input
                      type="date"
                      placeholder="End Date"
                      value={filterEndDate}
                      onChange={(e) => setFilterEndDate(e.target.value)}
                    />
                  </div>

                  {allReports.length > 0 && (
                    <p className="text-sm text-gray-600">
                      Found {allReports.length} training report{allReports.length !== 1 ? 's' : ''}
                    </p>
                  )}
                </div>

                {/* Reports Grid */}
                {loadingReports ? (
                  <div className="flex justify-center items-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                  </div>
                ) : allReports.length === 0 ? (
                  <div className="text-center py-12">
                    <FileText className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                    <p className="text-gray-600">No training reports found</p>
                    <p className="text-sm text-gray-500 mt-2">
                      Reports will appear here once coordinators submit them
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {allReports.map((report) => (
                      <Card key={report.id} className="hover:shadow-lg transition-shadow">
                        <CardHeader className="pb-3">
                          <CardTitle className="text-lg">{report.session_name}</CardTitle>
                          <CardDescription className="space-y-1">
                            <div className="flex items-center text-xs">
                              <Building2 className="w-3 h-3 mr-1" />
                              {report.company_name}
                            </div>
                            <div className="flex items-center text-xs">
                              <Book className="w-3 h-3 mr-1" />
                              {report.program_name}
                            </div>
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          <div className="text-sm space-y-1">
                            <div className="flex justify-between">
                              <span className="text-gray-600">Coordinator:</span>
                              <span className="font-medium">{report.coordinator_name}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Location:</span>
                              <span className="font-medium">{report.session_location}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Dates:</span>
                              <span className="font-medium text-xs">
                                {report.session_start_date} to {report.session_end_date}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Participants:</span>
                              <span className="font-medium">{report.participant_count}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">Submitted:</span>
                              <span className="font-medium text-xs">
                                {new Date(report.submitted_at).toLocaleDateString()}
                              </span>
                            </div>
                          </div>

                          <div className="pt-3 border-t space-y-2">
                            <Button
                              onClick={() => handleDownloadReportPDF(report.session_id)}
                              className="w-full bg-green-600 hover:bg-green-700"
                              size="sm"
                            >
                              <Download className="w-4 h-4 mr-2" />
                              Download PDF
                            </Button>
                            <Button
                              onClick={() => handleViewReportDetails(report)}
                              variant="outline"
                              className="w-full"
                              size="sm"
                            >
                              <FileText className="w-4 h-4 mr-2" />
                              View Details
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Report Details Dialog */}
            <Dialog open={reportDetailsOpen} onOpenChange={setReportDetailsOpen}>
              <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>Training Report Details</DialogTitle>
                  <DialogDescription>
                    {selectedReport?.session_name}
                  </DialogDescription>
                </DialogHeader>
                {selectedReport && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm font-semibold text-gray-700">Company</p>
                        <p className="text-sm">{selectedReport.company_name}</p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-700">Program</p>
                        <p className="text-sm">{selectedReport.program_name}</p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-700">Location</p>
                        <p className="text-sm">{selectedReport.session_location}</p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-700">Coordinator</p>
                        <p className="text-sm">{selectedReport.coordinator_name}</p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-700">Training Period</p>
                        <p className="text-sm">
                          {selectedReport.session_start_date} to {selectedReport.session_end_date}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-700">Participants</p>
                        <p className="text-sm">{selectedReport.participant_count} participants</p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-700">Submitted Date</p>
                        <p className="text-sm">
                          {new Date(selectedReport.submitted_at).toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-700">Status</p>
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          {selectedReport.status}
                        </span>
                      </div>
                    </div>

                    <div className="border-t pt-4">
                      <p className="text-sm font-semibold text-gray-700 mb-2">Files</p>
                      <div className="space-y-2">
                        {selectedReport.pdf_filename && (
                          <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                            <div className="flex items-center">
                              <FileText className="w-5 h-5 text-red-600 mr-2" />
                              <span className="text-sm font-medium">Final Report (PDF)</span>
                            </div>
                            <Button
                              onClick={() => handleDownloadReportPDF(selectedReport.session_id)}
                              size="sm"
                              variant="outline"
                            >
                              <Download className="w-4 h-4 mr-1" />
                              Download
                            </Button>
                          </div>
                        )}
                        {selectedReport.docx_filename && (
                          <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                            <div className="flex items-center">
                              <FileText className="w-5 h-5 text-blue-600 mr-2" />
                              <span className="text-sm font-medium">Original Report (DOCX)</span>
                            </div>
                            <span className="text-xs text-gray-500">{selectedReport.docx_filename}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </DialogContent>
            </Dialog>
          </TabsContent>

          {/* Finance Tab */}
          <TabsContent value="finance">
            <div className="space-y-6">
              {/* Year Filter */}
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-3">
                  <Label className="text-sm font-medium text-gray-700">Financial Year:</Label>
                  <Select value={financeYear?.toString()} onValueChange={(val) => setFinanceYear(parseInt(val))}>
                    <SelectTrigger className="w-[140px]" data-testid="admin-year-selector">
                      <SelectValue placeholder="Select Year" />
                    </SelectTrigger>
                    <SelectContent>
                      {financeAvailableYears.map(year => (
                        <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="text-sm text-gray-500">
                  Showing data for <span className="font-semibold text-gray-800">{financeYear}</span>
                </div>
              </div>

              {/* Finance Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-blue-700">Total Invoices</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-blue-900">
                      <span id="finance-total-invoices">{financeSummary.invoiceCount || financeSummary.invoices.length}</span> (RM {financeSummary.totalInvoiced.toLocaleString()})
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-green-700">Total Collected</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-green-900" id="finance-collected">RM {financeSummary.totalCollected.toLocaleString()}</div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-orange-700">Outstanding</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-orange-900" id="finance-outstanding">RM {financeSummary.totalOutstanding.toLocaleString()}</div>
                  </CardContent>
                </Card>
                <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-purple-700">Pending Payables</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-purple-900" id="finance-payables">RM {financeSummary.totalPayables.toLocaleString()}</div>
                  </CardContent>
                </Card>
              </div>

              {/* Quick Access to Full Finance Portal */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <DollarSign className="w-5 h-5 text-green-600" />
                    Finance Portal
                  </CardTitle>
                  <CardDescription>
                    Access the full Finance Portal for invoice management, payments, and reports
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-4">
                    <Button 
                      className="bg-green-600 hover:bg-green-700"
                      onClick={() => window.open('/finance', '_blank')}
                    >
                      <DollarSign className="w-4 h-4 mr-2" />
                      Open Finance Portal
                    </Button>
                    <Button 
                      variant="outline"
                      onClick={async () => {
                        try {
                          const response = await axiosInstance.get('/finance/dashboard');
                          const data = response.data;
                          document.getElementById('finance-total-invoices').textContent = data.invoices.total;
                          document.getElementById('finance-collected').textContent = `RM ${data.financials.total_collected.toLocaleString()}`;
                          document.getElementById('finance-outstanding').textContent = `RM ${data.financials.outstanding_receivables.toLocaleString()}`;
                          document.getElementById('finance-payables').textContent = `RM ${data.payables.pending_total.toLocaleString()}`;
                          toast.success('Finance data refreshed');
                        } catch (error) {
                          toast.error('Failed to load finance data');
                        }
                      }}
                    >
                      Refresh Data
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Recent Invoices Preview */}
              <Card>
                <CardHeader>
                  <CardTitle>Recent Invoices</CardTitle>
                  <CardDescription>Latest invoices from training sessions</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-500 text-center py-4">
                    Open the Finance Portal to view and manage all invoices
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Staff Tab - Unified Staff Management */}
          <TabsContent value="staff">
            <Card>
              <CardHeader>
                <CardTitle>Staff Management</CardTitle>
                <CardDescription>Manage all staff members (Coordinators, Assistant Admins, Trainers)</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <SearchBar
                    placeholder="Search staff by name, email, or ID..."
                    onSearch={setStaffSearch}
                    className="max-w-md"
                  />
                </div>
                <div className="space-y-6">
                  
                  {/* Coordinators Section */}
                  <Card className="border-2 border-purple-200">
                    <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50">
                      <div className="flex justify-between items-center">
                        <div>
                          <CardTitle className="text-lg">Coordinators</CardTitle>
                          <CardDescription>Manage training coordinators ({filteredCoordinators.length} {staffSearch ? 'found' : 'total'})</CardDescription>
                        </div>
                        <Dialog open={coordinatorDialogOpen} onOpenChange={setCoordinatorDialogOpen}>
                          <DialogTrigger asChild>
                            <Button size="sm" data-testid="create-coordinator-button">
                              <UserCog className="w-4 h-4 mr-2" />
                              Add Coordinator
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Create New Coordinator</DialogTitle>
                              <DialogDescription>
                                Add a coordinator account
                              </DialogDescription>
                            </DialogHeader>
                            <form onSubmit={handleCreateCoordinator} className="space-y-4">
                              <div>
                                <Label htmlFor="coordinator-name">Full Name *</Label>
                                <Input
                                  id="coordinator-name"
                                  data-testid="coordinator-name-input"
                                  value={coordinatorForm.full_name}
                                  onChange={(e) => setCoordinatorForm({ ...coordinatorForm, full_name: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="coordinator-id">ID Number *</Label>
                                <Input
                                  id="coordinator-id"
                                  data-testid="coordinator-id-input"
                                  value={coordinatorForm.id_number}
                                  onChange={(e) => setCoordinatorForm({ ...coordinatorForm, id_number: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="coordinator-email">Email *</Label>
                                <Input
                                  id="coordinator-email"
                                  data-testid="coordinator-email-input"
                                  type="email"
                                  value={coordinatorForm.email}
                                  onChange={(e) => setCoordinatorForm({ ...coordinatorForm, email: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="coordinator-password">Password *</Label>
                                <Input
                                  id="coordinator-password"
                                  data-testid="coordinator-password-input"
                                  type="password"
                                  value={coordinatorForm.password}
                                  onChange={(e) => setCoordinatorForm({ ...coordinatorForm, password: e.target.value })}
                                  required
                                />
                              </div>
                              <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-lg">
                                <input
                                  type="checkbox"
                                  id="coordinator-marketing"
                                  checked={coordinatorForm.additional_roles.includes("marketing")}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setCoordinatorForm({ ...coordinatorForm, additional_roles: [...coordinatorForm.additional_roles, "marketing"] });
                                    } else {
                                      setCoordinatorForm({ ...coordinatorForm, additional_roles: coordinatorForm.additional_roles.filter(r => r !== "marketing") });
                                    }
                                  }}
                                  className="w-4 h-4"
                                />
                                <Label htmlFor="coordinator-marketing" className="text-sm font-medium">
                                  Also has Marketing access (can view training calendar & own commission)
                                </Label>
                              </div>
                              <Button data-testid="submit-coordinator-button" type="submit" className="w-full">
                                Create Coordinator
                              </Button>
                            </form>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        {filteredCoordinators.length === 0 ? (
                          <p className="text-gray-500 text-center py-8">
                            {staffSearch ? "No coordinators match your search." : "No coordinators yet"}
                          </p>
                        ) : (
                          filteredCoordinators.map((coordinator) => (
                            <div
                              key={coordinator.id}
                              data-testid={`coordinator-item-${coordinator.id}`}
                              className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg hover:bg-purple-100 transition-colors flex justify-between items-start"
                            >
                              <div>
                                <h3 className="font-semibold text-gray-900">{coordinator.full_name}</h3>
                                <p className="text-sm text-gray-600">{coordinator.email}</p>
                                <div className="flex gap-2 mt-2 flex-wrap">
                                  <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                                    Coordinator
                                  </span>
                                  {coordinator.additional_roles?.includes("marketing") && (
                                    <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                      + Marketing
                                    </span>
                                  )}
                                  <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                                    ID: {coordinator.id_number}
                                  </span>
                                </div>
                              </div>
                              <div className="flex gap-2">
                                <Button
                                  data-testid={`edit-coordinator-${coordinator.id}`}
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleEditStaff(coordinator)}
                                >
                                  <Edit className="w-4 h-4" />
                                </Button>
                                <Button
                                  data-testid={`delete-coordinator-${coordinator.id}`}
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => handleDeleteClick("coordinator", coordinator)}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Assistant Admins Section */}
                  <Card className="border-2 border-blue-200">
                    <CardHeader className="bg-gradient-to-r from-blue-50 to-cyan-50">
                      <div className="flex justify-between items-center">
                        <div>
                          <CardTitle className="text-lg">Assistant Admins</CardTitle>
                          <CardDescription>Manage assistant administrators ({filteredAssistantAdmins.length} {staffSearch ? 'found' : 'total'})</CardDescription>
                        </div>
                        <Dialog open={assistantAdminDialogOpen} onOpenChange={setAssistantAdminDialogOpen}>
                          <DialogTrigger asChild>
                            <Button size="sm" data-testid="create-assistant-admin-button">
                              <UserPlus className="w-4 h-4 mr-2" />
                              Add Assistant Admin
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Create New Assistant Admin</DialogTitle>
                              <DialogDescription>
                                Add an assistant admin account
                              </DialogDescription>
                            </DialogHeader>
                            <form onSubmit={handleCreateAssistantAdmin} className="space-y-4">
                              <div>
                                <Label htmlFor="assistant-admin-name">Full Name *</Label>
                                <Input
                                  id="assistant-admin-name"
                                  data-testid="assistant-admin-name-input"
                                  value={assistantAdminForm.full_name}
                                  onChange={(e) => setAssistantAdminForm({ ...assistantAdminForm, full_name: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="assistant-admin-id">ID Number *</Label>
                                <Input
                                  id="assistant-admin-id"
                                  data-testid="assistant-admin-id-input"
                                  value={assistantAdminForm.id_number}
                                  onChange={(e) => setAssistantAdminForm({ ...assistantAdminForm, id_number: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="assistant-admin-email">Email *</Label>
                                <Input
                                  id="assistant-admin-email"
                                  data-testid="assistant-admin-email-input"
                                  type="email"
                                  value={assistantAdminForm.email}
                                  onChange={(e) => setAssistantAdminForm({ ...assistantAdminForm, email: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="assistant-admin-password">Password *</Label>
                                <Input
                                  id="assistant-admin-password"
                                  data-testid="assistant-admin-password-input"
                                  type="password"
                                  value={assistantAdminForm.password}
                                  onChange={(e) => setAssistantAdminForm({ ...assistantAdminForm, password: e.target.value })}
                                  required
                                />
                              </div>
                              <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-lg">
                                <input
                                  type="checkbox"
                                  id="assistant-admin-marketing"
                                  checked={assistantAdminForm.additional_roles.includes("marketing")}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setAssistantAdminForm({ ...assistantAdminForm, additional_roles: [...assistantAdminForm.additional_roles, "marketing"] });
                                    } else {
                                      setAssistantAdminForm({ ...assistantAdminForm, additional_roles: assistantAdminForm.additional_roles.filter(r => r !== "marketing") });
                                    }
                                  }}
                                  className="w-4 h-4"
                                />
                                <Label htmlFor="assistant-admin-marketing" className="text-sm font-medium">
                                  Also has Marketing access
                                </Label>
                              </div>
                              <Button data-testid="submit-assistant-admin-button" type="submit" className="w-full">
                                Create Assistant Admin
                              </Button>
                            </form>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        {filteredAssistantAdmins.length === 0 ? (
                          <p className="text-gray-500 text-center py-8">
                            {staffSearch ? "No assistant admins match your search." : "No assistant admins yet"}
                          </p>
                        ) : (
                          filteredAssistantAdmins.map((assistantAdmin) => (
                            <div
                              key={assistantAdmin.id}
                              data-testid={`assistant-admin-item-${assistantAdmin.id}`}
                              className="p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg hover:bg-blue-100 transition-colors flex justify-between items-start"
                            >
                              <div>
                                <h3 className="font-semibold text-gray-900">{assistantAdmin.full_name}</h3>
                                <p className="text-sm text-gray-600">{assistantAdmin.email}</p>
                                <div className="flex gap-2 mt-2 flex-wrap">
                                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                    Assistant Admin
                                  </span>
                                  {assistantAdmin.additional_roles?.includes("marketing") && (
                                    <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                      + Marketing
                                    </span>
                                  )}
                                  <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                                    ID: {assistantAdmin.id_number}
                                  </span>
                                </div>
                              </div>
                              <div className="flex gap-2">
                                <Button
                                  data-testid={`edit-assistant-admin-${assistantAdmin.id}`}
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleEditStaff(assistantAdmin)}
                                >
                                  <Edit className="w-4 h-4" />
                                </Button>
                                <Button
                                  data-testid={`delete-assistant-admin-${assistantAdmin.id}`}
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => handleDeleteClick("assistant_admin", assistantAdmin)}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Trainers Section */}
                  <Card className="border-2 border-orange-200">
                    <CardHeader className="bg-gradient-to-r from-orange-50 to-amber-50">
                      <div className="flex justify-between items-center">
                        <div>
                          <CardTitle className="text-lg">Trainers</CardTitle>
                          <CardDescription>Create trainer accounts (roles assigned per session) ({filteredTrainers.length} {staffSearch ? 'found' : 'total'})</CardDescription>
                        </div>
                        <Dialog open={trainerDialogOpen} onOpenChange={setTrainerDialogOpen}>
                          <DialogTrigger asChild>
                            <Button size="sm" data-testid="create-trainer-button">
                              <UserPlus className="w-4 h-4 mr-2" />
                              Add Trainer
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Create New Trainer</DialogTitle>
                              <DialogDescription>
                                Add a trainer account
                              </DialogDescription>
                            </DialogHeader>
                            <form onSubmit={handleCreateTrainer} className="space-y-4">
                              <div>
                                <Label htmlFor="trainer-name">Full Name *</Label>
                                <Input
                                  id="trainer-name"
                                  data-testid="trainer-name-input"
                                  value={trainerForm.full_name}
                                  onChange={(e) => setTrainerForm({ ...trainerForm, full_name: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="trainer-id">ID Number *</Label>
                                <Input
                                  id="trainer-id"
                                  data-testid="trainer-id-input"
                                  value={trainerForm.id_number}
                                  onChange={(e) => setTrainerForm({ ...trainerForm, id_number: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="trainer-email">Email *</Label>
                                <Input
                                  id="trainer-email"
                                  data-testid="trainer-email-input"
                                  type="email"
                                  value={trainerForm.email}
                                  onChange={(e) => setTrainerForm({ ...trainerForm, email: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="trainer-password">Password *</Label>
                                <Input
                                  id="trainer-password"
                                  data-testid="trainer-password-input"
                                  type="password"
                                  value={trainerForm.password}
                                  onChange={(e) => setTrainerForm({ ...trainerForm, password: e.target.value })}
                                  required
                                />
                              </div>
                              <Button data-testid="submit-trainer-button" type="submit" className="w-full">
                                Create Trainer
                              </Button>
                            </form>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        {filteredTrainers.length === 0 ? (
                          <p className="text-gray-500 text-center py-8">
                            {staffSearch ? "No trainers match your search." : "No trainers yet"}
                          </p>
                        ) : (
                          filteredTrainers.map((trainer) => (
                            <div
                              key={trainer.id}
                              data-testid={`trainer-item-${trainer.id}`}
                              className="p-4 bg-gradient-to-r from-orange-50 to-amber-50 rounded-lg hover:bg-orange-100 transition-colors flex justify-between items-start"
                            >
                              <div>
                                <h3 className="font-semibold text-gray-900">{trainer.full_name}</h3>
                                <p className="text-sm text-gray-600">{trainer.email}</p>
                                <div className="flex gap-2 mt-2">
                                  <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded">
                                    Trainer
                                  </span>
                                  <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                                    ID: {trainer.id_number}
                                  </span>
                                </div>
                              </div>
                              <div className="flex gap-2">
                                <Button
                                  data-testid={`edit-trainer-${trainer.id}`}
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleEditStaff(trainer)}
                                >
                                  <Edit className="w-4 h-4" />
                                </Button>
                                <Button
                                  data-testid={`delete-trainer-${trainer.id}`}
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => handleDeleteClick("trainer", trainer)}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Finance Users Section */}
                  <Card className="border-2 border-green-200">
                    <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50">
                      <div className="flex justify-between items-center">
                        <div>
                          <CardTitle className="text-lg">Finance Users</CardTitle>
                          <CardDescription>Manage finance portal users ({users.filter(u => u.role === "finance").length} total)</CardDescription>
                        </div>
                        <Dialog open={financeDialogOpen} onOpenChange={setFinanceDialogOpen}>
                          <DialogTrigger asChild>
                            <Button size="sm" className="bg-green-600 hover:bg-green-700">
                              <DollarSign className="w-4 h-4 mr-2" />
                              Add Finance User
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Create Finance User</DialogTitle>
                              <DialogDescription>
                                Add a user who can access the Finance Portal
                              </DialogDescription>
                            </DialogHeader>
                            <form onSubmit={handleCreateFinance} className="space-y-4">
                              <div>
                                <Label htmlFor="finance-name">Full Name *</Label>
                                <Input
                                  id="finance-name"
                                  value={financeForm.full_name}
                                  onChange={(e) => setFinanceForm({ ...financeForm, full_name: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="finance-id">ID Number *</Label>
                                <Input
                                  id="finance-id"
                                  value={financeForm.id_number}
                                  onChange={(e) => setFinanceForm({ ...financeForm, id_number: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="finance-email">Email *</Label>
                                <Input
                                  id="finance-email"
                                  type="email"
                                  value={financeForm.email}
                                  onChange={(e) => setFinanceForm({ ...financeForm, email: e.target.value })}
                                  required
                                />
                              </div>
                              <div>
                                <Label htmlFor="finance-password">Password *</Label>
                                <Input
                                  id="finance-password"
                                  type="password"
                                  value={financeForm.password}
                                  onChange={(e) => setFinanceForm({ ...financeForm, password: e.target.value })}
                                  required
                                />
                              </div>
                              <Button type="submit" className="w-full bg-green-600 hover:bg-green-700">
                                Create Finance User
                              </Button>
                            </form>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <div className="space-y-2">
                        {users.filter(u => u.role === "finance").length === 0 ? (
                          <p className="text-gray-500 text-center py-8">
                            No finance users yet. Create one to access the Finance Portal.
                          </p>
                        ) : (
                          users.filter(u => u.role === "finance").map((financeUser) => (
                            <div
                              key={financeUser.id}
                              className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg hover:bg-green-100 transition-colors flex justify-between items-start"
                            >
                              <div>
                                <h3 className="font-semibold text-gray-900">{financeUser.full_name}</h3>
                                <p className="text-sm text-gray-600">{financeUser.email}</p>
                                <div className="flex gap-2 mt-2">
                                  <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                    Finance
                                  </span>
                                  <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                                    ID: {financeUser.id_number}
                                  </span>
                                </div>
                              </div>
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleEditStaff(financeUser)}
                                >
                                  <Edit className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </CardContent>
                  </Card>

                </div>
              </CardContent>
            </Card>

            {/* Edit Staff Dialog */}
            <Dialog open={editStaffDialogOpen} onOpenChange={setEditStaffDialogOpen}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Edit Staff Member</DialogTitle>
                  <DialogDescription>
                    Update staff member details
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleUpdateStaff} className="space-y-4">
                  <div>
                    <Label htmlFor="edit-staff-name">Full Name *</Label>
                    <Input
                      id="edit-staff-name"
                      value={editStaffForm.full_name}
                      onChange={(e) => setEditStaffForm({ ...editStaffForm, full_name: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="edit-staff-email">Email *</Label>
                    <Input
                      id="edit-staff-email"
                      type="email"
                      value={editStaffForm.email}
                      onChange={(e) => setEditStaffForm({ ...editStaffForm, email: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="edit-staff-id">ID Number *</Label>
                    <Input
                      id="edit-staff-id"
                      value={editStaffForm.id_number}
                      onChange={(e) => setEditStaffForm({ ...editStaffForm, id_number: e.target.value })}
                      required
                    />
                  </div>
                  {editingStaff && ["coordinator", "assistant_admin"].includes(editingStaff.role) && (
                    <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-lg">
                      <input
                        type="checkbox"
                        id="edit-staff-marketing"
                        checked={editStaffForm.additional_roles?.includes("marketing")}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setEditStaffForm({ ...editStaffForm, additional_roles: [...(editStaffForm.additional_roles || []), "marketing"] });
                          } else {
                            setEditStaffForm({ ...editStaffForm, additional_roles: (editStaffForm.additional_roles || []).filter(r => r !== "marketing") });
                          }
                        }}
                        className="w-4 h-4"
                      />
                      <Label htmlFor="edit-staff-marketing" className="text-sm font-medium">
                        Also has Marketing access
                      </Label>
                    </div>
                  )}
                  <Button type="submit" className="w-full">
                    Update Staff Member
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </TabsContent>

          {/* Past Training Tab */}
          <TabsContent value="past-training">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <FileText className="w-5 h-5 mr-2" />
                  Past Training Archive
                </CardTitle>
                <CardDescription>
                  Search and view completed training sessions
                </CardDescription>
              </CardHeader>
              <CardContent>
                {/* Search Filters */}
                <div className="flex flex-wrap items-center gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="month-filter" className="text-sm font-medium">Month:</Label>
                    <Select
                      value={selectedMonth.toString()}
                      onValueChange={(value) => setSelectedMonth(parseInt(value))}
                    >
                      <SelectTrigger className="w-32">
                        <SelectValue placeholder="Select month" />
                      </SelectTrigger>
                      <SelectContent>
                        {generateMonthOptions().map((month) => (
                          <SelectItem key={month.value} value={month.value.toString()}>
                            {month.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Label htmlFor="year-filter" className="text-sm font-medium">Year:</Label>
                    <Select
                      value={selectedYear.toString()}
                      onValueChange={(value) => setSelectedYear(parseInt(value))}
                    >
                      <SelectTrigger className="w-24">
                        <SelectValue placeholder="Year" />
                      </SelectTrigger>
                      <SelectContent>
                        {generateYearOptions().map((year) => (
                          <SelectItem key={year} value={year.toString()}>
                            {year}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <Button
                    onClick={loadPastTraining}
                    disabled={loadingPastTraining}
                    className="flex items-center gap-2"
                  >
                    {loadingPastTraining ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      <Search className="w-4 h-4" />
                    )}
                    Search
                  </Button>
                  
                  <Button
                    onClick={() => {
                      setSelectedMonth(new Date().getMonth() + 1);
                      setSelectedYear(new Date().getFullYear());
                      setPastTrainingSessions([]);
                      setExpandedPastSession(null);
                    }}
                    variant="outline"
                    size="sm"
                  >
                    Clear
                  </Button>
                </div>

                {/* Results */}
                <div className="space-y-4">
                  {loadingPastTraining ? (
                    <div className="flex justify-center items-center py-12">
                      <div className="text-center">
                        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                        <p className="text-gray-600">Searching past training sessions...</p>
                      </div>
                    </div>
                  ) : pastTrainingSessions.length === 0 ? (
                    <div className="text-center py-12">
                      <FileText className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No past training found</h3>
                      <p className="text-gray-600">
                        {selectedMonth && selectedYear 
                          ? `No completed training sessions found for ${generateMonthOptions().find(m => m.value === selectedMonth)?.label} ${selectedYear}`
                          : "Use the search filters above to find past training sessions"
                        }
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <p className="text-sm text-gray-600">
                          Found {pastTrainingSessions.length} training session{pastTrainingSessions.length !== 1 ? 's' : ''}
                        </p>
                      </div>
                      
                      {pastTrainingSessions.map((session) => (
                        <Card key={session.id} className="hover:shadow-md transition-shadow">
                          <CardContent className="p-4">
                            <div className="flex justify-between items-start">
                              <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                  <h3 className="font-semibold text-gray-900">{session.name}</h3>
                                  <Badge variant="secondary" className="text-xs">
                                    {session.completion_status === 'completed' ? 'Completed' : 'Archived'}
                                  </Badge>
                                </div>
                                
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm text-gray-600 mb-3">
                                  <div className="flex items-center gap-1">
                                    <Building2 className="w-4 h-4" />
                                    <span>{session.company_name || 'Unknown Company'}</span>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <Calendar className="w-4 h-4" />
                                    <span>{new Date(session.start_date).toLocaleDateString()}</span>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <Users className="w-4 h-4" />
                                    <span>{session.participant_ids?.length || 0} participants</span>
                                  </div>
                                </div>
                                
                                <p className="text-sm text-gray-600">
                                  <span className="font-medium">Program:</span> {session.program_name || 'Unknown Program'}
                                </p>
                              </div>
                              
                              <div className="flex gap-2">
                                <Button
                                  onClick={() => handlePastSessionClick(session)}
                                  variant="outline"
                                  size="sm"
                                  className="flex items-center gap-1"
                                >
                                  <Eye className="w-4 h-4" />
                                  {expandedPastSession?.id === session.id ? 'Hide Details' : 'View Details'}
                                </Button>
                                <Button
                                  onClick={() => navigate(`/results-summary/${session.id}`)}
                                  size="sm"
                                  className="flex items-center gap-1"
                                >
                                  <FileText className="w-4 h-4" />
                                  View Results
                                </Button>
                              </div>
                            </div>
                            
                            {/* Expanded Details */}
                            {expandedPastSession?.id === session.id && (
                              <div className="mt-4 pt-4 border-t border-gray-200">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                                  <div>
                                    <h4 className="font-medium text-gray-900 mb-2">Session Information</h4>
                                    <div className="space-y-1">
                                      <p><span className="text-gray-600">Location:</span> {session.location}</p>
                                      <p><span className="text-gray-600">Start Date:</span> {new Date(session.start_date).toLocaleString()}</p>
                                      <p><span className="text-gray-600">End Date:</span> {new Date(session.end_date).toLocaleString()}</p>
                                      {session.completed_date && (
                                        <p><span className="text-gray-600">Completed:</span> {new Date(session.completed_date).toLocaleString()}</p>
                                      )}
                                    </div>
                                  </div>
                                  <div>
                                    <h4 className="font-medium text-gray-900 mb-2">Training Team</h4>
                                    <div className="space-y-1">
                                      {session.trainer_assignments?.map((assignment, index) => (
                                        <p key={index}>
                                          <span className="text-gray-600">{assignment.role === 'chief' ? 'Chief Trainer' : 'Trainer'}:</span> {assignment.trainer_name || 'Unknown'}
                                        </p>
                                      ))}
                                      {session.coordinator_name && (
                                        <p><span className="text-gray-600">Coordinator:</span> {session.coordinator_name}</p>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Trainers Tab */}
          {/* All Users Tab */}
          <TabsContent value="users">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>All Users</CardTitle>
                    <CardDescription>View all system users grouped by company. Select users to bulk delete.</CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      variant="outline"
                      onClick={async () => {
                        try {
                          const response = await axiosInstance.get('/users/export/participants', {
                            responseType: 'blob'
                          });
                          const url = window.URL.createObjectURL(new Blob([response.data]));
                          const link = document.createElement('a');
                          link.href = url;
                          link.setAttribute('download', `participants_export_${new Date().toISOString().split('T')[0]}.csv`);
                          document.body.appendChild(link);
                          link.click();
                          link.remove();
                          toast.success('Participant data exported');
                        } catch (error) {
                          toast.error('Failed to export data');
                        }
                      }}
                      className="flex items-center gap-2"
                      data-testid="export-participants-btn"
                    >
                      <Download className="w-4 h-4" />
                      Export Participants
                    </Button>
                    {selectedUsers.length > 0 && (
                      <Button 
                        variant="destructive" 
                        onClick={() => setBulkDeleteDialogOpen(true)}
                        className="flex items-center gap-2"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete Selected ({selectedUsers.length})
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {users.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No users yet</p>
                ) : (
                  <div className="space-y-6">
                    {/* Admin, Trainers, Coordinators (No Company) */}
                    {users.filter(u => !u.company_id).length > 0 && (
                      <div>
                        <div className="flex items-center gap-3 mb-3">
                          <input
                            type="checkbox"
                            className="h-4 w-4 rounded border-gray-300"
                            checked={users.filter(u => !u.company_id).every(u => selectedUsers.includes(u.id))}
                            onChange={() => toggleAllUsers(users.filter(u => !u.company_id))}
                          />
                          <h3 className="text-lg font-semibold text-gray-700">System Users (No Company)</h3>
                        </div>
                        <div className="space-y-2">
                          {users.filter(u => !u.company_id).map((u) => (
                            <div
                              key={u.id}
                              data-testid={`user-item-${u.id}`}
                              className={`p-4 rounded-lg flex justify-between items-center hover:bg-gray-100 transition-colors ${
                                selectedUsers.includes(u.id) ? 'bg-red-50 border-2 border-red-200' : 'bg-gray-50'
                              }`}
                            >
                              <div className="flex items-center gap-3">
                                <input
                                  type="checkbox"
                                  className="h-4 w-4 rounded border-gray-300"
                                  checked={selectedUsers.includes(u.id)}
                                  onChange={() => toggleUserSelection(u.id)}
                                />
                                <div>
                                  <h3 className="font-semibold text-gray-900">{u.full_name}</h3>
                                  <p className="text-sm text-gray-600">{u.email}</p>
                                  <div className="flex gap-2 mt-1">
                                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded capitalize">
                                      {u.role.replace('_', ' ')}
                                    </span>
                                    <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                                      ID: {u.id_number}
                                    </span>
                                    <span className={`text-xs px-2 py-1 rounded ${u.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                      {u.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                  </div>
                                </div>
                              </div>
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    setResetPasswordUser(u);
                                    setResetPasswordDialogOpen(true);
                                  }}
                                  data-testid={`reset-password-${u.id}`}
                                >
                                  <UserCog className="w-4 h-4 mr-1" />
                                  Reset Password
                                </Button>
                                <Button
                                  size="sm"
                                  variant={u.is_active ? "outline" : "default"}
                                  onClick={() => handleToggleUserStatus(u.id, u.is_active)}
                                  data-testid={`toggle-status-${u.id}`}
                                >
                                  {u.is_active ? 'Deactivate' : 'Activate'}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => handleDeleteClick("user", u)}
                                  data-testid={`delete-user-${u.id}`}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Users Grouped by Company */}
                    {companies.map((company) => {
                      const companyUsers = users.filter(u => u.company_id === company.id);
                      if (companyUsers.length === 0) return null;
                      
                      return (
                        <div key={company.id}>
                          <div className="flex items-center gap-3 mb-3">
                            <input
                              type="checkbox"
                              className="h-4 w-4 rounded border-gray-300"
                              checked={companyUsers.every(u => selectedUsers.includes(u.id))}
                              onChange={() => toggleAllUsers(companyUsers)}
                            />
                            <h3 className="text-lg font-semibold text-gray-700">{company.name} ({companyUsers.length} users)</h3>
                          </div>
                          <div className="space-y-2">
                            {companyUsers.map((u) => (
                              <div
                                key={u.id}
                                data-testid={`user-item-${u.id}`}
                                className={`p-4 rounded-lg flex justify-between items-center hover:shadow-md transition-shadow ${
                                  selectedUsers.includes(u.id) ? 'bg-red-50 border-2 border-red-200' : 'bg-gradient-to-r from-blue-50 to-indigo-50'
                                }`}
                              >
                                <div className="flex items-center gap-3">
                                  <input
                                    type="checkbox"
                                    className="h-4 w-4 rounded border-gray-300"
                                    checked={selectedUsers.includes(u.id)}
                                    onChange={() => toggleUserSelection(u.id)}
                                  />
                                  <div>
                                    <h3 className="font-semibold text-gray-900">{u.full_name}</h3>
                                    <p className="text-sm text-gray-600">{u.email}</p>
                                    <div className="flex gap-2 mt-1">
                                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded capitalize">
                                        {u.role.replace('_', ' ')}
                                      </span>
                                      <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                                        ID: {u.id_number}
                                      </span>
                                      <span className={`text-xs px-2 py-1 rounded ${u.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                        {u.is_active ? 'Active' : 'Inactive'}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                                <div className="flex gap-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => {
                                      setResetPasswordUser(u);
                                      setResetPasswordDialogOpen(true);
                                    }}
                                    data-testid={`reset-password-${u.id}`}
                                  >
                                    <UserCog className="w-4 h-4 mr-1" />
                                    Reset Password
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant={u.is_active ? "outline" : "default"}
                                    onClick={() => handleToggleUserStatus(u.id, u.is_active)}
                                    data-testid={`toggle-status-${u.id}`}
                                  >
                                    {u.is_active ? 'Deactivate' : 'Activate'}
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="destructive"
                                    onClick={() => handleDeleteClick("user", u)}
                                    data-testid={`delete-user-${u.id}`}
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </Button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
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
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>Certificates Repository</CardTitle>
                    <CardDescription>View all uploaded participant certificates</CardDescription>
                  </div>
                  <Button onClick={loadAllCertificates} disabled={loadingCertificates}>
                    {loadingCertificates ? "Loading..." : "Refresh"}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {/* Search and Filters */}
                <div className="mb-6 space-y-4">
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <Input
                        placeholder="Search by participant name, ID number, or email..."
                        value={certificatesSearch}
                        onChange={(e) => setCertificatesSearch(e.target.value)}
                        className="w-full"
                      />
                    </div>
                  </div>
                  
                  <div className="flex gap-4">
                    <Select value={filterCertSession} onValueChange={setFilterCertSession}>
                      <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Filter by Session" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Sessions</SelectItem>
                        {sessions.map((session) => (
                          <SelectItem key={session.id} value={session.id}>
                            {session.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    <Select value={filterCertProgram} onValueChange={setFilterCertProgram}>
                      <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Filter by Program" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Programs</SelectItem>
                        {programs.map((program) => (
                          <SelectItem key={program.id} value={program.name}>
                            {program.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    {(certificatesSearch || filterCertSession !== "all" || filterCertProgram !== "all") && (
                      <Button 
                        variant="outline" 
                        onClick={() => {
                          setCertificatesSearch("");
                          setFilterCertSession("all");
                          setFilterCertProgram("all");
                        }}
                      >
                        Clear Filters
                      </Button>
                    )}
                  </div>
                </div>

                {/* Certificates Table */}
                {loadingCertificates ? (
                  <div className="text-center py-8">
                    <p className="text-gray-500">Loading certificates...</p>
                  </div>
                ) : allCertificates.length === 0 ? (
                  <div className="text-center py-12">
                    <Award className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <p className="text-gray-500">No certificates uploaded yet</p>
                    <p className="text-sm text-gray-400 mt-2">Certificates will appear here once coordinators upload them</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-gray-50">
                          <th className="text-left p-3 font-semibold">Participant</th>
                          <th className="text-left p-3 font-semibold">ID Number</th>
                          <th className="text-left p-3 font-semibold">Session</th>
                          <th className="text-left p-3 font-semibold">Program</th>
                          <th className="text-left p-3 font-semibold">Company</th>
                          <th className="text-left p-3 font-semibold">Upload Date</th>
                          <th className="text-center p-3 font-semibold">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {allCertificates
                          .filter((cert) => {
                            // Search filter
                            const searchLower = certificatesSearch.toLowerCase();
                            const matchesSearch = !certificatesSearch || 
                              cert.participant_name?.toLowerCase().includes(searchLower) ||
                              cert.participant_id_number?.toLowerCase().includes(searchLower) ||
                              cert.participant_email?.toLowerCase().includes(searchLower);
                            
                            // Session filter
                            const matchesSession = filterCertSession === "all" || cert.session_id === filterCertSession;
                            
                            // Program filter
                            const matchesProgram = filterCertProgram === "all" || cert.program_name === filterCertProgram;
                            
                            return matchesSearch && matchesSession && matchesProgram;
                          })
                          .map((cert, index) => (
                            <tr key={index} className="border-b hover:bg-gray-50">
                              <td className="p-3">
                                <div>
                                  <p className="font-medium text-gray-900">{cert.participant_name}</p>
                                  <p className="text-xs text-gray-500">{cert.participant_email}</p>
                                </div>
                              </td>
                              <td className="p-3 text-gray-700">{cert.participant_id_number}</td>
                              <td className="p-3">
                                <div>
                                  <p className="font-medium text-gray-900">{cert.session_name}</p>
                                  <p className="text-xs text-gray-500">
                                    {cert.session_start_date} to {cert.session_end_date}
                                  </p>
                                </div>
                              </td>
                              <td className="p-3 text-gray-700">{cert.program_name}</td>
                              <td className="p-3 text-gray-700">{cert.company_name}</td>
                              <td className="p-3 text-gray-700">
                                {cert.uploaded_at ? new Date(cert.uploaded_at).toLocaleDateString() : 'N/A'}
                              </td>
                              <td className="p-3 text-center">
                                <div className="flex gap-2 justify-center">
                                  <Button
                                    size="sm"
                                    onClick={() => handleDownloadCertificate(cert.certificate_url, cert.participant_name)}
                                    className="bg-blue-600 hover:bg-blue-700"
                                  >
                                    <Download className="w-3 h-3 mr-1" />
                                    Download
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}${cert.certificate_url}`, '_blank')}
                                  >
                                    View
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                    
                    {/* Summary */}
                    <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <p className="text-sm text-gray-700">
                        <span className="font-semibold">Total Certificates:</span> {allCertificates.length}
                        {certificatesSearch || filterCertSession !== "all" || filterCertProgram !== "all" ? (
                          <span className="ml-2">
                            | <span className="font-semibold">Filtered:</span> {
                              allCertificates.filter((cert) => {
                                const searchLower = certificatesSearch.toLowerCase();
                                const matchesSearch = !certificatesSearch || 
                                  cert.participant_name?.toLowerCase().includes(searchLower) ||
                                  cert.participant_id_number?.toLowerCase().includes(searchLower) ||
                                  cert.participant_email?.toLowerCase().includes(searchLower);
                                const matchesSession = filterCertSession === "all" || cert.session_id === filterCertSession;
                                const matchesProgram = filterCertProgram === "all" || cert.program_name === filterCertProgram;
                                return matchesSearch && matchesSession && matchesProgram;
                              }).length
                            }
                          </span>
                        ) : null}
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Quotations Tab */}
          <TabsContent value="quotations">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center flex-wrap gap-3">
                  <div>
                    <CardTitle>Quotation Management</CardTitle>
                    <CardDescription>Review and approve marketing quotations</CardDescription>
                  </div>
                  <div className="flex gap-2 items-center">
                    <Badge className="bg-yellow-500 text-white">{pendingQuotations.length} Pending</Badge>
                    <Select value={quotationFilter} onValueChange={setQuotationFilter}>
                      <SelectTrigger className="w-40">
                        <SelectValue placeholder="Filter" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Status</SelectItem>
                        <SelectItem value="pending_approval">Pending Approval</SelectItem>
                        <SelectItem value="approved">Approved</SelectItem>
                        <SelectItem value="rejected">Rejected</SelectItem>
                        <SelectItem value="sent">Sent</SelectItem>
                        <SelectItem value="accepted">Accepted</SelectItem>
                        <SelectItem value="declined">Declined</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {filteredQuotations.length === 0 ? (
                  <p className="text-center text-gray-500 py-8">No quotations found</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-gray-50">
                          <th className="text-left p-3">Quotation No</th>
                          <th className="text-left p-3">Client</th>
                          <th className="text-left p-3">Marketer</th>
                          <th className="text-left p-3">Programme</th>
                          <th className="text-right p-3">Amount</th>
                          <th className="text-center p-3">Status</th>
                          <th className="text-center p-3">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredQuotations.map(q => (
                          <tr key={q.id} className="border-b hover:bg-gray-50">
                            <td className="p-3 font-medium">{q.quotation_number}</td>
                            <td className="p-3">{q.client_name}</td>
                            <td className="p-3">{q.marketer_name}</td>
                            <td className="p-3">{q.programme_name}</td>
                            <td className="p-3 text-right">RM {(q.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                            <td className="p-3 text-center">{getQuotationStatusBadge(q.status)}</td>
                            <td className="p-3">
                              <div className="flex justify-center gap-1">
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  onClick={() => { setSelectedQuotation(q); setViewQuotationDialog(true); }}
                                  title="View Details"
                                >
                                  <Eye className="w-4 h-4" />
                                </Button>
                                
                                {q.status === 'pending_approval' && (
                                  <>
                                    <Button 
                                      variant="ghost" 
                                      size="sm" 
                                      onClick={() => handleApproveQuotation(q.id)}
                                      title="Approve"
                                      className="text-green-600 hover:text-green-700"
                                    >
                                      <CheckCircle className="w-4 h-4" />
                                    </Button>
                                    <Button 
                                      variant="ghost" 
                                      size="sm" 
                                      onClick={() => { setSelectedQuotation(q); setRejectDialogOpen(true); }}
                                      title="Reject"
                                      className="text-red-600 hover:text-red-700"
                                    >
                                      <XCircle className="w-4 h-4" />
                                    </Button>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* All Marketing Clients */}
            <Card className="mt-6">
              <CardHeader>
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <CardTitle className="text-base sm:text-lg">All Marketing Clients</CardTitle>
                    <CardDescription className="text-xs sm:text-sm">View all clients across all marketers</CardDescription>
                  </div>
                  <Button 
                    onClick={() => {
                      window.location.href = `${process.env.REACT_APP_BACKEND_URL}/api/marketing/clients/export`;
                    }}
                    size="sm"
                    variant="outline"
                    className="text-xs sm:text-sm"
                  >
                    <Download className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> Export CSV
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {allClients.length === 0 ? (
                  <p className="text-center text-gray-500 py-4 text-sm">No clients registered yet.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs sm:text-sm">
                      <thead>
                        <tr className="border-b bg-gray-50">
                          <th className="text-left p-2">Company</th>
                          <th className="text-left p-2">Contact Person</th>
                          <th className="text-left p-2 hidden sm:table-cell">Email</th>
                          <th className="text-left p-2 hidden md:table-cell">Phone</th>
                          <th className="text-left p-2">Marketer</th>
                        </tr>
                      </thead>
                      <tbody>
                        {allClients.map(client => (
                          <tr key={client.id} className="border-b hover:bg-gray-50">
                            <td className="p-2 font-medium max-w-[120px] truncate">{client.company_name}</td>
                            <td className="p-2 max-w-[100px] truncate">{client.contact_person}</td>
                            <td className="p-2 max-w-[150px] truncate hidden sm:table-cell">{client.contact_email}</td>
                            <td className="p-2 hidden md:table-cell">{client.contact_phone}</td>
                            <td className="p-2">
                              <Badge variant="outline" className="text-xs">
                                {client.marketer_name}
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Description Items Management */}
            <Card className="mt-6">
              <CardHeader>
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <CardTitle className="text-base sm:text-lg">Quotation Description Items</CardTitle>
                    <CardDescription className="text-xs sm:text-sm">Manage reusable description items for quotations</CardDescription>
                  </div>
                  <Button 
                    onClick={() => {
                      const name = prompt("Enter item name:");
                      if (!name) return;
                      const description = prompt("Enter item description:");
                      if (!description) return;
                      const category = prompt("Enter category (e.g., inclusions, equipment, services):", "inclusions");
                      
                      axiosInstance.post('/marketing/description-items', {
                        name,
                        description,
                        category: category || "inclusions",
                        sort_order: 0
                      }).then(() => {
                        toast.success("Description item created");
                        loadData();
                      }).catch(err => {
                        toast.error(err.response?.data?.detail || "Failed to create item");
                      });
                    }}
                    size="sm"
                    className="text-xs sm:text-sm"
                  >
                    <Plus className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> Add Item
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {descriptionItems.length === 0 ? (
                    <p className="text-center text-gray-500 py-4 text-sm">No description items yet. Add items that marketers can select when creating quotations.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b bg-gray-50">
                            <th className="text-left p-2 text-xs sm:text-sm">Name</th>
                            <th className="text-left p-2 text-xs sm:text-sm">Description</th>
                            <th className="text-left p-2 text-xs sm:text-sm">Category</th>
                            <th className="text-center p-2 text-xs sm:text-sm">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {descriptionItems.map(item => (
                            <tr key={item.id} className="border-b hover:bg-gray-50">
                              <td className="p-2 font-medium text-xs sm:text-sm">{item.name}</td>
                              <td className="p-2 text-xs sm:text-sm max-w-[200px] truncate">{item.description}</td>
                              <td className="p-2 text-xs sm:text-sm">
                                <Badge variant="outline">{item.category}</Badge>
                              </td>
                              <td className="p-2 text-center">
                                <Button 
                                  variant="ghost" 
                                  size="sm"
                                  onClick={() => {
                                    if (confirm(`Delete "${item.name}"?`)) {
                                      axiosInstance.delete(`/marketing/description-items/${item.id}`)
                                        .then(() => {
                                          toast.success("Item deleted");
                                          loadData();
                                        })
                                        .catch(err => toast.error(err.response?.data?.detail || "Failed to delete"));
                                    }
                                  }}
                                  className="text-red-600 h-7 w-7 p-0"
                                >
                                  <Trash2 className="w-3 h-3 sm:w-4 sm:h-4" />
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* PDF Templates Management */}
            <Card className="mt-6">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>PDF Document Templates</CardTitle>
                    <CardDescription>Customize cover letter and terms & conditions for quotation PDFs</CardDescription>
                  </div>
                  <Button 
                    onClick={() => {
                      loadPdfTemplates();
                      setShowPdfTemplatesDialog(true);
                    }}
                    size="sm"
                  >
                    <Edit className="w-4 h-4 mr-2" /> Edit Templates
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h4 className="font-semibold text-blue-900 mb-2">Cover Letter (Page 1)</h4>
                    <p className="text-sm text-blue-700">
                      Customize the introductory letter that appears on the first page of the quotation PDF.
                      Use placeholders like {"{{programme_name}}"}, {"{{company_name}}"}, {"{{contact_person}}"}, {"{{quotation_number}}"}.
                    </p>
                  </div>
                  <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                    <h4 className="font-semibold text-green-900 mb-2">Terms & Conditions (Pages 3-6)</h4>
                    <p className="text-sm text-green-700">
                      Define the terms and conditions that will be included in pages 3-6 of the quotation PDF document.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
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
                              {participant.email} • ID: {participant.id_number}
                            </p>
                          </div>
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
                <Textarea
                  value={pdfTemplates.cover_letter}
                  onChange={(e) => setPdfTemplates({ ...pdfTemplates, cover_letter: e.target.value })}
                  placeholder="RE: QUOTATION FOR {{programme_name}}

Thank you for your interest in our training programmes. We are pleased to submit our quotation for the {{programme_name}} as per your request.

We trust our proposal meets your requirements and look forward to being of service to {{company_name}}."
                  rows={8}
                  className="font-mono text-sm"
                />
              </div>
              
              <div>
                <Label className="text-lg font-semibold">Terms & Conditions (Pages 3+)</Label>
                <p className="text-sm text-gray-500 mb-2">
                  Enter your terms and conditions. Use clear numbering for sections (1., 1.1, 2., etc.)
                </p>
                <Textarea
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
                  className="font-mono text-sm"
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
