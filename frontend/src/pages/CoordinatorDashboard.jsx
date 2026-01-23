import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { LogOut, Calendar, Users, FileText, BarChart3, Camera, Upload, Sparkles, Save, Send, Edit, Trash2, Clock, MessageSquare, Download, CheckCircle, Search, Eye, Building2, BookOpen, Plus, DollarSign, Wallet } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import MyEarnings from "../components/MyEarnings";
import { ManagementTab } from "../components/coordinator/ManagementTab";

const CoordinatorDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { primaryColor, companyName, logoUrl } = useTheme();
  
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
  
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [trainers, setTrainers] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [testResults, setTestResults] = useState([]);
  const [courseFeedback, setCourseFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Bulk upload states
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  
  // Training Report states
  const [trainingReport, setTrainingReport] = useState({
    group_photo: "",
    theory_photo_1: "",
    theory_photo_2: "",
    practical_photo_1: "",
    practical_photo_2: "",
    practical_photo_3: "",
    additional_notes: "",
    status: "draft"
  });
  const [aiGeneratedReport, setAiGeneratedReport] = useState("");
  const [generatingReport, setGeneratingReport] = useState(false);
  
  // Professional DOCX Report states
  const [professionalReportStatus, setProfessionalReportStatus] = useState({
    docx_generated: false,
    edited_uploaded: false,
    pdf_submitted: false,
    docx_filename: null,
    edited_docx_filename: null,
    pdf_filename: null
  });
  const [generatingDOCX, setGeneratingDOCX] = useState(false);
  const [uploadingEdited, setUploadingEdited] = useState(false);
  const [submittingFinal, setSubmittingFinal] = useState(false);
  const [markingCompleted, setMarkingCompleted] = useState(false);
  const [editSessionDialogOpen, setEditSessionDialogOpen] = useState(false);
  const [editingSession, setEditingSession] = useState(null);
  const [checklistIssues, setChecklistIssues] = useState([]);
  const [allChecklists, setAllChecklists] = useState([]);
  const [sessionAccess, setSessionAccess] = useState([]);
  const [sessionStats, setSessionStats] = useState({});
  const [addParticipantDialogOpen, setAddParticipantDialogOpen] = useState(false);
  const [newParticipant, setNewParticipant] = useState({
    email: "",
    password: "",
    full_name: "",
    id_number: "",
    phone_number: ""
  });

  // Certificate upload states
  const [uploadingCertificates, setUploadingCertificates] = useState({});
  const [certificateStatuses, setCertificateStatuses] = useState({});

  // Coordinator Feedback states
  const [coordinatorFeedbackTemplate, setCoordinatorFeedbackTemplate] = useState(null);
  const [coordinatorFeedback, setCoordinatorFeedback] = useState({});
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
  const [marketingIncomeData, setMarketingIncomeData] = useState(null);
  const [loadingIncome, setLoadingIncome] = useState(false);
  const [incomeFilter, setIncomeFilter] = useState({
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    showAll: false
  });
  
  // Check if user has marketing role
  const hasMarketingRole = user.additional_roles?.includes('marketing') || user.role === 'marketing';
  
  // Completion checklist state
  const [completionChecklist, setCompletionChecklist] = useState(null);
  
  // Attendance status state
  const [attendanceStatus, setAttendanceStatus] = useState({});  // { participant_id: "present" | "absent" }
  const [updatingAttendance, setUpdatingAttendance] = useState({});  // { participant_id: boolean }
  
  // Vehicle issues expanded state
  const [expandedVehicleIssue, setExpandedVehicleIssue] = useState(null);  // participant name
  const [expandedChecklist, setExpandedChecklist] = useState(null);  // participant name for all checklists

  useEffect(() => {
    loadSessions();
    loadCoordinatorFeedbackTemplate();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const response = await axiosInstance.get('/sessions');
      // Filter sessions where user is coordinator
      const coordinatorSessions = response.data.filter(s => s.coordinator_id === user.id);
      setSessions(coordinatorSessions);
      
      // Load stats for all sessions
      await loadAllSessionStats(coordinatorSessions);
      
      if (coordinatorSessions.length > 0) {
        selectSession(coordinatorSessions[0]);
      }
      setLoading(false);
    } catch (error) {
      toast.error("Failed to load sessions");
      setLoading(false);
    }
  };

  const loadAllSessionStats = async (sessionsList) => {
    const stats = {};
    
    for (const session of sessionsList) {
      try {
        const [testResultsRes, feedbackRes] = await Promise.all([
          axiosInstance.get(`/tests/results/session/${session.id}`).catch(() => ({ data: [] })),
          axiosInstance.get(`/feedback/session/${session.id}`).catch(() => ({ data: [] }))
        ]);
        
        const testResults = testResultsRes.data || [];
        const feedbackResults = feedbackRes.data || [];
        
        const preTestResults = testResults.filter(r => r.test_type === 'pre' || r.test_type === 'pre_test');
        const postTestResults = testResults.filter(r => r.test_type === 'post' || r.test_type === 'post_test');
        
        stats[session.id] = {
          participantCount: session.participant_ids?.length || 0,
          preTestCompleted: preTestResults.length,
          postTestCompleted: postTestResults.length,
          feedbackCompleted: feedbackResults.length
        };
      } catch (error) {
        console.error(`Failed to load stats for session ${session.id}`);
        stats[session.id] = {
          participantCount: session.participant_ids?.length || 0,
          preTestCompleted: 0,
          postTestCompleted: 0,
          feedbackCompleted: 0
        };
      }
    }
    
    setSessionStats(stats);
  };

  const selectSession = async (session) => {
    try {
      setSelectedSession(session);
      // Wait for data to load before proceeding
      await Promise.all([
        loadSessionData(session),
        loadTrainingReport(session.id)
      ]);
    } catch (error) {
      console.error("Error selecting session:", error);
      toast.error("Failed to load session data");
    }
  };


  // Load coordinator feedback template
  const loadCoordinatorFeedbackTemplate = async () => {
    try {
      const response = await axiosInstance.get("/coordinator-feedback-template");
      setCoordinatorFeedbackTemplate(response.data);
    } catch (error) {
      console.error("Failed to load feedback template:", error);
    }
  };

  // Load all income data (coordinator + marketing if applicable)
  const loadAllIncome = async () => {
    setLoadingIncome(true);
    try {
      // Load coordinator income
      const coordResponse = await axiosInstance.get(`/finance/income/coordinator/${user.id}`);
      setIncomeData(coordResponse.data);
      
      // If user has marketing role, also load marketing income
      if (hasMarketingRole) {
        const mktResponse = await axiosInstance.get(`/finance/income/marketing/${user.id}`);
        setMarketingIncomeData(mktResponse.data);
      }
    } catch (error) {
      console.error('Failed to load income:', error);
    } finally {
      setLoadingIncome(false);
    }
  };

  // Load existing coordinator feedback for session
  const loadCoordinatorFeedback = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/coordinator-feedback/${sessionId}`);
      if (response.data && response.data.responses) {
        setCoordinatorFeedback(response.data.responses);
        setFeedbackSubmitted(true);
      }
    } catch (error) {
      console.log("No existing feedback found");
      setFeedbackSubmitted(false);
    }
  };

  // Submit coordinator feedback
  const handleSubmitCoordinatorFeedback = async () => {
    if (!selectedSession) {
      toast.error("No session selected");
      return;
    }

    setSubmittingFeedback(true);
    try {
      await axiosInstance.post(`/coordinator-feedback/${selectedSession.id}`, coordinatorFeedback);
      toast.success("Feedback submitted successfully!");
      setFeedbackSubmitted(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to submit feedback");
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const loadCompletionChecklist = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/sessions/${sessionId}/completion-checklist`);
      setCompletionChecklist(response.data);
    } catch (error) {
      console.error("Failed to load completion checklist:", error);
      setCompletionChecklist(null);
    }
  };

  const loadAttendanceStatus = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/sessions/${sessionId}/participants/attendance`);
      setAttendanceStatus(response.data);
    } catch (error) {
      console.error("Failed to load attendance status:", error);
      setAttendanceStatus({});
    }
  };

  const handleMarkAttendance = async (participantId, status) => {
    if (!selectedSession) return;
    
    try {
      setUpdatingAttendance(prev => ({ ...prev, [participantId]: true }));
      
      await axiosInstance.post(
        `/sessions/${selectedSession.id}/participants/${participantId}/attendance`,
        null,
        { params: { status } }
      );
      
      setAttendanceStatus(prev => ({ ...prev, [participantId]: status }));
      toast.success(`Participant marked as ${status}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update attendance");
    } finally {
      setUpdatingAttendance(prev => ({ ...prev, [participantId]: false }));
    }
  };


  const loadSessionData = async (session) => {
    try {
      // Accept session object directly instead of looking it up
      if (!session) {
        console.error("Session not provided");
        return;
      }
      
      const sessionId = session.id;
      
      console.log("Loading data for session:", sessionId);
      console.log("Session participant_ids:", session.participant_ids);
      
      const [usersRes, attendanceRes, testResultsRes, feedbackRes, certificatesRes] = await Promise.all([
        axiosInstance.get(`/users`).catch(err => {
          console.error("Failed to load users:", err);
          return { data: [] };
        }),
        axiosInstance.get(`/attendance/session/${sessionId}`).catch(err => {
          console.error("Failed to load attendance:", err);
          return { data: [] };
        }),
        axiosInstance.get(`/tests/results/session/${sessionId}`).catch(err => {
          console.error("Failed to load test results:", err);
          return { data: [] };
        }),
        axiosInstance.get(`/feedback/session/${sessionId}`).catch(err => {
          console.error("Failed to load feedback:", err);
          return { data: [] };
        }),
        axiosInstance.get(`/certificates/session/${sessionId}`).catch(err => {
          console.error("Failed to load certificates:", err);
          return { data: [] };
        })
      ]);
      
      console.log("Loaded users:", usersRes.data.length);
      console.log("Loaded attendance:", attendanceRes.data.length);
      console.log("Loaded test results:", testResultsRes.data.length);
      console.log("Loaded certificates:", certificatesRes.data.length);
      
      // Filter participants for THIS specific session
      const sessionParticipants = usersRes.data.filter(u => 
        session?.participant_ids && session.participant_ids.includes(u.id)
      );
      
      console.log("Filtered session participants:", sessionParticipants.length);
      
      setParticipants(sessionParticipants);
      setAttendance(attendanceRes.data || []);
      setTestResults(testResultsRes.data || []);
      setCourseFeedback(feedbackRes.data || []);
      
      // Populate certificate statuses
      const certStatuses = {};
      (certificatesRes.data || []).forEach(cert => {
        certStatuses[cert.participant_id] = {
          uploaded: true,
          url: cert.file_path,
          certificate_id: cert.id
        };
      });
      setCertificateStatuses(certStatuses);
      
      // Load session access controls
      await loadSessionAccess(sessionId);
      
      // Load checklist issues
      if (sessionParticipants.length > 0) {
        await loadChecklistIssues(sessionId, sessionParticipants);
      }
      
      // Load coordinator feedback, completion checklist, and attendance status
      await loadCoordinatorFeedback(sessionId);
      await loadCompletionChecklist(sessionId);
      await loadAttendanceStatus(sessionId);
    } catch (error) {
      console.error("Failed to load session data", error);
      toast.error("Failed to load session data: " + error.message);
    }
  };

  const loadSessionAccess = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/participant-access/session/${sessionId}`);
      setSessionAccess(response.data);
    } catch (error) {
      console.error("Failed to load session access", error);
      setSessionAccess([]);
    }
  };

  const handleToggleAccess = async (accessType, enabled) => {
    if (!selectedSession) return;
    
    try {
      await axiosInstance.post(`/participant-access/session/${selectedSession.id}/toggle`, {
        access_type: accessType,
        enabled: enabled
      });
      
      toast.success(`${accessType} ${enabled ? 'enabled' : 'disabled'} for all participants`);
      await loadSessionAccess(selectedSession.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to update ${accessType} access`);
    }
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
      loadSessions();
      
      // Reset file input
      e.target.value = '';
    } catch (error) {
      const errorMessage = error.response?.data?.detail || "Failed to upload file";
      toast.error(errorMessage);
    } finally {
      setUploading(false);
    }
  };


  const loadChecklistIssues = async (sessionId, participantsList) => {
    try {
      const issues = [];
      const completedChecklists = [];
      
      // Get checklists for all participants in this session
      for (const participant of participantsList) {
        try {
          const response = await axiosInstance.get(`/vehicle-checklists/${sessionId}/${participant.id}`);
          const checklist = response.data;
          
          // Support both old and new checklist formats
          const checklistItems = checklist?.items || checklist?.checklist_items || [];
          
          if (checklistItems.length > 0) {
            // Store all completed checklists
            completedChecklists.push({
              participant_name: participant.full_name,
              participant_id: participant.id,
              checklist: checklist,
              items: checklistItems
            });
            
            // Also filter for issues
            const needsRepair = checklistItems.filter(item => 
              (item.status || '').toLowerCase() === 'needs_repair'
            );
            
            if (needsRepair.length > 0) {
              issues.push({
                participant_name: participant.full_name,
                participant_id: participant.id,
                items: needsRepair
              });
            }
          }
        } catch (err) {
          // Checklist doesn't exist for this participant, skip
          console.log(`No checklist found for participant ${participant.full_name}:`, err.response?.status);
          continue;
        }
      }
      
      console.log(`Found ${completedChecklists.length} completed checklists, ${issues.length} with issues`);
      setAllChecklists(completedChecklists);
      setChecklistIssues(issues);
    } catch (error) {
      console.error("Failed to load checklist issues", error);
    }
  };

  const loadTrainingReport = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/training-reports/${sessionId}`);
      if (response.data && response.data.id) {
        setTrainingReport(response.data);
        setAiGeneratedReport(response.data.additional_notes || "");
      }
    } catch (error) {
      // Report doesn't exist yet, that's ok
      console.log("No existing report");
    }
  };

  const handlePhotoUpload = async (e, fieldName) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Image too large. Maximum size is 5MB");
      return;
    }

    const reader = new FileReader();
    reader.onloadend = () => {
      setTrainingReport(prev => ({
        ...prev,
        [fieldName]: reader.result
      }));
      toast.success("Photo uploaded");
    };
    reader.readAsDataURL(file);
  };

  const handleSaveReport = async (status = "draft") => {
    if (!selectedSession) {
      toast.error("Please select a session first");
      return;
    }

    try {
      const reportData = {
        ...trainingReport,
        session_id: selectedSession.id,
        additional_notes: aiGeneratedReport,
        status: status
      };

      await axiosInstance.post('/training-reports', reportData);
      toast.success(status === "draft" ? "Report saved as draft" : "Report submitted successfully!");
      
      if (status === "submitted") {
        setTrainingReport(prev => ({ ...prev, status: "submitted" }));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save report");
    }
  };

  const handleGenerateAIReport = async () => {
    if (!selectedSession) {
      toast.error("Please select a session first");
      return;
    }

    setGeneratingReport(true);
    try {
      const response = await axiosInstance.post(`/training-reports/${selectedSession.id}/generate-ai-report`);
      
      // Add checklist issues section to the AI report
      let fullReport = response.data.generated_report;
      
      if (checklistIssues.length > 0) {
        fullReport += "\n\n## VEHICLE INSPECTION ISSUES\n\n";
        fullReport += "The following vehicle issues requiring attention were identified during trainer inspections:\n\n";
        
        checklistIssues.forEach((issue, idx) => {
          fullReport += `**${idx + 1}. ${issue.participant_name}**\n`;
          issue.items.forEach(item => {
            fullReport += `   - ${item.item_name || item.name}: ${item.comments || 'Needs repair'}\n`;
          });
          fullReport += "\n";
        });
        
        fullReport += "**Recommendation:** These issues should be addressed before participants use their vehicles on public roads.\n";
      } else {
        fullReport += "\n\n## VEHICLE INSPECTION\n\n";
        fullReport += "All participant vehicles were inspected and found to be in good working condition. No issues requiring immediate attention were identified.\n";
      }
      
      setAiGeneratedReport(fullReport);
      toast.success("AI report generated successfully with checklist data!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to generate AI report");
    } finally {
      setGeneratingReport(false);
    }
  };


  // Professional DOCX Report Functions
  const handleGenerateProfessionalReport = async () => {
    if (!selectedSession) {
      toast.error("Please select a session first");
      return;
    }

    setGeneratingDOCX(true);
    try {
      const response = await axiosInstance.post(`/training-reports/${selectedSession.id}/generate-docx`);
      
      setProfessionalReportStatus(prev => ({
        ...prev,
        docx_generated: true,
        docx_filename: response.data.filename
      }));
      
      toast.success("Professional report generated! Click 'Download DOCX' to edit it.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to generate professional report");
    } finally {
      setGeneratingDOCX(false);
    }
  };

  const handleDownloadDOCX = async () => {
    try {
      const response = await axiosInstance.get(`/training-reports/${selectedSession.id}/download-docx`, {
        responseType: 'blob',
        headers: {
          'Accept': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
      });
      
      // Create blob with proper MIME type
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
      });
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = professionalReportStatus.docx_filename || `Training_Report_${selectedSession.name}.docx`;
      link.style.display = 'none';
      
      // Append to body, click, and cleanup
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
      
      toast.success("DOCX report downloaded! Check your Downloads folder.");
    } catch (error) {
      console.error("Download error:", error);
      toast.error(error.response?.data?.detail || "Failed to download report");
    }
  };

  const handleUploadEditedDOCX = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.docx')) {
      toast.error("Please upload a DOCX file");
      return;
    }

    setUploadingEdited(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axiosInstance.post(
        `/training-reports/${selectedSession.id}/upload-edited-docx`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );
      
      setProfessionalReportStatus(prev => ({
        ...prev,
        edited_uploaded: true,
        edited_docx_filename: response.data.filename
      }));
      
      toast.success("Edited report uploaded successfully! You can now submit the final report.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload edited report");
    } finally {
      setUploadingEdited(false);
    }
  };

  const handleSubmitFinalReport = async () => {
    if (!professionalReportStatus.edited_uploaded && !professionalReportStatus.docx_generated) {
      toast.error("Please generate and/or upload a report first");
      return;
    }

    setSubmittingFinal(true);
    try {
      const response = await axiosInstance.post(`/training-reports/${selectedSession.id}/submit-final`);
      
      setProfessionalReportStatus(prev => ({
        ...prev,
        pdf_submitted: true,
        pdf_filename: response.data.pdf_filename
      }));
      
      // Reload completion checklist to update status
      await loadCompletionChecklist(selectedSession.id);
      
      toast.success("✓ Final report uploaded successfully! You can now mark the training as completed.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to submit final report");
    } finally {
      setSubmittingFinal(false);
    }
  };

  const handleMarkSessionCompleted = async () => {
    if (!selectedSession) return;
    try {
      setMarkingCompleted(true);
      await axiosInstance.post(`/sessions/${selectedSession.id}/mark-completed`);
      
      toast.success("✓ Training marked as completed and moved to Past Training!");
      
      // Reload session data to show updated completion status
      await selectSession(selectedSession);
    } catch (error) {
      const errorMessage = error.response?.data?.detail || "Failed to mark session as completed";
      toast.error(errorMessage);
      
      // If error is about missing report, reload checklist to show current status
      if (errorMessage.includes("report")) {
        loadCompletionChecklist(selectedSession.id);
      }
    } finally {
      setMarkingCompleted(false);
    }
  };


  const handleUpdateSession = async () => {
    try {
      await axiosInstance.put(`/sessions/${editingSession.id}`, editingSession);
      toast.success("Session updated successfully");
      setEditSessionDialogOpen(false);
      loadSessions();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update session");
    }
  };

  const handleAddParticipant = async () => {
    if (!newParticipant.full_name || !newParticipant.id_number) {
      toast.error("Please fill all required fields (name and ID number)");
      return;
    }

    if (!selectedSession) {
      toast.error("Please select a session first");
      return;
    }

    try {
      // Create new user with defaults
      const userResponse = await axiosInstance.post("/auth/register", {
        ...newParticipant,
        password: newParticipant.password || "mddrc1",  // Default password
        email: newParticipant.email || "",  // Optional email
        role: "participant",
        company_id: selectedSession.company_id
      });

      const newUserId = userResponse.data.id;

      // Add to session
      const updatedParticipantIds = [...(selectedSession.participant_ids || []), newUserId];
      await axiosInstance.put(`/sessions/${selectedSession.id}`, {
        ...selectedSession,
        participant_ids: updatedParticipantIds
      });
      
      toast.success(`Participant ${newParticipant.full_name} added successfully`);
      setAddParticipantDialogOpen(false);
      setNewParticipant({ email: "", password: "", full_name: "", id_number: "", phone_number: "" });
      
      // Reload data
      await loadSessions();
      if (selectedSession) {
        await loadSessionData(selectedSession);
      }
    } catch (error) {
      console.error("Add participant error:", error);
      const errorMessage = error.response?.data?.detail 
        ? formatValidationError(error.response.data.detail)
        : "Failed to add participant";
      toast.error(errorMessage);
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

  // Handle certificate upload for a participant
  const handleCertificateUpload = async (participantId, file) => {
    if (!file) return;
    
    // Validate file type
    if (file.type !== 'application/pdf') {
      toast.error("Only PDF files are allowed");
      return;
    }
    
    // Check file size (5MB max)
    const maxSize = 5 * 1024 * 1024; // 5MB in bytes
    if (file.size > maxSize) {
      toast.error("File size exceeds 5MB limit");
      return;
    }
    
    setUploadingCertificates(prev => ({ ...prev, [participantId]: true }));
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axiosInstance.post(
        `/certificates/upload/${selectedSession.id}/${participantId}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      
      toast.success("Certificate uploaded successfully!");
      
      // Update certificate status
      setCertificateStatuses(prev => ({
        ...prev,
        [participantId]: {
          uploaded: true,
          url: response.data.certificate_url,
          size: response.data.file_size_mb
        }
      }));
      
      // Reload session data to refresh status
      await loadSessionData(selectedSession);
      
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload certificate");
    } finally {
      setUploadingCertificates(prev => ({ ...prev, [participantId]: false }));
    }
  };


  // Calculate statistics
  const uniqueParticipantsWithAttendance = attendance.filter((v, i, a) => 
    a.findIndex(t => t.participant_id === v.participant_id) === i
  ).length;
  
  // Separate pre-test and post-test results
  const preTestResults = testResults.filter(r => r.test_type === 'pre');
  const postTestResults = testResults.filter(r => r.test_type === 'post');
  
  const stats = {
    totalParticipants: participants.length,
    attendanceRate: participants.length > 0 
      ? ((uniqueParticipantsWithAttendance / participants.length) * 100).toFixed(0)
      : 0,
    preTestPassRate: preTestResults.length > 0
      ? ((preTestResults.filter(r => r.passed).length / preTestResults.length) * 100).toFixed(0)
      : 0,
    postTestPassRate: postTestResults.length > 0
      ? ((postTestResults.filter(r => r.passed).length / postTestResults.length) * 100).toFixed(0)
      : 0,
    improvement: (preTestResults.length > 0 && postTestResults.length > 0)
      ? (((postTestResults.filter(r => r.passed).length / postTestResults.length) - 
          (preTestResults.filter(r => r.passed).length / preTestResults.length)) * 100).toFixed(0)
      : 0,
    totalTestsTaken: testResults.length
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50">
      {/* Header */}
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
              <h1 className="text-2xl font-bold text-gray-900">Coordinator Portal</h1>
              <p className="text-sm text-gray-600">Welcome, {user.full_name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Marketing Portal link for users with marketing role */}
            {(user.additional_roles?.includes('marketing') || user.role === 'marketing') && (
              <Button 
                onClick={() => window.location.href = '/marketing'} 
                variant="outline" 
                className="flex items-center gap-2 bg-orange-50 border-orange-300 text-orange-700 hover:bg-orange-100"
              >
                <FileText className="w-4 h-4" />
                Marketing
              </Button>
            )}
            <Button onClick={onLogout} variant="outline" className="flex items-center gap-2">
              <LogOut className="w-4 h-4" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        ) : sessions.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Calendar className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-500">No sessions assigned yet</p>
            </CardContent>
          </Card>
        ) : (
          <Tabs defaultValue="sessions" className="space-y-6">
            <TabsList className="flex flex-wrap w-full h-auto justify-start gap-2 bg-gray-100 p-2 rounded-lg sm:grid sm:grid-cols-5">
              <TabsTrigger value="sessions" className="flex-1 min-w-[100px] sm:min-w-0">
                <Calendar className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">My Sessions</span>
                <span className="sm:hidden">Sessions</span>
              </TabsTrigger>
              <TabsTrigger value="management" className="flex-1 min-w-[100px] sm:min-w-0">
                <Users className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Session Management</span>
                <span className="sm:hidden">Management</span>
              </TabsTrigger>
              <TabsTrigger value="past-training" className="flex-1 min-w-[100px] sm:min-w-0">
                <FileText className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Past Training</span>
                <span className="sm:hidden">Past</span>
              </TabsTrigger>
              <TabsTrigger value="report" className="flex-1 min-w-[100px] sm:min-w-0">
                <FileText className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Training Report</span>
                <span className="sm:hidden">Report</span>
              </TabsTrigger>
              <TabsTrigger value="analytics" className="flex-1 min-w-[100px] sm:min-w-0">
                <BarChart3 className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">Analytics</span>
                <span className="sm:hidden">Analytics</span>
              </TabsTrigger>
              <TabsTrigger value="my-earnings" data-testid="my-earnings-tab" className="flex-1 min-w-[100px] sm:min-w-0 bg-gradient-to-r from-emerald-500 to-teal-500 text-white">
                <Wallet className="w-4 h-4 mr-2" />
                <span className="hidden sm:inline">My Earnings</span>
                <span className="sm:hidden">Earnings</span>
              </TabsTrigger>
            </TabsList>

            {/* Tab 1: My Sessions */}
            <TabsContent value="sessions">
              <Card>
                <CardHeader>
                  <CardTitle>My Assigned Sessions</CardTitle>
                  <CardDescription>Training sessions you are coordinating</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {sessions.map((session) => {
                      const stats = sessionStats[session.id] || {};
                      const participantTotal = stats.participantCount || 0;
                      
                      return (
                        <button
                          key={session.id}
                          onClick={() => selectSession(session)}
                          className={`p-5 rounded-lg border-2 text-left transition-all ${
                            selectedSession?.id === session.id
                              ? 'border-indigo-500 bg-indigo-50 shadow-md'
                              : 'border-gray-200 hover:border-indigo-300 bg-white'
                          }`}
                        >
                          <h3 className="font-bold text-gray-900 text-lg">{session.company_name || "Unknown Company"}</h3>
                          <p className="text-base text-gray-700 mt-1">{session.program_name || "Unknown Program"}</p>
                          <div className="mt-3 space-y-2">
                            <p className="text-sm text-gray-600">Session: {session.name}</p>
                            <p className="text-sm text-gray-600 flex items-center gap-2">
                              <Calendar className="w-4 h-4" />
                              {new Date(session.start_date).toLocaleDateString()} - {new Date(session.end_date).toLocaleDateString()}
                            </p>
                            <p className="text-sm text-gray-600">{session.location}</p>
                            
                            {/* Stats Summary */}
                            <div className="mt-3 pt-3 border-t space-y-1">
                              <div className="flex justify-between items-center">
                                <span className="text-xs text-gray-600">Participants:</span>
                                <span className="text-xs font-semibold text-gray-900">{participantTotal}</span>
                              </div>
                              <div className="flex justify-between items-center">
                                <span className="text-xs text-blue-600">Pre-Test:</span>
                                <span className="text-xs font-semibold text-blue-700">
                                  {stats.preTestCompleted || 0}/{participantTotal}
                                </span>
                              </div>
                              <div className="flex justify-between items-center">
                                <span className="text-xs text-green-600">Post-Test:</span>
                                <span className="text-xs font-semibold text-green-700">
                                  {stats.postTestCompleted || 0}/{participantTotal}
                                </span>
                              </div>
                              <div className="flex justify-between items-center">
                                <span className="text-xs text-purple-600">Feedback:</span>
                                <span className="text-xs font-semibold text-purple-700">
                                  {stats.feedbackCompleted || 0}/{participantTotal}
                                </span>
                              </div>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Tab 2: Session Management */}
            <TabsContent value="management">
              {selectedSession ? (
                <div className="space-y-6">
                  {/* Session Details Card */}
                  <Card>
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle>{selectedSession.name}</CardTitle>
                          <CardDescription>{selectedSession.location}</CardDescription>
                        </div>
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
                          
                          <Button
                            onClick={() => {
                              setEditingSession({ ...selectedSession });
                              setEditSessionDialogOpen(true);
                            }}
                            variant="outline"
                          >
                            <Edit className="w-4 h-4 mr-2" />
                            Edit Session
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-sm text-gray-600">Start Date</p>
                          <p className="font-semibold">{new Date(selectedSession.start_date).toLocaleDateString()}</p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">End Date</p>
                          <p className="font-semibold">{new Date(selectedSession.end_date).toLocaleDateString()}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Release Controls */}
                  <Card className="border-indigo-200">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Clock className="w-5 h-5 text-indigo-600" />
                        Release Controls
                      </CardTitle>
                      <CardDescription>Control when participants can access tests and feedback</CardDescription>
                    </CardHeader>
                    <CardContent>
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
                    </CardContent>
                  </Card>

                  {/* Session Summary Statistics */}
                  <Card className="bg-gradient-to-r from-indigo-50 to-purple-50">
                    <CardHeader>
                      <CardTitle>Session Summary</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                          <p className="text-2xl font-bold text-indigo-600">{participants.length}</p>
                          <p className="text-sm text-gray-600 mt-1">Total Participants</p>
                        </div>
                        <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                          <p className="text-2xl font-bold text-blue-600">
                            {testResults.filter(r => r.test_type === 'pre').length}/{participants.length}
                          </p>
                          <p className="text-sm text-gray-600 mt-1">Pre-Test Completed</p>
                        </div>
                        <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                          <p className="text-2xl font-bold text-green-600">
                            {testResults.filter(r => r.test_type === 'post').length}/{participants.length}
                          </p>
                          <p className="text-sm text-gray-600 mt-1">Post-Test Completed</p>
                        </div>
                        <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                          <p className="text-2xl font-bold text-purple-600">
                            {attendance.filter((v, i, a) => a.findIndex(t => t.participant_id === v.participant_id) === i).length}/{participants.length}
                          </p>
                          <p className="text-sm text-gray-600 mt-1">Attendance Records</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Participants */}
                  <Card>
                    <CardHeader>
                      <div className="flex justify-between items-center">
                        <div>
                          <CardTitle>Participants ({participants.length})</CardTitle>
                          <CardDescription>All participants enrolled in this session</CardDescription>
                        </div>
                        <Button
                          onClick={() => setAddParticipantDialogOpen(true)}
                          variant="outline"
                          size="sm"
                          style={{ borderColor: primaryColor, color: primaryColor }}
                        >
                          <Users className="w-4 h-4 mr-2" />
                          Add Participant
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {participants.length === 0 ? (
                        <div className="text-center py-8">
                          <Users className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                          <p className="text-gray-500">No participants assigned yet</p>
                          <Button
                            onClick={() => setAddParticipantDialogOpen(true)}
                            variant="outline"
                            className="mt-4"
                          >
                            Add First Participant
                          </Button>
                        </div>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b bg-gray-50">
                                <th className="text-left p-3 font-semibold">Participant Name</th>
                                <th className="text-left p-3 font-semibold">ID Number</th>
                                <th className="text-center p-3 font-semibold">Attendance</th>
                                <th className="text-center p-3 font-semibold">Pre-Test</th>
                                <th className="text-center p-3 font-semibold">Post-Test</th>
                                <th className="text-center p-3 font-semibold">Feedback</th>
                                <th className="text-center p-3 font-semibold">Certificate</th>
                              </tr>
                            </thead>
                            <tbody>
                              {participants.map((p) => {
                                // Find participant's test results
                                const preTest = testResults.find(r => r.participant_id === p.id && r.test_type === 'pre');
                                const postTest = testResults.find(r => r.participant_id === p.id && r.test_type === 'post');
                                
                                // Find participant's access record for feedback status
                                const access = sessionAccess.find(a => a.participant_id === p.id);
                                
                                return (
                                  <tr key={p.id} className="border-b hover:bg-gray-50">
                                    <td className="p-3">
                                      <p className="font-medium text-gray-900">{p.full_name}</p>
                                      <p className="text-xs text-gray-500">{p.email}</p>
                                    </td>
                                    <td className="p-3 text-gray-700">{p.id_number || 'N/A'}</td>
                                    <td className="p-3 text-center">
                                      <div className="flex flex-col gap-1 items-center">
                                        {attendanceStatus[p.id] === 'absent' ? (
                                          <>
                                            <span className="px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-800">
                                              ✗ ABSENT
                                            </span>
                                            <Button
                                              onClick={() => handleMarkAttendance(p.id, 'present')}
                                              disabled={updatingAttendance[p.id]}
                                              size="sm"
                                              variant="outline"
                                              className="text-xs h-6"
                                            >
                                              {updatingAttendance[p.id] ? "..." : "Mark Present"}
                                            </Button>
                                          </>
                                        ) : attendanceStatus[p.id] === 'present' ? (
                                          <>
                                            <span className="px-2 py-1 rounded text-xs font-bold bg-green-100 text-green-800">
                                              ✓ PRESENT
                                            </span>
                                            <Button
                                              onClick={() => handleMarkAttendance(p.id, 'absent')}
                                              disabled={updatingAttendance[p.id]}
                                              size="sm"
                                              variant="outline"
                                              className="text-xs h-6"
                                            >
                                              {updatingAttendance[p.id] ? "..." : "Mark Absent"}
                                            </Button>
                                          </>
                                        ) : (
                                          <div className="flex gap-1">
                                            <Button
                                              onClick={() => handleMarkAttendance(p.id, 'present')}
                                              disabled={updatingAttendance[p.id]}
                                              size="sm"
                                              className="text-xs h-7 bg-green-600 hover:bg-green-700"
                                            >
                                              Present
                                            </Button>
                                            <Button
                                              onClick={() => handleMarkAttendance(p.id, 'absent')}
                                              disabled={updatingAttendance[p.id]}
                                              size="sm"
                                              variant="destructive"
                                              className="text-xs h-7"
                                            >
                                              Absent
                                            </Button>
                                          </div>
                                        )}
                                      </div>
                                    </td>
                                    <td className="p-3 text-center">
                                      {preTest ? (
                                        <div className="flex flex-col items-center gap-1">
                                          <span className={`px-2 py-1 rounded text-xs font-bold ${
                                            preTest.passed 
                                              ? 'bg-green-100 text-green-800' 
                                              : 'bg-red-100 text-red-800'
                                          }`}>
                                            {preTest.passed ? '✓ PASS' : '✗ FAIL'}
                                          </span>
                                          <span className="text-xs text-gray-600">
                                            {preTest.score?.toFixed(0)}%
                                          </span>
                                        </div>
                                      ) : (
                                        <span className="text-gray-400 text-xs">Not taken</span>
                                      )}
                                    </td>
                                    <td className="p-3 text-center">
                                      {postTest ? (
                                        <div className="flex flex-col items-center gap-1">
                                          <span className={`px-2 py-1 rounded text-xs font-bold ${
                                            postTest.passed 
                                              ? 'bg-green-100 text-green-800' 
                                              : 'bg-red-100 text-red-800'
                                          }`}>
                                            {postTest.passed ? '✓ PASS' : '✗ FAIL'}
                                          </span>
                                          <span className="text-xs text-gray-600">
                                            {postTest.score?.toFixed(0)}%
                                          </span>
                                        </div>
                                      ) : (
                                        <span className="text-gray-400 text-xs">Not taken</span>
                                      )}
                                    </td>
                                    <td className="p-3 text-center">
                                      {access?.feedback_completed ? (
                                        <span className="px-2 py-1 rounded text-xs font-bold bg-purple-100 text-purple-800">
                                          ✓ Submitted
                                        </span>
                                      ) : (
                                        <span className="text-gray-400 text-xs">Not submitted</span>
                                      )}
                                    </td>
                                    <td className="p-3 text-center">
                                      <div className="flex flex-col gap-2 items-center">
                                        {certificateStatuses[p.id]?.uploaded ? (
                                          <div className="flex flex-col gap-1 items-center">
                                            <span className="px-2 py-1 rounded text-xs font-bold bg-blue-100 text-blue-800">
                                              ✓ Uploaded
                                            </span>
                                            <div className="flex gap-2">
                                              <button
                                                onClick={() => {
                                                  const certUrl = certificateStatuses[p.id]?.url;
                                                  if (certUrl) {
                                                    // Use REACT_APP_BACKEND_URL for external access
                                                    window.open(`${process.env.REACT_APP_BACKEND_URL}${certUrl}`, '_blank');
                                                  }
                                                }}
                                                className="cursor-pointer text-xs text-blue-600 hover:underline"
                                              >
                                                View
                                              </button>
                                              <label 
                                                htmlFor={`cert-${p.id}`}
                                                className="cursor-pointer text-xs text-blue-600 hover:underline"
                                              >
                                                Replace
                                              </label>
                                            </div>
                                          </div>
                                        ) : (
                                          <label 
                                            htmlFor={`cert-${p.id}`}
                                            className="cursor-pointer px-3 py-1 rounded text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                                          >
                                            {uploadingCertificates[p.id] ? "Uploading..." : "Upload PDF"}
                                          </label>
                                        )}
                                        <input
                                          id={`cert-${p.id}`}
                                          type="file"
                                          accept=".pdf"
                                          className="hidden"
                                          onChange={(e) => {
                                            const file = e.target.files?.[0];
                                            if (file) {
                                              handleCertificateUpload(p.id, file);
                                            }
                                            e.target.value = null; // Reset input
                                          }}
                                          disabled={uploadingCertificates[p.id]}
                                        />
                                      </div>
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Attendance */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Attendance Records</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {attendance.length === 0 ? (
                        <p className="text-gray-500 text-center py-8">No attendance records yet</p>
                      ) : (
                        <div className="space-y-2">
                          {attendance.slice(0, 10).map((record, idx) => {
                            const formatTime = (timeStr) => {
                              if (!timeStr) return '-';
                              // Time is already in HH:MM:SS format from backend
                              try {
                                // If it's already in HH:MM:SS format, just format it nicely
                                const parts = timeStr.split(':');
                                if (parts.length >= 2) {
                                  const hour = parseInt(parts[0]);
                                  const minute = parts[1];
                                  const ampm = hour >= 12 ? 'PM' : 'AM';
                                  const displayHour = hour % 12 || 12;
                                  return `${displayHour}:${minute} ${ampm}`;
                                }
                                return timeStr;
                              } catch {
                                return timeStr;
                              }
                            };
                            
                            return (
                              <div key={idx} className="p-3 bg-gray-50 rounded flex justify-between items-center">
                                <div>
                                  <p className="font-medium">{record.participant_name}</p>
                                  <p className="text-xs text-gray-600">{new Date(record.date).toLocaleDateString()}</p>
                                </div>
                                <div className="text-sm">
                                  <span className="text-green-600 font-medium">In: {formatTime(record.clock_in)}</span>
                                  <span className="mx-2">|</span>
                                  <span className="text-red-600 font-medium">Out: {formatTime(record.clock_out)}</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* All Vehicle Checklists */}
                  <Card className="border-blue-200">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-blue-700">
                        <span className="text-2xl">✓</span>
                        Vehicle Checklists - All Inspections
                      </CardTitle>
                      <CardDescription>All vehicle inspections completed by trainers</CardDescription>
                    </CardHeader>
                    <CardContent>
                      {allChecklists.length === 0 ? (
                        <div className="text-center py-8">
                          <p className="text-gray-500">No checklists completed yet</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <p className="text-sm text-gray-600 mb-3">
                            {allChecklists.length} participant{allChecklists.length !== 1 ? 's' : ''} with completed checklists. Click to view details.
                          </p>
                          {allChecklists.map((checklistData, idx) => (
                            <div key={idx} className="border border-blue-200 rounded-lg overflow-hidden">
                              {/* Collapsed view - just participant name */}
                              <div 
                                className="p-3 bg-blue-50 hover:bg-blue-100 cursor-pointer transition-colors flex justify-between items-center"
                                onClick={() => setExpandedChecklist(expandedChecklist === checklistData.participant_name ? null : checklistData.participant_name)}
                              >
                                <div className="flex items-center gap-3">
                                  <span className="text-blue-600 font-bold">✓</span>
                                  <div>
                                    <h4 className="font-semibold text-blue-900">{checklistData.participant_name}</h4>
                                    <p className="text-xs text-blue-700">{checklistData.items.length} item{checklistData.items.length !== 1 ? 's' : ''} inspected</p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs text-blue-600 font-medium">
                                    {expandedChecklist === checklistData.participant_name ? 'Hide Details' : 'View Details'}
                                  </span>
                                  <span className={`text-blue-600 transition-transform ${expandedChecklist === checklistData.participant_name ? 'rotate-180' : ''}`}>
                                    ▼
                                  </span>
                                </div>
                              </div>
                              
                              {/* Expanded view - checklist details */}
                              {expandedChecklist === checklistData.participant_name && (
                                <div className="p-4 bg-white border-t border-blue-200">
                                  <div className="space-y-2">
                                    {checklistData.items.map((item, itemIdx) => {
                                      const itemStatus = (item.status || '').toLowerCase();
                                      const needsRepair = itemStatus === 'needs_repair';
                                      
                                      return (
                                        <div 
                                          key={itemIdx} 
                                          className={`flex justify-between items-center p-3 rounded border-2 ${
                                            needsRepair 
                                              ? 'bg-red-50 border-red-300' 
                                              : 'bg-green-50 border-green-200'
                                          }`}
                                        >
                                          <span className={`text-sm font-medium ${needsRepair ? 'text-red-900' : 'text-gray-900'}`}>
                                            {needsRepair && '⚠️ '}
                                            {item.item || item.name || 'Item'}
                                          </span>
                                          <span className={`text-xs px-3 py-1.5 rounded-full font-bold ${
                                            needsRepair
                                              ? 'bg-red-200 text-red-900 border-2 border-red-400' 
                                              : 'bg-green-200 text-green-900 border-2 border-green-400'
                                          }`}>
                                            {needsRepair ? '🔧 NEEDS REPAIR' : '✓ ' + (item.status?.toUpperCase() || 'GOOD')}
                                          </span>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Vehicle Checklist Issues */}
                  <Card className="border-red-200">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-red-700">
                        <span className="text-2xl">⚠️</span>
                        Vehicle Issues - Needs Repair
                      </CardTitle>
                      <CardDescription>Items flagged by trainers requiring attention</CardDescription>
                    </CardHeader>
                    <CardContent>
                      {checklistIssues.length === 0 ? (
                        <div className="text-center py-8">
                          <p className="text-green-600 font-medium">✓ No vehicle issues reported</p>
                          <p className="text-sm text-gray-500 mt-1">All vehicles inspected are in good condition</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <p className="text-sm text-gray-600 mb-3">
                            {checklistIssues.length} participant{checklistIssues.length !== 1 ? 's' : ''} with vehicle issues. Click to view details.
                          </p>
                          {checklistIssues.map((issue, idx) => (
                            <div key={idx} className="border border-red-200 rounded-lg overflow-hidden">
                              {/* Collapsed view - just participant name */}
                              <div 
                                className="p-3 bg-red-50 hover:bg-red-100 cursor-pointer transition-colors flex justify-between items-center"
                                onClick={() => setExpandedVehicleIssue(expandedVehicleIssue === issue.participant_name ? null : issue.participant_name)}
                              >
                                <div className="flex items-center gap-3">
                                  <span className="text-red-600 font-bold">⚠️</span>
                                  <div>
                                    <h4 className="font-semibold text-red-900">{issue.participant_name}</h4>
                                    <p className="text-xs text-red-700">{issue.items.length} issue{issue.items.length !== 1 ? 's' : ''} found</p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs text-red-600 font-medium">
                                    {expandedVehicleIssue === issue.participant_name ? 'Hide Details' : 'View Details'}
                                  </span>
                                  <span className={`text-red-600 transition-transform ${expandedVehicleIssue === issue.participant_name ? 'rotate-180' : ''}`}>
                                    ▼
                                  </span>
                                </div>
                              </div>
                              
                              {/* Expanded view - issue details */}
                              {expandedVehicleIssue === issue.participant_name && (
                                <div className="p-4 bg-white border-t border-red-200">
                                  <div className="space-y-3">
                                    {issue.items.map((item, itemIdx) => (
                                      <div key={itemIdx} className="p-3 bg-red-50 rounded border border-red-200">
                                        <p className="font-semibold text-sm text-red-900 mb-2">
                                          🔧 {item.item || item.item_name || item.name || 'Item'}
                                        </p>
                                        {item.comments && (
                                          <p className="text-sm text-gray-700 bg-white p-2 rounded mb-2">
                                            <span className="font-medium">Issue: </span>{item.comments}
                                          </p>
                                        )}
                                        {(item.photo_url || item.photo) && (
                                          <div className="mt-2">
                                            <p className="text-xs text-gray-600 mb-1">Photo:</p>
                                            <img 
                                              src={item.photo_url || item.photo} 
                                              alt={item.item || 'Vehicle item'} 
                                              className="w-32 h-32 object-cover rounded border-2 border-red-300 cursor-pointer hover:scale-105 transition-transform"
                                              onClick={() => window.open(item.photo_url || item.photo, '_blank')}
                                            />
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <Card>
                  <CardContent className="py-12 text-center">
                    <p className="text-gray-500">Please select a session first</p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Tab 3: Training Report */}
            <TabsContent value="report">
              {selectedSession ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Training Completion Report - {selectedSession.name}</CardTitle>
                    <CardDescription>
                      Upload training photos and generate a comprehensive report
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Photo Upload Section */}
                    <div className="space-y-4">
                      <h3 className="font-semibold text-lg">Training Photos</h3>
                      <p className="text-sm text-gray-600">Upload photos from the training session (max 5MB each)</p>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Group Photo */}
                        <div className="space-y-2">
                          <Label>1. Group Photo *</Label>
                          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-indigo-500 transition-colors">
                            {trainingReport.group_photo ? (
                              <div className="relative">
                                <img src={trainingReport.group_photo} alt="Group" className="w-full h-40 object-cover rounded" />
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  className="absolute top-2 right-2"
                                  onClick={() => setTrainingReport(prev => ({ ...prev, group_photo: "" }))}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            ) : (
                              <label className="cursor-pointer">
                                <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                                <p className="text-sm text-gray-600">Click to upload</p>
                                <input
                                  type="file"
                                  accept="image/*"
                                  capture="environment"
                                  className="hidden"
                                  onChange={(e) => handlePhotoUpload(e, 'group_photo')}
                                />
                              </label>
                            )}
                          </div>
                        </div>

                        {/* Theory Photo 1 */}
                        <div className="space-y-2">
                          <Label>2. Theory Session Photo 1 *</Label>
                          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-indigo-500 transition-colors">
                            {trainingReport.theory_photo_1 ? (
                              <div className="relative">
                                <img src={trainingReport.theory_photo_1} alt="Theory 1" className="w-full h-40 object-cover rounded" />
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  className="absolute top-2 right-2"
                                  onClick={() => setTrainingReport(prev => ({ ...prev, theory_photo_1: "" }))}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            ) : (
                              <label className="cursor-pointer">
                                <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                                <p className="text-sm text-gray-600">Click to upload</p>
                                <input
                                  type="file"
                                  accept="image/*"
                                  capture="environment"
                                  className="hidden"
                                  onChange={(e) => handlePhotoUpload(e, 'theory_photo_1')}
                                />
                              </label>
                            )}
                          </div>
                        </div>

                        {/* Theory Photo 2 */}
                        <div className="space-y-2">
                          <Label>3. Theory Session Photo 2 *</Label>
                          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-indigo-500 transition-colors">
                            {trainingReport.theory_photo_2 ? (
                              <div className="relative">
                                <img src={trainingReport.theory_photo_2} alt="Theory 2" className="w-full h-40 object-cover rounded" />
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  className="absolute top-2 right-2"
                                  onClick={() => setTrainingReport(prev => ({ ...prev, theory_photo_2: "" }))}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            ) : (
                              <label className="cursor-pointer">
                                <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                                <p className="text-sm text-gray-600">Click to upload</p>
                                <input
                                  type="file"
                                  accept="image/*"
                                  capture="environment"
                                  className="hidden"
                                  onChange={(e) => handlePhotoUpload(e, 'theory_photo_2')}
                                />
                              </label>
                            )}
                          </div>
                        </div>

                        {/* Practical Photo 1 */}
                        <div className="space-y-2">
                          <Label>4. Practical Session Photo 1 *</Label>
                          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-indigo-500 transition-colors">
                            {trainingReport.practical_photo_1 ? (
                              <div className="relative">
                                <img src={trainingReport.practical_photo_1} alt="Practical 1" className="w-full h-40 object-cover rounded" />
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  className="absolute top-2 right-2"
                                  onClick={() => setTrainingReport(prev => ({ ...prev, practical_photo_1: "" }))}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            ) : (
                              <label className="cursor-pointer">
                                <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                                <p className="text-sm text-gray-600">Click to upload</p>
                                <input
                                  type="file"
                                  accept="image/*"
                                  capture="environment"
                                  className="hidden"
                                  onChange={(e) => handlePhotoUpload(e, 'practical_photo_1')}
                                />
                              </label>
                            )}
                          </div>
                        </div>

                        {/* Practical Photo 2 */}
                        <div className="space-y-2">
                          <Label>5. Practical Session Photo 2 *</Label>
                          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-indigo-500 transition-colors">
                            {trainingReport.practical_photo_2 ? (
                              <div className="relative">
                                <img src={trainingReport.practical_photo_2} alt="Practical 2" className="w-full h-40 object-cover rounded" />
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  className="absolute top-2 right-2"
                                  onClick={() => setTrainingReport(prev => ({ ...prev, practical_photo_2: "" }))}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            ) : (
                              <label className="cursor-pointer">
                                <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                                <p className="text-sm text-gray-600">Click to upload</p>
                                <input
                                  type="file"
                                  accept="image/*"
                                  capture="environment"
                                  className="hidden"
                                  onChange={(e) => handlePhotoUpload(e, 'practical_photo_2')}
                                />
                              </label>
                            )}
                          </div>
                        </div>

                        {/* Practical Photo 3 */}
                        <div className="space-y-2">
                          <Label>6. Practical Session Photo 3 *</Label>
                          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-indigo-500 transition-colors">
                            {trainingReport.practical_photo_3 ? (
                              <div className="relative">
                                <img src={trainingReport.practical_photo_3} alt="Practical 3" className="w-full h-40 object-cover rounded" />
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  className="absolute top-2 right-2"
                                  onClick={() => setTrainingReport(prev => ({ ...prev, practical_photo_3: "" }))}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            ) : (
                              <label className="cursor-pointer">
                                <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                                <p className="text-sm text-gray-600">Click to upload</p>
                                <input
                                  type="file"
                                  accept="image/*"
                                  capture="environment"
                                  className="hidden"
                                  onChange={(e) => handlePhotoUpload(e, 'practical_photo_3')}
                                />
                              </label>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Professional DOCX Report Workflow */}
                    <div className="space-y-4 border-t pt-6">
                      <div>
                        <h3 className="font-semibold text-lg text-indigo-900">📄 Professional Training Report (DOCX → PDF)</h3>
                        <p className="text-sm text-gray-600">Generate auto-filled report, edit in MS Word, and submit as PDF</p>
                      </div>

                      {/* Step 1: Generate DOCX */}
                      <Card className="bg-blue-50 border-blue-200">
                        <CardContent className="pt-6">
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-semibold text-blue-900">Step 1: Generate Report</p>
                              <p className="text-sm text-gray-700">Creates a professional DOCX with all your session data pre-filled</p>
                              {professionalReportStatus.docx_generated && (
                                <p className="text-xs text-green-700 mt-1">✓ Report generated: {professionalReportStatus.docx_filename}</p>
                              )}
                            </div>
                            <Button
                              onClick={handleGenerateProfessionalReport}
                              disabled={generatingDOCX || professionalReportStatus.pdf_submitted}
                              className="bg-blue-600 hover:bg-blue-700"
                            >
                              {generatingDOCX ? (
                                <>
                                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                  Generating...
                                </>
                              ) : (
                                <>
                                  <FileText className="w-4 h-4 mr-2" />
                                  Generate DOCX
                                </>
                              )}
                            </Button>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Step 2: Download & Edit */}
                      <Card className="bg-purple-50 border-purple-200">
                        <CardContent className="pt-6">
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-semibold text-purple-900">Step 2: Download & Edit</p>
                              <p className="text-sm text-gray-700">Download, open in MS Word, add comments & photos, save</p>
                            </div>
                            <Button
                              onClick={handleDownloadDOCX}
                              disabled={!professionalReportStatus.docx_generated || professionalReportStatus.pdf_submitted}
                              variant="outline"
                              className="border-purple-400 text-purple-700 hover:bg-purple-100"
                            >
                              <Upload className="w-4 h-4 mr-2" />
                              Download DOCX
                            </Button>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Step 3: Upload Edited */}
                      <Card className="bg-amber-50 border-amber-200">
                        <CardContent className="pt-6">
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-semibold text-amber-900">Step 3: Upload Edited Report</p>
                              <p className="text-sm text-gray-700">Upload your edited DOCX file</p>
                              {professionalReportStatus.edited_uploaded && (
                                <p className="text-xs text-green-700 mt-1">✓ Edited report uploaded: {professionalReportStatus.edited_docx_filename}</p>
                              )}
                            </div>
                            <label>
                              <input
                                type="file"
                                accept=".docx"
                                onChange={handleUploadEditedDOCX}
                                disabled={!professionalReportStatus.docx_generated || professionalReportStatus.pdf_submitted || uploadingEdited}
                                className="hidden"
                              />
                              <Button
                                as="span"
                                disabled={!professionalReportStatus.docx_generated || professionalReportStatus.pdf_submitted || uploadingEdited}
                                variant="outline"
                                className="border-amber-400 text-amber-700 hover:bg-amber-100 cursor-pointer"
                              >
                                {uploadingEdited ? (
                                  <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-amber-700 mr-2"></div>
                                    Uploading...
                                  </>
                                ) : (
                                  <>
                                    <Upload className="w-4 h-4 mr-2" />
                                    Upload Edited DOCX
                                  </>
                                )}
                              </Button>
                            </label>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Step 4: Submit Final */}
                      <Card className="bg-green-50 border-green-200">
                        <CardContent className="pt-6">
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="font-semibold text-green-900">Step 4: Submit Final Report</p>
                              <p className="text-sm text-gray-700">Converts to PDF and sends to supervisors & admins</p>
                              {professionalReportStatus.pdf_submitted && (
                                <p className="text-xs text-green-700 mt-1">✓ Report submitted as PDF: {professionalReportStatus.pdf_filename}</p>
                              )}
                            </div>
                            <Button
                              onClick={handleSubmitFinalReport}
                              disabled={!professionalReportStatus.docx_generated || professionalReportStatus.pdf_submitted || submittingFinal}
                              className="bg-green-600 hover:bg-green-700"
                            >
                              {submittingFinal ? (
                                <>
                                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                  Submitting...
                                </>
                              ) : (
                                <>
                                  <Send className="w-4 h-4 mr-2" />
                                  Submit Final Report
                                </>
                              )}
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Divider */}
                    <div className="border-t my-8"></div>

                    {/* AI Report Generation */}
                    <div className="space-y-4">
                      <div className="flex justify-between items-center">
                        <div>
                          <h3 className="font-semibold text-lg">AI-Powered Report (Optional)</h3>
                          <p className="text-sm text-gray-600">Quick text-based report generation</p>
                        </div>
                        <Button
                          onClick={handleGenerateAIReport}
                          disabled={generatingReport}
                          style={{ backgroundColor: primaryColor }}
                        >
                          {generatingReport ? (
                            <>
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                              Generating...
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-4 h-4 mr-2" />
                              Generate AI Report
                            </>
                          )}
                        </Button>
                      </div>

                      <Textarea
                        value={aiGeneratedReport}
                        onChange={(e) => setAiGeneratedReport(e.target.value)}
                        placeholder="Click 'Generate AI Report' to create a comprehensive training report, or write your own..."
                        className="min-h-[400px] font-mono text-sm"
                      />
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3 border-t pt-6">
                      <Button
                        onClick={() => handleSaveReport("draft")}
                        variant="outline"
                        className="flex-1"
                        disabled={trainingReport.status === "submitted"}
                      >
                        <Save className="w-4 h-4 mr-2" />
                        Save as Draft
                      </Button>
                      <Button
                        onClick={() => handleSaveReport("submitted")}
                        style={{ backgroundColor: primaryColor }}
                        className="flex-1"
                        disabled={trainingReport.status === "submitted"}
                      >
                        <Send className="w-4 h-4 mr-2" />
                        Submit Final Report
                      </Button>
                    </div>

                    {trainingReport.status === "submitted" && (
                      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                        <p className="text-green-800 font-semibold">✓ Report Submitted Successfully</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="py-12 text-center">
                    <p className="text-gray-500">Please select a session first</p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Tab 4: Analytics */}
            <TabsContent value="analytics">
              {selectedSession ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm text-gray-600">Total Participants</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-3xl font-bold text-indigo-600">{stats.totalParticipants}</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm text-gray-600">Attendance Rate</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-3xl font-bold text-green-600">{stats.attendanceRate}%</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm text-gray-600">Pre-Test Pass Rate</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-3xl font-bold text-blue-600">{stats.preTestPassRate}%</p>
                      <p className="text-xs text-gray-500 mt-1">Before Training</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm text-gray-600">Post-Test Pass Rate</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-3xl font-bold text-green-600">{stats.postTestPassRate}%</p>
                      <p className="text-xs text-gray-500 mt-1">After Training</p>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm text-gray-600">Improvement</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className={`text-3xl font-bold ${stats.improvement >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {stats.improvement > 0 ? '+' : ''}{stats.improvement}%
                      </p>
                      <p className="text-xs text-gray-500 mt-1">Pass Rate Change</p>
                    </CardContent>
                  </Card>

                  {/* Test Results Breakdown */}
                  <Card className="md:col-span-2">
                    <CardHeader>
                      <CardTitle>Test Results Overview</CardTitle>
                      <CardDescription>Recent test submissions and scores</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {!testResults || testResults.length === 0 ? (
                          <div className="text-center py-8">
                            <FileText className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                            <p className="text-gray-500">No test results yet</p>
                            <p className="text-sm text-gray-400 mt-1">Results will appear when participants complete tests</p>
                          </div>
                        ) : (
                          testResults.slice(0, 8).map((result, idx) => {
                            const participant = participants.find(p => p.id === result.participant_id);
                            const scorePercentage = result.total_questions > 0 
                              ? ((result.correct_answers / result.total_questions) * 100).toFixed(0)
                              : 0;
                            
                            return (
                              <div key={idx} className="flex justify-between items-center p-3 bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg border">
                                <div className="flex-1">
                                  <p className="font-semibold text-sm">
                                    {participant?.full_name || 'Unknown Participant'}
                                  </p>
                                  <div className="flex items-center gap-3 mt-1">
                                    <p className="text-xs text-gray-600">
                                      {result.test_type === 'pre' ? '📝 Pre-Test' : '📋 Post-Test'}
                                    </p>
                                    <p className="text-xs text-gray-600">
                                      Score: {result.correct_answers}/{result.total_questions} ({scorePercentage}%)
                                    </p>
                                  </div>
                                </div>
                                <span className={`px-3 py-1.5 rounded-full text-xs font-bold border ${
                                  result.passed 
                                    ? 'bg-green-100 text-green-800 border-green-300' 
                                    : 'bg-red-100 text-red-800 border-red-300'
                                }`}>
                                  {result.passed ? '✓ PASSED' : '✗ FAILED'}
                                </span>
                              </div>
                            );
                          })
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Attendance Summary */}
                  <Card className="md:col-span-2">
                    <CardHeader>
                      <CardTitle>Recent Attendance</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {attendance.length === 0 ? (
                          <p className="text-gray-500 text-center py-8">No attendance records yet</p>
                        ) : (
                          attendance.slice(0, 5).map((record, idx) => (
                            <div key={idx} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                              <div>
                                <p className="font-medium text-sm">{record.participant_name}</p>
                                <p className="text-xs text-gray-600">{new Date(record.date).toLocaleDateString()}</p>
                              </div>
                              <div className="text-xs">
                                <span className="text-green-600">In: {record.clock_in || '-'}</span>
                                <span className="mx-2">|</span>
                                <span className="text-red-600">Out: {record.clock_out || '-'}</span>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <Card>
                  <CardContent className="py-12 text-center">
                    <p className="text-gray-500">Please select a session first</p>
                  </CardContent>
                </Card>
              )}


                  {/* Feedback Summary */}
                  <Card className="md:col-span-2">
                    <CardHeader>
                      <CardTitle>Participant Feedback Summary</CardTitle>
                      <CardDescription>All participant feedback and ratings</CardDescription>
                    </CardHeader>
                    <CardContent>
                      {!courseFeedback || courseFeedback.length === 0 ? (
                        <div className="text-center py-8">
                          <MessageSquare className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                          <p className="text-gray-500">No feedback submitted yet</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {courseFeedback.map((feedback, idx) => {
                            const participant = participants.find(p => p.id === feedback.participant_id);
                            const starRatings = feedback.responses?.filter(r => typeof r.answer === 'number') || [];
                            const textResponses = feedback.responses?.filter(r => typeof r.answer === 'string') || [];
                            
                            return (
                              <div key={idx} className="border rounded-lg p-4 bg-purple-50">
                                <div className="flex justify-between items-start mb-3">
                                  <h4 className="font-semibold text-purple-900">
                                    {participant?.full_name || 'Unknown Participant'}
                                  </h4>
                                  <span className="text-xs text-gray-500">
                                    {new Date(feedback.submitted_at).toLocaleDateString()}
                                  </span>
                                </div>
                                
                                {/* Star Ratings */}
                                {starRatings.length > 0 && (
                                  <div className="mb-3">
                                    <p className="text-sm font-medium text-gray-700 mb-2">Ratings:</p>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                      {starRatings.map((rating, rIdx) => (
                                        <div key={rIdx} className="flex justify-between text-sm">
                                          <span className="text-gray-600 text-xs">{rating.question}:</span>
                                          <span className="text-yellow-600 font-medium">
                                            {'⭐'.repeat(rating.answer)} ({rating.answer}/5)
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                
                                {/* Text Responses */}
                                {textResponses.length > 0 && (
                                  <div>
                                    <p className="text-sm font-medium text-gray-700 mb-2">Comments:</p>
                                    <div className="space-y-2">
                                      {textResponses.map((response, rIdx) => (
                                        <div key={rIdx} className="bg-white p-2 rounded border">
                                          <p className="text-xs font-medium text-gray-700">{response.question}</p>
                                          <p className="text-sm text-gray-900 mt-1">{response.answer}</p>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </CardContent>
                  </Card>


                  {/* Coordinator Feedback Section */}
                  <Card className="md:col-span-2">
                    <CardHeader>
                      <CardTitle>Coordinator Feedback</CardTitle>
                      <CardDescription>Provide your feedback about the training session</CardDescription>
                    </CardHeader>
                    <CardContent>
                      {coordinatorFeedbackTemplate && (
                        <div className="space-y-4">
                          {coordinatorFeedbackTemplate.questions?.map((question) => (
                            <div key={question.id} className="space-y-2">
                              <label className="text-sm font-medium text-gray-700">
                                {question.question}
                                {question.type === 'rating' && <span className="text-gray-500 ml-1">(Rate 1-{question.scale})</span>}
                              </label>
                              {question.type === 'rating' ? (
                                <div className="flex gap-2">
                                  {[...Array(question.scale)].map((_, i) => (
                                    <button
                                      key={i}
                                      onClick={() => setCoordinatorFeedback({...coordinatorFeedback, [question.id]: i + 1})}
                                      className={`w-10 h-10 rounded-full font-bold ${
                                        coordinatorFeedback[question.id] === i + 1
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
                                  value={coordinatorFeedback[question.id] || ''}
                                  onChange={(e) => setCoordinatorFeedback({...coordinatorFeedback, [question.id]: e.target.value})}
                                  className="w-full p-2 border rounded-md"
                                  rows={3}
                                  disabled={feedbackSubmitted}
                                  placeholder="Enter your response..."
                                />
                              )}
                            </div>
                          ))}
                          
                          <div className="flex items-center gap-2 mt-6">
                            {feedbackSubmitted ? (
                              <div className="flex items-center gap-2">
                                <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                                  ✓ Feedback Submitted
                                </span>
                                <Button
                                  onClick={() => setFeedbackSubmitted(false)}
                                  variant="outline"
                                  size="sm"
                                >
                                  Edit
                                </Button>
                              </div>
                            ) : (
                              <Button
                                onClick={handleSubmitCoordinatorFeedback}
                                disabled={submittingFeedback}
                                className="bg-blue-600 hover:bg-blue-700"
                              >
                                {submittingFeedback ? "Submitting..." : "Submit Feedback"}
                              </Button>
                            )}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Report Generation Section */}
                  <Card className="md:col-span-2">
                    <CardHeader>
                      <CardTitle>Training Report Generation</CardTitle>
                      <CardDescription>Generate comprehensive training report with all session data</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                          <h4 className="font-semibold text-blue-900 mb-2">Report Generation Workflow:</h4>
                          <ol className="list-decimal list-inside space-y-1 text-sm text-blue-800">
                            <li>Generate DOCX report with all session data</li>
                            <li>Download and edit the report offline (add photos, notes, etc.)</li>
                            <li>Upload the edited report as PDF</li>
                            <li>Report will be visible in Supervisor and Admin portals</li>
                          </ol>
                        </div>

                        <div className="space-y-3">
                          {/* Step 1: Generate DOCX */}
                          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div className="flex-1">
                              <h5 className="font-medium text-gray-900">Step 1: Generate DOCX Report</h5>
                              <p className="text-sm text-gray-600">Creates a Word document with all session data</p>
                            </div>
                            <Button
                              onClick={async () => {
                                if (!selectedSession) return;
                                setGeneratingDOCX(true);
                                try {
                                  await axiosInstance.post(`/training-reports/${selectedSession.id}/generate-docx`);
                                  toast.success("Report generated! Click download to get the file.");
                                  setProfessionalReportStatus({...professionalReportStatus, docx_generated: true});
                                } catch (error) {
                                  toast.error(error.response?.data?.detail || "Failed to generate report");
                                } finally {
                                  setGeneratingDOCX(false);
                                }
                              }}
                              disabled={generatingDOCX}
                              className="bg-blue-600 hover:bg-blue-700"
                            >
                              {generatingDOCX ? "Generating..." : "Generate DOCX"}
                            </Button>
                          </div>

                          {/* Step 2: Download DOCX */}
                          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div className="flex-1">
                              <h5 className="font-medium text-gray-900">Step 2: Download DOCX</h5>
                              <p className="text-sm text-gray-600">Download to edit offline</p>
                            </div>
                            <Button
                              onClick={async () => {
                                if (!selectedSession) return;
                                try {
                                  const response = await axiosInstance.get(
                                    `/training-reports/${selectedSession.id}/download-docx`,
                                    { responseType: 'blob' }
                                  );
                                  const url = window.URL.createObjectURL(new Blob([response.data]));
                                  const link = document.createElement('a');
                                  link.href = url;
                                  link.download = `Training_Report_${selectedSession.name.replace(/\s+/g, '_')}.docx`;
                                  document.body.appendChild(link);
                                  link.click();
                                  link.remove();
                                  window.URL.revokeObjectURL(url);
                                  toast.success("Report downloaded!");
                                } catch (error) {
                                  toast.error("Failed to download report");
                                }
                              }}
                              variant="outline"
                            >
                              <Download className="w-4 h-4 mr-2" />
                              Download DOCX
                            </Button>
                          </div>

                          {/* Step 3: Upload Final PDF */}
                          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div className="flex-1">
                              <h5 className="font-medium text-gray-900">Step 3: Upload Final PDF</h5>
                              <p className="text-sm text-gray-600">After editing, upload the final PDF version</p>
                            </div>
                            <div>
                              <input
                                id={`upload-report-pdf-${selectedSession?.id}`}
                                type="file"
                                accept=".pdf"
                                className="hidden"
                                onChange={async (e) => {
                                  const file = e.target.files?.[0];
                                  if (!file || !selectedSession) return;
                                  
                                  if (!file.name.toLowerCase().endsWith('.pdf')) {
                                    toast.error("Please upload a PDF file");
                                    return;
                                  }

                                  setUploadingEdited(true);
                                  try {
                                    const formData = new FormData();
                                    formData.append('file', file);
                                    
                                    await axiosInstance.post(
                                      `/training-reports/${selectedSession.id}/upload-final-pdf`,
                                      formData,
                                      { headers: { 'Content-Type': 'multipart/form-data' } }
                                    );
                                    
                                    // Reload completion checklist to update status
                                    await loadCompletionChecklist(selectedSession.id);
                                    
                                    toast.success("✓ Final report uploaded successfully! You can now mark the training as completed.");
                                    setProfessionalReportStatus({
                                      ...professionalReportStatus,
                                      pdf_submitted: true
                                    });
                                  } catch (error) {
                                    console.error("Upload error:", error);
                                    toast.error(error.response?.data?.detail || "Failed to upload report");
                                  } finally {
                                    setUploadingEdited(false);
                                  }
                                  e.target.value = null;
                                }}
                              />
                              <Button 
                                variant="outline" 
                                disabled={uploadingEdited}
                                onClick={() => document.getElementById(`upload-report-pdf-${selectedSession?.id}`)?.click()}
                              >
                                <Upload className="w-4 h-4 mr-2" />
                                {uploadingEdited ? "Uploading..." : "Upload PDF"}
                              </Button>
                            </div>
                          </div>

                          {professionalReportStatus.pdf_submitted && (
                            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                              <p className="text-blue-800 font-medium">✓ Final report uploaded successfully!</p>
                              <p className="text-sm text-blue-700 mt-1">You can now mark the training as completed below.</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Mark as Completed Section - Shows after PDF submission */}
                  {professionalReportStatus.pdf_submitted && (
                    <Card className="bg-blue-50 border-blue-200">
                      <CardContent className="pt-6">
                        <div className="text-center space-y-4">
                          <div>
                            <h4 className="font-semibold text-blue-900 text-lg">Complete Training & Archive</h4>
                            <p className="text-sm text-blue-800">
                              Review the checklist below before marking this session as completed.
                            </p>
                          </div>
                          
                          {selectedSession?.completion_status === 'completed' ? (
                            <div className="bg-green-100 border border-green-400 rounded-lg p-3">
                              <p className="text-green-900 font-semibold">✓ Training Marked as Completed</p>
                              <p className="text-green-700 text-sm">
                                This session has been archived and moved to Past Training records.
                              </p>
                              {selectedSession?.completed_date && (
                                <p className="text-green-600 text-xs mt-1">
                                  Completed on: {new Date(selectedSession.completed_date).toLocaleString()}
                                </p>
                              )}
                            </div>
                          ) : (
                            <>
                              {/* Completion Checklist */}
                              {completionChecklist && (
                                <div className="bg-white rounded-lg p-4 text-left space-y-3 border border-blue-200">
                                  <h5 className="font-semibold text-gray-900 text-sm">Completion Checklist</h5>
                                  {Object.entries(completionChecklist.items || {}).map(([key, item]) => (
                                    <div key={key} className="flex items-start gap-3">
                                      <div className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center ${
                                        item.completed ? 'bg-green-500' : 'bg-gray-300'
                                      }`}>
                                        {item.completed && (
                                          <CheckCircle className="w-3 h-3 text-white" />
                                        )}
                                      </div>
                                      <div className="flex-1">
                                        <p className={`text-sm font-medium ${
                                          item.completed ? 'text-green-900' : 'text-gray-700'
                                        }`}>
                                          {item.label}
                                          {item.required && <span className="text-red-500 ml-1">*</span>}
                                        </p>
                                      </div>
                                    </div>
                                  ))}
                                  
                                  {!completionChecklist.can_complete && (
                                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mt-3">
                                      <p className="text-amber-900 text-xs">
                                        ⚠️ Please complete all required items before marking as completed
                                      </p>
                                    </div>
                                  )}
                                </div>
                              )}
                              
                              <Button
                                onClick={handleMarkSessionCompleted}
                                disabled={markingCompleted || !completionChecklist?.can_complete}
                                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                              >
                                {markingCompleted ? (
                                  <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                    Marking as Completed...
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle className="w-4 h-4 mr-2" />
                                    {completionChecklist?.can_complete 
                                      ? "Mark Training as Completed" 
                                      : "Complete Checklist to Continue"}
                                  </>
                                )}
                              </Button>
                            </>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}

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
                              <div className="flex justify-between items-start">
                                <div className="flex-1">
                                  <div className="flex items-center gap-3 mb-2">
                                    <div>
                                      <h3 className="font-semibold text-lg text-gray-900">{session.company_name || 'Unknown Company'}</h3>
                                      <p className="text-base text-gray-700">{session.program_name || 'Unknown Program'}</p>
                                    </div>
                                    <Badge variant="secondary" className="text-xs">
                                      {session.completion_status === 'completed' ? 'Completed' : 'Archived'}
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
                                    style={{ backgroundColor: primaryColor }}
                                  >
                                    <BarChart3 className="w-4 h-4" />
                                    Results
                                  </Button>
                                </div>
                              </div>
                              
                              {expandedPastSession?.id === session.id && (
                                <div className="mt-4 pt-4 border-t space-y-2">
                                  <div className="grid grid-cols-2 gap-4 text-sm">
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
              <MyEarnings 
                userId={user.id} 
                userRoles={[user.role, ...(user.additional_roles || [])]}
              />
            </TabsContent>

          </Tabs>
        )}
      </main>

      {/* Edit Session Dialog */}
      <Dialog open={editSessionDialogOpen} onOpenChange={setEditSessionDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Session</DialogTitle>
            <DialogDescription>Update session details</DialogDescription>
          </DialogHeader>
          {editingSession && (
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
              <Button onClick={handleUpdateSession} className="w-full">
                Update Session
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Add Participant Dialog */}
      <Dialog open={addParticipantDialogOpen} onOpenChange={setAddParticipantDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Participant to Session</DialogTitle>
            <DialogDescription>
              Add a new participant to {selectedSession?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="p-name">Full Name *</Label>
              <Input
                id="p-name"
                value={newParticipant.full_name}
                onChange={(e) => setNewParticipant({ ...newParticipant, full_name: e.target.value })}
                placeholder="John Doe"
              />
            </div>
            <div>
              <Label htmlFor="p-id">ID Number * (will be used as login ID)</Label>
              <Input
                id="p-id"
                value={newParticipant.id_number}
                onChange={(e) => setNewParticipant({ ...newParticipant, id_number: e.target.value })}
                placeholder="990101-01-1234"
              />
            </div>
            <div>
              <Label htmlFor="p-email">Email (optional)</Label>
              <Input
                id="p-email"
                type="email"
                value={newParticipant.email}
                onChange={(e) => setNewParticipant({ ...newParticipant, email: e.target.value })}
                placeholder="john@example.com (optional)"
              />
            </div>
            <div>
              <Label htmlFor="p-phone">Phone Number (optional)</Label>
              <Input
                id="p-phone"
                type="tel"
                value={newParticipant.phone_number}
                onChange={(e) => setNewParticipant({ ...newParticipant, phone_number: e.target.value })}
                placeholder="+60123456789 (optional)"
              />
            </div>
            <p className="text-xs text-gray-500 bg-blue-50 p-2 rounded">
              💡 Default login: IC number / password: mddrc1
            </p>
            <Button onClick={handleAddParticipant} className="w-full" style={{ backgroundColor: primaryColor }}>
              Add Participant
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CoordinatorDashboard;
