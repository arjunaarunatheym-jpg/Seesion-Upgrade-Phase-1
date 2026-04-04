import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useTheme } from "../context/ThemeContext";
import { Plus, Users, LogOut, Calendar, BookOpen, ClipboardList, ClipboardCheck, MessageSquare, FileText, Search, Eye, Building2, BarChart3, Archive, Upload, Settings, DollarSign, Wallet } from "lucide-react";
import TestManagement from "./TestManagement";
import ChecklistManagement from "./ChecklistManagement";
import FeedbackManagement from "./FeedbackManagement";
import MyEarnings from "../components/MyEarnings";
import { DigitalSignatureManager } from "../components/shared/DigitalSignatureManager";
import { PastTrainingTab } from "../components/shared/PastTrainingTab";

const AssistantAdminDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { primaryColor, secondaryColor, companyName, logoUrl } = useTheme();
  const [sessions, setSessions] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [participantForm, setParticipantForm] = useState({
    full_name: "",
    id_number: "",
    company_id: ""
  });

  // Past Training states
  const [pastTrainingSessions, setPastTrainingSessions] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [loadingPastTraining, setLoadingPastTraining] = useState(false);
  const [expandedPastSession, setExpandedPastSession] = useState(null);
  const [activeTab, setActiveTab] = useState("sessions");

  // Bulk upload states
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Session access control states
  const [sessionAccess, setSessionAccess] = useState([]);
  
  // Income states (dual role support)
  const [incomeData, setIncomeData] = useState(null);
  const [coordinatorIncomeData, setCoordinatorIncomeData] = useState(null);
  const [marketingIncomeData, setMarketingIncomeData] = useState(null);
  const [loadingIncome, setLoadingIncome] = useState(false);
  
  // Check additional roles
  const hasCoordinatorRole = user.additional_roles?.includes('coordinator') || user.role === 'coordinator';
  const hasMarketingRole = user.additional_roles?.includes('marketing') || user.role === 'marketing';
  const hasTrainerRole = user.additional_roles?.includes('trainer') || user.role === 'trainer';

  useEffect(() => {
    loadSessions();
    loadCompanies();
    loadPrograms();
  }, []);

  const loadSessions = async () => {
    try {
      const response = await axiosInstance.get("/sessions");
      setSessions(response.data);
    } catch (error) {
      toast.error("Failed to load sessions");
    }
  };

  const loadCompanies = async () => {
    try {
      const response = await axiosInstance.get("/companies");
      setCompanies(response.data);
    } catch (error) {
      toast.error("Failed to load companies");
    }
  };

  const loadPrograms = async () => {
    try {
      const response = await axiosInstance.get("/programs");
      setPrograms(response.data);
    } catch (error) {
      toast.error("Failed to load programs");
    }
  };

  // Load session access status
  const loadSessionAccess = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/participant-access/session/${sessionId}`);
      setSessionAccess(response.data || []);
    } catch (error) {
      console.error('Failed to load session access:', error);
      setSessionAccess([]);
    }
  };

  // Toggle pre-test, post-test, feedback access
  const handleToggleAccess = async (accessType, enabled) => {
    if (!selectedSession) return;
    
    try {
      await axiosInstance.post(`/participant-access/session/${selectedSession.id}/toggle`, {
        access_type: accessType,
        enabled: enabled
      });
      
      toast.success(`${accessType.replace('_', ' ')} ${enabled ? 'enabled' : 'disabled'} for all participants`);
      await loadSessionAccess(selectedSession.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to update ${accessType} access`);
    }
  };

  // Check if any access is enabled
  const isAccessEnabled = (accessType) => {
    if (!sessionAccess || sessionAccess.length === 0) return false;
    const field = accessType === 'pre_test' ? 'can_access_pre_test' : 
                  accessType === 'post_test' ? 'can_access_post_test' : 
                  accessType === 'feedback' ? 'can_access_feedback' : 'can_access_checklist';
    return sessionAccess.some(a => a[field] === true);
  };

  // Load all income data based on roles
  const loadAllIncome = async () => {
    setLoadingIncome(true);
    try {
      // Check if user has coordinator role
      if (hasCoordinatorRole) {
        const coordRes = await axiosInstance.get(`/finance/income/coordinator/${user.id}`);
        setCoordinatorIncomeData(coordRes.data);
      }
      
      // Check if user has marketing role
      if (hasMarketingRole) {
        const mktRes = await axiosInstance.get(`/finance/income/marketing/${user.id}`);
        setMarketingIncomeData(mktRes.data);
      }
      
      // Check if user has trainer role
      if (hasTrainerRole) {
        const trainerRes = await axiosInstance.get(`/finance/income/trainer/${user.id}`);
        setIncomeData(trainerRes.data);
      }
    } catch (error) {
      console.error('Failed to load income:', error);
    } finally {
      setLoadingIncome(false);
    }
  };

  const loadParticipants = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/sessions/${sessionId}/participants`);
      setParticipants(response.data);
    } catch (error) {
      toast.error("Failed to load participants");
    }
  };

  const handleSelectSession = (session) => {
    setSelectedSession(session);
    loadParticipants(session.id);
    loadSessionAccess(session.id);
  };

  const handleAddParticipant = async (e) => {
    e.preventDefault();

    if (!participantForm.full_name || !participantForm.id_number || !participantForm.company_id) {
      toast.error("Please fill in all fields");
      return;
    }

    try {
      // Register participant with default credentials (email optional - auto-generated)
      await axiosInstance.post("/auth/register", {
        full_name: participantForm.full_name,
        id_number: participantForm.id_number,
        // email: not required - will be auto-generated as IC@mddrc.com
        // password: not required - defaults to mddrc1
        role: "participant",
        company_id: participantForm.company_id,
        location: ""
      });

      // Add to session
      await axiosInstance.post(`/sessions/${selectedSession.id}/participants`, {
        participant_ids: [participantForm.id_number] // Using IC as identifier
      });

      toast.success("Participant added successfully! Login: IC number, Password: mddrc1");
      
      setParticipantForm({ full_name: "", id_number: "", company_id: "" });
      setAddDialogOpen(false);
      loadParticipants(selectedSession.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to add participant");
    }
  };

  // Past Training functions
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
      { value: 1, label: "January" },
      { value: 2, label: "February" },
      { value: 3, label: "March" },
      { value: 4, label: "April" },
      { value: 5, label: "May" },
      { value: 6, label: "June" },
      { value: 7, label: "July" },
      { value: 8, label: "August" },
      { value: 9, label: "September" },
      { value: 10, label: "October" },
      { value: 11, label: "November" },
      { value: 12, label: "December" }
    ];
  };

  const handleBulkUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      toast.error("Please upload an Excel file (.xlsx or .xls)");
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axiosInstance.post(
        `/sessions/${selectedSession.id}/participants/bulk-upload`,
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
      loadParticipants(selectedSession.id);
      
      // Reset file input
      e.target.value = '';
    } catch (error) {
      const errorMessage = error.response?.data?.detail || "Failed to upload file";
      toast.error(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div 
      className="min-h-screen"
      style={{
        background: `linear-gradient(to bottom right, ${primaryColor}10, ${secondaryColor}10, ${primaryColor}05)`
      }}
    >
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
            <div className="flex items-center gap-3 sm:gap-4">
              {logoUrl && (
                <button
                  onClick={() => navigate('/calendar')}
                  className="hover:opacity-80 transition-opacity cursor-pointer"
                >
                  <img 
                    src={logoUrl} 
                    alt={companyName}
                    className="h-8 sm:h-10 w-auto object-contain"
                  />
                </button>
              )}
              <div>
                <h1 className="text-lg sm:text-2xl font-bold text-gray-900">Assistant Admin Portal</h1>
                <p className="text-xs sm:text-sm text-gray-600">Add participants to training sessions</p>
              </div>
            </div>
            <div className="flex items-center gap-2 sm:gap-4 self-end sm:self-auto">
              <span className="text-xs sm:text-sm text-gray-600 hidden sm:inline">{user.full_name}</span>
              <Button variant="outline" size="sm" onClick={onLogout}>
                <LogOut className="w-4 h-4 sm:mr-2" />
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Main Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="flex w-full mb-6 h-auto justify-start gap-2 bg-white shadow-sm p-2 rounded-lg overflow-x-auto scrollbar-hide">
            <TabsTrigger value="sessions" className="flex-shrink-0">
              <Calendar className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline">Active Sessions</span>
            </TabsTrigger>
            <TabsTrigger value="session-mgmt" className="flex-shrink-0 bg-gradient-to-r from-blue-500 to-indigo-500 text-white data-[state=active]:text-white">
              <Settings className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline">Session Mgmt</span>
            </TabsTrigger>
            <TabsTrigger value="programs" className="flex-1 min-w-[80px]">
              <BookOpen className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Program Content</span>
              <span className="sm:hidden">Content</span>
            </TabsTrigger>
            <TabsTrigger value="past-training" className="flex-1 min-w-[80px]">
              <Archive className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">Past Training</span>
              <span className="sm:hidden">Archive</span>
            </TabsTrigger>
            <TabsTrigger value="my-earnings" data-testid="my-earnings-tab" className="flex-1 min-w-[80px] bg-gradient-to-r from-emerald-500 to-teal-500 text-white">
              <Wallet className="w-4 h-4 mr-2" />
              <span className="hidden sm:inline">My Earnings</span>
              <span className="sm:hidden">Earnings</span>
            </TabsTrigger>
          </TabsList>

          {/* Active Sessions Tab */}
          <TabsContent value="sessions">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Sessions List */}
          <Card className="md:col-span-1">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Calendar className="w-5 h-5 mr-2" />
                Training Sessions
              </CardTitle>
              <CardDescription>Select a session to add participants</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {sessions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center" data-testid="empty-state">
                    <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center mb-3">
                      <Calendar className="w-7 h-7 text-slate-400" />
                    </div>
                    <h3 className="text-base font-semibold text-slate-700 mb-1">No sessions available</h3>
                    <p className="text-sm text-slate-500">Sessions will appear here when created.</p>
                  </div>
                ) : (
                  sessions.map((session) => (
                    <button
                      key={session.id}
                      onClick={() => handleSelectSession(session)}
                      className={`w-full text-left p-3 rounded-lg border transition-all ${
                        selectedSession?.id === session.id
                          ? "bg-blue-50 border-blue-500"
                          : "bg-white border-gray-200 hover:border-blue-300"
                      }`}
                    >
                      <p className="font-semibold text-sm">{session.company_name || "Unknown Company"}</p>
                      <p className="text-xs text-gray-700 mt-0.5">{session.program_name || "Unknown Program"}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {session.start_date} - {session.end_date}
                      </p>
                    </button>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Participants List */}
          <Card className="md:col-span-2">
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle className="flex items-center">
                    <Users className="w-5 h-5 mr-2" />
                    Participants
                  </CardTitle>
                  <CardDescription>
                    {selectedSession ? `${selectedSession.company_name || "Unknown Company"} - ${selectedSession.program_name || "Unknown Program"}` : "Select a session to view participants"}
                  </CardDescription>
                </div>
                {selectedSession && (
                  <div className="flex gap-2">
                    <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
                      <DialogTrigger asChild>
                        <Button variant="outline">
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

                    <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
                      <DialogTrigger asChild>
                        <Button>
                          <Plus className="w-4 h-4 mr-2" />
                          Add Participant
                        </Button>
                      </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Add New Participant</DialogTitle>
                        <DialogDescription>
                          Enter participant details. Login will be auto-created with IC as username and &apos;mddrc1&apos; as password.
                        </DialogDescription>
                      </DialogHeader>
                      <form onSubmit={handleAddParticipant} className="space-y-4">
                        <div>
                          <Label htmlFor="full_name">Full Name *</Label>
                          <Input
                            id="full_name"
                            value={participantForm.full_name}
                            onChange={(e) => setParticipantForm({ ...participantForm, full_name: e.target.value })}
                            placeholder="John Doe"
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="id_number">IC Number *</Label>
                          <Input
                            id="id_number"
                            value={participantForm.id_number}
                            onChange={(e) => setParticipantForm({ ...participantForm, id_number: e.target.value })}
                            placeholder="990101-01-1234"
                            required
                          />
                          <p className="text-xs text-gray-500 mt-1">This will be used as login username</p>
                        </div>
                        <div>
                          <Label htmlFor="company_id">Company *</Label>
                          <Select
                            value={participantForm.company_id}
                            onValueChange={(value) => setParticipantForm({ ...participantForm, company_id: value })}
                          >
                            <SelectTrigger>
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
                        <div className="bg-blue-50 p-3 rounded-lg">
                          <p className="text-sm font-medium text-blue-900">Default Login Credentials:</p>
                          <p className="text-sm text-blue-700 mt-1">
                            Username: <span className="font-mono">{participantForm.id_number || "[IC Number]"}</span>
                          </p>
                          <p className="text-sm text-blue-700">
                            Password: <span className="font-mono">mddrc1</span>
                          </p>
                        </div>
                        <Button type="submit" className="w-full">Add Participant</Button>
                      </form>
                    </DialogContent>
                  </Dialog>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {!selectedSession ? (
                <div className="text-center py-12">
                  <Users className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                  <p className="text-gray-500">Select a session to manage participants</p>
                </div>
              ) : participants.length === 0 ? (
                <div className="text-center py-12">
                  <Users className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                  <p className="text-gray-500">No participants added yet</p>
                  <Button className="mt-4" onClick={() => setAddDialogOpen(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Add First Participant
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  {participants.map((participant, idx) => {
                    // Handle nested structure: {user: {...}, access: {...}}
                    const user = participant.user || participant;
                    return (
                      <div
                        key={user.id || idx}
                        className="p-4 bg-gradient-to-r from-green-50 to-teal-50 rounded-lg border border-green-200"
                      >
                        <div className="flex items-center gap-3">
                          <span className="font-semibold text-gray-700 bg-white px-3 py-1 rounded">
                            {idx + 1}
                          </span>
                          <div className="flex-1">
                            <p className="font-medium text-gray-900">{user.full_name}</p>
                            <p className="text-sm text-gray-600">IC: {user.id_number}</p>
                            <p className="text-xs text-gray-500">Login: {user.id_number} / mddrc1</p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
            </div>
          </TabsContent>

          {/* Session Management Tab - Release Pre-test, Post-test, Feedback */}
          <TabsContent value="session-mgmt">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5 text-blue-600" />
                  Session Management
                </CardTitle>
                <CardDescription>
                  Control participant access to pre-test, post-test, and feedback forms.
                  Use this when coordinator is unavailable.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!selectedSession ? (
                  <div className="text-center py-8">
                    <p className="text-gray-500 mb-4">Select a session from the list below to manage access</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
                      {sessions.map(session => (
                        <Card 
                          key={session.id} 
                          className="cursor-pointer hover:border-blue-500 transition-colors"
                          onClick={() => handleSelectSession(session)}
                        >
                          <CardContent className="p-4">
                            <p className="font-semibold">{session.company_name}</p>
                            <p className="text-sm text-gray-600">{session.name}</p>
                            <p className="text-xs text-gray-500">{session.start_date} - {session.end_date}</p>
                            <Badge className="mt-2">{session.participant_ids?.length || 0} participants</Badge>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Selected Session Info */}
                    <div className="flex justify-between items-center p-4 bg-blue-50 rounded-lg">
                      <div>
                        <h3 className="font-semibold text-lg">{selectedSession.company_name}</h3>
                        <p className="text-gray-600">{selectedSession.name}</p>
                        <p className="text-sm text-gray-500">{selectedSession.start_date} - {selectedSession.end_date}</p>
                      </div>
                      <Button variant="outline" onClick={() => setSelectedSession(null)}>
                        Change Session
                      </Button>
                    </div>

                    {/* Toggle Controls - Same style as Coordinator */}
                    <div className="space-y-4">
                      {/* Pre-Test */}
                      <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                        <div>
                          <p className="font-semibold text-gray-900">Pre-Test</p>
                          <p className="text-sm text-gray-600">Initial assessment before training</p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={sessionAccess.some(a => a.can_access_pre_test)}
                            onChange={(e) => handleToggleAccess('pre_test', e.target.checked)}
                          />
                          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                        </label>
                      </div>

                      {/* Post-Test */}
                      <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
                        <div>
                          <p className="font-semibold text-gray-900">Post-Test</p>
                          <p className="text-sm text-gray-600">Final assessment after training</p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={sessionAccess.some(a => a.can_access_post_test)}
                            onChange={(e) => handleToggleAccess('post_test', e.target.checked)}
                          />
                          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
                        </label>
                      </div>

                      {/* Feedback */}
                      <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg">
                        <div>
                          <p className="font-semibold text-gray-900">Feedback Form</p>
                          <p className="text-sm text-gray-600">Training feedback and evaluation</p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={sessionAccess.some(a => a.can_access_feedback)}
                            onChange={(e) => handleToggleAccess('feedback', e.target.checked)}
                          />
                          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                        </label>
                      </div>

                      {/* Clock Out */}
                      <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                        <div>
                          <p className="font-semibold text-gray-900">Clock Out</p>
                          <p className="text-sm text-gray-600">Release clock out for participants</p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            className="sr-only peer"
                            checked={sessionAccess.some(a => a.can_clock_out)}
                            onChange={(e) => handleToggleAccess('clock_out', e.target.checked)}
                          />
                          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        </label>
                      </div>
                    </div>

                    {/* Current Status */}
                    <Card className="bg-gray-50">
                      <CardHeader>
                        <CardTitle className="text-base">Current Access Status</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
                          <div className="flex items-center justify-between">
                            <span>Pre-Test:</span>
                            <span className={`font-medium ${sessionAccess.some(a => a.can_access_pre_test) ? 'text-green-600' : 'text-red-600'}`}>
                              {sessionAccess.some(a => a.can_access_pre_test) ? 'Enabled' : 'Disabled'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Post-Test:</span>
                            <span className={`font-medium ${sessionAccess.some(a => a.can_access_post_test) ? 'text-green-600' : 'text-red-600'}`}>
                              {sessionAccess.some(a => a.can_access_post_test) ? 'Enabled' : 'Disabled'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Feedback:</span>
                            <span className={`font-medium ${sessionAccess.some(a => a.can_access_feedback) ? 'text-green-600' : 'text-red-600'}`}>
                              {sessionAccess.some(a => a.can_access_feedback) ? 'Enabled' : 'Disabled'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Clock Out:</span>
                            <span className={`font-medium ${sessionAccess.some(a => a.can_clock_out) ? 'text-green-600' : 'text-red-600'}`}>
                              {sessionAccess.some(a => a.can_clock_out) ? 'Enabled' : 'Disabled'}
                            </span>
                          </div>
                        </div>
                        <p className="text-xs text-gray-500 mt-3">
                          Note: Changes apply to all participants in this session immediately
                        </p>
                      </CardContent>
                    </Card>

                    {/* Participant List with Access Status */}
                    <div className="mt-6">
                      <h4 className="font-semibold mb-3">Participant Access Status ({sessionAccess.length})</h4>
                      <div className="space-y-2 max-h-[300px] overflow-y-auto">
                        {sessionAccess.map((access, idx) => (
                          <div key={access.participant_id || idx} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                            <span className="font-medium">{access.participant_name || `Participant ${idx + 1}`}</span>
                            <div className="flex gap-2">
                              <Badge className={access.can_access_pre_test ? 'bg-blue-500' : 'bg-gray-300'}>
                                Pre {access.can_access_pre_test ? '✓' : '✗'}
                              </Badge>
                              <Badge className={access.can_access_post_test ? 'bg-green-500' : 'bg-gray-300'}>
                                Post {access.can_access_post_test ? '✓' : '✗'}
                              </Badge>
                              <Badge className={access.can_access_feedback ? 'bg-purple-500' : 'bg-gray-300'}>
                                Feedback {access.can_access_feedback ? '✓' : '✗'}
                              </Badge>
                              <Badge className={access.can_clock_out ? 'bg-blue-500' : 'bg-gray-300'}>
                                Clock Out {access.can_clock_out ? '✓' : '✗'}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Programs Tab */}
          <TabsContent value="programs">
            <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <BookOpen className="w-5 h-5 mr-2" />
                Program Content Management
              </CardTitle>
              <CardDescription>
                Manage tests, checklists, and feedback forms for training programs
              </CardDescription>
            </CardHeader>
            <CardContent>
              {programs.length === 0 ? (
                <div className="text-center py-12">
                  <BookOpen className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                  <p className="text-gray-500">No programs available. Ask an admin to create training programs first.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {programs.map((program) => (
                    <div key={program.id}>
                      <Card className="border-2 border-blue-200">
                        <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <CardTitle className="text-lg">{program.name}</CardTitle>
                              {program.description && (
                                <CardDescription>{program.description}</CardDescription>
                              )}
                              <div className="flex gap-3 mt-2">
                                <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                  Pass Mark: {program.pass_percentage}%
                                </span>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setSelectedProgram(selectedProgram?.id === program.id ? null : program)}
                            >
                              <ClipboardList className="w-4 h-4 mr-2" />
                              {selectedProgram?.id === program.id ? 'Hide' : 'Manage Content'}
                            </Button>
                          </div>
                        </CardHeader>
                      </Card>

                      {/* Expandable Content Management Section */}
                      {selectedProgram?.id === program.id && (
                        <Card className="mt-2 border-l-4 border-blue-500">
                          <CardContent className="pt-6">
                            <Tabs defaultValue="tests" className="w-full">
                              <TabsList className="flex flex-wrap w-full grid-cols-3 mb-4 h-auto justify-start gap-2 bg-gray-100 p-2 rounded-lg sm:grid sm:grid-cols-3">
                                <TabsTrigger value="tests" className="flex-1 min-w-[100px] sm:min-w-0">
                                  <ClipboardList className="w-4 h-4 mr-2" />
                                  Tests
                                </TabsTrigger>
                                <TabsTrigger value="checklists" className="flex-1 min-w-[100px] sm:min-w-0">
                                  <ClipboardCheck className="w-4 h-4 mr-2" />
                                  Checklists
                                </TabsTrigger>
                                <TabsTrigger value="feedback" className="flex-1 min-w-[100px] sm:min-w-0">
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
                              <TabsContent value="feedback">
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
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
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
                    style={{ backgroundColor: primaryColor }}
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
                            <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
                              <div className="flex-1 w-full">
                                <div className="flex items-center gap-3 mb-2 flex-wrap">
                                  <div>
                                    <h3 className="font-semibold text-lg text-gray-900">{session.company_name || 'Unknown Company'}</h3>
                                    <p className="text-base text-gray-700">{session.program_name || 'Unknown Program'}</p>
                                  </div>
                                  <Badge variant="secondary" className="text-xs">
                                    {session.completion_status === 'completed' ? 'Completed' : 'Archived'}
                                  </Badge>
                                </div>
                                
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm text-gray-600 mb-3">
                                  <div className="flex items-center gap-1">
                                    <BookOpen className="w-4 h-4" />
                                    <span>{session.name}</span>
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
                              </div>
                              
                              <div className="flex gap-2 w-full sm:w-auto">
                                <Button
                                  onClick={() => handlePastSessionClick(session)}
                                  variant="outline"
                                  size="sm"
                                  className="flex items-center gap-1 flex-1 sm:flex-none"
                                >
                                  <Eye className="w-4 h-4" />
                                  {expandedPastSession?.id === session.id ? 'Hide' : 'View'}
                                </Button>
                                <Button
                                  onClick={() => navigate(`/results-summary/${session.id}`)}
                                  size="sm"
                                  className="flex items-center gap-1 flex-1 sm:flex-none"
                                  style={{ backgroundColor: primaryColor }}
                                >
                                  <BarChart3 className="w-4 h-4" />
                                  Results
                                </Button>
                              </div>
                            </div>
                            
                            {expandedPastSession?.id === session.id && (
                              <div className="mt-4 pt-4 border-t space-y-2">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                                  <div>
                                    <span className="font-medium text-gray-700">Location:</span>
                                    <p className="text-gray-600 mt-1">{session.location || 'Not specified'}</p>
                                  </div>
                                  <div>
                                    <span className="font-medium text-gray-700">Date Range:</span>
                                    <p className="text-gray-600 mt-1">
                                      {new Date(session.start_date).toLocaleDateString()} - {new Date(session.end_date).toLocaleDateString()}
                                    </p>
                                  </div>
                                  <div>
                                    <span className="font-medium text-gray-700">Venue:</span>
                                    <p className="text-gray-600 mt-1">{session.venue || 'Not specified'}</p>
                                  </div>
                                  <div>
                                    <span className="font-medium text-gray-700">Status:</span>
                                    <p className="text-gray-600 mt-1">
                                      {session.is_archived ? '✓ Archived' : 'Active'}
                                    </p>
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

          {/* My Earnings Tab - Combined Income & Payroll */}
          <TabsContent value="my-earnings">
            <div className="space-y-6">
              <MyEarnings 
                userId={user.id} 
                userRoles={[user.role, ...(user.additional_roles || [])]}
              />
              <DigitalSignatureManager user={user} />
            </div>
          </TabsContent>

        </Tabs>
      </div>
    </div>
  );
};

export default AssistantAdminDashboard;
