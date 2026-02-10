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
import { toast } from "sonner";
import { Eye, CheckCircle, XCircle, Download, Plus, Trash2, Edit } from "lucide-react";

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
  // Filter state
  const [quotationFilter, setQuotationFilter] = useState("all");

  // Filter quotations
  const filteredQuotations = useMemo(() => {
    if (quotationFilter === "all") return quotations;
    return quotations.filter(q => q.status === quotationFilter);
  }, [quotations, quotationFilter]);

  const pendingQuotations = quotations.filter(q => q.status === 'pending_approval');

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
      await axiosInstance.put(`/marketing/quotations/${quotationId}/approve`);
      toast.success("Quotation approved successfully");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to approve quotation");
    }
  };

  const handleAddDescriptionItem = async () => {
    const name = prompt("Enter item name:");
    if (!name) return;
    const description = prompt("Enter item description:");
    if (!description) return;
    const category = prompt("Enter category (e.g., inclusions, equipment, services):", "inclusions");
    
    try {
      await axiosInstance.post('/marketing/description-items', {
        name,
        description,
        category: category || "inclusions",
        sort_order: 0
      });
      toast.success("Description item created");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create item");
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
          <div className="flex justify-between items-center flex-wrap gap-3">
            <div>
              <CardTitle>Quotation Management</CardTitle>
              <CardDescription>Review and approve marketing quotations</CardDescription>
            </div>
            <div className="flex gap-2 items-center">
              <Badge className="bg-yellow-500 text-white">{pendingQuotations.length} Pending</Badge>
              <Select value={quotationFilter} onValueChange={setQuotationFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Filter" />
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
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
              <CardTitle className="text-base sm:text-lg">All Marketing Clients</CardTitle>
              <CardDescription className="text-xs sm:text-sm">View all clients across all marketers</CardDescription>
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
        </CardHeader>
        <CardContent>
          {allClients.length === 0 ? (
            <p className="text-center text-gray-500 py-4 text-sm">No clients registered yet.</p>
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
                  {allClients.map(client => (
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

      {/* Description Items Management */}
      <Card className="mt-6">
        <CardHeader>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
              <CardTitle className="text-base sm:text-lg">Quotation Description Items</CardTitle>
              <CardDescription className="text-xs sm:text-sm">Manage reusable description items for quotations</CardDescription>
            </div>
            <Button 
              onClick={handleAddDescriptionItem}
              size="sm"
              className="text-xs sm:text-sm"
            >
              <Plus className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" /> Add Item
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {descriptionItems.length === 0 ? (
              <p className="text-center text-gray-500 py-4 text-sm">No description items yet. Add items that marketers can select when creating quotations.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="text-left p-2 text-xs sm:text-sm">Name</th>
                      <th className="text-left p-2 text-xs sm:text-sm">Description</th>
                      <th className="text-left p-2 text-xs sm:text-sm">Category</th>
                      <th className="text-center p-2 text-xs sm:text-sm">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {descriptionItems.map(item => (
                      <tr key={item.id} className="border-b hover:bg-gray-50">
                        <td className="p-2 font-medium text-xs sm:text-sm">{item.name}</td>
                        <td className="p-2 text-xs sm:text-sm max-w-[200px] truncate">{item.description}</td>
                        <td className="p-2 text-xs sm:text-sm">
                          <Badge variant="outline">{item.category}</Badge>
                        </td>
                        <td className="p-2 text-center">
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => handleDeleteDescriptionItem(item)}
                            className="text-red-600 h-7 w-7 p-0"
                          >
                            <Trash2 className="w-3 h-3 sm:w-4 sm:h-4" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

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
