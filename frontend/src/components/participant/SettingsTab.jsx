/**
 * SettingsTab Component - Extracted from ParticipantDashboard
 * Displays password change form
 */
import { axiosInstance } from "../../App";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { toast } from "sonner";
import { Lock } from "lucide-react";

const SettingsTab = () => {
  const handleChangePassword = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const currentPassword = formData.get('current_password');
    const newPassword = formData.get('new_password');
    const confirmPassword = formData.get('confirm_password');

    if (newPassword !== confirmPassword) {
      toast.error("New passwords don't match");
      return;
    }

    if (newPassword.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }

    try {
      await axiosInstance.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      toast.success("Password changed successfully!");
      e.target.reset();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to change password");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <Lock className="w-5 h-5 mr-2" />
          Change Password
        </CardTitle>
        <CardDescription>Update your account password</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
          <div>
            <Label htmlFor="current_password">Current Password</Label>
            <Input
              id="current_password"
              name="current_password"
              type="password"
              placeholder="Enter current password"
              required
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="new_password">New Password</Label>
            <Input
              id="new_password"
              name="new_password"
              type="password"
              placeholder="Enter new password (min 6 characters)"
              required
              minLength={6}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="confirm_password">Confirm New Password</Label>
            <Input
              id="confirm_password"
              name="confirm_password"
              type="password"
              placeholder="Confirm new password"
              required
              minLength={6}
              className="mt-1"
            />
          </div>
          <Button type="submit" className="w-full">
            <Lock className="w-4 h-4 mr-2" />
            Change Password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};

export { SettingsTab };
