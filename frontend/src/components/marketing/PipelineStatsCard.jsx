/**
 * PipelineStatsCard - Quick stats for lead pipeline
 */
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { TrendingUp, DollarSign, Clock, Target, Users, AlertCircle } from "lucide-react";

const PipelineStatsCard = ({
  stats,
  reminders,
  formatCurrency,
  onViewReminders,
  isAdmin = false,
}) => {
  return (
    <div className="space-y-4">
      {/* Follow-up Reminders Alert */}
      {(reminders?.overdue_count > 0 || reminders?.upcoming_count > 0) && (
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-amber-600" />
                <div>
                  {reminders.overdue_count > 0 && (
                    <span className="text-amber-800 font-medium">
                      {reminders.overdue_count} overdue follow-up{reminders.overdue_count > 1 ? 's' : ''}
                    </span>
                  )}
                  {reminders.overdue_count > 0 && reminders.upcoming_count > 0 && <span className="mx-2">|</span>}
                  {reminders.upcoming_count > 0 && (
                    <span className="text-amber-700">
                      {reminders.upcoming_count} upcoming this week
                    </span>
                  )}
                </div>
              </div>
              <button 
                onClick={onViewReminders}
                className="text-sm text-amber-700 hover:text-amber-900 underline"
              >
                View all
              </button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Total Leads</p>
                <p className="text-2xl font-bold text-gray-900">{stats?.total_leads || 0}</p>
              </div>
              <Users className="w-8 h-8 text-gray-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Active</p>
                <p className="text-2xl font-bold text-blue-600">{stats?.active_leads || 0}</p>
              </div>
              <Target className="w-8 h-8 text-blue-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Conversion</p>
                <p className="text-2xl font-bold text-green-600">{stats?.conversion_rate || 0}%</p>
              </div>
              <TrendingUp className="w-8 h-8 text-green-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Avg Deal</p>
                <p className="text-lg font-bold text-emerald-600">{formatCurrency(stats?.avg_deal_size || 0)}</p>
              </div>
              <DollarSign className="w-8 h-8 text-emerald-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Avg Days</p>
                <p className="text-2xl font-bold text-purple-600">{stats?.avg_days_to_close || 0}</p>
              </div>
              <Clock className="w-8 h-8 text-purple-200" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500">Won Value</p>
                <p className="text-lg font-bold text-green-600">{formatCurrency(stats?.won_value || 0)}</p>
              </div>
              <DollarSign className="w-8 h-8 text-green-200" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Stage Breakdown */}
      {stats?.stage_counts && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Pipeline Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="bg-gray-50">
                Inquiry: {stats.stage_counts.inquiry || 0}
              </Badge>
              <Badge variant="outline" className="bg-blue-50 text-blue-700">
                Contacted: {stats.stage_counts.contacted || 0}
              </Badge>
              <Badge variant="outline" className="bg-purple-50 text-purple-700">
                Quotation Sent: {stats.stage_counts.quotation_sent || 0}
              </Badge>
              <Badge variant="outline" className="bg-yellow-50 text-yellow-700">
                Negotiating: {stats.stage_counts.negotiating || 0}
              </Badge>
              <Badge variant="outline" className="bg-green-50 text-green-700">
                Won: {stats.stage_counts.won || 0}
              </Badge>
              <Badge variant="outline" className="bg-red-50 text-red-700">
                Lost: {stats.stage_counts.lost || 0}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export { PipelineStatsCard };
