/**
 * SessionManagementTab - Admin Data Management for Sessions
 * Features: Mark Complete, Revert Complete, Export Template, Import Data
 */
import { useState } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { CheckCircle, Undo2, Download, Upload, Search, FileSpreadsheet } from "lucide-react";

const SessionManagementTab = ({ sessions, loading, onRefresh }) => {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [completeDialog, setCompleteDialog] = useState({ open: false, session: null });
  const [revertDialog, setRevertDialog] = useState({ open: false, session: null });
  const [completeReason, setCompleteReason] = useState("");
  const [revertReason, setRevertReason] = useState("");
  const [importDialog, setImportDialog] = useState({ open: false, session: null });
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);

  const filtered = sessions.filter(s => {
    const matchSearch = !search || 
      (s.company_name || "").toLowerCase().includes(search.toLowerCase()) ||
      (s.program_name || "").toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || 
      (statusFilter === "completed" && s.completion_status === "completed") ||
      (statusFilter === "ongoing" && s.completion_status !== "completed");
    return matchSearch && matchStatus;
  });

  const handleMarkComplete = async () => {
    try {
      await axiosInstance.post(`/sessions/${completeDialog.session.id}/admin-complete`, { reason: completeReason });
      toast.success("Session marked as completed");
      setCompleteDialog({ open: false, session: null });
      setCompleteReason("");
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to mark complete");
    }
  };

  const handleRevertComplete = async () => {
    try {
      await axiosInstance.post(`/sessions/${revertDialog.session.id}/admin-revert-complete`, { reason: revertReason });
      toast.success("Session reverted to ongoing");
      setRevertDialog({ open: false, session: null });
      setRevertReason("");
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to revert");
    }
  };

  const handleExport = async (session) => {
    try {
      const response = await axiosInstance.get(`/sessions/${session.id}/export-template`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const company = (session.company_name || "session").replace(/\s+/g, "_").substring(0, 30);
      link.download = `MDDRC_Template_${company}_${session.start_date}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Template downloaded");
    } catch (err) {
      toast.error("Failed to download template");
    }
  };

  const handleImport = async () => {
    if (!importFile) return;
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append('file', importFile);
      const res = await axiosInstance.post(`/sessions/${importDialog.session.id}/import-data`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const data = res.data;
      const parts = [`${data.test_scores_imported} test scores`, `${data.attendance_imported} attendance records`];
      if (data.vehicle_checklists_imported > 0) parts.push(`${data.vehicle_checklists_imported} vehicle checklists`);
      toast.success(`Imported: ${parts.join(', ')}`);
      if (data.errors?.length > 0) {
        toast.warning(`${data.errors.length} errors during import`);
      }
      setImportDialog({ open: false, session: null });
      setImportFile(null);
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Import failed");
    } finally {
      setImporting(false);
    }
  };

  const getCompletionBadge = (session) => {
    if (session.completion_status === "completed") {
      return <Badge className="bg-green-600 text-white">Completed</Badge>;
    }
    return <Badge variant="outline" className="text-amber-600 border-amber-400">Ongoing</Badge>;
  };

  return (
    <>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input 
              placeholder="Search by company or programme..." 
              value={search} 
              onChange={e => setSearch(e.target.value)}
              className="pl-10"
              data-testid="session-mgmt-search"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[160px]" data-testid="session-mgmt-status-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sessions</SelectItem>
              <SelectItem value="ongoing">Ongoing</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading sessions...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No sessions found</div>
        ) : (
          <div className="overflow-x-auto border rounded-lg">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Date</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Company</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Programme</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-500">Pax</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-500">Status</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-500">Completion</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filtered.map(session => (
                  <tr key={session.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">
                      {session.start_date}{session.end_date && session.end_date !== session.start_date ? ` → ${session.end_date}` : ''}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium">{session.company_name || '-'}</td>
                    <td className="px-4 py-3 text-sm">{session.program_name || '-'}</td>
                    <td className="px-4 py-3 text-sm text-center">{session.participant_ids?.length || 0}</td>
                    <td className="px-4 py-3 text-center">
                      <Badge variant={session.status === 'active' ? 'default' : 'secondary'}>{session.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-center">{getCompletionBadge(session)}</td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        {session.completion_status !== "completed" ? (
                          <Button size="sm" variant="ghost" title="Mark as Complete"
                            data-testid={`complete-session-${session.id}`}
                            onClick={() => { setCompleteReason(""); setCompleteDialog({ open: true, session }); }}>
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          </Button>
                        ) : (
                          <Button size="sm" variant="ghost" title="Revert to Ongoing"
                            data-testid={`revert-session-${session.id}`}
                            onClick={() => { setRevertReason(""); setRevertDialog({ open: true, session }); }}>
                            <Undo2 className="h-4 w-4 text-amber-600" />
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" title="Download Excel Template"
                          data-testid={`export-session-${session.id}`}
                          onClick={() => handleExport(session)}>
                          <Download className="h-4 w-4 text-blue-600" />
                        </Button>
                        <Button size="sm" variant="ghost" title="Import Excel Data"
                          data-testid={`import-session-${session.id}`}
                          onClick={() => { setImportFile(null); setImportDialog({ open: true, session }); }}>
                          <Upload className="h-4 w-4 text-purple-600" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Mark Complete Dialog */}
      <Dialog open={completeDialog.open} onOpenChange={open => setCompleteDialog({ ...completeDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-600">
              <CheckCircle className="w-5 h-5" />
              Mark Session as Completed
            </DialogTitle>
            <DialogDescription>
              <strong>{completeDialog.session?.company_name}</strong> — {completeDialog.session?.program_name}
              <br />
              Date: {completeDialog.session?.start_date}
              {completeDialog.session?.end_date && completeDialog.session?.end_date !== completeDialog.session?.start_date && ` to ${completeDialog.session?.end_date}`}
              <br />
              Participants: {completeDialog.session?.participant_ids?.length || 0}
              <br /><br />
              Marking as complete will: recognize revenue in P&L, archive the session, and make it available in past training.
            </DialogDescription>
          </DialogHeader>
          <div>
            <Label>Reason for Admin Completion *</Label>
            <Textarea placeholder="e.g., Coordinator unable to access portal, session data verified offline"
              value={completeReason} onChange={e => setCompleteReason(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCompleteDialog({ open: false, session: null })}>Cancel</Button>
            <Button onClick={handleMarkComplete} disabled={!completeReason} className="bg-green-600 hover:bg-green-700">
              Mark as Completed
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revert Complete Dialog */}
      <Dialog open={revertDialog.open} onOpenChange={open => setRevertDialog({ ...revertDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <Undo2 className="w-5 h-5" />
              Revert Session to Ongoing
            </DialogTitle>
            <DialogDescription>
              Revert <strong>{revertDialog.session?.company_name}</strong> back to ongoing. This will remove it from P&L revenue.
            </DialogDescription>
          </DialogHeader>
          <div>
            <Label>Reason *</Label>
            <Textarea placeholder="e.g., Need to add more participants, incorrect data"
              value={revertReason} onChange={e => setRevertReason(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRevertDialog({ open: false, session: null })}>Cancel</Button>
            <Button onClick={handleRevertComplete} disabled={!revertReason} className="bg-amber-600 hover:bg-amber-700">
              Revert to Ongoing
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Data Dialog */}
      <Dialog open={importDialog.open} onOpenChange={open => setImportDialog({ ...importDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-purple-600">
              <FileSpreadsheet className="w-5 h-5" />
              Import Session Data
            </DialogTitle>
            <DialogDescription>
              Upload filled Excel template for <strong>{importDialog.session?.company_name}</strong>
              <br />
              This will import test scores (raw marks), attendance, and vehicle checklists.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
              <strong>Steps:</strong>
              <ol className="list-decimal ml-4 mt-1 space-y-1">
                <li>First download the template using the <Download className="inline h-3 w-3" /> button</li>
                <li>Fill in test scores (raw marks), attendance, and vehicle checklists in the Excel file</li>
                <li>Upload the completed file here</li>
              </ol>
            </div>
            <div>
              <Label>Select Excel File (.xlsx)</Label>
              <Input type="file" accept=".xlsx,.xls"
                data-testid="import-file-input"
                onChange={e => setImportFile(e.target.files?.[0] || null)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setImportDialog({ open: false, session: null })}>Cancel</Button>
            <Button onClick={handleImport} disabled={!importFile || importing} className="bg-purple-600 hover:bg-purple-700">
              {importing ? "Importing..." : "Import Data"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export { SessionManagementTab };
