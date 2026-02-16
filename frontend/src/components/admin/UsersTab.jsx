/**
 * UsersTab Component - Extracted from AdminDashboard
 * Manages all system users grouped by company with bulk operations
 */
import { useState } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { toast } from "sonner";
import { Download, Trash2, UserCog, ChevronDown, ChevronRight, Users } from "lucide-react";

const UsersTab = ({
  users,
  companies,
  onRefresh,
  onDeleteClick,
}) => {
  // Selection state
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  
  // Collapsible state - track which groups are expanded
  const [expandedGroups, setExpandedGroups] = useState({});
  
  // Reset password state
  const [resetPasswordUser, setResetPasswordUser] = useState(null);
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false);
  const [newPassword, setNewPassword] = useState("");

  const toggleGroup = (groupId) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupId]: !prev[groupId]
    }));
  };

  const toggleUserSelection = (userId) => {
    setSelectedUsers(prev =>
      prev.includes(userId)
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const toggleAllUsers = (usersToToggle) => {
    const allSelected = usersToToggle.every(u => selectedUsers.includes(u.id));
    if (allSelected) {
      setSelectedUsers(prev => prev.filter(id => !usersToToggle.some(u => u.id === id)));
    } else {
      setSelectedUsers(prev => [...new Set([...prev, ...usersToToggle.map(u => u.id)])]);
    }
  };

  const handleToggleUserStatus = async (userId, currentStatus) => {
    try {
      await axiosInstance.put(`/users/${userId}/status`, {
        is_active: !currentStatus
      });
      toast.success(`User ${currentStatus ? 'deactivated' : 'activated'} successfully`);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update user status");
    }
  };

  const handleBulkDelete = async () => {
    try {
      await axiosInstance.post('/users/bulk-delete', {
        user_ids: selectedUsers
      });
      toast.success(`${selectedUsers.length} user(s) deleted successfully`);
      setSelectedUsers([]);
      setBulkDeleteDialogOpen(false);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete users");
    }
  };

  const handleResetPassword = async () => {
    if (!resetPasswordUser || !newPassword) return;
    
    try {
      await axiosInstance.put(`/users/${resetPasswordUser.id}/reset-password`, {
        new_password: newPassword
      });
      toast.success(`Password reset for ${resetPasswordUser.full_name}`);
      setResetPasswordDialogOpen(false);
      setResetPasswordUser(null);
      setNewPassword("");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to reset password");
    }
  };

  const handleExportParticipants = async () => {
    try {
      const response = await axiosInstance.get('/users/export/participants', {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `participants_export_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Participant data exported');
    } catch (error) {
      toast.error('Failed to export data');
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>All Users</CardTitle>
              <CardDescription>View all system users grouped by company. Select users to bulk delete.</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button 
                variant="outline"
                onClick={handleExportParticipants}
                className="flex items-center gap-2"
                data-testid="export-participants-btn"
              >
                <Download className="w-4 h-4" />
                Export Participants
              </Button>
              {selectedUsers.length > 0 && (
                <Button 
                  variant="destructive" 
                  onClick={() => setBulkDeleteDialogOpen(true)}
                  className="flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Selected ({selectedUsers.length})
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {users.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No users yet</p>
          ) : (
            <div className="space-y-6">
              {/* Admin, Trainers, Coordinators (No Company) */}
              {users.filter(u => !u.company_id).length > 0 && (
                <Collapsible 
                  open={expandedGroups['system-users'] !== false} 
                  onOpenChange={() => toggleGroup('system-users')}
                  className="border rounded-lg overflow-hidden"
                >
                  <CollapsibleTrigger className="w-full">
                    <div className="flex items-center justify-between p-4 bg-gray-100 hover:bg-gray-200 transition-colors cursor-pointer">
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-gray-300"
                          checked={users.filter(u => !u.company_id).every(u => selectedUsers.includes(u.id))}
                          onChange={(e) => {
                            e.stopPropagation();
                            toggleAllUsers(users.filter(u => !u.company_id));
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <Users className="w-5 h-5 text-gray-600" />
                        <h3 className="text-lg font-semibold text-gray-700">System Users (No Company)</h3>
                        <span className="text-sm text-gray-500 bg-white px-2 py-0.5 rounded-full">
                          {users.filter(u => !u.company_id).length} users
                        </span>
                      </div>
                      {expandedGroups['system-users'] !== false ? (
                        <ChevronDown className="w-5 h-5 text-gray-500" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-gray-500" />
                      )}
                    </div>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="p-3 space-y-2 bg-white">
                      {users.filter(u => !u.company_id).map((u) => (
                        <div
                          key={u.id}
                          data-testid={`user-item-${u.id}`}
                          className={`p-4 rounded-lg flex justify-between items-center hover:bg-gray-100 transition-colors ${
                            selectedUsers.includes(u.id) ? 'bg-red-50 border-2 border-red-200' : 'bg-gray-50'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <input
                              type="checkbox"
                              className="h-4 w-4 rounded border-gray-300"
                              checked={selectedUsers.includes(u.id)}
                              onChange={() => toggleUserSelection(u.id)}
                            />
                            <div>
                              <h3 className="font-semibold text-gray-900">{u.full_name}</h3>
                              <p className="text-sm text-gray-600">{u.email}</p>
                              <div className="flex gap-2 mt-1 flex-wrap">
                                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded capitalize">
                                  {u.role.replace('_', ' ')}
                                </span>
                                <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                                  ID: {u.id_number}
                                </span>
                                <span className={`text-xs px-2 py-1 rounded ${u.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                  {u.is_active ? 'Active' : 'Inactive'}
                                </span>
                              </div>
                            </div>
                          </div>
                          <div className="flex gap-2 flex-wrap justify-end">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setResetPasswordUser(u);
                                setResetPasswordDialogOpen(true);
                              }}
                              data-testid={`reset-password-${u.id}`}
                            >
                              <UserCog className="w-4 h-4 mr-1" />
                              Reset Password
                            </Button>
                            <Button
                              size="sm"
                              variant={u.is_active ? "outline" : "default"}
                              onClick={() => handleToggleUserStatus(u.id, u.is_active)}
                              data-testid={`toggle-status-${u.id}`}
                            >
                              {u.is_active ? 'Deactivate' : 'Activate'}
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => onDeleteClick("user", u)}
                              data-testid={`delete-user-${u.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )}

              {/* Users Grouped by Company */}
              {companies.map((company) => {
                const companyUsers = users.filter(u => u.company_id === company.id);
                if (companyUsers.length === 0) return null;
                const groupId = `company-${company.id}`;
                
                return (
                  <Collapsible 
                    key={company.id}
                    open={expandedGroups[groupId] === true}
                    onOpenChange={() => toggleGroup(groupId)}
                    className="border rounded-lg overflow-hidden"
                  >
                    <CollapsibleTrigger className="w-full">
                      <div className="flex items-center justify-between p-4 bg-blue-50 hover:bg-blue-100 transition-colors cursor-pointer">
                        <div className="flex items-center gap-3">
                          <input
                            type="checkbox"
                            className="h-4 w-4 rounded border-gray-300"
                            checked={companyUsers.every(u => selectedUsers.includes(u.id))}
                            onChange={(e) => {
                              e.stopPropagation();
                              toggleAllUsers(companyUsers);
                            }}
                            onClick={(e) => e.stopPropagation()}
                          />
                          <Users className="w-5 h-5 text-blue-600" />
                          <h3 className="text-lg font-semibold text-gray-700">{company.name}</h3>
                          <span className="text-sm text-blue-600 bg-white px-2 py-0.5 rounded-full">
                            {companyUsers.length} users
                          </span>
                        </div>
                        {expandedGroups[groupId] ? (
                          <ChevronDown className="w-5 h-5 text-blue-500" />
                        ) : (
                          <ChevronRight className="w-5 h-5 text-blue-500" />
                        )}
                      </div>
                    </CollapsibleTrigger>
                    <CollapsibleContent>
                      <div className="p-3 space-y-2 bg-white">
                        {companyUsers.map((u) => (
                          <div
                            key={u.id}
                            data-testid={`user-item-${u.id}`}
                            className={`p-4 rounded-lg flex justify-between items-center hover:shadow-md transition-shadow ${
                              selectedUsers.includes(u.id) ? 'bg-red-50 border-2 border-red-200' : 'bg-gradient-to-r from-blue-50 to-indigo-50'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <input
                                type="checkbox"
                                className="h-4 w-4 rounded border-gray-300"
                                checked={selectedUsers.includes(u.id)}
                                onChange={() => toggleUserSelection(u.id)}
                              />
                              <div>
                                <h3 className="font-semibold text-gray-900">{u.full_name}</h3>
                                <p className="text-sm text-gray-600">{u.email}</p>
                                <div className="flex gap-2 mt-1 flex-wrap">
                                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded capitalize">
                                    {u.role.replace('_', ' ')}
                                  </span>
                                  <span className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                                    ID: {u.id_number}
                                  </span>
                                  <span className={`text-xs px-2 py-1 rounded ${u.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                    {u.is_active ? 'Active' : 'Inactive'}
                                  </span>
                                </div>
                              </div>
                            </div>
                            <div className="flex gap-2 flex-wrap justify-end">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setResetPasswordUser(u);
                                  setResetPasswordDialogOpen(true);
                                }}
                                data-testid={`reset-password-${u.id}`}
                              >
                                <UserCog className="w-4 h-4 mr-1" />
                                Reset Password
                              </Button>
                              <Button
                                size="sm"
                                variant={u.is_active ? "outline" : "default"}
                                onClick={() => handleToggleUserStatus(u.id, u.is_active)}
                                data-testid={`toggle-status-${u.id}`}
                              >
                                {u.is_active ? 'Deactivate' : 'Activate'}
                              </Button>
                              <Button
                                size="sm"
                                variant="destructive"
                                onClick={() => onDeleteClick("user", u)}
                                data-testid={`delete-user-${u.id}`}
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Bulk Delete Dialog */}
      <Dialog open={bulkDeleteDialogOpen} onOpenChange={setBulkDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Selected Users</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {selectedUsers.length} selected user(s)? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleBulkDelete}>
              Delete {selectedUsers.length} Users
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={resetPasswordDialogOpen} onOpenChange={setResetPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              Set a new password for {resetPasswordUser?.full_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="new-password">New Password</Label>
              <Input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setResetPasswordDialogOpen(false);
              setResetPasswordUser(null);
              setNewPassword("");
            }}>
              Cancel
            </Button>
            <Button onClick={handleResetPassword} disabled={!newPassword}>
              Reset Password
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export { UsersTab };
