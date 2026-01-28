import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { LogOut, FileText, ClipboardCheck, MessageSquare, Award, Play, Users, Clock, Download, Eye, Settings, Lock, AlertTriangle, Shield, Globe } from "lucide-react";
import { FaFacebook, FaInstagram, FaTiktok, FaYoutube, FaTwitter, FaLinkedin } from 'react-icons/fa';
import IndemnityForm from "../components/IndemnityForm";

// Tab Components
import { OverviewTab } from "../components/participant/OverviewTab";
import { CertificatesTab } from "../components/participant/CertificatesTab";
import { DetailsTab } from "../components/participant/DetailsTab";
import { TestsTab } from "../components/participant/TestsTab";
import { ChecklistsTab } from "../components/participant/ChecklistsTab";
import { SettingsTab } from "../components/participant/SettingsTab";

// Helper function to render social media icon
const SocialIcon = ({ icon, className = "" }) => {
  const iconClass = `text-2xl ${className}`;
  switch(icon) {
    case 'facebook': return <FaFacebook className={`${iconClass} text-[#1877F2]`} />;
    case 'instagram': return <FaInstagram className={`${iconClass} text-[#E4405F]`} />;
    case 'tiktok': return <FaTiktok className={`${iconClass} text-black`} />;
    case 'youtube': return <FaYoutube className={`${iconClass} text-[#FF0000]`} />;
    case 'twitter': return <FaTwitter className={`${iconClass} text-[#1DA1F2]`} />;
    case 'linkedin': return <FaLinkedin className={`${iconClass} text-[#0A66C2]`} />;
    default: return <Globe className={`w-6 h-6 text-gray-500 ${className}`} />;
  }
};

