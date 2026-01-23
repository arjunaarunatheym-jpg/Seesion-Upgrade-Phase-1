/**
 * PastTrainingTab Component - Extracted from AdminDashboard
 * Manages past training archive with search and filtering
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Search, FileText, Building2, Calendar, Users, Eye } from "lucide-react";

const PastTrainingTab = () => {
  const navigate = useNavigate();
  
  // State
  const [pastTrainingSessions, setPastTrainingSessions] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [loadingPastTraining, setLoadingPastTraining] = useState(false);
  const [expandedPastSession, setExpandedPastSession] = useState(null);

  const generateYearOptions = () => {
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let year = currentYear; year >= currentYear - 5; year--) {
      years.push(year);
    }
    return years;
  };

  const generateMonthOptions = () => {
    return [
      { value: 1, label: 'January' },
      { value: 2, label: 'February' },
      { value: 3, label: 'March' },
      { value: 4, label: 'April' },
      { value: 5, label: 'May' },
      { value: 6, label: 'June' },
      { value: 7, label: 'July' },
      { value: 8, label: 'August' },
      { value: 9, label: 'September' },
      { value: 10, label: 'October' },
      { value: 11, label: 'November' },
      { value: 12, label: 'December' },
    ];
  };

  const loadPastTraining = async () => {
    try {
      setLoadingPastTraining(true);
      const params = new URLSearchParams();
      if (selectedMonth && selectedYear) {
        params.append('month', selectedMonth);
        params.append('year', selectedYear);
      }
      const response = await axiosInstance.get(`/sessions/past-training?${params.toString()}`);
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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <FileText className="w-5 h-5 mr-2" />
          Past Training Archive
        </CardTitle>
        <CardDescription>
          Search and view completed training sessions
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Search Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2">
            <Label htmlFor="month-filter" className="text-sm font-medium">Month:</Label>
            <Select
              value={selectedMonth.toString()}
              onValueChange={(value) => setSelectedMonth(parseInt(value))}
            >
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Select month" />
              </SelectTrigger>
              <SelectContent>
                {generateMonthOptions().map((month) => (
                  <SelectItem key={month.value} value={month.value.toString()}>
                    {month.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex items-center gap-2">
            <Label htmlFor="year-filter" className="text-sm font-medium">Year:</Label>
            <Select
              value={selectedYear.toString()}
              onValueChange={(value) => setSelectedYear(parseInt(value))}
            >
              <SelectTrigger className="w-24">
                <SelectValue placeholder="Year" />
              </SelectTrigger>
              <SelectContent>
                {generateYearOptions().map((year) => (
                  <SelectItem key={year} value={year.toString()}>
                    {year}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <Button
            onClick={loadPastTraining}
            disabled={loadingPastTraining}
            className="flex items-center gap-2"
          >
            {loadingPastTraining ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <Search className="w-4 h-4" />
            )}
            Search
          </Button>
          
          <Button
            onClick={() => {
              setSelectedMonth(new Date().getMonth() + 1);
              setSelectedYear(new Date().getFullYear());
              setPastTrainingSessions([]);
              setExpandedPastSession(null);
            }}
            variant="outline"
            size="sm"
          >
            Clear
          </Button>
        </div>

        {/* Results */}
        <div className="space-y-4">
          {loadingPastTraining ? (
            <div className="flex justify-center items-center py-12">
              <div className="text-center">
                <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-gray-600">Searching past training sessions...</p>
              </div>
            </div>
          ) : pastTrainingSessions.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No past training found</h3>
              <p className="text-gray-600">
                {selectedMonth && selectedYear 
                  ? `No completed training sessions found for ${generateMonthOptions().find(m => m.value === selectedMonth)?.label} ${selectedYear}`
                  : "Use the search filters above to find past training sessions"
                }
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <p className="text-sm text-gray-600">
                  Found {pastTrainingSessions.length} training session{pastTrainingSessions.length !== 1 ? 's' : ''}
                </p>
              </div>
              
              {pastTrainingSessions.map((session) => (
                <Card key={session.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-gray-900">{session.name}</h3>
                          <Badge variant="secondary" className="text-xs">
                            {session.completion_status === 'completed' ? 'Completed' : 'Archived'}
                          </Badge>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm text-gray-600 mb-3">
                          <div className="flex items-center gap-1">
                            <Building2 className="w-4 h-4" />
                            <span>{session.company_name || 'Unknown Company'}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            <span>{new Date(session.start_date).toLocaleDateString()}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Users className="w-4 h-4" />
                            <span>{session.participant_ids?.length || 0} participants</span>
                          </div>
                        </div>
                        
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Program:</span> {session.program_name || 'Unknown Program'}
                        </p>
                      </div>
                      
                      <div className="flex gap-2">
                        <Button
                          onClick={() => handlePastSessionClick(session)}
                          variant="outline"
                          size="sm"
                          className="flex items-center gap-1"
                        >
                          <Eye className="w-4 h-4" />
                          {expandedPastSession?.id === session.id ? 'Hide Details' : 'View Details'}
                        </Button>
                        <Button
                          onClick={() => navigate(`/results-summary/${session.id}`)}
                          size="sm"
                          className="flex items-center gap-1"
                        >
                          <FileText className="w-4 h-4" />
                          View Results
                        </Button>
                      </div>
                    </div>
                    
                    {/* Expanded Details */}
                    {expandedPastSession?.id === session.id && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                          <div>
                            <h4 className="font-medium text-gray-900 mb-2">Session Information</h4>
                            <div className="space-y-1">
                              <p><span className="text-gray-600">Location:</span> {session.location}</p>
                              <p><span className="text-gray-600">Start Date:</span> {new Date(session.start_date).toLocaleString()}</p>
                              <p><span className="text-gray-600">End Date:</span> {new Date(session.end_date).toLocaleString()}</p>
                              {session.completed_date && (
                                <p><span className="text-gray-600">Completed:</span> {new Date(session.completed_date).toLocaleString()}</p>
                              )}
                            </div>
                          </div>
                          <div>
                            <h4 className="font-medium text-gray-900 mb-2">Training Team</h4>
                            <div className="space-y-1">
                              {session.trainer_assignments?.map((assignment, index) => (
                                <p key={index}>
                                  <span className="text-gray-600">{assignment.role === 'chief' ? 'Chief Trainer' : 'Trainer'}:</span> {assignment.trainer_name || 'Unknown'}
                                </p>
                              ))}
                              {session.coordinator_name && (
                                <p><span className="text-gray-600">Coordinator:</span> {session.coordinator_name}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export { PastTrainingTab };
