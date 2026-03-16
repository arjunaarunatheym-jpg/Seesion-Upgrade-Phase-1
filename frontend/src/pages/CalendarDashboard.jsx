import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { axiosInstance } from "../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useTheme } from "../context/ThemeContext";
import { 
  ChevronLeft, 
  ChevronRight, 
  Calendar as CalendarIcon,
  Users,
  Building2,
  MapPin,
  Clock,
  LogOut,
  Settings,
  BarChart3
} from "lucide-react";

const CalendarDashboard = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const { primaryColor, secondaryColor, companyName, logoUrl } = useTheme();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [sessions, setSessions] = useState([]);
  const [expandedDate, setExpandedDate] = useState(null);
  const [loading, setLoading] = useState(true);

  // Month names for display
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  // Days of week
  const daysOfWeek = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  useEffect(() => {
    loadCalendarSessions();
  }, []);

  const loadCalendarSessions = async () => {
    try {
      setLoading(true);
      const response = await axiosInstance.get("/sessions/calendar");
      setSessions(response.data);
    } catch (error) {
      toast.error("Failed to load calendar sessions");
    } finally {
      setLoading(false);
    }
  };

  // Navigate to previous month
  const goToPrevMonth = () => {
    setCurrentDate(prev => {
      const newDate = new Date(prev);
      newDate.setMonth(prev.getMonth() - 1);
      return newDate;
    });
    setExpandedDate(null);
  };

  // Navigate to next month
  const goToNextMonth = () => {
    setCurrentDate(prev => {
      const newDate = new Date(prev);
      newDate.setMonth(prev.getMonth() + 1);
      return newDate;
    });
    setExpandedDate(null);
  };

  // Get sessions for a specific date
  const getSessionsForDate = (date) => {
    // Format date as YYYY-MM-DD in local timezone
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    
    return sessions.filter(session => {
      // Check if date falls within session's start_date and end_date range
      const startDate = session.start_date;
      const endDate = session.end_date || session.start_date; // If no end_date, use start_date
      
      return dateStr >= startDate && dateStr <= endDate;
    });
  };

  // Generate calendar days for current month
  const generateCalendarDays = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    // First day of the month
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    // Days to show (including previous/next month days)
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    const endDate = new Date(lastDay);
    endDate.setDate(endDate.getDate() + (6 - lastDay.getDay()));
    
    const days = [];
    const current = new Date(startDate);
    
    while (current <= endDate) {
      days.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    
    return days;
  };

  // Handle date click
  const handleDateClick = (date) => {
    // Format date as YYYY-MM-DD in local timezone
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    
    const sessionsForDate = getSessionsForDate(date);
    
    if (sessionsForDate.length > 0) {
      setExpandedDate(expandedDate === dateStr ? null : dateStr);
    }
  };

  // Check if date is in current month
  const isCurrentMonth = (date) => {
    return date.getMonth() === currentDate.getMonth();
  };

  // Check if date is today
  const isToday = (date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const calendarDays = generateCalendarDays();

  return (
    <div 
      className="min-h-screen"
      style={{
        background: `linear-gradient(to bottom right, ${primaryColor}10, ${secondaryColor}10, ${primaryColor}05)`
      }}
    >
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            {logoUrl && (
              <img 
                src={logoUrl} 
                alt={companyName}
                className="h-10 w-auto object-contain"
              />
            )}
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Training Calendar</h1>
              <p className="text-sm text-gray-600">Welcome, {user.full_name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={() => {
                if (user.email === "arjuna@mddrc.com.my" || user.role === "admin") navigate("/admin");
                else if (user.role === "assistant_admin") navigate("/assistant-admin");
                else if (user.role === "coordinator") navigate("/coordinator");
                else if (user.role === "trainer") navigate("/trainer");
                else if (user.role === "marketing") navigate("/marketing");
                else if (user.role === "finance") navigate("/finance");
              }}
              variant="outline"
              size="sm"
              className="flex items-center gap-1"
            >
              <BarChart3 className="w-4 h-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </Button>
            <Button
              onClick={onLogout}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Logout</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-4">
                <CalendarIcon className="w-6 h-6 text-blue-600" />
                <div>
                  <CardTitle className="text-2xl">
                    {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
                  </CardTitle>
                  <CardDescription>
                    All training sessions (past and future)
                  </CardDescription>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={goToPrevMonth}
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-1"
                >
                  <ChevronLeft className="w-4 h-4" />
                  <span className="hidden sm:inline">Previous</span>
                </Button>
                <Button
                  onClick={goToNextMonth}
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-1"
                >
                  <span className="hidden sm:inline">Next</span>
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center items-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Calendar Grid */}
                <div className="grid grid-cols-7 gap-1 mb-4">
                  {/* Day headers */}
                  {daysOfWeek.map(day => (
                    <div 
                      key={day} 
                      className="p-2 text-center text-sm font-medium text-gray-500 bg-gray-50 rounded-t-lg"
                    >
                      {day}
                    </div>
                  ))}
                  
                  {/* Calendar days */}
                  {calendarDays.map((date, index) => {
                    // Format date as YYYY-MM-DD in local timezone
                    const year = date.getFullYear();
                    const month = String(date.getMonth() + 1).padStart(2, '0');
                    const day = String(date.getDate()).padStart(2, '0');
                    const dateStr = `${year}-${month}-${day}`;
                    
                    const daysSessions = getSessionsForDate(date);
                    const isExpanded = expandedDate === dateStr;
                    
                    return (
                      <div key={index} className="relative">
                        <button
                          onClick={() => handleDateClick(date)}
                          className={`w-full p-2 text-center border rounded-lg transition-colors min-h-[60px] flex flex-col justify-between ${
                            isCurrentMonth(date)
                              ? isToday(date)
                                ? 'bg-blue-100 border-blue-300 text-blue-900 font-bold'
                                : daysSessions.length > 0
                                  ? 'bg-green-50 border-green-200 text-green-900 hover:bg-green-100 cursor-pointer'
                                  : 'bg-white border-gray-200 text-gray-900 hover:bg-gray-50'
                              : 'bg-gray-50 border-gray-100 text-gray-400'
                          }`}
                          disabled={!isCurrentMonth(date) || daysSessions.length === 0}
                        >
                          <span className="text-sm font-medium">{date.getDate()}</span>
                          {daysSessions.length > 0 && (
                            <div className="flex justify-center">
                              <div 
                                className="w-2 h-2 rounded-full"
                                style={{ backgroundColor: primaryColor }}
                              ></div>
                            </div>
                          )}
                        </button>
                        
                        {/* Expanded session details - Mobile Friendly */}
                        {isExpanded && daysSessions.length > 0 && (
                          <div className="fixed md:absolute top-20 md:top-full left-2 right-2 md:left-0 md:right-0 z-50 mt-1 max-h-[70vh] overflow-y-auto">
                            <Card className="shadow-lg border-2 border-blue-200">
                              <CardContent className="p-2 sm:p-3">
                                <div className="space-y-2">
                                  {daysSessions.map((session) => (
                                    <div 
                                      key={session.id}
                                      className="p-2 sm:p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg"
                                    >
                                      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2">
                                        <div className="flex-1 min-w-0">
                                          <h4 className="font-semibold text-gray-900 text-xs sm:text-sm truncate">
                                            {session.company_name || "Unknown Company"}
                                          </h4>
                                          <p className="text-xs text-gray-700 mt-0.5 truncate">
                                            {session.program_name || "Unknown Program"}
                                          </p>
                                          <div className="flex items-center gap-1 text-xs text-gray-600 mt-1">
                                            <MapPin className="w-3 h-3 flex-shrink-0" />
                                            <span className="truncate">{session.location}</span>
                                          </div>
                                        </div>
                                        <Badge variant="secondary" className="text-xs self-start flex-shrink-0">
                                          <Users className="w-3 h-3 mr-1" />
                                          {session.participant_count}
                                        </Badge>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Legend */}
                <div className="flex flex-wrap items-center justify-center gap-6 pt-4 border-t">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-blue-100 border border-blue-300 rounded"></div>
                    <span className="text-sm text-gray-600">Today</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: primaryColor }}
                    ></div>
                    <span className="text-sm text-gray-600">Training scheduled</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">Click dates with training to see details</span>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default CalendarDashboard;