const ParticipantDashboard = ({ user, onLogout, onUserUpdate }) => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [testResults, setTestResults] = useState([]);
  const [checklists, setChecklists] = useState([]);
  const [availableTests, setAvailableTests] = useState([]);
  const [participantAccess, setParticipantAccess] = useState({});
  const [vehicleDetails, setVehicleDetails] = useState({});
  const [attendanceToday, setAttendanceToday] = useState({});
  const [vehicleForm, setVehicleForm] = useState({
    vehicle_model: "",
    registration_number: "",
    roadtax_expiry: ""
  });
  
  // First-time login states
  const [showVerificationDialog, setShowVerificationDialog] = useState(false);
  const [showIndemnityDialog, setShowIndemnityDialog] = useState(false);
  const [verificationData, setVerificationData] = useState({ 
    full_name: "", 
    id_number: "",
    contact_email: "",
    contact_phone: ""
  });
  const [activeTab, setActiveTab] = useState("overview");
  const [companySettings, setCompanySettings] = useState({});
  const [currentTrainingSession, setCurrentTrainingSession] = useState(null);
  const [showSocialPopup, setShowSocialPopup] = useState(false);
  const [socialMediaLinks, setSocialMediaLinks] = useState([]);
  
  // Tab restrictions removed - all tabs accessible

  useEffect(() => {
    // Check if first-time login (not verified) - explicitly check for true
    if (user.profile_verified === true && user.indemnity_accepted === true) {
      // Already verified, just load data
      loadData();
    } else {
      // First time login, show verification
      setVerificationData({
        full_name: user.full_name || "",
        id_number: user.id_number || "",
        contact_email: user.contact_email || "",
        contact_phone: user.contact_phone || ""
      });
      setShowVerificationDialog(true);
    }
    
    // Check if returning from feedback submission
    const justSubmittedFeedback = sessionStorage.getItem('feedbackSubmitted');
    if (justSubmittedFeedback) {
      sessionStorage.removeItem('feedbackSubmitted');
      // Force multiple reloads to ensure data is updated
      setTimeout(() => loadData(), 500);
      setTimeout(() => loadData(), 1500);
      setTimeout(() => loadData(), 3000);
      // Show social media popup after feedback (if not dismissed before)
      if (!user.social_popup_dismissed) {
        setTimeout(() => setShowSocialPopup(true), 2000);
      }
    }
  }, [user.profile_verified, user.indemnity_accepted, user.social_popup_dismissed]);
  
  // Also reload when component becomes visible (tab focus)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        loadData();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const loadData = async () => {
    try {
      // Load data with individual error handling
      const sessionsRes = await axiosInstance.get("/sessions").catch(() => ({ data: [] }));
      const certsRes = await axiosInstance.get(`/certificates/participant/${user.id}`).catch(() => ({ data: [] }));
      const resultsRes = await axiosInstance.get(`/tests/results/participant/${user.id}`).catch(() => ({ data: [] }));
      const checklistsRes = await axiosInstance.get(`/checklists/participant/${user.id}`).catch(() => ({ data: [] }));
      
      setSessions(sessionsRes.data);
      setCertificates(certsRes.data);
      setTestResults(resultsRes.data);
      setChecklists(checklistsRes.data);
      
      // Load available tests and access for each session
      if (sessionsRes.data.length > 0) {
        loadAvailableTests(sessionsRes.data);
        loadParticipantAccess(sessionsRes.data);
        
        // Load vehicle details and attendance for each session
        const firstSession = sessionsRes.data[0];
        await loadVehicleDetails(firstSession.id);
        await loadAttendanceToday(firstSession.id);
        
        sessionsRes.data.forEach(session => {
          if (session.id !== firstSession.id) {
            loadVehicleDetails(session.id);
            loadAttendanceToday(session.id);
          }
        });
      }
    } catch (error) {
      console.error("Dashboard load error:", error);
      toast.error("Failed to load dashboard data");
    }
  };

  const loadParticipantAccess = async (sessionsList) => {
    try {
      // Add timestamp to prevent caching
      const timestamp = new Date().getTime();
      const accessPromises = sessionsList.map(session =>
        axiosInstance.get(`/participant-access/${session.id}?_t=${timestamp}`)
          .then(res => ({ [session.id]: res.data }))
          .catch(() => ({ [session.id]: {} }))
      );
      const accessArrays = await Promise.all(accessPromises);
      const allAccess = accessArrays.reduce((acc, curr) => ({ ...acc, ...curr }), {});
      setParticipantAccess(allAccess);
    } catch (error) {
      console.error("Failed to load participant access");
    }
  };

  const loadAvailableTests = async (sessionsList) => {
    try {
      const testsPromises = sessionsList.map(session =>
        axiosInstance.get(`/sessions/${session.id}/tests/available`)
          .then(res => res.data.map(test => ({ ...test, session_id: session.id, session_name: session.name })))
          .catch(() => [])
      );
      const testsArrays = await Promise.all(testsPromises);
      const allTests = testsArrays.flat();
      setAvailableTests(allTests);
    } catch (error) {
      console.error("Failed to load available tests");
    }
  };

  const handleTakeTest = (testId, sessionId) => {
    navigate(`/take-test/${testId}/${sessionId}`);
  };

  const handleViewResult = (resultId) => {
    navigate(`/test-results/${resultId}`);
  };

  const handleFeedback = (sessionId) => {
    navigate(`/feedback/${sessionId}`);
  };
  
  const handleRefreshStatus = async () => {
    toast.info("Refreshing...", { duration: 1000 });
    // Force a hard reload to get completely fresh data
    window.location.reload();
  };

  const handleDownloadCertificate = async (sessionId) => {
    try {
      const response = await axiosInstance.post(`/certificates/generate/${sessionId}/${user.id}`);
      const certificateUrl = response.data.certificate_url;
      
      // Fetch the PDF as blob
      const pdfResponse = await axiosInstance.get(certificateUrl, {
        responseType: 'blob'
      });
      
      // Create blob with proper MIME type
      const blob = new Blob([pdfResponse.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      
      // Create download link
      const link = document.createElement('a');
      link.href = url;
      link.download = `certificate_${sessionId}.pdf`;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
      
      toast.success("Certificate downloaded! Check your Downloads folder.");
    } catch (error) {
      console.error('Download error:', error);
      toast.error(error.response?.data?.detail || "Failed to download certificate");
    }
  };

  const handleDownloadExistingCertificate = async (cert) => {
    try {
      // Fetch the PDF as blob
      const pdfResponse = await axiosInstance.get(cert.certificate_url, {
        responseType: 'blob'
      });
      
      // Create blob with proper MIME type
      const blob = new Blob([pdfResponse.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      
      // Create download link
      const link = document.createElement('a');
      link.href = url;
      link.download = `certificate_${cert.session_id}.pdf`;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
      
      toast.success("Certificate downloaded! Check your Downloads folder.");
    } catch (error) {
      console.error('Download error:', error);
      toast.error("Failed to download certificate");
    }
  };

  const handlePreviewCertificate = async (sessionId) => {
    try {
      // First generate/get the certificate
      const response = await axiosInstance.post(`/certificates/generate/${sessionId}/${user.id}`);
      const certificateUrl = response.data.certificate_url;
      
      // Open PDF in new tab - simple and reliable
      window.open(`${process.env.REACT_APP_BACKEND_URL}${certificateUrl}`, '_blank');
      
      toast.success("Opening certificate...");
    } catch (error) {
      console.error('Preview error:', error);
      toast.error(error.response?.data?.detail || "Failed to preview certificate");
    }
  };

  const handlePreviewExistingCertificate = async (cert) => {
    try {
      // Open PDF in new tab - simple and reliable
      window.open(`${process.env.REACT_APP_BACKEND_URL}${cert.certificate_url}`, '_blank');
      
      toast.success("Opening certificate...");
    } catch (error) {
      console.error('Preview error:', error);
      toast.error("Failed to preview certificate");
    }
  };

  const handleVehicleSubmit = async (sessionId) => {
    if (!vehicleForm.vehicle_model || !vehicleForm.registration_number || !vehicleForm.roadtax_expiry) {
      toast.error("Please fill in all vehicle details");
      return;
    }

    try {
      await axiosInstance.post("/vehicle-details/submit", {
        session_id: sessionId,
        ...vehicleForm
      });
      toast.success("Vehicle details saved!");
      loadVehicleDetails(sessionId);
      setVehicleForm({ vehicle_model: "", registration_number: "", roadtax_expiry: "" });
    } catch (error) {
      toast.error("Failed to save vehicle details");
    }
  };

  const loadVehicleDetails = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/vehicle-details/${sessionId}/${user.id}`);
      if (response.data) {
        setVehicleDetails(prev => ({ ...prev, [sessionId]: response.data }));
      }
    } catch (error) {
      console.error("Failed to load vehicle details");
    }
  };

  const loadAttendanceToday = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/attendance/${sessionId}/${user.id}`);
      if (response.data && response.data.length > 0) {
        // Get Malaysian date for comparison (UTC+8)
        const malaysiaOffset = 8 * 60; // UTC+8 in minutes
        const now = new Date();
        const malaysiaTime = new Date(now.getTime() + (malaysiaOffset + now.getTimezoneOffset()) * 60000);
        const today = malaysiaTime.toISOString().split('T')[0];
        
        // First try to find today's attendance record
        let attendanceRecord = response.data.find(a => a.date === today);
        
        // If no record for today, check if there's any existing record for this session
        // This handles cases where super admin set attendance on a different date
        // or timezone differences caused date mismatch
        if (!attendanceRecord && response.data.length > 0) {
          // Get the most recent record (sort by date descending)
          const sortedRecords = [...response.data].sort((a, b) => 
            new Date(b.date || 0) - new Date(a.date || 0)
          );
          attendanceRecord = sortedRecords[0];
        }
        
        if (attendanceRecord) {
          setAttendanceToday(prev => ({
            ...prev,
            [sessionId]: {
              clock_in: attendanceRecord.clock_in_time || attendanceRecord.clock_in,
              clock_out: attendanceRecord.clock_out_time || attendanceRecord.clock_out
            }
          }));
        }
      }
    } catch (error) {
      console.error("Failed to load attendance");
    }
  };

  const handleClockIn = async (sessionId) => {
    try {
      await axiosInstance.post("/attendance/clock-in", { session_id: sessionId });
      toast.success("Clocked in successfully!");
      // Reload attendance to get the exact time
      await loadAttendanceToday(sessionId);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to clock in");
    }
  };

  const handleClockOut = async (sessionId) => {
    try {
      await axiosInstance.post("/attendance/clock-out", { session_id: sessionId });
      toast.success("Clocked out successfully!");
      // Reload attendance to get the exact time
      await loadAttendanceToday(sessionId);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to clock out");
    }
  };

  // Handle profile verification
  const handleVerification = async () => {
    if (!verificationData.full_name.trim() || !verificationData.id_number.trim()) {
      toast.error("Please fill in both name and IC number");
      return;
    }
    
    try {
      // Update user profile with verified name, IC, and contact details
      await axiosInstance.put("/users/profile", {
        full_name: verificationData.full_name.trim(),
        id_number: verificationData.id_number.trim(),
        contact_email: verificationData.contact_email.trim(),
        contact_phone: verificationData.contact_phone.trim()
      });
      
      setShowVerificationDialog(false);
      setShowIndemnityDialog(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to verify profile");
    }
  };

  // Handle indemnity form acceptance (new enhanced form)
  const handleIndemnityAccept = async (formData) => {
    try {
      // Mark profile as verified and indemnity accepted with signature data
      await axiosInstance.put("/users/profile", {
        profile_verified: true,
        indemnity_accepted: true,
        indemnity_accepted_at: new Date().toISOString(),
        indemnity_signature: `Digitally signed by ${formData.signed_name}`,
        indemnity_signed_name: formData.signed_name,
        indemnity_signed_ic: formData.signed_ic,
        indemnity_signed_date: formData.signed_date,
        // Enhanced fields
        indemnity_sections_accepted: formData.sections_accepted,
        indemnity_training_id: formData.training_id,
        indemnity_trainer_name: formData.trainer_name,
        indemnity_vehicle_reg: formData.vehicle_reg,
        indemnity_locked: true  // Lock the record after submission
      });
      
      setShowIndemnityDialog(false);
      
      // Update user state if callback provided
      if (onUserUpdate) {
        onUserUpdate({ 
          ...user, 
          profile_verified: true, 
          indemnity_accepted: true,
          indemnity_signed_name: formData.signed_name,
          indemnity_signed_ic: formData.signed_ic,
          indemnity_signed_date: formData.signed_date,
          indemnity_locked: true
        });
      }
      
      toast.success("Welcome! Your indemnity form has been signed and locked.");
      
      // Redirect to My Details tab after indemnity submission
      setActiveTab("details");
      
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to accept indemnity");
      throw error;  // Re-throw so the form knows submission failed
    }
  };

  // Load company settings
  useEffect(() => {
    const loadCompanySettings = async () => {
      try {
        const response = await axiosInstance.get("/finance/company-settings");
        setCompanySettings(response.data);
        // Load active social media links
        const activeLinks = (response.data.social_media_links || []).filter(l => l.is_active);
        setSocialMediaLinks(activeLinks);
      } catch (error) {
        console.log("Could not load company settings");
      }
    };
    loadCompanySettings();
  }, []);

  // Handle social popup dismiss
  const handleDismissSocialPopup = async (dontShowAgain) => {
    setShowSocialPopup(false);
    if (dontShowAgain) {
      try {
        await axiosInstance.put("/users/profile", { social_popup_dismissed: true });
      } catch (error) {
        console.log("Could not save preference");
      }
    }
  };

  // Trigger social popup after feedback (called from feedback submission)
  const triggerSocialPopupAfterFeedback = () => {
    if (!user.social_popup_dismissed && socialMediaLinks.length > 0) {
      setTimeout(() => setShowSocialPopup(true), 1000);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-teal-50 to-cyan-50">
      {/* Verification Dialog - First Time Login */}
      <Dialog open={showVerificationDialog} onOpenChange={() => {}}>
        <DialogContent className="sm:max-w-md" onPointerDownOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-600" />
              Verify Your Details
            </DialogTitle>
            <DialogDescription>
              Please verify your information and provide your contact details.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="verify-name">Full Name (as per IC) *</Label>
              <Input
                id="verify-name"
                value={verificationData.full_name}
                onChange={(e) => setVerificationData({ ...verificationData, full_name: e.target.value })}
                placeholder="Enter your full name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="verify-ic">IC Number *</Label>
              <Input
                id="verify-ic"
                value={verificationData.id_number}
                onChange={(e) => setVerificationData({ ...verificationData, id_number: e.target.value })}
                placeholder="e.g., 901231-14-5678"
              />
            </div>
            <div className="border-t pt-4 mt-4">
              <p className="text-sm text-gray-600 mb-3">Your Contact Information (for official communications)</p>
              <div className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="verify-email">Personal Email</Label>
                  <Input
                    id="verify-email"
                    type="email"
                    value={verificationData.contact_email}
                    onChange={(e) => setVerificationData({ ...verificationData, contact_email: e.target.value })}
                    placeholder="your.email@example.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="verify-phone">Phone Number</Label>
                  <Input
                    id="verify-phone"
                    type="tel"
                    value={verificationData.contact_phone}
                    onChange={(e) => setVerificationData({ ...verificationData, contact_phone: e.target.value })}
                    placeholder="e.g., 012-345 6789"
                  />
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={handleVerification} className="w-full">
              Verify & Continue
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Indemnity Form Dialog */}
      <Dialog open={showIndemnityDialog} onOpenChange={() => {}}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto" onPointerDownOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-600" />
              Indemnity & Waiver Form
            </DialogTitle>
            <DialogDescription>
              Please read and accept the indemnity form before proceeding.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            {/* This old indemnity content is replaced by IndemnityForm component */}
          </div>
        </DialogContent>
      </Dialog>

      {/* New Enhanced Indemnity Form */}
      <IndemnityForm
        open={showIndemnityDialog}
        onAccept={handleIndemnityAccept}
        participant={{
          ...user,
          company_name: sessions[0]?.company_name || null
        }}
        trainingSession={currentTrainingSession || (sessions.length > 0 ? {
          name: sessions[0]?.name,
          type: sessions[0]?.type,
          start_date: sessions[0]?.start_date,
          venue: sessions[0]?.venue,
          trainer_name: sessions[0]?.trainer_name
        } : null)}
        companySettings={companySettings}
      />

      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Participant Portal</h1>
            <p className="text-sm text-gray-600">Welcome, {user.full_name}</p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleRefreshStatus}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <Clock className="w-4 h-4" />
              <span className="hidden sm:inline">Refresh</span>
            </Button>
            <Button
              data-testid="participant-logout-button"
              onClick={onLogout}
              variant="outline"
              className="flex items-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="flex flex-wrap w-full mb-8 h-auto justify-start gap-2 bg-gray-100 p-2 rounded-lg md:grid md:grid-cols-5">
            <TabsTrigger value="overview" data-testid="overview-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <FileText className="w-4 h-4 mr-2" />
              <span className="text-sm">Overview</span>
            </TabsTrigger>
            <TabsTrigger value="details" data-testid="details-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <Users className="w-4 h-4 mr-2" />
              <span className="text-sm">My Details</span>
            </TabsTrigger>
            <TabsTrigger value="certificates" data-testid="certificates-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <Award className="w-4 h-4 mr-2" />
              <span className="text-sm">Certificates</span>
            </TabsTrigger>
            <TabsTrigger value="tests" data-testid="tests-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <ClipboardCheck className="w-4 h-4 mr-2" />
              <span className="text-sm">Tests</span>
            </TabsTrigger>
            <TabsTrigger value="checklists" data-testid="checklists-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <ClipboardCheck className="w-4 h-4 mr-2" />
              <span className="text-sm">Checklists</span>
            </TabsTrigger>
            <TabsTrigger value="settings" data-testid="settings-tab" className="flex-1 min-w-[120px] md:min-w-0">
              <Settings className="w-4 h-4 mr-2" />
              <span className="text-sm">Settings</span>
            </TabsTrigger>
          </TabsList>

          {/* Overview */}
          <TabsContent value="overview">
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
                <CardHeader>
                  <CardTitle className="text-blue-900">My Sessions</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-bold text-blue-900">{sessions.length}</p>
                </CardContent>
              </Card>
              <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
                <CardHeader>
                  <CardTitle className="text-green-900">Certificates</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-bold text-green-900">
                    {/* Count certificates from participant_access where certificate_url exists */}
                    {Object.values(participantAccess).filter(access => access.certificate_url).length}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
                <CardHeader>
                  <CardTitle className="text-purple-900">Tests Completed</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-bold text-purple-900">{testResults.length}</p>
                </CardContent>
              </Card>
            </div>

            <Card className="mt-6">
              <CardHeader>
                <CardTitle>My Training Sessions</CardTitle>
              </CardHeader>
              <CardContent>
                {sessions.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No sessions assigned yet</p>
                ) : (
                  <div className="space-y-3">
                    {sessions.map((session) => {
                      const access = participantAccess[session.id] || {};
                      const feedbackSubmitted = access.feedback_completed || false;
                      const canAccessFeedback = access.can_access_feedback || false;
                      
                      return (
                        <div
                          key={session.id}
                          data-testid={`participant-session-${session.id}`}
                          className="p-4 bg-gradient-to-r from-teal-50 to-cyan-50 rounded-lg border-2 border-teal-200"
                        >
                          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
                            <div className="flex-1">
                              <h3 className="font-semibold text-gray-900 text-base">{session.name}</h3>
                              <p className="text-sm text-gray-600 mt-1">Location: {session.location}</p>
                              <p className="text-sm text-gray-600">
                                {session.start_date} to {session.end_date}
                              </p>
                            </div>
                            <div className="flex flex-row sm:flex-col gap-2 flex-wrap">
                              {canAccessFeedback && !feedbackSubmitted && (
                                <Button
                                  size="sm"
                                  onClick={() => handleFeedback(session.id)}
                                  className="bg-yellow-600 hover:bg-yellow-700"
                                  data-testid={`feedback-button-${session.id}`}
                                >
                                  <MessageSquare className="w-4 h-4 mr-2" />
                                  Submit Feedback
                                </Button>
                              )}
                              {feedbackSubmitted && (
                                <span className="text-xs text-green-700 font-semibold">✓ Feedback Submitted</span>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Certificates */}
          <TabsContent value="certificates">
            <Card>
              <CardHeader>
                <CardTitle>My Certificates</CardTitle>
                <CardDescription>View and download your training certificates</CardDescription>
              </CardHeader>
              <CardContent>
                {sessions.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No sessions assigned yet</p>
                ) : (
                  <div className="space-y-4">
                    {sessions.map((session) => {
                      const access = participantAccess[session.id] || {};
                      const hasCertificate = access.certificate_url;
                      const feedbackSubmitted = access.feedback_completed;
                      const attendance = attendanceToday[session.id] || {};
                      const clockedOut = attendance.clock_out;
                      const sessionActive = session.status === 'active';
                      
                      const canDownload = hasCertificate && feedbackSubmitted && clockedOut && sessionActive;
                      
                      return (
                        <div
                          key={session.id}
                          data-testid={`certificate-${session.id}`}
                          className={`p-6 rounded-lg border ${
                            canDownload 
                              ? 'bg-green-50 border-green-200' 
                              : 'bg-gray-50 border-gray-200'
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex items-start gap-4">
                              <Award className={`w-10 h-10 ${canDownload ? 'text-green-600' : 'text-gray-400'}`} />
                              <div>
                                <h3 className="font-semibold text-gray-900 text-lg">{session.name}</h3>
                                <p className="text-sm text-gray-600 mt-1">
                                  {session.start_date} to {session.end_date}
                                </p>
                                <p className="text-sm text-gray-600">
                                  {session.location}
                                </p>
                                
                                {/* Status Indicators */}
                                <div className="flex flex-wrap gap-2 mt-3">
                                  {hasCertificate ? (
                                    <span className="px-2 py-1 rounded text-xs font-bold bg-blue-100 text-blue-800">
                                      ✓ Certificate Uploaded
                                    </span>
                                  ) : (
                                    <span className="px-2 py-1 rounded text-xs font-bold bg-gray-100 text-gray-600">
                                      Certificate Not Yet Uploaded
                                    </span>
                                  )}
                                  
                                  {feedbackSubmitted ? (
                                    <span className="px-2 py-1 rounded text-xs font-bold bg-purple-100 text-purple-800">
                                      ✓ Feedback Submitted
                                    </span>
                                  ) : (
                                    <span className="px-2 py-1 rounded text-xs font-bold bg-yellow-100 text-yellow-800">
                                      Feedback Required
                                    </span>
                                  )}
                                  
                                  {clockedOut ? (
                                    <span className="px-2 py-1 rounded text-xs font-bold bg-green-100 text-green-800">
                                      ✓ Clocked Out
                                    </span>
                                  ) : (
                                    <span className="px-2 py-1 rounded text-xs font-bold bg-yellow-100 text-yellow-800">
                                      Clock Out Required
                                    </span>
                                  )}
                                  
                                  {!sessionActive && (
                                    <span className="px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-800">
                                      Session Inactive
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            
                            {/* Download Button */}
                            <div>
                              {canDownload ? (
                                <Button
                                  onClick={async (e) => {
                                    const btn = e.currentTarget;
                                    const originalText = btn.innerHTML;
                                    btn.disabled = true;
                                    btn.innerHTML = '<span class="animate-spin mr-2">⏳</span> Downloading...';
                                    
                                    try {
                                      // Add timestamp to bust cache and get latest certificate
                                      const timestamp = new Date().getTime();
                                      const response = await axiosInstance.get(
                                        `/certificates/download/${session.id}/${user.id}?_t=${timestamp}`,
                                        { 
                                          responseType: 'blob',
                                          timeout: 60000, // 60 second timeout for large files
                                          headers: {
                                            'Cache-Control': 'no-cache',
                                            'Pragma': 'no-cache'
                                          }
                                        }
                                      );
                                      
                                      // Check if the response is actually a PDF (not an error)
                                      const contentType = response.headers['content-type'];
                                      if (contentType && contentType.includes('application/json')) {
                                        // Server returned JSON error, not a PDF
                                        const text = await response.data.text();
                                        const errorData = JSON.parse(text);
                                        toast.error(errorData.detail || "Failed to download certificate");
                                        return;
                                      }
                                      
                                      // Verify we got actual data
                                      if (!response.data || response.data.size === 0) {
                                        toast.error("Certificate file is empty. Please contact administrator.");
                                        return;
                                      }
                                      
                                      // Create blob and download
                                      const blob = new Blob([response.data], { type: 'application/pdf' });
                                      const url = window.URL.createObjectURL(blob);
                                      const link = document.createElement('a');
                                      link.href = url;
                                      link.download = `${user.full_name.replace(/ /g, '_')}_certificate.pdf`;
                                      document.body.appendChild(link);
                                      link.click();
                                      link.remove();
                                      window.URL.revokeObjectURL(url);
                                      toast.success("Certificate downloaded!");
                                    } catch (error) {
                                      console.error('Certificate download error:', error);
                                      // Handle blob error responses
                                      if (error.response?.data instanceof Blob) {
                                        try {
                                          const text = await error.response.data.text();
                                          const errorData = JSON.parse(text);
                                          toast.error(errorData.detail || "Failed to download certificate");
                                        } catch {
                                          toast.error("Failed to download certificate. Please try again.");
                                        }
                                      } else if (error.code === 'ECONNABORTED') {
                                        toast.error("Download timed out. Please try again.");
                                      } else {
                                        toast.error(error.response?.data?.detail || "Failed to download certificate. Please try again.");
                                      }
                                    } finally {
                                      btn.disabled = false;
                                      btn.innerHTML = originalText;
                                    }
                                  }}
                                  className="bg-green-600 hover:bg-green-700 text-white"
                                  data-testid={`download-cert-${session.id}`}
                                >
                                  <Download className="w-4 h-4 mr-2" />
                                  Download Certificate
                                </Button>
                              ) : (
                                <div className="text-right">
                                  <p className="text-sm font-medium text-gray-600 mb-2">Not Available Yet</p>
                                  <p className="text-xs text-gray-500">
                                    {!hasCertificate && "Certificate not uploaded by coordinator"}
                                    {hasCertificate && !feedbackSubmitted && "Submit feedback first"}
                                    {hasCertificate && feedbackSubmitted && !clockedOut && "Clock out first"}
                                    {hasCertificate && feedbackSubmitted && clockedOut && !sessionActive && "Session is inactive"}
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Social Media Section on Certificates Tab */}
            {socialMediaLinks.length > 0 && (
              <Card className="mt-4 bg-gradient-to-r from-pink-50 to-purple-50">
                <CardContent className="py-4">
                  <p className="text-center text-sm text-gray-700 mb-3">
                    🎉 Stay connected with us for more driving tips and updates!
                  </p>
                  <div className="flex justify-center gap-4">
                    {socialMediaLinks.map((link, index) => (
                      <a
                        key={index}
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex flex-col items-center gap-1 hover:scale-110 transition-transform p-2 bg-white rounded-lg shadow-sm"
                      >
                        <SocialIcon icon={link.icon} />
                        <span className="text-xs text-gray-600">{link.platform}</span>
                      </a>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* My Details */}
          <TabsContent value="details">
            {sessions.length === 0 ? (
              <Card>
                <CardHeader>
                  <CardTitle>My Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-500 text-center py-8">No sessions assigned yet</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-6">
                {sessions.map((session) => {
                  const vehicleInfo = vehicleDetails[session.id];
                  const attendance = attendanceToday[session.id] || {};
                  const access = participantAccess[session.id] || {};
                  const canClockOut = access.can_clock_out || false;

                  return (
                    <Card key={session.id}>
                      <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50">
                        <CardTitle>{session.name}</CardTitle>
                        <CardDescription>
                          {session.start_date} to {session.end_date} • {session.location}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="pt-6 space-y-6">
                        {/* Attendance */}
                        <div>
                          <h3 className="font-semibold text-gray-900 mb-3">Attendance</h3>
                          <div className="space-y-3">
                            {/* Clock In Checkbox */}
                            <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                              <input
                                type="checkbox"
                                id={`clock-in-${session.id}`}
                                checked={!!attendance.clock_in}
                                onChange={() => {
                                  if (!attendance.clock_in) {
                                    handleClockIn(session.id);
                                  }
                                }}
                                className="w-5 h-5 text-green-600 rounded focus:ring-2 focus:ring-green-500"
                                data-testid={`clock-in-${session.id}`}
                              />
                              <label htmlFor={`clock-in-${session.id}`} className="flex-1 cursor-pointer">
                                <span className="font-medium text-gray-900">Clock In</span>
                                {attendance.clock_in && (
                                  <span className="ml-2 text-sm text-green-600">
                                    ✓ Clocked in at {
                                      (() => {
                                        if (typeof attendance.clock_in === 'string') {
                                          // If it's in HH:MM:SS format, convert to 12-hour format
                                          const parts = attendance.clock_in.split(':');
                                          if (parts.length >= 2) {
                                            const hour = parseInt(parts[0]);
                                            const minute = parts[1];
                                            const ampm = hour >= 12 ? 'PM' : 'AM';
                                            const displayHour = hour % 12 || 12;
                                            return `${displayHour}:${minute} ${ampm}`;
                                          }
                                          // Try as ISO date
                                          const date = new Date(attendance.clock_in);
                                          return isNaN(date.getTime()) ? attendance.clock_in : date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
                                        }
                                        return 'today';
                                      })()
                                    }
                                  </span>
                                )}
                              </label>
                            </div>

                            {/* Clock Out Checkbox */}
                            <div className={`flex items-center gap-3 p-3 rounded-lg border ${
                              attendance.clock_in && canClockOut
                                ? 'bg-blue-50 border-blue-200' 
                                : 'bg-gray-100 border-gray-200 opacity-50'
                            }`}>
                              <input
                                type="checkbox"
                                id={`clock-out-${session.id}`}
                                checked={!!attendance.clock_out}
                                onChange={() => {
                                  if (attendance.clock_in && !attendance.clock_out && canClockOut) {
                                    handleClockOut(session.id);
                                  }
                                }}
                                disabled={!attendance.clock_in || !canClockOut}
                                className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                                data-testid={`clock-out-${session.id}`}
                              />
                              <label htmlFor={`clock-out-${session.id}`} className={`flex-1 ${attendance.clock_in && canClockOut ? 'cursor-pointer' : 'cursor-not-allowed'}`}>
                                <span className="font-medium text-gray-900">Clock Out</span>
                                {attendance.clock_out && (
                                  <span className="ml-2 text-sm text-blue-600">
                                    ✓ Clocked out at {
                                      (() => {
                                        if (typeof attendance.clock_out === 'string') {
                                          // If it's in HH:MM:SS format, convert to 12-hour format
                                          const parts = attendance.clock_out.split(':');
                                          if (parts.length >= 2) {
                                            const hour = parseInt(parts[0]);
                                            const minute = parts[1];
                                            const ampm = hour >= 12 ? 'PM' : 'AM';
                                            const displayHour = hour % 12 || 12;
                                            return `${displayHour}:${minute} ${ampm}`;
                                          }
                                          // Try as ISO date
                                          const date = new Date(attendance.clock_out);
                                          return isNaN(date.getTime()) ? attendance.clock_out : date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
                                        }
                                        return 'today';
                                      })()
                                    }
                                  </span>
                                )}
                                {!attendance.clock_in && (
                                  <span className="ml-2 text-xs text-gray-500">(Clock in first)</span>
                                )}
                                {attendance.clock_in && !canClockOut && !attendance.clock_out && (
                                  <span className="ml-2 text-xs text-orange-500">(Not yet released by coordinator)</span>
                                )}
                              </label>
                            </div>
                          </div>
                        </div>

                        {/* Vehicle Details */}
                        <div>
                          <h3 className="font-semibold text-gray-900 mb-3">Vehicle Details</h3>
                          {vehicleInfo ? (
                            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                <div>
                                  <p className="text-sm text-gray-600">Vehicle Model</p>
                                  <p className="font-medium">{vehicleInfo.vehicle_model}</p>
                                </div>
                                <div>
                                  <p className="text-sm text-gray-600">Registration No.</p>
                                  <p className="font-medium">{vehicleInfo.registration_number}</p>
                                </div>
                                <div>
                                  <p className="text-sm text-gray-600">Roadtax Expiry</p>
                                  <p className="font-medium">{vehicleInfo.roadtax_expiry}</p>
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="space-y-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                              <p className="text-sm text-yellow-800 mb-3">Please provide your vehicle details</p>
                              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                <div>
                                  <Label htmlFor="vehicle_model">Vehicle Model</Label>
                                  <Input
                                    id="vehicle_model"
                                    value={vehicleForm.vehicle_model}
                                    onChange={(e) => setVehicleForm({ ...vehicleForm, vehicle_model: e.target.value })}
                                    placeholder="e.g., Honda City"
                                    data-testid={`vehicle-model-${session.id}`}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="registration_number">Registration Number</Label>
                                  <Input
                                    id="registration_number"
                                    value={vehicleForm.registration_number}
                                    onChange={(e) => setVehicleForm({ ...vehicleForm, registration_number: e.target.value })}
                                    placeholder="e.g., ABC 1234"
                                    data-testid={`registration-${session.id}`}
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="roadtax_expiry">Roadtax Expiry</Label>
                                  <Input
                                    id="roadtax_expiry"
                                    type="date"
                                    value={vehicleForm.roadtax_expiry}
                                    onChange={(e) => setVehicleForm({ ...vehicleForm, roadtax_expiry: e.target.value })}
                                    data-testid={`roadtax-${session.id}`}
                                  />
                                </div>
                              </div>
                              <Button
                                onClick={() => handleVehicleSubmit(session.id)}
                                className="w-full"
                                data-testid={`submit-vehicle-${session.id}`}
                              >
                                Save Vehicle Details
                              </Button>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          {/* Tests */}
          <TabsContent value="tests">
            {/* Available Tests */}
            {availableTests.length > 0 && (
              <Card className="mb-6 bg-gradient-to-r from-emerald-50 to-teal-50 border-emerald-200">
                <CardHeader>
                  <CardTitle>Available Tests</CardTitle>
                  <CardDescription>Tests you need to complete</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {availableTests.map((test) => (
                      <div
                        key={`${test.id}-${test.session_id}`}
                        data-testid={`available-test-${test.id}`}
                        className="p-4 bg-white rounded-lg border-2 border-emerald-300"
                      >
                        <div className="flex justify-between items-center">
                          <div>
                            <h3 className="font-semibold text-gray-900">
                              {test.test_type === "pre" ? "Pre-Test" : "Post-Test"}
                            </h3>
                            <p className="text-sm text-gray-600">{test.session_name}</p>
                            <p className="text-sm text-gray-500 mt-1">
                              {test.questions.length} questions
                            </p>
                          </div>
                          <Button
                            onClick={() => handleTakeTest(test.id, test.session_id)}
                            data-testid={`take-test-${test.id}`}
                            className="bg-emerald-600 hover:bg-emerald-700"
                          >
                            <Play className="w-4 h-4 mr-2" />
                            Start Test
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Completed Tests */}
            <Card>
              <CardHeader>
                <CardTitle>Test Results</CardTitle>
                <CardDescription>View your completed test scores</CardDescription>
              </CardHeader>
              <CardContent>
                {testResults.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No test results yet</p>
                ) : (
                  <div className="space-y-3">
                    {testResults.map((result) => (
                      <div
                        key={result.id}
                        data-testid={`test-result-${result.id}`}
                        className={`p-4 rounded-lg cursor-pointer hover:shadow-md transition-shadow ${
                          result.passed
                            ? 'bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200'
                            : 'bg-gradient-to-r from-red-50 to-orange-50 border border-red-200'
                        }`}
                        onClick={() => handleViewResult(result.id)}
                      >
                        <div className="flex justify-between items-center">
                          <div>
                            <h3 className="font-semibold text-gray-900">
                              {result.test_type === "pre" ? "Pre-Test" : "Post-Test"}
                            </h3>
                            <p className="text-sm text-gray-600">
                              Submitted: {new Date(result.submitted_at).toLocaleDateString()}
                            </p>
                            <p className={`text-xs font-semibold mt-1 ${result.passed ? 'text-green-600' : 'text-red-600'}`}>
                              {result.passed ? "PASSED" : "FAILED"}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className={`text-3xl font-bold ${result.passed ? 'text-green-600' : 'text-red-600'}`}>
                              {result.score.toFixed(1)}%
                            </p>
                            <p className="text-sm text-gray-600">
                              {result.correct_answers} / {result.total_questions} correct
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Checklists */}
          <TabsContent value="checklists">
            <Card>
              <CardHeader>
                <CardTitle>Vehicle Inspection Checklists</CardTitle>
                <CardDescription>View checklists completed by your trainer</CardDescription>
              </CardHeader>
              <CardContent>
                {checklists.length === 0 ? (
                  <div className="text-center py-12">
                    <ClipboardCheck className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <p className="text-gray-500">No trainer checklists completed yet</p>
                    <p className="text-sm text-gray-400 mt-2">Your trainer will inspect your vehicle and submit the checklist</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {checklists.map((checklist) => (
                      <div
                        key={checklist.id}
                        data-testid={`checklist-${checklist.id}`}
                        className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200"
                      >
                        <div className="flex justify-between items-start mb-4">
                          <div>
                            <h3 className="font-semibold text-lg text-gray-900">
                              Trainer Inspection
                            </h3>
                            <p className="text-sm text-gray-600">
                              Completed: {new Date(checklist.submitted_at || checklist.verified_at).toLocaleDateString()}
                            </p>
                          </div>
                          <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            {checklist.verification_status || "Completed"}
                          </span>
                        </div>

                        {/* Checklist Items */}
                        {checklist.checklist_items && checklist.checklist_items.length > 0 ? (
                          <div className="space-y-3">
                            <h4 className="font-semibold text-sm text-gray-700 mb-2">Inspection Results:</h4>
                            {checklist.checklist_items.map((item, idx) => {
                              const itemName = item.item_name || item.name || item.item || 'Item';
                              // Handle different status formats
                              let itemStatus;
                              if (item.status) {
                                itemStatus = item.status.toLowerCase();
                              } else if (item.completed === true || item.completed === 'true') {
                                itemStatus = 'good';
                              } else if (item.completed === false || item.completed === 'false') {
                                // Old format: completed=false means not checked or pending
                                itemStatus = 'pending';
                              } else {
                                itemStatus = 'pending';
                              }
                              const itemComments = item.comments || item.comment || '';
                              const itemPhoto = item.photo || item.photo_url || item.image || '';
                              
                              return (
                                <div key={idx} className="p-4 bg-white rounded-lg border shadow-sm">
                                  <div className="flex justify-between items-start gap-3">
                                    <div className="flex-1">
                                      <p className="font-semibold text-gray-900 text-base">{itemName}</p>
                                      {itemComments && (
                                        <p className="text-sm text-gray-600 mt-2">
                                          <span className="font-semibold">Comments:</span> {itemComments}
                                        </p>
                                      )}
                                    </div>
                                    <span
                                      className={`px-4 py-1.5 rounded-full text-xs font-bold ml-3 whitespace-nowrap ${
                                        itemStatus === "good"
                                          ? "bg-green-100 text-green-800 border border-green-300"
                                          : itemStatus === "satisfactory"
                                          ? "bg-yellow-100 text-yellow-800 border border-yellow-300"
                                          : itemStatus === "needs_repair"
                                          ? "bg-red-100 text-red-800 border border-red-300"
                                          : "bg-gray-100 text-gray-800 border border-gray-300"
                                      }`}
                                    >
                                      {itemStatus === "needs_repair" ? "NEEDS REPAIR" : itemStatus.toUpperCase()}
                                    </span>
                                  </div>
                                  {itemPhoto && (
                                    <div className="mt-3">
                                      <p className="text-xs text-gray-500 mb-1">Photo:</p>
                                      <img
                                        src={itemPhoto}
                                        alt={itemName}
                                        className="w-48 h-48 object-cover rounded-lg border-2 border-gray-200 shadow-sm"
                                      />
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="text-center py-4 text-gray-500">
                            <p>No checklist items available</p>
                          </div>
                        )}

                        {/* Areas needing attention */}
                        {checklist.checklist_items && checklist.checklist_items.filter(item => (item.status || '').toLowerCase() === "needs_repair").length > 0 && (
                          <div className="mt-4 p-4 bg-red-50 border-2 border-red-300 rounded-lg">
                            <p className="font-bold text-red-800 text-base flex items-center gap-2">
                              <span className="text-xl">⚠️</span> Items Needing Attention
                            </p>
                            <ul className="mt-3 space-y-2">
                              {checklist.checklist_items
                                .filter(item => (item.status || '').toLowerCase() === "needs_repair")
                                .map((item, idx) => (
                                  <li key={idx} className="text-sm text-red-800 font-medium flex items-start gap-2">
                                    <span className="mt-0.5">•</span>
                                    <span>{item.item_name || item.name || item.item || 'Item'}</span>
                                  </li>
                                ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Lock className="w-5 h-5 mr-2" />
                  Change Password
                </CardTitle>
                <CardDescription>Update your account password</CardDescription>
              </CardHeader>
              <CardContent>
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const formData = new FormData(e.target);
                    const currentPassword = formData.get('current_password');
                    const newPassword = formData.get('new_password');
                    const confirmPassword = formData.get('confirm_password');

                    if (newPassword !== confirmPassword) {
                      toast.error("New passwords don't match");
                      return;
                    }

                    if (newPassword.length < 6) {
                      toast.error("Password must be at least 6 characters");
                      return;
                    }

                    try {
                      await axiosInstance.post('/auth/change-password', {
                        current_password: currentPassword,
                        new_password: newPassword
                      });
                      toast.success("Password changed successfully!");
                      e.target.reset();
                    } catch (error) {
                      toast.error(error.response?.data?.detail || "Failed to change password");
                    }
                  }}
                  className="space-y-4 max-w-md"
                >
                  <div>
                    <Label htmlFor="current_password">Current Password</Label>
                    <Input
                      id="current_password"
                      name="current_password"
                      type="password"
                      placeholder="Enter current password"
                      required
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="new_password">New Password</Label>
                    <Input
                      id="new_password"
                      name="new_password"
                      type="password"
                      placeholder="Enter new password (min 6 characters)"
                      required
                      minLength={6}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="confirm_password">Confirm New Password</Label>
                    <Input
                      id="confirm_password"
                      name="confirm_password"
                      type="password"
                      placeholder="Confirm new password"
                      required
                      minLength={6}
                      className="mt-1"
                    />
                  </div>
                  <Button type="submit" className="w-full">
                    <Lock className="w-4 h-4 mr-2" />
                    Change Password
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* Social Media Footer */}
      {socialMediaLinks.length > 0 && (
        <footer className="bg-gray-100 border-t py-4 mt-8">
          <div className="max-w-4xl mx-auto px-4 text-center">
            <p className="text-sm text-gray-600 mb-3">Follow us on social media</p>
            <div className="flex justify-center gap-4">
              {socialMediaLinks.map((link, index) => (
                <a
                  key={index}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:scale-110 transition-transform"
                  title={link.platform}
                >
                  <SocialIcon icon={link.icon} />
                </a>
              ))}
            </div>
          </div>
        </footer>
      )}

      {/* Social Media Popup (after feedback) */}
      <Dialog open={showSocialPopup} onOpenChange={setShowSocialPopup}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center text-xl">🎉 Thank You for Your Feedback!</DialogTitle>
            <DialogDescription className="text-center">
              Stay connected with us for driving tips, safety updates, and more!
            </DialogDescription>
          </DialogHeader>
          <div className="py-6">
            <p className="text-center text-sm text-gray-600 mb-4">Follow us on social media:</p>
            <div className="flex justify-center gap-6">
              {socialMediaLinks.map((link, index) => (
                <a
                  key={index}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex flex-col items-center gap-2 hover:scale-110 transition-transform"
                >
                  <SocialIcon icon={link.icon} className="text-4xl" />
                  <span className="text-xs text-gray-600">{link.platform}</span>
                </a>
              ))}
            </div>
          </div>
          <DialogFooter className="flex-col gap-2 sm:flex-col">
            <div className="flex items-center justify-center gap-2 mb-2">
              <input
                type="checkbox"
                id="dont-show-again"
                className="rounded"
              />
              <label htmlFor="dont-show-again" className="text-sm text-gray-600">Don&apos;t show this again</label>
            </div>
            <div className="flex gap-2 justify-center">
              <Button variant="outline" onClick={() => {
                const dontShow = document.getElementById('dont-show-again')?.checked;
                handleDismissSocialPopup(dontShow);
              }}>
                Maybe Later
              </Button>
              <Button onClick={() => {
                const dontShow = document.getElementById('dont-show-again')?.checked;
                handleDismissSocialPopup(dontShow);
              }}>
                Done
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ParticipantDashboard;
