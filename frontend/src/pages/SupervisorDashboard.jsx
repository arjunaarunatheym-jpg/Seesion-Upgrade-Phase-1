import { useState, useEffect } from "react";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { LogOut, ClipboardCheck, Users, CheckCircle, XCircle, FileText, Download, Calendar } from "lucide-react";

const SupervisorDashboard = ({ user, onLogout }) => {
  const [sessions, setSessions] = useState([]);
  const [pendingChecklists, setPendingChecklists] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [attendance, setAttendance] = useState([]);
  const [reports, setReports] = useState([]);
  const [loadingReports, setLoadingReports] = useState(false);

  useEffect(() => {
    loadData();
    loadReports();
  }, []);

  const loadData = async () => {
    try {
      const [sessionsRes, checklistsRes] = await Promise.all([
        axiosInstance.get("/sessions"),
        axiosInstance.get("/checklists/pending"),
      ]);
      setSessions(sessionsRes.data);
      setPendingChecklists(checklistsRes.data);
    } catch (error) {
      toast.error("Failed to load dashboard data");
    }
  };

  const loadAttendance = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/attendance/session/${sessionId}`);
      setAttendance(response.data);
    } catch (error) {
      console.error("Failed to load attendance", error);


  const loadReports = async () => {
    setLoadingReports(true);
    try {
      const response = await axiosInstance.get("/training-reports/supervisor/sessions");
      setReports(response.data || []);
    } catch (error) {
      console.error("Failed to load reports", error);
      toast.error("Failed to load reports");
    } finally {
      setLoadingReports(false);
    }
  };

  const downloadReport = async (report) => {
    try {
      const response = await axiosInstance.get(report.pdf_url, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `Training_Report_${report.session_name?.replace(/\s+/g, '_')}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Report downloaded!");
    } catch (error) {
      toast.error("Failed to download report");
    }
  };

      toast.error("Failed to load attendance");
    }
  };

  const handleVerifyChecklist = async (checklistId, status) => {
    try {
      await axiosInstance.post("/checklists/verify", {
        checklist_id: checklistId,
        status: status,
      });
      toast.success(`Checklist ${status} successfully`);
      loadData();
    } catch (error) {
      toast.error("Failed to verify checklist");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-orange-50 to-rose-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Supervisor Dashboard</h1>
            <p className="text-sm text-gray-600">Welcome, {user.full_name}</p>
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
            <Button
              data-testid="supervisor-logout-button"
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
        <Tabs defaultValue="checklists" className="w-full">
          <TabsList className="grid w-full grid-cols-4 mb-8">
            <TabsTrigger value="sessions" data-testid="sessions-tab">
              <Users className="w-4 h-4 mr-2" />
              My Sessions
            </TabsTrigger>
            <TabsTrigger value="attendance" data-testid="attendance-tab">
              <CheckCircle className="w-4 h-4 mr-2" />
              Attendance
            </TabsTrigger>
            <TabsTrigger value="reports" data-testid="reports-tab">
              <FileText className="w-4 h-4 mr-2" />
              Reports
            </TabsTrigger>
            <TabsTrigger value="checklists" data-testid="checklists-tab">
              <ClipboardCheck className="w-4 h-4 mr-2" />
              Checklists
            </TabsTrigger>
          </TabsList>

          {/* Checklists Tab */}
          <TabsContent value="checklists">
            <Card>
              <CardHeader>
                <CardTitle>Pending Vehicle Checklists</CardTitle>
                <CardDescription>Review and verify participant checklists</CardDescription>
              </CardHeader>
              <CardContent>
                {pendingChecklists.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No pending checklists</p>
                ) : (
                  <div className="space-y-4">
                    {pendingChecklists.map((checklist) => (
                      <div
                        key={checklist.id}
                        data-testid={`pending-checklist-${checklist.id}`}
                        className="p-4 bg-white rounded-lg border-2 border-orange-200 shadow-sm"
                      >
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <h3 className="font-semibold text-gray-900">
                              {checklist.interval.replace("_", " ").toUpperCase()} Checklist
                            </h3>
                            <p className="text-sm text-gray-600">
                              Participant ID: {checklist.participant_id}
                            </p>
                            <p className="text-sm text-gray-600">
                              Submitted: {new Date(checklist.submitted_at).toLocaleDateString()}
                            </p>
                          </div>
                          <div className="flex gap-2">
                            <Button
                              data-testid={`approve-checklist-${checklist.id}`}
                              size="sm"
                              className="bg-green-500 hover:bg-green-600"
                              onClick={() => handleVerifyChecklist(checklist.id, "approved")}
                            >
                              <CheckCircle className="w-4 h-4 mr-1" />
                              Approve
                            </Button>
                            <Button
                              data-testid={`reject-checklist-${checklist.id}`}
                              size="sm"
                              variant="destructive"
                              onClick={() => handleVerifyChecklist(checklist.id, "rejected")}
                            >
                              <XCircle className="w-4 h-4 mr-1" />
                              Reject
                            </Button>
                          </div>
                        </div>
                        <div className="mt-3 pt-3 border-t">
                          <h4 className="text-sm font-semibold mb-2">Checklist Items:</h4>
                          <div className="space-y-1">
                            {checklist.checklist_items.map((item, idx) => (
                              <div key={idx} className="text-sm flex items-center gap-2">
                                <span
                                  className={`w-2 h-2 rounded-full ${
                                    item.status ? "bg-green-500" : "bg-red-500"
                                  }`}
                                ></span>
                                <span className="flex-1">{item.item}</span>
                                {item.comments && (
                                  <span className="text-gray-500 text-xs">({item.comments})</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Sessions Tab */}
          <TabsContent value="sessions">
            <Card>
              <CardHeader>
                <CardTitle>My Training Sessions</CardTitle>
                <CardDescription>Sessions you are supervising</CardDescription>
              </CardHeader>
              <CardContent>
                {sessions.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center" data-testid="empty-state">
                    <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center mb-3">
                      <Calendar className="w-7 h-7 text-slate-400" />
                    </div>
                    <h3 className="text-base font-semibold text-slate-700 mb-1">No sessions assigned yet</h3>
                    <p className="text-sm text-slate-500">Sessions will appear here once assigned by admin.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {sessions.map((session) => (
                      <div
                        key={session.id}
                        data-testid={`supervisor-session-${session.id}`}
                        className="p-4 bg-gradient-to-r from-orange-50 to-amber-50 rounded-lg"
                      >
                        <h3 className="font-semibold text-gray-900">{session.name}</h3>
                        <p className="text-sm text-gray-600 mt-1">Location: {session.location}</p>
                        <p className="text-sm text-gray-600">
                          {session.start_date} to {session.end_date}
                        </p>
                        <p className="text-sm text-gray-600 mt-2">
                          Participants: {session.participant_ids.length}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>


          {/* Reports Tab */}
          <TabsContent value="reports">
            <Card>
              <CardHeader>
                <CardTitle>Training Reports</CardTitle>
                <CardDescription>View submitted training reports for your sessions</CardDescription>
              </CardHeader>
              <CardContent>
                {loadingReports ? (
                  <div className="text-center py-8">
                    <p className="text-gray-500">Loading reports...</p>
                  </div>
                ) : reports.length === 0 ? (
                  <div className="text-center py-12">
                    <FileText className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <p className="text-gray-500">No training reports submitted yet</p>
                    <p className="text-sm text-gray-400 mt-2">Reports will appear here once coordinators submit them</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {reports.map((report) => (
                      <div
                        key={report.session_id}
                        className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h3 className="text-lg font-semibold text-gray-900">{report.session_name}</h3>
                            <div className="mt-2 space-y-1">
                              <p className="text-sm text-gray-600">
                                <span className="font-medium">Dates:</span> {report.session_start_date} to {report.session_end_date}
                              </p>
                              <p className="text-sm text-gray-600">
                                <span className="font-medium">Location:</span> {report.location || 'N/A'}
                              </p>
                              <p className="text-sm text-gray-600">
                                <span className="font-medium">Submitted:</span> {report.submitted_at ? new Date(report.submitted_at).toLocaleDateString() : 'N/A'}
                              </p>
                              <p className="text-sm">
                                <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium">
                                  ✓ Submitted
                                </span>
                              </p>
                            </div>
                          </div>
                          <div className="flex flex-col gap-2">
                            <Button
                              onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}${report.pdf_url}`, '_blank')}
                              variant="outline"
                              size="sm"
                            >
                              <FileText className="w-4 h-4 mr-2" />
                              View Report
                            </Button>
                            <Button
                              onClick={() => downloadReport(report)}
                              className="bg-blue-600 hover:bg-blue-700"
                              size="sm"
                            >
                              <Download className="w-4 h-4 mr-2" />
                              Download PDF
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>



          {/* Attendance Tab */}
          <TabsContent value="attendance">
            <Card>
              <CardHeader>
                <CardTitle>Session Attendance</CardTitle>
                <CardDescription>Select a session to view attendance records</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Session Selector */}
                  <div>
                    <label className="text-sm font-medium mb-2 block">Select Session:</label>
                    <select
                      className="w-full p-2 border rounded-lg"
                      value={selectedSession?.id || ''}
                      onChange={(e) => {
                        const session = sessions.find(s => s.id === e.target.value);
                        setSelectedSession(session);
                        if (session) loadAttendance(session.id);
                      }}
                    >
                      <option value="">Choose a session...</option>
                      {sessions.map((session) => (
                        <option key={session.id} value={session.id}>
                          {session.name} - {session.location}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Attendance List */}
                  {selectedSession && (
                    <div className="mt-6">
                      <h3 className="font-semibold text-lg mb-4">Attendance Records</h3>
                      {attendance.length === 0 ? (
                        <p className="text-gray-500 text-center py-8">No attendance records yet</p>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-50 border-b">
                              <tr>
                                <th className="text-left p-3 font-semibold">Participant</th>
                                <th className="text-left p-3 font-semibold">Vehicle Details</th>
                                <th className="text-center p-3 font-semibold">Clock In</th>
                                <th className="text-center p-3 font-semibold">Clock Out</th>
                                <th className="text-center p-3 font-semibold">Status</th>
                              </tr>
                            </thead>
                            <tbody>
                              {attendance.map((record) => (
                                <tr key={record.id} className="border-b hover:bg-gray-50">
                                  <td className="p-3">
                                    <p className="font-medium">{record.participant_name}</p>
                                    <p className="text-xs text-gray-500">{record.participant_email}</p>
                                  </td>
                                  <td className="p-3">
                                    <p className="text-xs">{record.vehicle_type || 'N/A'}</p>
                                    <p className="text-xs text-gray-500">{record.plate_number || 'N/A'}</p>
                                  </td>
                                  <td className="p-3 text-center">
                                    <span className="text-green-700 font-medium">
                                      {record.clock_in || 'N/A'}
                                    </span>
                                  </td>
                                  <td className="p-3 text-center">
                                    <span className={record.clock_out ? 'text-blue-700 font-medium' : 'text-gray-400'}>
                                      {record.clock_out || 'Not clocked out'}
                                    </span>
                                  </td>
                                  <td className="p-3 text-center">
                                    {record.clock_out ? (
                                      <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium">
                                        Complete
                                      </span>
                                    ) : (
                                      <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs font-medium">
                                        In Progress
                                      </span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

        </Tabs>
      </main>
    </div>
  );
};

export default SupervisorDashboard;
