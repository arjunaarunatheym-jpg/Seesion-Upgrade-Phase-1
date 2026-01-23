/**
 * ReportTab Component - Extracted from CoordinatorDashboard
 * Handles training photo uploads and report generation (DOCX/PDF workflow + AI)
 */
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Upload, Trash2, FileText, Sparkles, Save, Send } from "lucide-react";

const ReportTab = ({
  selectedSession,
  trainingReport,
  setTrainingReport,
  aiGeneratedReport,
  setAiGeneratedReport,
  professionalReportStatus,
  generatingDOCX,
  uploadingEdited,
  submittingFinal,
  generatingReport,
  primaryColor,
  // Handlers
  handlePhotoUpload,
  handleGenerateProfessionalReport,
  handleDownloadDOCX,
  handleUploadEditedDOCX,
  handleSubmitFinalReport,
  handleGenerateAIReport,
  handleSaveReport,
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

  const photoFields = [
    { key: 'group_photo', label: '1. Group Photo *', alt: 'Group' },
    { key: 'theory_photo_1', label: '2. Theory Session Photo 1 *', alt: 'Theory 1' },
    { key: 'theory_photo_2', label: '3. Theory Session Photo 2 *', alt: 'Theory 2' },
    { key: 'practical_photo_1', label: '4. Practical Session Photo 1 *', alt: 'Practical 1' },
    { key: 'practical_photo_2', label: '5. Practical Session Photo 2 *', alt: 'Practical 2' },
    { key: 'practical_photo_3', label: '6. Practical Session Photo 3 *', alt: 'Practical 3' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Training Completion Report - {selectedSession.name}</CardTitle>
        <CardDescription>
          Upload training photos and generate a comprehensive report
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Photo Upload Section */}
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Training Photos</h3>
          <p className="text-sm text-gray-600">Upload photos from the training session (max 5MB each)</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {photoFields.map((field) => (
              <div key={field.key} className="space-y-2">
                <Label>{field.label}</Label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-indigo-500 transition-colors">
                  {trainingReport[field.key] ? (
                    <div className="relative">
                      <img src={trainingReport[field.key]} alt={field.alt} className="w-full h-40 object-cover rounded" />
                      <Button
                        size="sm"
                        variant="destructive"
                        className="absolute top-2 right-2"
                        onClick={() => setTrainingReport(prev => ({ ...prev, [field.key]: "" }))}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ) : (
                    <label className="cursor-pointer">
                      <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                      <p className="text-sm text-gray-600">Click to upload</p>
                      <input
                        type="file"
                        accept="image/*"
                        capture="environment"
                        className="hidden"
                        onChange={(e) => handlePhotoUpload(e, field.key)}
                      />
                    </label>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Professional DOCX Report Workflow */}
        <div className="space-y-4 border-t pt-6">
          <div>
            <h3 className="font-semibold text-lg text-indigo-900">📄 Professional Training Report (DOCX → PDF)</h3>
            <p className="text-sm text-gray-600">Generate auto-filled report, edit in MS Word, and submit as PDF</p>
          </div>

          {/* Step 1: Generate DOCX */}
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="pt-6">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-semibold text-blue-900">Step 1: Generate Report</p>
                  <p className="text-sm text-gray-700">Creates a professional DOCX with all your session data pre-filled</p>
                  {professionalReportStatus.docx_generated && (
                    <p className="text-xs text-green-700 mt-1">✓ Report generated: {professionalReportStatus.docx_filename}</p>
                  )}
                </div>
                <Button
                  onClick={handleGenerateProfessionalReport}
                  disabled={generatingDOCX || professionalReportStatus.pdf_submitted}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {generatingDOCX ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Generating...
                    </>
                  ) : (
                    <>
                      <FileText className="w-4 h-4 mr-2" />
                      Generate DOCX
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Step 2: Download & Edit */}
          <Card className="bg-purple-50 border-purple-200">
            <CardContent className="pt-6">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-semibold text-purple-900">Step 2: Download & Edit</p>
                  <p className="text-sm text-gray-700">Download, open in MS Word, add comments & photos, save</p>
                </div>
                <Button
                  onClick={handleDownloadDOCX}
                  disabled={!professionalReportStatus.docx_generated || professionalReportStatus.pdf_submitted}
                  variant="outline"
                  className="border-purple-400 text-purple-700 hover:bg-purple-100"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Download DOCX
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Step 3: Upload Edited */}
          <Card className="bg-amber-50 border-amber-200">
            <CardContent className="pt-6">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-semibold text-amber-900">Step 3: Upload Edited Report</p>
                  <p className="text-sm text-gray-700">Upload your edited DOCX file</p>
                  {professionalReportStatus.edited_uploaded && (
                    <p className="text-xs text-green-700 mt-1">✓ Edited report uploaded: {professionalReportStatus.edited_docx_filename}</p>
                  )}
                </div>
                <label>
                  <input
                    type="file"
                    accept=".docx"
                    onChange={handleUploadEditedDOCX}
                    disabled={!professionalReportStatus.docx_generated || professionalReportStatus.pdf_submitted || uploadingEdited}
                    className="hidden"
                  />
                  <Button
                    as="span"
                    disabled={!professionalReportStatus.docx_generated || professionalReportStatus.pdf_submitted || uploadingEdited}
                    variant="outline"
                    className="border-amber-400 text-amber-700 hover:bg-amber-100 cursor-pointer"
                  >
                    {uploadingEdited ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-amber-700 mr-2"></div>
                        Uploading...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 mr-2" />
                        Upload Edited DOCX
                      </>
                    )}
                  </Button>
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Step 4: Submit Final */}
          <Card className="bg-green-50 border-green-200">
            <CardContent className="pt-6">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-semibold text-green-900">Step 4: Submit Final Report</p>
                  <p className="text-sm text-gray-700">Converts to PDF and sends to supervisors & admins</p>
                  {professionalReportStatus.pdf_submitted && (
                    <p className="text-xs text-green-700 mt-1">✓ Report submitted as PDF: {professionalReportStatus.pdf_filename}</p>
                  )}
                </div>
                <Button
                  onClick={handleSubmitFinalReport}
                  disabled={!professionalReportStatus.docx_generated || professionalReportStatus.pdf_submitted || submittingFinal}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {submittingFinal ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Submitting...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Submit Final Report
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Divider */}
        <div className="border-t my-8"></div>

        {/* AI Report Generation */}
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-lg">AI-Powered Report (Optional)</h3>
              <p className="text-sm text-gray-600">Quick text-based report generation</p>
            </div>
            <Button
              onClick={handleGenerateAIReport}
              disabled={generatingReport}
              style={{ backgroundColor: primaryColor }}
            >
              {generatingReport ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Generate AI Report
                </>
              )}
            </Button>
          </div>

          <Textarea
            value={aiGeneratedReport}
            onChange={(e) => setAiGeneratedReport(e.target.value)}
            placeholder="Click 'Generate AI Report' to create a comprehensive training report, or write your own..."
            className="min-h-[400px] font-mono text-sm"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 border-t pt-6">
          <Button
            onClick={() => handleSaveReport("draft")}
            variant="outline"
            className="flex-1"
            disabled={trainingReport.status === "submitted"}
          >
            <Save className="w-4 h-4 mr-2" />
            Save as Draft
          </Button>
          <Button
            onClick={() => handleSaveReport("submitted")}
            style={{ backgroundColor: primaryColor }}
            className="flex-1"
            disabled={trainingReport.status === "submitted"}
          >
            <Send className="w-4 h-4 mr-2" />
            Submit Final Report
          </Button>
        </div>

        {trainingReport.status === "submitted" && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
            <p className="text-green-800 font-semibold">✓ Report Submitted Successfully</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { ReportTab };
