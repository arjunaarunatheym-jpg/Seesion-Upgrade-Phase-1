/**
 * LeadPipelineTab - Lead management with pipeline stages
 */
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Badge } from "../ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";
import { 
  Plus, Search, Phone, Mail, Building, Calendar, DollarSign, 
  ChevronRight, Edit, Trash2, UserPlus, AlertCircle, Clock, FileText,
  Eye, Download, Percent, CheckCircle, XCircle, Send, Archive, RotateCcw
} from "lucide-react";
import { toast } from "sonner";
import { axiosInstance } from "../../App";

const STAGES = [
  { id: "inquiry", label: "Inquiry", color: "bg-gray-100 text-gray-800", borderColor: "border-gray-300" },
  { id: "contacted", label: "Contacted", color: "bg-blue-100 text-blue-800", borderColor: "border-blue-300" },
  { id: "quotation_sent", label: "Quotation Sent", color: "bg-purple-100 text-purple-800", borderColor: "border-purple-300" },
  { id: "negotiating", label: "Negotiating", color: "bg-yellow-100 text-yellow-800", borderColor: "border-yellow-300" },
  { id: "won", label: "Won", color: "bg-green-100 text-green-800", borderColor: "border-green-300" },
  { id: "lost", label: "Lost", color: "bg-red-100 text-red-800", borderColor: "border-red-300" },
];

const SOURCES = [
  { id: "referral", label: "Referral" },
  { id: "website", label: "Website" },
  { id: "cold_call", label: "Cold Call" },
  { id: "event", label: "Event/Exhibition" },
  { id: "social_media", label: "Social Media" },
  { id: "other", label: "Other" },
];

