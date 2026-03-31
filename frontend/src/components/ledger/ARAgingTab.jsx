import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Loader2, Download, AlertTriangle, Clock, CheckCircle } from 'lucide-react';
import { axiosInstance } from '../../App';

const BUCKET_LABELS = [
  { key: "current", label: "Current (0-30)", color: "bg-green-100 text-green-800 border-green-200" },
  { key: "days_31_60", label: "31-60 Days", color: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  { key: "days_61_90", label: "61-90 Days", color: "bg-orange-100 text-orange-800 border-orange-200" },
  { key: "days_91_120", label: "91-120 Days", color: "bg-red-100 text-red-800 border-red-200" },
  { key: "days_120_plus", label: "120+ Days", color: "bg-red-200 text-red-900 border-red-300" },
];

const fmt = (v) => `RM ${(v || 0).toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function ARAgingTab({ companySettings }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("summary"); // summary | detail | company

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await axiosInstance.get('/finance/ar-aging');
        setData(res.data);
      } catch { /* silent */ }
      setLoading(false);
    };
    load();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400 mr-2" /> Loading aging report...
        </CardContent>
      </Card>
    );
  }

  if (!data) return <Card><CardContent className="py-8 text-center text-gray-400">Failed to load AR Aging report</CardContent></Card>;

  const { summary, buckets, by_company, total_invoices } = data;

  const handleExport = () => {
    const rows = [["Invoice #", "Company", "Date", "Days Outstanding", "Amount", "Status"]];
    for (const bucket of BUCKET_LABELS) {
      for (const inv of (buckets[bucket.key] || [])) {
        rows.push([inv.invoice_number, inv.company, inv.date, inv.days_outstanding, inv.amount?.toFixed(2), inv.status]);
      }
    }
    const csv = rows.map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `ar_aging_${new Date().toISOString().slice(0,10)}.csv`; a.click();
  };

  return (
    <div className="space-y-4" data-testid="ar-aging-tab">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <CardTitle className="text-lg">Accounts Receivable Aging</CardTitle>
              <CardDescription>As of {new Date(data.as_of).toLocaleDateString('en-MY')} — {total_invoices} outstanding invoice(s)</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant={view === "summary" ? "default" : "outline"} size="sm" onClick={() => setView("summary")}>Summary</Button>
              <Button variant={view === "detail" ? "default" : "outline"} size="sm" onClick={() => setView("detail")}>By Invoice</Button>
              <Button variant={view === "company" ? "default" : "outline"} size="sm" onClick={() => setView("company")}>By Company</Button>
              <Button variant="outline" size="sm" onClick={handleExport}><Download className="w-3 h-3 mr-1" /> CSV</Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Summary Buckets */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            {BUCKET_LABELS.map(b => (
              <div key={b.key} className={`rounded-lg border p-3 ${b.color}`}>
                <div className="text-xs font-medium opacity-80">{b.label}</div>
                <div className="text-lg font-bold mt-1">{fmt(summary[b.key])}</div>
                <div className="text-xs opacity-60">{(buckets[b.key] || []).length} inv</div>
              </div>
            ))}
            <div className="rounded-lg border p-3 bg-gray-100 text-gray-800 border-gray-300">
              <div className="text-xs font-medium opacity-80">Total Outstanding</div>
              <div className="text-lg font-bold mt-1">{fmt(summary.total)}</div>
              <div className="text-xs opacity-60">{total_invoices} inv</div>
            </div>
          </div>

          {/* Detail View: By Invoice */}
          {view === "detail" && (
            <div className="space-y-4">
              {BUCKET_LABELS.map(b => {
                const items = buckets[b.key] || [];
                if (!items.length) return null;
                return (
                  <div key={b.key}>
                    <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <Badge className={b.color}>{b.label}</Badge>
                      <span className="text-gray-500">({items.length} invoices, {fmt(summary[b.key])})</span>
                    </h4>
                    <div className="border rounded-lg overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="text-left px-3 py-2 font-medium">Invoice #</th>
                            <th className="text-left px-3 py-2 font-medium">Company</th>
                            <th className="text-left px-3 py-2 font-medium">Date</th>
                            <th className="text-right px-3 py-2 font-medium">Days</th>
                            <th className="text-right px-3 py-2 font-medium">Amount</th>
                          </tr>
                        </thead>
                        <tbody>
                          {items.sort((a, b) => b.days_outstanding - a.days_outstanding).map(inv => (
                            <tr key={inv.id} className="border-t hover:bg-gray-50">
                              <td className="px-3 py-2 font-medium">{inv.invoice_number || "—"}</td>
                              <td className="px-3 py-2 text-gray-600 truncate max-w-[200px]">{inv.company}</td>
                              <td className="px-3 py-2 text-gray-500">{inv.date}</td>
                              <td className="px-3 py-2 text-right">{inv.days_outstanding}d</td>
                              <td className="px-3 py-2 text-right font-medium">{fmt(inv.amount)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })}
              {total_invoices === 0 && <p className="text-center text-gray-400 py-6">No outstanding invoices</p>}
            </div>
          )}

          {/* Summary View: Bar Visualization */}
          {view === "summary" && (
            <div className="space-y-3">
              {summary.total > 0 ? (
                <>
                  <div className="flex h-8 rounded-lg overflow-hidden border">
                    {BUCKET_LABELS.map(b => {
                      const pct = summary.total > 0 ? ((summary[b.key] || 0) / summary.total * 100) : 0;
                      if (pct === 0) return null;
                      const colors = { current: "bg-green-400", days_31_60: "bg-yellow-400", days_61_90: "bg-orange-400", days_91_120: "bg-red-400", days_120_plus: "bg-red-600" };
                      return <div key={b.key} className={`${colors[b.key]} flex items-center justify-center text-xs font-medium text-white`} style={{ width: `${pct}%` }} title={`${b.label}: ${fmt(summary[b.key])}`}>{pct >= 10 ? `${Math.round(pct)}%` : ""}</div>;
                    })}
                  </div>
                  <div className="flex flex-wrap gap-3 text-xs">
                    {BUCKET_LABELS.map(b => {
                      const colors = { current: "bg-green-400", days_31_60: "bg-yellow-400", days_61_90: "bg-orange-400", days_91_120: "bg-red-400", days_120_plus: "bg-red-600" };
                      return <div key={b.key} className="flex items-center gap-1"><span className={`w-3 h-3 rounded ${colors[b.key]}`} />{b.label}</div>;
                    })}
                  </div>
                  {(summary.days_91_120 > 0 || summary.days_120_plus > 0) && (
                    <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg mt-3">
                      <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                      <div className="text-sm text-red-800">
                        <span className="font-semibold">{fmt((summary.days_91_120 || 0) + (summary.days_120_plus || 0))}</span> is overdue by more than 90 days. Consider following up with these clients.
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex items-center justify-center gap-2 py-8 text-green-600">
                  <CheckCircle className="w-5 h-5" /> All invoices are paid. No outstanding receivables.
                </div>
              )}
            </div>
          )}

          {/* Company View */}
          {view === "company" && (
            <div>
              {Object.keys(by_company).length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium">Company</th>
                        <th className="text-right px-3 py-2 font-medium">Current</th>
                        <th className="text-right px-3 py-2 font-medium">31-60</th>
                        <th className="text-right px-3 py-2 font-medium">61-90</th>
                        <th className="text-right px-3 py-2 font-medium">91-120</th>
                        <th className="text-right px-3 py-2 font-medium">120+</th>
                        <th className="text-right px-3 py-2 font-medium">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(by_company).sort((a, b) => b[1].total - a[1].total).map(([company, data]) => (
                        <tr key={company} className="border-t hover:bg-gray-50">
                          <td className="px-3 py-2 font-medium truncate max-w-[200px]">{company}</td>
                          <td className="px-3 py-2 text-right">{data.current ? fmt(data.current) : "—"}</td>
                          <td className="px-3 py-2 text-right">{data.days_31_60 ? fmt(data.days_31_60) : "—"}</td>
                          <td className="px-3 py-2 text-right">{data.days_61_90 ? fmt(data.days_61_90) : "—"}</td>
                          <td className="px-3 py-2 text-right">{data.days_91_120 ? fmt(data.days_91_120) : "—"}</td>
                          <td className="px-3 py-2 text-right text-red-600 font-medium">{data.days_120_plus ? fmt(data.days_120_plus) : "—"}</td>
                          <td className="px-3 py-2 text-right font-bold">{fmt(data.total)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-gray-100 font-semibold">
                      <tr>
                        <td className="px-3 py-2">Total</td>
                        <td className="px-3 py-2 text-right">{fmt(summary.current)}</td>
                        <td className="px-3 py-2 text-right">{fmt(summary.days_31_60)}</td>
                        <td className="px-3 py-2 text-right">{fmt(summary.days_61_90)}</td>
                        <td className="px-3 py-2 text-right">{fmt(summary.days_91_120)}</td>
                        <td className="px-3 py-2 text-right">{fmt(summary.days_120_plus)}</td>
                        <td className="px-3 py-2 text-right">{fmt(summary.total)}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              ) : (
                <p className="text-center text-gray-400 py-6">No outstanding receivables</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
