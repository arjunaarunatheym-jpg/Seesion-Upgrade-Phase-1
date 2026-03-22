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
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { toast } from "sonner";
import { FileSpreadsheet, RefreshCw, Edit, Check, FileText, Download, CreditCard, X, RotateCcw, Plus, ChevronDown, ChevronRight, Calendar } from "lucide-react";

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
  
  // Collapsible state for month groups
  const [expandedMonths, setExpandedMonths] = useState({});

  // Filter invoices by status
  const filteredInvoices = useMemo(() => {
    if (statusFilter === "all") return invoices;
    return invoices.filter(inv => inv.status === statusFilter);
  }, [invoices, statusFilter]);

  // Group invoices by month
  const groupedByMonth = useMemo(() => {
    const groups = {};
    filteredInvoices.forEach(inv => {
      const dateStr = inv.invoice_date || inv.created_at;
      if (!dateStr) return;
      const date = new Date(dateStr);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      const label = date.toLocaleString('en', { month: 'long', year: 'numeric' });
      
      if (!groups[key]) {
        groups[key] = {
          key,
          label,
          invoices: [],
          total: 0
        };
      }
      groups[key].invoices.push(inv);
      groups[key].total += inv.total_amount || 0;
    });
    return Object.values(groups).sort((a, b) => b.key.localeCompare(a.key));
  }, [filteredInvoices]);

  const toggleMonth = (monthKey) => {
    setExpandedMonths(prev => ({
      ...prev,
      [monthKey]: !prev[monthKey]
    }));
  };

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
          <div className="space-y-3" data-testid="invoices-loading">
            {[1,2,3,4,5].map(i => (
              <div key={i} className="flex items-center gap-4 p-3">
                <div className="h-5 w-28 bg-gray-200 animate-pulse rounded" />
                <div className="h-5 flex-1 bg-gray-200 animate-pulse rounded" />
                <div className="h-5 w-20 bg-gray-200 animate-pulse rounded-full" />
                <div className="h-5 w-24 bg-gray-200 animate-pulse rounded" />
              </div>
            ))}
          </div>
        ) : filteredInvoices.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center" data-testid="empty-state">
            <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
              <FileText className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-700 mb-1">No invoices found</h3>
            <p className="text-sm text-slate-500 max-w-sm">
              {statusFilter !== 'all' ? `No invoices with status "${statusFilter}". Try changing the filter.` : 'Invoices will appear here when sessions are created and approved.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {groupedByMonth.map((group) => (
              <Collapsible
                key={group.key}
                open={expandedMonths[group.key] !== false}
                onOpenChange={() => toggleMonth(group.key)}
                className="border rounded-lg overflow-hidden"
              >
                <CollapsibleTrigger className="w-full">
                  <div className="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100 transition-colors cursor-pointer">
                    <div className="flex items-center gap-3">
                      <Calendar className="w-5 h-5 text-blue-600" />
                      <h3 className="text-lg font-semibold text-gray-700">{group.label}</h3>
                      <Badge variant="outline" className="text-blue-600 border-blue-300">
                        {group.invoices.length} invoices
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="font-bold text-blue-700">
                        RM {group.total.toLocaleString('en-MY', { minimumFractionDigits: 2 })}
                      </span>
                      {expandedMonths[group.key] !== false ? (
                        <ChevronDown className="w-5 h-5 text-blue-500" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-blue-500" />
                      )}
                    </div>
                  </div>
                </CollapsibleTrigger>
                <CollapsibleContent>
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
                        {group.invoices.map((invoice) => (
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
                </CollapsibleContent>
              </Collapsible>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { InvoicesTab };
