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
import { ReportTab } from "../components/coordinator/ReportTab";
import { AnalyticsTab } from "../components/coordinator/AnalyticsTab";
import { PastTrainingTab } from "../components/coordinator/PastTrainingTab";

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
        loadTrainingReport(session.id),
        loadReportStatus(session.id)
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

  // Load report status when session changes
  const loadReportStatus = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/training-reports/${sessionId}/status`);
      setProfessionalReportStatus(response.data);
    } catch (error) {
      console.error("Failed to load report status:", error);
      setProfessionalReportStatus({
        docx_generated: false,
        edited_uploaded: false,
        pdf_submitted: false,
        docx_filename: null,
        edited_docx_filename: null,
        pdf_filename: null
      });
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
    if (!professionalReportStatus?.docx_generated) {
      toast.error("Please generate the report first before downloading");
      return;
    }
    
    try {
      const response = await axiosInstance.get(`/training-reports/${selectedSession.id}/download-docx`, {
        responseType: 'blob'
      });
      
      // Check if the response is actually an error (JSON instead of blob)
      if (response.data.type === 'application/json') {
        const text = await response.data.text();
        const error = JSON.parse(text);
        toast.error(error.detail || "Failed to download report");
        return;
      }
      
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
      // Reload status in case it's out of sync
      await loadReportStatus(selectedSession.id);
      
      if (error.response?.status === 404) {
        toast.error("Report file not found. Please regenerate the report.");
        setProfessionalReportStatus(prev => ({ ...prev, docx_generated: false }));
      } else {
        toast.error("Failed to download report. Please try again.");
      }
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


  const [activeTab, setActiveTab] = useState("sessions");

  // Function to navigate to Analytics tab with a specific session
  const handleSelectSessionForReport = async (session) => {
    await selectSession(session);
    setActiveTab("analytics");
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
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="flex flex-wrap w-full h-auto justify-start gap-2 bg-gray-100 p-2 rounded-lg sm:grid sm:grid-cols-6">
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
              <ManagementTab
                selectedSession={selectedSession}
                participants={participants}
                attendance={attendance}
                testResults={testResults}
                sessionAccess={sessionAccess}
                allChecklists={allChecklists}
                checklistIssues={checklistIssues}
                certificateStatuses={certificateStatuses}
                uploadingCertificates={uploadingCertificates}
                attendanceStatus={attendanceStatus}
                updatingAttendance={updatingAttendance}
                uploading={uploading}
                uploadDialogOpen={uploadDialogOpen}
                setUploadDialogOpen={setUploadDialogOpen}
                primaryColor={primaryColor}
                handleBulkUpload={handleBulkUpload}
                handleToggleAccess={handleToggleAccess}
                handleMarkAttendance={handleMarkAttendance}
                handleCertificateUpload={handleCertificateUpload}
                setEditingSession={setEditingSession}
                setEditSessionDialogOpen={setEditSessionDialogOpen}
                setAddParticipantDialogOpen={setAddParticipantDialogOpen}
              />
            </TabsContent>

            {/* Tab 3: Training Report */}
            <TabsContent value="report">
              <ReportTab
                selectedSession={selectedSession}
                trainingReport={trainingReport}
                setTrainingReport={setTrainingReport}
                aiGeneratedReport={aiGeneratedReport}
                setAiGeneratedReport={setAiGeneratedReport}
                professionalReportStatus={professionalReportStatus}
                generatingDOCX={generatingDOCX}
                uploadingEdited={uploadingEdited}
                submittingFinal={submittingFinal}
                generatingReport={generatingReport}
                primaryColor={primaryColor}
                handlePhotoUpload={handlePhotoUpload}
                handleGenerateProfessionalReport={handleGenerateProfessionalReport}
                handleDownloadDOCX={handleDownloadDOCX}
                handleUploadEditedDOCX={handleUploadEditedDOCX}
                handleSubmitFinalReport={handleSubmitFinalReport}
                handleGenerateAIReport={handleGenerateAIReport}
                handleSaveReport={handleSaveReport}
              />
            </TabsContent>

            {/* Tab 4: Analytics */}
            <TabsContent value="analytics">
              <AnalyticsTab
                selectedSession={selectedSession}
                stats={stats}
                participants={participants}
                testResults={testResults}
                attendance={attendance}
                courseFeedback={courseFeedback}
                coordinatorFeedbackTemplate={coordinatorFeedbackTemplate}
                coordinatorFeedback={coordinatorFeedback}
                setCoordinatorFeedback={setCoordinatorFeedback}
                feedbackSubmitted={feedbackSubmitted}
                setFeedbackSubmitted={setFeedbackSubmitted}
                submittingFeedback={submittingFeedback}
                professionalReportStatus={professionalReportStatus}
                setProfessionalReportStatus={setProfessionalReportStatus}
                generatingDOCX={generatingDOCX}
                setGeneratingDOCX={setGeneratingDOCX}
                uploadingEdited={uploadingEdited}
                setUploadingEdited={setUploadingEdited}
                completionChecklist={completionChecklist}
                loadCompletionChecklist={loadCompletionChecklist}
                handleSubmitCoordinatorFeedback={handleSubmitCoordinatorFeedback}
                handleMarkAsCompleted={handleMarkSessionCompleted}
              />
            </TabsContent>

            {/* Past Training Tab */}
            <TabsContent value="past-training">
              <PastTrainingTab
                selectedMonth={selectedMonth}
                setSelectedMonth={setSelectedMonth}
                selectedYear={selectedYear}
                setSelectedYear={setSelectedYear}
                pastTrainingSessions={pastTrainingSessions}
                setPastTrainingSessions={setPastTrainingSessions}
                loadingPastTraining={loadingPastTraining}
                expandedPastSession={expandedPastSession}
                setExpandedPastSession={setExpandedPastSession}
                primaryColor={primaryColor}
                loadPastTraining={loadPastTraining}
                handlePastSessionClick={handlePastSessionClick}
                generateMonthOptions={generateMonthOptions}
                generateYearOptions={generateYearOptions}
              />
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
