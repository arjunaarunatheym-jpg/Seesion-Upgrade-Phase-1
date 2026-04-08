/**
 * DetailsTab Component - Extracted from ParticipantDashboard
 * Displays attendance and vehicle details for each session
 * Active sessions show full interaction, past sessions are read-only
 */
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { ChevronDown, ChevronRight, History } from "lucide-react";

const DetailsTab = ({
  sessions,
  pastSessions = [],
  vehicleDetails,
  attendanceToday,
  participantAccess,
  vehicleForm,
  setVehicleForm,
  onClockIn,
  onClockOut,
  onVehicleSubmit,
}) => {
  const [showPast, setShowPast] = useState(false);

  // Helper function to format time
  const formatTime = (timeStr) => {
    if (typeof timeStr === 'string') {
      const parts = timeStr.split(':');
      if (parts.length >= 2) {
        const hour = parseInt(parts[0]);
        const minute = parts[1];
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour % 12 || 12;
        return `${displayHour}:${minute} ${ampm}`;
      }
      const date = new Date(timeStr);
      return isNaN(date.getTime()) ? timeStr : date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
    }
    return 'today';
  };

  const renderActiveSession = (session) => {
    const vehicleInfo = vehicleDetails[session.id];
    const attendance = attendanceToday[session.id] || {};
    const access = participantAccess[session.id] || {};
    const canClockOut = access.can_clock_out || false;

    return (
      <Card key={session.id}>
        <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50">
          <CardTitle>{session.name}</CardTitle>
          <CardDescription>
            {session.start_date} to {session.end_date} {session.location ? `\u2022 ${session.location}` : ''}
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6 space-y-6">
          {/* Attendance */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-3">Attendance</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                <input
                  type="checkbox"
                  id={`clock-in-${session.id}`}
                  checked={!!attendance.clock_in}
                  onChange={() => { if (!attendance.clock_in) onClockIn(session.id); }}
                  className="w-5 h-5 text-green-600 rounded focus:ring-2 focus:ring-green-500"
                  data-testid={`clock-in-${session.id}`}
                />
                <label htmlFor={`clock-in-${session.id}`} className="flex-1 cursor-pointer">
                  <span className="font-medium text-gray-900">Clock In</span>
                  {attendance.clock_in && (
                    <span className="ml-2 text-sm text-green-600">Clocked in at {formatTime(attendance.clock_in)}</span>
                  )}
                </label>
              </div>

              <div className={`flex items-center gap-3 p-3 rounded-lg border ${
                attendance.clock_in && canClockOut
                  ? 'bg-blue-50 border-blue-200'
                  : 'bg-gray-100 border-gray-200 opacity-50'
              }`}>
                <input
                  type="checkbox"
                  id={`clock-out-${session.id}`}
                  checked={!!attendance.clock_out}
                  onChange={() => { if (attendance.clock_in && !attendance.clock_out && canClockOut) onClockOut(session.id); }}
                  disabled={!attendance.clock_in || !canClockOut}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  data-testid={`clock-out-${session.id}`}
                />
                <label htmlFor={`clock-out-${session.id}`} className={`flex-1 ${attendance.clock_in && canClockOut ? 'cursor-pointer' : 'cursor-not-allowed'}`}>
                  <span className="font-medium text-gray-900">Clock Out</span>
                  {attendance.clock_out && (
                    <span className="ml-2 text-sm text-blue-600">Clocked out at {formatTime(attendance.clock_out)}</span>
                  )}
                  {!attendance.clock_in && (
                    <span className="ml-2 text-xs text-gray-500">(Clock in first)</span>
                  )}
                  {attendance.clock_in && !canClockOut && !attendance.clock_out && (
                    <span className="ml-2 text-xs text-orange-500">(Not yet released by coordinator)</span>
                  )}
                </label>
              </div>
            </div>
          </div>

          {/* Vehicle Details */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-3">Vehicle Details</h3>
            {vehicleInfo ? (
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Vehicle Model</p>
                    <p className="font-medium">{vehicleInfo.vehicle_model}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Registration No.</p>
                    <p className="font-medium">{vehicleInfo.registration_number}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Roadtax Expiry</p>
                    <p className="font-medium">{vehicleInfo.roadtax_expiry}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <p className="text-sm text-yellow-800 mb-3">Please provide your vehicle details</p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="vehicle_model">Vehicle Model</Label>
                    <Input
                      id="vehicle_model"
                      value={vehicleForm.vehicle_model}
                      onChange={(e) => setVehicleForm({ ...vehicleForm, vehicle_model: e.target.value })}
                      placeholder="e.g., Honda City"
                      data-testid={`vehicle-model-${session.id}`}
                    />
                  </div>
                  <div>
                    <Label htmlFor="registration_number">Registration Number</Label>
                    <Input
                      id="registration_number"
                      value={vehicleForm.registration_number}
                      onChange={(e) => setVehicleForm({ ...vehicleForm, registration_number: e.target.value })}
                      placeholder="e.g., ABC 1234"
                      data-testid={`registration-${session.id}`}
                    />
                  </div>
                  <div>
                    <Label htmlFor="roadtax_expiry">Roadtax Expiry</Label>
                    <Input
                      id="roadtax_expiry"
                      type="date"
                      value={vehicleForm.roadtax_expiry}
                      onChange={(e) => setVehicleForm({ ...vehicleForm, roadtax_expiry: e.target.value })}
                      data-testid={`roadtax-${session.id}`}
                    />
                  </div>
                </div>
                <Button
                  onClick={() => onVehicleSubmit(session.id)}
                  className="w-full"
                  data-testid={`submit-vehicle-${session.id}`}
                >
                  Save Vehicle Details
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  const renderPastSession = (session) => {
    const vehicleInfo = vehicleDetails[session.id];
    const attendance = attendanceToday[session.id] || {};

    return (
      <Card key={session.id} className="opacity-75">
        <CardHeader className="bg-gradient-to-r from-gray-100 to-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-gray-700">{session.name}</CardTitle>
              <CardDescription>{session.start_date} to {session.end_date} {session.location ? `\u2022 ${session.location}` : ''}</CardDescription>
            </div>
            <span className="text-xs bg-gray-300 text-gray-700 px-2 py-0.5 rounded-full">Past</span>
          </div>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          {/* Attendance summary - read only */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-2 text-sm">Attendance</h3>
            <div className="flex gap-4 text-sm">
              <span className={attendance.clock_in ? 'text-green-600' : 'text-gray-400'}>
                Clock In: {attendance.clock_in ? formatTime(attendance.clock_in) : 'N/A'}
              </span>
              <span className={attendance.clock_out ? 'text-blue-600' : 'text-gray-400'}>
                Clock Out: {attendance.clock_out ? formatTime(attendance.clock_out) : 'N/A'}
              </span>
            </div>
          </div>
          {/* Vehicle summary - read only */}
          {vehicleInfo && (
            <div>
              <h3 className="font-semibold text-gray-700 mb-2 text-sm">Vehicle</h3>
              <p className="text-sm text-gray-600">{vehicleInfo.vehicle_model} — {vehicleInfo.registration_number}</p>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  if (sessions.length === 0 && pastSessions.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle>My Details</CardTitle></CardHeader>
        <CardContent><p className="text-gray-500 text-center py-8">No sessions assigned yet</p></CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Active Sessions */}
      {sessions.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-gray-500">
            <p className="font-medium">No active sessions</p>
            <p className="text-sm">Your upcoming or current training sessions will appear here.</p>
          </CardContent>
        </Card>
      ) : (
        sessions.map((session) => renderActiveSession(session))
      )}

      {/* Past Sessions - Collapsible */}
      {pastSessions.length > 0 && (
        <div>
          <button
            onClick={() => setShowPast(!showPast)}
            className="flex items-center gap-2 w-full text-left px-3 py-2 text-sm font-semibold text-gray-500 hover:text-gray-700 transition-colors"
            data-testid="toggle-past-sessions-details"
          >
            {showPast ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            <History className="w-4 h-4" />
            Past Sessions ({pastSessions.length})
          </button>
          {showPast && (
            <div className="space-y-4 mt-2">
              {pastSessions.map((session) => renderPastSession(session))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export { DetailsTab };
