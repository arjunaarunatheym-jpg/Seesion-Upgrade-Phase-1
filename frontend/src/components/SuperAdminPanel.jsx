import { useState, useEffect } from "react";
import { axiosInstance } from "../App";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { toast } from "sonner";
import { ChevronDown, ChevronRight, Clock, CheckCircle, XCircle, Edit, Car, ClipboardList, MessageSquare, FileText, User, Upload, X, RefreshCw } from "lucide-react";

const SuperAdminPanel = () => {
  const [sessions, setSessions] = useState([]);
  const [expandedSessions, setExpandedSessions] = useState({});
  const [expandedParticipants, setExpandedParticipants] = useState({});
  const [loading, setLoading] = useState(false);

  // Dialog states
  const [clockInOutDialog, setClockInOutDialog] = useState({ open: false, participant: null, sessionId: null });
  const [vehicleDialog, setVehicleDialog] = useState({ open: false, participant: null, sessionId: null });
  const [testDialog, setTestDialog] = useState({ open: false, participant: null, sessionId: null, testType: null });
  const [checklistDialog, setChecklistDialog] = useState({ open: false, participant: null, sessionId: null });
  const [feedbackDialog, setFeedbackDialog] = useState({ open: false, participant: null, sessionId: null });

  // Form states
  const [clockForm, setClockForm] = useState({ clockIn: "", clockOut: "" });
  const [vehicleForm, setVehicleForm] = useState({ vehicle_model: "", registration_number: "", roadtax_expiry: "" });
  const [testForm, setTestForm] = useState({ score: "" });
  const [checklistForm, setChecklistForm] = useState({ interval: "pre", items: [] });
  const [checklistTemplate, setChecklistTemplate] = useState(null);
  const [feedbackForm, setFeedbackForm] = useState({ responses: [] });
  const [feedbackTemplate, setFeedbackTemplate] = useState(null);
  
  // Score calculator state
  const [scoreCalculator, setScoreCalculator] = useState({ correct: "", total: "" });
  
  // Program pass percentage (fetched when opening test dialog)
  const [programPassPercentage, setProgramPassPercentage] = useState(70);

  useEffect(() => {
    loadActiveSessions();
  }, []);

  const loadActiveSessions = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get("/sessions");
      const today = new Date();
      const activeSessions = response.data.filter(s => {
        const endDate = new Date(s.end_date);
        return endDate >= today || s.status === "active";
      });
      setSessions(activeSessions);
    } catch (error) {
      toast.error("Failed to load sessions");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadSessionParticipants = async (sessionId) => {
    try {
      // Use the new optimized endpoint that returns ALL data in ONE call
      const response = await axiosInstance.get(`/sessions/${sessionId}/participants/enriched`);
      return response.data;
    } catch (error) {
      console.error("Failed to load participants:", error);
      return [];
    }
  };

  const toggleSessionExpand = async (sessionId) => {
    if (expandedSessions[sessionId]) {
      setExpandedSessions(prev => ({ ...prev, [sessionId]: null }));
    } else {
      const participants = await loadSessionParticipants(sessionId);
      setExpandedSessions(prev => ({ ...prev, [sessionId]: participants }));
    }
  };

  const refreshParticipant = async (sessionId, participantId) => {
    const participants = await loadSessionParticipants(sessionId);
    setExpandedSessions(prev => ({ ...prev, [sessionId]: participants }));
  };

  const toggleParticipantExpand = (participantId) => {
    setExpandedParticipants(prev => ({
      ...prev,
      [participantId]: !prev[participantId]
    }));
  };

  // Handle Clock In/Out - Keep dialog open and refresh status
  const handleClockInOut = async () => {
    try {
      const { participant, sessionId } = clockInOutDialog;
      
      if (clockForm.clockIn) {
        // Extract time without timezone conversion - keep it as selected
        const clockInDate = new Date(clockForm.clockIn);
        const clockInTime = `${String(clockInDate.getHours()).padStart(2, '0')}:${String(clockInDate.getMinutes()).padStart(2, '0')}:00`;
        
        await axiosInstance.post("/super-admin/attendance/clock-in", {
          session_id: sessionId,
          participant_id: participant.id,
          clock_in: `${clockInDate.toISOString().split('T')[0]}T${clockInTime}+08:00`
        });
      }
      
      if (clockForm.clockOut) {
        // Extract time without timezone conversion - keep it as selected
        const clockOutDate = new Date(clockForm.clockOut);
        const clockOutTime = `${String(clockOutDate.getHours()).padStart(2, '0')}:${String(clockOutDate.getMinutes()).padStart(2, '0')}:00`;
        
        await axiosInstance.post("/super-admin/attendance/clock-out", {
          session_id: sessionId,
          participant_id: participant.id,
          clock_out: `${clockOutDate.toISOString().split('T')[0]}T${clockOutTime}+08:00`
        });
      }
      
      toast.success("Attendance updated successfully");
      
      // Refresh participant data
      await refreshParticipant(sessionId, participant.id);
      
      // Clear form and close dialog after successful submission
      setClockForm({ clockIn: "", clockOut: "" });
      setClockInOutDialog({ open: false, participant: null, sessionId: null });
    } catch (error) {
      toast.error("Failed to update attendance");
      console.error(error);
    }
  };

  // Handle Vehicle Details
  const handleVehicleSubmit = async () => {
    try {
      const { participant, sessionId } = vehicleDialog;
      
      if (!vehicleForm.vehicle_model || !vehicleForm.registration_number || !vehicleForm.roadtax_expiry) {
        toast.error("Please fill in all vehicle details");
        return;
      }
      
      await axiosInstance.post("/super-admin/vehicle-details", {
        session_id: sessionId,
        participant_id: participant.id,
        vehicle_model: vehicleForm.vehicle_model,
        registration_number: vehicleForm.registration_number,
        roadtax_expiry: vehicleForm.roadtax_expiry
      });
      
      toast.success("Vehicle details saved");
      
      await refreshParticipant(sessionId, participant.id);
      setVehicleForm({ vehicle_model: "", registration_number: "", roadtax_expiry: "" });
      
      // Close dialog after successful submission
      setVehicleDialog({ open: false, participant: null, sessionId: null });
    } catch (error) {
      toast.error("Failed to save vehicle details");
      console.error(error);
    }
  };

  // Open Test Dialog and fetch program pass percentage
  const openTestDialog = async (participant, sessionId, testType, existingScore) => {
    try {
      console.log("Opening test dialog for session:", sessionId);
      
      // Fetch session to get program_id
      const sessionRes = await axiosInstance.get(`/sessions/${sessionId}`);
      const programId = sessionRes.data.program_id;
      console.log("Session program_id:", programId);
      
      // Fetch ALL programs and find the matching one
      const programsRes = await axiosInstance.get('/programs');
      console.log("All programs:", programsRes.data.map(p => ({ id: p.id, name: p.name, pass: p.pass_percentage })));
      
      const program = programsRes.data.find(p => p.id === programId);
      console.log("Found program:", program);
      
      const passPercentage = program?.pass_percentage || 70;
      console.log("Setting pass percentage to:", passPercentage);
      setProgramPassPercentage(passPercentage);
      
      // Set dialog state
      setTestDialog({ open: true, participant, sessionId, testType });
      
      // Pre-fill score if exists
      if (existingScore !== undefined && existingScore !== null) {
        setTestForm({ score: existingScore.toString() });
        toast.info(`Editing existing ${testType}-test`, { duration: 2000 });
      } else {
        setTestForm({ score: "" });
      }
      setScoreCalculator({ correct: "", total: "" });
    } catch (error) {
      console.error("Failed to fetch program pass percentage:", error);
      // Default to 70% if fetch fails
      setProgramPassPercentage(70);
      setTestDialog({ open: true, participant, sessionId, testType });
      setTestForm({ score: existingScore?.toString() || "" });
      setScoreCalculator({ correct: "", total: "" });
    }
  };

  // Handle Test Submission - Update badge immediately
  const handleTestSubmit = async () => {
    try {
      const { participant, sessionId, testType } = testDialog;
      const score = parseFloat(testForm.score);
      
      if (isNaN(score) || score < 0 || score > 100) {
        toast.error("Please enter a valid score between 0-100");
        return;
      }
      
      const sessionRes = await axiosInstance.get(`/sessions/${sessionId}`);
      const program = sessionRes.data;
      
      const testsRes = await axiosInstance.get(`/tests/program/${program.program_id}`);
      const test = testsRes.data.find(t => t.test_type === testType);
      
      if (!test) {
        toast.error(`No ${testType}-test found for this program`);
        return;
      }
      
      const totalQuestions = test.questions.length;
      const correctAnswersNeeded = Math.round((score / 100) * totalQuestions);
      
      const answers = test.questions.map((q, index) => {
        if (index < correctAnswersNeeded) {
          return q.correct_answer;
        } else {
          const wrongOptions = [0, 1, 2, 3].filter(opt => opt !== q.correct_answer);
          return wrongOptions[0];
        }
      });
      
      await axiosInstance.post("/tests/super-admin-submit", {
        test_id: test.id,
        session_id: sessionId,
        participant_id: participant.id,
        answers: answers
      });
      
      toast.success(`${testType === 'pre' ? 'Pre' : 'Post'}-test submitted with ${score}% (${correctAnswersNeeded}/${totalQuestions} correct)`);
      
      // Refresh participant to update badge
      await refreshParticipant(sessionId, participant.id);
      
      setTestForm({ score: "" });
      setScoreCalculator({ correct: "", total: "" });
      
      // Close dialog after successful submission
      setTestDialog({ open: false, participant: null, sessionId: null, testType: null });
    } catch (error) {
      toast.error("Failed to submit test");
      console.error(error);
    }
  };

  // Load Checklist Template
  const loadChecklistTemplate = async (sessionId) => {
    try {
      const sessionRes = await axiosInstance.get(`/sessions/${sessionId}`);
      const templatesRes = await axiosInstance.get("/checklist-templates");
      const template = templatesRes.data.find(t => t.program_id === sessionRes.data.program_id);
      
      if (!template) {
        toast.error("No checklist template found");
        return null;
      }
      
      return template;
    } catch (error) {
      console.error(error);
      return null;
    }
  };

  // Handle Checklist Dialog Open
  const openChecklistDialog = async (participant, sessionId) => {
    const template = await loadChecklistTemplate(sessionId);
    if (template) {
      setChecklistTemplate(template);
      
      // Check if checklist already exists for this participant
      try {
        const existingRes = await axiosInstance.get(`/vehicle-checklists/${sessionId}/${participant.id}`);
        const existingChecklist = existingRes.data;
        
        if (existingChecklist && existingChecklist.checklist_items) {
          // Pre-fill form with existing data for editing
          setChecklistForm({
            items: existingChecklist.checklist_items.map(item => ({
              item: item.item,
              status: item.status || "good",
              comments: item.comments || "",
              image: item.photo_url || null
            }))
          });
          toast.info("Editing existing checklist", { duration: 2000 });
        } else {
          // No existing checklist, create fresh form from template
          setChecklistForm({
            items: template.items.map(item => ({ item, status: "good", comments: "", image: null }))
          });
        }
      } catch (error) {
        // No existing checklist found, create fresh form from template
        setChecklistForm({
          items: template.items.map(item => ({ item, status: "good", comments: "", image: null }))
        });
      }
      
      setChecklistDialog({ open: true, participant, sessionId });
    }
  };

  // Handle Checklist Item Status Change
  const updateChecklistItemStatus = (index, status) => {
    setChecklistForm(prev => ({
      ...prev,
      items: prev.items.map((item, i) => 
        i === index ? { ...item, status } : item
      )
    }));
  };
  
  // Handle Checklist Comments Change
  const updateChecklistItemComments = (index, comments) => {
    setChecklistForm(prev => ({
      ...prev,
      items: prev.items.map((item, i) => 
        i === index ? { ...item, comments } : item
      )
    }));
  };

  // Handle Checklist Image Upload
  const handleChecklistImageUpload = (index, event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setChecklistForm(prev => ({
          ...prev,
          items: prev.items.map((item, i) => 
            i === index ? { ...item, image: reader.result } : item
          )
        }));
      };
      reader.readAsDataURL(file);
    }
  };

  // Handle Checklist Submission
  const handleChecklistSubmit = async () => {
    try {
      const { participant, sessionId } = checklistDialog;
      
      // Validate: needs_repair items must have comments
      for (let i = 0; i < checklistForm.items.length; i++) {
        if (checklistForm.items[i].status === "needs_repair" && !checklistForm.items[i].comments.trim()) {
          toast.error(`Please add repair details for: ${checklistForm.items[i].item}`);
          return;
        }
      }
      
      await axiosInstance.post("/super-admin/checklist/submit", {
        session_id: sessionId,
        participant_id: participant.id,
        checklist_items: checklistForm.items.map(item => ({
          item: item.item,
          status: item.status,
          comments: item.comments,
          photo_url: item.image || ""
        }))
      });
      
      toast.success("Checklist submitted successfully");
      
      await refreshParticipant(sessionId, participant.id);
      
      // Reset form and close dialog after successful submission
      if (checklistTemplate) {
        setChecklistForm({
          items: checklistTemplate.items.map(item => ({ item, status: "good", comments: "", image: null }))
        });
      }
      
      setChecklistDialog({ open: false, participant: null, sessionId: null });
    } catch (error) {
      toast.error("Failed to submit checklist");
      console.error(error);
    }
  };

  // Load Feedback Template
  const loadFeedbackTemplate = async (sessionId) => {
    try {
      const sessionRes = await axiosInstance.get(`/sessions/${sessionId}`);
      const templatesRes = await axiosInstance.get(`/feedback-templates/program/${sessionRes.data.program_id}`);
      
      if (!templatesRes.data || !templatesRes.data.questions) {
        toast.error("No feedback template found");
        return null;
      }
      
      return templatesRes.data;
    } catch (error) {
      console.error(error);
      return null;
    }
  };

  // Handle Feedback Dialog Open
  const openFeedbackDialog = async (participant, sessionId) => {
    const template = await loadFeedbackTemplate(sessionId);
    if (template) {
      setFeedbackTemplate(template);
      
      // Check if feedback already exists for this participant
      try {
        const feedbackRes = await axiosInstance.get(`/feedback/session/${sessionId}`);
        const existingFeedback = feedbackRes.data.find(f => f.participant_id === participant.id);
        
        if (existingFeedback && existingFeedback.responses) {
          // Pre-fill form with existing feedback responses
          setFeedbackForm({
            responses: template.questions.map(q => {
              const existingResponse = existingFeedback.responses.find(r => r.question === q.question);
              return {
                question: q.question,
                response: existingResponse ? existingResponse.response : ""
              };
            })
          });
          toast.info("Editing existing feedback", { duration: 2000 });
        } else {
          // No existing feedback, create fresh form from template
          setFeedbackForm({
            responses: template.questions.map(q => ({ question: q.question, response: "" }))
          });
        }
      } catch (error) {
        // No existing feedback found, create fresh form from template
        setFeedbackForm({
          responses: template.questions.map(q => ({ question: q.question, response: "" }))
        });
      }
      
      setFeedbackDialog({ open: true, participant, sessionId });
    }
  };

  // Handle Feedback Response Change
  const handleFeedbackResponseChange = (index, value) => {
    setFeedbackForm(prev => ({
      responses: prev.responses.map((r, i) => 
        i === index ? { ...r, response: value } : r
      )
    }));
  };

  // Handle Feedback Submission
  const handleFeedbackSubmit = async () => {
    try {
      const { participant, sessionId } = feedbackDialog;
      
      await axiosInstance.post("/super-admin/feedback/submit", {
        session_id: sessionId,
        participant_id: participant.id,
        responses: feedbackForm.responses
      });
      
      toast.success("Feedback submitted successfully");
      
      await refreshParticipant(sessionId, participant.id);
      
      // Reset form and close dialog after successful submission
      if (feedbackTemplate) {
        setFeedbackForm({
          responses: feedbackTemplate.questions.map(q => ({ question: q.question, response: "" }))
        });
      }
      
      setFeedbackDialog({ open: false, participant: null, sessionId: null });
    } catch (error) {
      toast.error("Failed to submit feedback");
      console.error(error);
    }
  };

  const getStatusBadge = (status) => {
    if (status && status.completed) {
      return status.passed !== undefined ? (
        status.passed ? (
          <Badge className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" /> Passed ({status.score}%)</Badge>
        ) : (
          <Badge className="bg-red-500"><XCircle className="w-3 h-3 mr-1" /> Failed ({status.score}%)</Badge>
        )
      ) : (
        <Badge className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" /> Completed</Badge>
      );
    }
    return <Badge variant="outline"><Clock className="w-3 h-3 mr-1" /> Pending</Badge>;
  };

  // Download template functions
  const downloadTemplate = async (type) => {
    try {
      const response = await axiosInstance.get(`/templates/${type}`, {
        responseType: 'blob'
      });
      
      const filename = {
        'pre-post-assessment': 'PrePost_Assessment_Template.xlsx',
        'feedback': 'Feedback_Template.xlsx',
        'checklist': 'Vehicle_Checklist_Template.xlsx'
      }[type];
      
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      window.URL.revokeObjectURL(url);
      
      toast.success(`${filename} downloaded!`);
    } catch (error) {
      toast.error("Failed to download template");
      console.error(error);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="bg-gradient-to-r from-purple-600 to-pink-600 text-white">
          <CardTitle className="flex items-center">
            🔐 Super Admin - Quick Testing Panel
          </CardTitle>
          <CardDescription className="text-purple-100">
            Fill in participant data exactly as they would. Dialogs stay open so you can continue working. Click refresh icon to update status.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Excel Templates Download Section */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Download Excel Templates (Master Files)
          </CardTitle>
          <CardDescription>
            Save these templates locally. Use as reference to quickly restore your data after redeployment.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Program Configuration Templates */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
              📋 Program Configuration (Questions & Items)
            </h4>
            <p className="text-xs text-gray-500 mb-3">
              Templates for program setup - test questions, feedback questions, checklist items
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <Button 
                variant="outline" 
                className="h-auto py-3 flex flex-col items-center gap-1 hover:bg-blue-50 hover:border-blue-400"
                onClick={() => downloadTemplate('program-test-questions')}
              >
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                  <FileText className="w-4 h-4 text-blue-600" />
                </div>
                <span className="font-semibold text-sm">Test Questions</span>
                <span className="text-xs text-gray-500">Pre/Post test setup</span>
              </Button>
              
              <Button 
                variant="outline" 
                className="h-auto py-3 flex flex-col items-center gap-1 hover:bg-green-50 hover:border-green-400"
                onClick={() => downloadTemplate('program-feedback-questions')}
              >
                <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-green-600" />
                </div>
                <span className="font-semibold text-sm">Feedback Questions</span>
                <span className="text-xs text-gray-500">Feedback form setup</span>
              </Button>
              
              <Button 
                variant="outline" 
                className="h-auto py-3 flex flex-col items-center gap-1 hover:bg-orange-50 hover:border-orange-400"
                onClick={() => downloadTemplate('program-checklist-items')}
              >
                <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center">
                  <ClipboardList className="w-4 h-4 text-orange-600" />
                </div>
                <span className="font-semibold text-sm">Checklist Items</span>
                <span className="text-xs text-gray-500">Vehicle inspection setup</span>
              </Button>
            </div>
          </div>

          <div className="border-t pt-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
              👥 Participant Data Templates
            </h4>
            <p className="text-xs text-gray-500 mb-3">
              Templates for participant records - scores, feedback responses, inspection results
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <Button 
                variant="outline" 
                className="h-auto py-3 flex flex-col items-center gap-1 hover:bg-blue-50 hover:border-blue-400"
                onClick={() => downloadTemplate('pre-post-assessment')}
              >
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                  <FileText className="w-4 h-4 text-blue-600" />
                </div>
                <span className="font-semibold text-sm">Assessment Scores</span>
                <span className="text-xs text-gray-500">Participant test results</span>
              </Button>
              
              <Button 
                variant="outline" 
                className="h-auto py-3 flex flex-col items-center gap-1 hover:bg-green-50 hover:border-green-400"
                onClick={() => downloadTemplate('feedback')}
              >
                <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-green-600" />
                </div>
                <span className="font-semibold text-sm">Feedback Responses</span>
                <span className="text-xs text-gray-500">Participant feedback</span>
              </Button>
              
              <Button 
                variant="outline" 
                className="h-auto py-3 flex flex-col items-center gap-1 hover:bg-orange-50 hover:border-orange-400"
                onClick={() => downloadTemplate('checklist')}
              >
                <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center">
                  <ClipboardList className="w-4 h-4 text-orange-600" />
                </div>
                <span className="font-semibold text-sm">Checklist Results</span>
                <span className="text-xs text-gray-500">Inspection records</span>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="text-center py-8">Loading active sessions...</div>
      ) : sessions.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-gray-500">
            <p className="text-lg">No active sessions found</p>
            <p className="text-sm mt-2">Create a session in the Sessions tab to get started</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => (
            <Card key={session.id} className="overflow-hidden">
              <CardHeader 
                className="cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => toggleSessionExpand(session.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {expandedSessions[session.id] ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                    <div>
                      <CardTitle className="text-lg">{session.company_name} - {session.program_name}</CardTitle>
                      <CardDescription>
                        {session.start_date} to {session.end_date} • {session.location} • {session.participant_ids?.length || 0} participants
                      </CardDescription>
                    </div>
                  </div>
                  <Badge variant={expandedSessions[session.id] ? "default" : "outline"}>
                    {expandedSessions[session.id] ? "Expanded" : "Click to expand"}
                  </Badge>
                </div>
              </CardHeader>

              {expandedSessions[session.id] && (
                <CardContent className="pt-0">
                  <div className="space-y-2">
                    {expandedSessions[session.id].map((participant) => (
                      <Card key={participant.id} className="bg-gray-50">
                        <CardHeader 
                          className="cursor-pointer hover:bg-gray-100 transition-colors py-3"
                          onClick={() => toggleParticipantExpand(participant.id)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {expandedParticipants[participant.id] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                              <User className="w-4 h-4" />
                              <div>
                                <p className="font-semibold">{participant.full_name}</p>
                                <p className="text-sm text-gray-600">IC: {participant.id_number}</p>
                              </div>
                            </div>
                            <div className="flex gap-2 items-center">
                              {getStatusBadge(participant.preTest)}
                              {getStatusBadge(participant.postTest)}
                              {getStatusBadge(participant.checklist)}
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  refreshParticipant(session.id, participant.id);
                                  toast.success("Status refreshed");
                                }}
                                title="Refresh status"
                              >
                                <RefreshCw className="w-4 h-4" />
                              </Button>
                            </div>
                          </div>
                        </CardHeader>

                        {expandedParticipants[participant.id] && (
                          <CardContent className="grid grid-cols-2 md:grid-cols-3 gap-3 pt-0">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={async () => {
                                setClockInOutDialog({ open: true, participant, sessionId: session.id });
                                // Load existing attendance data to pre-fill form
                                try {
                                  const response = await axiosInstance.get(`/attendance/${session.id}/${participant.id}`);
                                  if (response.data && response.data.length > 0) {
                                    const attendance = response.data[0];
                                    // Convert HH:MM:SS format to datetime-local format for input
                                    const today = new Date().toISOString().split('T')[0];
                                    const clockInValue = attendance.clock_in ? `${today}T${attendance.clock_in.substring(0, 5)}` : "";
                                    const clockOutValue = attendance.clock_out ? `${today}T${attendance.clock_out.substring(0, 5)}` : "";
                                    setClockForm({ 
                                      clockIn: clockInValue, 
                                      clockOut: clockOutValue 
                                    });
                                  } else {
                                    setClockForm({ clockIn: "", clockOut: "" });
                                  }
                                } catch (error) {
                                  console.error("Failed to load attendance:", error);
                                  setClockForm({ clockIn: "", clockOut: "" });
                                }
                              }}
                              className={`flex items-center gap-2 ${
                                participant.clockedIn ? 'bg-green-100 hover:bg-green-200 border-green-400' : 'bg-red-100 hover:bg-red-200 border-red-400'
                              }`}
                            >
                              <Clock className="w-4 h-4" />
                              Clock In/Out
                            </Button>

                            <Button
                              variant="outline"
                              size="sm"
                              onClick={async () => {
                                setVehicleDialog({ open: true, participant, sessionId: session.id });
                                // Load existing vehicle data
                                try {
                                  const response = await axiosInstance.get(`/vehicle-details/${session.id}/${participant.id}`);
                                  if (response.data) {
                                    setVehicleForm({
                                      vehicle_model: response.data.vehicle_model || "",
                                      registration_number: response.data.registration_number || "",
                                      roadtax_expiry: response.data.roadtax_expiry || ""
                                    });
                                  } else {
                                    setVehicleForm({ vehicle_model: "", registration_number: "", roadtax_expiry: "" });
                                  }
                                } catch (error) {
                                  console.error("Failed to load vehicle data:", error);
                                  setVehicleForm({ vehicle_model: "", registration_number: "", roadtax_expiry: "" });
                                }
                              }}
                              className={`flex items-center gap-2 ${
                                participant.vehicleDetails ? 'bg-green-100 hover:bg-green-200 border-green-400' : 'bg-red-100 hover:bg-red-200 border-red-400'
                              }`}
                            >
                              <Car className="w-4 h-4" />
                              Vehicle
                            </Button>

                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openTestDialog(
                                participant, 
                                session.id, 
                                "pre", 
                                participant.preTest?.score
                              )}
                              className={`flex items-center gap-2 ${
                                participant.preTest ? 'bg-green-100 hover:bg-green-200 border-green-400' : 'bg-red-100 hover:bg-red-200 border-red-400'
                              }`}
                            >
                              <FileText className="w-4 h-4" />
                              Pre-Test
                            </Button>

                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openTestDialog(
                                participant, 
                                session.id, 
                                "post", 
                                participant.postTest?.score
                              )}
                              className={`flex items-center gap-2 ${
                                participant.postTest ? 'bg-green-100 hover:bg-green-200 border-green-400' : 'bg-red-100 hover:bg-red-200 border-red-400'
                              }`}
                            >
                              <FileText className="w-4 h-4" />
                              Post-Test
                            </Button>

                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openChecklistDialog(participant, session.id)}
                              className={`flex items-center gap-2 ${
                                participant.checklist ? 'bg-green-100 hover:bg-green-200 border-green-400' : 'bg-red-100 hover:bg-red-200 border-red-400'
                              }`}
                            >
                              <ClipboardList className="w-4 h-4" />
                              Checklist
                            </Button>

                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openFeedbackDialog(participant, session.id)}
                              className={`flex items-center gap-2 ${
                                participant.feedback ? 'bg-green-100 hover:bg-green-200 border-green-400' : 'bg-red-100 hover:bg-red-200 border-red-400'
                              }`}
                            >
                              <MessageSquare className="w-4 h-4" />
                              Feedback
                            </Button>
                          </CardContent>
                        )}
                      </Card>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Clock In/Out Dialog - Stays Open */}
      <Dialog open={clockInOutDialog.open} onOpenChange={(open) => !open && setClockInOutDialog({ open: false, participant: null, sessionId: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clock In/Out - {clockInOutDialog.participant?.full_name}</DialogTitle>
            <DialogDescription>Set attendance times. Dialog stays open so you can edit again.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Clock In Time</Label>
              <Input
                type="datetime-local"
                value={clockForm.clockIn}
                onChange={(e) => setClockForm({ ...clockForm, clockIn: e.target.value })}
              />
            </div>
            <div>
              <Label>Clock Out Time</Label>
              <Input
                type="datetime-local"
                value={clockForm.clockOut}
                onChange={(e) => setClockForm({ ...clockForm, clockOut: e.target.value })}
              />
            </div>
            <Button onClick={handleClockInOut} className="w-full">
              Save Attendance (Stays Open)
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Vehicle Dialog */}
      <Dialog open={vehicleDialog.open} onOpenChange={(open) => !open && setVehicleDialog({ open: false, participant: null, sessionId: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Vehicle Details - {vehicleDialog.participant?.full_name}</DialogTitle>
            <DialogDescription>Enter vehicle information. Dialog stays open.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Vehicle Model</Label>
              <Input
                value={vehicleForm.vehicle_model}
                onChange={(e) => setVehicleForm({ ...vehicleForm, vehicle_model: e.target.value })}
                placeholder="Toyota Vios"
              />
            </div>
            <div>
              <Label>Registration Number (Plate Number)</Label>
              <Input
                value={vehicleForm.registration_number}
                onChange={(e) => setVehicleForm({ ...vehicleForm, registration_number: e.target.value })}
                placeholder="ABC1234"
              />
            </div>
            <div>
              <Label>Road Tax Expiry Date</Label>
              <Input
                type="date"
                value={vehicleForm.roadtax_expiry}
                onChange={(e) => setVehicleForm({ ...vehicleForm, roadtax_expiry: e.target.value })}
              />
            </div>
            <Button onClick={handleVehicleSubmit} className="w-full">
              Save Vehicle Details
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Test Dialog - Score Calculator with Auto-Percentage */}
      <Dialog open={testDialog.open} onOpenChange={(open) => !open && setTestDialog({ open: false, participant: null, sessionId: null, testType: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {testDialog.testType === 'pre' ? 'Pre' : 'Post'}-Test - {testDialog.participant?.full_name}
            </DialogTitle>
            <DialogDescription>
              Enter exact score (correct answers out of total) or percentage directly.
              <span className="block mt-1 font-semibold text-orange-600">Pass Mark: {programPassPercentage}%</span>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* Score Calculator */}
            <div className="bg-gray-50 p-4 rounded-lg space-y-3">
              <Label className="font-semibold">Score Calculator</Label>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-sm text-gray-600">Correct Answers</Label>
                  <Input
                    type="number"
                    min="0"
                    value={scoreCalculator.correct}
                    onChange={(e) => {
                      const correct = e.target.value;
                      setScoreCalculator(prev => ({ ...prev, correct }));
                      // Auto-calculate percentage if both values exist
                      if (correct && scoreCalculator.total && parseInt(scoreCalculator.total) > 0) {
                        const percentage = (parseInt(correct) / parseInt(scoreCalculator.total)) * 100;
                        setTestForm({ score: percentage.toFixed(1) });
                      }
                    }}
                    placeholder="36"
                  />
                </div>
                <div>
                  <Label className="text-sm text-gray-600">Total Questions</Label>
                  <Input
                    type="number"
                    min="1"
                    value={scoreCalculator.total}
                    onChange={(e) => {
                      const total = e.target.value;
                      setScoreCalculator(prev => ({ ...prev, total }));
                      // Auto-calculate percentage if both values exist
                      if (scoreCalculator.correct && total && parseInt(total) > 0) {
                        const percentage = (parseInt(scoreCalculator.correct) / parseInt(total)) * 100;
                        setTestForm({ score: percentage.toFixed(1) });
                      }
                    }}
                    placeholder="40"
                  />
                </div>
              </div>
              
              {/* Result Display */}
              {scoreCalculator.correct && scoreCalculator.total && parseInt(scoreCalculator.total) > 0 && (
                <div className={`text-center p-3 rounded-lg ${
                  (parseInt(scoreCalculator.correct) / parseInt(scoreCalculator.total)) * 100 >= programPassPercentage 
                    ? 'bg-green-100 border-2 border-green-400' 
                    : 'bg-red-100 border-2 border-red-400'
                }`}>
                  <p className={`text-2xl font-bold ${
                    (parseInt(scoreCalculator.correct) / parseInt(scoreCalculator.total)) * 100 >= programPassPercentage 
                      ? 'text-green-700' 
                      : 'text-red-700'
                  }`}>
                    {((parseInt(scoreCalculator.correct) / parseInt(scoreCalculator.total)) * 100).toFixed(1)}%
                  </p>
                  <p className="text-sm text-gray-600">
                    {scoreCalculator.correct} / {scoreCalculator.total} correct answers
                  </p>
                  <p className={`text-xs font-semibold mt-1 ${
                    (parseInt(scoreCalculator.correct) / parseInt(scoreCalculator.total)) * 100 >= programPassPercentage 
                      ? 'text-green-600' 
                      : 'text-red-600'
                  }`}>
                    {(parseInt(scoreCalculator.correct) / parseInt(scoreCalculator.total)) * 100 >= programPassPercentage ? '✓ PASS' : '✗ FAIL'} (Pass Mark: {programPassPercentage}%)
                  </p>
                </div>
              )}
            </div>
            
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-muted-foreground">Or enter percentage directly</span>
              </div>
            </div>
            
            <div>
              <Label>Score (%)</Label>
              <Input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={testForm.score}
                onChange={(e) => {
                  setTestForm({ score: e.target.value });
                  // Clear calculator when manually entering percentage
                  setScoreCalculator({ correct: "", total: "" });
                }}
                placeholder="85"
                className={`text-lg font-semibold ${
                  testForm.score && parseFloat(testForm.score) >= programPassPercentage ? 'border-green-400 bg-green-50' : 
                  testForm.score && parseFloat(testForm.score) < programPassPercentage ? 'border-red-400 bg-red-50' : ''
                }`}
              />
              {testForm.score && (
                <p className={`text-sm font-semibold mt-1 ${
                  parseFloat(testForm.score) >= programPassPercentage ? 'text-green-600' : 'text-red-600'
                }`}>
                  {parseFloat(testForm.score) >= programPassPercentage ? `✓ PASS (≥${programPassPercentage}%)` : `✗ FAIL (<${programPassPercentage}%)`}
                </p>
              )}
            </div>
            <Button onClick={handleTestSubmit} className="w-full">
              Submit Test (Badge Updates)
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Checklist Dialog - Same as Trainer Portal */}
      <Dialog open={checklistDialog.open} onOpenChange={(open) => !open && setChecklistDialog({ open: false, participant: null, sessionId: null })} className="max-w-2xl">
        <DialogContent className="max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Checklist - {checklistDialog.participant?.full_name}</DialogTitle>
            <DialogDescription>Select status for each item. Upload pictures if needed. Same as trainer portal.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-3">
              {checklistForm.items.map((item, index) => (
                <Card key={index} className="p-3">
                  <div className="space-y-3">
                    <Label className="text-sm font-semibold">{item.item}</Label>
                    
                    <div>
                      <Label className="text-xs text-gray-600">Status:</Label>
                      <RadioGroup value={item.status} onValueChange={(val) => updateChecklistItemStatus(index, val)} className="flex gap-4 mt-2">
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="good" id={`good-${index}`} />
                          <Label htmlFor={`good-${index}`} className="text-sm cursor-pointer">✓ Good</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="satisfactory" id={`sat-${index}`} />
                          <Label htmlFor={`sat-${index}`} className="text-sm cursor-pointer">~ Satisfactory</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="needs_repair" id={`repair-${index}`} />
                          <Label htmlFor={`repair-${index}`} className="text-sm cursor-pointer">✗ Needs Repair</Label>
                        </div>
                      </RadioGroup>
                    </div>
                    
                    {item.status === "needs_repair" && (
                      <div>
                        <Label className="text-xs text-gray-600">Repair Details (Required):</Label>
                        <Textarea
                          value={item.comments}
                          onChange={(e) => updateChecklistItemComments(index, e.target.value)}
                          placeholder="Describe what needs to be repaired..."
                          rows={2}
                          className="mt-1"
                        />
                      </div>
                    )}
                    
                    <div>
                      {item.image ? (
                        <div className="relative inline-block">
                          <img src={item.image} alt="Checklist" className="w-32 h-32 object-cover rounded" />
                          <Button
                            size="sm"
                            variant="destructive"
                            className="absolute top-1 right-1 h-6 w-6 p-0"
                            onClick={() => {
                              setChecklistForm(prev => ({
                                ...prev,
                                items: prev.items.map((it, i) => 
                                  i === index ? { ...it, image: null } : it
                                )
                              }));
                            }}
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      ) : (
                        <label className="cursor-pointer">
                          <div className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800">
                            <Upload className="w-4 h-4" />
                            Upload Picture (Optional)
                          </div>
                          <input
                            type="file"
                            accept="image/*"
                            className="hidden"
                            onChange={(e) => handleChecklistImageUpload(index, e)}
                          />
                        </label>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
            <Button onClick={handleChecklistSubmit} className="w-full">
              Submit Checklist (Badge Updates)
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Feedback Dialog */}
      <Dialog open={feedbackDialog.open} onOpenChange={(open) => !open && setFeedbackDialog({ open: false, participant: null, sessionId: null })} className="max-w-2xl">
        <DialogContent className="max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Feedback - {feedbackDialog.participant?.full_name}</DialogTitle>
            <DialogDescription>Fill in feedback form. Dialog stays open.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {feedbackTemplate?.questions.map((question, index) => (
              <div key={index}>
                <Label>{question.question}</Label>
                {question.type === 'rating' ? (
                  <Select 
                    value={feedbackForm.responses[index]?.response} 
                    onValueChange={(val) => handleFeedbackResponseChange(index, val)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select rating" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">⭐ 1 Star</SelectItem>
                      <SelectItem value="2">⭐⭐ 2 Stars</SelectItem>
                      <SelectItem value="3">⭐⭐⭐ 3 Stars</SelectItem>
                      <SelectItem value="4">⭐⭐⭐⭐ 4 Stars</SelectItem>
                      <SelectItem value="5">⭐⭐⭐⭐⭐ 5 Stars</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Textarea
                    value={feedbackForm.responses[index]?.response}
                    onChange={(e) => handleFeedbackResponseChange(index, e.target.value)}
                    placeholder="Enter your response..."
                    rows={3}
                  />
                )}
              </div>
            ))}
            <Button onClick={handleFeedbackSubmit} className="w-full">
              Submit Feedback
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SuperAdminPanel;