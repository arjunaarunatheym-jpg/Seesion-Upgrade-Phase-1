import { useState, useEffect } from "react";
import { Card, CardContent } from "../components/ui/card";
import {
  Calendar,
  TrendingUp,
  AlertCircle,
  Users,
  Star,
  UserCheck,
  Briefcase,
  FileText,
} from "lucide-react";
import { axiosInstance } from "../App";

const KPI_CONFIG = [
  {
    key: "sessions_this_month",
    label: "Sessions This Month",
    icon: Calendar,
    color: "text-blue-600",
    bg: "bg-blue-50",
    format: "number",
  },
  {
    key: "revenue_ytd",
    label: "Revenue YTD",
    icon: TrendingUp,
    color: "text-emerald-600",
    bg: "bg-emerald-50",
    format: "currency",
  },
  {
    key: "outstanding_total",
    label: "Outstanding",
    icon: AlertCircle,
    color: "text-amber-600",
    bg: "bg-amber-50",
    format: "currency",
    subKey: "outstanding_count",
    subLabel: "invoices",
  },
  {
    key: "total_trainees_ytd",
    label: "Trainees YTD",
    icon: Users,
    color: "text-violet-600",
    bg: "bg-violet-50",
    format: "number",
  },
  {
    key: "avg_feedback_score",
    label: "Avg Feedback",
    icon: Star,
    color: "text-yellow-600",
    bg: "bg-yellow-50",
    format: "rating",
    subKey: "feedback_count",
    subLabel: "responses",
  },
  {
    key: "trainer_utilization",
    label: "Trainer Utilization",
    icon: UserCheck,
    color: "text-teal-600",
    bg: "bg-teal-50",
    format: "percent",
    subKey: "trainers_assigned",
    subLabel: "of",
    subKey2: "total_trainers",
    subLabel2: "trainers",
  },
  {
    key: "staff_count",
    label: "Active Staff",
    icon: Briefcase,
    color: "text-indigo-600",
    bg: "bg-indigo-50",
    format: "number",
  },
  {
    key: "pending_quotations",
    label: "Pending Quotes",
    icon: FileText,
    color: "text-orange-600",
    bg: "bg-orange-50",
    format: "number",
  },
];

function formatValue(value, format) {
  if (value === null || value === undefined) return "—";
  switch (format) {
    case "currency":
      return `RM ${Number(value).toLocaleString("en-MY", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    case "percent":
      return `${value}%`;
    case "rating":
      return value > 0 ? `${value}/5` : "N/A";
    default:
      return Number(value).toLocaleString();
  }
}

export function DashboardKPIs() {
  const [kpis, setKpis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchKPIs = async () => {
      try {
        const res = await axiosInstance.get("/admin/dashboard-kpis");
        setKpis(res.data);
      } catch (e) {
        console.error("Failed to fetch KPIs:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchKPIs();
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6" data-testid="kpi-loading">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="border rounded-lg p-4 space-y-2">
            <div className="h-4 w-20 bg-gray-200 animate-pulse rounded" />
            <div className="h-7 w-16 bg-gray-200 animate-pulse rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (!kpis) return null;

  return (
    <div className="mb-6" data-testid="dashboard-kpis">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
          Business Overview — {kpis.year}
        </h2>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {KPI_CONFIG.map((kpi) => {
          const Icon = kpi.icon;
          const value = kpis[kpi.key];
          return (
            <Card
              key={kpi.key}
              className="border border-gray-200 hover:shadow-md transition-shadow"
              data-testid={`kpi-${kpi.key}`}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-500 truncate">
                      {kpi.label}
                    </p>
                    <p className={`text-xl md:text-2xl font-bold mt-1 ${kpi.color}`}>
                      {formatValue(value, kpi.format)}
                    </p>
                    {kpi.subKey && kpis[kpi.subKey] !== undefined && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        {kpi.subKey2
                          ? `${kpis[kpi.subKey]} ${kpi.subLabel} ${kpis[kpi.subKey2]} ${kpi.subLabel2}`
                          : `${kpis[kpi.subKey]} ${kpi.subLabel}`}
                      </p>
                    )}
                  </div>
                  <div className={`p-2 rounded-lg ${kpi.bg} flex-shrink-0`}>
                    <Icon className={`w-4 h-4 ${kpi.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
