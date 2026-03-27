import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { ExternalLink, CheckCircle, Clock, AlertCircle, UserCheck, UserX } from "lucide-react";

const statusColor = {
  paid: "bg-green-100 text-green-800",
  collected: "bg-green-100 text-green-800",
  issued: "bg-blue-100 text-blue-800",
  approved: "bg-blue-100 text-blue-800",
  pending: "bg-yellow-100 text-yellow-800",
  unpaid: "bg-red-100 text-red-800",
  active: "bg-emerald-100 text-emerald-800",
  completed: "bg-gray-100 text-gray-700",
  cancelled: "bg-red-100 text-red-700",
};

function InvoiceList({ items, onNavigate }) {
  if (!items?.length) return <p className="text-gray-400 text-center py-6">No invoices found</p>;
  const total = items.reduce((s, i) => s + (i.amount || 0), 0);
  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-2">{items.length} invoice(s) • Total: RM {total.toLocaleString("en-MY", { minimumFractionDigits: 2 })}</div>
      {items.map((inv) => (
        <div key={inv.id} className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 transition-colors" data-testid={`drilldown-item-${inv.id}`}>
          <div className="min-w-0 flex-1">
            <div className="font-medium text-sm truncate">{inv.invoice_number || "—"}</div>
            <div className="text-xs text-gray-500 truncate">{inv.company || "—"}</div>
            {inv.date && <div className="text-xs text-gray-400">{inv.date.substring(0, 10)}</div>}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 ml-3">
            <span className="font-semibold text-sm">RM {(inv.amount || 0).toLocaleString()}</span>
            <Badge className={`text-xs ${statusColor[inv.status] || "bg-gray-100 text-gray-700"}`}>{inv.status}</Badge>
          </div>
        </div>
      ))}
      {onNavigate && (
        <Button variant="outline" size="sm" className="w-full mt-2" onClick={onNavigate}>
          <ExternalLink className="w-3 h-3 mr-1" /> Open Finance Portal
        </Button>
      )}
    </div>
  );
}

function SessionList({ items }) {
  if (!items?.length) return <p className="text-gray-400 text-center py-6">No sessions found</p>;
  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-2">{items.length} session(s)</div>
      {items.map((s) => (
        <div key={s.id} className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50">
          <div className="min-w-0 flex-1">
            <div className="font-medium text-sm truncate">{s.program}</div>
            <div className="text-xs text-gray-500 truncate">{s.company}</div>
            <div className="text-xs text-gray-400">{s.start_date?.substring(0, 10)} → {s.end_date?.substring(0, 10)}</div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 ml-3">
            <span className="text-xs text-gray-500">{s.participants} pax</span>
            <Badge className={`text-xs ${statusColor[s.status] || "bg-gray-100"}`}>{s.status}</Badge>
          </div>
        </div>
      ))}
    </div>
  );
}

function PayablesList({ items }) {
  if (!items?.length) return <p className="text-gray-400 text-center py-6">No pending payables</p>;
  const total = items.reduce((s, p) => s + (p.nett_pay || 0), 0);
  const months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-2">{items.length} payable(s) • Total: RM {total.toLocaleString("en-MY", { minimumFractionDigits: 2 })}</div>
      {items.map((p) => (
        <div key={p.id} className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50">
          <div>
            <div className="font-medium text-sm">{p.staff_name || "—"}</div>
            <div className="text-xs text-gray-400">{months[p.month] || ""} {p.year}</div>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm">RM {(p.nett_pay || 0).toLocaleString()}</span>
            <Badge className="text-xs bg-red-100 text-red-700">{p.status}</Badge>
          </div>
        </div>
      ))}
    </div>
  );
}

function TraineeList({ items }) {
  if (!items?.length) return <p className="text-gray-400 text-center py-6">No trainees found</p>;
  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-2">{items.length} trainee(s)</div>
      {items.map((t, i) => (
        <div key={t.id || i} className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50">
          <div className="font-medium text-sm">{t.name || "—"}</div>
          <div className="text-xs text-gray-400">{t.nric || ""}</div>
        </div>
      ))}
    </div>
  );
}

