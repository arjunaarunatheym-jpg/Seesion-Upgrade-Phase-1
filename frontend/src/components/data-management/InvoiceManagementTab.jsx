/**
 * InvoiceManagementTab Component - Extracted from DataManagement
 * Handles invoice number editing, voiding, backdating, override, and deletion
 */
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { FileText, Hash, Calendar, Edit, Ban, RefreshCw, Trash2, Undo2 } from "lucide-react";

const InvoiceManagementTab = ({
  invoices,
  invoiceSearch,
  setInvoiceSearch,
  invoiceStatusFilter,
  setInvoiceStatusFilter,
  loading,
  loadInvoices,
  getInvoiceStatusBadge,
  setEditNumberForm,
  setEditNumberDialog,
  setBackdateForm,
  setBackdateDialog,
  setOverrideForm,
  setOverrideDialog,
  setEditPaidForm,
  setEditPaidDialog,
  setVoidForm,
  setVoidDialog,
  setDeleteForm,
  setDeleteDialog,
  setRevertForm,
  setRevertDialog,
}) => {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center flex-wrap gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Invoice Management
              </CardTitle>
              <CardDescription>Edit invoice numbers, void invoices, backdate, override validation, and delete</CardDescription>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Input
                placeholder="Search invoices..."
                value={invoiceSearch}
                onChange={(e) => setInvoiceSearch(e.target.value)}
                className="w-48"
              />
              <Select value={invoiceStatusFilter} onValueChange={setInvoiceStatusFilter}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="auto_draft">Draft</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="issued">Issued</SelectItem>
                  <SelectItem value="paid">Paid</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                  <SelectItem value="voided">Voided</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={loadInvoices} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {invoices.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">No invoices found.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice #</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => (
                  <TableRow key={invoice.id}>
                    <TableCell className="font-mono text-sm">{invoice.invoice_number}</TableCell>
                    <TableCell>{invoice.company_name}</TableCell>
                    <TableCell className="font-semibold">RM {invoice.total_amount?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                    <TableCell>{getInvoiceStatusBadge(invoice.status)}</TableCell>
                    <TableCell className="text-sm">{invoice.created_at ? new Date(invoice.created_at).toLocaleDateString() : "N/A"}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1 flex-wrap">
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Edit Invoice Number"
                          onClick={() => {
                            const parts = invoice.invoice_number?.split("/") || [];
                            setEditNumberForm({
                              year: parseInt(parts[2]) || new Date().getFullYear(),
                              month: parseInt(parts[3]) || new Date().getMonth() + 1,
                              sequence: parseInt(parts[4]) || 1,
                              reason: ""
                            });
                            setEditNumberDialog({ open: true, invoice });
                          }}
                        >
                          <Hash className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Backdate Invoice"
                          onClick={() => {
                            setBackdateForm({ newDate: "", reason: "" });
                            setBackdateDialog({ open: true, invoice });
                          }}
                        >
                          <Calendar className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Override Amount"
                          onClick={() => {
                            setOverrideForm({ totalAmount: invoice.total_amount, reason: "" });
                            setOverrideDialog({ open: true, invoice });
                          }}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        {invoice.status === "paid" && (
                          <Button
                            size="sm"
                            variant="ghost"
                            title="Edit Paid Invoice"
                            onClick={() => {
                              setEditPaidForm({
                                billToName: invoice.bill_to_name || "",
                                billToAddress: invoice.bill_to_address || "",
                                totalAmount: invoice.total_amount,
                                reason: ""
                              });
                              setEditPaidDialog({ open: true, invoice });
                            }}
                          >
                            <FileText className="h-4 w-4 text-blue-500" />
                          </Button>
                        )}
                        {invoice.status !== "voided" && invoice.status !== "cancelled" && (
                          <Button
                            size="sm"
                            variant="ghost"
                            title="Void Invoice"
                            onClick={() => {
                              setVoidForm({ reason: "" });
                              setVoidDialog({ open: true, invoice });
                            }}
                          >
                            <Ban className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                        {(invoice.status === "cancelled" || invoice.status === "voided") && (
                          <Button
                            size="sm"
                            variant="ghost"
                            title="Revert to Draft"
                            data-testid={`revert-invoice-${invoice.id}`}
                            onClick={() => {
                              setRevertForm({ targetStatus: "auto_draft", reason: "" });
                              setRevertDialog({ open: true, invoice });
                            }}
                          >
                            <Undo2 className="h-4 w-4 text-amber-600" />
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Delete Invoice"
                          onClick={() => {
                            setDeleteForm({ reason: "", reuseNumber: invoice.status === "auto_draft" || invoice.status === "draft" });
                            setDeleteDialog({ open: true, invoice });
                          }}
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export { InvoiceManagementTab };
