/**
 * OverviewTab Component - Extracted from ParticipantDashboard
 * Displays session overview with stats and session list
 */
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { MessageSquare } from "lucide-react";

const OverviewTab = ({
  sessions,
  participantAccess,
  testResults,
  onFeedback,
}) => {
  return (
    <>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <CardHeader>
            <CardTitle className="text-blue-900">My Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold text-blue-900">{sessions.length}</p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <CardHeader>
            <CardTitle className="text-green-900">Certificates</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold text-green-900">
              {Object.values(participantAccess).filter(access => access.certificate_url).length}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
          <CardHeader>
            <CardTitle className="text-purple-900">Tests Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold text-purple-900">{testResults.length}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>My Training Sessions</CardTitle>
        </CardHeader>
        <CardContent>
          {sessions.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No sessions assigned yet</p>
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => {
                const access = participantAccess[session.id] || {};
                const feedbackSubmitted = access.feedback_completed || false;
                const canAccessFeedback = access.can_access_feedback || false;
                
                return (
                  <div
                    key={session.id}
                    data-testid={`participant-session-${session.id}`}
                    className="p-4 bg-gradient-to-r from-teal-50 to-cyan-50 rounded-lg border-2 border-teal-200"
                  >
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 text-base">{session.name}</h3>
                        <p className="text-sm text-gray-600 mt-1">Location: {session.location}</p>
                        <p className="text-sm text-gray-600">
                          {session.start_date} to {session.end_date}
                        </p>
                      </div>
                      <div className="flex flex-row sm:flex-col gap-2 flex-wrap">
                        {canAccessFeedback && !feedbackSubmitted && (
                          <Button
                            size="sm"
                            onClick={() => onFeedback(session.id)}
                            className="bg-yellow-600 hover:bg-yellow-700"
                            data-testid={`feedback-button-${session.id}`}
                          >
                            <MessageSquare className="w-4 h-4 mr-2" />
                            Submit Feedback
                          </Button>
                        )}
                        {feedbackSubmitted && (
                          <span className="text-xs text-green-700 font-semibold">✓ Feedback Submitted</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
};

export { OverviewTab };
