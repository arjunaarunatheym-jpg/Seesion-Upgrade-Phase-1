/**
 * CertificatesTab Component - Extracted from AdminDashboard
 * Manages certificates repository with search and filtering
 */
import { useState, useEffect } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Award, Download } from "lucide-react";

const CertificatesTab = ({
  sessions,
  programs,
  isActive,
}) => {
  // State
  const [allCertificates, setAllCertificates] = useState([]);
  const [loadingCertificates, setLoadingCertificates] = useState(false);
  const [certificatesSearch, setCertificatesSearch] = useState("");
  const [filterCertSession, setFilterCertSession] = useState("all");
  const [filterCertProgram, setFilterCertProgram] = useState("all");

  // Load certificates when tab becomes active
  useEffect(() => {
    if (isActive && allCertificates.length === 0) {
      loadAllCertificates();
    }
  }, [isActive]);

  const loadAllCertificates = async () => {
    setLoadingCertificates(true);
    try {
      const response = await axiosInstance.get("/certificates/all");
      setAllCertificates(response.data);
    } catch (error) {
      console.error("Failed to load certificates:", error);
      toast.error("Failed to load certificates");
    } finally {
      setLoadingCertificates(false);
    }
  };

  const handleDownloadCertificate = async (url, participantName) => {
    try {
      const response = await axiosInstance.get(url, {
        responseType: 'blob'
      });
      
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', `certificate_${participantName.replace(/\s+/g, '_')}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
      
      toast.success("Certificate downloaded successfully");
    } catch (error) {
      toast.error("Failed to download certificate");
    }
  };

  // Filter certificates
  const filteredCertificates = allCertificates.filter((cert) => {
    const searchLower = certificatesSearch.toLowerCase();
    const matchesSearch = !certificatesSearch || 
      cert.participant_name?.toLowerCase().includes(searchLower) ||
      cert.participant_id_number?.toLowerCase().includes(searchLower) ||
      cert.participant_email?.toLowerCase().includes(searchLower);
    
    const matchesSession = filterCertSession === "all" || cert.session_id === filterCertSession;
    const matchesProgram = filterCertProgram === "all" || cert.program_name === filterCertProgram;
    
    return matchesSearch && matchesSession && matchesProgram;
  });

  return (
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
                {filteredCertificates.map((cert, index) => (
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
                {(certificatesSearch || filterCertSession !== "all" || filterCertProgram !== "all") && (
                  <span className="ml-2">
                    | <span className="font-semibold">Filtered:</span> {filteredCertificates.length}
                  </span>
                )}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { CertificatesTab };
