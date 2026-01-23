/**
 * ReportsTab Component - Extracted from AdminDashboard
 * Manages training reports archive with search and filtering
 */
import { useState, useEffect } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Search, FileText, Download, Building2, Book } from "lucide-react";

const ReportsTab = ({
  companies,
  programs,
  isActive,
}) => {
  // State
  const [allReports, setAllReports] = useState([]);
  const [loadingReports, setLoadingReports] = useState(false);
  const [reportsSearch, setReportsSearch] = useState("");
  const [filterCompany, setFilterCompany] = useState("all");
  const [filterProgram, setFilterProgram] = useState("all");
  const [filterStartDate, setFilterStartDate] = useState("");
  const [filterEndDate, setFilterEndDate] = useState("");
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportDetailsOpen, setReportDetailsOpen] = useState(false);

  // Load reports when tab becomes active
  useEffect(() => {
    if (isActive && allReports.length === 0) {
      loadAllReports();
    }
  }, [isActive]);

  const loadAllReports = async () => {
    setLoadingReports(true);
    try {
      const params = {};
      if (reportsSearch) params.search = reportsSearch;
      if (filterCompany && filterCompany !== "all") params.company_id = filterCompany;
      if (filterProgram && filterProgram !== "all") params.program_id = filterProgram;
      if (filterStartDate) params.start_date = filterStartDate;
      if (filterEndDate) params.end_date = filterEndDate;

      const response = await axiosInstance.get("/training-reports/all", { params });
      setAllReports(response.data.reports || []);
    } catch (error) {
      console.error("Failed to load reports:", error);
      toast.error("Failed to load training reports");
    } finally {
      setLoadingReports(false);
    }
  };

  const handleDownloadReportPDF = async (sessionId) => {
    try {
      const response = await axiosInstance.get(`/training-reports/${sessionId}/download`, {
        responseType: 'blob'
      });
      
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'training_report.pdf';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success("Report downloaded successfully");
    } catch (error) {
      console.error("Download error:", error);
      toast.error(error.response?.data?.detail || "Failed to download report");
    }
  };

  const handleViewReportDetails = (report) => {
    setSelectedReport(report);
    setReportDetailsOpen(true);
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Training Reports Archive</CardTitle>
          <CardDescription>
            Search and access all submitted training reports
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Search and Filters */}
          <div className="mb-6 space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <Input
                  placeholder="Search by session name, coordinator, company, program, location..."
                  value={reportsSearch}
                  onChange={(e) => setReportsSearch(e.target.value)}
                  className="w-full"
                />
              </div>
              <Button onClick={loadAllReports} variant="outline">
                <Search className="w-4 h-4 mr-2" />
                Search
              </Button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Select value={filterCompany} onValueChange={setFilterCompany}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by Company" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Companies</SelectItem>
                  {companies.map((company) => (
                    <SelectItem key={company.id} value={company.id}>
                      {company.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={filterProgram} onValueChange={setFilterProgram}>
                <SelectTrigger>
                  <SelectValue placeholder="Filter by Program" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Programs</SelectItem>
                  {programs.map((program) => (
                    <SelectItem key={program.id} value={program.id}>
                      {program.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Input
                type="date"
                placeholder="Start Date"
                value={filterStartDate}
                onChange={(e) => setFilterStartDate(e.target.value)}
              />

              <Input
                type="date"
                placeholder="End Date"
                value={filterEndDate}
                onChange={(e) => setFilterEndDate(e.target.value)}
              />
            </div>

            {allReports.length > 0 && (
              <p className="text-sm text-gray-600">
                Found {allReports.length} training report{allReports.length !== 1 ? 's' : ''}
              </p>
            )}
          </div>

          {/* Reports Grid */}
          {loadingReports ? (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          ) : allReports.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-16 h-16 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600">No training reports found</p>
              <p className="text-sm text-gray-500 mt-2">
                Reports will appear here once coordinators submit them
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {allReports.map((report) => (
                <Card key={report.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">{report.session_name}</CardTitle>
                    <CardDescription className="space-y-1">
                      <div className="flex items-center text-xs">
                        <Building2 className="w-3 h-3 mr-1" />
                        {report.company_name}
                      </div>
                      <div className="flex items-center text-xs">
                        <Book className="w-3 h-3 mr-1" />
                        {report.program_name}
                      </div>
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="text-sm space-y-1">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Coordinator:</span>
                        <span className="font-medium">{report.coordinator_name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Location:</span>
                        <span className="font-medium">{report.session_location}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Dates:</span>
                        <span className="font-medium text-xs">
                          {report.session_start_date} to {report.session_end_date}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Participants:</span>
                        <span className="font-medium">{report.participant_count}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Submitted:</span>
                        <span className="font-medium text-xs">
                          {new Date(report.submitted_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    <div className="pt-3 border-t space-y-2">
                      <Button
                        onClick={() => handleDownloadReportPDF(report.session_id)}
                        className="w-full bg-green-600 hover:bg-green-700"
                        size="sm"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download PDF
                      </Button>
                      <Button
                        onClick={() => handleViewReportDetails(report)}
                        variant="outline"
                        className="w-full"
                        size="sm"
                      >
                        <FileText className="w-4 h-4 mr-2" />
                        View Details
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Report Details Dialog */}
      <Dialog open={reportDetailsOpen} onOpenChange={setReportDetailsOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Training Report Details</DialogTitle>
            <DialogDescription>
              {selectedReport?.session_name}
            </DialogDescription>
          </DialogHeader>
          {selectedReport && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-semibold text-gray-700">Company</p>
                  <p className="text-sm">{selectedReport.company_name}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-700">Program</p>
                  <p className="text-sm">{selectedReport.program_name}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-700">Location</p>
                  <p className="text-sm">{selectedReport.session_location}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-700">Coordinator</p>
                  <p className="text-sm">{selectedReport.coordinator_name}</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-700">Training Period</p>
                  <p className="text-sm">
                    {selectedReport.session_start_date} to {selectedReport.session_end_date}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-700">Participants</p>
                  <p className="text-sm">{selectedReport.participant_count} participants</p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-700">Submitted Date</p>
                  <p className="text-sm">
                    {new Date(selectedReport.submitted_at).toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-700">Status</p>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    {selectedReport.status}
                  </span>
                </div>
              </div>

              <div className="border-t pt-4">
                <p className="text-sm font-semibold text-gray-700 mb-2">Files</p>
                <div className="space-y-2">
                  {selectedReport.pdf_filename && (
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div className="flex items-center">
                        <FileText className="w-5 h-5 text-red-600 mr-2" />
                        <span className="text-sm font-medium">Final Report (PDF)</span>
                      </div>
                      <Button
                        onClick={() => handleDownloadReportPDF(selectedReport.session_id)}
                        size="sm"
                        variant="outline"
                      >
                        <Download className="w-4 h-4 mr-1" />
                        Download
                      </Button>
                    </div>
                  )}
                  {selectedReport.docx_filename && (
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div className="flex items-center">
                        <FileText className="w-5 h-5 text-blue-600 mr-2" />
                        <span className="text-sm font-medium">Original Report (DOCX)</span>
                      </div>
                      <span className="text-xs text-gray-500">{selectedReport.docx_filename}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export { ReportsTab };
