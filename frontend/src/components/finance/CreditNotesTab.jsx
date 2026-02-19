/**
 * CreditNotesTab Component - Extracted from FinanceDashboard
 * Manages credit notes (HRDCorp deductions, etc.)
 */
import { useState, useEffect } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { FileX, RefreshCw, Check, FileText, Printer, Download, Plus } from "lucide-react";

const CreditNotesTab = ({
  creditNotes,
  companySettings,
  onRefresh,
}) => {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [invoices, setInvoices] = useState([]);
  const [newCN, setNewCN] = useState({
    invoice_id: "",
    reason: "HRDCorp Levy Deduction",
    description: "",
    percentage: 4,
    amount: 0
  });
  const [selectedInvoice, setSelectedInvoice] = useState(null);

  // Fetch invoices for dropdown
  useEffect(() => {
    if (showCreateDialog) {
      axiosInstance.get("/finance/admin/invoices")
        .then(res => {
          // Only show issued/paid invoices
          const validInvoices = res.data.filter(inv => 
            inv.status === 'issued' || inv.status === 'paid' || inv.status === 'partial'
          );
          setInvoices(validInvoices);
        })
        .catch(err => console.error("Failed to fetch invoices:", err));
    }
  }, [showCreateDialog]);

  // Calculate amount when invoice or percentage changes
  useEffect(() => {
    if (selectedInvoice && newCN.percentage > 0) {
      const calcAmount = (selectedInvoice.total_amount * newCN.percentage) / 100;
      setNewCN(prev => ({ ...prev, amount: Math.round(calcAmount * 100) / 100 }));
    }
  }, [selectedInvoice, newCN.percentage]);

  const handleInvoiceSelect = (invoiceId) => {
    const invoice = invoices.find(inv => inv.id === invoiceId);
    setSelectedInvoice(invoice);
    setNewCN(prev => ({ ...prev, invoice_id: invoiceId }));
  };

  const handleCreateCN = async () => {
    if (!newCN.invoice_id) {
      toast.error("Please select an invoice");
      return;
    }
    if (newCN.amount <= 0) {
      toast.error("Amount must be greater than 0");
      return;
    }

    try {
      const payload = {
        invoice_id: newCN.invoice_id,
        reason: newCN.reason,
        description: newCN.description || `${newCN.percentage}% deduction`,
        percentage: newCN.percentage,
        amount: newCN.amount
      };
      
      await axiosInstance.post("/finance/credit-notes", payload);
      toast.success("Credit note created");
      setShowCreateDialog(false);
      setNewCN({ invoice_id: "", reason: "HRDCorp Levy Deduction", description: "", percentage: 4, amount: 0 });
      setSelectedInvoice(null);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create credit note");
    }
  };

  // API Handlers
  const handleApproveCN = async (cnId) => {
    try {
      await axiosInstance.post(`/finance/credit-notes/${cnId}/approve`);
      toast.success("Credit note approved");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to approve credit note");
    }
  };

  const handleIssueCN = async (cnId) => {
    try {
      await axiosInstance.post(`/finance/credit-notes/${cnId}/issue`);
      toast.success("Credit note issued");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to issue credit note");
    }
  };

  const handlePrintCreditNote = async (cn) => {
    try {
      const { printCreditNote } = await import('../../utils/printCreditNote');
      printCreditNote(cn, companySettings);
    } catch (error) {
      console.error("Print error:", error);
      toast.error("Failed to generate credit note PDF");
    }
  };

  return (
    <>
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FileX className="w-5 h-5 text-red-600" />
              Credit Notes
            </CardTitle>
            <CardDescription>Track deductions like HRDCorp levy - Status: Draft → Approved → Issued</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="default" onClick={() => setShowCreateDialog(true)} data-testid="create-credit-note-btn">
              <Plus className="w-4 h-4 mr-2" />
              Create Credit Note
            </Button>
            <Button variant="outline" onClick={onRefresh}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {creditNotes.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <FileX className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p>No credit notes yet</p>
            <p className="text-sm">Credit notes are created when recording payments with deductions, or manually using the button above</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">CN Number</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Date</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Invoice</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Company</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Reason</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Amount</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-500">Status</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {creditNotes.map((cn) => (
                  <tr key={cn.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-red-600">{cn.cn_number}</td>
                    <td className="px-4 py-3 text-sm">{cn.created_at ? new Date(cn.created_at).toLocaleDateString('en-MY') : '-'}</td>
                    <td className="px-4 py-3 text-sm">{cn.invoice_number || '-'}</td>
                    <td className="px-4 py-3 text-sm">{cn.company_name || '-'}</td>
                    <td className="px-4 py-3 text-sm">{cn.reason}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium text-red-600">- RM {cn.amount?.toLocaleString()}</td>
                    <td className="px-4 py-3 text-center">
                      <Badge className={
                        cn.status === 'issued' ? 'bg-green-500' : 
                        cn.status === 'approved' ? 'bg-blue-500' : 
                        'bg-yellow-500'
                      }>
                        {cn.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        {/* Approve Button - only for draft */}
                        {cn.status === 'draft' && (
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 px-2 text-blue-600 border-blue-300 hover:bg-blue-50"
                            onClick={() => handleApproveCN(cn.id)}
                            title="Approve"
                          >
                            <Check className="w-4 h-4" />
                          </Button>
                        )}
                        {/* Issue Button - for draft or approved */}
                        {(cn.status === 'draft' || cn.status === 'approved') && (
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 px-2 text-green-600 border-green-300 hover:bg-green-50"
                            onClick={() => handleIssueCN(cn.id)}
                            title="Issue"
                          >
                            <FileText className="w-4 h-4" />
                          </Button>
                        )}
                        {/* Print Button - always available */}
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="h-8 px-2"
                          onClick={() => handlePrintCreditNote(cn)}
                          title="Print"
                        >
                          <Printer className="w-4 h-4" />
                        </Button>
                        {/* Download/Export */}
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="h-8 px-2"
                          onClick={() => handlePrintCreditNote(cn)}
                          title="Download PDF"
                        >
                          <Download className="w-4 h-4" />
                        </Button>
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

    {/* Create Credit Note Dialog */}
    <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Create Credit Note</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div>
            <Label>Select Invoice *</Label>
            <Select value={newCN.invoice_id} onValueChange={handleInvoiceSelect}>
              <SelectTrigger data-testid="cn-invoice-select">
                <SelectValue placeholder="Select an invoice" />
              </SelectTrigger>
              <SelectContent>
                {invoices.map(inv => (
                  <SelectItem key={inv.id} value={inv.id}>
                    {inv.invoice_number} - {inv.company_name} (RM {inv.total_amount?.toLocaleString()})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedInvoice && (
            <div className="p-3 bg-gray-50 rounded text-sm">
              <p><strong>Invoice:</strong> {selectedInvoice.invoice_number}</p>
              <p><strong>Company:</strong> {selectedInvoice.company_name}</p>
              <p><strong>Amount:</strong> RM {selectedInvoice.total_amount?.toLocaleString()}</p>
            </div>
          )}

          <div>
            <Label>Reason</Label>
            <Select value={newCN.reason} onValueChange={(v) => setNewCN({...newCN, reason: v})}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="HRDCorp Levy Deduction">HRDCorp Levy Deduction</SelectItem>
                <SelectItem value="Discount">Discount</SelectItem>
                <SelectItem value="Adjustment">Adjustment</SelectItem>
                <SelectItem value="Other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label>Description (optional)</Label>
            <Textarea 
              value={newCN.description}
              onChange={(e) => setNewCN({...newCN, description: e.target.value})}
              placeholder="e.g., 4% levy deduction"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Percentage (%)</Label>
              <Input 
                type="number"
                value={newCN.percentage}
                onChange={(e) => setNewCN({...newCN, percentage: parseFloat(e.target.value) || 0})}
                min="0"
                max="100"
                step="0.5"
              />
            </div>
            <div>
              <Label>Amount (RM)</Label>
              <Input 
                type="number"
                value={newCN.amount}
                onChange={(e) => setNewCN({...newCN, amount: parseFloat(e.target.value) || 0})}
                min="0"
                step="0.01"
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateCN} data-testid="submit-credit-note-btn">Create Credit Note</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
};

export { CreditNotesTab };
