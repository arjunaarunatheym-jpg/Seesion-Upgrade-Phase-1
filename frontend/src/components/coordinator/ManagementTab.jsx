/**
 * ManagementTab Component - Extracted from CoordinatorDashboard
 * Manages session details, participants, attendance, tests, and vehicle checklists
 */
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Upload, Edit, Clock, Users } from "lucide-react";

const ManagementTab = ({
  selectedSession,
  participants,
  attendance,
  testResults,
  sessionAccess,
  allChecklists,
  checklistIssues,
  certificateStatuses,
  uploadingCertificates,
  attendanceStatus,
  updatingAttendance,
  uploading,
  uploadDialogOpen,
  setUploadDialogOpen,
  primaryColor,
  // Handlers
  handleBulkUpload,
  handleToggleAccess,
  handleMarkAttendance,
  handleCertificateUpload,
  setEditingSession,
  setEditSessionDialogOpen,
  setAddParticipantDialogOpen,
}) => {
  const [expandedChecklist, setExpandedChecklist] = useState(null);
  const [expandedVehicleIssue, setExpandedVehicleIssue] = useState(null);

  if (!selectedSession) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-gray-500">Please select a session first</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Session Details Card */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <CardTitle>{selectedSession.name}</CardTitle>
              <CardDescription>{selectedSession.location}</CardDescription>
            </div>
            <div className="flex gap-2">
              <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <Upload className="w-4 h-4 mr-2" />
                    Bulk Upload
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Bulk Upload Participants</DialogTitle>
                    <DialogDescription>
                      Upload an Excel file (.xlsx or .xls) with participant data
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="bg-blue-50 p-4 rounded-lg space-y-2">
                      <p className="text-sm font-medium text-blue-900">Excel Format Required:</p>
                      <ul className="text-sm text-blue-700 space-y-1">
                        <li>• Column 1: <strong>Full Name</strong></li>
                        <li>• Column 2: <strong>IC</strong> (UPPERCASE, no dashes)</li>
                        <li>• Column 3: <strong>Company Name</strong></li>
                      </ul>
                      <p className="text-xs text-blue-600 mt-2">
                        Note: New companies will be created automatically if not found
                      </p>
                    </div>
                    
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                      <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                      <label className="cursor-pointer">
                        <span className="text-sm text-gray-600">
                          {uploading ? "Uploading..." : "Click to select Excel file"}
                        </span>
                        <Input
                          type="file"
                          accept=".xlsx,.xls"
                          onChange={handleBulkUpload}
                          disabled={uploading}
                          className="hidden"
                        />
                      </label>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
              
              <Button
                onClick={() => {
                  setEditingSession({ ...selectedSession });
                  setEditSessionDialogOpen(true);
                }}
                variant="outline"
              >
                <Edit className="w-4 h-4 mr-2" />
                Edit Session
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Start Date</p>
              <p className="font-semibold">{new Date(selectedSession.start_date).toLocaleDateString()}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">End Date</p>
              <p className="font-semibold">{new Date(selectedSession.end_date).toLocaleDateString()}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Release Controls */}
      <Card className="border-indigo-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-600" />
            Release Controls
          </CardTitle>
          <CardDescription>Control when participants can access tests and feedback</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Pre-Test */}
            <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
              <div>
                <p className="font-semibold text-gray-900">Pre-Test</p>
                <p className="text-sm text-gray-600">Initial assessment before training</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={sessionAccess.some(a => a.can_access_pre_test)}
                  onChange={(e) => handleToggleAccess('pre_test', e.target.checked)}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
              </label>
            </div>

            {/* Post-Test */}
            <div className="flex items-center justify-between p-4 bg-green-50 rounded-lg">
              <div>
                <p className="font-semibold text-gray-900">Post-Test</p>
                <p className="text-sm text-gray-600">Final assessment after training</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={sessionAccess.some(a => a.can_access_post_test)}
                  onChange={(e) => handleToggleAccess('post_test', e.target.checked)}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-600"></div>
              </label>
            </div>

            {/* Feedback */}
            <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg">
              <div>
                <p className="font-semibold text-gray-900">Feedback Form</p>
                <p className="text-sm text-gray-600">Training feedback and evaluation</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={sessionAccess.some(a => a.can_access_feedback)}
                  onChange={(e) => handleToggleAccess('feedback', e.target.checked)}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
              </label>
            </div>

            {/* Clock Out */}
            <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
              <div>
                <p className="font-semibold text-gray-900">Clock Out</p>
                <p className="text-sm text-gray-600">Release clock out for participants</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={sessionAccess.some(a => a.can_clock_out)}
                  onChange={(e) => handleToggleAccess('clock_out', e.target.checked)}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Session Summary Statistics */}
      <Card className="bg-gradient-to-r from-indigo-50 to-purple-50">
        <CardHeader>
          <CardTitle>Session Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-white rounded-lg shadow-sm">
              <p className="text-2xl font-bold text-indigo-600">{participants.length}</p>
              <p className="text-sm text-gray-600 mt-1">Total Participants</p>
            </div>
            <div className="text-center p-4 bg-white rounded-lg shadow-sm">
              <p className="text-2xl font-bold text-blue-600">
                {testResults.filter(r => r.test_type === 'pre').length}/{participants.length}
              </p>
              <p className="text-sm text-gray-600 mt-1">Pre-Test Completed</p>
            </div>
            <div className="text-center p-4 bg-white rounded-lg shadow-sm">
              <p className="text-2xl font-bold text-green-600">
                {testResults.filter(r => r.test_type === 'post').length}/{participants.length}
              </p>
              <p className="text-sm text-gray-600 mt-1">Post-Test Completed</p>
            </div>
            <div className="text-center p-4 bg-white rounded-lg shadow-sm">
              <p className="text-2xl font-bold text-purple-600">
                {attendance.filter((v, i, a) => a.findIndex(t => t.participant_id === v.participant_id) === i).length}/{participants.length}
              </p>
              <p className="text-sm text-gray-600 mt-1">Attendance Records</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Participants */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Participants ({participants.length})</CardTitle>
              <CardDescription>All participants enrolled in this session</CardDescription>
            </div>
            <Button
              onClick={() => setAddParticipantDialogOpen(true)}
              variant="outline"
              size="sm"
              style={{ borderColor: primaryColor, color: primaryColor }}
            >
              <Users className="w-4 h-4 mr-2" />
              Add Participant
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {participants.length === 0 ? (
            <div className="text-center py-8">
              <Users className="w-12 h-12 mx-auto text-gray-400 mb-2" />
              <p className="text-gray-500">No participants assigned yet</p>
              <Button
                onClick={() => setAddParticipantDialogOpen(true)}
                variant="outline"
                className="mt-4"
              >
                Add First Participant
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="text-left p-3 font-semibold">Participant Name</th>
                    <th className="text-left p-3 font-semibold">ID Number</th>
                    <th className="text-center p-3 font-semibold">Attendance</th>
                    <th className="text-center p-3 font-semibold">Pre-Test</th>
                    <th className="text-center p-3 font-semibold">Post-Test</th>
                    <th className="text-center p-3 font-semibold">Feedback</th>
                    <th className="text-center p-3 font-semibold">Certificate</th>
                  </tr>
                </thead>
                <tbody>
                  {participants.map((p) => {
                    const preTest = testResults.find(r => r.participant_id === p.id && r.test_type === 'pre');
                    const postTest = testResults.find(r => r.participant_id === p.id && r.test_type === 'post');
                    const access = sessionAccess.find(a => a.participant_id === p.id);
                    
                    return (
                      <tr key={p.id} className="border-b hover:bg-gray-50">
                        <td className="p-3">
                          <p className="font-medium text-gray-900">{p.full_name}</p>
                          <p className="text-xs text-gray-500">{p.email}</p>
                        </td>
                        <td className="p-3 text-gray-700">{p.id_number || 'N/A'}</td>
                        <td className="p-3 text-center">
                          <div className="flex flex-col gap-1 items-center">
                            {attendanceStatus[p.id] === 'absent' ? (
                              <>
                                <span className="px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-800">
                                  ✗ ABSENT
                                </span>
                                <Button
                                  onClick={() => handleMarkAttendance(p.id, 'present')}
                                  disabled={updatingAttendance[p.id]}
                                  size="sm"
                                  variant="outline"
                                  className="text-xs h-6"
                                >
                                  {updatingAttendance[p.id] ? "..." : "Mark Present"}
                                </Button>
                              </>
                            ) : attendanceStatus[p.id] === 'present' ? (
                              <>
                                <span className="px-2 py-1 rounded text-xs font-bold bg-green-100 text-green-800">
                                  ✓ PRESENT
                                </span>
                                <Button
                                  onClick={() => handleMarkAttendance(p.id, 'absent')}
                                  disabled={updatingAttendance[p.id]}
                                  size="sm"
                                  variant="outline"
                                  className="text-xs h-6"
                                >
                                  {updatingAttendance[p.id] ? "..." : "Mark Absent"}
                                </Button>
                              </>
                            ) : (
                              <div className="flex gap-1">
                                <Button
                                  onClick={() => handleMarkAttendance(p.id, 'present')}
                                  disabled={updatingAttendance[p.id]}
                                  size="sm"
                                  className="text-xs h-7 bg-green-600 hover:bg-green-700"
                                >
                                  Present
                                </Button>
                                <Button
                                  onClick={() => handleMarkAttendance(p.id, 'absent')}
                                  disabled={updatingAttendance[p.id]}
                                  size="sm"
                                  variant="destructive"
                                  className="text-xs h-7"
                                >
                                  Absent
                                </Button>
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="p-3 text-center">
                          {preTest ? (
                            <div className="flex flex-col items-center gap-1">
                              <span className={`px-2 py-1 rounded text-xs font-bold ${
                                preTest.passed 
                                  ? 'bg-green-100 text-green-800' 
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {preTest.passed ? '✓ PASS' : '✗ FAIL'}
                              </span>
                              <span className="text-xs text-gray-600">
                                {preTest.score?.toFixed(0)}%
                              </span>
                            </div>
                          ) : (
                            <span className="text-gray-400 text-xs">Not taken</span>
                          )}
                        </td>
                        <td className="p-3 text-center">
                          {postTest ? (
                            <div className="flex flex-col items-center gap-1">
                              <span className={`px-2 py-1 rounded text-xs font-bold ${
                                postTest.passed 
                                  ? 'bg-green-100 text-green-800' 
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {postTest.passed ? '✓ PASS' : '✗ FAIL'}
                              </span>
                              <span className="text-xs text-gray-600">
                                {postTest.score?.toFixed(0)}%
                              </span>
                            </div>
                          ) : (
                            <span className="text-gray-400 text-xs">Not taken</span>
                          )}
                        </td>
                        <td className="p-3 text-center">
                          {access?.feedback_completed ? (
                            <span className="px-2 py-1 rounded text-xs font-bold bg-purple-100 text-purple-800">
                              ✓ Submitted
                            </span>
                          ) : (
                            <span className="text-gray-400 text-xs">Not submitted</span>
                          )}
                        </td>
                        <td className="p-3 text-center">
                          <div className="flex flex-col gap-2 items-center">
                            {certificateStatuses[p.id]?.uploaded ? (
                              <div className="flex flex-col gap-1 items-center">
                                <span className="px-2 py-1 rounded text-xs font-bold bg-blue-100 text-blue-800">
                                  ✓ Uploaded
                                </span>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => {
                                      const certUrl = certificateStatuses[p.id]?.url;
                                      if (certUrl) {
                                        window.open(`${process.env.REACT_APP_BACKEND_URL}${certUrl}`, '_blank');
                                      }
                                    }}
                                    className="cursor-pointer text-xs text-blue-600 hover:underline"
                                  >
                                    View
                                  </button>
                                  <label 
                                    htmlFor={`cert-${p.id}`}
                                    className="cursor-pointer text-xs text-blue-600 hover:underline"
                                  >
                                    Replace
                                  </label>
                                </div>
                              </div>
                            ) : (
                              <label 
                                htmlFor={`cert-${p.id}`}
                                className="cursor-pointer px-3 py-1 rounded text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                              >
                                {uploadingCertificates[p.id] ? "Uploading..." : "Upload PDF"}
                              </label>
                            )}
                            <input
                              id={`cert-${p.id}`}
                              type="file"
                              accept=".pdf"
                              className="hidden"
                              onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file) {
                                  handleCertificateUpload(p.id, file);
                                }
                                e.target.value = null;
                              }}
                              disabled={uploadingCertificates[p.id]}
                            />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Attendance Records */}
      <Card>
        <CardHeader>
          <CardTitle>Attendance Records</CardTitle>
        </CardHeader>
        <CardContent>
          {attendance.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No attendance records yet</p>
          ) : (
            <div className="space-y-2">
              {attendance.slice(0, 10).map((record, idx) => {
                const formatTime = (timeStr) => {
                  if (!timeStr) return '-';
                  try {
                    const parts = timeStr.split(':');
                    if (parts.length >= 2) {
                      const hour = parseInt(parts[0]);
                      const minute = parts[1];
                      const ampm = hour >= 12 ? 'PM' : 'AM';
                      const displayHour = hour % 12 || 12;
                      return `${displayHour}:${minute} ${ampm}`;
                    }
                    return timeStr;
                  } catch {
                    return timeStr;
                  }
                };
                
                return (
                  <div key={idx} className="p-3 bg-gray-50 rounded flex justify-between items-center">
                    <div>
                      <p className="font-medium">{record.participant_name}</p>
                      <p className="text-xs text-gray-600">{new Date(record.date).toLocaleDateString()}</p>
                    </div>
                    <div className="text-sm">
                      <span className="text-green-600 font-medium">In: {formatTime(record.clock_in)}</span>
                      <span className="mx-2">|</span>
                      <span className="text-red-600 font-medium">Out: {formatTime(record.clock_out)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* All Vehicle Checklists */}
      <Card className="border-blue-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-blue-700">
            <span className="text-2xl">✓</span>
            Vehicle Checklists - All Inspections
          </CardTitle>
          <CardDescription>All vehicle inspections completed by trainers</CardDescription>
        </CardHeader>
        <CardContent>
          {allChecklists.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">No checklists completed yet</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-gray-600 mb-3">
                {allChecklists.length} participant{allChecklists.length !== 1 ? 's' : ''} with completed checklists. Click to view details.
              </p>
              {allChecklists.map((checklistData, idx) => (
                <div key={idx} className="border border-blue-200 rounded-lg overflow-hidden">
                  <div 
                    className="p-3 bg-blue-50 hover:bg-blue-100 cursor-pointer transition-colors flex justify-between items-center"
                    onClick={() => setExpandedChecklist(expandedChecklist === checklistData.participant_name ? null : checklistData.participant_name)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-blue-600 font-bold">✓</span>
                      <div>
                        <h4 className="font-semibold text-blue-900">{checklistData.participant_name}</h4>
                        <p className="text-xs text-blue-700">{checklistData.items.length} item{checklistData.items.length !== 1 ? 's' : ''} inspected</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-blue-600 font-medium">
                        {expandedChecklist === checklistData.participant_name ? 'Hide Details' : 'View Details'}
                      </span>
                      <span className={`text-blue-600 transition-transform ${expandedChecklist === checklistData.participant_name ? 'rotate-180' : ''}`}>
                        ▼
                      </span>
                    </div>
                  </div>
                  
                  {expandedChecklist === checklistData.participant_name && (
                    <div className="p-4 bg-white border-t border-blue-200">
                      <div className="space-y-2">
                        {checklistData.items.map((item, itemIdx) => {
                          const itemStatus = (item.status || '').toLowerCase();
                          const needsRepair = itemStatus === 'needs_repair';
                          
                          return (
                            <div 
                              key={itemIdx} 
                              className={`flex justify-between items-center p-3 rounded border-2 ${
                                needsRepair 
                                  ? 'bg-red-50 border-red-300' 
                                  : 'bg-green-50 border-green-200'
                              }`}
                            >
                              <span className={`text-sm font-medium ${needsRepair ? 'text-red-900' : 'text-gray-900'}`}>
                                {needsRepair && '⚠️ '}
                                {item.item || item.name || 'Item'}
                              </span>
                              <span className={`text-xs px-3 py-1.5 rounded-full font-bold ${
                                needsRepair
                                  ? 'bg-red-200 text-red-900 border-2 border-red-400' 
                                  : 'bg-green-200 text-green-900 border-2 border-green-400'
                              }`}>
                                {needsRepair ? '🔧 NEEDS REPAIR' : '✓ ' + (item.status?.toUpperCase() || 'GOOD')}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Vehicle Checklist Issues */}
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-red-700">
            <span className="text-2xl">⚠️</span>
            Vehicle Issues - Needs Repair
          </CardTitle>
          <CardDescription>Items flagged by trainers requiring attention</CardDescription>
        </CardHeader>
        <CardContent>
          {checklistIssues.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-green-600 font-medium">✓ No vehicle issues reported</p>
              <p className="text-sm text-gray-500 mt-1">All vehicles inspected are in good condition</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-gray-600 mb-3">
                {checklistIssues.length} participant{checklistIssues.length !== 1 ? 's' : ''} with vehicle issues. Click to view details.
              </p>
              {checklistIssues.map((issue, idx) => (
                <div key={idx} className="border border-red-200 rounded-lg overflow-hidden">
                  <div 
                    className="p-3 bg-red-50 hover:bg-red-100 cursor-pointer transition-colors flex justify-between items-center"
                    onClick={() => setExpandedVehicleIssue(expandedVehicleIssue === issue.participant_name ? null : issue.participant_name)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-red-600 font-bold">⚠️</span>
                      <div>
                        <h4 className="font-semibold text-red-900">{issue.participant_name}</h4>
                        <p className="text-xs text-red-700">{issue.items.length} issue{issue.items.length !== 1 ? 's' : ''} found</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-red-600 font-medium">
                        {expandedVehicleIssue === issue.participant_name ? 'Hide Details' : 'View Details'}
                      </span>
                      <span className={`text-red-600 transition-transform ${expandedVehicleIssue === issue.participant_name ? 'rotate-180' : ''}`}>
                        ▼
                      </span>
                    </div>
                  </div>
                  
                  {expandedVehicleIssue === issue.participant_name && (
                    <div className="p-4 bg-white border-t border-red-200">
                      <div className="space-y-3">
                        {issue.items.map((item, itemIdx) => (
                          <div key={itemIdx} className="p-3 bg-red-50 rounded border border-red-200">
                            <p className="font-semibold text-sm text-red-900 mb-2">
                              🔧 {item.item || item.item_name || item.name || 'Item'}
                            </p>
                            {item.comments && (
                              <p className="text-sm text-gray-700 bg-white p-2 rounded mb-2">
                                <span className="font-medium">Issue: </span>{item.comments}
                              </p>
                            )}
                            {(item.photo_url || item.photo) && (
                              <div className="mt-2">
                                <p className="text-xs text-gray-600 mb-1">Photo:</p>
                                <img 
                                  src={item.photo_url || item.photo} 
                                  alt={item.item || 'Vehicle item'} 
                                  className="w-32 h-32 object-cover rounded border-2 border-red-300 cursor-pointer hover:scale-105 transition-transform"
                                  onClick={() => window.open(item.photo_url || item.photo, '_blank')}
                                />
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export { ManagementTab };
