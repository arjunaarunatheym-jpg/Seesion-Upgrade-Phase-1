import { useEffect, useMemo, useState } from 'react';
import { axiosInstance } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription
} from '../ui/dialog';
import { Checkbox } from '../ui/checkbox';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '../ui/table';
import { toast } from 'sonner';
import {
  Percent, Wallet, CheckCircle, Clock, Loader2, Eye, ChevronRight, BanknoteIcon, ListChecks
} from 'lucide-react';

const fmt = (n) => `RM ${Number(n || 0).toLocaleString('en-MY', { minimumFractionDigits: 2 })}`;

export default function AdminFeePayoutsPanel({ scope = 'auto' }) {
  // scope: 'auto' lets the backend decide (recipient sees own; admin sees all).
  const [summary, setSummary] = useState(null);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDetail, setShowDetail] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [paying, setPaying] = useState(false);
  const [paymentRef, setPaymentRef] = useState('');
  const [paymentNotes, setPaymentNotes] = useState('');
  const [filter, setFilter] = useState('pending'); // 'all', 'pending', 'paid'

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [sumRes, listRes] = await Promise.all([
        axiosInstance.get('/admin-fee/payouts/summary'),
        axiosInstance.get('/admin-fee/payouts'),
      ]);
      setSummary(sumRes.data);
      setRecords(listRes.data.records || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load admin fee payouts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const isAdminView = !!summary?.is_admin_view;

  const filteredRecords = useMemo(() => {
    if (filter === 'all') return records;
    return records.filter(r => r.status === filter);
  }, [records, filter]);

  const toggleSelect = (id) => {
    const s = new Set(selectedIds);
    if (s.has(id)) s.delete(id); else s.add(id);
    setSelectedIds(s);
  };

  const selectAllPending = () => {
    const allPending = filteredRecords.filter(r => r.status === 'pending').map(r => r.id);
    setSelectedIds(new Set(allPending));
  };

  const clearSelection = () => setSelectedIds(new Set());

  const selectedTotal = useMemo(() => {
    return filteredRecords
      .filter(r => selectedIds.has(r.id))
      .reduce((s, r) => s + Number(r.calculated_amount || 0), 0);
  }, [filteredRecords, selectedIds]);

  const bulkPay = async () => {
    if (selectedIds.size === 0) {
      toast.error('Select at least one record');
      return;
    }
    setPaying(true);
    try {
      const res = await axiosInstance.post('/admin-fee/payouts/bulk-pay', {
        record_ids: Array.from(selectedIds),
        payment_reference: paymentRef || undefined,
        notes: paymentNotes || undefined,
      });
      toast.success(`Paid ${res.data.modified_count} payouts (${fmt(res.data.total_amount)}) | Ref: ${res.data.payment_reference}`);
      clearSelection();
      setPaymentRef('');
      setPaymentNotes('');
      await fetchAll();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Bulk pay failed');
    } finally {
      setPaying(false);
    }
  };

  const markOnePaid = async (id) => {
    try {
      await axiosInstance.post(`/admin-fee/payouts/${id}/mark-paid`);
      toast.success('Marked as paid');
      await fetchAll();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed');
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6 flex items-center justify-center text-gray-500">
          <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading admin fee payouts...
        </CardContent>
      </Card>
    );
  }

  if (!summary) return null;

  return (
    <>
      <Card data-testid="admin-fee-payouts-card" className="border-amber-200">
        <CardHeader className="bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-100">
          <CardTitle className="flex items-center gap-2">
            <Percent className="w-5 h-5 text-amber-700" />
            {isAdminView ? 'Admin Fee Payouts' : 'My Pending Admin Fee Earnings'}
          </CardTitle>
          <CardDescription>
            {isAdminView
              ? 'All outstanding administration fee payouts across all recipients.'
              : 'Administration fee earnings owed to you from May 2026 onwards.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          {/* Summary tiles */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-lg border bg-amber-50/40 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase tracking-wide text-amber-700">Pending</span>
                <Clock className="w-4 h-4 text-amber-600" />
              </div>
              <div className="mt-2 text-2xl font-bold text-amber-800" data-testid="pending-total">{fmt(summary.pending_amount)}</div>
              <div className="text-xs text-amber-700/80">{summary.pending_count} sessions</div>
            </div>
            <div className="rounded-lg border bg-emerald-50/40 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase tracking-wide text-emerald-700">Paid</span>
                <CheckCircle className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="mt-2 text-2xl font-bold text-emerald-800">{fmt(summary.paid_amount)}</div>
              <div className="text-xs text-emerald-700/80">{summary.paid_count} sessions</div>
            </div>
            <div className="rounded-lg border bg-slate-50 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase tracking-wide text-slate-600">Lifetime</span>
                <Wallet className="w-4 h-4 text-slate-600" />
              </div>
              <div className="mt-2 text-2xl font-bold text-slate-800">{fmt(summary.pending_amount + summary.paid_amount)}</div>
              <div className="text-xs text-slate-600">{summary.pending_count + summary.paid_count} sessions total</div>
            </div>
          </div>

          {/* By recipient (admin only) */}
          {isAdminView && summary.by_recipient?.length > 0 && (
            <div>
              <h4 className="font-semibold text-sm text-gray-700 mb-2 flex items-center gap-1">
                <ListChecks className="w-4 h-4" /> Pending by Recipient
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {summary.by_recipient.filter(r => r.pending_amount > 0).map(r => (
                  <div key={r.recipient_id} className="flex items-center justify-between rounded-md border p-3 bg-white">
                    <div>
                      <div className="font-medium">{r.recipient_name || '(unknown)'}</div>
                      <div className="text-xs text-gray-500">{r.pending_count} pending sessions</div>
                    </div>
                    <div className="text-amber-700 font-bold">{fmt(r.pending_amount)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* By month */}
          {summary.by_month?.length > 0 && (
            <div>
              <h4 className="font-semibold text-sm text-gray-700 mb-2">Monthly Trend (most recent first)</h4>
              <div className="flex flex-wrap gap-2">
                {summary.by_month.slice(0, 6).map(m => (
                  <Badge key={m.month} variant="outline" className="px-3 py-1 text-xs">
                    {m.month} — {fmt(m.amount)} <span className="text-amber-600 ml-1">({fmt(m.pending_amount)} pending)</span>
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t">
            <Button variant="outline" onClick={() => { setFilter('pending'); setShowDetail(true); }} data-testid="view-breakdown-btn">
              <Eye className="w-4 h-4 mr-2" /> View Breakdown
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
            {isAdminView && summary.pending_count > 0 && (
              <Button
                onClick={() => { setFilter('pending'); setShowDetail(true); setTimeout(selectAllPending, 50); }}
                className="bg-amber-600 hover:bg-amber-700"
                data-testid="open-pay-all-btn"
              >
                <BanknoteIcon className="w-4 h-4 mr-2" /> Pay All Pending
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Detail dialog */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-5xl" data-testid="payouts-detail-dialog">
          <DialogHeader>
            <DialogTitle>Administration Fee Payouts</DialogTitle>
            <DialogDescription>
              {isAdminView
                ? 'Select payouts to pay in bulk, or mark them paid one by one.'
                : 'Full breakdown of your administration fee earnings.'}
            </DialogDescription>
          </DialogHeader>

          {/* Filter tabs */}
          <div className="flex items-center gap-2">
            {['pending', 'paid', 'all'].map(opt => (
              <Button
                key={opt}
                size="sm"
                variant={filter === opt ? 'default' : 'outline'}
                onClick={() => { setFilter(opt); clearSelection(); }}
                data-testid={`filter-${opt}`}
              >
                {opt[0].toUpperCase() + opt.slice(1)}
              </Button>
            ))}
            {isAdminView && filter === 'pending' && filteredRecords.length > 0 && (
              <Button size="sm" variant="ghost" onClick={selectAllPending}>Select All Pending</Button>
            )}
            {selectedIds.size > 0 && (
              <Button size="sm" variant="ghost" onClick={clearSelection}>Clear Selection ({selectedIds.size})</Button>
            )}
          </div>

          {/* Records table */}
          <div className="max-h-[55vh] overflow-auto border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  {isAdminView && <TableHead className="w-10"></TableHead>}
                  <TableHead>Session Start</TableHead>
                  <TableHead>Company</TableHead>
                  {isAdminView && <TableHead>Recipient</TableHead>}
                  <TableHead className="text-right">Rate</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Status</TableHead>
                  {isAdminView && <TableHead></TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRecords.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={isAdminView ? 8 : 5} className="text-center text-gray-500 py-6">
                      No records to display
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredRecords.map(r => (
                    <TableRow key={r.id} className={selectedIds.has(r.id) ? 'bg-amber-50' : ''}>
                      {isAdminView && (
                        <TableCell>
                          {r.status === 'pending' && (
                            <Checkbox
                              checked={selectedIds.has(r.id)}
                              onCheckedChange={() => toggleSelect(r.id)}
                              data-testid={`select-${r.id}`}
                            />
                          )}
                        </TableCell>
                      )}
                      <TableCell>{r.session_start_date || '-'}</TableCell>
                      <TableCell>{r.company_name || '-'}</TableCell>
                      {isAdminView && <TableCell>{r.marketing_user_name || '-'}</TableCell>}
                      <TableCell className="text-right">{r.commission_rate}%</TableCell>
                      <TableCell className="text-right font-medium">{fmt(r.calculated_amount)}</TableCell>
                      <TableCell>
                        {r.status === 'paid'
                          ? <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">Paid {r.paid_date || ''}</Badge>
                          : <Badge variant="outline" className="border-amber-300 text-amber-700">Pending</Badge>}
                      </TableCell>
                      {isAdminView && (
                        <TableCell>
                          {r.status === 'pending' && (
                            <Button size="sm" variant="ghost" onClick={() => markOnePaid(r.id)} data-testid={`pay-${r.id}`}>
                              Mark Paid
                            </Button>
                          )}
                        </TableCell>
                      )}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Bulk action footer */}
          {isAdminView && selectedIds.size > 0 && (
            <div className="border-t pt-4 space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">Payment Reference (optional)</Label>
                  <Input
                    placeholder="auto: ADMFEE-YYYYMMDD..."
                    value={paymentRef}
                    onChange={(e) => setPaymentRef(e.target.value)}
                    data-testid="payment-ref-input"
                  />
                </div>
                <div>
                  <Label className="text-xs">Notes (optional)</Label>
                  <Input
                    placeholder="e.g. May 2026 payout, cheque #4571"
                    value={paymentNotes}
                    onChange={(e) => setPaymentNotes(e.target.value)}
                    data-testid="payment-notes-input"
                  />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-sm">
                  Selected: <span className="font-bold">{selectedIds.size}</span> records ·
                  Total: <span className="font-bold text-amber-700">{fmt(selectedTotal)}</span>
                </div>
                <Button onClick={bulkPay} disabled={paying} className="bg-amber-600 hover:bg-amber-700" data-testid="confirm-bulk-pay-btn">
                  {paying ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <BanknoteIcon className="w-4 h-4 mr-2" />}
                  Pay {selectedIds.size} Selected ({fmt(selectedTotal)})
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
