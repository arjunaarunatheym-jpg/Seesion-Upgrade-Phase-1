/**
 * ReportTab Component - Shows Pending and Past Reports
 * Clicking a pending report navigates to Analytics tab for that session
 */
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { FileText, Download, Clock, CheckCircle, ChevronRight, Search, Calendar } from "lucide-react";
import { axiosInstance } from "../../App";

const ReportTab = ({
  sessions,
  onSelectSessionForReport, // Function to switch to Analytics tab with selected session
  primaryColor,
}) => {
  const [pendingReports, setPendingReports] = useState([]);
  const [pastReports, setPastReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  const months = [
    { value: 1, label: 'January' }, { value: 2, label: 'February' },
    { value: 3, label: 'March' }, { value: 4, label: 'April' },
    { value: 5, label: 'May' }, { value: 6, label: 'June' },
    { value: 7, label: 'July' }, { value: 8, label: 'August' },
    { value: 9, label: 'September' }, { value: 10, label: 'October' },
    { value: 11, label: 'November' }, { value: 12, label: 'December' }
  ];

  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 2 + i);

  useEffect(() => {
    loadReportStatuses();
  }, [sessions]);

  useEffect(() => {
    filterPastReports();
  }, [selectedMonth, selectedYear, sessions]);

  const loadReportStatuses = async () => {
    setLoading(true);
    try {
      const pending = [];
      const past = [];

      for (const session of sessions) {
        try {
          const response = await axiosInstance.get(`/training-reports/${session.id}/status`);
          const reportData = {
            ...session,
            reportStatus: response.data
          };

          if (response.data.pdf_submitted || response.data.status === 'submitted') {
            past.push(reportData);
          } else {
            pending.push(reportData);
          }
        } catch (error) {
          // No report exists - it's pending
          pending.push({ ...session, reportStatus: { docx_generated: false, pdf_submitted: false } });
        }
      }

      setPendingReports(pending);
      setPastReports(past);
    } catch (error) {
      console.error("Failed to load report statuses:", error);
    } finally {
      setLoading(false);
    }
  };

  const filterPastReports = () => {
    // Filter past reports by selected month/year based on session end_date
    const filtered = pastReports.filter(report => {
      if (!report.end_date) return false;
      const endDate = new Date(report.end_date);
      return endDate.getMonth() + 1 === selectedMonth && endDate.getFullYear() === selectedYear;
    });
    return filtered;
  };

  const handleDownloadReport = async (sessionId, filename) => {
    try {
      const response = await axiosInstance.get(`/training-reports/${sessionId}/download-pdf`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || `Training_Report_${sessionId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download failed:", error);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-MY', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading reports...</p>
        </CardContent>
      </Card>
    );
  }

  const filteredPastReports = filterPastReports();

  return (
    <div className="space-y-6">
      {/* Pending Reports */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Clock className="w-5 h-5 text-amber-500" />
            Pending Reports ({pendingReports.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {pendingReports.length === 0 ? (
            <p className="text-gray-500 text-center py-6">No pending reports. All reports submitted!</p>
          ) : (
            <div className="space-y-2">
              {pendingReports.map((session) => (
                <button
                  key={session.id}
                  data-testid={`pending-report-${session.id}`}
                  onClick={() => {
                    console.log("Clicking pending report for session:", session.id);
                    onSelectSessionForReport(session);
                  }}
                  className="w-full flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-lg cursor-pointer hover:bg-amber-100 transition-colors text-left"
                >
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{session.company_name || 'Unknown Company'}</p>
                    <p className="text-sm text-gray-600">
                      {session.program_name || 'Training'} • {formatDate(session.start_date)} - {formatDate(session.end_date)}
                    </p>
                    <div className="flex gap-2 mt-1">
                      {session.reportStatus?.docx_generated ? (
                        <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700">DOCX Generated</Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs bg-gray-100 text-gray-600">Not Started</Badge>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Past/Submitted Reports */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <CardTitle className="flex items-center gap-2 text-lg">
              <CheckCircle className="w-5 h-5 text-green-500" />
              Submitted Reports
            </CardTitle>
            <div className="flex items-center gap-2">
              <Select value={selectedMonth.toString()} onValueChange={(v) => setSelectedMonth(parseInt(v))}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {months.map(m => (
                    <SelectItem key={m.value} value={m.value.toString()}>{m.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={selectedYear.toString()} onValueChange={(v) => setSelectedYear(parseInt(v))}>
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {years.map(y => (
                    <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredPastReports.length === 0 ? (
            <p className="text-gray-500 text-center py-6">
              No submitted reports for {months.find(m => m.value === selectedMonth)?.label} {selectedYear}
            </p>
          ) : (
            <div className="space-y-2">
              {filteredPastReports.map((session) => (
                <div
                  key={session.id}
                  className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg"
                >
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{session.company_name || 'Unknown Company'}</p>
                    <p className="text-sm text-gray-600">
                      {session.program_name || 'Training'} • {formatDate(session.end_date)}
                    </p>
                    <Badge variant="outline" className="text-xs bg-green-100 text-green-700 mt-1">Submitted</Badge>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownloadReport(session.id, session.reportStatus?.pdf_filename)}
                    className="border-green-400 text-green-700 hover:bg-green-100"
                  >
                    <Download className="w-4 h-4 mr-1" />
                    Download
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export { ReportTab };
