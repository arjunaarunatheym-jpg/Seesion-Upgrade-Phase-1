/**
 * SessionsTab Component - Extracted from AdminDashboard
 * Manages training sessions with participants, trainers, coordinators, and supervisors
 */
import { useState, useMemo, useEffect } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Calendar, Plus, Trash2, Edit, Upload, DollarSign, FileText } from "lucide-react";
import { SearchBar } from "../SearchBar";

// Initial form state for session creation
const initialSessionForm = {
  program_id: "",
  company_id: "",
  location: "",
  venue_type: "client",
  start_date: "",
  end_date: "",
  participants: [],
  supervisors: [],
  trainer_assignments: [],
  coordinator_id: "",
  marketing_user_id: "",
  commission_type: "percentage",
  commission_rate: "",
  commission_fixed_amount: "",
  create_new_marketing: false,
  new_marketing_name: "",
  new_marketing_id: "",
  reuse_invoice_number: "",  // For reusing deleted invoice numbers
};

const initialNewParticipant = {
  email: "",
  password: "",
  full_name: "",
  id_number: "",
  phone_number: "",
};

const initialNewSupervisor = {
  email: "",
  password: "",
  full_name: "",
  id_number: "",
  phone_number: "",
};

const initialNewTrainerAssignment = {
  trainer_id: "",
  role: "regular",
};

