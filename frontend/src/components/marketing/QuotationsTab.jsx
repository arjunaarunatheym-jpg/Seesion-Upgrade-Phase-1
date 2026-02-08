/**
 * QuotationsTab - Marketing quotation management
 */
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/card";
import { Button } from "../ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Plus, Eye, Edit, Send, Download, CheckCircle, XCircle, Percent } from "lucide-react";

const QuotationsTab = ({
  quotations,
  quotationFilter,
  setQuotationFilter,
  formatCurrency,
  getStatusBadge,
  onNewQuotation,
  onViewQuotation,
  onEditQuotation,
  onSubmitForApproval,
  onDownloadPdf,
  onMarkSent,
  onClientResponse,
  onApplyDiscount,
  downloadingPdf,
}) => {
  const filteredQuotations = quotationFilter === 'all' 
    ? quotations 
    : quotations.filter(q => q.status === quotationFilter);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <CardTitle className="text-lg sm:text-xl">Quotations</CardTitle>
            <CardDescription className="text-xs sm:text-sm">Manage your quotations</CardDescription>
          </div>
          <div className="flex gap-2 w-full sm:w-auto">
            <Select value={quotationFilter} onValueChange={setQuotationFilter}>
              <SelectTrigger className="w-full sm:w-40 text-xs sm:text-sm">
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="pending_approval">Pending</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
                <SelectItem value="sent">Sent</SelectItem>
                <SelectItem value="accepted">Accepted</SelectItem>
                <SelectItem value="declined">Declined</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={onNewQuotation} className="text-xs sm:text-sm whitespace-nowrap">
              <Plus className="w-3 h-3 sm:w-4 sm:h-4 mr-1" /> <span className="hidden sm:inline">New </span>Quotation
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-2 sm:px-6">
        <div className="overflow-x-auto -mx-2 sm:mx-0">
          <table className="w-full text-xs sm:text-sm min-w-[600px]">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left p-2 sm:p-3">Quote No</th>
                <th className="text-left p-2 sm:p-3">Client</th>
                <th className="text-left p-2 sm:p-3 hidden sm:table-cell">Programme</th>
                <th className="text-right p-2 sm:p-3">Amount</th>
                <th className="text-center p-2 sm:p-3">Status</th>
                <th className="text-center p-2 sm:p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredQuotations.map(q => (
                <tr key={q.id} className="border-b hover:bg-gray-50">
                  <td className="p-2 sm:p-3 font-medium text-xs">{q.quotation_number}</td>
                  <td className="p-2 sm:p-3 max-w-[100px] truncate">{q.client_name}</td>
                  <td className="p-2 sm:p-3 max-w-[150px] truncate hidden sm:table-cell">{q.programme_name}</td>
                  <td className="p-2 sm:p-3 text-right whitespace-nowrap">{formatCurrency(q.total_amount)}</td>
                  <td className="p-2 sm:p-3 text-center">{getStatusBadge(q.status)}</td>
                  <td className="p-2 sm:p-3">
                    <div className="flex justify-center gap-0.5 sm:gap-1">
                      <Button variant="ghost" size="sm" onClick={() => onViewQuotation(q.id)} title="View" className="h-7 w-7 sm:h-8 sm:w-8 p-0">
                        <Eye className="w-3 h-3 sm:w-4 sm:h-4" />
                      </Button>
                      
                      {q.status === 'draft' && (
                        <>
                          <Button variant="ghost" size="sm" onClick={() => onEditQuotation(q)} title="Edit" className="h-7 w-7 sm:h-8 sm:w-8 p-0">
                            <Edit className="w-3 h-3 sm:w-4 sm:h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => onSubmitForApproval(q.id)} title="Submit for Approval" className="text-yellow-600 h-7 w-7 sm:h-8 sm:w-8 p-0">
                            <Send className="w-3 h-3 sm:w-4 sm:h-4" />
                          </Button>
                        </>
                      )}
                      
                      {q.status === 'rejected' && (
                        <Button variant="ghost" size="sm" onClick={() => onEditQuotation(q)} title="Revise" className="h-7 w-7 sm:h-8 sm:w-8 p-0">
                          <Edit className="w-3 h-3 sm:w-4 sm:h-4" />
                        </Button>
                      )}
                      
                      {q.status === 'approved' && (
                        <>
                          <Button variant="ghost" size="sm" onClick={() => onDownloadPdf(q.id)} title="Download PDF" className="text-blue-600 h-7 w-7 sm:h-8 sm:w-8 p-0" disabled={downloadingPdf}>
                            <Download className="w-3 h-3 sm:w-4 sm:h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => onMarkSent(q.id)} title="Mark as Sent" className="text-green-600 h-7 w-7 sm:h-8 sm:w-8 p-0">
                            <Send className="w-3 h-3 sm:w-4 sm:h-4" />
                          </Button>
                        </>
                      )}
                      
                      {q.status === 'sent' && (
                        <>
                          <Button variant="ghost" size="sm" onClick={() => onDownloadPdf(q.id)} title="Download PDF" className="text-blue-600 h-7 w-7 sm:h-8 sm:w-8 p-0" disabled={downloadingPdf}>
                            <Download className="w-3 h-3 sm:w-4 sm:h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => onApplyDiscount(q)} title="Apply Discount" className="text-purple-600 h-7 w-7 sm:h-8 sm:w-8 p-0">
                            <Percent className="w-3 h-3 sm:w-4 sm:h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => onClientResponse(q.id, 'accepted')} title="Client Accepted" className="text-green-600 h-7 w-7 sm:h-8 sm:w-8 p-0">
                            <CheckCircle className="w-3 h-3 sm:w-4 sm:h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => onClientResponse(q.id, 'declined')} title="Client Declined" className="text-red-600 h-7 w-7 sm:h-8 sm:w-8 p-0">
                            <XCircle className="w-3 h-3 sm:w-4 sm:h-4" />
                          </Button>
                        </>
                      )}
                      
                      {q.status === 'accepted' && (
                        <Button variant="ghost" size="sm" onClick={() => onDownloadPdf(q.id)} title="Download Final PDF" className="text-emerald-600 h-7 w-7 sm:h-8 sm:w-8 p-0" disabled={downloadingPdf}>
                          <Download className="w-3 h-3 sm:w-4 sm:h-4" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {filteredQuotations.length === 0 && (
          <p className="text-center text-gray-500 py-6 sm:py-8 text-sm">No quotations found.</p>
        )}
      </CardContent>
    </Card>
  );
};

export { QuotationsTab };
