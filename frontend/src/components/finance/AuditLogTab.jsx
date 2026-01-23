/**
 * AuditLogTab Component - Extracted from FinanceDashboard
 * Displays audit history for finance-related actions
 */
import { useState } from "react";
import { axiosInstance } from "../../App";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RefreshCw } from "lucide-react";

const AuditLogTab = () => {
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      const response = await axiosInstance.get('/finance/audit-logs');
      setAuditLogs(response.data || []);
    } catch (error) {
      console.error('Failed to load audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <CardTitle>Audit Log</CardTitle>
          <Button variant="outline" onClick={loadAuditLogs} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Loading...' : 'Load Logs'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {auditLogs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>Click Load Logs to view audit history</p>
          </div>
        ) : (
          <div className="space-y-3">
            {auditLogs.map((log, idx) => (
              <div key={log.id || idx} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium">{log.action} - {log.entity_type}</p>
                    <p className="text-sm text-gray-500">By: {log.changed_by_name}</p>
                    {log.remark && <p className="text-sm text-gray-400">{log.remark}</p>}
                  </div>
                  <p className="text-xs text-gray-400">
                    {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { AuditLogTab };
