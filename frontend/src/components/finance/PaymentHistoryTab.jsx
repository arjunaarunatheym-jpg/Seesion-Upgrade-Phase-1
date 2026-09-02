/**
 * PaymentHistoryTab — Full searchable/filterable/paginated Payment History (READ-ONLY)
 * Phase 1: complements (does not replace) the "Recent Payments" widget.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  Search, Filter, ChevronLeft, ChevronRight, Download,
  Receipt as ReceiptIcon, Paperclip, RefreshCw, X, Eye,
} from "lucide-react";

const DEFAULT_PAGE_SIZE = 25;
const PAGE_SIZE_OPTIONS = [25, 50, 100];

const PAYMENT_METHOD_OPTIONS = [
  { value: "all", label: "All methods" },
  { value: "bank_transfer", label: "Bank Transfer" },
  { value: "cash", label: "Cash" },
  { value: "cheque", label: "Cheque" },
  { value: "online", label: "Online" },
  { value: "credit_card", label: "Credit Card" },
];

const FUNDING_OPTIONS = [
  { value: "all", label: "All funding" },
  { value: "self_pay", label: "Self Pay" },
  { value: "hrdcorp", label: "HRD Corp" },
  { value: "partial", label: "Partial" },
  { value: "other", label: "Other" },
];

const STATUS_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "reversed", label: "Reversed" },
  { value: "all", label: "All" },
];

const SORT_OPTIONS = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "highest", label: "Highest amount" },
  { value: "lowest", label: "Lowest amount" },
];

const fmtRM = (n) => `RM ${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const useDebouncedValue = (value, ms = 400) => {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
};

const PaymentHistoryTab = () => {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 400);

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("all");
  const [fundingSource, setFundingSource] = useState("all");
  const [status, setStatus] = useState("active");
  const [sort, setSort] = useState("newest");

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        q: debouncedSearch || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        payment_method: paymentMethod !== "all" ? paymentMethod : undefined,
        funding_source: fundingSource !== "all" ? fundingSource : undefined,
        status,
        sort,
        page,
        page_size: pageSize,
      };
      const { data } = await axiosInstance.get("/finance/payments/history", { params });
      setItems(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 0);
    } catch (e) {
      const msg = e?.response?.data?.detail || "Failed to load payment history";
      setError(msg);
      setItems([]);
      setTotal(0);
      setTotalPages(0);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, dateFrom, dateTo, paymentMethod, fundingSource, status, sort, page, pageSize]);

  // Reset to page 1 whenever any filter / search / sort changes
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, dateFrom, dateTo, paymentMethod, fundingSource, status, sort, pageSize]);

  useEffect(() => { load(); }, [load]);

  const clearFilters = () => {
    setSearch("");
    setDateFrom("");
    setDateTo("");
    setPaymentMethod("all");
    setFundingSource("all");
    setStatus("active");
    setSort("newest");
    setPage(1);
    setPageSize(DEFAULT_PAGE_SIZE);
  };

  const openDetail = async (payment) => {
    setDetail(null);
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const { data } = await axiosInstance.get(`/finance/payments/${payment.id}/detail`);
      setDetail(data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load payment detail");
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleViewProof = async (paymentId) => {
    try {
      const { data } = await axiosInstance.get(`/finance/payments/${paymentId}/proof`);
      if (data?.receipt_url) {
        const w = window.open("", "_blank");
        if (w) w.document.write(`<iframe src="${data.receipt_url}" style="width:100vw;height:100vh;border:none;"></iframe>`);
      } else {
        toast.info("No proof of payment uploaded");
      }
    } catch {
      toast.error("Failed to load proof of payment");
    }
  };

  const handleViewHrdInvoice = async (paymentId) => {
    try {
      const { data } = await axiosInstance.get(`/finance/payments/${paymentId}/hrdcorp-invoice`);
      if (data?.hrdcorp_invoice_url) {
        const w = window.open("", "_blank");
        if (w) w.document.write(`<iframe src="${data.hrdcorp_invoice_url}" style="width:100vw;height:100vh;border:none;"></iframe>`);
      } else {
        toast.info("No HRDCorp invoice uploaded");
      }
    } catch {
      toast.error("Failed to load HRDCorp invoice");
    }
  };

  const handleExportCsv = async () => {
    try {
      const params = {
        q: debouncedSearch || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        payment_method: paymentMethod !== "all" ? paymentMethod : undefined,
        funding_source: fundingSource !== "all" ? fundingSource : undefined,
        status,
        sort,
      };
      const response = await axiosInstance.get("/finance/payments/history/export", {
        params,
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "text/csv" }));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `payment-history-${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Export downloaded");
    } catch {
      toast.error("Failed to export payment history");
    }
  };

  const firstIdx = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastIdx = Math.min(page * pageSize, total);

  const pageNumbers = useMemo(() => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
    const pages = [1];
    if (page > 3) pages.push("…");
    for (let p = Math.max(2, page - 1); p <= Math.min(totalPages - 1, page + 1); p += 1) pages.push(p);
    if (page < totalPages - 2) pages.push("…");
    pages.push(totalPages);
    return pages;
  }, [page, totalPages]);

  return (
    <div className="space-y-4" data-testid="payment-history-page">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start flex-wrap gap-3">
            <div>
              <CardTitle>Payment History</CardTitle>
              <CardDescription>Search, filter and browse the full historical payment ledger. Read-only.</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={load} data-testid="ph-refresh-btn">
                <RefreshCw className="w-4 h-4 mr-1" /> Refresh
              </Button>
              <Button variant="outline" size="sm" onClick={handleExportCsv} data-testid="ph-export-btn">
                <Download className="w-4 h-4 mr-1" /> Export CSV
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Search + Filters */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
            <div className="md:col-span-6 relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <Input
                data-testid="ph-search-input"
                placeholder="Search receipt #, invoice #, client, reference or programme…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="md:col-span-3">
              <Select value={sort} onValueChange={setSort}>
                <SelectTrigger data-testid="ph-sort-select"><SelectValue placeholder="Sort" /></SelectTrigger>
                <SelectContent>
                  {SORT_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-3">
              <Select value={String(pageSize)} onValueChange={(v) => setPageSize(parseInt(v, 10))}>
                <SelectTrigger data-testid="ph-page-size-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PAGE_SIZE_OPTIONS.map((s) => <SelectItem key={s} value={String(s)}>{s} per page</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            <div>
              <Label className="text-xs text-gray-600">From date</Label>
              <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} data-testid="ph-date-from" />
            </div>
            <div>
              <Label className="text-xs text-gray-600">To date</Label>
              <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} data-testid="ph-date-to" />
            </div>
            <div>
              <Label className="text-xs text-gray-600">Payment method</Label>
              <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                <SelectTrigger data-testid="ph-method-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PAYMENT_METHOD_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-gray-600">Funding source</Label>
              <Select value={fundingSource} onValueChange={setFundingSource}>
                <SelectTrigger data-testid="ph-funding-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {FUNDING_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-gray-600">Status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger data-testid="ph-status-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-between items-center flex-wrap gap-2">
            <div className="text-xs text-gray-500">
              {loading
                ? "Loading…"
                : total === 0
                ? "No payments match the selected search or filters."
                : `Showing ${firstIdx}–${lastIdx} of ${total.toLocaleString()} payments`}
            </div>
            <Button variant="ghost" size="sm" onClick={clearFilters} data-testid="ph-clear-filters">
              <X className="w-3.5 h-3.5 mr-1" /> Clear filters
            </Button>
          </div>

          {/* Table */}
          <div className="overflow-x-auto border rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-700">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">Date</th>
                  <th className="text-left px-3 py-2 font-medium">Receipt #</th>
                  <th className="text-left px-3 py-2 font-medium">Client / Company</th>
                  <th className="text-left px-3 py-2 font-medium">Invoice #</th>
                  <th className="text-left px-3 py-2 font-medium">Programme</th>
                  <th className="text-left px-3 py-2 font-medium">Funding</th>
                  <th className="text-left px-3 py-2 font-medium">Method</th>
                  <th className="text-left px-3 py-2 font-medium">Reference</th>
                  <th className="text-right px-3 py-2 font-medium">Amount</th>
                  <th className="text-left px-3 py-2 font-medium">Status</th>
                  <th className="text-right px-3 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody data-testid="ph-table-body">
                {loading && (
                  Array.from({ length: Math.min(pageSize, 6) }).map((_, i) => (
                    <tr key={`sk-${i}`} className="border-t">
                      <td colSpan={11} className="px-3 py-3">
                        <div className="h-4 bg-gray-100 rounded animate-pulse" />
                      </td>
                    </tr>
                  ))
                )}
                {!loading && error && (
                  <tr>
                    <td colSpan={11} className="px-3 py-6 text-center text-red-600" data-testid="ph-error">
                      {error}
                    </td>
                  </tr>
                )}
                {!loading && !error && items.length === 0 && (
                  <tr>
                    <td colSpan={11} className="px-3 py-8 text-center text-gray-500" data-testid="ph-empty">
                      No payments match the selected search or filters.
                    </td>
                  </tr>
                )}
                {!loading && !error && items.map((p) => (
                  <tr key={p.id} className="border-t hover:bg-gray-50" data-testid={`ph-row-${p.id}`}>
                    <td className="px-3 py-2 whitespace-nowrap">{p.payment_date || "—"}</td>
                    <td className="px-3 py-2 whitespace-nowrap font-mono text-xs">{p.receipt_number || "—"}</td>
                    <td className="px-3 py-2">{p.company_name || "—"}</td>
                    <td className="px-3 py-2 whitespace-nowrap font-mono text-xs">{p.invoice_number || "—"}</td>
                    <td className="px-3 py-2">{p.programme_name || p.session_name || "—"}</td>
                    <td className="px-3 py-2">
                      {p.payment_type === "hrdcorp" ? (
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">HRD Corp</Badge>
                      ) : p.payment_type === "self_pay" ? (
                        <Badge variant="outline" className="bg-gray-50 text-gray-700">Self Pay</Badge>
                      ) : p.payment_type ? (
                        <Badge variant="outline">{p.payment_type}</Badge>
                      ) : "—"}
                    </td>
                    <td className="px-3 py-2 capitalize">{(p.payment_method || "—").replace(/_/g, " ")}</td>
                    <td className="px-3 py-2 text-xs">{p.reference_number || "—"}</td>
                    <td className="px-3 py-2 text-right font-medium">
                      <span className={p.status === "reversed" ? "text-red-500 line-through" : "text-green-700"}>
                        {fmtRM(p.amount)}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {p.status === "reversed"
                        ? <Badge className="bg-red-100 text-red-700 border-red-200" data-testid={`ph-status-reversed-${p.id}`}>Reversed</Badge>
                        : <Badge className="bg-green-100 text-green-700 border-green-200">Active</Badge>}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex justify-end gap-1">
                        {p.has_receipt && (
                          <Button variant="ghost" size="sm" title="View proof of payment" onClick={() => handleViewProof(p.id)} data-testid={`ph-view-proof-${p.id}`}>
                            <Paperclip className="w-4 h-4 text-green-600" />
                          </Button>
                        )}
                        {p.has_hrdcorp_invoice && (
                          <Button variant="ghost" size="sm" title="View HRDCorp invoice" onClick={() => handleViewHrdInvoice(p.id)} data-testid={`ph-view-hrd-${p.id}`}>
                            <Paperclip className="w-4 h-4 text-blue-600" />
                          </Button>
                        )}
                        <Button variant="ghost" size="sm" title="View detail" onClick={() => openDetail(p)} data-testid={`ph-view-detail-${p.id}`}>
                          <Eye className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 0 && (
            <div className="flex justify-between items-center flex-wrap gap-2 pt-1">
              <div className="text-xs text-gray-500">Page {page} of {totalPages}</div>
              <div className="flex gap-1 items-center">
                <Button
                  variant="outline" size="sm"
                  disabled={page <= 1 || loading}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  data-testid="ph-prev-page"
                >
                  <ChevronLeft className="w-4 h-4 mr-1" /> Previous
                </Button>
                {pageNumbers.map((n, idx) => (
                  n === "…" ? (
                    <span key={`e-${idx}`} className="px-2 text-gray-400">…</span>
                  ) : (
                    <Button
                      key={n}
                      variant={n === page ? "default" : "outline"}
                      size="sm"
                      className="min-w-[36px]"
                      onClick={() => setPage(n)}
                      data-testid={`ph-page-${n}`}
                    >
                      {n}
                    </Button>
                  )
                ))}
                <Button
                  variant="outline" size="sm"
                  disabled={page >= totalPages || loading}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  data-testid="ph-next-page"
                >
                  Next <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Payment Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Payment Detail</DialogTitle>
            <DialogDescription>Read-only historical record.</DialogDescription>
          </DialogHeader>
          {detailLoading || !detail ? (
            <div className="py-8 text-center text-gray-500" data-testid="ph-detail-loading">Loading…</div>
          ) : (
            <div className="space-y-4 text-sm" data-testid="ph-detail-body">
              <div className="grid grid-cols-2 gap-3">
                <div><span className="text-gray-500">Receipt #</span><div className="font-mono">{detail.payment?.receipt_number || "—"}</div></div>
                <div><span className="text-gray-500">Payment date</span><div>{detail.payment?.payment_date || "—"}</div></div>
                <div><span className="text-gray-500">Amount</span><div className="font-semibold">{fmtRM(detail.payment?.amount)}</div></div>
                <div><span className="text-gray-500">Method</span><div className="capitalize">{(detail.payment?.payment_method || "—").replace(/_/g, " ")}</div></div>
                <div><span className="text-gray-500">Reference #</span><div>{detail.payment?.reference_number || "—"}</div></div>
                <div><span className="text-gray-500">Funding source</span><div className="capitalize">{detail.payment?.payment_type || "—"}</div></div>
                <div><span className="text-gray-500">Client</span><div>{detail.invoice?.bill_to_name || detail.invoice?.company_name || "—"}</div></div>
                <div><span className="text-gray-500">Invoice #</span><div className="font-mono">{detail.invoice?.invoice_number || "—"}</div></div>
                <div><span className="text-gray-500">Programme</span><div>{detail.program?.name || detail.invoice?.session_name || detail.invoice?.programme_name || "—"}</div></div>
                <div><span className="text-gray-500">Session start</span><div>{detail.session?.start_date || "—"}</div></div>
                <div><span className="text-gray-500">Recorded by</span><div>{detail.recorded_by_name || "—"}</div></div>
                <div><span className="text-gray-500">Recorded at</span><div className="text-xs">{detail.payment?.created_at || "—"}</div></div>
              </div>
              {detail.payment?.notes && (
                <div>
                  <span className="text-gray-500 text-xs">Notes</span>
                  <div className="mt-1 p-2 bg-gray-50 rounded text-xs whitespace-pre-wrap">{detail.payment.notes}</div>
                </div>
              )}
              {detail.payment?.status === "reversed" && (
                <div className="p-3 rounded bg-red-50 border border-red-200 text-red-700 text-xs">
                  <strong>Reversed.</strong> {detail.payment?.reversal_reason || "This payment has been reversed."}
                </div>
              )}
              <div className="flex flex-wrap gap-2 pt-2 border-t">
                {detail.payment?.has_receipt && (
                  <Button variant="outline" size="sm" onClick={() => handleViewProof(detail.payment.id)} data-testid="ph-detail-view-proof">
                    <Paperclip className="w-4 h-4 mr-1" /> View proof of payment
                  </Button>
                )}
                {detail.payment?.has_hrdcorp_invoice && (
                  <Button variant="outline" size="sm" onClick={() => handleViewHrdInvoice(detail.payment.id)} data-testid="ph-detail-view-hrd">
                    <Paperclip className="w-4 h-4 mr-1" /> View HRDCorp invoice
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export { PaymentHistoryTab };
