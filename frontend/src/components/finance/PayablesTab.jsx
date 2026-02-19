/**
 * PayablesTab Component - Extracted from FinanceDashboard
 * Manages staff payables: trainer fees, coordinator fees, marketing commissions
 */
import { useState, useEffect } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Lock, Unlock, Download, Printer, RefreshCw, Check, ChevronDown, ChevronRight, Calendar } from "lucide-react";

const PayablesTab = ({
  payables,
  currentYear,
  onRefresh,
}) => {
  const [payablesMonth, setPayablesMonth] = useState(new Date().getMonth() + 1);
  const [payablesYear, setPayablesYear] = useState(currentYear);
  const [currentPeriodStatus, setCurrentPeriodStatus] = useState({ status: 'open', exists: false });
  
  // Track expanded month groups - all collapsed by default
  const [expandedGroups, setExpandedGroups] = useState({});
  const [reopenDialog, setReopenDialog] = useState({ open: false, reason: '' });

  // Load period status when month/year changes
  useEffect(() => {
    loadPeriodStatus();
  }, [payablesMonth, payablesYear]);

  // Load period status
  const loadPeriodStatus = async () => {
    try {
      const response = await axiosInstance.get(`/finance/payables/period-status?year=${payablesYear}&month=${payablesMonth}`);
      setCurrentPeriodStatus(response.data);
    } catch (error) {
      console.error("Failed to load period status:", error);
    }
  };

  // Toggle group expansion
  const toggleGroup = (groupKey) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupKey]: !prev[groupKey]
    }));
  };

  // Group payables by month
  const groupByMonth = (records) => {
    const groups = {};
    records.forEach(record => {
      const sessionDate = record.session_start_date || record.session_date;
      if (!sessionDate) return;
      const date = new Date(sessionDate);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      if (!groups[key]) {
        groups[key] = {
          key,
          label: date.toLocaleString('en', { month: 'long', year: 'numeric' }),
          records: [],
          total: 0
        };
      }
      groups[key].records.push(record);
      groups[key].total += record.fee_amount || record.total_fee || record.calculated_amount || 0;
    });
    return Object.values(groups).sort((a, b) => b.key.localeCompare(a.key));
  };

  // Filter records by selected month/year
  const filterByPeriod = (records) => {
    return records.filter(record => {
      const sessionDate = record.session_start_date || record.session_date;
      if (!sessionDate) return false;
      const d = new Date(sessionDate);
      return d.getFullYear() === payablesYear && (d.getMonth() + 1) === payablesMonth;
    });
  };

  // Calculate totals for summary cards
  const trainerTotal = filterByPeriod(payables.trainer_fees).reduce((sum, f) => sum + (f.fee_amount || 0), 0);
  const coordinatorTotal = filterByPeriod(payables.coordinator_fees).reduce((sum, f) => sum + (f.total_fee || 0), 0);
  const marketingTotal = filterByPeriod(payables.marketing_commissions).reduce((sum, f) => sum + (f.calculated_amount || 0), 0);

  // API Handlers
  const handleMarkPaid = async (type, id) => {
    if (currentPeriodStatus.status === 'closed') {
      toast.error('Cannot modify payables - period is closed');
      return;
    }
    try {
      await axiosInstance.post(`/finance/payables/${type}/${id}/mark-paid`);
      toast.success("Marked as paid");
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to mark as paid");
    }
  };

  const handleBulkMarkPaid = async (type, records) => {
    if (currentPeriodStatus.status === 'closed') {
      toast.error('Cannot modify payables - period is closed');
      return;
    }
    const unpaidRecords = records.filter(r => r.status !== 'paid');
    if (unpaidRecords.length === 0) return;
    
    try {
      await Promise.all(unpaidRecords.map(r => 
        axiosInstance.post(`/finance/payables/${type}/${r.id}/mark-paid`)
      ));
      toast.success(`${unpaidRecords.length} items marked as paid`);
      onRefresh();
    } catch (error) {
      toast.error("Failed to mark items as paid");
    }
  };

  const handleClosePeriod = async () => {
    try {
      // Always fetch fresh period status first
      const freshStatus = await axiosInstance.get(`/finance/payables/period-status?year=${payablesYear}&month=${payablesMonth}`);
      let periodId = freshStatus.data.period?.id;
      
      // If period doesn't exist, create it
      if (!freshStatus.data.exists) {
        const createRes = await axiosInstance.post('/finance/payables/periods', { year: payablesYear, month: payablesMonth });
        periodId = createRes.data.id;
      }
      
      // Now close the period
      if (periodId) {
        await axiosInstance.post(`/finance/payables/periods/${periodId}/close`);
        toast.success(`Period ${payablesYear}-${String(payablesMonth).padStart(2, '0')} closed successfully`);
        await loadPeriodStatus();
      } else {
        toast.error('Could not find or create period');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to close period");
    }
  };

  const handleReopenPeriod = () => {
    // Open dialog instead of using window.prompt
    setReopenDialog({ open: true, reason: '' });
  };

  const confirmReopenPeriod = async () => {
    if (!reopenDialog.reason || reopenDialog.reason.trim().length < 5) {
      toast.error('Reason must be at least 5 characters');
      return;
    }
    
    try {
      if (currentPeriodStatus.period?.id) {
        await axiosInstance.post(`/finance/payables/periods/${currentPeriodStatus.period.id}/reopen?reason=${encodeURIComponent(reopenDialog.reason)}`);
        toast.success('Period reopened successfully');
        setReopenDialog({ open: false, reason: '' });
        await loadPeriodStatus();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to reopen period");
    }
  };

  const handleExportPayablesExcel = async () => {
    try {
      // Get the backend URL from environment (React uses REACT_APP_ prefix)
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      
      // Get auth token from localStorage
      const token = localStorage.getItem('token');
      
      if (!token) {
        toast.error('Please login to download');
        return;
      }
      
      toast.info('Starting download...');
      
      // Create a hidden form to submit the download request
      // This bypasses CORS and triggers native browser download
      const downloadUrl = `${backendUrl}/api/finance/payables/download-excel?year=${payablesYear}&month=${payablesMonth}&token=${encodeURIComponent(token)}`;
      
      // Open in a new tab to trigger download
      const newWindow = window.open(downloadUrl, '_blank');
      
      // If popup was blocked, try alternate method
      if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
        // Fallback: use hidden iframe
        let iframe = document.getElementById('download-iframe');
        if (!iframe) {
          iframe = document.createElement('iframe');
          iframe.id = 'download-iframe';
          iframe.style.display = 'none';
          document.body.appendChild(iframe);
        }
        iframe.src = downloadUrl;
        toast.success('Download started - check your downloads folder');
      } else {
        toast.success('Download started in new tab');
        // Close the window after a short delay (for download)
        setTimeout(() => {
          try { newWindow.close(); } catch(e) {}
        }, 2000);
      }
    } catch (error) {
      console.error('Export error:', error);
      toast.error(error.message || "Failed to export payables");
    }
  };

  const handlePrintPayables = () => {
    window.print();
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center flex-wrap gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                Staff Payables
                {currentPeriodStatus.status === 'closed' && (
                  <Badge className="bg-red-500 text-white ml-2">CLOSED</Badge>
                )}
                {currentPeriodStatus.status === 'open' && (
                  <Badge className="bg-green-500 text-white ml-2">OPEN</Badge>
                )}
              </CardTitle>
              <CardDescription>
                Monthly closing: 1st-31st | Payment release: 15th of following month
              </CardDescription>
            </div>
            <div className="flex gap-2 flex-wrap items-center">
              {/* Month/Year Selector */}
              <Select value={payablesMonth.toString()} onValueChange={(val) => setPayablesMonth(parseInt(val))}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="Month" />
                </SelectTrigger>
                <SelectContent>
                  {[1,2,3,4,5,6,7,8,9,10,11,12].map(m => (
                    <SelectItem key={m} value={m.toString()}>
                      {new Date(2000, m-1).toLocaleString('en', {month: 'long'})}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={payablesYear.toString()} onValueChange={(val) => setPayablesYear(parseInt(val))}>
                <SelectTrigger className="w-[100px]">
                  <SelectValue placeholder="Year" />
                </SelectTrigger>
                <SelectContent>
                  {[currentYear, currentYear - 1, currentYear - 2].map(y => (
                    <SelectItem key={y} value={y.toString()}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              {/* Period Control */}
              {currentPeriodStatus.status === 'open' ? (
                <Button variant="outline" onClick={handleClosePeriod} className="border-red-300 text-red-600 hover:bg-red-50">
                  <Lock className="w-4 h-4 mr-2" />
                  Close Period
                </Button>
              ) : (
                <Button variant="outline" onClick={handleReopenPeriod} className="border-green-300 text-green-600 hover:bg-green-50">
                  <Unlock className="w-4 h-4 mr-2" />
                  Reopen
                </Button>
              )}
              
              {/* Export/Print */}
              <Button variant="outline" onClick={handleExportPayablesExcel} className="bg-green-50 border-green-300 text-green-700 hover:bg-green-100">
                <Download className="w-4 h-4 mr-2" />
                Excel
              </Button>
              <Button variant="outline" onClick={handlePrintPayables}>
                <Printer className="w-4 h-4 mr-2" />
                Print
              </Button>
              <Button variant="outline" onClick={onRefresh}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Period Status Banner */}
          {currentPeriodStatus.status === 'closed' && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
              <Lock className="w-5 h-5" />
              <span className="font-medium">Period {payablesYear}-{String(payablesMonth).padStart(2, '0')} is CLOSED.</span>
              <span className="text-sm">No changes allowed. Contact admin to reopen if needed.</span>
            </div>
          )}

          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="p-4">
                <p className="text-sm text-blue-700 font-medium">Trainer Fees</p>
                <p className="text-xl font-bold text-blue-900">
                  RM {trainerTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-blue-600">
                  {filterByPeriod(payables.trainer_fees).filter(f => f.status !== 'paid').length} pending / {filterByPeriod(payables.trainer_fees).length} total
                </p>
              </CardContent>
            </Card>
            <Card className="bg-green-50 border-green-200">
              <CardContent className="p-4">
                <p className="text-sm text-green-700 font-medium">Coordinator Fees</p>
                <p className="text-xl font-bold text-green-900">
                  RM {coordinatorTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-green-600">
                  {filterByPeriod(payables.coordinator_fees).filter(f => f.status !== 'paid').length} pending / {filterByPeriod(payables.coordinator_fees).length} total
                </p>
              </CardContent>
            </Card>
            <Card className="bg-purple-50 border-purple-200">
              <CardContent className="p-4">
                <p className="text-sm text-purple-700 font-medium">Marketing Commission</p>
                <p className="text-xl font-bold text-purple-900">
                  RM {marketingTotal.toLocaleString('en-MY', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-xs text-purple-600">
                  {filterByPeriod(payables.marketing_commissions).filter(f => f.status !== 'paid').length} pending / {filterByPeriod(payables.marketing_commissions).length} total
                </p>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="trainer" className="w-full">
            <TabsList className="mb-4">
              <TabsTrigger value="trainer">Trainers ({payables.trainer_fees.length})</TabsTrigger>
              <TabsTrigger value="coordinator">Coordinators ({payables.coordinator_fees.length})</TabsTrigger>
              <TabsTrigger value="marketing">Marketing ({payables.marketing_commissions.length})</TabsTrigger>
            </TabsList>

            {/* Trainer Fees Tab */}
            <TabsContent value="trainer">
              {payables.trainer_fees.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No trainer fees</p>
              ) : (
                <div className="space-y-3">
                  {groupByMonth(payables.trainer_fees).map(group => (
                    <Collapsible
                      key={group.key}
                      open={expandedGroups[`trainer-${group.key}`] === true}
                      onOpenChange={() => toggleGroup(`trainer-${group.key}`)}
                      className="border rounded-lg overflow-hidden"
                    >
                      <CollapsibleTrigger className="w-full">
                        <div className="bg-blue-100 px-4 py-3 flex justify-between items-center cursor-pointer hover:bg-blue-200 transition-colors">
                          <div className="flex items-center gap-3">
                            {expandedGroups[`trainer-${group.key}`] ? (
                              <ChevronDown className="w-5 h-5 text-blue-600" />
                            ) : (
                              <ChevronRight className="w-5 h-5 text-blue-600" />
                            )}
                            <Calendar className="w-5 h-5 text-blue-600" />
                            <div className="text-left">
                              <h4 className="font-semibold text-blue-900">{group.label}</h4>
                              <p className="text-sm text-blue-700">Total: RM {group.total.toLocaleString()} | {group.records.length} item(s)</p>
                            </div>
                          </div>
                          {group.records.some(r => r.status !== 'paid') && (
                            <Button 
                              size="sm" 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleBulkMarkPaid('trainer', group.records);
                              }}
                            >
                              <Check className="w-4 h-4 mr-1" />
                              Pay All ({group.records.filter(r => r.status !== 'paid').length})
                            </Button>
                          )}
                        </div>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="divide-y bg-white">
                          {group.records.map(fee => (
                            <div key={fee.id} className="p-3 flex justify-between items-center hover:bg-gray-50">
                              <div>
                                <p className="font-medium">{fee.trainer_name}</p>
                                <p className="text-sm text-gray-600">{fee.company_name || 'Unknown Company'}</p>
                                <p className="text-xs text-gray-500">Role: {fee.role || fee.trainer_role || 'Trainer'}</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <div className="text-right">
                                  <p className="font-bold">RM {(fee.fee_amount || 0).toLocaleString()}</p>
                                  <Badge className={fee.status === 'paid' ? 'bg-green-500' : 'bg-yellow-500'}>
                                    {fee.status || 'pending'}
                                  </Badge>
                                </div>
                                {fee.status !== 'paid' && (
                                  <Button size="sm" variant="outline" onClick={() => handleMarkPaid('trainer', fee.id)}>
                                    <Check className="w-4 h-4" />
                                  </Button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Coordinator Fees Tab */}
            <TabsContent value="coordinator">
              {payables.coordinator_fees.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No coordinator fees</p>
              ) : (
                <div className="space-y-3">
                  {groupByMonth(payables.coordinator_fees).map(group => (
                    <Collapsible
                      key={group.key}
                      open={expandedGroups[`coordinator-${group.key}`] === true}
                      onOpenChange={() => toggleGroup(`coordinator-${group.key}`)}
                      className="border rounded-lg overflow-hidden"
                    >
                      <CollapsibleTrigger className="w-full">
                        <div className="bg-green-100 px-4 py-3 flex justify-between items-center cursor-pointer hover:bg-green-200 transition-colors">
                          <div className="flex items-center gap-3">
                            {expandedGroups[`coordinator-${group.key}`] ? (
                              <ChevronDown className="w-5 h-5 text-green-600" />
                            ) : (
                              <ChevronRight className="w-5 h-5 text-green-600" />
                            )}
                            <Calendar className="w-5 h-5 text-green-600" />
                            <div className="text-left">
                              <h4 className="font-semibold text-green-900">{group.label}</h4>
                              <p className="text-sm text-green-700">Total: RM {group.total.toLocaleString()} | {group.records.length} item(s)</p>
                            </div>
                          </div>
                          {group.records.some(r => r.status !== 'paid') && (
                            <Button 
                              size="sm" 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleBulkMarkPaid('coordinator', group.records);
                              }}
                            >
                              <Check className="w-4 h-4 mr-1" />
                              Pay All ({group.records.filter(r => r.status !== 'paid').length})
                            </Button>
                          )}
                        </div>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="divide-y bg-white">
                          {group.records.map(fee => (
                            <div key={fee.id} className="p-3 flex justify-between items-center hover:bg-gray-50">
                              <div>
                                <p className="font-medium">{fee.coordinator_name}</p>
                                <p className="text-sm text-gray-600">{fee.company_name || 'Unknown Company'}</p>
                                <p className="text-xs text-gray-500">{fee.num_days || 1} day(s) × RM {fee.daily_rate || 0}</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <div className="text-right">
                                  <p className="font-bold">RM {(fee.total_fee || 0).toLocaleString()}</p>
                                  <Badge className={fee.status === 'paid' ? 'bg-green-500' : 'bg-yellow-500'}>
                                    {fee.status || 'pending'}
                                  </Badge>
                                </div>
                                {fee.status !== 'paid' && (
                                  <Button size="sm" variant="outline" onClick={() => handleMarkPaid('coordinator', fee.id)}>
                                    <Check className="w-4 h-4" />
                                  </Button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Marketing Commissions Tab */}
            <TabsContent value="marketing">
              {payables.marketing_commissions.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No marketing commissions</p>
              ) : (
                <div className="space-y-3">
                  {groupByMonth(payables.marketing_commissions).map(group => (
                    <Collapsible
                      key={group.key}
                      open={expandedGroups[`marketing-${group.key}`] === true}
                      onOpenChange={() => toggleGroup(`marketing-${group.key}`)}
                      className="border rounded-lg overflow-hidden"
                    >
                      <CollapsibleTrigger className="w-full">
                        <div className="bg-purple-100 px-4 py-3 flex justify-between items-center cursor-pointer hover:bg-purple-200 transition-colors">
                          <div className="flex items-center gap-3">
                            {expandedGroups[`marketing-${group.key}`] ? (
                              <ChevronDown className="w-5 h-5 text-purple-600" />
                            ) : (
                              <ChevronRight className="w-5 h-5 text-purple-600" />
                            )}
                            <Calendar className="w-5 h-5 text-purple-600" />
                            <div className="text-left">
                              <h4 className="font-semibold text-purple-900">{group.label}</h4>
                              <p className="text-sm text-purple-700">Total: RM {group.total.toLocaleString()} | {group.records.length} item(s)</p>
                            </div>
                          </div>
                          {group.records.some(r => r.status !== 'paid') && (
                            <Button 
                              size="sm" 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleBulkMarkPaid('marketing', group.records);
                              }}
                            >
                              <Check className="w-4 h-4 mr-1" />
                              Pay All ({group.records.filter(r => r.status !== 'paid').length})
                            </Button>
                          )}
                        </div>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="divide-y bg-white">
                          {group.records.map(comm => (
                            <div key={comm.id} className="p-3 flex justify-between items-center hover:bg-gray-50">
                              <div>
                                <p className="font-medium">{comm.marketing_user_name}</p>
                                <p className="text-sm text-gray-600">{comm.company_name || 'Unknown Company'}</p>
                                <p className="text-xs text-gray-500">{comm.commission_rate || 0}% commission</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <div className="text-right">
                                  <p className="font-bold">RM {(comm.calculated_amount || 0).toLocaleString()}</p>
                                  <Badge className={comm.status === 'paid' ? 'bg-green-500' : 'bg-yellow-500'}>
                                    {comm.status || 'pending'}
                                  </Badge>
                                </div>
                                {comm.status !== 'paid' && (
                                  <Button size="sm" variant="outline" onClick={() => handleMarkPaid('marketing', comm.id)}>
                                    <Check className="w-4 h-4" />
                                  </Button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Reopen Period Dialog */}
      <Dialog open={reopenDialog.open} onOpenChange={(open) => setReopenDialog({ ...reopenDialog, open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reopen Period</DialogTitle>
            <DialogDescription>
              Please provide a reason for reopening the period {payablesYear}-{String(payablesMonth).padStart(2, '0')}.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="reopen-reason">Reason (minimum 5 characters)</Label>
              <Input
                id="reopen-reason"
                value={reopenDialog.reason}
                onChange={(e) => setReopenDialog({ ...reopenDialog, reason: e.target.value })}
                placeholder="Enter reason for reopening..."
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setReopenDialog({ open: false, reason: '' })}>
                Cancel
              </Button>
              <Button onClick={confirmReopenPeriod}>
                Confirm Reopen
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export { PayablesTab };
