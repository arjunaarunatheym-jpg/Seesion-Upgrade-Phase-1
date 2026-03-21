import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Users, FileText, Calendar, LogOut, CheckCircle2, Clock } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

const SupervisorDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { primaryColor, companyName, logoUrl } = useTheme();
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [attendance, setAttendance] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadAttendance = useCallback(async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/attendance/session/${sessionId}`);
      setAttendance(response.data);
    } catch (error) {
      toast.error("Failed to load attendance");
      setAttendance([]);
    }
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axiosInstance.get('/sessions');
      // Filter sessions where user is supervisor
      const supervisorSessions = response.data.filter(s => 
        s.supervisor_ids && s.supervisor_ids.includes(user.id)
      );
      setSessions(supervisorSessions);
      
      if (supervisorSessions.length > 0) {
        setSelectedSession(supervisorSessions[0]);
        loadAttendance(supervisorSessions[0].id);
      }
      setLoading(false);
    } catch (error) {
      toast.error("Failed to load sessions");
      setLoading(false);
    }
  }, [user.id, loadAttendance]);

  const handleSessionChange = (session) => {
    setSelectedSession(session);
    loadAttendance(session.id);
  };

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Group attendance by participant
  const groupedAttendance = attendance.reduce((acc, record) => {
    if (!acc[record.participant_id]) {
      acc[record.participant_id] = {
        participant_name: record.participant_name || 'Unknown',
        participant_email: record.participant_email || '',
        records: []
      };
    }
    acc[record.participant_id].records.push(record);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-rose-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <div className="flex items-center gap-3 sm:gap-4">
            {logoUrl && (
              <button
                onClick={() => navigate('/')}
                className="hover:opacity-80 transition-opacity cursor-pointer"
              >
                <img 
                  src={logoUrl} 
                  alt={companyName}
                  className="h-8 sm:h-10 w-auto object-contain"
                />
              </button>
            )}
            <div>
              <h1 className="text-lg sm:text-2xl font-bold text-gray-900">Supervisor Portal</h1>
              <p className="text-xs sm:text-sm text-gray-600">Welcome, {user.full_name}</p>
            </div>
          </div>
          <Button
            onClick={onLogout}
            variant="outline"
            size="sm"
            className="flex items-center gap-1 sm:gap-2 self-end sm:self-auto"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        ) : sessions.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Users className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-500">No sessions assigned yet</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {/* Session Selector */}
            <Card>
              <CardHeader>
                <CardTitle>My Sessions</CardTitle>
                <CardDescription>Select a session to view attendance details</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {sessions.map((session) => (
                    <button
                      key={session.id}
                      onClick={() => handleSessionChange(session)}
                      className={`p-4 rounded-lg border-2 text-left transition-all ${
                        selectedSession?.id === session.id
                          ? 'border-purple-500 bg-purple-50'
                          : 'border-gray-200 hover:border-purple-300'
                      }`}
                    >
                      <h3 className="font-semibold text-gray-900">{session.company_name || "Unknown Company"}</h3>
                      <p className="text-base text-gray-700 mt-0.5">{session.program_name || "Unknown Program"}</p>
                      <p className="text-sm text-gray-600 mt-1">{session.location}</p>
                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(session.start_date).toLocaleDateString()} - {new Date(session.end_date).toLocaleDateString()}
                      </p>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Attendance View */}
            {selectedSession && (
              <Tabs defaultValue="attendance" className="space-y-4">
                <TabsList className="flex flex-wrap w-full h-auto justify-start gap-2 bg-gray-100 p-2 rounded-lg">
                  <TabsTrigger value="attendance" className="flex-1 min-w-[120px] sm:min-w-0">
                    <Clock className="w-4 h-4 mr-2" />
                    <span className="hidden sm:inline">Attendance</span>
                    <span className="sm:hidden">Attend</span>
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="attendance">
                  <Card>
                    <CardHeader>
                      <CardTitle>Attendance Records - {selectedSession.company_name || "Unknown Company"} ({selectedSession.program_name || "Unknown Program"})</CardTitle>
                      <CardDescription>
                        View all participant attendance for this session
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      {Object.keys(groupedAttendance).length === 0 ? (
                        <div className="text-center py-12">
                          <Calendar className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                          <p className="text-gray-500">No attendance records yet</p>
                        </div>
                      ) : (
                        <div className="space-y-6">
                          {Object.entries(groupedAttendance).map(([participantId, data]) => (
                            <div key={participantId} className="border rounded-lg p-4 bg-gradient-to-r from-blue-50 to-indigo-50">
                              <div className="flex justify-between items-start mb-3">
                                <div>
                                  <h3 className="font-semibold text-gray-900">{data.participant_name}</h3>
                                  <p className="text-sm text-gray-600">{data.participant_email}</p>
                                </div>
                                <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                                  {data.records.length} day(s)
                                </span>
                              </div>
                              
                              {/* Attendance Records */}
                              <div className="space-y-2">
                                {data.records.map((record, idx) => (
                                  <div key={idx} className="flex items-center justify-between p-3 bg-white rounded border">
                                    <div className="flex items-center gap-4">
                                      <div>
                                        <p className="text-sm font-medium text-gray-900">
                                          {new Date(record.date).toLocaleDateString()}
                                        </p>
                                      </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                      <div className="text-sm">
                                        <span className="text-gray-600">In:</span>
                                        <span className={`ml-2 font-medium ${
                                          record.clock_in ? 'text-green-600' : 'text-gray-400'
                                        }`}>
                                          {record.clock_in || '-'}
                                        </span>
                                      </div>
                                      <div className="text-sm">
                                        <span className="text-gray-600">Out:</span>
                                        <span className={`ml-2 font-medium ${
                                          record.clock_out ? 'text-red-600' : 'text-gray-400'
                                        }`}>
                                          {record.clock_out || '-'}
                                        </span>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default SupervisorDashboard;
