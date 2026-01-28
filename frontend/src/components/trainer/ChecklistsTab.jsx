/**
 * ChecklistsTab - Trainer vehicle inspection checklists
 */
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { ClipboardCheck, Users } from "lucide-react";

const ChecklistsTab = ({
  selectedSession,
  sessionParticipants,
  isChiefTrainer,
  getMyRole,
  onNavigateChecklist,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Vehicle Checklists</CardTitle>
        <CardDescription>
          Complete vehicle inspection checklists for your assigned participants in the selected session
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!selectedSession ? (
          <div className="text-center py-12">
            <ClipboardCheck className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500">Please select a session above to view checklists</p>
          </div>
        ) : (
          <div className="space-y-4">
            <Card className="border-l-4 border-l-orange-500">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <span className={`inline-block mb-2 px-2 py-1 rounded text-xs ${
                      isChiefTrainer(selectedSession) ? 'bg-purple-100 text-purple-800' : 'bg-orange-100 text-orange-800'
                    }`}>
                      {getMyRole(selectedSession)}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <Users className="w-4 h-4 inline mr-1" />
                    {sessionParticipants[selectedSession.id]?.length || 0} Participants
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {(!sessionParticipants[selectedSession.id] || sessionParticipants[selectedSession.id].length === 0) ? (
                  <p className="text-gray-500 text-center py-4">No participants assigned</p>
                ) : (
                  <div className="space-y-2">
                    {sessionParticipants[selectedSession.id].map((participant) => {
                      const isCompleted = participant.checklist && participant.checklist.verification_status === 'completed';
                      
                      return (
                        <div
                          key={participant.id}
                          className={`p-3 rounded-lg border flex justify-between items-center ${
                            isCompleted 
                              ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-200' 
                              : 'bg-gradient-to-r from-orange-50 to-amber-50 border-orange-200'
                          }`}
                        >
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-semibold text-gray-900">{participant.full_name}</p>
                              {isCompleted && (
                                <span className="px-2 py-0.5 bg-green-600 text-white text-xs rounded-full">
                                  ✓ Completed
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-gray-600">{participant.email}</p>
                          </div>
                          <Button
                            onClick={() => onNavigateChecklist(selectedSession.id, participant.id)}
                            size="sm"
                            className={isCompleted 
                              ? 'bg-green-600 hover:bg-green-700' 
                              : 'bg-orange-600 hover:bg-orange-700'
                            }
                          >
                            <ClipboardCheck className="w-4 h-4 mr-2" />
                            {isCompleted ? 'View Checklist' : 'Complete Checklist'}
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { ChecklistsTab };
