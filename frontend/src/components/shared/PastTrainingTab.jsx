/**
 * PastTrainingTab - Shared component for past training archive
 * Used by TrainerDashboard, AssistantAdminDashboard, CoordinatorDashboard
 */
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { FileText, Search, Calendar, Building, Users, ChevronDown, ChevronRight, Eye } from "lucide-react";

const PastTrainingTab = ({
  pastSessions,
  loading,
  selectedMonth,
  selectedYear,
  setSelectedMonth,
  setSelectedYear,
  onSearch,
  onViewResults,
  expandedSession,
  onToggleExpand,
  sessionParticipants,
}) => {
  const months = [
    { value: 1, label: 'January' }, { value: 2, label: 'February' },
    { value: 3, label: 'March' }, { value: 4, label: 'April' },
    { value: 5, label: 'May' }, { value: 6, label: 'June' },
    { value: 7, label: 'July' }, { value: 8, label: 'August' },
    { value: 9, label: 'September' }, { value: 10, label: 'October' },
    { value: 11, label: 'November' }, { value: 12, label: 'December' }
  ];

  const years = [];
  const currentYear = new Date().getFullYear();
  for (let y = currentYear; y >= currentYear - 5; y--) {
    years.push(y);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <FileText className="w-5 h-5 mr-2" />
          Past Training Archive
        </CardTitle>
        <CardDescription>Search and view completed training sessions</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="flex-1">
            <Label>Month</Label>
            <Select value={selectedMonth?.toString()} onValueChange={(v) => setSelectedMonth(parseInt(v))}>
              <SelectTrigger>
                <SelectValue placeholder="Select month" />
              </SelectTrigger>
              <SelectContent>
                {months.map(m => (
                  <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex-1">
            <Label>Year</Label>
            <Select value={selectedYear?.toString()} onValueChange={(v) => setSelectedYear(parseInt(v))}>
              <SelectTrigger>
                <SelectValue placeholder="Select year" />
              </SelectTrigger>
              <SelectContent>
                {years.map(y => (
                  <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-end">
            <Button onClick={onSearch} disabled={loading}>
              <Search className="w-4 h-4 mr-2" />
              Search
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-500">Loading past sessions...</p>
          </div>
        ) : pastSessions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Calendar className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>No completed sessions found for the selected period</p>
          </div>
        ) : (
          <div className="space-y-4">
            {pastSessions.map(session => {
              const isExpanded = expandedSession === session.id;
              const participants = sessionParticipants?.[session.id] || [];
              
              return (
                <Card key={session.id} className="border">
                  <CardHeader className="bg-gradient-to-r from-gray-50 to-slate-50 py-3">
                    <div className="flex justify-between items-start">
                      <div className="flex items-start gap-3">
                        {onToggleExpand && (
                          <button
                            onClick={() => onToggleExpand(session.id)}
                            className="p-1 hover:bg-gray-200 rounded mt-1"
                          >
                            {isExpanded ? (
                              <ChevronDown className="w-5 h-5 text-gray-600" />
                            ) : (
                              <ChevronRight className="w-5 h-5 text-gray-600" />
                            )}
                          </button>
                        )}
                        <div>
                          <div className="flex items-center gap-2">
                            <Building className="w-4 h-4 text-gray-500" />
                            <span className="font-semibold">{session.company_name}</span>
                          </div>
                          <p className="text-sm text-gray-600 mt-1">{session.program_name}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            {session.start_date} to {session.end_date} • {session.location}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="text-sm text-gray-600 flex items-center">
                          <Users className="w-4 h-4 mr-1" />
                          {session.participant_count || participants.length || 0}
                        </div>
                        {onViewResults && (
                          <Button size="sm" variant="outline" onClick={() => onViewResults(session.id)}>
                            <Eye className="w-4 h-4 mr-1" />
                            View
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  
                  {isExpanded && participants.length > 0 && (
                    <CardContent className="pt-4">
                      <h4 className="font-semibold text-gray-900 mb-3">Participants</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                        {participants.map(p => (
                          <div key={p.id} className="p-2 bg-gray-50 rounded text-sm">
                            <p className="font-medium">{p.full_name}</p>
                            <p className="text-xs text-gray-500">{p.email}</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { PastTrainingTab };
