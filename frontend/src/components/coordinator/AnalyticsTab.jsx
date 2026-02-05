/**
 * AnalyticsTab Component - Extracted from CoordinatorDashboard
 * Displays session statistics, test results, attendance, feedback, and completion workflow
 */
import { useState } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { FileText, MessageSquare, Upload, Download, CheckCircle, FileSpreadsheet } from "lucide-react";

const AnalyticsTab = ({
  selectedSession,
  stats,
  participants,
  testResults,
  attendance,
  courseFeedback,
  coordinatorFeedbackTemplate,
  coordinatorFeedback,
  setCoordinatorFeedback,
  feedbackSubmitted,
  setFeedbackSubmitted,
  submittingFeedback,
  professionalReportStatus,
  setProfessionalReportStatus,
  generatingDOCX,
  setGeneratingDOCX,
  uploadingEdited,
  setUploadingEdited,
  completionChecklist,
  loadCompletionChecklist,
  handleSubmitCoordinatorFeedback,
  handleMarkAsCompleted,
}) => {
  if (!selectedSession) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-gray-500">Please select a session first</p>
        </CardContent>
      </Card>
    );
  }

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('en-MY', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  return (
    <>
      {/* Session Indicator Banner */}
      <Card className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
        <CardContent className="py-4">
          <div className="flex items-center gap-3">
            <div className="w-2 h-12 bg-blue-500 rounded-full"></div>
            <div>
              <p className="text-sm text-blue-600 font-medium">Currently Working On</p>
              <p className="text-lg font-bold text-gray-900">{selectedSession.company_name || 'Unknown Company'}</p>
              <p className="text-sm text-gray-600">
                {selectedSession.program_name || 'Training'} • {formatDate(selectedSession.start_date)} - {formatDate(selectedSession.end_date)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Stats Cards */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-gray-600">Total Participants</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-indigo-600">{stats.totalParticipants}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-gray-600">Attendance Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{stats.attendanceRate}%</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-gray-600">Pre-Test Pass Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{stats.preTestPassRate}%</p>
            <p className="text-xs text-gray-500 mt-1">Before Training</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-gray-600">Post-Test Pass Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{stats.postTestPassRate}%</p>
            <p className="text-xs text-gray-500 mt-1">After Training</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm text-gray-600">Improvement</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${stats.improvement >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {stats.improvement > 0 ? '+' : ''}{stats.improvement}%
            </p>
            <p className="text-xs text-gray-500 mt-1">Pass Rate Change</p>
          </CardContent>
        </Card>

        {/* Test Results Breakdown */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Test Results Overview</CardTitle>
            <CardDescription>Recent test submissions and scores</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {!testResults || testResults.length === 0 ? (
                <div className="text-center py-8">
                  <FileText className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                  <p className="text-gray-500">No test results yet</p>
                  <p className="text-sm text-gray-400 mt-1">Results will appear when participants complete tests</p>
                </div>
              ) : (
                testResults.slice(0, 8).map((result, idx) => {
                  const participant = participants.find(p => p.id === result.participant_id);
                  const scorePercentage = result.total_questions > 0 
                    ? ((result.correct_answers / result.total_questions) * 100).toFixed(0)
                    : 0;
                  
                  return (
                    <div key={idx} className="flex justify-between items-center p-3 bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg border">
                      <div className="flex-1">
                        <p className="font-semibold text-sm">
                          {participant?.full_name || 'Unknown Participant'}
                        </p>
                        <div className="flex items-center gap-3 mt-1">
                          <p className="text-xs text-gray-600">
                            {result.test_type === 'pre' ? '📝 Pre-Test' : '📋 Post-Test'}
                          </p>
                          <p className="text-xs text-gray-600">
                            Score: {result.correct_answers}/{result.total_questions} ({scorePercentage}%)
                          </p>
                        </div>
                      </div>
                      <span className={`px-3 py-1.5 rounded-full text-xs font-bold border ${
                        result.passed 
                          ? 'bg-green-100 text-green-800 border-green-300' 
                          : 'bg-red-100 text-red-800 border-red-300'
                      }`}>
                        {result.passed ? '✓ PASSED' : '✗ FAILED'}
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>

        {/* Attendance Summary */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Recent Attendance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {attendance.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No attendance records yet</p>
              ) : (
                attendance.slice(0, 5).map((record, idx) => (
                  <div key={idx} className="flex justify-between items-center p-3 bg-gray-50 rounded">
                    <div>
                      <p className="font-medium text-sm">{record.participant_name}</p>
                      <p className="text-xs text-gray-600">{new Date(record.date).toLocaleDateString()}</p>
                    </div>
                    <div className="text-xs">
                      <span className="text-green-600">In: {record.clock_in || '-'}</span>
                      <span className="mx-2">|</span>
                      <span className="text-red-600">Out: {record.clock_out || '-'}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Feedback Summary */}
      <Card className="md:col-span-2 mt-6">
        <CardHeader>
          <CardTitle>Participant Feedback Summary</CardTitle>
          <CardDescription>All participant feedback and ratings</CardDescription>
        </CardHeader>
        <CardContent>
          {!courseFeedback || courseFeedback.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-12 h-12 mx-auto text-gray-400 mb-2" />
              <p className="text-gray-500">No feedback submitted yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {courseFeedback.map((feedback, idx) => {
                const participant = participants.find(p => p.id === feedback.participant_id);
                const starRatings = feedback.responses?.filter(r => typeof r.answer === 'number') || [];
                const textResponses = feedback.responses?.filter(r => typeof r.answer === 'string') || [];
                
                return (
                  <div key={idx} className="border rounded-lg p-4 bg-purple-50">
                    <div className="flex justify-between items-start mb-3">
                      <h4 className="font-semibold text-purple-900">
                        {participant?.full_name || 'Unknown Participant'}
                      </h4>
                      <span className="text-xs text-gray-500">
                        {new Date(feedback.submitted_at).toLocaleDateString()}
                      </span>
                    </div>
                    
                    {starRatings.length > 0 && (
                      <div className="mb-3">
                        <p className="text-sm font-medium text-gray-700 mb-2">Ratings:</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {starRatings.map((rating, rIdx) => (
                            <div key={rIdx} className="flex justify-between text-sm">
                              <span className="text-gray-600 text-xs">{rating.question}:</span>
                              <span className="text-yellow-600 font-medium">
                                {'⭐'.repeat(rating.answer)} ({rating.answer}/5)
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {textResponses.length > 0 && (
                      <div>
                        <p className="text-sm font-medium text-gray-700 mb-2">Comments:</p>
                        <div className="space-y-2">
                          {textResponses.map((response, rIdx) => (
                            <div key={rIdx} className="bg-white p-2 rounded border">
                              <p className="text-xs font-medium text-gray-700">{response.question}</p>
                              <p className="text-sm text-gray-900 mt-1">{response.answer}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Coordinator Feedback Section */}
      <Card className="md:col-span-2 mt-6">
        <CardHeader>
          <CardTitle>Coordinator Feedback</CardTitle>
          <CardDescription>Provide your feedback about the training session</CardDescription>
        </CardHeader>
        <CardContent>
          {coordinatorFeedbackTemplate && (
            <div className="space-y-4">
              {coordinatorFeedbackTemplate.questions?.map((question) => (
                <div key={question.id} className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    {question.question}
                    {question.type === 'rating' && <span className="text-gray-500 ml-1">(Rate 1-{question.scale})</span>}
                  </label>
                  {question.type === 'rating' ? (
                    <div className="flex gap-2">
                      {[...Array(question.scale)].map((_, i) => (
                        <button
                          key={i}
                          onClick={() => setCoordinatorFeedback({...coordinatorFeedback, [question.id]: i + 1})}
                          className={`w-10 h-10 rounded-full font-bold ${
                            coordinatorFeedback[question.id] === i + 1
                              ? 'bg-blue-600 text-white'
                              : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                          }`}
                          disabled={feedbackSubmitted}
                        >
                          {i + 1}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <textarea
                      value={coordinatorFeedback[question.id] || ''}
                      onChange={(e) => setCoordinatorFeedback({...coordinatorFeedback, [question.id]: e.target.value})}
                      className="w-full p-2 border rounded-md"
                      rows={3}
                      disabled={feedbackSubmitted}
                      placeholder="Enter your response..."
                    />
                  )}
                </div>
              ))}
              
              <div className="flex items-center gap-2 mt-6">
                {feedbackSubmitted ? (
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                      ✓ Feedback Submitted
                    </span>
                    <Button
                      onClick={() => setFeedbackSubmitted(false)}
                      variant="outline"
                      size="sm"
                    >
                      Edit
                    </Button>
                  </div>
                ) : (
                  <Button
                    onClick={handleSubmitCoordinatorFeedback}
                    disabled={submittingFeedback}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {submittingFeedback ? "Submitting..." : "Submit Feedback"}
                  </Button>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Report Generation Section */}
      <Card className="md:col-span-2 mt-6">
        <CardHeader>
          <CardTitle>Training Report Generation</CardTitle>
          <CardDescription>Generate comprehensive training report with all session data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Excel Feedback Export */}
            <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex-1">
                <h5 className="font-medium text-green-900">📊 Export Feedback Excel</h5>
                <p className="text-sm text-green-700">Download complete feedback data (Soalan Maklum Balas) in Excel format</p>
              </div>
              <Button
                onClick={async () => {
                  if (!selectedSession) return;
                  try {
                    const response = await axiosInstance.get(
                      `/sessions/${selectedSession.id}/export-feedback-excel`,
                      { responseType: 'blob' }
                    );
                    const url = window.URL.createObjectURL(new Blob([response.data]));
                    const link = document.createElement('a');
                    link.href = url;
                    const companyName = (selectedSession.company_name || 'Session').replace(/\s+/g, '_').substring(0, 20);
                    const dateStr = selectedSession.start_date ? selectedSession.start_date.substring(0, 10).replace(/-/g, '') : '';
                    link.download = `FEEDBACK_REPORT_${companyName}_${dateStr}.xlsx`;
                    document.body.appendChild(link);
                    link.click();
                    link.remove();
                    window.URL.revokeObjectURL(url);
                    toast.success("Feedback report exported!");
                  } catch (error) {
                    toast.error("Failed to export feedback report");
                  }
                }}
                className="bg-green-600 hover:bg-green-700"
                data-testid="export-feedback-excel-btn"
              >
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                Export Excel
              </Button>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-semibold text-blue-900 mb-2">Report Generation Workflow:</h4>
              <ol className="list-decimal list-inside space-y-1 text-sm text-blue-800">
                <li>Generate DOCX report with all session data</li>
                <li>Download and edit the report offline (add photos, notes, etc.)</li>
                <li>Upload the edited report as PDF</li>
                <li>Report will be visible in Supervisor and Admin portals</li>
              </ol>
            </div>

            <div className="space-y-3">
              {/* Step 1: Generate DOCX */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <h5 className="font-medium text-gray-900">Step 1: Generate DOCX Report</h5>
                  <p className="text-sm text-gray-600">Creates a Word document with all session data</p>
                </div>
                <Button
                  onClick={async () => {
                    if (!selectedSession) return;
                    setGeneratingDOCX(true);
                    try {
                      await axiosInstance.post(`/training-reports/${selectedSession.id}/generate-docx`);
                      toast.success("Report generated! Click download to get the file.");
                      setProfessionalReportStatus({...professionalReportStatus, docx_generated: true});
                    } catch (error) {
                      toast.error(error.response?.data?.detail || "Failed to generate report");
                    } finally {
                      setGeneratingDOCX(false);
                    }
                  }}
                  disabled={generatingDOCX}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {generatingDOCX ? "Generating..." : "Generate DOCX"}
                </Button>
              </div>

              {/* Step 2: Download DOCX */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <h5 className="font-medium text-gray-900">Step 2: Download DOCX</h5>
                  <p className="text-sm text-gray-600">Download to edit offline</p>
                </div>
                <Button
                  onClick={async () => {
                    if (!selectedSession) return;
                    try {
                      const response = await axiosInstance.get(
                        `/training-reports/${selectedSession.id}/download-docx`,
                        { responseType: 'blob' }
                      );
                      const url = window.URL.createObjectURL(new Blob([response.data]));
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = `Training_Report_${selectedSession.name.replace(/\s+/g, '_')}.docx`;
                      document.body.appendChild(link);
                      link.click();
                      link.remove();
                      window.URL.revokeObjectURL(url);
                      toast.success("Report downloaded!");
                    } catch (error) {
                      toast.error("Failed to download report");
                    }
                  }}
                  variant="outline"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download DOCX
                </Button>
              </div>

              {/* Step 3: Upload Final PDF */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <h5 className="font-medium text-gray-900">Step 3: Upload Final PDF</h5>
                  <p className="text-sm text-gray-600">After editing, upload the final PDF version</p>
                </div>
                <div>
                  <input
                    id={`upload-report-pdf-analytics-${selectedSession?.id}`}
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file || !selectedSession) return;
                      
                      if (!file.name.toLowerCase().endsWith('.pdf')) {
                        toast.error("Please upload a PDF file");
                        return;
                      }

                      setUploadingEdited(true);
                      try {
                        const formData = new FormData();
                        formData.append('file', file);
                        
                        await axiosInstance.post(
                          `/training-reports/${selectedSession.id}/upload-final-pdf`,
                          formData,
                          { headers: { 'Content-Type': 'multipart/form-data' } }
                        );
                        
                        await loadCompletionChecklist(selectedSession.id);
                        
                        toast.success("✓ Final report uploaded successfully! You can now mark the training as completed.");
                        setProfessionalReportStatus({
                          ...professionalReportStatus,
                          pdf_submitted: true
                        });
                      } catch (error) {
                        console.error("Upload error:", error);
                        toast.error(error.response?.data?.detail || "Failed to upload report");
                      } finally {
                        setUploadingEdited(false);
                      }
                      e.target.value = null;
                    }}
                  />
                  <Button 
                    variant="outline" 
                    disabled={uploadingEdited}
                    onClick={() => document.getElementById(`upload-report-pdf-analytics-${selectedSession?.id}`)?.click()}
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    {uploadingEdited ? "Uploading..." : "Upload PDF"}
                  </Button>
                </div>
              </div>

              {professionalReportStatus.pdf_submitted && (
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-blue-800 font-medium">✓ Final report uploaded successfully!</p>
                  <p className="text-sm text-blue-700 mt-1">You can now mark the training as completed below.</p>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Mark as Completed Section */}
      {professionalReportStatus.pdf_submitted && (
        <Card className="bg-blue-50 border-blue-200 mt-6">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <div>
                <h4 className="font-semibold text-blue-900 text-lg">Complete Training & Archive</h4>
                <p className="text-sm text-blue-800">
                  Review the checklist below before marking this session as completed.
                </p>
              </div>
              
              {selectedSession?.completion_status === 'completed' ? (
                <div className="bg-green-100 border border-green-400 rounded-lg p-3">
                  <p className="text-green-900 font-semibold">✓ Training Marked as Completed</p>
                  <p className="text-green-700 text-sm">
                    This session has been archived and moved to Past Training records.
                  </p>
                </div>
              ) : (
                <>
                  {/* Completion Checklist */}
                  <div className="bg-white rounded-lg p-4 text-left max-w-md mx-auto">
                    <h5 className="font-medium text-gray-900 mb-3">Pre-completion Checklist:</h5>
                    <div className="space-y-2">
                      <div className={`flex items-center gap-2 ${completionChecklist?.all_attendance ? 'text-green-700' : 'text-gray-500'}`}>
                        <CheckCircle className={`w-5 h-5 ${completionChecklist?.all_attendance ? 'text-green-600' : 'text-gray-400'}`} />
                        <span className="text-sm">All attendance recorded</span>
                      </div>
                      <div className={`flex items-center gap-2 ${completionChecklist?.all_tests ? 'text-green-700' : 'text-gray-500'}`}>
                        <CheckCircle className={`w-5 h-5 ${completionChecklist?.all_tests ? 'text-green-600' : 'text-gray-400'}`} />
                        <span className="text-sm">All tests completed</span>
                      </div>
                      <div className={`flex items-center gap-2 ${completionChecklist?.report_uploaded ? 'text-green-700' : 'text-gray-500'}`}>
                        <CheckCircle className={`w-5 h-5 ${completionChecklist?.report_uploaded ? 'text-green-600' : 'text-gray-400'}`} />
                        <span className="text-sm">Final report uploaded</span>
                      </div>
                    </div>
                  </div>

                  <Button
                    onClick={handleMarkAsCompleted}
                    className="bg-green-600 hover:bg-green-700"
                    size="lg"
                  >
                    <CheckCircle className="w-5 h-5 mr-2" />
                    Mark Training as Completed
                  </Button>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
};

export { AnalyticsTab };
