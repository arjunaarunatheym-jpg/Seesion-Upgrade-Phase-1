/**
 * FeedbackTab - Trainer feedback responses view
 */
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { MessageSquare, Eye, Users, Building2, Calendar } from "lucide-react";

const FeedbackTab = ({
  feedbackSessions,
  onViewFeedback,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          Participant Feedback
        </CardTitle>
        <CardDescription>
          View feedback submitted by participants for your training sessions
        </CardDescription>
      </CardHeader>
      <CardContent>
        {feedbackSessions.length === 0 ? (
          <div className="text-center py-12">
            <MessageSquare className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500">No feedback received yet</p>
            <p className="text-sm text-gray-400 mt-2">Feedback will appear here once participants submit their responses</p>
          </div>
        ) : (
          <div className="space-y-4">
            {feedbackSessions.map((session) => (
              <Card key={session.id} className="border hover:shadow-md transition-shadow">
                <CardContent className="p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Building2 className="w-4 h-4 text-gray-500" />
                        <span className="font-semibold text-gray-900">{session.company_name}</span>
                      </div>
                      <p className="text-sm text-gray-600 mb-1">{session.program_name}</p>
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {session.start_date}
                        </span>
                        <span className="flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          {session.feedback_count || 0} responses
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      {session.feedback_count > 0 && (
                        <Badge className="bg-green-100 text-green-800">
                          {session.feedback_count} Feedback
                        </Badge>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onViewFeedback(session.id)}
                        disabled={!session.feedback_count}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { FeedbackTab };
