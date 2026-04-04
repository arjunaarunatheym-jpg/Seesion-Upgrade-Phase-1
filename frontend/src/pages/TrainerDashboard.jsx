import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useTheme } from "../context/ThemeContext";
import { LogOut, Calendar, ClipboardCheck, Users, FileText, ChevronDown, ChevronRight, MessageSquare, Search, Eye, Building2, BookOpen, DollarSign, Settings, Wallet, MapPin, Clock, Phone, AlertTriangle, StickyNote, Trash2, Send, User } from "lucide-react";
import MyEarnings from "../components/MyEarnings";
import MyPayroll from "../components/MyPayroll";
import { ChecklistsTab } from "../components/trainer/ChecklistsTab";
import { FeedbackTab } from "../components/trainer/FeedbackTab";
import { PastTrainingTab } from "../components/shared/PastTrainingTab";
import { DigitalSignatureManager } from "../components/shared/DigitalSignatureManager";

const TrainerDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { primaryColor, secondaryColor, companyName, logoUrl } = useTheme();
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [expandedSession, setExpandedSession] = useState(null);
  const [sessionParticipants, setSessionParticipants] = useState({});
  const [sessionAccess, setSessionAccess] = useState([]);

  const [feedbackTemplate, setFeedbackTemplate] = useState(null);
  const [selectedFeedbackSession, setSelectedFeedbackSession] = useState(null);
  const [feedback, setFeedback] = useState({});
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  // Past Training states
  const [pastTrainingSessions, setPastTrainingSessions] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [loadingPastTraining, setLoadingPastTraining] = useState(false);
  const [expandedPastSession, setExpandedPastSession] = useState(null);

  // Income states
  const [incomeData, setIncomeData] = useState(null);
  const [coordinatorIncomeData, setCoordinatorIncomeData] = useState(null);
  const [marketingIncomeData, setMarketingIncomeData] = useState(null);
  const [loadingIncome, setLoadingIncome] = useState(false);
  const [incomeFilter, setIncomeFilter] = useState({
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    showAll: false
  });
  
  // Check if user has additional roles
  const hasCoordinatorRole = user.additional_roles?.includes('coordinator') || user.role === 'coordinator';
  const hasMarketingRole = user.additional_roles?.includes('marketing') || user.role === 'marketing';

  // Session notes state
  const [sessionNotes, setSessionNotes] = useState([]);
  const [newNote, setNewNote] = useState("");
  const [submittingNote, setSubmittingNote] = useState(false);

  // Compute today's sessions
  const getTodaySessions = () => {
    const today = new Date().toISOString().split('T')[0];
    return sessions.filter(s => {
      const start = s.start_date?.split('T')[0];
      const end = s.end_date?.split('T')[0] || start;
      return start <= today && today <= end;
    });
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
      
      toast.success(`${accessType.replace('_', ' ')} ${enabled ? 'released' : 'disabled'} for all participants`);
      await loadSessionAccess(selectedSession.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to update ${accessType} access`);
    }
  };

  // Check if any access is enabled for a specific type
  const isAccessEnabled = (accessType) => {
    if (!sessionAccess || sessionAccess.length === 0) return false;
    const field = accessType === 'pre_test' ? 'can_access_pre_test' : 
                  accessType === 'post_test' ? 'can_access_post_test' : 
                  accessType === 'feedback' ? 'can_access_feedback' : 'can_access_checklist';
    return sessionAccess.some(a => a[field] === true);
  };

  // Load all income data
  const loadAllIncome = async () => {
    setLoadingIncome(true);
    try {
      // Load trainer income
      const trainerRes = await axiosInstance.get(`/finance/income/trainer/${user.id}`);
      setIncomeData(trainerRes.data);
      
      // Load coordinator income if applicable
      if (hasCoordinatorRole) {
        const coordRes = await axiosInstance.get(`/finance/income/coordinator/${user.id}`);
        setCoordinatorIncomeData(coordRes.data);
      }
      
      // Load marketing income if applicable
      if (hasMarketingRole) {
        const mktRes = await axiosInstance.get(`/finance/income/marketing/${user.id}`);
        setMarketingIncomeData(mktRes.data);
      }
    } catch (error) {
      console.error('Failed to load income:', error);
    } finally {
      setLoadingIncome(false);
    }
  };

  const loadSessionNotes = async (sessionId) => {
    try {
      const res = await axiosInstance.get(`/sessions/${sessionId}/notes`);
      setSessionNotes(res.data || []);
    } catch { setSessionNotes([]); }
  };

  const handleAddNote = async () => {
    if (!selectedSession || !newNote.trim()) return;
    setSubmittingNote(true);
    try {
      await axiosInstance.post(`/sessions/${selectedSession.id}/notes`, { content: newNote.trim() });
      setNewNote("");
      toast.success("Note added");
      loadSessionNotes(selectedSession.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add note");
    } finally { setSubmittingNote(false); }
  };

  const handleDeleteNote = async (noteId) => {
    if (!selectedSession) return;
    try {
      await axiosInstance.delete(`/sessions/${selectedSession.id}/notes/${noteId}`);
      toast.success("Note deleted");
      loadSessionNotes(selectedSession.id);
    } catch { toast.error("Failed to delete note"); }
  };

  useEffect(() => {
    loadSessions();
    
    // Check if returning from checklist submission
    const lastSessionId = sessionStorage.getItem('trainerLastSession');
    if (lastSessionId) {
      // Auto-expand and reload the session
      setTimeout(() => {
        setExpandedSession(lastSessionId);
        loadSessionParticipants(lastSessionId);
      }, 500);
    }
  }, []);

  // Load session access and notes when selectedSession changes
  useEffect(() => {
    if (selectedSession) {
      loadSessionAccess(selectedSession.id);
      loadSessionNotes(selectedSession.id);
    }
  }, [selectedSession]);

  const loadSessions = async () => {
    try {
      // Add timestamp to prevent caching
      const timestamp = new Date().getTime();
      const response = await axiosInstance.get(`/sessions?_t=${timestamp}`);
      // Filter sessions where user is assigned as trainer
      const mySessions = response.data.filter(session => 
        session.trainer_assignments && session.trainer_assignments.some(t => t.trainer_id === user.id)
      );
      
      // Load participants for all sessions first to check checklist status
      const sessionsWithParticipants = await Promise.all(
        mySessions.map(async (session) => {
          try {
            const participantsResponse = await axiosInstance.get(`/sessions/${session.id}/participants`);
            return { ...session, participantsData: participantsResponse.data };
          } catch (error) {
            return { ...session, participantsData: [] };
          }
        })
      );
      
      // Backend now handles date filtering for trainers
      // Sessions endpoint only returns current/future sessions for trainers
      // Sort sessions by start_date (upcoming first, then current)
      sessionsWithParticipants.sort((a, b) => new Date(a.start_date) - new Date(b.start_date));
      
      setSessions(sessionsWithParticipants);
      
      // Auto-select first session if available
      if (sessionsWithParticipants.length > 0) {
        setSelectedSession(sessionsWithParticipants[0]);
        // Load assigned participants for the first session
        loadSessionParticipants(sessionsWithParticipants[0].id);
      }
    } catch (error) {
      console.error("Failed to load sessions:", error);
      toast.error("Failed to load sessions: " + (error.response?.data?.detail || error.message));
    }
  };

  const loadSessionParticipants = async (sessionId) => {
    try {
      // Get assigned participants for this trainer (auto-distributed equally)
      const response = await axiosInstance.get(`/trainer-checklist/${sessionId}/assigned-participants`);
      const participants = response.data;
      
      // Load checklists for this session to check completion status
      try {
        const checklistsRes = await axiosInstance.get(`/checklists/session/${sessionId}`);
        const checklists = checklistsRes.data || [];
        
        // Attach checklist status to each participant
        const participantsWithStatus = participants.map(p => {
          const checklist = checklists.find(c => c.participant_id === p.id);
          return {
            ...p,
            checklist: checklist || null
          };
        });
        
        setSessionParticipants(prev => ({
          ...prev,
          [sessionId]: participantsWithStatus
        }));
      } catch (checklistError) {
        // If checklist loading fails, just set participants without status
        setSessionParticipants(prev => ({
          ...prev,
          [sessionId]: participants
        }));
      }
    } catch (error) {
      console.error("Failed to load assigned participants for session", sessionId, error);
      // Set empty array if no participants assigned
      setSessionParticipants(prev => ({
        ...prev,
        [sessionId]: []
      }));
    }
  };

  const getMyRole = (session) => {
    if (!session.trainer_assignments) return "Trainer";
    const assignment = session.trainer_assignments.find(t => t.trainer_id === user.id);
    return assignment ? (assignment.role === "chief" ? "Chief Trainer" : "Regular Trainer") : "Trainer";
  };

  // Check if user is chief trainer for any current session
  const isChiefTrainerForAnySessions = () => {
    return sessions.some(session => {
      if (!session.trainer_assignments) return false;
      const assignment = session.trainer_assignments.find(t => t.trainer_id === user.id);
      return assignment && assignment.role === "chief";
    });
  };

  // Get only sessions where user is chief trainer
  const getChiefTrainerSessions = () => {
    return sessions.filter(session => {
      if (!session.trainer_assignments) return false;
      const assignment = session.trainer_assignments.find(t => t.trainer_id === user.id);
      return assignment && assignment.role === "chief";
    });
  };


  const loadFeedbackTemplate = async () => {
    try {
      const response = await axiosInstance.get("/chief-trainer-feedback-template");
      setFeedbackTemplate(response.data);
    } catch (error) {
      console.error("Failed to load feedback template");
    }
  };

  const loadFeedback = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/chief-trainer-feedback/${sessionId}`);
      if (response.data && response.data.responses) {
        setFeedback(response.data.responses);
        setFeedbackSubmitted(true);
      } else {
        setFeedback({});
        setFeedbackSubmitted(false);
      }
    } catch (error) {
      setFeedback({});
      setFeedbackSubmitted(false);
    }
  };

  const handleSubmitFeedback = async () => {
    if (!selectedFeedbackSession) return;

    setSubmittingFeedback(true);
    try {
      await axiosInstance.post(`/chief-trainer-feedback/${selectedFeedbackSession.id}`, feedback);
      toast.success("Feedback submitted successfully!");
      setFeedbackSubmitted(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to submit feedback");
    } finally {
      setSubmittingFeedback(false);
    }
  };

  useEffect(() => {
    loadFeedbackTemplate();
  }, []);


  const isChiefTrainer = (session) => {
    if (!session.trainer_assignments) return false;
    const assignment = session.trainer_assignments.find(t => t.trainer_id === user.id);
    return assignment && assignment.role === "chief";
  };

  const handleViewResults = (sessionId) => {
    navigate(`/results-summary/${sessionId}`);
  };

  const loadPastTraining = async () => {
    try {
      setLoadingPastTraining(true);
      
      // Build query params for month/year filter
      const params = new URLSearchParams();
      if (selectedMonth) params.append('month', selectedMonth);
      if (selectedYear) params.append('year', selectedYear);
      
      // Use the past-training endpoint which handles trainer filtering on backend
      const response = await axiosInstance.get(`/sessions/past-training?${params.toString()}`);
      
      // Load participants for each session to check checklist completion
      const sessionsWithParticipants = await Promise.all(
        response.data.map(async (session) => {
          try {
            const participantsResponse = await axiosInstance.get(`/sessions/${session.id}/participants`);
            return { ...session, participantsData: participantsResponse.data };
          } catch (error) {
            return { ...session, participantsData: [] };
          }
        })
      );
      
      setPastTrainingSessions(sessionsWithParticipants);
    } catch (error) {
      toast.error("Failed to load past training sessions");
      setPastTrainingSessions([]);
    } finally {
      setLoadingPastTraining(false);
    }
  };

  const loadIncome = async () => {
    setLoadingIncome(true);
    try {
      const response = await axiosInstance.get(`/finance/income/trainer/${user.id}`);
      setIncomeData(response.data);
    } catch (error) {
      console.error('Failed to load income:', error);
      // Don't show error toast - income might not be set up yet
    } finally {
      setLoadingIncome(false);
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

  const toggleSessionExpand = (sessionId) => {
    if (expandedSession === sessionId) {
      setExpandedSession(null);
      sessionStorage.removeItem('trainerLastSession');
    } else {
      setExpandedSession(sessionId);
      loadSessionParticipants(sessionId);
      // Store for auto-reload after checklist
      sessionStorage.setItem('trainerLastSession', sessionId);
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
        <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-3 sm:py-4 flex justify-between items-center">
          <div className="flex items-center gap-2 sm:gap-4 flex-1 min-w-0">
            {logoUrl && (
              <button
                onClick={() => navigate('/calendar')}
                className="hover:opacity-80 transition-opacity cursor-pointer flex-shrink-0"
              >
                <img 
                  src={logoUrl} 
                  alt={companyName}
                  className="h-8 sm:h-10 w-auto object-contain"
                />
              </button>
            )}
            <div className="min-w-0">
              <h1 className="text-lg sm:text-2xl font-bold text-gray-900 truncate">Trainer Portal</h1>
              <p className="text-xs sm:text-sm text-gray-600 truncate">Welcome, {user.full_name}</p>
            </div>
          </div>
          <Button
            data-testid="trainer-logout-button"
            onClick={onLogout}
            variant="outline"
            className="flex items-center gap-1 sm:gap-2 text-sm sm:text-base flex-shrink-0"
          >
            <LogOut className="w-3 h-3 sm:w-4 sm:h-4" />
            <span className="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-4 sm:py-6 lg:py-8">
        {/* Today's Session Summary Card */}
        {(() => {
          const todaySessions = getTodaySessions();
          if (todaySessions.length === 0) return null;
          return (
            <Card className="mb-6 border-2 border-amber-300 bg-gradient-to-r from-amber-50 to-orange-50" data-testid="todays-session-card">
              <CardContent className="pt-5 pb-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-full bg-amber-500 flex items-center justify-center">
                    <Calendar className="w-4 h-4 text-white" />
                  </div>
                  <h2 className="font-bold text-lg text-amber-900">Today's Session{todaySessions.length > 1 ? 's' : ''}</h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {todaySessions.map(s => (
                    <div key={s.id} className="p-3 bg-white rounded-lg border border-amber-200 flex flex-col gap-1">
                      <p className="font-semibold text-gray-900">{s.company_name || "Unknown Company"}</p>
                      <p className="text-sm text-gray-700">{s.program_name || "Unknown Program"}</p>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600 mt-1">
                        <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{s.location || "TBD"}</span>
                        <span className="flex items-center gap-1"><Users className="w-3 h-3" />{sessionParticipants[s.id]?.length || s.participant_ids?.length || 0} pax</span>
                        <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{s.start_date?.split('T')[0]} to {s.end_date?.split('T')[0] || s.start_date?.split('T')[0]}</span>
                      </div>
                      <Badge className="self-start mt-1 text-xs" variant="outline">{getMyRole(s)}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })()}
        {/* Session Selector */}
        {sessions.length > 0 && (
          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                <Label className="text-sm font-medium whitespace-nowrap">Select Session:</Label>
                <Select
                  value={selectedSession?.id || ""}
                  onValueChange={(sessionId) => {
                    const session = sessions.find(s => s.id === sessionId);
                    setSelectedSession(session);
                    if (session) {
                      loadSessionParticipants(session.id);
                    }
                  }}
                >
                  <SelectTrigger className="w-full sm:flex-1">
                    <SelectValue placeholder="Choose a session..." />
                  </SelectTrigger>
                  <SelectContent>
                    {sessions.map((session) => (
                      <SelectItem key={session.id} value={session.id}>
                        {session.company_name || "Unknown Company"} - {session.program_name || "Unknown Program"} ({new Date(session.start_date).toLocaleDateString()})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {selectedSession && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-semibold text-lg">{selectedSession.company_name || "Unknown Company"}</h3>
                  <p className="text-base text-gray-700">{selectedSession.program_name || "Unknown Program"}</p>
                  <div className="mt-2 text-sm text-gray-600 space-y-1">
                    <p>Location: {selectedSession.location}</p>
                    <p>Duration: {selectedSession.start_date} to {selectedSession.end_date}</p>
                    <p>Participants: {sessionParticipants[selectedSession.id]?.length || 0}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <Tabs defaultValue="sessions" className="w-full">
          <TabsList className="flex flex-wrap w-full mb-8 h-auto justify-start gap-2 bg-gray-100 p-2 rounded-lg md:grid md:grid-cols-5">
            <TabsTrigger value="sessions" data-testid="sessions-tab" className="flex-1 min-w-[140px] md:min-w-0">
              <Calendar className="w-4 h-4 mr-2" />
              <span className="text-sm">My Sessions</span>
            </TabsTrigger>
            <TabsTrigger value="session-mgmt" data-testid="session-mgmt-tab" className="flex-1 min-w-[140px] md:min-w-0 bg-gradient-to-r from-blue-500 to-indigo-500 text-white">
              <Settings className="w-4 h-4 mr-2" />
              <span className="text-sm">Session Mgmt</span>
            </TabsTrigger>
            <TabsTrigger value="checklists" data-testid="checklists-tab" className="flex-1 min-w-[140px] md:min-w-0">
              <ClipboardCheck className="w-4 h-4 mr-2" />
              <span className="text-sm">Checklists</span>
            </TabsTrigger>
            <TabsTrigger value="past-training" data-testid="past-training-tab" className="flex-1 min-w-[140px] md:min-w-0">
              <FileText className="w-4 h-4 mr-2" />
              <span className="text-sm">Past Training</span>
            </TabsTrigger>
            <TabsTrigger value="session-notes" data-testid="session-notes-tab" className="flex-1 min-w-[140px] md:min-w-0">
              <StickyNote className="w-4 h-4 mr-2" />
              <span className="text-sm">Notes</span>
            </TabsTrigger>
            <TabsTrigger value="my-earnings" data-testid="my-earnings-tab" className="flex-shrink-0 bg-gradient-to-r from-emerald-500 to-teal-500 text-white">
              <Wallet className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline text-sm">My Earnings</span>
            </TabsTrigger>
            <TabsTrigger value="my-payroll" data-testid="my-payroll-tab" className="flex-shrink-0 bg-gradient-to-r from-blue-500 to-cyan-500 text-white">
              <DollarSign className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline text-sm">My Payroll</span>
            </TabsTrigger>
            {isChiefTrainerForAnySessions() && (
              <TabsTrigger value="feedback" data-testid="feedback-tab" className="flex-1 min-w-[140px] md:min-w-0">
                <MessageSquare className="w-4 h-4 mr-2" />
                <span className="text-sm">Chief Trainer Feedback</span>
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="sessions">
            <Card>
              <CardHeader>
                <CardTitle>Assigned Training Sessions</CardTitle>
                <CardDescription>Sessions you are assigned to as trainer</CardDescription>
              </CardHeader>
              <CardContent>
                {sessions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center" data-testid="empty-state">
                    <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                      <Calendar className="w-8 h-8 text-slate-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-700 mb-1">No sessions assigned yet</h3>
                    <p className="text-sm text-slate-500 max-w-sm">Sessions will appear here once an admin assigns you as a trainer.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {sessions.map((session) => {
                      const isExpanded = expandedSession === session.id;
                      const participants = sessionParticipants[session.id] || [];
                      const isChief = isChiefTrainer(session);

                      return (
                        <Card key={session.id} className="border-2">
                          <CardHeader className="bg-gradient-to-r from-orange-50 to-amber-50">
                            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
                              <div className="flex-1">
                                <div className="flex items-center gap-3">
                                  <button
                                    onClick={() => toggleSessionExpand(session.id)}
                                    className="p-1 hover:bg-gray-200 rounded min-h-[44px] min-w-[44px] flex items-center justify-center"
                                  >
                                    {isExpanded ? (
                                      <ChevronDown className="w-5 h-5 text-gray-600" />
                                    ) : (
                                      <ChevronRight className="w-5 h-5 text-gray-600" />
                                    )}
                                  </button>
                                  <div>
                                    <CardTitle className="text-lg sm:text-xl">{session.company_name || "Unknown Company"}</CardTitle>
                                    <p className="text-base text-gray-700 mt-1">{session.program_name || "Unknown Program"}</p>
                                    <div className="mt-2 text-sm text-gray-600 space-y-1">
                                      <p>Session: {session.name}</p>
                                      <p>Location: {session.location}</p>
                                      <p>Duration: {session.start_date} to {session.end_date}</p>
                                    </div>
                                  </div>
                                </div>
                              </div>
                              <div className="flex flex-row sm:flex-col gap-2 sm:items-end items-start">
                                <div className="flex items-center gap-2 text-sm text-gray-600">
                                  <Users className="w-4 h-4" />
                                  <span>{participants.length} Participants</span>
                                </div>
                                <Button
                                  onClick={() => handleViewResults(session.id)}
                                  size="sm"
                                  variant="outline"
                                  data-testid={`view-results-${session.id}`}
                                  className="whitespace-nowrap"
                                >
                                  <FileText className="w-4 h-4 mr-2" />
                                  View Results
                                </Button>
                              </div>
                            </div>
                          </CardHeader>
                          
                          {isExpanded && participants.length > 0 && (
                            <CardContent className="pt-4">
                              <h4 className="font-semibold text-gray-900 mb-3">Participants</h4>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {participants.map((participant) => (
                                  <div
                                    key={participant.id}
                                    className="p-3 bg-gray-50 rounded-lg border flex items-start gap-3"
                                  >
                                    {participant.profile_photo ? (
                                      <img src={participant.profile_photo} alt="" className="w-10 h-10 rounded-full object-cover border flex-shrink-0" />
                                    ) : (
                                      <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                                        <User className="w-5 h-5 text-gray-400" />
                                      </div>
                                    )}
                                    <div className="flex-1 min-w-0">
                                      <p className="font-medium text-gray-900 truncate">{participant.full_name}</p>
                                      <p className="text-sm text-gray-600 truncate">{participant.email}</p>
                                      {participant.id_number && (
                                        <p className="text-xs text-gray-500 mt-0.5">IC: {participant.id_number}</p>
                                      )}
                                      {(participant.emergency_contact_name || participant.emergency_contact_phone) && (
                                        <div className="mt-1.5 pt-1.5 border-t border-gray-200 flex items-center gap-1 text-xs text-orange-700">
                                          <Phone className="w-3 h-3" />
                                          <span>Emergency: {participant.emergency_contact_name}{participant.emergency_contact_phone ? ` (${participant.emergency_contact_phone})` : ''}</span>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </CardContent>
                          )}
                        </Card>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="session-mgmt">
            <Card>
              <CardHeader>
                <CardTitle>Session Management</CardTitle>
                <CardDescription>Control when participants can access tests and feedback</CardDescription>
              </CardHeader>
              <CardContent>
                {!selectedSession ? (
                  <div className="text-center py-12">
                    <Settings className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <p className="text-gray-500">Please select a session above to manage access</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <h3 className="font-semibold text-blue-900 mb-2">
                        Managing: {selectedSession.company_name} - {selectedSession.program_name}
                      </h3>
                      <p className="text-sm text-blue-700">
                        Control when participants can access different components of the training
                      </p>
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
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="checklists">
            <ChecklistsTab
              selectedSession={selectedSession}
              sessionParticipants={sessionParticipants}
              isChiefTrainer={isChiefTrainer}
              getMyRole={getMyRole}
              onNavigateChecklist={(sessionId, participantId) => navigate(`/trainer-checklist/${sessionId}/${participantId}`)}
            />
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
                      <p className="text-sm text-gray-500 mt-2">
                        Note: As a trainer, you can view sessions that are past their end date.
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
                                  <div>
                                    <h3 className="font-semibold text-lg text-gray-900">{session.company_name || 'Unknown Company'}</h3>
                                    <p className="text-base text-gray-700">{session.program_name || 'Unknown Program'}</p>
                                  </div>
                                  <Badge variant="secondary" className="text-xs">
                                    Past Training
                                  </Badge>
                                </div>
                                
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm text-gray-600 mb-3">
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
                                      <p><span className="text-gray-600">Start:</span> {new Date(session.start_date).toLocaleString()}</p>
                                      <p><span className="text-gray-600">End:</span> {new Date(session.end_date).toLocaleString()}</p>
                                    </div>
                                  </div>
                                  <div>
                                    <h4 className="font-medium text-gray-900 mb-2">Your Role</h4>
                                    <div className="space-y-1">
                                      <p className="text-sm">
                                        <Badge variant="outline">
                                          {getMyRole(session) || 'Trainer'}
                                        </Badge>
                                      </p>
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

          {/* Session Notes Tab */}
          <TabsContent value="session-notes">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <StickyNote className="w-5 h-5" />
                  Session Notes
                </CardTitle>
                <CardDescription>
                  {selectedSession ? `Notes for ${selectedSession.company_name} - ${selectedSession.program_name}` : 'Select a session above to view/add notes'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {!selectedSession ? (
                  <div className="text-center py-12">
                    <StickyNote className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <p className="text-gray-500">Select a session above to manage notes</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Add note */}
                    <div className="flex gap-2">
                      <Input
                        value={newNote}
                        onChange={(e) => setNewNote(e.target.value)}
                        placeholder="Add a note about this session..."
                        className="flex-1"
                        data-testid="session-note-input"
                        onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleAddNote()}
                      />
                      <Button onClick={handleAddNote} disabled={submittingNote || !newNote.trim()} size="sm" data-testid="add-note-btn">
                        <Send className="w-4 h-4" />
                      </Button>
                    </div>
                    {/* Notes list */}
                    {sessionNotes.length === 0 ? (
                      <p className="text-sm text-gray-500 text-center py-6">No notes yet for this session.</p>
                    ) : (
                      <div className="space-y-2">
                        {sessionNotes.map(note => (
                          <div key={note.id} className="p-3 bg-gray-50 rounded-lg border flex justify-between items-start gap-2">
                            <div>
                              <p className="text-sm text-gray-900">{note.content}</p>
                              <p className="text-xs text-gray-500 mt-1">{note.trainer_name} &middot; {new Date(note.created_at).toLocaleString()}</p>
                            </div>
                            {note.trainer_id === user.id && (
                              <button onClick={() => handleDeleteNote(note.id)} className="text-gray-400 hover:text-red-500 flex-shrink-0" data-testid={`delete-note-${note.id}`}>
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Chief Trainer Feedback Tab - Only shown for chief trainers */}
          {isChiefTrainerForAnySessions() && (
          <TabsContent value="feedback">
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Select Session for Feedback</CardTitle>
                <CardDescription>Choose a session to provide chief trainer feedback</CardDescription>
              </CardHeader>
              <CardContent>
                <select
                  value={selectedFeedbackSession?.id || ""}
                  onChange={(e) => {
                    const session = getChiefTrainerSessions().find(s => s.id === e.target.value);
                    if (session) {
                      setSelectedFeedbackSession(session);
                      loadFeedback(session.id);
                    }
                  }}
                  className="w-full p-2 border rounded-md"
                >
                  <option value="">Select a session...</option>
                  {getChiefTrainerSessions().map((session) => (
                    <option key={session.id} value={session.id}>
                      {session.company_name || "Unknown Company"} - {session.program_name || "Unknown Program"} ({session.start_date ? new Date(session.start_date).toLocaleDateString() : 'Date TBD'})
                    </option>
                  ))}
                </select>
              </CardContent>
            </Card>

            {selectedFeedbackSession && feedbackTemplate && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5" />
                    Chief Trainer Feedback
                  </CardTitle>
                  <CardDescription>
                    Session: {selectedFeedbackSession.name} | Role: {getMyRole(selectedFeedbackSession)}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {feedbackTemplate.questions?.map((question) => (
                      <div key={question.id} className="space-y-2">
                        <label className="text-sm font-medium text-gray-700">
                          {question.question}
                          {question.type === 'rating' && (
                            <span className="text-gray-500 ml-1">(Rate 1-{question.scale})</span>
                          )}
                        </label>
                        {question.type === 'rating' ? (
                          <div className="flex gap-2">
                            {[...Array(question.scale)].map((_, i) => (
                              <button
                                key={i}
                                onClick={() => setFeedback({...feedback, [question.id]: i + 1})}
                                className={`w-10 h-10 rounded-full font-bold ${
                                  feedback[question.id] === i + 1
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                                }`}
                                disabled={feedbackSubmitted}
                              >
                                {i + 1}
                              </button>
                            ))}
                          </div>
                        ) : (
                          <textarea
                            value={feedback[question.id] || ''}
                            onChange={(e) => setFeedback({...feedback, [question.id]: e.target.value})}
                            className="w-full p-3 border rounded-md"
                            rows={4}
                            disabled={feedbackSubmitted}
                            placeholder="Enter your response..."
                          />
                        )}
                      </div>
                    ))}
                    
                    <div className="flex items-center gap-2 mt-6 pt-6 border-t">
                      {feedbackSubmitted ? (
                        <div className="flex items-center gap-2">
                          <span className="px-4 py-2 bg-green-100 text-green-800 rounded-lg text-sm font-medium">
                            ✓ Feedback Submitted
                          </span>
                          <Button
                            onClick={() => setFeedbackSubmitted(false)}
                            variant="outline"
                            size="sm"
                          >
                            Edit Feedback
                          </Button>
                        </div>
                      ) : (
                        <Button
                          onClick={handleSubmitFeedback}
                          disabled={submittingFeedback}
                          className="bg-blue-600 hover:bg-blue-700"
                        >
                          {submittingFeedback ? "Submitting..." : "Submit Feedback"}
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {!selectedFeedbackSession && (
              <Card>
                <CardContent className="py-12 text-center">
                  <MessageSquare className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                  <p className="text-gray-600">Select a session above to provide feedback</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>
          )}

          {/* My Earnings Tab - Combined Income & Payroll */}
          <TabsContent value="my-earnings">
            <MyEarnings 
              userId={user.id} 
              userRoles={[user.role, ...(user.additional_roles || [])]}
            />
          </TabsContent>

          <TabsContent value="my-payroll">
            <div className="space-y-6">
              <MyPayroll />
              <DigitalSignatureManager user={user} />
            </div>
          </TabsContent>

        </Tabs>
      </main>
    </div>
  );
};

export default TrainerDashboard;
