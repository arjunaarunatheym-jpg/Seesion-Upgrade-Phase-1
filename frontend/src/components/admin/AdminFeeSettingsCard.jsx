import { useEffect, useState } from 'react';
import { axiosInstance } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Percent, Save, Loader2, Info } from 'lucide-react';

export default function AdminFeeSettingsCard() {
  const [config, setConfig] = useState(null);
  const [recipients, setRecipients] = useState([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [c, r] = await Promise.all([
          axiosInstance.get('/admin-fee/config'),
          axiosInstance.get('/admin-fee/recipients'),
        ]);
        setConfig(c.data);
        setRecipients(r.data.recipients || []);
      } catch (e) {
        toast.error(e.response?.data?.detail || 'Failed to load admin fee config');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const save = async () => {
    if (!config) return;
    if (config.percentage < 0 || config.percentage > 100) {
      toast.error('Percentage must be between 0 and 100');
      return;
    }
    if (!config.recipient_id) {
      toast.error('Please select a recipient');
      return;
    }
    setSaving(true);
    try {
      const res = await axiosInstance.put('/admin-fee/config', {
        enabled: !!config.enabled,
        percentage: parseFloat(config.percentage),
        recipient_id: config.recipient_id,
        recipient_name: config.recipient_name,
        effective_from: config.effective_from,
      });
      setConfig(res.data.config);
      toast.success('Administration fee config saved');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6 flex items-center justify-center text-gray-500">
          <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading admin fee settings...
        </CardContent>
      </Card>
    );
  }

  if (!config) return null;

  return (
    <Card data-testid="admin-fee-settings-card" className="border-amber-200">
      <CardHeader className="bg-amber-50/60 border-b border-amber-100">
        <CardTitle className="flex items-center gap-2">
          <Percent className="w-5 h-5 text-amber-700" />
          Administration Fee
        </CardTitle>
        <CardDescription>
          A configurable percentage fee automatically added as a session expense and recorded as a payable to the selected marketing recipient. Applies only to sessions on or after the effective date.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-6 space-y-5">
        <div className="flex items-center justify-between p-3 rounded-lg border bg-gray-50">
          <div>
            <Label className="text-base">Enable Administration Fee</Label>
            <p className="text-xs text-gray-500">When off, no fees are auto-generated for any session.</p>
          </div>
          <Switch
            checked={!!config.enabled}
            onCheckedChange={(v) => setConfig({ ...config, enabled: v })}
            data-testid="admin-fee-enabled-switch"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label>Percentage (%)</Label>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={config.percentage ?? 0}
              onChange={(e) => setConfig({ ...config, percentage: e.target.value })}
              data-testid="admin-fee-percentage-input"
            />
            <p className="text-xs text-gray-500 mt-1">Applied to invoice subtotal (training fee + add-ons; before SST).</p>
          </div>
          <div>
            <Label>Effective From</Label>
            <Input
              type="date"
              value={config.effective_from || ''}
              onChange={(e) => setConfig({ ...config, effective_from: e.target.value })}
              data-testid="admin-fee-effective-date"
            />
            <p className="text-xs text-gray-500 mt-1">Only sessions with start date on/after this apply.</p>
          </div>
        </div>

        <div>
          <Label>Recipient (Marketing person to be paid)</Label>
          <Select
            value={config.recipient_id || ''}
            onValueChange={(v) => {
              const r = recipients.find((x) => x.id === v);
              setConfig({ ...config, recipient_id: v, recipient_name: r?.full_name });
            }}
          >
            <SelectTrigger data-testid="admin-fee-recipient-select">
              <SelectValue placeholder="Choose recipient" />
            </SelectTrigger>
            <SelectContent>
              {recipients.map((r) => (
                <SelectItem key={r.id} value={r.id}>
                  {r.full_name}  <span className="text-xs text-gray-400">({r.role})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-gray-500 mt-1">Only marketing-role users are listed. Default: Vighnesh Arunatheym.</p>
        </div>

        <div className="flex items-start gap-2 p-3 rounded-md bg-blue-50 border border-blue-100 text-sm">
          <Info className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-blue-800">
            <strong>How it works:</strong> Whenever you save session expenses or an invoice, the system recalculates the admin fee for that session.
            It only applies if the session start date is on or after the effective date. The fee appears as an auto-generated session expense
            AND a pending payable to the selected recipient (visible in marketing commissions). Per-session override available on the session expense screen.
          </div>
        </div>

        <div className="flex justify-end">
          <Button onClick={save} disabled={saving} className="bg-amber-600 hover:bg-amber-700" data-testid="save-admin-fee-btn">
            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
            Save Configuration
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
