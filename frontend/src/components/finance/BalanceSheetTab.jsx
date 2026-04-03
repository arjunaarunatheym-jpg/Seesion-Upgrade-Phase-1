import React, { useState, useEffect, useCallback } from 'react';
import { axiosInstance } from '../../App';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { Download, Printer, ChevronDown, ChevronRight, CheckCircle, AlertTriangle } from 'lucide-react';

const fmtRM = (v) => {
  const n = Number(v) || 0;
  return `RM ${n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const fmtDate = (d) => {
  if (!d) return '-';
  try { return new Date(d + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }); } catch { return d; }
};

const AccountRow = ({ account, indent = false }) => (
  <tr className="border-b border-gray-100 hover:bg-gray-50/50">
    <td className={`py-2.5 px-4 text-sm text-gray-600 ${indent ? 'pl-10' : 'pl-4'}`}>{account.account_code}</td>
    <td className={`py-2.5 px-4 text-sm text-gray-900 ${indent ? 'pl-10' : 'pl-4'}`}>{account.account_name}</td>
    <td className="py-2.5 px-4 text-sm text-right font-medium tabular-nums">
      <span className={account.balance < 0 ? 'text-red-600' : 'text-gray-900'}>{fmtRM(account.balance)}</span>
    </td>
  </tr>
);

const SectionHeader = ({ title, total, expanded, onToggle }) => (
  <tr className="bg-gray-50 cursor-pointer" onClick={onToggle}>
    <td colSpan={2} className="py-3 px-4 font-semibold text-gray-900 text-sm">
      <span className="flex items-center gap-2">
        {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        {title}
      </span>
    </td>
    <td className="py-3 px-4 text-right font-bold text-sm tabular-nums">{fmtRM(total)}</td>
  </tr>
);

const SubSectionHeader = ({ title }) => (
  <tr>
    <td colSpan={3} className="py-2 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider bg-gray-50/50">{title}</td>
  </tr>
);

export const BalanceSheetTab = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [asAt, setAsAt] = useState(new Date().toISOString().split('T')[0]);
  const [expandedSections, setExpandedSections] = useState({ assets: true, liabilities: true, equity: true });

  const toggleSection = (s) => setExpandedSections(prev => ({ ...prev, [s]: !prev[s] }));

  const loadBalanceSheet = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axiosInstance.get(`/finance/balance-sheet?as_at=${asAt}`);
      setData(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to load Balance Sheet');
    } finally { setLoading(false); }
  }, [asAt]);

  useEffect(() => { loadBalanceSheet(); }, [loadBalanceSheet]);

  const handlePrint = () => {
    if (!data) return;
    const s = data.summary;
    const renderRows = (accounts) => accounts.map(a =>
      `<tr><td style="padding:6px 12px;font-size:13px;color:#555">${a.account_code}</td><td style="padding:6px 12px;font-size:13px">${a.account_name}</td><td style="padding:6px 12px;text-align:right;font-weight:500;font-variant-numeric:tabular-nums">${fmtRM(a.balance)}</td></tr>`
    ).join('');

    const sectionBlock = (title, items, total) => `
      <tr style="background:#f8f9fa"><td colspan="2" style="padding:10px 12px;font-weight:700;font-size:14px">${title}</td><td style="padding:10px 12px;text-align:right;font-weight:700">${fmtRM(total)}</td></tr>
      ${renderRows(items)}
    `;

    const html = `<!DOCTYPE html><html><head><title>Balance Sheet - ${data.period}</title>
      <style>body{font-family:'Segoe UI',Tahoma,sans-serif;margin:40px}table{width:100%;border-collapse:collapse}th{text-align:left;padding:8px 12px;border-bottom:2px solid #333;font-size:12px;text-transform:uppercase;color:#666}td{border-bottom:1px solid #eee}.total-row td{border-top:2px solid #333;font-weight:700;padding:10px 12px}h1{font-size:22px;margin-bottom:4px}h2{font-size:14px;color:#666;margin-bottom:24px}.balanced{color:#16a34a;font-weight:700}.unbalanced{color:#dc2626;font-weight:700}@media print{body{margin:20px}}</style>
    </head><body>
      <h1>Balance Sheet</h1>
      <h2>${data.period}</h2>
      <table>
        <thead><tr><th>Code</th><th>Account</th><th style="text-align:right">Amount</th></tr></thead>
        <tbody>
          ${sectionBlock('ASSETS', [...(data.assets.current || []), ...(data.assets.non_current || [])], data.assets.total)}
          <tr class="total-row"><td colspan="2" style="padding:10px 12px">Total Assets</td><td style="text-align:right;padding:10px 12px">${fmtRM(s.total_assets)}</td></tr>
          ${sectionBlock('LIABILITIES', [...(data.liabilities.current || []), ...(data.liabilities.non_current || [])], data.liabilities.total)}
          ${sectionBlock('EQUITY', data.equity.accounts || [], data.equity.total)}
          <tr class="total-row"><td colspan="2" style="padding:10px 12px">Total Liabilities + Equity</td><td style="text-align:right;padding:10px 12px">${fmtRM(s.total_liabilities_equity)}</td></tr>
          <tr><td colspan="2" style="padding:10px 12px;font-weight:700">Balance Check</td><td style="text-align:right;padding:10px 12px" class="${s.is_balanced ? 'balanced' : 'unbalanced'}">${s.is_balanced ? 'BALANCED' : `Difference: ${fmtRM(s.difference)}`}</td></tr>
        </tbody>
      </table>
      <p style="margin-top:24px;font-size:11px;color:#999">Generated: ${new Date().toLocaleString()}</p>
    </body></html>`;

    const w = window.open('', '_blank');
    w.document.write(html);
    w.document.close();
    w.setTimeout(() => w.print(), 300);
  };

  const summary = data?.summary || {};

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <Label className="text-xs text-gray-500">As at date</Label>
          <Input type="date" value={asAt} onChange={e => setAsAt(e.target.value)} className="w-44" data-testid="bs-date-input" />
        </div>
        <Button onClick={loadBalanceSheet} variant="outline" size="sm" disabled={loading} data-testid="bs-refresh-btn">
          {loading ? 'Loading...' : 'Refresh'}
        </Button>
        <Button onClick={handlePrint} variant="outline" size="sm" disabled={!data} data-testid="bs-print-btn">
          <Printer className="w-4 h-4 mr-1" />Print
        </Button>
      </div>

      {loading && !data ? (
        <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-16 bg-gray-100 animate-pulse rounded-lg" />)}</div>
      ) : !data ? (
        <Card><CardContent className="py-12 text-center text-gray-500">No data available.</CardContent></Card>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card className="border-l-4 border-l-blue-500">
              <CardContent className="pt-4 pb-3">
                <p className="text-xs text-gray-500 uppercase">Total Assets</p>
                <p className="text-xl font-bold text-gray-900">{fmtRM(summary.total_assets)}</p>
              </CardContent>
            </Card>
            <Card className="border-l-4 border-l-orange-500">
              <CardContent className="pt-4 pb-3">
                <p className="text-xs text-gray-500 uppercase">Total Liabilities</p>
                <p className="text-xl font-bold text-gray-900">{fmtRM(summary.total_liabilities)}</p>
              </CardContent>
            </Card>
            <Card className="border-l-4 border-l-purple-500">
              <CardContent className="pt-4 pb-3">
                <p className="text-xs text-gray-500 uppercase">Total Equity</p>
                <p className="text-xl font-bold text-gray-900">{fmtRM(summary.total_equity)}</p>
              </CardContent>
            </Card>
            <Card className={`border-l-4 ${summary.is_balanced ? 'border-l-emerald-500' : 'border-l-red-500'}`}>
              <CardContent className="pt-4 pb-3">
                <p className="text-xs text-gray-500 uppercase">Balance Check</p>
                <div className="flex items-center gap-1.5 mt-1">
                  {summary.is_balanced ? (
                    <><CheckCircle className="w-5 h-5 text-emerald-600" /><span className="text-lg font-bold text-emerald-700">Balanced</span></>
                  ) : (
                    <><AlertTriangle className="w-5 h-5 text-red-500" /><span className="text-lg font-bold text-red-600">Off by {fmtRM(summary.difference)}</span></>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Period label */}
          <p className="text-sm text-gray-500">{data.period}</p>

          {/* Balance Sheet Table */}
          <Card>
            <CardContent className="p-0">
              <table className="w-full" data-testid="balance-sheet-table">
                <thead>
                  <tr className="border-b-2 border-gray-200">
                    <th className="text-left py-3 px-4 text-xs text-gray-500 uppercase font-semibold w-24">Code</th>
                    <th className="text-left py-3 px-4 text-xs text-gray-500 uppercase font-semibold">Account</th>
                    <th className="text-right py-3 px-4 text-xs text-gray-500 uppercase font-semibold w-40">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {/* ASSETS */}
                  <SectionHeader title="ASSETS" total={data.assets.total} expanded={expandedSections.assets} onToggle={() => toggleSection('assets')} />
                  {expandedSections.assets && (
                    <>
                      {data.assets.current?.length > 0 && <SubSectionHeader title="Current Assets" />}
                      {data.assets.current?.map(a => <AccountRow key={a.account_code} account={a} indent />)}
                      {data.assets.non_current?.length > 0 && <SubSectionHeader title="Non-Current Assets" />}
                      {data.assets.non_current?.map(a => <AccountRow key={a.account_code} account={a} indent />)}
                    </>
                  )}

                  {/* LIABILITIES */}
                  <SectionHeader title="LIABILITIES" total={data.liabilities.total} expanded={expandedSections.liabilities} onToggle={() => toggleSection('liabilities')} />
                  {expandedSections.liabilities && (
                    <>
                      {data.liabilities.current?.length > 0 && <SubSectionHeader title="Current Liabilities" />}
                      {data.liabilities.current?.map(a => <AccountRow key={a.account_code} account={a} indent />)}
                      {data.liabilities.non_current?.length > 0 && <SubSectionHeader title="Non-Current Liabilities" />}
                      {data.liabilities.non_current?.map(a => <AccountRow key={a.account_code} account={a} indent />)}
                    </>
                  )}

                  {/* EQUITY */}
                  <SectionHeader title="EQUITY" total={data.equity.total} expanded={expandedSections.equity} onToggle={() => toggleSection('equity')} />
                  {expandedSections.equity && (
                    <>
                      {data.equity.accounts?.map(a => <AccountRow key={a.account_code} account={a} indent />)}
                    </>
                  )}

                  {/* TOTALS */}
                  <tr className="border-t-2 border-gray-300 bg-gray-50">
                    <td colSpan={2} className="py-3 px-4 font-bold text-gray-900">Total Assets</td>
                    <td className="py-3 px-4 text-right font-bold tabular-nums">{fmtRM(summary.total_assets)}</td>
                  </tr>
                  <tr className="bg-gray-50">
                    <td colSpan={2} className="py-3 px-4 font-bold text-gray-900">Total Liabilities + Equity</td>
                    <td className="py-3 px-4 text-right font-bold tabular-nums">{fmtRM(summary.total_liabilities_equity)}</td>
                  </tr>
                  <tr className={summary.is_balanced ? 'bg-emerald-50' : 'bg-red-50'}>
                    <td colSpan={2} className="py-3 px-4 font-bold text-sm">Accounting Equation Check (A = L + E)</td>
                    <td className={`py-3 px-4 text-right font-bold text-sm ${summary.is_balanced ? 'text-emerald-700' : 'text-red-600'}`}>
                      {summary.is_balanced ? 'BALANCED' : `Difference: ${fmtRM(summary.difference)}`}
                    </td>
                  </tr>
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};
