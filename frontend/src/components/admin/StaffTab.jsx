/**
 * StaffTab Component - Extracted from AdminDashboard
 * Manages all staff members (Coordinators, Assistant Admins, Trainers, Finance Users)
 */
import { useState, useMemo } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";
import { UserPlus, UserCog, Trash2, Edit, DollarSign } from "lucide-react";
import { SearchBar } from "../SearchBar";

// Initial form states
const initialCoordinatorForm = {
  email: "",
  password: "",
  full_name: "",
  id_number: "",
  additional_roles: [],
};

const initialAssistantAdminForm = {
  email: "",
  password: "",
  full_name: "",
  id_number: "",
  additional_roles: [],
};

const initialTrainerForm = {
  email: "",
  password: "",
  full_name: "",
  id_number: "",
};

const initialFinanceForm = {
  email: "",
  password: "",
  full_name: "",
  id_number: "",
};

const initialEditStaffForm = {
  full_name: "",
  email: "",
  id_number: "",
  additional_roles: [],
};

const StaffTab = ({
  users,
  onRefresh,
  onDeleteClick,
}) => {
  // Search state
  const [staffSearch, setStaffSearch] = useState("");
  
  // Dialog states
  const [coordinatorDialogOpen, setCoordinatorDialogOpen] = useState(false);
  const [assistantAdminDialogOpen, setAssistantAdminDialogOpen] = useState(false);
  const [trainerDialogOpen, setTrainerDialogOpen] = useState(false);
  const [financeDialogOpen, setFinanceDialogOpen] = useState(false);
  const [editStaffDialogOpen, setEditStaffDialogOpen] = useState(false);
  
  // Form states
  const [coordinatorForm, setCoordinatorForm] = useState(initialCoordinatorForm);
  const [assistantAdminForm, setAssistantAdminForm] = useState(initialAssistantAdminForm);
  const [trainerForm, setTrainerForm] = useState(initialTrainerForm);
  const [financeForm, setFinanceForm] = useState(initialFinanceForm);
  const [editStaffForm, setEditStaffForm] = useState(initialEditStaffForm);
  const [editingStaff, setEditingStaff] = useState(null);

  // Filter staff by search
  const { filteredCoordinators, filteredTrainers, filteredAssistantAdmins } = useMemo(() => {
    if (!staffSearch) {
      return {
        filteredCoordinators: users.filter(u => u.role === "coordinator"),
        filteredTrainers: users.filter(u => u.role === "trainer"),
        filteredAssistantAdmins: users.filter(u => u.role === "assistant_admin"),
      };
    }
    
    const searchLower = staffSearch.toLowerCase();
    const matchesSearch = (user) =>
      user.full_name?.toLowerCase().includes(searchLower) ||
      user.email?.toLowerCase().includes(searchLower) ||
      user.id_number?.toLowerCase().includes(searchLower);
    
    return {
      filteredCoordinators: users.filter(u => u.role === "coordinator" && matchesSearch(u)),
      filteredTrainers: users.filter(u => u.role === "trainer" && matchesSearch(u)),
      filteredAssistantAdmins: users.filter(u => u.role === "assistant_admin" && matchesSearch(u)),
    };
  }, [staffSearch, users]);

  // Create handlers
  const handleCreateTrainer = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/users/trainer", trainerForm);
      toast.success("Trainer created successfully");
      setTrainerForm(initialTrainerForm);
      setTrainerDialogOpen(false);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create trainer");
    }
  };

  const handleCreateCoordinator = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/users/coordinator", coordinatorForm);
      toast.success("Coordinator created successfully");
      setCoordinatorForm(initialCoordinatorForm);
      setCoordinatorDialogOpen(false);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create coordinator");
    }
  };

  const handleCreateAssistantAdmin = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/users/assistant-admin", assistantAdminForm);
      toast.success("Assistant Admin created successfully");
      setAssistantAdminForm(initialAssistantAdminForm);
      setAssistantAdminDialogOpen(false);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create assistant admin");
    }
  };

  const handleCreateFinance = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.post("/users/finance", financeForm);
      toast.success("Finance user created successfully");
      setFinanceForm(initialFinanceForm);
      setFinanceDialogOpen(false);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create finance user");
    }
  };

  // Edit handlers
  const handleEditStaff = (staff) => {
    setEditingStaff(staff);
    setEditStaffForm({
      full_name: staff.full_name,
      email: staff.email,
      id_number: staff.id_number,
      additional_roles: staff.additional_roles || [],
    });
    setEditStaffDialogOpen(true);
  };

  const handleUpdateStaff = async (e) => {
    e.preventDefault();
    try {
      await axiosInstance.put(`/users/${editingStaff.id}`, editStaffForm);
      toast.success(`${editingStaff.role.replace('_', ' ')} updated successfully`);
      setEditStaffDialogOpen(false);
      setEditingStaff(null);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update staff");
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Staff Management</CardTitle>
          <CardDescription>Manage all staff members (Coordinators, Assistant Admins, Trainers)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <SearchBar
              placeholder="Search staff by name, email, or ID..."
              onSearch={setStaffSearch}
              className="max-w-md"
            />
          </div>
          <div className="space-y-6">
            
            {/* Coordinators Section */}
            <Card className="border-2 border-purple-200">
              <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50">
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle className="text-lg">Coordinators</CardTitle>
                    <CardDescription>Manage training coordinators ({filteredCoordinators.length} {staffSearch ? 'found' : 'total'})</CardDescription>
                  </div>
                  <Dialog open={coordinatorDialogOpen} onOpenChange={setCoordinatorDialogOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm" data-testid="create-coordinator-button">
                        <UserCog className="w-4 h-4 mr-2" />
                        Add Coordinator
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Create New Coordinator</DialogTitle>
                        <DialogDescription>
                          Add a coordinator account
                        </DialogDescription>
                      </DialogHeader>
                      <form onSubmit={handleCreateCoordinator} className="space-y-4">
                        <div>
                          <Label htmlFor="coordinator-name">Full Name *</Label>
                          <Input
                            id="coordinator-name"
                            data-testid="coordinator-name-input"
                            value={coordinatorForm.full_name}
                            onChange={(e) => setCoordinatorForm({ ...coordinatorForm, full_name: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="coordinator-id">ID Number *</Label>
                          <Input
                            id="coordinator-id"
                            data-testid="coordinator-id-input"
                            value={coordinatorForm.id_number}
                            onChange={(e) => setCoordinatorForm({ ...coordinatorForm, id_number: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="coordinator-email">Email *</Label>
                          <Input
                            id="coordinator-email"
                            data-testid="coordinator-email-input"
                            type="email"
                            value={coordinatorForm.email}
                            onChange={(e) => setCoordinatorForm({ ...coordinatorForm, email: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="coordinator-password">Password *</Label>
                          <Input
                            id="coordinator-password"
                            data-testid="coordinator-password-input"
                            type="password"
                            value={coordinatorForm.password}
                            onChange={(e) => setCoordinatorForm({ ...coordinatorForm, password: e.target.value })}
                            required
                          />
                        </div>
                        <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-lg">
                          <input
                            type="checkbox"
                            id="coordinator-marketing"
                            checked={coordinatorForm.additional_roles.includes("marketing")}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setCoordinatorForm({ ...coordinatorForm, additional_roles: [...coordinatorForm.additional_roles, "marketing"] });
                              } else {
                                setCoordinatorForm({ ...coordinatorForm, additional_roles: coordinatorForm.additional_roles.filter(r => r !== "marketing") });
                              }
                            }}
                            className="w-4 h-4"
                          />
                          <Label htmlFor="coordinator-marketing" className="text-sm font-medium">
                            Also has Marketing access (can view training calendar & own commission)
                          </Label>
                        </div>
                        <Button data-testid="submit-coordinator-button" type="submit" className="w-full">
                          Create Coordinator
                        </Button>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="space-y-2">
                  {filteredCoordinators.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">
                      {staffSearch ? "No coordinators match your search." : "No coordinators yet"}
                    </p>
                  ) : (
                    filteredCoordinators.map((coordinator) => (
                      <div
                        key={coordinator.id}
                        data-testid={`coordinator-item-${coordinator.id}`}
                        className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg hover:bg-purple-100 transition-colors flex justify-between items-start"
                      >
                        <div>
                          <h3 className="font-semibold text-gray-900">{coordinator.full_name}</h3>
                          <p className="text-sm text-gray-600">{coordinator.email}</p>
                          <div className="flex gap-2 mt-2 flex-wrap">
                            <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                              Coordinator
                            </span>
                            {coordinator.additional_roles?.includes("marketing") && (
                              <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                + Marketing
                              </span>
                            )}
                            <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                              ID: {coordinator.id_number}
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            data-testid={`edit-coordinator-${coordinator.id}`}
                            size="sm"
                            variant="outline"
                            onClick={() => handleEditStaff(coordinator)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button
                            data-testid={`delete-coordinator-${coordinator.id}`}
                            size="sm"
                            variant="destructive"
                            onClick={() => onDeleteClick("coordinator", coordinator)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Assistant Admins Section */}
            <Card className="border-2 border-blue-200">
              <CardHeader className="bg-gradient-to-r from-blue-50 to-cyan-50">
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle className="text-lg">Assistant Admins</CardTitle>
                    <CardDescription>Manage assistant administrators ({filteredAssistantAdmins.length} {staffSearch ? 'found' : 'total'})</CardDescription>
                  </div>
                  <Dialog open={assistantAdminDialogOpen} onOpenChange={setAssistantAdminDialogOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm" data-testid="create-assistant-admin-button">
                        <UserPlus className="w-4 h-4 mr-2" />
                        Add Assistant Admin
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Create New Assistant Admin</DialogTitle>
                        <DialogDescription>
                          Add an assistant admin account
                        </DialogDescription>
                      </DialogHeader>
                      <form onSubmit={handleCreateAssistantAdmin} className="space-y-4">
                        <div>
                          <Label htmlFor="assistant-admin-name">Full Name *</Label>
                          <Input
                            id="assistant-admin-name"
                            data-testid="assistant-admin-name-input"
                            value={assistantAdminForm.full_name}
                            onChange={(e) => setAssistantAdminForm({ ...assistantAdminForm, full_name: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="assistant-admin-id">ID Number *</Label>
                          <Input
                            id="assistant-admin-id"
                            data-testid="assistant-admin-id-input"
                            value={assistantAdminForm.id_number}
                            onChange={(e) => setAssistantAdminForm({ ...assistantAdminForm, id_number: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="assistant-admin-email">Email *</Label>
                          <Input
                            id="assistant-admin-email"
                            data-testid="assistant-admin-email-input"
                            type="email"
                            value={assistantAdminForm.email}
                            onChange={(e) => setAssistantAdminForm({ ...assistantAdminForm, email: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="assistant-admin-password">Password *</Label>
                          <Input
                            id="assistant-admin-password"
                            data-testid="assistant-admin-password-input"
                            type="password"
                            value={assistantAdminForm.password}
                            onChange={(e) => setAssistantAdminForm({ ...assistantAdminForm, password: e.target.value })}
                            required
                          />
                        </div>
                        <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-lg">
                          <input
                            type="checkbox"
                            id="assistant-admin-marketing"
                            checked={assistantAdminForm.additional_roles.includes("marketing")}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setAssistantAdminForm({ ...assistantAdminForm, additional_roles: [...assistantAdminForm.additional_roles, "marketing"] });
                              } else {
                                setAssistantAdminForm({ ...assistantAdminForm, additional_roles: assistantAdminForm.additional_roles.filter(r => r !== "marketing") });
                              }
                            }}
                            className="w-4 h-4"
                          />
                          <Label htmlFor="assistant-admin-marketing" className="text-sm font-medium">
                            Also has Marketing access
                          </Label>
                        </div>
                        <Button data-testid="submit-assistant-admin-button" type="submit" className="w-full">
                          Create Assistant Admin
                        </Button>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="space-y-2">
                  {filteredAssistantAdmins.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">
                      {staffSearch ? "No assistant admins match your search." : "No assistant admins yet"}
                    </p>
                  ) : (
                    filteredAssistantAdmins.map((assistantAdmin) => (
                      <div
                        key={assistantAdmin.id}
                        data-testid={`assistant-admin-item-${assistantAdmin.id}`}
                        className="p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg hover:bg-blue-100 transition-colors flex justify-between items-start"
                      >
                        <div>
                          <h3 className="font-semibold text-gray-900">{assistantAdmin.full_name}</h3>
                          <p className="text-sm text-gray-600">{assistantAdmin.email}</p>
                          <div className="flex gap-2 mt-2 flex-wrap">
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                              Assistant Admin
                            </span>
                            {assistantAdmin.additional_roles?.includes("marketing") && (
                              <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                + Marketing
                              </span>
                            )}
                            <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                              ID: {assistantAdmin.id_number}
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            data-testid={`edit-assistant-admin-${assistantAdmin.id}`}
                            size="sm"
                            variant="outline"
                            onClick={() => handleEditStaff(assistantAdmin)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button
                            data-testid={`delete-assistant-admin-${assistantAdmin.id}`}
                            size="sm"
                            variant="destructive"
                            onClick={() => onDeleteClick("assistant_admin", assistantAdmin)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Trainers Section */}
            <Card className="border-2 border-orange-200">
              <CardHeader className="bg-gradient-to-r from-orange-50 to-amber-50">
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle className="text-lg">Trainers</CardTitle>
                    <CardDescription>Create trainer accounts (roles assigned per session) ({filteredTrainers.length} {staffSearch ? 'found' : 'total'})</CardDescription>
                  </div>
                  <Dialog open={trainerDialogOpen} onOpenChange={setTrainerDialogOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm" data-testid="create-trainer-button">
                        <UserPlus className="w-4 h-4 mr-2" />
                        Add Trainer
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Create New Trainer</DialogTitle>
                        <DialogDescription>
                          Add a trainer account
                        </DialogDescription>
                      </DialogHeader>
                      <form onSubmit={handleCreateTrainer} className="space-y-4">
                        <div>
                          <Label htmlFor="trainer-name">Full Name *</Label>
                          <Input
                            id="trainer-name"
                            data-testid="trainer-name-input"
                            value={trainerForm.full_name}
                            onChange={(e) => setTrainerForm({ ...trainerForm, full_name: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="trainer-id">ID Number *</Label>
                          <Input
                            id="trainer-id"
                            data-testid="trainer-id-input"
                            value={trainerForm.id_number}
                            onChange={(e) => setTrainerForm({ ...trainerForm, id_number: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="trainer-email">Email *</Label>
                          <Input
                            id="trainer-email"
                            data-testid="trainer-email-input"
                            type="email"
                            value={trainerForm.email}
                            onChange={(e) => setTrainerForm({ ...trainerForm, email: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="trainer-password">Password *</Label>
                          <Input
                            id="trainer-password"
                            data-testid="trainer-password-input"
                            type="password"
                            value={trainerForm.password}
                            onChange={(e) => setTrainerForm({ ...trainerForm, password: e.target.value })}
                            required
                          />
                        </div>
                        <Button data-testid="submit-trainer-button" type="submit" className="w-full">
                          Create Trainer
                        </Button>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="space-y-2">
                  {filteredTrainers.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">
                      {staffSearch ? "No trainers match your search." : "No trainers yet"}
                    </p>
                  ) : (
                    filteredTrainers.map((trainer) => (
                      <div
                        key={trainer.id}
                        data-testid={`trainer-item-${trainer.id}`}
                        className="p-4 bg-gradient-to-r from-orange-50 to-amber-50 rounded-lg hover:bg-orange-100 transition-colors flex justify-between items-start"
                      >
                        <div>
                          <h3 className="font-semibold text-gray-900">{trainer.full_name}</h3>
                          <p className="text-sm text-gray-600">{trainer.email}</p>
                          <div className="flex gap-2 mt-2">
                            <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded">
                              Trainer
                            </span>
                            <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                              ID: {trainer.id_number}
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            data-testid={`edit-trainer-${trainer.id}`}
                            size="sm"
                            variant="outline"
                            onClick={() => handleEditStaff(trainer)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button
                            data-testid={`delete-trainer-${trainer.id}`}
                            size="sm"
                            variant="destructive"
                            onClick={() => onDeleteClick("trainer", trainer)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Finance Users Section */}
            <Card className="border-2 border-green-200">
              <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50">
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle className="text-lg">Finance Users</CardTitle>
                    <CardDescription>Manage finance portal users ({users.filter(u => u.role === "finance").length} total)</CardDescription>
                  </div>
                  <Dialog open={financeDialogOpen} onOpenChange={setFinanceDialogOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm" className="bg-green-600 hover:bg-green-700">
                        <DollarSign className="w-4 h-4 mr-2" />
                        Add Finance User
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Create Finance User</DialogTitle>
                        <DialogDescription>
                          Add a user who can access the Finance Portal
                        </DialogDescription>
                      </DialogHeader>
                      <form onSubmit={handleCreateFinance} className="space-y-4">
                        <div>
                          <Label htmlFor="finance-name">Full Name *</Label>
                          <Input
                            id="finance-name"
                            value={financeForm.full_name}
                            onChange={(e) => setFinanceForm({ ...financeForm, full_name: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="finance-id">ID Number *</Label>
                          <Input
                            id="finance-id"
                            value={financeForm.id_number}
                            onChange={(e) => setFinanceForm({ ...financeForm, id_number: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="finance-email">Email *</Label>
                          <Input
                            id="finance-email"
                            type="email"
                            value={financeForm.email}
                            onChange={(e) => setFinanceForm({ ...financeForm, email: e.target.value })}
                            required
                          />
                        </div>
                        <div>
                          <Label htmlFor="finance-password">Password *</Label>
                          <Input
                            id="finance-password"
                            type="password"
                            value={financeForm.password}
                            onChange={(e) => setFinanceForm({ ...financeForm, password: e.target.value })}
                            required
                          />
                        </div>
                        <Button type="submit" className="w-full bg-green-600 hover:bg-green-700">
                          Create Finance User
                        </Button>
                      </form>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="space-y-2">
                  {users.filter(u => u.role === "finance").length === 0 ? (
                    <p className="text-gray-500 text-center py-8">
                      No finance users yet. Create one to access the Finance Portal.
                    </p>
                  ) : (
                    users.filter(u => u.role === "finance").map((financeUser) => (
                      <div
                        key={financeUser.id}
                        className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg hover:bg-green-100 transition-colors flex justify-between items-start"
                      >
                        <div>
                          <h3 className="font-semibold text-gray-900">{financeUser.full_name}</h3>
                          <p className="text-sm text-gray-600">{financeUser.email}</p>
                          <div className="flex gap-2 mt-2">
                            <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                              Finance
                            </span>
                            <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                              ID: {financeUser.id_number}
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleEditStaff(financeUser)}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

          </div>
        </CardContent>
      </Card>

      {/* Edit Staff Dialog */}
      <Dialog open={editStaffDialogOpen} onOpenChange={setEditStaffDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Staff Member</DialogTitle>
            <DialogDescription>
              Update staff member details
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdateStaff} className="space-y-4">
            <div>
              <Label htmlFor="edit-staff-name">Full Name *</Label>
              <Input
                id="edit-staff-name"
                value={editStaffForm.full_name}
                onChange={(e) => setEditStaffForm({ ...editStaffForm, full_name: e.target.value })}
                required
              />
            </div>
            <div>
              <Label htmlFor="edit-staff-email">Email *</Label>
              <Input
                id="edit-staff-email"
                type="email"
                value={editStaffForm.email}
                onChange={(e) => setEditStaffForm({ ...editStaffForm, email: e.target.value })}
                required
              />
            </div>
            <div>
              <Label htmlFor="edit-staff-id">ID Number *</Label>
              <Input
                id="edit-staff-id"
                value={editStaffForm.id_number}
                onChange={(e) => setEditStaffForm({ ...editStaffForm, id_number: e.target.value })}
                required
              />
            </div>
            {editingStaff && ["coordinator", "assistant_admin"].includes(editingStaff.role) && (
              <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-lg">
                <input
                  type="checkbox"
                  id="edit-staff-marketing"
                  checked={editStaffForm.additional_roles?.includes("marketing")}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setEditStaffForm({ ...editStaffForm, additional_roles: [...(editStaffForm.additional_roles || []), "marketing"] });
                    } else {
                      setEditStaffForm({ ...editStaffForm, additional_roles: (editStaffForm.additional_roles || []).filter(r => r !== "marketing") });
                    }
                  }}
                  className="w-4 h-4"
                />
                <Label htmlFor="edit-staff-marketing" className="text-sm font-medium">
                  Also has Marketing access
                </Label>
              </div>
            )}
            <Button type="submit" className="w-full">
              Update Staff Member
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
};

export { StaffTab };
