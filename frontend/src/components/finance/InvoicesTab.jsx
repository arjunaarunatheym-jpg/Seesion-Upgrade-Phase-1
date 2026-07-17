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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { FileSpreadsheet, RefreshCw, Edit, Check, FileText, Download, CreditCard, X, RotateCcw, Plus, ChevronDown, ChevronRight, Calendar, Trash2 } from "lucide-react";
import ClaimFormPrint from "../ClaimFormPrint";

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
  const [claimFormSession, setClaimFormSession] = useState(null);

  // Ad-Hoc Invoice state
  const [showAdhocDialog, setShowAdhocDialog] = useState(false);
  const [adhocSubmitting, setAdhocSubmitting] = useState(false);
  const [adhocForm, setAdhocForm] = useState({
    bill_to_name: '',
    bill_to_address: '',
    bill_to_reg_no: '',
    contact_person: '',
    contact_email: '',
    contact_phone: '',
    your_reference: '',
    line_items: [{ description: '', quantity: 1, unit_price: 0 }],
    sst_percent: 0,
    discount: 0,
    rounding: 0,
    notes: '',
    invoice_date: new Date().toISOString().split('T')[0],
    due_date: '',
    reference_text: '',
  });

  const resetAdhocForm = () => {
    setAdhocForm({
      bill_to_name: '', bill_to_address: '', bill_to_reg_no: '',
      contact_person: '', contact_email: '', contact_phone: '', your_reference: '',
      line_items: [{ description: '', quantity: 1, unit_price: 0 }],
      sst_percent: 0, discount: 0, rounding: 0, notes: '',
      invoice_date: new Date().toISOString().split('T')[0], due_date: '',
      reference_text: '',
    });
  };

  const addLineItem = () => {
    setAdhocForm(prev => ({
      ...prev,
      line_items: [...prev.line_items, { description: '', quantity: 1, unit_price: 0 }]
    }));
  };

  const removeLineItem = (idx) => {
    if (adhocForm.line_items.length <= 1) return;
    setAdhocForm(prev => ({
      ...prev,
      line_items: prev.line_items.filter((_, i) => i !== idx)
    }));
  };

  const updateLineItem = (idx, field, value) => {
    setAdhocForm(prev => ({
      ...prev,
      line_items: prev.line_items.map((item, i) => i === idx ? { ...item, [field]: value } : item)
    }));
  };

  const adhocSubtotal = adhocForm.line_items.reduce((sum, item) => sum + (parseFloat(item.quantity) || 0) * (parseFloat(item.unit_price) || 0), 0);
  const adhocSst = adhocSubtotal * (parseFloat(adhocForm.sst_percent) || 0) / 100;
  const adhocTotal = adhocSubtotal + adhocSst - (parseFloat(adhocForm.discount) || 0) + (parseFloat(adhocForm.rounding) || 0);

  const handleCreateAdhocInvoice = async () => {
    if (!adhocForm.bill_to_name.trim()) { toast.error("Bill To name is required"); return; }
    if (!adhocForm.line_items.some(li => li.description.trim())) { toast.error("At least one line item description is required"); return; }
    
    setAdhocSubmitting(true);
    try {
      const payload = {
        ...adhocForm,
        line_items: adhocForm.line_items.filter(li => li.description.trim()).map(li => ({
          description: li.description,
          quantity: parseFloat(li.quantity) || 1,
          unit_price: parseFloat(li.unit_price) || 0,
          amount: (parseFloat(li.quantity) || 1) * (parseFloat(li.unit_price) || 0)
        })),
        sst_percent: parseFloat(adhocForm.sst_percent) || 0,
        discount: parseFloat(adhocForm.discount) || 0,
        rounding: parseFloat(adhocForm.rounding) || 0,
      };
      const res = await axiosInstance.post('/finance/invoices/adhoc', payload);
      toast.success(`Ad-hoc invoice ${res.data.invoice_number} created`);
      setShowAdhocDialog(false);
      resetAdhocForm();
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create invoice");
    } finally {
      setAdhocSubmitting(false);
    }
  };

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

  const handleConvertProforma = async (invoice) => {
    if (!confirm(
      `Convert proforma ${invoice.invoice_number} to a real Tax Invoice?\n\n` +
      `A new invoice will be created with a fresh INV/... number. ` +
      `The proforma will be marked as 'converted' and locked. Continue?`
    )) return;
    try {
      const res = await axiosInstance.post(`/finance/invoices/${invoice.id}/convert-to-invoice`);
      toast.success(`Converted to ${res.data.new_invoice_number}`);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to convert proforma");
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
      // Re-fetch invoice from API to guarantee fresh data (line_items, subtotal, etc.)
      const freshRes = await axiosInstance.get(`/finance/invoices`);
      const freshInvoice = (freshRes.data || []).find(i => i.id === invoice.id) || invoice;

      // Get app settings for logo
      const appSettings = await axiosInstance.get('/settings');
      const logoUrl = appSettings.data?.logo_url || companySettings?.logo_url;
      
      // Import and use print function
      const { printInvoice } = await import('../../utils/printInvoice');
      printInvoice(freshInvoice, companySettings, logoUrl);
    } catch (error) {
      console.error("Print error:", error);
      toast.error("Failed to generate invoice PDF");
    }
  };

  const handleDownloadSessionCosting = (invoice) => {
    if (!invoice.session_id) {
      toast.error("This invoice isn't linked to a session (e.g. Ad-Hoc invoice) — no costing report available.");
      return;
    }
    // Open the same ClaimFormPrint used in Admin Sessions tab so the layout is identical
    setClaimFormSession({ id: invoice.session_id, name: invoice.session_name || invoice.company_name || 'Session' });
  };

  return (
    <>
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center flex-wrap gap-4">
          <CardTitle>Invoice Management</CardTitle>
          <div className="flex gap-2 flex-wrap">
            <Button onClick={() => { resetAdhocForm(); setShowAdhocDialog(true); }} data-testid="create-adhoc-invoice-btn">
              <Plus className="w-4 h-4 mr-1" />
              Ad-Hoc Invoice
            </Button>
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
                            <td className="px-4 py-3 text-sm font-medium">
                              {invoice.invoice_number}
                              {invoice.invoice_type === 'adhoc' && (
                                <Badge className="ml-2 bg-indigo-100 text-indigo-700 text-[10px] px-1 py-0">Ad-Hoc</Badge>
                              )}
                              {invoice.document_type === 'proforma' && (
                                <Badge className="ml-2 bg-purple-100 text-purple-700 text-[10px] px-1 py-0" data-testid={`proforma-badge-${invoice.id}`}>PROFORMA</Badge>
                              )}
                              {invoice.converted_from_proforma_number && (
                                <span className="ml-2 text-[10px] text-gray-500">(from {invoice.converted_from_proforma_number})</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString('en-MY') : '-'}
                            </td>
                            <td className="px-4 py-3 text-sm">
                              {invoice.company_name || '-'}
                              {invoice.funding_source === 'hrdcorp' && (
                                <Badge className="ml-2 bg-blue-100 text-blue-700 text-[10px] px-1 py-0" data-testid={`funding-badge-${invoice.id}`}>HRDCORP</Badge>
                              )}
                              {invoice.funding_source === 'self_pay' && (
                                <Badge className="ml-2 bg-emerald-100 text-emerald-700 text-[10px] px-1 py-0" data-testid={`funding-badge-${invoice.id}`}>SELF PAY</Badge>
                              )}
                            </td>
                            <td className="px-4 py-3 text-sm">
                              {invoice.session_name || (invoice.reference_info?.text) || (invoice.invoice_type === 'adhoc' ? 'Ad-Hoc' : '-')}
                            </td>
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
                                
                                {/* Convert Proforma → Tax Invoice */}
                                {invoice.document_type === 'proforma' && invoice.status !== 'converted' && invoice.status !== 'cancelled' && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-purple-700"
                                    onClick={() => handleConvertProforma(invoice)}
                                    title="Convert to Tax Invoice"
                                    data-testid={`convert-proforma-${invoice.id}`}
                                  >
                                    <FileText className="w-4 h-4" />→
                                  </Button>
                                )}

                                {/* Download button for Proforma (any status) */}
                                {invoice.document_type === 'proforma' && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-purple-600"
                                    onClick={() => handlePrintInvoice(invoice)}
                                    title="Download Proforma"
                                    data-testid={`download-proforma-${invoice.id}`}
                                  >
                                    <Download className="w-4 h-4" />
                                  </Button>
                                )}

                                {/* Issue Button */}
                                {invoice.status === 'approved' && invoice.document_type !== 'proforma' && (
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
                                
                                {/* Session Costing / Claim Form — same layout as Admin Sessions tab */}
                                {invoice.session_id && (
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    className="text-teal-600"
                                    onClick={() => handleDownloadSessionCosting(invoice)}
                                    title="Download / Print Claim Form (Session Costing)"
                                    data-testid={`download-costing-${invoice.id}`}
                                  >
                                    <FileSpreadsheet className="w-4 h-4" />
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

      {/* Ad-Hoc Invoice Dialog */}
      <Dialog open={showAdhocDialog} onOpenChange={setShowAdhocDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5" />
              Create Ad-Hoc Invoice
            </DialogTitle>
            <DialogDescription>
              Create a standalone invoice not tied to a training session. Uses the same invoice numbering sequence.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Bill To Section */}
            <div className="bg-gray-50 p-4 rounded-lg space-y-3">
              <h4 className="font-semibold text-sm text-gray-700 uppercase tracking-wide">Bill To</h4>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <Label>Company Name <span className="text-red-500">*</span></Label>
                  <Input
                    value={adhocForm.bill_to_name}
                    onChange={(e) => setAdhocForm(p => ({ ...p, bill_to_name: e.target.value }))}
                    placeholder="Company name"
                    data-testid="adhoc-bill-to-name"
                  />
                </div>
                <div className="col-span-2">
                  <Label>Address</Label>
                  <Textarea
                    value={adhocForm.bill_to_address}
                    onChange={(e) => setAdhocForm(p => ({ ...p, bill_to_address: e.target.value }))}
                    placeholder="Full billing address"
                    rows={2}
                  />
                </div>
                <div>
                  <Label>Registration No</Label>
                  <Input
                    value={adhocForm.bill_to_reg_no}
                    onChange={(e) => setAdhocForm(p => ({ ...p, bill_to_reg_no: e.target.value }))}
                    placeholder="SSM / Company Reg No"
                  />
                </div>
                <div>
                  <Label>Contact Person</Label>
                  <Input
                    value={adhocForm.contact_person}
                    onChange={(e) => setAdhocForm(p => ({ ...p, contact_person: e.target.value }))}
                    placeholder="Attn: Name"
                  />
                </div>
                <div>
                  <Label>Email</Label>
                  <Input
                    value={adhocForm.contact_email}
                    onChange={(e) => setAdhocForm(p => ({ ...p, contact_email: e.target.value }))}
                    placeholder="billing@company.com"
                  />
                </div>
                <div>
                  <Label>Phone</Label>
                  <Input
                    value={adhocForm.contact_phone}
                    onChange={(e) => setAdhocForm(p => ({ ...p, contact_phone: e.target.value }))}
                    placeholder="+60..."
                  />
                </div>
              </div>
            </div>

            {/* Line Items */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-sm text-gray-700 uppercase tracking-wide">Line Items</h4>
                <Button size="sm" variant="outline" onClick={addLineItem}>
                  <Plus className="w-3 h-3 mr-1" /> Add Row
                </Button>
              </div>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-100">
                      <th className="px-3 py-2 text-left font-medium">Description</th>
                      <th className="px-3 py-2 text-right font-medium w-20">Qty</th>
                      <th className="px-3 py-2 text-right font-medium w-28">Unit Price</th>
                      <th className="px-3 py-2 text-right font-medium w-28">Amount</th>
                      <th className="w-10"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {adhocForm.line_items.map((item, idx) => (
                      <tr key={idx} className="border-t">
                        <td className="px-2 py-1">
                          <Input
                            value={item.description}
                            onChange={(e) => updateLineItem(idx, 'description', e.target.value)}
                            placeholder="Item description"
                            className="h-8 text-sm"
                            data-testid={`adhoc-line-desc-${idx}`}
                          />
                        </td>
                        <td className="px-2 py-1">
                          <Input
                            type="number"
                            value={item.quantity}
                            onChange={(e) => updateLineItem(idx, 'quantity', e.target.value)}
                            className="h-8 text-sm text-right"
                            min="0"
                            step="1"
                          />
                        </td>
                        <td className="px-2 py-1">
                          <Input
                            type="number"
                            value={item.unit_price}
                            onChange={(e) => updateLineItem(idx, 'unit_price', e.target.value)}
                            className="h-8 text-sm text-right"
                            min="0"
                            step="0.01"
                          />
                        </td>
                        <td className="px-3 py-1 text-right font-medium">
                          RM {((parseFloat(item.quantity) || 0) * (parseFloat(item.unit_price) || 0)).toLocaleString('en-MY', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-1 py-1">
                          {adhocForm.line_items.length > 1 && (
                            <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-500" onClick={() => removeLineItem(idx)}>
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Totals */}
              <div className="ml-auto w-64 space-y-1 text-sm">
                <div className="flex justify-between"><span>Subtotal:</span><span>RM {adhocSubtotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</span></div>
                <div className="flex justify-between items-center gap-2">
                  <span>SST (%):</span>
                  <Input
                    type="number"
                    value={adhocForm.sst_percent}
                    onChange={(e) => setAdhocForm(p => ({ ...p, sst_percent: e.target.value }))}
                    className="h-7 w-16 text-sm text-right"
                    min="0" max="100" step="0.5"
                  />
                  <span className="w-24 text-right">RM {adhocSst.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between items-center gap-2">
                  <span>Discount:</span>
                  <Input
                    type="number"
                    value={adhocForm.discount}
                    onChange={(e) => setAdhocForm(p => ({ ...p, discount: e.target.value }))}
                    className="h-7 w-16 text-sm text-right"
                    min="0" step="0.01"
                  />
                </div>
                <div className="flex justify-between items-center gap-2">
                  <span>Rounding:</span>
                  <Input
                    type="number"
                    value={adhocForm.rounding}
                    onChange={(e) => setAdhocForm(p => ({ ...p, rounding: e.target.value }))}
                    className="h-7 w-16 text-sm text-right"
                    step="0.01"
                  />
                </div>
                <div className="flex justify-between font-bold text-base border-t pt-1">
                  <span>TOTAL:</span>
                  <span>RM {adhocTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</span>
                </div>
              </div>
            </div>

            {/* Invoice Details */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Invoice Date</Label>
                <Input
                  type="date"
                  value={adhocForm.invoice_date}
                  onChange={(e) => setAdhocForm(p => ({ ...p, invoice_date: e.target.value }))}
                />
              </div>
              <div>
                <Label>Due Date</Label>
                <Input
                  type="date"
                  value={adhocForm.due_date}
                  onChange={(e) => setAdhocForm(p => ({ ...p, due_date: e.target.value }))}
                />
              </div>
              <div>
                <Label>Your Reference</Label>
                <Input
                  value={adhocForm.your_reference}
                  onChange={(e) => setAdhocForm(p => ({ ...p, your_reference: e.target.value }))}
                  placeholder="PO number, ref no, etc."
                />
              </div>
              <div>
                <Label>Reference (link to session/invoice)</Label>
                <Input
                  value={adhocForm.reference_text}
                  onChange={(e) => setAdhocForm(p => ({ ...p, reference_text: e.target.value }))}
                  placeholder="e.g., Balance for INV/MDDRC/2026/04/0001"
                />
              </div>
              <div className="col-span-2">
                <Label>Notes</Label>
                <Textarea
                  value={adhocForm.notes}
                  onChange={(e) => setAdhocForm(p => ({ ...p, notes: e.target.value }))}
                  placeholder="Internal notes or payment instructions..."
                  rows={2}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAdhocDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateAdhocInvoice} disabled={adhocSubmitting} data-testid="submit-adhoc-invoice">
              {adhocSubmitting ? 'Creating...' : `Create Invoice (RM ${adhocTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })})`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>

    {/* Session Costing / Claim Form modal — reuses the exact same component as Admin Sessions tab */}
    {claimFormSession && (
      <ClaimFormPrint
        session={claimFormSession}
        onClose={() => setClaimFormSession(null)}
      />
    )}
    </>
  );
};

export { InvoicesTab };
