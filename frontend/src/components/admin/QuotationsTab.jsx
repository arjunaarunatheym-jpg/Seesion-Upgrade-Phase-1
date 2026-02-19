/**
 * QuotationsTab Component - Extracted from AdminDashboard
 * Manages quotations, clients, description items, and PDF templates
 */
import { useState, useEffect, useMemo } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { Eye, CheckCircle, XCircle, Download, Plus, Trash2, Edit, Package, PackageX } from "lucide-react";

const QuotationsTab = ({
  quotations,
  allClients,
  descriptionItems,
  pdfTemplates,
  onRefresh,
  onViewQuotation,
  onRejectQuotation,
  onShowPdfTemplates,
  onUpdatePdfColor,
}) => {
  // Get current year and month for defaults
  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;
  
  // Filter state for Quotations
  const [quotationFilter, setQuotationFilter] = useState("all");
  const [quotationYear, setQuotationYear] = useState(currentYear.toString());
  const [quotationMonth, setQuotationMonth] = useState("all");
  
  // Filter state for Clients
  const [clientGroup, setClientGroup] = useState("all");
  
  // Description Item Dialog
  const [itemDialogOpen, setItemDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [itemForm, setItemForm] = useState({
    name: "",
    category: "inclusion",
    has_quantity: false
  });

  // Get available years from quotations
  const availableYears = useMemo(() => {
    const years = new Set();
    quotations.forEach(q => {
      if (q.created_at) {
        const year = new Date(q.created_at).getFullYear();
        years.add(year);
      }
    });
    years.add(currentYear); // Always include current year
    return Array.from(years).sort((a, b) => b - a);
  }, [quotations, currentYear]);

  // Month names for dropdown
  const months = [
    { value: "1", label: "January" },
    { value: "2", label: "February" },
    { value: "3", label: "March" },
    { value: "4", label: "April" },
    { value: "5", label: "May" },
    { value: "6", label: "June" },
    { value: "7", label: "July" },
    { value: "8", label: "August" },
    { value: "9", label: "September" },
    { value: "10", label: "October" },
    { value: "11", label: "November" },
    { value: "12", label: "December" },
  ];

  // Filter quotations by status, year, and month
  const filteredQuotations = useMemo(() => {
    let filtered = quotations;
    
    // Filter by status
    if (quotationFilter !== "all") {
      filtered = filtered.filter(q => q.status === quotationFilter);
    }
    
    // Filter by year
    if (quotationYear !== "all") {
      filtered = filtered.filter(q => {
        if (!q.created_at) return false;
        return new Date(q.created_at).getFullYear().toString() === quotationYear;
      });
    }
    
    // Filter by month
    if (quotationMonth !== "all") {
      filtered = filtered.filter(q => {
        if (!q.created_at) return false;
        return (new Date(q.created_at).getMonth() + 1).toString() === quotationMonth;
      });
    }
    
    return filtered;
  }, [quotations, quotationFilter, quotationYear, quotationMonth]);

  const pendingQuotations = quotations.filter(q => q.status === 'pending_approval');
  
  // Separate inclusions and exclusions - handle both singular and plural
  const inclusions = descriptionItems.filter(i => i.category === 'inclusion' || i.category === 'inclusions');
  const exclusions = descriptionItems.filter(i => i.category === 'exclusion' || i.category === 'exclusions');

  // Alphabetical groups for clients
  const clientGroups = [
    { value: "A-D", letters: ["A", "B", "C", "D"] },
    { value: "E-H", letters: ["E", "F", "G", "H"] },
    { value: "I-L", letters: ["I", "J", "K", "L"] },
    { value: "M-P", letters: ["M", "N", "O", "P"] },
    { value: "Q-T", letters: ["Q", "R", "S", "T"] },
    { value: "U-Z", letters: ["U", "V", "W", "X", "Y", "Z"] },
  ];

  // Filter and sort clients
  const filteredClients = useMemo(() => {
    let filtered = [...allClients].sort((a, b) => 
      (a.company_name || "").localeCompare(b.company_name || "")
    );
    
    if (clientGroup !== "all") {
      const group = clientGroups.find(g => g.value === clientGroup);
      if (group) {
        filtered = filtered.filter(c => {
          const firstLetter = (c.company_name || "")[0]?.toUpperCase();
          return group.letters.includes(firstLetter);
        });
      }
    }
    
    return filtered;
  }, [allClients, clientGroup]);

  const getQuotationStatusBadge = (status) => {
    const statusConfig = {
      pending_approval: { label: 'Pending Approval', className: 'bg-yellow-100 text-yellow-800' },
      approved: { label: 'Approved', className: 'bg-green-100 text-green-800' },
      rejected: { label: 'Rejected', className: 'bg-red-100 text-red-800' },
      sent: { label: 'Sent', className: 'bg-blue-100 text-blue-800' },
      accepted: { label: 'Accepted', className: 'bg-emerald-100 text-emerald-800' },
      declined: { label: 'Declined', className: 'bg-gray-100 text-gray-800' },
    };
    const config = statusConfig[status] || { label: status, className: 'bg-gray-100 text-gray-800' };
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  const handleApproveQuotation = async (quotationId) => {
    try {
      await axiosInstance.post(`/marketing/quotations/${quotationId}/approve`);
      toast.success("Quotation approved successfully");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to approve quotation");
    }
  };

  const openAddItemDialog = (category) => {
    setEditingItem(null);
    setItemForm({
      name: "",
      category: category,
      has_quantity: false
    });
    setItemDialogOpen(true);
  };

  const openEditItemDialog = (item) => {
    setEditingItem(item);
    setItemForm({
      name: item.name,
      category: item.category || "inclusion",
      has_quantity: item.has_quantity || false
    });
    setItemDialogOpen(true);
  };

  const handleSaveItem = async () => {
    if (!itemForm.name.trim()) {
      toast.error("Please enter item name");
      return;
    }
    
    try {
      if (editingItem) {
        await axiosInstance.put(`/marketing/description-items/${editingItem.id}`, itemForm);
        toast.success("Item updated");
      } else {
        await axiosInstance.post('/marketing/description-items', itemForm);
        toast.success("Item created");
      }
      setItemDialogOpen(false);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save item");
    }
  };

  const handleDeleteDescriptionItem = async (item) => {
    if (confirm(`Delete "${item.name}"?`)) {
      try {
        await axiosInstance.delete(`/marketing/description-items/${item.id}`);
        toast.success("Item deleted");
        onRefresh();
      } catch (error) {
        toast.error(error.response?.data?.detail || "Failed to delete");
      }
    }
  };

  return (
    <>
      {/* Quotation Management */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-center flex-wrap gap-3">
              <div>
                <CardTitle>Quotation Management</CardTitle>
                <CardDescription>Review and approve marketing quotations</CardDescription>
              </div>
              <Badge className="bg-yellow-500 text-white">{pendingQuotations.length} Pending</Badge>
            </div>
            {/* Filter Row */}
            <div className="flex flex-wrap gap-2 items-center">
              <Select value={quotationYear} onValueChange={setQuotationYear}>
                <SelectTrigger className="w-28">
                  <SelectValue placeholder="Year" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Years</SelectItem>
                  {availableYears.map(year => (
                    <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={quotationMonth} onValueChange={setQuotationMonth}>
                <SelectTrigger className="w-36">
                  <SelectValue placeholder="Month" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Months</SelectItem>
                  {months.map(m => (
                    <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={quotationFilter} onValueChange={setQuotationFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="pending_approval">Pending Approval</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="sent">Sent</SelectItem>
                  <SelectItem value="accepted">Accepted</SelectItem>
                  <SelectItem value="declined">Declined</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-sm text-gray-500 ml-2">
                {filteredQuotations.length} quotation{filteredQuotations.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredQuotations.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No quotations found</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="text-left p-3">Quotation No</th>
                    <th className="text-left p-3">Client</th>
                    <th className="text-left p-3">Marketer</th>
                    <th className="text-left p-3">Programme</th>
                    <th className="text-right p-3">Amount</th>
                    <th className="text-center p-3">Status</th>
                    <th className="text-center p-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredQuotations.map(q => (
                    <tr key={q.id} className="border-b hover:bg-gray-50">
                      <td className="p-3 font-medium">{q.quotation_number}</td>
                      <td className="p-3">{q.client_name}</td>
                      <td className="p-3">{q.marketer_name}</td>
                      <td className="p-3">{q.programme_name}</td>
                      <td className="p-3 text-right">RM {(q.total_amount || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}</td>
                      <td className="p-3 text-center">{getQuotationStatusBadge(q.status)}</td>
                      <td className="p-3">
                        <div className="flex justify-center gap-1">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={() => onViewQuotation(q)}
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          
                          {q.status === 'pending_approval' && (
                            <>
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => handleApproveQuotation(q.id)}
                                title="Approve"
                                className="text-green-600 hover:text-green-700"
                              >
                                <CheckCircle className="w-4 h-4" />
                              </Button>
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => onRejectQuotation(q)}
                                title="Reject"
                                className="text-red-600 hover:text-red-700"
                              >
                                <XCircle className="w-4 h-4" />
                              </Button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* All Marketing Clients */}
      <Card className="mt-6">
        <CardHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div>
                <CardTitle className="text-base sm:text-lg">All Marketing Clients</CardTitle>
                <CardDescription className="text-xs sm:text-sm">View all clients across all marketers ({allClients.length} total)</CardDescription>
              </div>
              <Button 
                onClick={() => {
                  window.location.href = `${process.env.REACT_APP_BACKEND_URL}/api/marketing/clients/export`;
                }}
                size="sm"
                variant="outline"
                className="text-xs sm:text-sm"
              >
                <Download className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> Export CSV
              </Button>
            </div>
            {/* Alphabetical Filter */}
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-sm text-gray-600">Filter by name:</span>
              <Select value={clientGroup} onValueChange={setClientGroup}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Group" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All (A-Z)</SelectItem>
                  {clientGroups.map(g => (
                    <SelectItem key={g.value} value={g.value}>{g.value}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-sm text-gray-500">
                {filteredClients.length} client{filteredClients.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredClients.length === 0 ? (
            <p className="text-center text-gray-500 py-4 text-sm">No clients found in this group.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs sm:text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="text-left p-2">Company</th>
                    <th className="text-left p-2">Contact Person</th>
                    <th className="text-left p-2 hidden sm:table-cell">Email</th>
                    <th className="text-left p-2 hidden md:table-cell">Phone</th>
                    <th className="text-left p-2">Marketer</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredClients.map(client => (
                    <tr key={client.id} className="border-b hover:bg-gray-50">
                      <td className="p-2 font-medium max-w-[120px] truncate">{client.company_name}</td>
                      <td className="p-2 max-w-[100px] truncate">{client.contact_person}</td>
                      <td className="p-2 max-w-[150px] truncate hidden sm:table-cell">{client.contact_email}</td>
                      <td className="p-2 hidden md:table-cell">{client.contact_phone}</td>
                      <td className="p-2">
                        <Badge variant="outline" className="text-xs">
                          {client.marketer_name}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Description Items Management - Inclusions & Exclusions */}
      <Card className="mt-6">
        <CardHeader>
          <div>
            <CardTitle className="text-base sm:text-lg">Quotation Inclusions & Exclusions</CardTitle>
            <CardDescription className="text-xs sm:text-sm">Manage items that marketers can select when creating quotations</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          {/* Two-column layout for Inclusions and Exclusions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Inclusions Column */}
            <div className="border rounded-lg p-4 bg-green-50/50">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-2">
                  <Package className="w-5 h-5 text-green-600" />
                  <h3 className="font-semibold text-green-800">Inclusions</h3>
                </div>
                <Button 
                  onClick={() => openAddItemDialog('inclusion')}
                  size="sm"
                  variant="outline"
                  className="text-xs border-green-600 text-green-600 hover:bg-green-100"
                >
                  <Plus className="w-3 h-3 mr-1" /> Add
                </Button>
              </div>
              {inclusions.length === 0 ? (
                <p className="text-center text-gray-500 py-4 text-sm">No inclusions yet</p>
              ) : (
                <div className="space-y-2">
                  {inclusions.map(item => (
                    <div key={item.id} className="flex items-center justify-between p-2 bg-white rounded border">
                      <div>
                        <span className="font-medium text-sm">{item.name}</span>
                        {item.has_quantity && (
                          <Badge variant="secondary" className="ml-2 text-xs">Qty</Badge>
                        )}
                      </div>
                      <div className="flex gap-1">
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => openEditItemDialog(item)}
                          className="h-7 w-7 p-0"
                        >
                          <Edit className="w-3 h-3" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => handleDeleteDescriptionItem(item)}
                          className="text-red-600 h-7 w-7 p-0"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Exclusions Column */}
            <div className="border rounded-lg p-4 bg-red-50/50">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-2">
                  <PackageX className="w-5 h-5 text-red-600" />
                  <h3 className="font-semibold text-red-800">Exclusions</h3>
                </div>
                <Button 
                  onClick={() => openAddItemDialog('exclusion')}
                  size="sm"
                  variant="outline"
                  className="text-xs border-red-600 text-red-600 hover:bg-red-100"
                >
                  <Plus className="w-3 h-3 mr-1" /> Add
                </Button>
              </div>
              {exclusions.length === 0 ? (
                <p className="text-center text-gray-500 py-4 text-sm">No exclusions yet</p>
              ) : (
                <div className="space-y-2">
                  {exclusions.map(item => (
                    <div key={item.id} className="flex items-center justify-between p-2 bg-white rounded border">
                      <div>
                        <span className="font-medium text-sm">{item.name}</span>
                        {item.has_quantity && (
                          <Badge variant="secondary" className="ml-2 text-xs">Qty</Badge>
                        )}
                      </div>
                      <div className="flex gap-1">
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => openEditItemDialog(item)}
                          className="h-7 w-7 p-0"
                        >
                          <Edit className="w-3 h-3" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => handleDeleteDescriptionItem(item)}
                          className="text-red-600 h-7 w-7 p-0"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Item Add/Edit Dialog */}
      <Dialog open={itemDialogOpen} onOpenChange={setItemDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingItem ? 'Edit Item' : `Add ${itemForm.category === 'inclusion' ? 'Inclusion' : 'Exclusion'}`}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="item-name">Item Name *</Label>
              <Input
                id="item-name"
                value={itemForm.name}
                onChange={(e) => setItemForm({...itemForm, name: e.target.value})}
                placeholder="e.g., JPJ Trainers, Venue Rental"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="item-category">Category</Label>
              <Select 
                value={itemForm.category} 
                onValueChange={(val) => setItemForm({...itemForm, category: val})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="inclusion">Inclusion</SelectItem>
                  <SelectItem value="exclusion">Exclusion</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="has-quantity"
                checked={itemForm.has_quantity}
                onCheckedChange={(checked) => setItemForm({...itemForm, has_quantity: checked})}
              />
              <Label htmlFor="has-quantity" className="text-sm">
                Allow quantity input (marketer can specify how many)
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setItemDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveItem}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* PDF Templates Management */}
      <Card className="mt-6">
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>PDF Document Templates</CardTitle>
              <CardDescription>Customize cover letter and terms & conditions for quotation PDFs</CardDescription>
            </div>
            <Button 
              onClick={onShowPdfTemplates}
              size="sm"
            >
              <Edit className="w-4 h-4 mr-2" /> Edit Templates
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h4 className="font-semibold text-blue-900 mb-2">Cover Letter (Page 1)</h4>
              <p className="text-sm text-blue-700">
                Customize the introductory letter. Placeholders: {"{{programme_name}}"}, {"{{company_name}}"}, {"{{contact_person}}"}, {"{{quotation_number}}"}, {"{{marketer_name}}"}, {"{{total_amount}}"}
              </p>
            </div>
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <h4 className="font-semibold text-green-900 mb-2">Terms & Conditions (Pages 3-6)</h4>
              <p className="text-sm text-green-700">
                Define the terms and conditions that will be included in pages 3-6 of the quotation PDF document.
              </p>
            </div>
          </div>
          
          {/* Color Settings */}
          <div className="mt-4 p-4 bg-purple-50 rounded-lg border border-purple-200">
            <h4 className="font-semibold text-purple-900 mb-2">PDF Color Theme</h4>
            <p className="text-sm text-purple-700 mb-3">Set the primary color for quotation PDF headers and titles</p>
            <div className="flex items-center gap-3">
              <input 
                type="color" 
                value={pdfTemplates?.primary_color || "#1a365d"}
                onChange={(e) => onUpdatePdfColor && onUpdatePdfColor(e.target.value)}
                className="w-10 h-10 rounded cursor-pointer border border-purple-300"
              />
              <span className="text-sm text-gray-600">Current: {pdfTemplates?.primary_color || "#1a365d"}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
};

export { QuotationsTab };
