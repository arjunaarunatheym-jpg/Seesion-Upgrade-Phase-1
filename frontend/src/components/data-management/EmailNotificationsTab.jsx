import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import { Textarea } from "../../components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { toast } from "sonner";
import { axiosInstance } from "../../App";
import { Mail, Bell, Send, Settings, Users, Paperclip, Clock, CheckCircle, AlertCircle, Plus, X, Upload } from "lucide-react";

const EmailNotificationsTab = ({ user }) => {
  const [activeTab, setActiveTab] = useState("settings");
  const [events, setEvents] = useState([]);
  const [settings, setSettings] = useState([]);
  const [recipients, setRecipients] = useState([]);
  const [broadcastHistory, setBroadcastHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sessions, setSessions] = useState([]);

  // Broadcast state
  const [broadcastForm, setBroadcastForm] = useState({
    subject: "",
    message: "",
    recipient_group: "",
    session_id: "",
    custom_emails: "",
  });
  const [attachment, setAttachment] = useState(null);
  const [sending, setSending] = useState(false);

  // Custom email input
  const [customEmailInputs, setCustomEmailInputs] = useState({});

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [eventsRes, settingsRes, recipientsRes, historyRes, sessionsRes] = await Promise.all([
        axiosInstance.get("/notifications/events"),
        axiosInstance.get("/notifications/settings"),
        axiosInstance.get("/notifications/recipients"),
        axiosInstance.get("/notifications/broadcast-history"),
        axiosInstance.get("/sessions"),
      ]);
      setEvents(eventsRes.data);
      setSettings(settingsRes.data);
      setRecipients(recipientsRes.data);
      setBroadcastHistory(historyRes.data);
      setSessions(sessionsRes.data?.slice(0, 50) || []);
    } catch (err) {
      toast.error("Failed to load notification settings");
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const getSetting = (eventId) => {
    return settings.find(s => s.event_id === eventId) || {
      event_id: eventId,
      enabled: true,
      recipient_roles: [],
      recipient_user_ids: [],
      custom_emails: [],
    };
  };

  const updateSetting = (eventId, field, value) => {
    setSettings(prev => {
      const existing = prev.find(s => s.event_id === eventId);
      if (existing) {
        return prev.map(s => s.event_id === eventId ? { ...s, [field]: value } : s);
      }
      return [...prev, { event_id: eventId, enabled: true, recipient_roles: [], recipient_user_ids: [], custom_emails: [], [field]: value }];
    });
  };

  const toggleRole = (eventId, role) => {
    const setting = getSetting(eventId);
    const roles = setting.recipient_roles || [];
    const newRoles = roles.includes(role) ? roles.filter(r => r !== role) : [...roles, role];
    updateSetting(eventId, "recipient_roles", newRoles);
  };

  const toggleUser = (eventId, userId) => {
    const setting = getSetting(eventId);
    const users = setting.recipient_user_ids || [];
    const newUsers = users.includes(userId) ? users.filter(u => u !== userId) : [...users, userId];
    updateSetting(eventId, "recipient_user_ids", newUsers);
  };

  const addCustomEmail = (eventId) => {
    const email = (customEmailInputs[eventId] || "").trim();
    if (!email || !email.includes("@")) return;
    const setting = getSetting(eventId);
    const emails = setting.custom_emails || [];
    if (!emails.includes(email)) {
      updateSetting(eventId, "custom_emails", [...emails, email]);
    }
    setCustomEmailInputs(prev => ({ ...prev, [eventId]: "" }));
  };

  const removeCustomEmail = (eventId, email) => {
    const setting = getSetting(eventId);
    updateSetting(eventId, "custom_emails", (setting.custom_emails || []).filter(e => e !== email));
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      await axiosInstance.put("/notifications/settings", settings);
      toast.success("Notification settings saved");
    } catch {
      toast.error("Failed to save settings");
    }
    setSaving(false);
  };

  const sendTestEmail = async () => {
    try {
      const res = await axiosInstance.post("/notifications/test", { email: user.email });
      toast.success(res.data.message);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send test email");
    }
  };

  const sendBroadcast = async () => {
    if (!broadcastForm.subject || !broadcastForm.message || !broadcastForm.recipient_group) {
      toast.error("Please fill in subject, message, and select recipients");
      return;
    }
    setSending(true);
    try {
      const formData = new FormData();
      formData.append("subject", broadcastForm.subject);
      formData.append("message", broadcastForm.message);
      formData.append("recipient_group", broadcastForm.recipient_group);
      if (broadcastForm.session_id) formData.append("session_id", broadcastForm.session_id);
      if (broadcastForm.custom_emails) formData.append("custom_emails", broadcastForm.custom_emails);
      if (attachment) formData.append("attachment", attachment);

      const res = await axiosInstance.post("/notifications/broadcast", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(res.data.message);
      setBroadcastForm({ subject: "", message: "", recipient_group: "", session_id: "", custom_emails: "" });
      setAttachment(null);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send broadcast");
    }
    setSending(false);
  };

  const ROLE_LABELS = {
    admin: "Admin", super_admin: "Super Admin", assistant_admin: "Asst Admin",
    finance: "Finance", coordinator: "Coordinator", marketing: "Marketing", trainer: "Trainer",
  };

  const categories = [...new Set(events.map(e => e.category))];

  if (loading) return <div className="flex justify-center py-12"><div className="animate-spin w-8 h-8 border-4 border-red-600 border-t-transparent rounded-full" /></div>;

  return (
    <div className="space-y-4" data-testid="email-notifications-tab">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="settings" data-testid="notif-settings-tab"><Settings className="w-4 h-4 mr-1.5" />Notification Rules</TabsTrigger>
          <TabsTrigger value="broadcast" data-testid="notif-broadcast-tab"><Send className="w-4 h-4 mr-1.5" />Broadcast / Greetings</TabsTrigger>
          <TabsTrigger value="history" data-testid="notif-history-tab"><Clock className="w-4 h-4 mr-1.5" />History</TabsTrigger>
        </TabsList>

        {/* NOTIFICATION RULES TAB */}
        <TabsContent value="settings">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-500">Configure who receives email notifications for each event.</p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={sendTestEmail} data-testid="send-test-email">
                <Mail className="w-4 h-4 mr-1.5" />Send Test Email
              </Button>
              <Button size="sm" onClick={saveSettings} disabled={saving} data-testid="save-notif-settings">
                {saving ? "Saving..." : "Save Settings"}
              </Button>
            </div>
          </div>

          {categories.map(cat => (
            <div key={cat} className="mb-6">
              <h3 className="font-semibold text-sm text-gray-700 mb-3 uppercase tracking-wide">{cat}</h3>
              <div className="space-y-3">
                {events.filter(e => e.category === cat).map(event => {
                  const setting = getSetting(event.id);
                  return (
                    <Card key={event.id} className={`border ${setting.enabled ? "border-gray-200" : "border-gray-100 opacity-60"}`} data-testid={`event-${event.id}`}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <div className="flex items-center gap-2">
                              <Bell className="w-4 h-4 text-gray-500" />
                              <span className="font-medium text-sm">{event.label}</span>
                              {event.note && <Badge variant="outline" className="text-[10px]">{event.note}</Badge>}
                            </div>
                            <p className="text-xs text-gray-500 mt-0.5 ml-6">{event.description}</p>
                          </div>
                          <Switch
                            checked={setting.enabled !== false}
                            onCheckedChange={(v) => updateSetting(event.id, "enabled", v)}
                            data-testid={`toggle-${event.id}`}
                          />
                        </div>

                        {setting.enabled !== false && (
                          <div className="ml-6 space-y-3">
                            {/* Role-based recipients */}
                            <div>
                              <Label className="text-xs text-gray-600 mb-1 block">Notify by Role:</Label>
                              <div className="flex flex-wrap gap-1.5">
                                {Object.entries(ROLE_LABELS).map(([role, label]) => (
                                  <Badge
                                    key={role}
                                    variant={(setting.recipient_roles || []).includes(role) ? "default" : "outline"}
                                    className="cursor-pointer text-xs"
                                    onClick={() => toggleRole(event.id, role)}
                                  >
                                    {label}
                                  </Badge>
                                ))}
                              </div>
                            </div>

                            {/* Specific staff */}
                            <div>
                              <Label className="text-xs text-gray-600 mb-1 block">Specific Staff:</Label>
                              <div className="flex flex-wrap gap-1.5">
                                {recipients.map(r => (
                                  <Badge
                                    key={r.id}
                                    variant={(setting.recipient_user_ids || []).includes(r.id) ? "default" : "outline"}
                                    className="cursor-pointer text-xs"
                                    onClick={() => toggleUser(event.id, r.id)}
                                  >
                                    {r.full_name} ({r.role})
                                  </Badge>
                                ))}
                              </div>
                            </div>

                            {/* Custom emails */}
                            <div>
                              <Label className="text-xs text-gray-600 mb-1 block">Custom Emails:</Label>
                              <div className="flex flex-wrap gap-1.5 mb-1.5">
                                {(setting.custom_emails || []).map(email => (
                                  <Badge key={email} variant="secondary" className="text-xs">
                                    {email}
                                    <X className="w-3 h-3 ml-1 cursor-pointer" onClick={() => removeCustomEmail(event.id, email)} />
                                  </Badge>
                                ))}
                              </div>
                              <div className="flex gap-1.5">
                                <Input
                                  placeholder="finance@mddrc.com.my"
                                  className="h-7 text-xs max-w-[250px]"
                                  value={customEmailInputs[event.id] || ""}
                                  onChange={(e) => setCustomEmailInputs(prev => ({ ...prev, [event.id]: e.target.value }))}
                                  onKeyDown={(e) => e.key === "Enter" && addCustomEmail(event.id)}
                                />
                                <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => addCustomEmail(event.id)}>
                                  <Plus className="w-3 h-3" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          ))}
        </TabsContent>

        {/* BROADCAST / GREETINGS TAB */}
        <TabsContent value="broadcast">
          <Card data-testid="broadcast-composer">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Send className="w-5 h-5" />Compose Broadcast Email
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Recipients</Label>
                <Select value={broadcastForm.recipient_group} onValueChange={v => setBroadcastForm(f => ({ ...f, recipient_group: v }))}>
                  <SelectTrigger data-testid="broadcast-recipient-group"><SelectValue placeholder="Select recipient group" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all_staff">All Staff</SelectItem>
                    <SelectItem value="all_participants">All Participants (with email)</SelectItem>
                    <SelectItem value="session_participants">Session Participants</SelectItem>
                    <SelectItem value="custom">Custom Email List</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {broadcastForm.recipient_group === "session_participants" && (
                <div>
                  <Label>Select Session</Label>
                  <Select value={broadcastForm.session_id} onValueChange={v => setBroadcastForm(f => ({ ...f, session_id: v }))}>
                    <SelectTrigger><SelectValue placeholder="Choose session..." /></SelectTrigger>
                    <SelectContent>
                      {sessions.map(s => (
                        <SelectItem key={s.id} value={s.id}>
                          {s.company_name || "Unnamed"} — {s.start_date}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {broadcastForm.recipient_group === "custom" && (
                <div>
                  <Label>Email Addresses (comma-separated)</Label>
                  <Input
                    placeholder="email1@example.com, email2@example.com"
                    value={broadcastForm.custom_emails}
                    onChange={e => setBroadcastForm(f => ({ ...f, custom_emails: e.target.value }))}
                    data-testid="broadcast-custom-emails"
                  />
                </div>
              )}

              <div>
                <Label>Subject</Label>
                <Input
                  placeholder="Selamat Hari Raya Aidilfitri from MDDRC"
                  value={broadcastForm.subject}
                  onChange={e => setBroadcastForm(f => ({ ...f, subject: e.target.value }))}
                  data-testid="broadcast-subject"
                />
              </div>

              <div>
                <Label>Message</Label>
                <Textarea
                  placeholder="Write your message here... You can use multiple lines for formatting."
                  rows={8}
                  value={broadcastForm.message}
                  onChange={e => setBroadcastForm(f => ({ ...f, message: e.target.value }))}
                  data-testid="broadcast-message"
                />
              </div>

              <div>
                <Label className="flex items-center gap-1.5 mb-2"><Paperclip className="w-4 h-4" />Attachment (optional — e.g., festive card, safety poster)</Label>
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 px-4 py-2 border rounded-md cursor-pointer hover:bg-gray-50 text-sm">
                    <Upload className="w-4 h-4" />
                    {attachment ? attachment.name : "Choose file"}
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.png,.jpg,.jpeg,.gif,.doc,.docx"
                      onChange={e => setAttachment(e.target.files[0])}
                      data-testid="broadcast-attachment"
                    />
                  </label>
                  {attachment && (
                    <Button size="sm" variant="ghost" onClick={() => setAttachment(null)}>
                      <X className="w-4 h-4" />Remove
                    </Button>
                  )}
                </div>
                {attachment && <p className="text-xs text-gray-500 mt-1">{(attachment.size / 1024).toFixed(0)} KB</p>}
              </div>

              <div className="flex justify-end pt-2">
                <Button onClick={sendBroadcast} disabled={sending} data-testid="send-broadcast-btn">
                  {sending ? "Sending..." : <><Send className="w-4 h-4 mr-1.5" />Send Broadcast</>}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* HISTORY TAB */}
        <TabsContent value="history">
          <div className="space-y-3" data-testid="broadcast-history">
            {broadcastHistory.length === 0 && (
              <p className="text-center text-gray-400 py-8 text-sm">No broadcasts sent yet</p>
            )}
            {broadcastHistory.map(h => (
              <Card key={h.id} className="border-gray-200">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-medium text-sm">{h.subject}</h4>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{h.message}</p>
                      <div className="flex items-center gap-3 mt-2">
                        <Badge variant="outline" className="text-xs">
                          <Users className="w-3 h-3 mr-1" />{h.recipient_count} recipients
                        </Badge>
                        <Badge variant="outline" className="text-xs capitalize">
                          {(h.recipient_group || "").replace("_", " ")}
                        </Badge>
                        {h.has_attachment && (
                          <Badge variant="secondary" className="text-xs">
                            <Paperclip className="w-3 h-3 mr-1" />{h.attachment_name}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="flex items-center gap-1 text-xs text-green-600">
                        <CheckCircle className="w-3 h-3" />Sent
                      </div>
                      <p className="text-[10px] text-gray-400 mt-0.5">{new Date(h.sent_at).toLocaleString()}</p>
                      <p className="text-[10px] text-gray-400">by {h.sent_by_name}</p>
                    </div>
                  </div>
                  {h.errors?.length > 0 && (
                    <div className="mt-2 p-2 bg-red-50 rounded text-xs text-red-600">
                      <AlertCircle className="w-3 h-3 inline mr-1" />
                      {h.errors.join(", ")}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export { EmailNotificationsTab };
