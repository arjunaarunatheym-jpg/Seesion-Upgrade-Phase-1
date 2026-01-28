/**
 * DashboardTab - Marketing Dashboard overview with stats and quick actions
 */
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Building, Clock, CheckCircle, DollarSign, Plus, Eye } from "lucide-react";

const DashboardTab = ({
  stats,
  quotations,
  formatCurrency,
  getStatusBadge,
  onNewQuotation,
  onAddClient,
  onViewQuotation,
}) => {
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Clients</p>
                <p className="text-2xl font-bold text-blue-600">{stats.clients || 0}</p>
              </div>
              <Building className="w-8 h-8 text-blue-200" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Pending Approval</p>
                <p className="text-2xl font-bold text-yellow-600">{stats.pending_approval || 0}</p>
              </div>
              <Clock className="w-8 h-8 text-yellow-200" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Accepted</p>
                <p className="text-2xl font-bold text-green-600">{stats.accepted || 0}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-200" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Accepted Value</p>
                <p className="text-xl font-bold text-emerald-600">{formatCurrency(stats.total_accepted_value)}</p>
              </div>
              <DollarSign className="w-8 h-8 text-emerald-200" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-3">
          <Button onClick={onNewQuotation}>
            <Plus className="w-4 h-4 mr-2" /> New Quotation
          </Button>
          <Button variant="outline" onClick={onAddClient}>
            <Building className="w-4 h-4 mr-2" /> Add Client
          </Button>
        </CardContent>
      </Card>

      {/* Recent Quotations */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Quotations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {quotations.slice(0, 5).map(q => (
              <div key={q.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100">
                <div>
                  <p className="font-medium">{q.quotation_number}</p>
                  <p className="text-sm text-gray-600">{q.client_name} - {formatCurrency(q.total_amount)}</p>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge(q.status)}
                  <Button variant="ghost" size="sm" onClick={() => onViewQuotation(q.id)}>
                    <Eye className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
            {quotations.length === 0 && (
              <p className="text-center text-gray-500 py-8">No quotations yet. Create your first one!</p>
            )}
          </div>
        </CardContent>
      </Card>
    </>
  );
};

export { DashboardTab };