function FeedbackList({ items }) {
  if (!items?.length) return <p className="text-gray-400 text-center py-6">No feedback found</p>;
  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-2">{items.length} response(s)</div>
      {items.map((f, i) => (
        <div key={i} className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50">
          <div>
            <div className="font-medium text-sm">{f.participant}</div>
            <div className="text-xs text-gray-400">{f.date?.substring(0, 10) || ""}</div>
          </div>
          <Badge className={`text-xs ${f.avg_score >= 4 ? "bg-green-100 text-green-800" : f.avg_score >= 3 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800"}`}>
            {f.avg_score}/5
          </Badge>
        </div>
      ))}
    </div>
  );
}

function TrainerList({ items }) {
  if (!items?.length) return <p className="text-gray-400 text-center py-6">No trainers found</p>;
  const assigned = items.filter(t => t.assigned).length;
  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-2">{assigned} of {items.length} trainers assigned this year</div>
      {items.map((t) => (
        <div key={t.id} className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50">
          <div className="flex items-center gap-2">
            {t.assigned ? <UserCheck className="w-4 h-4 text-green-600" /> : <UserX className="w-4 h-4 text-gray-400" />}
            <span className="font-medium text-sm">{t.name}</span>
          </div>
          <Badge className={`text-xs ${t.assigned ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-500"}`}>
            {t.assigned ? "Active" : "Unassigned"}
          </Badge>
        </div>
      ))}
    </div>
  );
}

function StaffList({ items }) {
  if (!items?.length) return <p className="text-gray-400 text-center py-6">No staff found</p>;
  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-2">{items.length} active staff</div>
      {items.map((s) => (
        <div key={s.id} className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50">
          <div>
            <div className="font-medium text-sm">{s.name}</div>
            <div className="text-xs text-gray-400">{s.email}</div>
          </div>
          <Badge className="text-xs bg-blue-100 text-blue-800 capitalize">{s.role?.replace("_", " ")}</Badge>
        </div>
      ))}
    </div>
  );
}

function QuotationList({ items }) {
  if (!items?.length) return <p className="text-gray-400 text-center py-6">No pending quotations</p>;
  return (
    <div className="space-y-2">
      <div className="text-xs text-gray-500 mb-2">{items.length} pending quotation(s)</div>
      {items.map((q) => (
        <div key={q.id} className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50">
          <div>
            <div className="font-medium text-sm">{q.quote_number || "—"}</div>
            <div className="text-xs text-gray-500">{q.company || "—"}</div>
          </div>
          <span className="font-semibold text-sm">RM {(q.amount || 0).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

export function KpiDrilldownDialog({ open, onClose, data, loading }) {
  if (!open) return null;
  const type = data?.type;
  const onNav = type === "invoices" ? () => window.open("/finance", "_blank") : null;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg" data-testid="kpi-drilldown-dialog">
        <DialogHeader>
          <DialogTitle className="text-base">{data?.title || "Details"}</DialogTitle>
          <DialogDescription>{loading ? "Loading..." : `${data?.items?.length || 0} items`}</DialogDescription>
        </DialogHeader>
        {loading ? (
          <div className="space-y-3 py-4">
            {[1,2,3].map(i => <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />)}
          </div>
        ) : (
          <div>
            {type === "invoices" && <InvoiceList items={data?.items} onNavigate={onNav} />}
            {type === "sessions" && <SessionList items={data?.items} />}
            {type === "payables" && <PayablesList items={data?.items} />}
            {type === "trainees" && <TraineeList items={data?.items} />}
            {type === "feedback" && <FeedbackList items={data?.items} />}
            {type === "trainers" && <TrainerList items={data?.items} />}
            {type === "staff" && <StaffList items={data?.items} />}
            {type === "quotations" && <QuotationList items={data?.items} />}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
