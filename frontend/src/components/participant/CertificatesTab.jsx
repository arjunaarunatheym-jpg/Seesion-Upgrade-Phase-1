/**
 * CertificatesTab Component - Extracted from ParticipantDashboard
 * Displays and allows downloading of training certificates
 */
import { axiosInstance } from "../../App";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { toast } from "sonner";
import { Award, Download, Globe } from "lucide-react";
import { FaFacebook, FaInstagram, FaTiktok, FaYoutube, FaTwitter, FaLinkedin } from 'react-icons/fa';

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

const CertificatesTab = ({
  user,
  sessions,
  participantAccess,
  attendanceToday,
  socialMediaLinks,
}) => {
  const handleDownloadCertificate = async (session, btn) => {
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin mr-2">⏳</span> Downloading...';
    
    try {
      const timestamp = new Date().getTime();
      const response = await axiosInstance.get(
        `/certificates/download/${session.id}/${user.id}?_t=${timestamp}`,
        { 
          responseType: 'blob',
          timeout: 60000,
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          }
        }
      );
      
      const contentType = response.headers['content-type'];
      if (contentType && contentType.includes('application/json')) {
        const text = await response.data.text();
        const errorData = JSON.parse(text);
        toast.error(errorData.detail || "Failed to download certificate");
        return;
      }
      
      if (!response.data || response.data.size === 0) {
        toast.error("Certificate file is empty. Please contact administrator.");
        return;
      }
      
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
  };

  return (
    <>
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
                            onClick={(e) => handleDownloadCertificate(session, e.currentTarget)}
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

      {/* Social Media Section */}
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
    </>
  );
};

export { CertificatesTab };
