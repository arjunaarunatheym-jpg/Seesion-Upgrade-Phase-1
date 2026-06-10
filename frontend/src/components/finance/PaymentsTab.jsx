/**
 * PaymentsTab Component - Extracted from FinanceDashboard
 * Handles payment recording and recent payments listing
 */
import { useState } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { CreditCard, RefreshCw, Receipt, Paperclip, Image as ImageIcon, X } from "lucide-react";

const initialPaymentForm = {
  invoice_id: '',
  amount: '',
  payment_date: new Date().toISOString().split('T')[0],
  payment_method: 'bank_transfer',
  reference_number: '',
  notes: '',
  receipt_url: '',
  create_cn: false,
  cn_mode: 'percentage', // 'percentage' or 'amount'
  cn_percentage: '4',
  cn_amount: '',
  cn_reason: 'HRDCorp Levy Deduction'
};

const PaymentsTab = ({
  invoices,
  payments,
  companySettings,
  onRefresh,
  selectedInvoiceId,
}) => {
  const [paymentForm, setPaymentForm] = useState({
    ...initialPaymentForm,
    invoice_id: selectedInvoiceId || ''
  });

  // Filter pending invoices for payment
  const pendingInvoices = invoices.filter(inv => inv.status === 'issued');

  // Handle invoice selection and auto-fill amount
  const handleInvoiceSelect = (invoiceId) => {
    const invoice = invoices.find(inv => inv.id === invoiceId);
    if (invoice) {
      setPaymentForm({
        ...paymentForm,
        invoice_id: invoiceId,
        amount: invoice.total_amount || ''
      });
    } else {
      setPaymentForm({ ...paymentForm, invoice_id: invoiceId });
    }
  };

  // Record payment API call
  const handleRecordPayment = async () => {
    if (!paymentForm.invoice_id || !paymentForm.amount) {
      toast.error("Please select invoice and enter amount");
      return;
    }

    try {
      const response = await axiosInstance.post('/finance/payments', {
        invoice_id: paymentForm.invoice_id,
        amount: parseFloat(paymentForm.amount),
        payment_date: paymentForm.payment_date,
        payment_method: paymentForm.payment_method,
        reference_number: paymentForm.reference_number,
        notes: paymentForm.notes,
        receipt_url: paymentForm.receipt_url || null,
        create_credit_note: paymentForm.create_cn,
        deduction_percentage: paymentForm.create_cn && paymentForm.cn_mode === 'percentage' ? parseFloat(paymentForm.cn_percentage) : null,
        deduction_amount: paymentForm.create_cn && paymentForm.cn_mode === 'amount' ? parseFloat(paymentForm.cn_amount) : null,
        deduction_reason: paymentForm.create_cn ? paymentForm.cn_reason : null
      });
      
      if (response.data.credit_note) {
        toast.success(`Payment recorded & Credit Note ${response.data.credit_note.cn_number} created!`);
      } else {
        toast.success("Payment recorded successfully");
      }
      setPaymentForm(initialPaymentForm);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to record payment");
    }
  };

  // Print receipt
  const handlePrintReceipt = async (payment) => {
    try {
      const { printReceipt } = await import('../../utils/printReceipt');
      printReceipt(payment, companySettings, axiosInstance);
    } catch (error) {
      console.error("Print error:", error);
      toast.error("Failed to generate receipt");
    }
  };

  // Handle proof-of-payment file selection (base64-encode, max 5 MB)
  const handleProofFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
      toast.error("Only image or PDF files are allowed");
      e.target.value = '';
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error("File must be 5 MB or smaller");
      e.target.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setPaymentForm((prev) => ({ ...prev, receipt_url: reader.result }));
    };
    reader.onerror = () => toast.error("Failed to read file");
    reader.readAsDataURL(file);
  };

  // View an existing payment's proof in a new tab
  const handleViewProof = async (paymentId) => {
    try {
      const { data } = await axiosInstance.get(`/finance/payments/${paymentId}/proof`);
      if (!data?.receipt_url) {
        toast.info("No proof of payment uploaded for this payment");
        return;
      }
      const w = window.open();
      if (w) {
        w.document.write(`<title>Proof of Payment</title><body style="margin:0;background:#222;display:flex;align-items:center;justify-content:center;min-height:100vh;"><img src="${data.receipt_url}" style="max-width:100%;max-height:100vh;object-fit:contain"/></body>`);
      }
    } catch (e) {
      toast.error("Failed to load proof of payment");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Record Payment Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-green-600" />
            Record Payment
          </CardTitle>
          <CardDescription>Record payment received for an invoice</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Select Invoice (Pending Only)</Label>
            <Select value={paymentForm.invoice_id} onValueChange={handleInvoiceSelect}>
              <SelectTrigger>
                <SelectValue placeholder="Select an invoice to pay" />
              </SelectTrigger>
              <SelectContent>
                {pendingInvoices.length === 0 ? (
                  <SelectItem value="none" disabled>No pending invoices</SelectItem>
                ) : (
                  pendingInvoices.map(inv => (
                    <SelectItem key={inv.id} value={inv.id}>
                      {inv.invoice_number} - {inv.company_name || inv.session_name} (RM {inv.total_amount?.toLocaleString()})
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Payment Amount (RM)</Label>
              <Input 
                type="number" 
                value={paymentForm.amount}
                onChange={(e) => setPaymentForm({...paymentForm, amount: e.target.value})}
                placeholder="0.00"
              />
            </div>
            <div>
              <Label>Payment Date</Label>
              <Input 
                type="date" 
                value={paymentForm.payment_date}
                onChange={(e) => setPaymentForm({...paymentForm, payment_date: e.target.value})}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Payment Method</Label>
              <Select value={paymentForm.payment_method} onValueChange={(v) => setPaymentForm({...paymentForm, payment_method: v})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                  <SelectItem value="cheque">Cheque</SelectItem>
                  <SelectItem value="cash">Cash</SelectItem>
                  <SelectItem value="online">Online Payment</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Reference Number</Label>
              <Input 
                value={paymentForm.reference_number}
                onChange={(e) => setPaymentForm({...paymentForm, reference_number: e.target.value})}
                placeholder="Transaction ref"
              />
            </div>
          </div>
          
          <div>
            <Label>Notes (Optional)</Label>
            <Input 
              value={paymentForm.notes}
              onChange={(e) => setPaymentForm({...paymentForm, notes: e.target.value})}
              placeholder="Additional notes"
            />
          </div>

          {/* Proof of Payment Upload (Optional) */}
          <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 space-y-2" data-testid="proof-of-payment-section">
            <Label className="text-blue-800 font-medium flex items-center gap-2">
              <Paperclip className="w-4 h-4" /> Proof of Payment (Optional)
            </Label>
            {!paymentForm.receipt_url ? (
              <Input
                type="file"
                accept="image/*,application/pdf"
                onChange={handleProofFileChange}
                data-testid="proof-of-payment-input"
                className="bg-white"
              />
            ) : (
              <div className="flex items-center justify-between p-2 bg-white rounded border" data-testid="proof-of-payment-preview">
                <div className="flex items-center gap-2 text-sm text-gray-700 truncate">
                  <ImageIcon className="w-4 h-4 text-blue-600 shrink-0" />
                  {paymentForm.receipt_url.startsWith('data:application/pdf')
                    ? <span>PDF attached</span>
                    : <img src={paymentForm.receipt_url} alt="proof" className="h-12 w-12 object-cover rounded border" />}
                  <span className="text-xs text-gray-500">Attached</span>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setPaymentForm({ ...paymentForm, receipt_url: '' })}
                  data-testid="remove-proof-btn"
                >
                  <X className="w-4 h-4 text-red-600" />
                </Button>
              </div>
            )}
            <p className="text-xs text-blue-700">Upload bank transfer receipt, cheque image, or any proof (image or PDF, max 5MB).</p>
          </div>
          
          {/* Credit Note Option */}
          <div className="p-4 bg-red-50 rounded-lg border border-red-200 space-y-3">
            <div className="flex items-center gap-2">
              <input 
                type="checkbox" 
                id="create-cn"
                checked={paymentForm.create_cn}
                onChange={(e) => setPaymentForm({...paymentForm, create_cn: e.target.checked})}
              />
              <Label htmlFor="create-cn" className="text-red-700 font-medium">
                Create Credit Note (e.g., HRDCorp deduction)
              </Label>
            </div>
            {paymentForm.create_cn && (() => {
              const selectedInvoice = invoices.find(inv => inv.id === paymentForm.invoice_id);
              const invoiceTotal = selectedInvoice?.total_amount || 0;
              const calcAmount = paymentForm.cn_mode === 'percentage' 
                ? ((invoiceTotal * parseFloat(paymentForm.cn_percentage || 0)) / 100).toFixed(2)
                : parseFloat(paymentForm.cn_amount || 0).toFixed(2);
              const calcPct = paymentForm.cn_mode === 'amount' && invoiceTotal > 0
                ? ((parseFloat(paymentForm.cn_amount || 0) / invoiceTotal) * 100).toFixed(2)
                : paymentForm.cn_percentage;
              
              return (
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <Button 
                      type="button" size="sm" variant={paymentForm.cn_mode === 'percentage' ? 'default' : 'outline'}
                      onClick={() => setPaymentForm({...paymentForm, cn_mode: 'percentage'})}
                      className="text-xs"
                    >By Percentage (%)</Button>
                    <Button 
                      type="button" size="sm" variant={paymentForm.cn_mode === 'amount' ? 'default' : 'outline'}
                      onClick={() => setPaymentForm({...paymentForm, cn_mode: 'amount'})}
                      className="text-xs"
                    >By Amount (RM)</Button>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    {paymentForm.cn_mode === 'percentage' ? (
                      <div>
                        <Label className="text-sm">Deduction %</Label>
                        <Input 
                          type="number" 
                          value={paymentForm.cn_percentage}
                          onChange={(e) => setPaymentForm({...paymentForm, cn_percentage: e.target.value})}
                          placeholder="4"
                        />
                        {invoiceTotal > 0 && <p className="text-xs text-gray-500 mt-1">= RM {calcAmount}</p>}
                      </div>
                    ) : (
                      <div>
                        <Label className="text-sm">Deduction Amount (RM)</Label>
                        <Input 
                          type="number" 
                          value={paymentForm.cn_amount}
                          onChange={(e) => setPaymentForm({...paymentForm, cn_amount: e.target.value})}
                          placeholder="300"
                        />
                        {invoiceTotal > 0 && <p className="text-xs text-gray-500 mt-1">= {calcPct}% of RM {invoiceTotal.toLocaleString()}</p>}
                      </div>
                    )}
                    <div>
                      <Label className="text-sm">Reason</Label>
                      <Input 
                        value={paymentForm.cn_reason}
                        onChange={(e) => setPaymentForm({...paymentForm, cn_reason: e.target.value})}
                        placeholder="HRDCorp Levy"
                      />
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>
          
          <div className="flex gap-2">
            <Button onClick={handleRecordPayment} className="bg-green-600 hover:bg-green-700 flex-1">
              <CreditCard className="w-4 h-4 mr-2" />
              Record Payment
            </Button>
            <Button variant="outline" onClick={() => setPaymentForm(initialPaymentForm)}>
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent Payments */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Recent Payments</CardTitle>
            <Button variant="outline" size="sm" onClick={onRefresh}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {payments.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Receipt className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>No payments recorded yet</p>
              <Button variant="outline" size="sm" className="mt-2" onClick={onRefresh}>
                Load Payments
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {payments.slice(0, 10).map((payment) => (
                <div key={payment.id} className={`p-3 rounded-lg ${payment.status === 'reversed' ? 'bg-red-50 border border-red-200' : 'bg-gray-50'}`}>
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{payment.invoice_number}</p>
                        {payment.status === 'reversed' && (
                          <span className="px-2 py-0.5 text-xs font-bold bg-red-100 text-red-700 rounded" data-testid="reversed-badge">REVERSED</span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500">{payment.payment_date}</p>
                      {payment.status === 'reversed' && payment.reversal_reason && (
                        <p className="text-xs text-red-600 mt-1">Reason: {payment.reversal_reason}</p>
                      )}
                    </div>
                    <div className="text-right flex items-center gap-2">
                      <div>
                        <p className={`font-bold ${payment.status === 'reversed' ? 'text-red-400 line-through' : 'text-green-600'}`}>RM {payment.amount?.toLocaleString()}</p>
                        <p className="text-xs text-gray-500">{payment.payment_method}</p>
                      </div>
                      {payment.status !== 'reversed' && (
                        <>
                          {payment.receipt_url && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewProof(payment.id)}
                              title="View Proof of Payment"
                              data-testid={`view-proof-btn-${payment.id}`}
                            >
                              <Paperclip className="w-4 h-4 text-blue-600" />
                            </Button>
                          )}
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => handlePrintReceipt(payment)}
                            title="Print Receipt"
                          >
                            <Receipt className="w-4 h-4 text-purple-600" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export { PaymentsTab };
