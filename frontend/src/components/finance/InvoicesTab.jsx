/**
 * InvoicesTab Component - Extracted from FinanceDashboard
 * Manages invoice listing, approval, issuance, cancellation, and PDF generation
 */
import { useState, useMemo } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { FileSpreadsheet, RefreshCw, Edit, Check, FileText, Download, CreditCard, X, RotateCcw, Plus } from "lucide-react";

const InvoicesTab = ({
  invoices,
  loading,
  companySettings,
  onRefresh,
  onEditInvoice,
  onRecordPayment,
  setActiveTab,
}) => {
  // Filter state
  const [statusFilter, setStatusFilter] = useState("all");

  // Filter invoices by status
  const filteredInvoices = useMemo(() => {
    if (statusFilter === "all") return invoices;
    return invoices.filter(inv => inv.status === statusFilter);
  }, [invoices, statusFilter]);

  // Status badge helper
  const getStatusBadge = (status) => {
    const statusConfig = {
      draft: { label: 'Draft', className: 'bg-gray-100 text-gray-800' },
      auto_draft: { label: 'Auto Draft', className: 'bg-gray-100 text-gray-800' },
      pending: { label: 'Pending', className: 'bg-yellow-100 text-yellow-800' },
      approved: { label: 'Approved', className: 'bg-blue-100 text-blue-800' },
      issued: { label: 'Issued', className: 'bg-green-100 text-green-800' },
      paid: { label: 'Paid', className: 'bg-emerald-100 text-emerald-800' },
      cancelled: { label: 'Cancelled', className: 'bg-red-100 text-red-800' },
      voided: { label: 'Voided', className: 'bg-purple-100 text-purple-800' },
    };
    const config = statusConfig[status] || { label: status, className: 'bg-gray-100 text-gray-800' };
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  // API Handlers
  const handleApproveInvoice = async (invoiceId) => {
    try {
      await axiosInstance.post(`/finance/invoices/${invoiceId}/approve`);
      toast.success("Invoice approved");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to approve invoice");
    }
  };

  const handleIssueInvoice = async (invoiceId) => {
    try {
      await axiosInstance.post(`/finance/invoices/${invoiceId}/issue`);
      toast.success("Invoice issued");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to issue invoice");
    }
  };

  const handleCancelInvoice = async (invoiceId) => {
    if (!confirm("Are you sure you want to cancel this invoice?")) return;
    try {
      await axiosInstance.post(`/finance/invoices/${invoiceId}/cancel`);
      toast.success("Invoice cancelled");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to cancel invoice");
    }
  };

  const handleReverseVoidedInvoice = async (invoiceId) => {
    if (!confirm("Reverse this voided invoice back to Draft status?")) return;
    try {
      await axiosInstance.post(`/finance/invoices/${invoiceId}/reverse-void`);
      toast.success("Invoice reversed to Draft");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to reverse invoice");
    }
  };

  const handleCreateReplacementInvoice = async (invoiceId) => {
    try {
      const response = await axiosInstance.post(`/finance/invoices/${invoiceId}/create-replacement`);
      toast.success(`Replacement invoice ${response.data.invoice_number} created`);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create replacement");
    }
  };

  const handleExportInvoices = async () => {
    try {
      const response = await axiosInstance.get('/finance/invoices/export', {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `invoices_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("Invoices exported");
    } catch (error) {
      toast.error("Failed to export invoices");
    }
  };

  const handlePrintInvoice = async (invoice) => {
    try {
      // Get app settings for logo
      const appSettings = await axiosInstance.get('/settings');
      const logoUrl = appSettings.data?.logo_url || companySettings?.logo_url;
      
      // Import and use print function
      const { printInvoice } = await import('../../utils/printInvoice');
      printInvoice(invoice, companySettings, logoUrl);
    } catch (error) {
      console.error("Print error:", error);
      toast.error("Failed to generate invoice PDF");
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center flex-wrap gap-4">
          <CardTitle>Invoice Management</CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleExportInvoices} className="text-green-600">
              <FileSpreadsheet className="w-4 h-4 mr-1" />
              Export Excel
            </Button>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Invoices</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="issued">Issued</SelectItem>
                <SelectItem value="paid">Paid</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={onRefresh}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="text-center py-8">Loading invoices...</div>
        ) : filteredInvoices.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No invoices found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Invoice #</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Date</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Company</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Session</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Amount</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-500">Status</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredInvoices.map((invoice) => (
                  <tr key={invoice.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium">{invoice.invoice_number}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString('en-MY') : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">{invoice.company_name || '-'}</td>
                    <td className="px-4 py-3 text-sm">{invoice.session_name || '-'}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium">
                      RM {invoice.total_amount?.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-center">{getStatusBadge(invoice.status)}</td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex justify-center gap-1">
                        {/* Edit Button - Available before issuing */}
                        {!['issued', 'paid', 'cancelled'].includes(invoice.status) && (
                          <Button 
                            variant="ghost" 
                            size="sm"
                            className="text-orange-600"
                            onClick={() => onEditInvoice(invoice)}
                            title="Edit Invoice"
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                        )}
                        
                        {/* Approve Button */}
                        {(invoice.status === 'auto_draft' || invoice.status === 'draft') && (
                          <Button 
                            variant="ghost" 
                            size="sm"
                            className="text-green-600"
                            onClick={() => handleApproveInvoice(invoice.id)}
                            title="Approve"
                          >
                            <Check className="w-4 h-4" />
                          </Button>
                        )}
                        
                        {/* Issue Button */}
                        {invoice.status === 'approved' && (
                          <Button 
                            variant="ghost" 
                            size="sm"
                            className="text-blue-600"
                            onClick={() => handleIssueInvoice(invoice.id)}
                            title="Issue"
                          >
                            <FileText className="w-4 h-4" />
                          </Button>
                        )}
                        
                        {/* Issued Invoice Actions */}
                        {invoice.status === 'issued' && (
                          <>
                            <Button 
                              variant="ghost" 
                              size="sm"
                              className="text-green-600"
                              onClick={() => handlePrintInvoice(invoice)}
                              title="Download Invoice"
                            >
                              <Download className="w-4 h-4" />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="sm"
                              className="text-blue-600"
                              onClick={() => {
                                onRecordPayment(invoice.id);
                                setActiveTab('payments');
                              }}
                              title="Record Payment"
                            >
                              <CreditCard className="w-4 h-4" />
                            </Button>
                          </>
                        )}
                        
                        {/* Paid Invoice - Download */}
                        {invoice.status === 'paid' && (
                          <Button 
                            variant="ghost" 
                            size="sm"
                            className="text-green-600"
                            onClick={() => handlePrintInvoice(invoice)}
                            title="Download Invoice"
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                        )}
                        
                        {/* Cancel Button */}
                        {!['paid', 'cancelled', 'voided'].includes(invoice.status) && (
                          <Button 
                            variant="ghost" 
                            size="sm"
                            className="text-red-600"
                            onClick={() => handleCancelInvoice(invoice.id)}
                            title="Cancel"
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        )}
                        
                        {/* Voided Invoice Actions */}
                        {invoice.status === 'voided' && (
                          <>
                            <Button 
                              variant="outline" 
                              size="sm"
                              className="text-orange-600 border-orange-300 hover:bg-orange-50"
                              onClick={() => handleReverseVoidedInvoice(invoice.id)}
                              title="Reverse Void (back to Draft)"
                              data-testid={`reverse-void-${invoice.id}`}
                            >
                              <RotateCcw className="w-4 h-4 mr-1" />
                              Undo
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm"
                              className="text-blue-600 border-blue-300 hover:bg-blue-50"
                              onClick={() => handleCreateReplacementInvoice(invoice.id)}
                              title="Create Replacement Invoice"
                              data-testid={`create-replacement-${invoice.id}`}
                            >
                              <Plus className="w-4 h-4 mr-1" />
                              Replace
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
  );
};

export { InvoicesTab };
