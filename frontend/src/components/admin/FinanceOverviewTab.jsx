/**
 * FinanceOverviewTab - Admin finance summary and quick access
 */
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Label } from "../ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { DollarSign } from "lucide-react";
import { axiosInstance } from "../../App";
import { toast } from "sonner";

const FinanceOverviewTab = ({
  financeYear,
  setFinanceYear,
  financeAvailableYears,
  financeSummary,
}) => {
  const handleRefresh = async () => {
    try {
      const response = await axiosInstance.get('/finance/dashboard');
      const data = response.data;
      document.getElementById('finance-total-invoices').textContent = data.invoices.total;
      document.getElementById('finance-collected').textContent = `RM ${data.financials.total_collected.toLocaleString()}`;
      document.getElementById('finance-outstanding').textContent = `RM ${data.financials.outstanding_receivables.toLocaleString()}`;
      document.getElementById('finance-payables').textContent = `RM ${data.payables.pending_total.toLocaleString()}`;
      toast.success('Finance data refreshed');
    } catch (error) {
      toast.error('Failed to load finance data');
    }
  };

  return (
    <div className="space-y-6">
      {/* Year Filter */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <Label className="text-sm font-medium text-gray-700">Financial Year:</Label>
          <Select value={financeYear?.toString()} onValueChange={(val) => setFinanceYear(parseInt(val))}>
            <SelectTrigger className="w-[140px]" data-testid="admin-year-selector">
              <SelectValue placeholder="Select Year" />
            </SelectTrigger>
            <SelectContent>
              {financeAvailableYears.map(year => (
                <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="text-sm text-gray-500">
          Showing data for <span className="font-semibold text-gray-800">{financeYear}</span>
        </div>
      </div>

      {/* Finance Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-blue-700">Total Invoices</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-900">
              <span id="finance-total-invoices">{financeSummary.invoiceCount || financeSummary.invoices?.length || 0}</span> (RM {(financeSummary.totalInvoiced || 0).toLocaleString()})
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-green-700">Total Collected</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-900" id="finance-collected">RM {(financeSummary.totalCollected || 0).toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-orange-700">Outstanding</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-900" id="finance-outstanding">RM {(financeSummary.totalOutstanding || 0).toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-purple-700">Pending Payables</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-900" id="finance-payables">RM {(financeSummary.totalPayables || 0).toLocaleString()}</div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Access to Full Finance Portal */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-green-600" />
            Finance Portal
          </CardTitle>
          <CardDescription>
            Access the full Finance Portal for invoice management, payments, and reports
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Button 
              className="bg-green-600 hover:bg-green-700"
              onClick={() => window.open('/finance', '_blank')}
            >
              <DollarSign className="w-4 h-4 mr-2" />
              Open Finance Portal
            </Button>
            <Button variant="outline" onClick={handleRefresh}>
              Refresh Data
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent Invoices Preview */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Invoices</CardTitle>
          <CardDescription>Latest invoices from training sessions</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500 text-center py-4">
            Open the Finance Portal to view and manage all invoices
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export { FinanceOverviewTab };
