/**
 * ChecklistsTab Component - Extracted from ParticipantDashboard
 * Displays vehicle inspection checklists completed by trainers
 */
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { ClipboardCheck } from "lucide-react";

const ChecklistsTab = ({ checklists }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Vehicle Inspection Checklists</CardTitle>
        <CardDescription>View checklists completed by your trainer</CardDescription>
      </CardHeader>
      <CardContent>
        {checklists.length === 0 ? (
          <div className="text-center py-12">
            <ClipboardCheck className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-500">No trainer checklists completed yet</p>
            <p className="text-sm text-gray-400 mt-2">Your trainer will inspect your vehicle and submit the checklist</p>
          </div>
        ) : (
          <div className="space-y-4">
            {checklists.map((checklist) => (
              <div
                key={checklist.id}
                data-testid={`checklist-${checklist.id}`}
                className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200"
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-semibold text-lg text-gray-900">
                      Trainer Inspection
                    </h3>
                    <p className="text-sm text-gray-600">
                      Completed: {new Date(checklist.submitted_at || checklist.verified_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    {checklist.verification_status || "Completed"}
                  </span>
                </div>

                {/* Checklist Items */}
                {checklist.checklist_items && checklist.checklist_items.length > 0 ? (
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm text-gray-700 mb-2">Inspection Results:</h4>
                    {checklist.checklist_items.map((item, idx) => {
                      const itemName = item.item_name || item.name || item.item || 'Item';
                      let itemStatus;
                      if (item.status) {
                        itemStatus = item.status.toLowerCase();
                      } else if (item.completed === true || item.completed === 'true') {
                        itemStatus = 'good';
                      } else if (item.completed === false || item.completed === 'false') {
                        itemStatus = 'pending';
                      } else {
                        itemStatus = 'pending';
                      }
                      const itemComments = item.comments || item.comment || '';
                      const itemPhoto = item.photo || item.photo_url || item.image || '';
                      
                      return (
                        <div key={idx} className="p-4 bg-white rounded-lg border shadow-sm">
                          <div className="flex justify-between items-start gap-3">
                            <div className="flex-1">
                              <p className="font-semibold text-gray-900 text-base">{itemName}</p>
                              {itemComments && (
                                <p className="text-sm text-gray-600 mt-2">
                                  <span className="font-semibold">Comments:</span> {itemComments}
                                </p>
                              )}
                            </div>
                            <span
                              className={`px-4 py-1.5 rounded-full text-xs font-bold ml-3 whitespace-nowrap ${
                                itemStatus === "good"
                                  ? "bg-green-100 text-green-800 border border-green-300"
                                  : itemStatus === "satisfactory"
                                  ? "bg-yellow-100 text-yellow-800 border border-yellow-300"
                                  : itemStatus === "needs_repair"
                                  ? "bg-red-100 text-red-800 border border-red-300"
                                  : "bg-gray-100 text-gray-800 border border-gray-300"
                              }`}
                            >
                              {itemStatus === "needs_repair" ? "NEEDS REPAIR" : itemStatus.toUpperCase()}
                            </span>
                          </div>
                          {itemPhoto && (
                            <div className="mt-3">
                              <p className="text-xs text-gray-500 mb-1">Photo:</p>
                              <img
                                src={itemPhoto}
                                alt={itemName}
                                className="w-48 h-48 object-cover rounded-lg border-2 border-gray-200 shadow-sm"
                              />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-4 text-gray-500">
                    <p>No checklist items available</p>
                  </div>
                )}

                {/* Areas needing attention */}
                {checklist.checklist_items && checklist.checklist_items.filter(item => (item.status || '').toLowerCase() === "needs_repair").length > 0 && (
                  <div className="mt-4 p-4 bg-red-50 border-2 border-red-300 rounded-lg">
                    <p className="font-bold text-red-800 text-base flex items-center gap-2">
                      <span className="text-xl">⚠️</span> Items Needing Attention
                    </p>
                    <ul className="mt-3 space-y-2">
                      {checklist.checklist_items
                        .filter(item => (item.status || '').toLowerCase() === "needs_repair")
                        .map((item, idx) => (
                          <li key={idx} className="text-sm text-red-800 font-medium flex items-start gap-2">
                            <span className="mt-0.5">•</span>
                            <span>{item.item_name || item.name || item.item || 'Item'}</span>
                          </li>
                        ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { ChecklistsTab };
