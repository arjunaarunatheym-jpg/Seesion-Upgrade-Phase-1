/**
 * PastTrainingTab Component - Extracted from CoordinatorDashboard
 * Search and view completed training sessions archive
 */
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileText, Search, Eye, BarChart3, Calendar, Users, BookOpen } from "lucide-react";

const PastTrainingTab = ({
  selectedMonth,
  setSelectedMonth,
  selectedYear,
  setSelectedYear,
  pastTrainingSessions,
  setPastTrainingSessions,
  loadingPastTraining,
  expandedPastSession,
  setExpandedPastSession,
  primaryColor,
  loadPastTraining,
  handlePastSessionClick,
  generateMonthOptions,
  generateYearOptions,
}) => {
  const navigate = useNavigate();

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
            style={{ backgroundColor: primaryColor }}
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
                          <div>
                            <h3 className="font-semibold text-lg text-gray-900">{session.company_name || 'Unknown Company'}</h3>
                            <p className="text-base text-gray-700">{session.program_name || 'Unknown Program'}</p>
                          </div>
                          <Badge variant="secondary" className="text-xs">
                            {session.completion_status === 'completed' ? 'Completed' : 'Archived'}
                          </Badge>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm text-gray-600 mb-3">
                          <div className="flex items-center gap-1">
                            <BookOpen className="w-4 h-4" />
                            <span>{session.name}</span>
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
                          style={{ backgroundColor: primaryColor }}
                        >
                          <BarChart3 className="w-4 h-4" />
                          Results
                        </Button>
                      </div>
                    </div>
                    
                    {expandedPastSession?.id === session.id && (
                      <div className="mt-4 pt-4 border-t space-y-2">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="font-medium text-gray-700">Location:</span>
                            <p className="text-gray-600 mt-1">{session.location || 'Not specified'}</p>
                          </div>
                          <div>
                            <span className="font-medium text-gray-700">Date Range:</span>
                            <p className="text-gray-600 mt-1">
                              {new Date(session.start_date).toLocaleDateString()} - {new Date(session.end_date).toLocaleDateString()}
                            </p>
                          </div>
                          <div>
                            <span className="font-medium text-gray-700">Venue:</span>
                            <p className="text-gray-600 mt-1">{session.venue || 'Not specified'}</p>
                          </div>
                          <div>
                            <span className="font-medium text-gray-700">Status:</span>
                            <p className="text-gray-600 mt-1">
                              {session.is_archived ? '✓ Archived' : 'Active'}
                            </p>
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
