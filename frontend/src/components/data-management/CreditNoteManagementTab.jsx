/**
 * CreditNoteManagementTab Component - Extracted from DataManagement
 * Handles credit note editing, backdating, voiding with audit trail
 */
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { Badge } from "../ui/badge";
import { FileText, Hash, Calendar, Edit, Ban, RefreshCw } from "lucide-react";

const CreditNoteManagementTab = ({
  creditNotes,
  cnSearch,
  setCnSearch,
  cnStatusFilter,
  setCnStatusFilter,
  loading,
  loadCreditNotes,
  setEditCnNumberForm,
  setEditCnNumberDialog,
  setBackdateCnForm,
  setBackdateCnDialog,
  setEditCnForm,
  setEditCnDialog,
  setVoidCnForm,
  setVoidCnDialog,
}) => {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center flex-wrap gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-red-600" />
                Credit Note Management
              </CardTitle>
              <CardDescription>Edit credit notes, backdate, void, and track changes with audit trail</CardDescription>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Input
                placeholder="Search CN..."
                value={cnSearch}
                onChange={(e) => setCnSearch(e.target.value)}
                className="w-48"
              />
              <Select value={cnStatusFilter} onValueChange={setCnStatusFilter}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="issued">Issued</SelectItem>
                  <SelectItem value="voided">Voided</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={loadCreditNotes} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {creditNotes.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">No credit notes found.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>CN Number</TableHead>
                  <TableHead>Invoice</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {creditNotes.map((cn) => (
                  <TableRow key={cn.id}>
                    <TableCell className="font-mono text-sm text-red-600">{cn.cn_number}</TableCell>
                    <TableCell className="text-sm">{cn.invoice_number || "-"}</TableCell>
                    <TableCell>{cn.company_name || "-"}</TableCell>
                    <TableCell className="font-semibold text-red-600">- RM {cn.amount?.toLocaleString('en-MY', { minimumFractionDigits: 2 })}</TableCell>
                    <TableCell>
                      <Badge className={
                        cn.status === 'voided' ? 'bg-gray-500' :
                        cn.status === 'issued' ? 'bg-green-500' : 
                        cn.status === 'approved' ? 'bg-blue-500' : 
                        'bg-yellow-500'
                      }>
                        {cn.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{cn.created_at ? new Date(cn.created_at).toLocaleDateString() : "N/A"}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1 flex-wrap">
                        {cn.status !== 'voided' && (
                          <>
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Edit CN Number"
                              onClick={() => {
                                const parts = cn.cn_number?.split("/") || [];
                                setEditCnNumberForm({
                                  year: parseInt(parts[2]) || new Date().getFullYear(),
                                  month: parseInt(parts[3]) || new Date().getMonth() + 1,
                                  sequence: parseInt(parts[4]) || 1,
                                  reason: ""
                                });
                                setEditCnNumberDialog({ open: true, cn });
                              }}
                            >
                              <Hash className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Backdate CN"
                              onClick={() => {
                                setBackdateCnForm({ newDate: "", reason: "" });
                                setBackdateCnDialog({ open: true, cn });
                              }}
                            >
                              <Calendar className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Edit Details"
                              onClick={() => {
                                setEditCnForm({
                                  companyName: cn.company_name || "",
                                  reason: cn.reason || "",
                                  description: cn.description || "",
                                  amount: cn.amount || 0,
                                  percentage: cn.percentage || 4,
                                  editReason: ""
                                });
                                setEditCnDialog({ open: true, cn });
                              }}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              title="Void CN"
                              className="text-red-600 hover:text-red-800"
                              onClick={() => {
                                setVoidCnForm({ reason: "" });
                                setVoidCnDialog({ open: true, cn });
                              }}
                            >
                              <Ban className="h-4 w-4" />
                            </Button>
                          </>
                        )}
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

export { CreditNoteManagementTab };