const LeadPipelineTab = ({
  leads,
  onRefresh,
  formatCurrency,
  isAdmin = false,
  onCreateQuotation, // Callback to open quotation form with pre-filled data
  quotations = [], // Pass quotations to show inline
  onViewQuotation, // View quotation details
  onApplyDiscount, // Apply discount dialog
  onDownloadPdf, // Download PDF
  onClientResponse, // Accept/Decline quotation
  onMarkSent, // Mark as sent
  getStatusBadge, // Status badge component
}) => {
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [showDialog, setShowDialog] = useState(false);
  const [showArchivedDialog, setShowArchivedDialog] = useState(false);
  const [archivedLeads, setArchivedLeads] = useState([]);
  const [editingLead, setEditingLead] = useState(null);
  const [viewMode, setViewMode] = useState("pipeline"); // pipeline or list
  const [form, setForm] = useState({
    company_name: "",
    company_address: "",
    contact_person: "",
    contact_email: "",
    contact_phone: "",
    source: "",
    notes: "",
    expected_value: 0,
    follow_up_date: "",
  });
  
  // Won Dialog State
  const [wonDialogOpen, setWonDialogOpen] = useState(false);
  const [wonLead, setWonLead] = useState(null);
  const [wonForm, setWonForm] = useState({
    training_date: "",
    end_date: "",
    num_participants: "",
    venue: "",
    grant_id: "",
  });

  const resetForm = () => {
    setForm({
      company_name: "",
      company_address: "",
      contact_person: "",
      contact_email: "",
      contact_phone: "",
      source: "",
      notes: "",
      expected_value: 0,
      follow_up_date: "",
    });
    setEditingLead(null);
  };

  const handleOpenDialog = (lead = null) => {
    if (lead) {
      setEditingLead(lead);
      setForm({
        company_name: lead.company_name || "",
        company_address: lead.company_address || "",
        contact_person: lead.contact_person || "",
        contact_email: lead.contact_email || "",
        contact_phone: lead.contact_phone || "",
        source: lead.source || "",
        notes: lead.notes || "",
        expected_value: lead.expected_value || 0,
        follow_up_date: lead.follow_up_date || "",
      });
    } else {
      resetForm();
    }
    setShowDialog(true);
  };

  const handleSave = async () => {
    if (!form.company_name.trim()) {
      toast.error("Company name is required");
      return;
    }

    try {
      if (editingLead) {
        await axiosInstance.put(`/marketing/leads/${editingLead.id}`, form);
        toast.success("Lead updated");
      } else {
        await axiosInstance.post("/marketing/leads", form);
        toast.success("Lead created");
      }
      setShowDialog(false);
      resetForm();
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save lead");
    }
  };

  const handleDelete = async (leadId) => {
    if (!confirm("Archive this lead? (It will be hidden from your view but Admin can restore it)")) return;
    try {
      await axiosInstance.delete(`/marketing/leads/${leadId}`);
      toast.success("Lead archived");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to archive lead");
    }
  };

  const loadArchivedLeads = async () => {
    try {
      const response = await axiosInstance.get('/marketing/leads/archived');
      setArchivedLeads(response.data || []);
      setShowArchivedDialog(true);
    } catch (error) {
      toast.error("Failed to load archived leads");
    }
  };

  const handleRestoreLead = async (leadId) => {
    try {
      await axiosInstance.post(`/marketing/leads/${leadId}/unarchive`);
      toast.success("Lead restored");
      setArchivedLeads(prev => prev.filter(l => l.id !== leadId));
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to restore lead");
    }
  };

  const handleStageChange = async (leadId, newStage) => {
    // If changing to "won", open the won dialog instead
    if (newStage === "won") {
      const lead = leads.find(l => l.id === leadId);
      setWonLead(lead);
      setWonForm({
        training_date: "",
        end_date: "",
        num_participants: "",
        venue: lead?.company_address || "",
        grant_id: "",
      });
      setWonDialogOpen(true);
      return;
    }
    
    try {
      await axiosInstance.put(`/marketing/leads/${leadId}/stage?stage=${newStage}`);
      toast.success(`Lead moved to ${newStage}`);
      onRefresh();
    } catch (error) {
      toast.error("Failed to update stage");
    }
  };

  const handleMarkWon = async () => {
    if (!wonLead) return;
    
    if (!wonForm.training_date) {
      toast.error("Training start date is required");
      return;
    }
    
    try {
      await axiosInstance.post(`/marketing/leads/${wonLead.id}/mark-won`, {
        training_date: wonForm.training_date,
        end_date: wonForm.end_date || wonForm.training_date,
        num_participants: parseInt(wonForm.num_participants) || 0,
        venue: wonForm.venue,
        grant_id: wonForm.grant_id,
      });
      toast.success("Lead marked as Won! Draft session created.");
      setWonDialogOpen(false);
      setWonLead(null);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to mark as won");
    }
  };

  const handleConvertToClient = async (leadId) => {
    try {
      await axiosInstance.post(`/marketing/leads/${leadId}/convert-to-client`);
      toast.success("Lead converted to client!");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to convert lead");
    }
  };

  const handleCreateQuotation = async (lead) => {
    try {
      // Call backend to auto-create client and get client data
      const response = await axiosInstance.post(`/marketing/leads/${lead.id}/create-quotation`);
      
      if (response.data.already_exists) {
        toast.info("Lead already has a quotation");
      }
      
      // Call the parent callback to open quotation form with client pre-filled
      if (onCreateQuotation) {
        onCreateQuotation({
          client_id: response.data.client_id,
          client: response.data.client,
          lead_id: lead.id
        });
      }
      
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to prepare quotation");
    }
  };

  const handleReviveLead = async (lead) => {
    const reason = prompt("Enter reason for reviving this lead (optional):");
    const followUpDate = prompt("Enter follow-up date (YYYY-MM-DD):");
    
    try {
      await axiosInstance.post(`/marketing/leads/${lead.id}/revive`, {
        reason: reason || "",
        follow_up_date: followUpDate || null
      });
      toast.success("Lead revived successfully!");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to revive lead");
    }
  };

  // Filter leads
  const filteredLeads = leads.filter((lead) => {
    const matchesSearch = 
      lead.company_name?.toLowerCase().includes(search.toLowerCase()) ||
      lead.contact_person?.toLowerCase().includes(search.toLowerCase()) ||
      lead.contact_email?.toLowerCase().includes(search.toLowerCase());
    const matchesStage = stageFilter === "all" || lead.stage === stageFilter;
    const matchesSource = sourceFilter === "all" || lead.source === sourceFilter;
    return matchesSearch && matchesStage && matchesSource;
  });

  // Group leads by stage for pipeline view
  const leadsByStage = STAGES.reduce((acc, stage) => {
    acc[stage.id] = filteredLeads.filter((l) => l.stage === stage.id);
    return acc;
  }, {});

  const isOverdue = (followUpDate) => {
    if (!followUpDate) return false;
    return new Date(followUpDate) < new Date(new Date().toDateString());
  };

  const LeadCard = ({ lead }) => (
    <div 
      className={`p-3 bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow ${
        isOverdue(lead.follow_up_date) ? "border-red-300 bg-red-50" : ""
      }`}
      data-testid={`lead-${lead.id}`}
    >
      <div className="flex justify-between items-start mb-2">
        <h4 className="font-medium text-sm text-gray-900 truncate flex-1">{lead.company_name}</h4>
        <div className="flex gap-1 ml-2">
          <button 
            onClick={() => handleOpenDialog(lead)}
            className="p-1 hover:bg-gray-100 rounded"
            title="Edit"
          >
            <Edit className="w-3 h-3 text-gray-500" />
          </button>
          <button 
            onClick={() => handleDelete(lead.id)}
            className="p-1 hover:bg-orange-100 rounded"
            title="Archive"
          >
            <Trash2 className="w-3 h-3 text-orange-500" />
          </button>
        </div>
      </div>
      
      {lead.contact_person && (
        <p className="text-xs text-gray-600 mb-1">{lead.contact_person}</p>
      )}
      
      {lead.expected_value > 0 && (
        <p className="text-xs font-medium text-green-600 mb-1">
          {formatCurrency(lead.expected_value)}
        </p>
      )}
      
      {lead.follow_up_date && (
        <div className={`flex items-center gap-1 text-xs ${isOverdue(lead.follow_up_date) ? "text-red-600" : "text-gray-500"}`}>
          {isOverdue(lead.follow_up_date) ? <AlertCircle className="w-3 h-3" /> : <Calendar className="w-3 h-3" />}
          {lead.follow_up_date}
        </div>
      )}
      
      {lead.source && (
        <Badge variant="outline" className="text-xs mt-2">{lead.source}</Badge>
      )}
      
      {isAdmin && lead.created_by_name && (
        <p className="text-xs text-gray-400 mt-1">By: {lead.created_by_name}</p>
      )}
      
      {/* Quick stage actions */}
      {lead.stage !== "won" && lead.stage !== "lost" && (
        <div className="flex gap-1 mt-2 pt-2 border-t">
          <Select 
            value={lead.stage} 
            onValueChange={(value) => handleStageChange(lead.id, value)}
          >
            <SelectTrigger className="h-7 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STAGES.map((s) => (
                <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          {/* Create Quotation Button - show for active leads without quotation */}
          {!lead.quotation_id && onCreateQuotation && (
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => handleCreateQuotation(lead)}
              className="h-7 text-xs bg-blue-50 hover:bg-blue-100 text-blue-700"
              title="Create Quotation"
            >
              <FileText className="w-3 h-3 mr-1" />
              Quote
            </Button>
          )}
          
          {lead.stage === "won" && !lead.client_id && (
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => handleConvertToClient(lead.id)}
              className="h-7 text-xs"
            >
              <UserPlus className="w-3 h-3 mr-1" />
              To Client
            </Button>
          )}
        </div>
      )}
      
      {/* Show quotation link if exists */}
      {lead.quotation_id && (
        <div className="mt-2 pt-2 border-t space-y-2">
          {(() => {
            const quotation = quotations.find(q => q.id === lead.quotation_id);
            if (!quotation) return (
              <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700">
                <FileText className="w-3 h-3 mr-1" />
                Quotation linked
              </Badge>
            );
            
            return (
              <div className="bg-gray-50 rounded p-2 text-xs">
                <div className="flex justify-between items-start mb-1">
                  <span className="font-medium text-purple-700">{quotation.quotation_number}</span>
                  {getStatusBadge && getStatusBadge(quotation.status)}
                </div>
                <p className="font-bold text-green-700">{formatCurrency(quotation.total_amount)}</p>
                {quotation.discount_amount > 0 && (
                  <p className="text-orange-600">Disc: {formatCurrency(quotation.discount_amount)}</p>
                )}
                
                {/* Quotation Actions */}
                <div className="flex flex-wrap gap-1 mt-2">
                  {onViewQuotation && (
                    <Button variant="ghost" size="sm" onClick={() => onViewQuotation(quotation.id)} className="h-6 px-2 text-xs">
                      <Eye className="w-3 h-3" />
                    </Button>
                  )}
                  
                  {quotation.status === 'approved' && onMarkSent && (
                    <Button variant="ghost" size="sm" onClick={() => onMarkSent(quotation.id)} className="h-6 px-2 text-xs text-green-600">
                      <Send className="w-3 h-3" />
                    </Button>
                  )}
                  
                  {quotation.status === 'sent' && (
                    <>
                      {onApplyDiscount && (
                        <Button variant="ghost" size="sm" onClick={() => onApplyDiscount(quotation)} className="h-6 px-2 text-xs text-purple-600" title="Apply Discount">
                          <Percent className="w-3 h-3" />
                        </Button>
                      )}
                      {onClientResponse && (
                        <>
                          <Button variant="ghost" size="sm" onClick={() => onClientResponse(quotation.id, 'accepted')} className="h-6 px-2 text-xs text-green-600" title="Won">
                            <CheckCircle className="w-3 h-3" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => onClientResponse(quotation.id, 'declined')} className="h-6 px-2 text-xs text-red-600" title="Lost">
                            <XCircle className="w-3 h-3" />
                          </Button>
                        </>
                      )}
                    </>
                  )}
                  
                  {['approved', 'sent', 'accepted'].includes(quotation.status) && onDownloadPdf && (
                    <Button variant="ghost" size="sm" onClick={() => onDownloadPdf(quotation.id)} className="h-6 px-2 text-xs text-blue-600">
                      <Download className="w-3 h-3" />
                    </Button>
                  )}
                </div>
              </div>
            );
          })()}
        </div>
      )}
      
      {/* Revive button for lost leads */}
      {lead.stage === "lost" && (
        <div className="mt-2 pt-2 border-t">
          <Button 
            size="sm" 
            variant="outline"
            onClick={() => handleReviveLead(lead)}
            className="h-7 text-xs w-full text-green-600 border-green-300 hover:bg-green-50"
          >
            <Clock className="w-3 h-3 mr-1" />
            Revive Lead
          </Button>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Header */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            placeholder="Search leads..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={stageFilter} onValueChange={setStageFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All Stages" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Stages</SelectItem>
            {STAGES.map((s) => (
              <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={sourceFilter} onValueChange={setSourceFilter}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Sources" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Sources</SelectItem>
            {SOURCES.map((s) => (
              <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="flex gap-2">
          {isAdmin && (
            <Button 
              variant="outline"
              size="sm"
              onClick={loadArchivedLeads}
              className="text-orange-600 border-orange-300"
            >
              <Archive className="w-4 h-4 mr-1" />
              Archived
            </Button>
          )}
          <Button 
            variant={viewMode === "pipeline" ? "default" : "outline"}
            size="sm"
            onClick={() => setViewMode("pipeline")}
          >
            Pipeline
          </Button>
          <Button 
            variant={viewMode === "list" ? "default" : "outline"}
            size="sm"
            onClick={() => setViewMode("list")}
          >
            List
          </Button>
        </div>
        <Button onClick={() => handleOpenDialog()} data-testid="add-lead-btn">
          <Plus className="w-4 h-4 mr-2" />
          Add Lead
        </Button>
      </div>

      {/* Pipeline View */}
      {viewMode === "pipeline" && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 overflow-x-auto">
          {STAGES.map((stage) => (
            <div 
              key={stage.id}
              className={`min-w-[200px] rounded-lg border-2 ${stage.borderColor} p-2`}
            >
              <div className={`flex items-center justify-between mb-2 px-2 py-1 rounded ${stage.color}`}>
                <span className="font-medium text-sm">{stage.label}</span>
                <Badge variant="secondary" className="text-xs">
                  {leadsByStage[stage.id]?.length || 0}
                </Badge>
              </div>
              <div className="space-y-2 max-h-[500px] overflow-y-auto">
                {leadsByStage[stage.id]?.map((lead) => (
                  <LeadCard key={lead.id} lead={lead} />
                ))}
                {leadsByStage[stage.id]?.length === 0 && (
                  <p className="text-xs text-gray-400 text-center py-4">No leads</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* List View */}
      {viewMode === "list" && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Company</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Contact</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Stage</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Value</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Follow-up</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Source</th>
                    {isAdmin && <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Owner</th>}
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {filteredLeads.map((lead) => {
                    const stageInfo = STAGES.find((s) => s.id === lead.stage);
                    return (
                      <tr key={lead.id} className={isOverdue(lead.follow_up_date) ? "bg-red-50" : ""}>
                        <td className="px-4 py-3">
                          <p className="font-medium text-sm">{lead.company_name}</p>
                        </td>
                        <td className="px-4 py-3">
                          <p className="text-sm">{lead.contact_person || "-"}</p>
                          {lead.contact_email && (
                            <p className="text-xs text-gray-500">{lead.contact_email}</p>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <Badge className={stageInfo?.color}>{stageInfo?.label}</Badge>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {lead.expected_value > 0 ? formatCurrency(lead.expected_value) : "-"}
                        </td>
                        <td className="px-4 py-3">
                          {lead.follow_up_date ? (
                            <span className={`text-sm ${isOverdue(lead.follow_up_date) ? "text-red-600 font-medium" : ""}`}>
                              {lead.follow_up_date}
                            </span>
                          ) : "-"}
                        </td>
                        <td className="px-4 py-3 text-sm">{lead.source || "-"}</td>
                        {isAdmin && <td className="px-4 py-3 text-sm text-gray-500">{lead.created_by_name || "-"}</td>}
                        <td className="px-4 py-3">
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" onClick={() => handleOpenDialog(lead)}>
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => handleDelete(lead.id)}>
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {filteredLeads.length === 0 && (
                <p className="text-center py-8 text-gray-500">No leads found</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingLead ? "Edit Lead" : "Add New Lead"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Company Name *</Label>
              <Input
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                placeholder="Company name"
                data-testid="lead-company-input"
              />
            </div>
            <div>
              <Label>Company Address</Label>
              <Textarea
                value={form.company_address}
                onChange={(e) => setForm({ ...form, company_address: e.target.value })}
                placeholder="Full company address"
                rows={2}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Contact Person</Label>
                <Input
                  value={form.contact_person}
                  onChange={(e) => setForm({ ...form, contact_person: e.target.value })}
                  placeholder="Name"
                />
              </div>
              <div>
                <Label>Phone</Label>
                <Input
                  value={form.contact_phone}
                  onChange={(e) => setForm({ ...form, contact_phone: e.target.value })}
                  placeholder="Phone"
                />
              </div>
            </div>
            <div>
              <Label>Email</Label>
              <Input
                value={form.contact_email}
                onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
                placeholder="Email"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Source</Label>
                <Select value={form.source} onValueChange={(v) => setForm({ ...form, source: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select source" />
                  </SelectTrigger>
                  <SelectContent>
                    {SOURCES.map((s) => (
                      <SelectItem key={s.id} value={s.id}>{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Expected Value (RM)</Label>
                <Input
                  type="number"
                  value={form.expected_value}
                  onChange={(e) => setForm({ ...form, expected_value: parseFloat(e.target.value) || 0 })}
                  placeholder="0"
                />
              </div>
            </div>
            <div>
              <Label>Follow-up Date</Label>
              <Input
                type="date"
                value={form.follow_up_date}
                onChange={(e) => setForm({ ...form, follow_up_date: e.target.value })}
              />
            </div>
            <div>
              <Label>Notes</Label>
              <Textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Additional notes..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter className="flex-col sm:flex-row gap-2">
            {editingLead && !editingLead.quotation_id && onCreateQuotation && (
              <Button 
                variant="outline" 
                onClick={() => {
                  handleCreateQuotation(editingLead);
                  setShowDialog(false);
                }}
                className="w-full sm:w-auto bg-blue-50 hover:bg-blue-100 text-blue-700"
              >
                <FileText className="w-4 h-4 mr-2" />
                Create Quotation
              </Button>
            )}
            <div className="flex gap-2 w-full sm:w-auto">
              <Button variant="outline" onClick={() => setShowDialog(false)}>Cancel</Button>
              <Button onClick={handleSave} data-testid="save-lead-btn">
                {editingLead ? "Update" : "Create"} Lead
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Mark as Won Dialog */}
      <Dialog open={wonDialogOpen} onOpenChange={setWonDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-700">
              <CheckCircle className="w-5 h-5" />
              Mark Lead as Won
            </DialogTitle>
          </DialogHeader>
          {wonLead && (
            <div className="space-y-4 py-2">
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="font-medium">{wonLead.company_name}</p>
                <p className="text-sm text-gray-600">{wonLead.contact_person}</p>
                {wonLead.expected_value > 0 && (
                  <p className="text-sm text-green-600 font-medium mt-1">
                    Expected Value: {formatCurrency(wonLead.expected_value)}
                  </p>
                )}
              </div>
              
              <p className="text-sm text-gray-600">
                Enter training details to create a draft session:
              </p>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Training Start Date *</Label>
                  <Input
                    type="date"
                    value={wonForm.training_date}
                    onChange={(e) => setWonForm({ ...wonForm, training_date: e.target.value })}
                    data-testid="won-training-date"
                  />
                </div>
                <div>
                  <Label className="text-xs">End Date</Label>
                  <Input
                    type="date"
                    value={wonForm.end_date}
                    onChange={(e) => setWonForm({ ...wonForm, end_date: e.target.value })}
                    min={wonForm.training_date}
                    data-testid="won-end-date"
                  />
                </div>
              </div>
              
              <div>
                <Label className="text-xs">Number of Participants (Pax)</Label>
                <Input
                  type="number"
                  min="1"
                  placeholder="e.g. 20"
                  value={wonForm.num_participants}
                  onChange={(e) => setWonForm({ ...wonForm, num_participants: e.target.value })}
                  data-testid="won-num-participants"
                />
              </div>
              
              <div>
                <Label className="text-xs">Venue / Location</Label>
                <Input
                  placeholder="Training venue address"
                  value={wonForm.venue}
                  onChange={(e) => setWonForm({ ...wonForm, venue: e.target.value })}
                  data-testid="won-venue"
                />
              </div>
              
              <div>
                <Label className="text-xs">Grant ID (if applicable)</Label>
                <Input
                  placeholder="e.g. HRDF-123456"
                  value={wonForm.grant_id}
                  onChange={(e) => setWonForm({ ...wonForm, grant_id: e.target.value })}
                  data-testid="won-grant-id"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setWonDialogOpen(false)}>Cancel</Button>
            <Button 
              onClick={handleMarkWon} 
              className="bg-green-600 hover:bg-green-700"
              data-testid="confirm-mark-won-btn"
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Mark as Won & Create Session
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export { LeadPipelineTab };
