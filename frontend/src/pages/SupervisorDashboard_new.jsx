import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Users, FileText, Calendar, LogOut, Clock, Download, Award, ClipboardCheck, DollarSign, CheckCircle, XCircle, Minus } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

const fmtDate = (d) => {
  if (!d) return "-";
  try { return new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }); } catch { return d; }
};

const SupervisorDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { companyName, logoUrl } = useTheme();
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingData, setLoadingData] = useState(false);

  const loadSessionData = useCallback(async (sessionId) => {
    setLoadingData(true);
    try {
      const res = await axiosInstance.get(`/sessions/${sessionId}/supervisor-data`);
      setSessionData(res.data);
    } catch {
      toast.error("Failed to load session data");
      setSessionData(null);
    } finally { setLoadingData(false); }
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axiosInstance.get("/sessions");
      const supervisorSessions = response.data.filter(s =>
        s.supervisor_ids && s.supervisor_ids.includes(user.id)
      );
      setSessions(supervisorSessions);
      if (supervisorSessions.length > 0) {
        setSelectedSession(supervisorSessions[0]);
        loadSessionData(supervisorSessions[0].id);
      }
    } catch { toast.error("Failed to load sessions"); }
    finally { setLoading(false); }
  }, [user.id, loadSessionData]);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  const handleSessionChange = (session) => {
    setSelectedSession(session);
    loadSessionData(session.id);
  };

  const handleExportAttendance = async () => {
    if (!selectedSession || !sessionData) return;
    // Build CSV client-side from sessionData
    const rows = [["Name", "IC Number", "Attended", "Days"]];
    (sessionData.participants || []).forEach(p => {
      rows.push([p.full_name, p.id_number, p.attended ? "Yes" : "No", p.attendance_days]);
    });
    const csv = rows.map(r => r.map(c => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `attendance_${selectedSession.company_name || "session"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Attendance exported");
  };

  const handleDownloadCert = async (certUrl, name) => {
    try {
      const res = await axiosInstance.get(certUrl, { responseType: "blob" });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `certificate_${name.replace(/\s+/g, "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error("Failed to download certificate"); }
  };

  const stats = sessionData?.stats || {};
  const participants = sessionData?.participants || [];
  const invoices = sessionData?.invoices || [];

  const StatusIcon = ({ val }) => {
    if (val === true) return <CheckCircle className="w-4 h-4 text-emerald-600" />;
    if (val === false) return <XCircle className="w-4 h-4 text-red-500" />;
    return <Minus className="w-4 h-4 text-gray-300" />;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-purple-50 to-pink-50">
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            {logoUrl && (
              <img src={logoUrl} alt={companyName} className="h-8 sm:h-10 w-auto object-contain" />
            )}
            <div>
              <h1 className="text-lg sm:text-2xl font-bold text-gray-900">Supervisor Portal</h1>
              <p className="text-xs sm:text-sm text-gray-600">Welcome, {user.full_name}</p>
            </div>
          </div>
          <Button onClick={onLogout} variant="outline" size="sm" className="flex items-center gap-1" data-testid="supervisor-logout-button">
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {loading ? (
          <div className="space-y-4">
            {[1,2,3].map(i => <div key={i} className="h-20 bg-gray-200 animate-pulse rounded-lg" />)}
          </div>
        ) : sessions.length === 0 ? (
          <Card><CardContent className="py-12 text-center" data-testid="empty-state">
            <Calendar className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-semibold text-gray-700">No sessions assigned</h3>
            <p className="text-sm text-gray-500">Sessions will appear here once assigned by admin.</p>
          </CardContent></Card>
        ) : (
          <div className="space-y-6">
            {/* Session Selector */}
            <div className="flex gap-3 overflow-x-auto pb-2">
              {sessions.map(s => (
                <button
                  key={s.id}
                  onClick={() => handleSessionChange(s)}
                  data-testid={`session-card-${s.id}`}
                  className={`flex-shrink-0 p-4 rounded-lg border-2 text-left transition-all min-w-[220px] ${
                    selectedSession?.id === s.id ? "border-purple-500 bg-purple-50 shadow-md" : "border-gray-200 hover:border-purple-300 bg-white"
                  }`}
                >
                  <p className="font-semibold text-gray-900">{s.company_name || "Unknown"}</p>
                  <p className="text-sm text-gray-700">{s.program_name || "Unknown"}</p>
                  <p className="text-xs text-gray-500 mt-1">{fmtDate(s.start_date)} - {fmtDate(s.end_date)}</p>
                  <p className="text-xs text-gray-500">{s.location}</p>
                </button>
              ))}
            </div>

            {loadingData ? (
              <div className="flex justify-center py-12">
                <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : selectedSession && sessionData && (
              <>
                {/* Stats Summary */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="supervisor-stats">
                  <Card className="border-l-4 border-l-blue-500">
                    <CardContent className="pt-4 pb-3 px-4">
                      <p className="text-xs text-gray-500 uppercase">Staff</p>
                      <p className="text-2xl font-bold text-gray-900">{stats.total_participants || 0}</p>
                    </CardContent>
                  </Card>
                  <Card className="border-l-4 border-l-emerald-500">
                    <CardContent className="pt-4 pb-3 px-4">
                      <p className="text-xs text-gray-500 uppercase">Attended</p>
                      <p className="text-2xl font-bold text-emerald-700">{stats.attended || 0}<span className="text-sm font-normal text-gray-500">/{stats.total_participants || 0}</span></p>
                    </CardContent>
                  </Card>
                  <Card className="border-l-4 border-l-amber-500">
                    <CardContent className="pt-4 pb-3 px-4">
                      <p className="text-xs text-gray-500 uppercase">Pass Rate</p>
                      <p className="text-2xl font-bold text-amber-700">{stats.post_test_pass_rate || 0}%</p>
                    </CardContent>
                  </Card>
                  <Card className="border-l-4 border-l-purple-500">
                    <CardContent className="pt-4 pb-3 px-4">
                      <p className="text-xs text-gray-500 uppercase">Post-Test Passed</p>
                      <p className="text-2xl font-bold text-purple-700">{stats.post_test_passed || 0}<span className="text-sm font-normal text-gray-500">/{stats.total_participants || 0}</span></p>
                    </CardContent>
                  </Card>
                  <Card className="border-l-4 border-l-pink-500">
                    <CardContent className="pt-4 pb-3 px-4">
                      <p className="text-xs text-gray-500 uppercase">Certs Issued</p>
                      <p className="text-2xl font-bold text-pink-700">{stats.certificates_issued || 0}<span className="text-sm font-normal text-gray-500">/{stats.total_participants || 0}</span></p>
                    </CardContent>
                  </Card>
                </div>

                {/* Tabs */}
                <Tabs defaultValue="progress" className="space-y-4">
                  <TabsList className="flex flex-wrap w-full h-auto justify-start gap-2 bg-gray-100 p-2 rounded-lg">
                    <TabsTrigger value="progress" data-testid="progress-tab" className="flex-shrink-0">
                      <Users className="w-4 h-4 mr-1.5" />Staff Progress
                    </TabsTrigger>
                    <TabsTrigger value="attendance" data-testid="attendance-tab" className="flex-shrink-0">
                      <Clock className="w-4 h-4 mr-1.5" />Attendance
                    </TabsTrigger>
                    <TabsTrigger value="results" data-testid="results-tab" className="flex-shrink-0">
                      <ClipboardCheck className="w-4 h-4 mr-1.5" />Test Results
                    </TabsTrigger>
                    <TabsTrigger value="certificates" data-testid="certificates-tab" className="flex-shrink-0">
                      <Award className="w-4 h-4 mr-1.5" />Certificates
                    </TabsTrigger>
                    <TabsTrigger value="invoices" data-testid="invoices-tab" className="flex-shrink-0">
                      <DollarSign className="w-4 h-4 mr-1.5" />Invoice
                    </TabsTrigger>
                  </TabsList>

                  {/* Staff Progress Tab */}
                  <TabsContent value="progress">
                    <Card>
                      <CardHeader>
                        <CardTitle>Staff Training Progress</CardTitle>
                        <CardDescription>Overview of each participant's completion status</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {participants.length === 0 ? (
                          <p className="text-center py-8 text-gray-500">No participants in this session.</p>
                        ) : (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm" data-testid="progress-table">
                              <thead>
                                <tr className="border-b bg-gray-50">
                                  <th className="text-left p-3 font-medium text-gray-700">Name</th>
                                  <th className="text-left p-3 font-medium text-gray-700">IC</th>
                                  <th className="text-center p-3 font-medium text-gray-700">Attended</th>
                                  <th className="text-center p-3 font-medium text-gray-700">Pre-Test</th>
                                  <th className="text-center p-3 font-medium text-gray-700">Post-Test</th>
                                  <th className="text-center p-3 font-medium text-gray-700">Certificate</th>
                                </tr>
                              </thead>
                              <tbody>
                                {participants.map(p => (
                                  <tr key={p.id} className="border-b hover:bg-gray-50">
                                    <td className="p-3 font-medium text-gray-900 truncate max-w-[200px]" title={p.full_name}>{p.full_name}</td>
                                    <td className="p-3 text-gray-600">{p.id_number || "-"}</td>
                                    <td className="p-3 text-center"><StatusIcon val={p.attended} /></td>
                                    <td className="p-3 text-center"><StatusIcon val={p.pre_test_passed} /></td>
                                    <td className="p-3 text-center"><StatusIcon val={p.post_test_passed} /></td>
                                    <td className="p-3 text-center"><StatusIcon val={p.has_certificate} /></td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>

                  {/* Attendance Tab */}
                  <TabsContent value="attendance">
                    <Card>
                      <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                          <CardTitle>Attendance</CardTitle>
                          <CardDescription>Attendance rate: {stats.attendance_rate || 0}%</CardDescription>
                        </div>
                        <Button variant="outline" size="sm" onClick={handleExportAttendance} data-testid="export-attendance-btn">
                          <Download className="w-4 h-4 mr-1.5" />Export CSV
                        </Button>
                      </CardHeader>
                      <CardContent>
                        {participants.length === 0 ? (
                          <p className="text-center py-8 text-gray-500">No data.</p>
                        ) : (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b bg-gray-50">
                                  <th className="text-left p-3 font-medium">Name</th>
                                  <th className="text-left p-3 font-medium">IC Number</th>
                                  <th className="text-center p-3 font-medium">Status</th>
                                  <th className="text-center p-3 font-medium">Days</th>
                                </tr>
                              </thead>
                              <tbody>
                                {participants.map(p => (
                                  <tr key={p.id} className="border-b hover:bg-gray-50">
                                    <td className="p-3 font-medium truncate max-w-[200px]" title={p.full_name}>{p.full_name}</td>
                                    <td className="p-3 text-gray-600">{p.id_number || "-"}</td>
                                    <td className="p-3 text-center">
                                      <Badge variant={p.attended ? "default" : "destructive"} className={p.attended ? "bg-emerald-100 text-emerald-800" : ""}>
                                        {p.attended ? "Present" : "Absent"}
                                      </Badge>
                                    </td>
                                    <td className="p-3 text-center">{p.attendance_days}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>

                  {/* Test Results Tab */}
                  <TabsContent value="results">
                    <Card>
                      <CardHeader>
                        <CardTitle>Test Results</CardTitle>
                        <CardDescription>Pre-test and post-test scores for each participant</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {participants.length === 0 ? (
                          <p className="text-center py-8 text-gray-500">No data.</p>
                        ) : (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm" data-testid="results-table">
                              <thead>
                                <tr className="border-b bg-gray-50">
                                  <th className="text-left p-3 font-medium">Name</th>
                                  <th className="text-center p-3 font-medium">Pre-Test Score</th>
                                  <th className="text-center p-3 font-medium">Pre-Test</th>
                                  <th className="text-center p-3 font-medium">Post-Test Score</th>
                                  <th className="text-center p-3 font-medium">Post-Test</th>
                                </tr>
                              </thead>
                              <tbody>
                                {participants.map(p => (
                                  <tr key={p.id} className="border-b hover:bg-gray-50">
                                    <td className="p-3 font-medium truncate max-w-[200px]" title={p.full_name}>{p.full_name}</td>
                                    <td className="p-3 text-center">{p.pre_test_score != null ? `${p.pre_test_score}%` : "-"}</td>
                                    <td className="p-3 text-center">
                                      {p.pre_test_passed != null ? (
                                        <Badge className={p.pre_test_passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}>
                                          {p.pre_test_passed ? "Pass" : "Fail"}
                                        </Badge>
                                      ) : <span className="text-gray-400">-</span>}
                                    </td>
                                    <td className="p-3 text-center">{p.post_test_score != null ? `${p.post_test_score}%` : "-"}</td>
                                    <td className="p-3 text-center">
                                      {p.post_test_passed != null ? (
                                        <Badge className={p.post_test_passed ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}>
                                          {p.post_test_passed ? "Pass" : "Fail"}
                                        </Badge>
                                      ) : <span className="text-gray-400">-</span>}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>

                  {/* Certificates Tab */}
                  <TabsContent value="certificates">
                    <Card>
                      <CardHeader>
                        <CardTitle>Certificates</CardTitle>
                        <CardDescription>{stats.certificates_issued || 0} of {stats.total_participants || 0} certificates issued</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {participants.length === 0 ? (
                          <p className="text-center py-8 text-gray-500">No data.</p>
                        ) : (
                          <div className="space-y-2">
                            {participants.map(p => (
                              <div key={p.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
                                <div>
                                  <p className="font-medium text-gray-900">{p.full_name}</p>
                                  <p className="text-xs text-gray-500">{p.id_number}</p>
                                </div>
                                {p.has_certificate ? (
                                  <Button size="sm" variant="outline" onClick={() => handleDownloadCert(p.certificate_url, p.full_name)} data-testid={`download-cert-${p.id}`}>
                                    <Download className="w-4 h-4 mr-1" />Download
                                  </Button>
                                ) : (
                                  <Badge variant="secondary" className="text-gray-500">Not Issued</Badge>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>

                  {/* Invoices Tab */}
                  <TabsContent value="invoices">
                    <Card>
                      <CardHeader>
                        <CardTitle>Session Invoice</CardTitle>
                        <CardDescription>Invoice details for this training session</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {invoices.length === 0 ? (
                          <div className="text-center py-8">
                            <DollarSign className="w-10 h-10 mx-auto text-gray-400 mb-3" />
                            <p className="text-gray-500">No invoice generated for this session yet.</p>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {invoices.map(inv => (
                              <div key={inv.id} className="p-4 border rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50" data-testid={`invoice-${inv.id}`}>
                                <div className="flex justify-between items-start">
                                  <div>
                                    <p className="font-semibold text-gray-900 text-lg">{inv.invoice_number || "Draft"}</p>
                                    <p className="text-sm text-gray-600 mt-1">Date: {fmtDate(inv.invoice_date)}</p>
                                  </div>
                                  <div className="text-right">
                                    <p className="text-2xl font-bold text-gray-900">RM {(inv.total_amount || 0).toLocaleString("en-MY", { minimumFractionDigits: 2 })}</p>
                                    <Badge className={
                                      inv.status === "paid" ? "bg-emerald-100 text-emerald-800 mt-1" :
                                      inv.status === "issued" ? "bg-blue-100 text-blue-800 mt-1" :
                                      inv.status === "voided" ? "bg-red-100 text-red-800 mt-1" :
                                      "bg-gray-100 text-gray-800 mt-1"
                                    }>
                                      {(inv.status || "draft").charAt(0).toUpperCase() + (inv.status || "draft").slice(1)}
                                    </Badge>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>
                </Tabs>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default SupervisorDashboard;