const SessionsTab = ({
  sessions,
  programs,
  companies,
  trainers,
  coordinators,
  allStaffForCoordinator,
  marketingUsers,
  onRefresh,
  onDeleteClick,
  onBulkUploadClick,
  onCostingClick,
  onIndemnityClick,
  getTrainerName,
  getCoordinatorName,
}) => {
  // Dialog and form states
  const [sessionDialogOpen, setSessionDialogOpen] = useState(false);
  const [sessionForm, setSessionForm] = useState(initialSessionForm);
  const [newParticipant, setNewParticipant] = useState(initialNewParticipant);
  const [newSupervisor, setNewSupervisor] = useState(initialNewSupervisor);
  const [newTrainerAssignment, setNewTrainerAssignment] = useState(initialNewTrainerAssignment);
  const [participantMatchStatus, setParticipantMatchStatus] = useState(null);
  const [supervisorMatchStatus, setSupervisorMatchStatus] = useState(null);
  
  // Edit session states
  const [editingSession, setEditingSession] = useState(null);
  const [editSessionDialogOpen, setEditSessionDialogOpen] = useState(false);
  
  // Search and filter states
  const [sessionsSearch, setSessionsSearch] = useState("");
  const [sessionsMonthFilter, setSessionsMonthFilter] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });

  // Filter sessions based on search and month filter
  const filteredSessions = useMemo(() => {
    let filtered = sessions;
    
    // Filter by month
    if (sessionsMonthFilter && sessionsMonthFilter !== "all") {
      filtered = filtered.filter(s => {
        if (s.start_date) {
          const dateStr = s.start_date.substring(0, 7);
          return dateStr === sessionsMonthFilter;
        }
        return false;
      });
    }
    
    // Filter by search
    if (sessionsSearch) {
      filtered = filtered.filter(s =>
        s.name.toLowerCase().includes(sessionsSearch.toLowerCase()) ||
        (s.company_name && s.company_name.toLowerCase().includes(sessionsSearch.toLowerCase())) ||
        (s.program_name && s.program_name.toLowerCase().includes(sessionsSearch.toLowerCase())) ||
        (s.location && s.location.toLowerCase().includes(sessionsSearch.toLowerCase()))
      );
    }
    
    return filtered;
  }, [sessionsSearch, sessionsMonthFilter, sessions]);

  // Check if participant exists in system
  useEffect(() => {
    const checkParticipantMatch = async () => {
      if (!newParticipant.full_name && !newParticipant.id_number) {
        setParticipantMatchStatus(null);
        return;
      }
      
      try {
        const response = await axiosInstance.get("/participant-access/check-existing", {
          params: {
            full_name: newParticipant.full_name || undefined,
            id_number: newParticipant.id_number || undefined,
          }
        });
        setParticipantMatchStatus(response.data);
      } catch (error) {
        setParticipantMatchStatus(null);
      }
    };
    
    const debounce = setTimeout(checkParticipantMatch, 300);
    return () => clearTimeout(debounce);
  }, [newParticipant.full_name, newParticipant.id_number]);

  // Check if supervisor exists in system
  useEffect(() => {
    const checkSupervisorMatch = async () => {
      if (!newSupervisor.full_name && !newSupervisor.id_number && !newSupervisor.email) {
        setSupervisorMatchStatus(null);
        return;
      }
      
      try {
        const response = await axiosInstance.get("/supervisor/check-existing", {
          params: {
            full_name: newSupervisor.full_name || undefined,
            id_number: newSupervisor.id_number || undefined,
            email: newSupervisor.email || undefined,
          }
        });
        setSupervisorMatchStatus(response.data);
      } catch (error) {
        setSupervisorMatchStatus(null);
      }
    };
    
    const debounce = setTimeout(checkSupervisorMatch, 300);
    return () => clearTimeout(debounce);
  }, [newSupervisor.full_name, newSupervisor.id_number, newSupervisor.email]);

  // Add participant to form
  const handleAddParticipant = () => {
    if (!newParticipant.full_name || !newParticipant.id_number) {
      toast.error("Name and ID number are required");
      return;
    }
    
    const participantWithDefaults = {
      ...newParticipant,
      email: newParticipant.email || `${newParticipant.id_number}@participant.local`,
      password: newParticipant.password || "mddrc1",
    };
    
    setSessionForm({
      ...sessionForm,
      participants: [...sessionForm.participants, participantWithDefaults],
    });
    
    setNewParticipant(initialNewParticipant);
    setParticipantMatchStatus(null);
  };

  // Remove participant from form
  const handleRemoveParticipant = (index) => {
    const updated = sessionForm.participants.filter((_, i) => i !== index);
    setSessionForm({ ...sessionForm, participants: updated });
  };

  // Add supervisor to form
  const handleAddSupervisor = () => {
    if (!newSupervisor.full_name) {
      toast.error("Supervisor name is required");
      return;
    }
    
    setSessionForm({
      ...sessionForm,
      supervisors: [...sessionForm.supervisors, { ...newSupervisor }],
    });
    
    setNewSupervisor(initialNewSupervisor);
    setSupervisorMatchStatus(null);
  };

  // Add trainer assignment
  const handleAddTrainerAssignment = () => {
    if (!newTrainerAssignment.trainer_id) {
      toast.error("Please select a trainer");
      return;
    }
    
    if (sessionForm.trainer_assignments.some(t => t.trainer_id === newTrainerAssignment.trainer_id)) {
      toast.error("This trainer is already assigned to this session");
      return;
    }
    
    setSessionForm({
      ...sessionForm,
      trainer_assignments: [...sessionForm.trainer_assignments, { ...newTrainerAssignment }],
    });
    
    setNewTrainerAssignment(initialNewTrainerAssignment);
  };

  // Remove trainer assignment
  const handleRemoveTrainerAssignment = (index) => {
    const updated = sessionForm.trainer_assignments.filter((_, i) => i !== index);
    setSessionForm({ ...sessionForm, trainer_assignments: updated });
  };

  // Create new session
  const handleCreateSession = async (e) => {
    e.preventDefault();
    
    // Participants are now optional - sessions can be created without participants
    // and participants can be added later via bulk upload or manual entry
    
    try {
      const program = programs.find(p => p.id === sessionForm.program_id);
      const sessionName = program ? 
        `${program.name} - ${new Date(sessionForm.start_date).toLocaleDateString('en-MY', { day: 'numeric', month: 'short', year: 'numeric' })}` :
        `Session - ${sessionForm.start_date}`;
      
      const response = await axiosInstance.post("/sessions", {
        name: sessionName,
        program_id: sessionForm.program_id,
        company_id: sessionForm.company_id,
        location: sessionForm.location,
        start_date: sessionForm.start_date,
        end_date: sessionForm.end_date,
        venue_type: sessionForm.venue_type,
        participants: sessionForm.participants,
        venue_type: sessionForm.venue_type,
        supervisors: sessionForm.supervisors,
        trainer_assignments: sessionForm.trainer_assignments,
        coordinator_id: sessionForm.coordinator_id || null,
        // Marketing commission
        marketing_user_id: sessionForm.marketing_user_id || null,
        commission_type: sessionForm.commission_type || null,
        commission_rate: sessionForm.commission_rate ? parseFloat(sessionForm.commission_rate) : null,
        commission_fixed_amount: sessionForm.commission_fixed_amount ? parseFloat(sessionForm.commission_fixed_amount) : null,
        // New marketing person
        create_new_marketing: sessionForm.create_new_marketing,
        new_marketing_name: sessionForm.new_marketing_name || null,
        new_marketing_id: sessionForm.new_marketing_id || null,
      });
      
      const participantCount = response.data.participant_count || 0;
      toast.success(participantCount > 0 
        ? `Session created with ${participantCount} participants` 
        : "Session created successfully. You can add participants later.");
      setSessionForm(initialSessionForm);
      setSessionDialogOpen(false);
      onRefresh();
    } catch (error) {
      console.error("Session creation error:", error);
      const errorMessage = error.response?.data?.detail || "Failed to create session";
      toast.error(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
    }
  };

  // Edit session handler
  const handleEditSession = (session) => {
    setEditingSession({
      ...session,
      trainer_assignments: session.trainer_assignments || [],
      coordinator_id: session.coordinator_id || "",
      marketing_user_id: session.marketing_user_id || "",
      commission_type: session.commission_type || "percentage",
      commission_rate: session.commission_rate || "",
      commission_fixed_amount: session.commission_fixed_amount || "",
    });
    setEditSessionDialogOpen(true);
  };

  // Update existing session
  const handleUpdateSession = async () => {
    if (!editingSession) return;
    
    try {
      await axiosInstance.put(`/sessions/${editingSession.id}`, {
        name: editingSession.name,
        program_id: editingSession.program_id,
        company_id: editingSession.company_id,
        location: editingSession.location,
        start_date: editingSession.start_date,
        end_date: editingSession.end_date,
        venue_type: editingSession.venue_type,
        trainer_assignments: editingSession.trainer_assignments,
        coordinator_id: editingSession.coordinator_id || null,
        marketing_user_id: editingSession.marketing_user_id || null,
        commission_type: editingSession.commission_type || null,
        commission_rate: editingSession.commission_rate ? parseFloat(editingSession.commission_rate) : null,
        commission_fixed_amount: editingSession.commission_fixed_amount ? parseFloat(editingSession.commission_fixed_amount) : null,
      });
      
      toast.success("Session updated successfully");
      setEditSessionDialogOpen(false);
      setEditingSession(null);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update session");
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle>Training Sessions</CardTitle>
            <CardDescription>Create and manage sessions</CardDescription>
          </div>
          <Dialog open={sessionDialogOpen} onOpenChange={setSessionDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="create-session-button" disabled={programs.length === 0 || companies.length === 0}>
                <Calendar className="w-4 h-4 mr-2" />
                Add Session
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Create New Session</DialogTitle>
                <DialogDescription>
                  Configure session details, participants, and trainers
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateSession} className="space-y-6">
                {/* Session Details */}
                <div className="space-y-4">
                  <h3 className="font-semibold text-lg">Session Details</h3>
                  <div>
                    <Label htmlFor="session-program">Program/Module *</Label>
                    <Select
                      value={sessionForm.program_id}
                      onValueChange={(value) => setSessionForm({ ...sessionForm, program_id: value })}
                      required
                    >
                      <SelectTrigger data-testid="session-program-select">
                        <SelectValue placeholder="Select program" />
                      </SelectTrigger>
                      <SelectContent>
                        {programs.map((program) => (
                          <SelectItem key={program.id} value={program.id}>
                            {program.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="session-company">Company *</Label>
                    <Select
                      value={sessionForm.company_id}
                      onValueChange={(value) => setSessionForm({ ...sessionForm, company_id: value })}
                      required
                    >
                      <SelectTrigger data-testid="session-company-select">
                        <SelectValue placeholder="Select company" />
                      </SelectTrigger>
                      <SelectContent>
                        {companies.map((company) => (
                          <SelectItem key={company.id} value={company.id}>
                            {company.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="session-location">Location *</Label>
                    <Input
                      id="session-location"
                      data-testid="session-location-input"
                      value={sessionForm.location}
                      onChange={(e) => setSessionForm({ ...sessionForm, location: e.target.value })}
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="start-date">Start Date *</Label>
                      <Input
                        id="start-date"
                        data-testid="session-start-date-input"
                        type="date"
                        value={sessionForm.start_date}
                        onChange={(e) => setSessionForm({ ...sessionForm, start_date: e.target.value })}
                        required
                      />
                    </div>
                    <div>
                      <Label htmlFor="end-date">End Date *</Label>
                      <Input
                        id="end-date"
                        data-testid="session-end-date-input"
                        type="date"
                        value={sessionForm.end_date}
                        onChange={(e) => setSessionForm({ ...sessionForm, end_date: e.target.value })}
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* Assign Trainers */}
                <div className="space-y-4 border-t pt-4">
                  <h3 className="font-semibold text-lg">Assign Trainers</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>Select Trainer</Label>
                      <Select
                        value={newTrainerAssignment.trainer_id}
                        onValueChange={(value) => setNewTrainerAssignment({ ...newTrainerAssignment, trainer_id: value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select trainer" />
                        </SelectTrigger>
                        <SelectContent>
                          {trainers.map((trainer) => (
                            <SelectItem key={trainer.id} value={trainer.id}>
                              {trainer.full_name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>Role for This Session</Label>
                      <Select
                        value={newTrainerAssignment.role}
                        onValueChange={(value) => setNewTrainerAssignment({ ...newTrainerAssignment, role: value })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="regular">Regular Trainer</SelectItem>
                          <SelectItem value="chief">Chief Trainer</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <Button
                    type="button"
                    onClick={handleAddTrainerAssignment}
                    variant="outline"
                    className="w-full"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Assign Trainer
                  </Button>
                  {sessionForm.trainer_assignments.length > 0 && (
                    <div className="space-y-2">
                      <Label className="text-sm text-gray-700">Assigned Trainers</Label>
                      {sessionForm.trainer_assignments.map((assignment, idx) => (
                        <div key={idx} className="flex justify-between items-center p-2 bg-blue-50 rounded">
                          <span className="text-sm">
                            {getTrainerName(assignment.trainer_id)} - <strong>{assignment.role === "chief" ? "Chief Trainer" : "Regular Trainer"}</strong>
                          </span>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveTrainerAssignment(idx)}
                          >
                            <Trash2 className="w-4 h-4 text-red-600" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Assign Coordinator */}
                <div className="space-y-4 border-t pt-4">
                  <h3 className="font-semibold text-lg">Assign Coordinator (Optional)</h3>
                  <p className="text-sm text-gray-500">Any staff member can be assigned as coordinator for this session</p>
                  <Select
                    value={sessionForm.coordinator_id}
                    onValueChange={(value) => setSessionForm({ ...sessionForm, coordinator_id: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select coordinator" />
                    </SelectTrigger>
                    <SelectContent>
                      {allStaffForCoordinator.map((staff) => (
                        <SelectItem key={staff.id} value={staff.id}>
                          {staff.full_name} ({staff.role.replace('_', ' ')})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Marketing Commission */}
                <div className="space-y-4 border-t pt-4">
                  <h3 className="font-semibold text-lg flex items-center gap-2">
                    <DollarSign className="w-5 h-5 text-green-600" />
                    Marketing Commission (Optional)
                  </h3>
                  
                  {/* Create New Marketing Person Checkbox */}
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="create-new-marketing"
                      checked={sessionForm.create_new_marketing}
                      onChange={(e) => setSessionForm({ 
                        ...sessionForm, 
                        create_new_marketing: e.target.checked,
                        marketing_user_id: e.target.checked ? "" : sessionForm.marketing_user_id 
                      })}
                    />
                    <Label htmlFor="create-new-marketing">Create new marketing person</Label>
                  </div>
                  
                  {sessionForm.create_new_marketing ? (
                    <div className="grid grid-cols-2 gap-4 p-4 bg-blue-50 rounded-lg">
                      <div>
                        <Label>Full Name *</Label>
                        <Input
                          value={sessionForm.new_marketing_name}
                          onChange={(e) => setSessionForm({ ...sessionForm, new_marketing_name: e.target.value })}
                          placeholder="Marketing person name"
                        />
                      </div>
                      <div>
                        <Label>IC Number * (will be user ID)</Label>
                        <Input
                          value={sessionForm.new_marketing_id}
                          onChange={(e) => setSessionForm({ ...sessionForm, new_marketing_id: e.target.value })}
                          placeholder="IC number (e.g. 890101-12-5678)"
                        />
                        <p className="text-xs text-gray-500 mt-1">Default password: mddrc1</p>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Marketing Person</Label>
                        <Select
                          value={sessionForm.marketing_user_id || "none"}
                          onValueChange={(value) => setSessionForm({ ...sessionForm, marketing_user_id: value === "none" ? "" : value })}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select marketing person" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">None</SelectItem>
                            {marketingUsers.map((user) => (
                              <SelectItem key={user.id} value={user.id}>
                                {user.full_name} ({user.role}{user.additional_roles?.includes("marketing") ? " + Marketing" : ""})
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label>Commission Type</Label>
                        <Select
                          value={sessionForm.commission_type}
                          onValueChange={(value) => setSessionForm({ ...sessionForm, commission_type: value })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="percentage">Percentage (%)</SelectItem>
                            <SelectItem value="fixed">Fixed Amount (RM)</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  )}
                  
                  {(sessionForm.marketing_user_id || sessionForm.create_new_marketing) && (
                    <div className="grid grid-cols-2 gap-4">
                      {sessionForm.create_new_marketing && (
                        <div>
                          <Label>Commission Type</Label>
                          <Select
                            value={sessionForm.commission_type}
                            onValueChange={(value) => setSessionForm({ ...sessionForm, commission_type: value })}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="percentage">Percentage of Profit</SelectItem>
                              <SelectItem value="fixed">Fixed Amount (RM)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      )}
                      {sessionForm.commission_type === "percentage" ? (
                        <div>
                          <Label>Commission Rate (%)</Label>
                          <Input
                            type="number"
                            min="0"
                            max="100"
                            step="0.1"
                            value={sessionForm.commission_rate}
                            onChange={(e) => setSessionForm({ ...sessionForm, commission_rate: e.target.value })}
                            placeholder="e.g. 10"
                          />
                          <p className="text-xs text-gray-500 mt-1">% of NET profit (after all expenses)</p>
                        </div>
                      ) : (
                        <div>
                          <Label>Fixed Amount (RM)</Label>
                          <Input
                            type="number"
                            min="0"
                            step="0.01"
                            value={sessionForm.commission_fixed_amount}
                            onChange={(e) => setSessionForm({ ...sessionForm, commission_fixed_amount: e.target.value })}
                            placeholder="e.g. 500"
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Add Supervisor (Optional) */}
                <div className="space-y-4 border-t pt-4">
                  <h3 className="font-semibold text-lg">Add Supervisor (Optional)</h3>
                  
                  {/* Match Status Indicator */}
                  {supervisorMatchStatus?.exists && (
                    <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-sm">
                      <p className="font-semibold text-blue-800">✓ Existing supervisor found</p>
                      <p className="text-blue-600 mt-1">
                        {supervisorMatchStatus.user.full_name} ({supervisorMatchStatus.user.email})
                        <br />
                        Will be linked to this session and data will be updated.
                      </p>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor="supervisor-name">Full Name</Label>
                      <Input
                        id="supervisor-name"
                        value={newSupervisor.full_name}
                        onChange={(e) => setNewSupervisor({ ...newSupervisor, full_name: e.target.value })}
                        placeholder="Supervisor Name"
                      />
                    </div>
                    <div>
                      <Label htmlFor="supervisor-id">ID Number</Label>
                      <Input
                        id="supervisor-id"
                        value={newSupervisor.id_number}
                        onChange={(e) => setNewSupervisor({ ...newSupervisor, id_number: e.target.value })}
                        placeholder="ID123456"
                      />
                    </div>
                    <div>
                      <Label htmlFor="supervisor-email">Email</Label>
                      <Input
                        id="supervisor-email"
                        type="email"
                        value={newSupervisor.email}
                        onChange={(e) => setNewSupervisor({ ...newSupervisor, email: e.target.value })}
                        placeholder="supervisor@example.com"
                      />
                    </div>
                    <div>
                      <Label htmlFor="supervisor-phone">Phone Number</Label>
                      <Input
                        id="supervisor-phone"
                        type="tel"
                        value={newSupervisor.phone_number}
                        onChange={(e) => setNewSupervisor({ ...newSupervisor, phone_number: e.target.value })}
                        placeholder="+1234567890"
                      />
                    </div>
                    <div className="col-span-2">
                      <Label htmlFor="supervisor-password">Password</Label>
                      <Input
                        id="supervisor-password"
                        type="password"
                        value={newSupervisor.password}
                        onChange={(e) => setNewSupervisor({ ...newSupervisor, password: e.target.value })}
                        placeholder="Password"
                      />
                    </div>
                  </div>
                  <Button
                    type="button"
                    onClick={handleAddSupervisor}
                    variant="outline"
                    className="w-full"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    {supervisorMatchStatus?.exists ? "Link Existing Supervisor" : "Add New Supervisor"}
                  </Button>

                  {/* Show added supervisors */}
                  {sessionForm.supervisors.length > 0 && (
                    <div className="space-y-2 border-t pt-4 mt-4">
                      <h4 className="font-semibold text-sm text-gray-700">
                        Supervisors to Add ({sessionForm.supervisors.length})
                      </h4>
                      {sessionForm.supervisors.map((sup, index) => (
                        <div
                          key={index}
                          className="flex justify-between items-center p-3 bg-purple-50 rounded-lg"
                        >
                          <div>
                            <p className="font-medium text-sm">{sup.full_name}</p>
                            <p className="text-xs text-gray-600">
                              {sup.email} • ID: {sup.id_number}
                            </p>
                          </div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              const updated = sessionForm.supervisors.filter((_, i) => i !== index);
                              setSessionForm({ ...sessionForm, supervisors: updated });
                            }}
                          >
                            <Trash2 className="w-4 h-4 text-red-600" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Add Participants */}
                <div className="space-y-4 border-t pt-4">
                  <h3 className="font-semibold text-lg">Add Participants</h3>
                  <p className="text-sm text-gray-600">
                    Type participant details below. Login ID will be their IC number and default password is &quot;mddrc1&quot;. System will automatically link existing users if name or ID number matches.
                  </p>
                  
                  {/* Match Status Indicator */}
                  {participantMatchStatus?.exists && (
                    <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-sm">
                      <p className="font-semibold text-blue-800">✓ Existing participant found</p>
                      <p className="text-blue-600 mt-1">
                        {participantMatchStatus.user.full_name} ({participantMatchStatus.user.email})
                        <br />
                        Will be linked to this session and data will be updated.
                      </p>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label htmlFor="participant-name">Full Name *</Label>
                      <Input
                        id="participant-name"
                        data-testid="participant-name-input"
                        value={newParticipant.full_name}
                        onChange={(e) => setNewParticipant({ ...newParticipant, full_name: e.target.value })}
                        placeholder="John Doe"
                      />
                    </div>
                    <div>
                      <Label htmlFor="participant-id">ID Number * (will be used as login ID)</Label>
                      <Input
                        id="participant-id"
                        data-testid="participant-id-input"
                        value={newParticipant.id_number}
                        onChange={(e) => setNewParticipant({ ...newParticipant, id_number: e.target.value })}
                        placeholder="990101-01-1234"
                      />
                    </div>
                    <div>
                      <Label htmlFor="participant-email">Email (optional)</Label>
                      <Input
                        id="participant-email"
                        data-testid="participant-email-input"
                        type="email"
                        value={newParticipant.email}
                        onChange={(e) => setNewParticipant({ ...newParticipant, email: e.target.value })}
                        placeholder="john@example.com (optional)"
                      />
                    </div>
                    <div>
                      <Label htmlFor="participant-phone">Phone Number (optional)</Label>
                      <Input
                        id="participant-phone"
                        data-testid="participant-phone-input"
                        type="tel"
                        value={newParticipant.phone_number}
                        onChange={(e) => setNewParticipant({ ...newParticipant, phone_number: e.target.value })}
                        placeholder="+60123456789 (optional)"
                      />
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 bg-blue-50 p-2 rounded">
                    💡 Default login: IC number / password: mddrc1
                  </p>
                  <Button
                    type="button"
                    data-testid="add-participant-button"
                    onClick={handleAddParticipant}
                    variant="outline"
                    className="w-full"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    {participantMatchStatus?.exists ? "Link Existing Participant" : "Add New Participant"}
                  </Button>
                </div>

                {sessionForm.participants.length > 0 && (
                  <div className="space-y-2 border-t pt-4">
                    <h3 className="font-semibold text-sm text-gray-700">
                      Participants ({sessionForm.participants.length})
                    </h3>
                    {sessionForm.participants.map((participant, index) => (
                      <div
                        key={index}
                        data-testid={`participant-list-item-${index}`}
                        className="flex justify-between items-center p-3 bg-green-50 rounded-lg"
                      >
                        <div>
                          <p className="font-medium text-sm">{participant.full_name}</p>
                          <p className="text-xs text-gray-600">
                            {participant.email} • ID: {participant.id_number}
                          </p>
                        </div>
                        <Button
                          type="button"
                          data-testid={`remove-participant-${index}`}
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveParticipant(index)}
                        >
                          <Trash2 className="w-4 h-4 text-red-600" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                <Button
                  data-testid="submit-session-button"
                  type="submit"
                  className="w-full"
                >
                  {sessionForm.participants.length > 0 
                    ? `Create Session with ${sessionForm.participants.length} Participant(s)`
                    : "Create Session"}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {programs.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">Please create at least one program first</p>
          </div>
        ) : companies.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">Please create at least one company first</p>
          </div>
        ) : (
          <>
            <div className="mb-4 flex flex-wrap gap-4 items-end">
              <div className="flex-1 min-w-[200px]">
                <SearchBar
                  placeholder="Search sessions by name, company, program, or location..."
                  onSearch={setSessionsSearch}
                  className="w-full"
                />
              </div>
              <div className="flex items-center gap-2">
                <Label className="text-sm whitespace-nowrap">Month:</Label>
                <Input
                  type="month"
                  value={sessionsMonthFilter}
                  onChange={(e) => setSessionsMonthFilter(e.target.value)}
                  className="w-40"
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSessionsMonthFilter("all")}
                  className={sessionsMonthFilter === "all" ? "bg-blue-100" : ""}
                >
                  All
                </Button>
              </div>
            </div>
            {sessionsMonthFilter && sessionsMonthFilter !== "all" && (
              <div className="mb-3 text-sm text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
                Showing sessions for: <strong>{new Date(sessionsMonthFilter + '-01').toLocaleString('en-MY', { month: 'long', year: 'numeric' })}</strong>
                {' '}({filteredSessions.length} session{filteredSessions.length !== 1 ? 's' : ''})
              </div>
            )}
            <div className="space-y-3">
              {filteredSessions.length === 0 ? (
                <p className="text-gray-500 text-center py-8">
                  {sessionsSearch || sessionsMonthFilter !== "all" ? "No sessions match your filters." : "No sessions yet"}
                </p>
              ) : (
                filteredSessions.map((session) => {
                const company = companies.find((c) => c.id === session.company_id);
                const program = programs.find((p) => p.id === session.program_id);
                return (
                  <div
                    key={session.id}
                    data-testid={`session-item-${session.id}`}
                    className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-semibold text-lg text-gray-900">{session.company_name || company?.name || "Unknown Company"}</h3>
                        <p className="text-base text-gray-700 mt-1">{session.program_name || program?.name || "Unknown Program"}</p>
                        <div className="mt-2 text-sm text-gray-600 space-y-1">
                          <p>Session: {session.name}</p>
                          <p>Location: {session.location}</p>
                          <p>Duration: {session.start_date} to {session.end_date}</p>
                          {session.trainer_assignments && session.trainer_assignments.length > 0 && (
                            <p>Trainers: {session.trainer_assignments.map(t => `${getTrainerName(t.trainer_id)} (${t.role})`).join(", ")}</p>
                          )}
                          {session.coordinator_id && (
                            <p>Coordinator: {getCoordinatorName(session.coordinator_id)}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-col gap-2 items-end">
                        <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                          {session.participant_ids.length} Participants
                        </span>
                        <div className="flex gap-2 flex-wrap justify-end">
                          <Button
                            data-testid={`bulk-upload-session-${session.id}`}
                            size="sm"
                            variant="outline"
                            className="bg-purple-50 border-purple-200 hover:bg-purple-100 text-purple-700"
                            onClick={() => onBulkUploadClick(session)}
                          >
                            <Upload className="w-4 h-4 mr-1" />
                            Bulk Upload
                          </Button>
                          <Button
                            data-testid={`costing-session-${session.id}`}
                            size="sm"
                            variant="outline"
                            className="bg-green-50 border-green-200 hover:bg-green-100 text-green-700"
                            onClick={() => onCostingClick(session)}
                          >
                            <DollarSign className="w-4 h-4 mr-1" />
                            Costing
                          </Button>
                          <Button
                            data-testid={`indemnity-session-${session.id}`}
                            size="sm"
                            variant="outline"
                            className="bg-purple-50 border-purple-200 hover:bg-purple-100 text-purple-700"
                            onClick={() => onIndemnityClick(session)}
                          >
                            <FileText className="w-4 h-4 mr-1" />
                            Indemnity
                          </Button>
                          <Button
                            data-testid={`edit-session-${session.id}`}
                            size="sm"
                            variant="outline"
                            onClick={() => handleEditSession(session)}
                          >
                            <Edit className="w-4 h-4 mr-1" />
                            Edit
                          </Button>
                          <Button
                            data-testid={`delete-session-${session.id}`}
                            size="sm"
                            variant="destructive"
                            onClick={() => onDeleteClick("session", session)}
                          >
                            <Trash2 className="w-4 h-4 mr-1" />
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
                })
              )}
            </div>
          </>
        )}
      </CardContent>

      {/* Edit Session Dialog */}
      <Dialog open={editSessionDialogOpen} onOpenChange={setEditSessionDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Session</DialogTitle>
            <DialogDescription>
              Modify session details
            </DialogDescription>
          </DialogHeader>
          {editingSession && (
            <div className="space-y-4">
              <div>
                <Label>Session Name</Label>
                <Input
                  value={editingSession.name || ""}
                  onChange={(e) => setEditingSession({ ...editingSession, name: e.target.value })}
                />
              </div>
              <div>
                <Label>Location</Label>
                <Input
                  value={editingSession.location || ""}
                  onChange={(e) => setEditingSession({ ...editingSession, location: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={editingSession.start_date || ""}
                    onChange={(e) => setEditingSession({ ...editingSession, start_date: e.target.value })}
                  />
                </div>
                <div>
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={editingSession.end_date || ""}
                    onChange={(e) => setEditingSession({ ...editingSession, end_date: e.target.value })}
                  />
                </div>
              </div>
              
              {/* Coordinator Selection */}
              <div>
                <Label>Coordinator</Label>
                <Select
                  value={editingSession.coordinator_id || "none"}
                  onValueChange={(value) => setEditingSession({ ...editingSession, coordinator_id: value === "none" ? "" : value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select coordinator" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {allStaffForCoordinator.map((staff) => (
                      <SelectItem key={staff.id} value={staff.id}>
                        {staff.full_name} ({staff.role.replace('_', ' ')})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Marketing Commission */}
              <div className="space-y-3 border-t pt-4">
                <h4 className="font-semibold">Marketing Commission</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Marketing Person</Label>
                    <Select
                      value={editingSession.marketing_user_id || "none"}
                      onValueChange={(value) => setEditingSession({ ...editingSession, marketing_user_id: value === "none" ? "" : value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select marketing person" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        {marketingUsers.map((user) => (
                          <SelectItem key={user.id} value={user.id}>
                            {user.full_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Commission Type</Label>
                    <Select
                      value={editingSession.commission_type || "percentage"}
                      onValueChange={(value) => setEditingSession({ ...editingSession, commission_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="percentage">Percentage (%)</SelectItem>
                        <SelectItem value="fixed">Fixed Amount (RM)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                {editingSession.commission_type === "percentage" ? (
                  <div>
                    <Label>Commission Rate (%)</Label>
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      value={editingSession.commission_rate || ""}
                      onChange={(e) => setEditingSession({ ...editingSession, commission_rate: e.target.value })}
                    />
                  </div>
                ) : (
                  <div>
                    <Label>Fixed Amount (RM)</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={editingSession.commission_fixed_amount || ""}
                      onChange={(e) => setEditingSession({ ...editingSession, commission_fixed_amount: e.target.value })}
                    />
                  </div>
                )}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditSessionDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateSession}>
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export { SessionsTab };
