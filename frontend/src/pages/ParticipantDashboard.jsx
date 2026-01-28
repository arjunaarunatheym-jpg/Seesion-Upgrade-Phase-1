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
    
    if (!verificationData.contact_email.trim()) {
      toast.error("Please provide your email address");
      return;
    }
    
    if (!verificationData.contact_phone.trim()) {
      toast.error("Please provide your phone number");
      return;
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(verificationData.contact_email.trim())) {
      toast.error("Please enter a valid email address");
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
                  <Label htmlFor="verify-email">Personal Email *</Label>
                  <Input
                    id="verify-email"
                    type="email"
                    value={verificationData.contact_email}
                    onChange={(e) => setVerificationData({ ...verificationData, contact_email: e.target.value })}
                    placeholder="your.email@example.com"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="verify-phone">Phone Number *</Label>
                  <Input
                    id="verify-phone"
                    type="tel"
                    value={verificationData.contact_phone}
                    onChange={(e) => setVerificationData({ ...verificationData, contact_phone: e.target.value })}
                    placeholder="e.g., 012-345 6789"
                    required
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

          {/* Overview Tab */}
          <TabsContent value="overview">
            <OverviewTab
              sessions={sessions}
              participantAccess={participantAccess}
              testResults={testResults}
              onFeedback={handleFeedback}
            />
          </TabsContent>

          {/* Certificates Tab */}
          <TabsContent value="certificates">
            <CertificatesTab
              user={user}
              sessions={sessions}
              participantAccess={participantAccess}
              attendanceToday={attendanceToday}
              socialMediaLinks={socialMediaLinks}
            />
          </TabsContent>

          {/* Details Tab */}
          <TabsContent value="details">
            <DetailsTab
              sessions={sessions}
              vehicleDetails={vehicleDetails}
              attendanceToday={attendanceToday}
              participantAccess={participantAccess}
              vehicleForm={vehicleForm}
              setVehicleForm={setVehicleForm}
              onClockIn={handleClockIn}
              onClockOut={handleClockOut}
              onVehicleSubmit={handleVehicleSubmit}
            />
          </TabsContent>

          {/* Tests Tab */}
          <TabsContent value="tests">
            <TestsTab
              availableTests={availableTests}
              testResults={testResults}
              onTakeTest={handleTakeTest}
              onViewResult={handleViewResult}
            />
          </TabsContent>

          {/* Checklists Tab */}
          <TabsContent value="checklists">
            <ChecklistsTab checklists={checklists} />
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings">
            <SettingsTab />
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
