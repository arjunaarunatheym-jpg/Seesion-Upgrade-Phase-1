/**
 * ChecklistsTab - Trainer vehicle inspection checklists
 * Self-select flow: trainers search and claim participants to inspect
 */
import { useState, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { ClipboardCheck, Users, Search, UserCheck, UserX, ChevronRight } from "lucide-react";
import { axiosInstance } from "../../App";
import { toast } from "sonner";

const ChecklistsTab = ({
  selectedSession,
  sessionParticipants,
  isChiefTrainer,
  getMyRole,
  onNavigateChecklist,
  user,
  onRefreshParticipants,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState("all"); // all | mine | unclaimed | completed
  const [claiming, setClaiming] = useState(null);

  const participants = sessionParticipants[selectedSession?.id] || [];

  // Safety: ensure participants is always an array of objects
  const safeParticipants = Array.isArray(participants) ? participants : [];

  const filteredParticipants = useMemo(() => {
    let list = safeParticipants;
    // Search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(p =>
        (p.full_name || "").toLowerCase().includes(q) ||
        (p.id_number || "").toLowerCase().includes(q)
      );
    }
    // Status filter
    if (filter === "mine") {
      list = list.filter(p => p.claimed_by_trainer_id === user?.id || p.submitted_by_trainer_id === user?.id);
    } else if (filter === "unclaimed") {
      list = list.filter(p => !p.claimed_by_trainer_id && !p.checklist_submitted);
    } else if (filter === "completed") {
      list = list.filter(p => p.checklist_submitted);
    }
    return list;
  }, [safeParticipants, searchQuery, filter, user?.id]);

  const stats = useMemo(() => {
    const total = safeParticipants.length;
    const mine = safeParticipants.filter(p => p.claimed_by_trainer_id === user?.id || p.submitted_by_trainer_id === user?.id).length;
    const completed = safeParticipants.filter(p => p.checklist_submitted).length;
    const unclaimed = safeParticipants.filter(p => !p.claimed_by_trainer_id && !p.checklist_submitted).length;
    return { total, mine, completed, unclaimed };
  }, [safeParticipants, user?.id]);

  const handleClaim = async (participantId) => {
    if (!selectedSession) return;
    try {
      setClaiming(participantId);
      await axiosInstance.post(`/trainer-checklist/${selectedSession.id}/claim/${participantId}`);
      toast.success("Participant claimed");
      if (onRefreshParticipants) onRefreshParticipants(selectedSession.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to claim");
    } finally {
      setClaiming(null);
    }
  };

  const handleUnclaim = async (participantId) => {
    if (!selectedSession) return;
    try {
      setClaiming(participantId);
      await axiosInstance.delete(`/trainer-checklist/${selectedSession.id}/claim/${participantId}`);
      toast.success("Participant released");
      if (onRefreshParticipants) onRefreshParticipants(selectedSession.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to release");
    } finally {
      setClaiming(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Vehicle Checklists</CardTitle>
        <CardDescription>
          Search and select participants to inspect. Claim a participant before starting their checklist.
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
            {/* Stats Bar */}
            <div className="grid grid-cols-4 gap-2" data-testid="checklist-stats">
              <button onClick={() => setFilter("all")} className={`p-2 rounded-lg text-center text-xs font-medium border transition-colors ${filter === "all" ? "bg-indigo-100 border-indigo-300 text-indigo-800" : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"}`}>
                <div className="text-lg font-bold">{stats.total}</div>Total
              </button>
              <button onClick={() => setFilter("mine")} className={`p-2 rounded-lg text-center text-xs font-medium border transition-colors ${filter === "mine" ? "bg-blue-100 border-blue-300 text-blue-800" : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"}`}>
                <div className="text-lg font-bold">{stats.mine}</div>Mine
              </button>
              <button onClick={() => setFilter("unclaimed")} className={`p-2 rounded-lg text-center text-xs font-medium border transition-colors ${filter === "unclaimed" ? "bg-amber-100 border-amber-300 text-amber-800" : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"}`}>
                <div className="text-lg font-bold">{stats.unclaimed}</div>Available
              </button>
              <button onClick={() => setFilter("completed")} className={`p-2 rounded-lg text-center text-xs font-medium border transition-colors ${filter === "completed" ? "bg-green-100 border-green-300 text-green-800" : "bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"}`}>
                <div className="text-lg font-bold">{stats.completed}</div>Done
              </button>
            </div>

            {/* Search Bar */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name or IC number..."
                className="pl-9"
                data-testid="checklist-search"
              />
            </div>

            {/* Participant List */}
            <div className="space-y-2">
              {filteredParticipants.length === 0 ? (
                <p className="text-gray-500 text-center py-6 text-sm">No participants match your filter</p>
              ) : (
                filteredParticipants.map((p) => {
                  const isMine = p.claimed_by_trainer_id === user?.id;
                  const isClaimedByOther = p.claimed_by_trainer_id && p.claimed_by_trainer_id !== user?.id;
                  const isDone = p.checklist_submitted;
                  const mySubmission = p.submitted_by_trainer_id === user?.id;

                  return (
                    <div
                      key={p.id}
                      data-testid={`checklist-participant-${p.id}`}
                      className={`p-3 rounded-lg border flex items-center gap-3 transition-all ${
                        isDone
                          ? "bg-green-50 border-green-200"
                          : isMine
                          ? "bg-blue-50 border-blue-300 shadow-sm"
                          : isClaimedByOther
                          ? "bg-gray-50 border-gray-200 opacity-60"
                          : "bg-white border-gray-200 hover:border-indigo-300"
                      }`}
                    >
                      {/* Avatar */}
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0 ${
                        isDone ? "bg-green-500" : isMine ? "bg-blue-500" : isClaimedByOther ? "bg-gray-400" : "bg-indigo-500"
                      }`}>
                        {(p.full_name || "?").charAt(0).toUpperCase()}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-sm text-gray-900 truncate">{p.full_name}</p>
                        <p className="text-xs text-gray-500">{p.id_number}</p>
                        {isDone && (
                          <p className="text-xs text-green-600 font-medium">
                            Inspected by {mySubmission ? "you" : p.submitted_by_trainer_name || "trainer"}
                          </p>
                        )}
                        {isClaimedByOther && !isDone && (
                          <p className="text-xs text-gray-500">
                            Claimed by {p.claimed_by_trainer_name}
                          </p>
                        )}
                      </div>

                      {/* Action Button */}
                      <div className="flex-shrink-0">
                        {isDone ? (
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-green-700 border-green-300 text-xs"
                            onClick={() => onNavigateChecklist(selectedSession.id, p.id)}
                            data-testid={`view-checklist-${p.id}`}
                          >
                            View
                          </Button>
                        ) : isMine ? (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              className="bg-orange-500 hover:bg-orange-600 text-xs"
                              onClick={() => onNavigateChecklist(selectedSession.id, p.id)}
                              data-testid={`start-checklist-${p.id}`}
                            >
                              Inspect <ChevronRight className="w-3 h-3 ml-1" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-gray-400 hover:text-red-500 text-xs px-2"
                              onClick={() => handleUnclaim(p.id)}
                              disabled={claiming === p.id}
                              data-testid={`unclaim-${p.id}`}
                            >
                              <UserX className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        ) : isClaimedByOther ? (
                          <span className="text-xs text-gray-400 px-2">Taken</span>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-indigo-600 border-indigo-300 hover:bg-indigo-50 text-xs"
                            onClick={() => handleClaim(p.id)}
                            disabled={claiming === p.id}
                            data-testid={`claim-${p.id}`}
                          >
                            {claiming === p.id ? "..." : <><UserCheck className="w-3.5 h-3.5 mr-1" />Claim</>}
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { ChecklistsTab };
