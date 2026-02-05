/**
 * AdminMarketingOverview - Admin view of all marketing staff performance
 */
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/card";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { 
  Users, TrendingUp, DollarSign, Target, Award, ChevronDown, ChevronUp,
  AlertCircle, Calendar
} from "lucide-react";
import { toast } from "sonner";
import { axiosInstance } from "../../App";
import { LeadPipelineTab } from "./LeadPipelineTab";
import { PipelineStatsCard } from "./PipelineStatsCard";

const AdminMarketingOverview = ({ formatCurrency }) => {
  const [loading, setLoading] = useState(true);
  const [allLeads, setAllLeads] = useState([]);
  const [pipelineStats, setPipelineStats] = useState({});
  const [userStats, setUserStats] = useState({});
  const [reminders, setReminders] = useState({ overdue: [], upcoming: [], overdue_count: 0, upcoming_count: 0 });
  const [expandedUser, setExpandedUser] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [leadsRes, statsRes, userStatsRes, remindersRes] = await Promise.all([
        axiosInstance.get('/marketing/leads'),
        axiosInstance.get('/marketing/stats/pipeline'),
        axiosInstance.get('/marketing/stats/by-user'),
        axiosInstance.get('/marketing/leads/reminders/pending'),
      ]);
      
      setAllLeads(leadsRes.data || []);
      setPipelineStats(statsRes.data || {});
      setUserStats(userStatsRes.data || {});
      setReminders(remindersRes.data || { overdue: [], upcoming: [], overdue_count: 0, upcoming_count: 0 });
    } catch (error) {
      console.error('Failed to load marketing data:', error);
      toast.error('Failed to load marketing overview');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const userStatsList = Object.entries(userStats).map(([userId, stats]) => ({
    userId,
    ...stats
  })).sort((a, b) => b.won_value - a.won_value);

  return (
    <div className="space-y-6">
      {/* Overall Stats */}
      <PipelineStatsCard
        stats={pipelineStats}
        reminders={reminders}
        formatCurrency={formatCurrency}
        onViewReminders={() => {}}
        isAdmin={true}
      />

      {/* Staff Performance Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            Marketing Staff Performance
          </CardTitle>
          <CardDescription>
            View leads and performance by marketing team member
          </CardDescription>
        </CardHeader>
        <CardContent>
          {userStatsList.length === 0 ? (
            <p className="text-center py-8 text-gray-500">No marketing data yet</p>
          ) : (
            <div className="space-y-3">
              {userStatsList.map((user) => {
                const conversionRate = user.total > 0 
                  ? Math.round(((user.won || 0) / (user.won + user.lost || 1)) * 100) 
                  : 0;
                
                return (
                  <div key={user.userId} className="border rounded-lg overflow-hidden">
                    {/* User Summary Row */}
                    <div 
                      className="flex items-center justify-between p-4 bg-gray-50 cursor-pointer hover:bg-gray-100"
                      onClick={() => setExpandedUser(expandedUser === user.userId ? null : user.userId)}
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                          <span className="text-blue-700 font-bold">
                            {(user.user_name || 'U')[0].toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{user.user_name || 'Unknown'}</p>
                          <p className="text-sm text-gray-500">{user.total} total leads</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-6">
                        <div className="text-center">
                          <p className="text-xs text-gray-500">Active</p>
                          <p className="font-bold text-blue-600">{user.active}</p>
                        </div>
                        <div className="text-center">
                          <p className="text-xs text-gray-500">Won</p>
                          <p className="font-bold text-green-600">{user.won}</p>
                        </div>
                        <div className="text-center">
                          <p className="text-xs text-gray-500">Lost</p>
                          <p className="font-bold text-red-600">{user.lost}</p>
                        </div>
                        <div className="text-center">
                          <p className="text-xs text-gray-500">Conversion</p>
                          <p className="font-bold text-purple-600">{conversionRate}%</p>
                        </div>
                        <div className="text-center min-w-[100px]">
                          <p className="text-xs text-gray-500">Won Value</p>
                          <p className="font-bold text-emerald-600">{formatCurrency(user.won_value)}</p>
                        </div>
                        
                        {expandedUser === user.userId ? (
                          <ChevronUp className="w-5 h-5 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-gray-400" />
                        )}
                      </div>
                    </div>
                    
                    {/* Expanded Leads List */}
                    {expandedUser === user.userId && (
                      <div className="p-4 border-t bg-white">
                        <h4 className="font-medium mb-3 text-gray-700">Leads by {user.user_name}</h4>
                        <LeadPipelineTab
                          leads={allLeads.filter(l => l.created_by === user.userId)}
                          onRefresh={loadData}
                          formatCurrency={formatCurrency}
                          isAdmin={true}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* All Leads Pipeline (Admin View) */}
      <Card>
        <CardHeader>
          <CardTitle>All Leads Pipeline</CardTitle>
          <CardDescription>View and manage all leads across marketing team</CardDescription>
        </CardHeader>
        <CardContent>
          <LeadPipelineTab
            leads={allLeads}
            onRefresh={loadData}
            formatCurrency={formatCurrency}
            isAdmin={true}
          />
        </CardContent>
      </Card>
    </div>
  );
};

export { AdminMarketingOverview };
