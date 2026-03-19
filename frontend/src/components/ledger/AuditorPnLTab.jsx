import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import {
  Loader2, FileText, ChevronDown, ChevronRight, Printer,
  Download, AlertTriangle, Filter, TrendingUp
} from 'lucide-react';
import { axiosInstance } from '../../App';
import { toast } from 'sonner';

const AuditorPnLTab = ({ selectedYear, companySettings }) => {
  const [loading, setLoading] = useState(false);
  const [pnlData, setPnlData] = useState(null);
  const [filterMode, setFilterMode] = useState('year'); // year, month, range
  const [filterMonth, setFilterMonth] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [postedOnly, setPostedOnly] = useState(true);
  const [expandedSections, setExpandedSections] = useState({ revenue: true, cost_of_sales: true, operating_expense: true, other_income: true });
  const [drilldownOpen, setDrilldownOpen] = useState(false);
  const [drilldownData, setDrilldownData] = useState(null);
  const [drilldownLoading, setDrilldownLoading] = useState(false);

  const fmt = (val) => `RM ${(val || 0).toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const loadPnL = useCallback(async () => {
    setLoading(true);
    try {
      let params = `posted_only=${postedOnly}`;
      if (filterMode === 'year') params += `&year=${selectedYear}`;
      else if (filterMode === 'month' && filterMonth) params += `&year=${selectedYear}&month=${filterMonth}`;
      else if (filterMode === 'range' && dateFrom && dateTo) params += `&date_from=${dateFrom}&date_to=${dateTo}`;
      else params += `&year=${selectedYear}`;
      
      const res = await axiosInstance.get(`/finance/pnl-journal?${params}`);
      setPnlData(res.data);
    } catch (err) {
      toast.error('Failed to load P&L');
    }
    setLoading(false);
  }, [selectedYear, filterMode, filterMonth, dateFrom, dateTo, postedOnly]);

  useEffect(() => { loadPnL(); }, [loadPnL]);

  const toggleSection = (key) => setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));

  const handleDrilldown = async (accountCode) => {
    setDrilldownLoading(true);
    setDrilldownOpen(true);
    try {
      let params = '';
      if (filterMode === 'range' && dateFrom && dateTo) params = `date_from=${dateFrom}&date_to=${dateTo}`;
      else params = `year=${selectedYear}`;
      const res = await axiosInstance.get(`/finance/pnl-journal/drilldown/${accountCode}?${params}`);
      setDrilldownData(res.data);
    } catch (err) {
      toast.error('Failed to load drill-down');
    }
    setDrilldownLoading(false);
  };

  const handleExportExcel = async () => {
    if (!pnlData) return;
    try {
      let params = `posted_only=${postedOnly}`;
      if (filterMode === 'year') params += `&year=${selectedYear}`;
      else if (filterMode === 'month' && filterMonth) params += `&year=${selectedYear}&month=${filterMonth}`;
      else if (filterMode === 'range' && dateFrom && dateTo) params += `&date_from=${dateFrom}&date_to=${dateTo}`;
      else params += `&year=${selectedYear}`;
      
      const res = await axiosInstance.get(`/finance/pnl-journal/export?${params}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `PnL_Statement_${pnlData.period || selectedYear}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('P&L exported');
    } catch {
      toast.error('Export failed');
    }
  };

  const handlePrint = () => {
    if (!pnlData) return;
    const settings = companySettings || {};
    const primaryColor = settings.primary_color || '#1a365d';
    const secondaryColor = settings.secondary_color || '#4472C4';
    const tagline = settings.tagline || 'Towards a Nation of Safe Drivers';
    let logoUrl = '';
    if (settings.logo_url) {
      logoUrl = settings.logo_url.startsWith('http') ? settings.logo_url : `${process.env.REACT_APP_BACKEND_URL}${settings.logo_url.startsWith('/') ? '' : '/'}${settings.logo_url}`;
    }
    const headerCustomFields = (settings.invoice_custom_fields || [])
      .filter(f => f.position === 'Header' || f.position === 'header')
      .map(f => ` &bull; ${f.label}: ${f.value}`)
      .join('');
    const s = pnlData.summary || {};
    const sections = pnlData.sections || {};
    
    const sectionHTML = (key, label, color) => {
      const sec = sections[key] || {};
      if (!sec.accounts || sec.accounts.length === 0) return '';
      return `
        <tr style="background:#f5f5f5;"><td colspan="3" style="padding:8px 12px;font-weight:bold;color:${color};font-size:12px;border-left:4px solid ${color};">${label}</td></tr>
        ${sec.accounts.map(a => `<tr><td style="padding:5px 12px 5px 30px;font-size:11px;">${a.account_code}</td><td style="padding:5px;font-size:11px;">${a.account_name}</td><td style="padding:5px 12px;text-align:right;font-size:11px;">${fmt(a.amount)}</td></tr>`).join('')}
        <tr style="border-top:2px solid #ddd;"><td colspan="2" style="padding:6px 12px;font-weight:bold;font-size:11px;">Subtotal ${label}</td><td style="padding:6px 12px;text-align:right;font-weight:bold;font-size:11px;">${fmt(sec.total)}</td></tr>
      `;
    };
    
    const w = window.open('', '_blank');
    w.document.write(`<!DOCTYPE html><html><head><title>P&L Statement (Auditor) - ${pnlData.period}</title>
    <style>
      @page { size: A4; margin: 15mm; }
      @media print { body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } }
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: Arial, sans-serif; font-size: 11px; padding: 25px; max-width: 210mm; margin: 0 auto; color: #333; }
      .header { display: flex; align-items: center; gap: 20px; padding-bottom: 15px; border-bottom: 3px solid ${primaryColor}; margin-bottom: 20px; }
      .logo-img { width: 100px; height: auto; }
      .company-name { font-size: 18px; font-weight: bold; color: ${primaryColor}; margin-bottom: 5px; }
      .company-info { font-size: 11px; color: #444; line-height: 1.5; }
      .doc-title { font-size: 20px; font-weight: bold; text-align: center; color: ${primaryColor}; margin: 15px 0 5px; padding: 10px; background: #f0f4f8; }
      .doc-subtitle { text-align: center; font-size: 13px; color: #555; margin-bottom: 15px; }
      table { width: 100%; border-collapse: collapse; }
      .calc-row td { padding: 10px 12px; font-weight: bold; font-size: 13px; }
      .net-row td { background: ${primaryColor}; color: white; padding: 12px; font-weight: bold; font-size: 14px; }
      .footer { margin-top: 30px; font-size: 9px; color: #777; padding-top: 12px; border-top: 1px solid #ddd; text-align: center; }
      .tagline { font-style: italic; color: ${primaryColor}; font-size: 12px; text-align: center; margin-top: 15px; }
      .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 9px; font-weight: bold; background: #e3f2fd; color: ${primaryColor}; }
    </style></head><body>
    <div class="header">
      ${logoUrl ? `<img src="${logoUrl}" class="logo-img" alt="Logo" />` : ''}
      <div>
        <div class="company-name">${settings.company_name || 'MDDRC SDN BHD'}</div>
        <div class="company-info">${settings.company_reg_no ? `(${settings.company_reg_no})` : ''} ${settings.address_line1 ? ` &bull; ${settings.address_line1}` : ''}${settings.address_line2 ? `, ${settings.address_line2}` : ''}<br>
        ${settings.city || ''}${settings.postcode ? ` ${settings.postcode}` : ''}${settings.state ? `, ${settings.state}` : ''} ${settings.phone ? ` &bull; Tel: ${settings.phone}` : ''}${settings.email ? ` &bull; ${settings.email}` : ''} ${headerCustomFields}</div>
      </div>
    </div>
    <div class="doc-title">PROFIT & LOSS STATEMENT</div>
    <div class="doc-subtitle">${pnlData.period} <span class="badge">${pnlData.posted_only ? 'Posted Only' : 'Including Drafts'} &bull; ${pnlData.journal_count} Journal Entries</span></div>
    <table>
      <thead><tr style="background:${secondaryColor};color:white;"><th style="padding:8px 12px;width:15%;">Code</th><th style="padding:8px;width:55%;">Account</th><th style="padding:8px 12px;text-align:right;width:30%;">Amount (RM)</th></tr></thead>
      <tbody>
        ${sectionHTML('revenue', 'REVENUE', '#16a34a')}
        ${sectionHTML('other_income', 'OTHER INCOME', '#0d9488')}
        <tr class="calc-row" style="background:#e8f5e9;border-top:2px solid #4caf50;"><td colspan="2" style="color:#2e7d32;">TOTAL INCOME</td><td style="text-align:right;color:#2e7d32;">${fmt(s.total_income)}</td></tr>
        ${sectionHTML('cost_of_sales', 'COST OF SALES / DIRECT COSTS', '#ea580c')}
        <tr class="calc-row" style="background:#e3f2fd;border-top:2px solid #2196f3;"><td colspan="2" style="color:#1565c0;">GROSS PROFIT (${s.gross_margin_pct || 0}%)</td><td style="text-align:right;color:#1565c0;">${fmt(s.gross_profit)}</td></tr>
        ${sectionHTML('operating_expense', 'OPERATING EXPENSES', '#dc2626')}
        <tr class="net-row"><td colspan="2">NET PROFIT BEFORE TAX (${s.net_margin_pct || 0}%)</td><td style="text-align:right;">${fmt(s.net_profit)}</td></tr>
      </tbody>
    </table>
    <div class="footer"><p>Auditor P&L Statement — ${settings.company_name || 'MDDRC'} Training Management System</p><p>Generated: ${new Date().toLocaleString('en-MY')} &bull; Source: Posted Journal Entries</p></div>
    <div class="tagline">"${tagline}"</div>
    <script>window.onload = function() { setTimeout(function() { window.print(); }, 500); };</script>
    </body></html>`);
    w.document.close();
  };

  const summary = pnlData?.summary || {};
  const sections = pnlData?.sections || {};
  const warnings = pnlData?.warnings || [];

  const SectionBlock = ({ sectionKey, color }) => {
    const sec = sections[sectionKey];
    if (!sec || sec.accounts.length === 0) return null;
    const isExpanded = expandedSections[sectionKey];
    return (
      <div className="mb-2">
        <button onClick={() => toggleSection(sectionKey)} className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-gray-50" style={{ borderLeft: `4px solid ${color}` }}>
          <span className="flex items-center gap-2 font-semibold text-sm" style={{ color }}>
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            {sec.label}
            <Badge variant="outline" className="text-xs">{sec.accounts.length} accounts</Badge>
          </span>
          <span className="font-bold text-sm">{fmt(sec.total)}</span>
        </button>
        {isExpanded && (
          <table className="w-full text-sm ml-4">
            <tbody>
              {sec.accounts.map(a => (
                <tr key={a.account_code} className="border-b border-gray-100 hover:bg-blue-50 cursor-pointer" onClick={() => handleDrilldown(a.account_code)}>
                  <td className="p-2 w-20 font-mono text-xs text-gray-500">{a.account_code}</td>
                  <td className="p-2">{a.account_name}</td>
                  <td className="p-2 text-right font-medium">{fmt(a.amount)}</td>
                  <td className="p-2 text-right text-xs text-gray-400">{a.entry_count} entries</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    );
  };

  if (loading && !pnlData) return <div className="flex items-center justify-center p-12"><Loader2 className="w-8 h-8 animate-spin text-blue-600" /></div>;

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-indigo-600" />
              Auditor P&L Statement
            </CardTitle>
            <CardDescription>Journal-based Profit & Loss — click any account to drill down</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleExportExcel} data-testid="export-pnl-excel">
              <Download className="w-4 h-4 mr-1" /> Excel
            </Button>
            <Button variant="outline" size="sm" onClick={handlePrint} data-testid="print-auditor-pnl">
              <Printer className="w-4 h-4 mr-1" /> Print
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-end gap-3 mt-3 p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <Select value={filterMode} onValueChange={setFilterMode}>
              <SelectTrigger className="w-28 h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="year">Full Year</SelectItem>
                <SelectItem value="month">Month</SelectItem>
                <SelectItem value="range">Date Range</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {filterMode === 'month' && (
            <Select value={filterMonth} onValueChange={setFilterMonth}>
              <SelectTrigger className="w-32 h-8 text-xs"><SelectValue placeholder="Month" /></SelectTrigger>
              <SelectContent>
                {[...Array(12)].map((_, i) => (
                  <SelectItem key={i+1} value={String(i+1)}>{new Date(2000, i).toLocaleString('en', { month: 'long' })}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {filterMode === 'range' && (<>
            <div><Label className="text-xs">From</Label><Input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="h-8 text-xs w-36" /></div>
            <div><Label className="text-xs">To</Label><Input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="h-8 text-xs w-36" /></div>
          </>)}
          <div className="flex items-center gap-1">
            <input type="checkbox" id="posted-only" checked={postedOnly} onChange={e => setPostedOnly(e.target.checked)} />
            <Label htmlFor="posted-only" className="text-xs">Posted only</Label>
          </div>
          <Button size="sm" variant="outline" onClick={loadPnL} className="h-8 text-xs">Apply</Button>
          {pnlData && <Badge variant="secondary" className="text-xs">{pnlData.journal_count} journals &bull; {pnlData.period}</Badge>}
        </div>
      </CardHeader>
      <CardContent>
        {/* Warnings */}
        {warnings.length > 0 && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-center gap-2 text-amber-700 font-semibold text-sm mb-1"><AlertTriangle className="w-4 h-4" /> Data Quality Warnings</div>
            {warnings.map((w, i) => <div key={i} className="text-xs text-amber-600 ml-6">- {w}</div>)}
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            { label: 'Total Revenue', value: summary.total_income, color: 'green' },
            { label: 'Gross Profit', value: summary.gross_profit, sub: `${summary.gross_margin_pct || 0}% margin`, color: 'blue' },
            { label: 'Operating Expenses', value: summary.operating_expenses, color: 'red' },
            { label: 'Net Profit', value: summary.net_profit, sub: `${summary.net_margin_pct || 0}% margin`, color: 'indigo' },
          ].map(c => (
            <div key={c.label} className={`p-3 rounded-lg border bg-${c.color}-50 border-${c.color}-200`}>
              <div className={`text-xs font-semibold text-${c.color}-700 uppercase`}>{c.label}</div>
              <div className="text-lg font-bold mt-1">{fmt(c.value)}</div>
              {c.sub && <div className="text-xs text-gray-500">{c.sub}</div>}
            </div>
          ))}
        </div>

        {/* P&L Sections */}
        <SectionBlock sectionKey="revenue" color="#16a34a" />
        <SectionBlock sectionKey="other_income" color="#0d9488" />
        
        <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200 my-2">
          <span className="font-bold text-green-800">TOTAL INCOME</span>
          <span className="font-bold text-green-800">{fmt(summary.total_income)}</span>
        </div>
        
        <SectionBlock sectionKey="cost_of_sales" color="#ea580c" />
        
        <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200 my-2">
          <span className="font-bold text-blue-800">GROSS PROFIT ({summary.gross_margin_pct || 0}%)</span>
          <span className="font-bold text-blue-800">{fmt(summary.gross_profit)}</span>
        </div>
        
        <SectionBlock sectionKey="operating_expense" color="#dc2626" />
        <SectionBlock sectionKey="other_expense" color="#9333ea" />
        
        <div className="flex items-center justify-between p-4 bg-indigo-900 text-white rounded-lg my-2">
          <span className="font-bold text-lg">NET PROFIT BEFORE TAX ({summary.net_margin_pct || 0}%)</span>
          <span className="font-bold text-lg">{fmt(summary.net_profit)}</span>
        </div>
      </CardContent>

      {/* Drill-down Dialog */}
      <Dialog open={drilldownOpen} onOpenChange={setDrilldownOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {drilldownData ? `${drilldownData.account_code} — ${drilldownData.account_name}` : 'Loading...'}
            </DialogTitle>
          </DialogHeader>
          {drilldownLoading ? (
            <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin" /></div>
          ) : drilldownData && (
            <div>
              <div className="flex gap-4 mb-3 text-sm">
                <Badge variant="outline">Total Debit: {fmt(drilldownData.total_debit)}</Badge>
                <Badge variant="outline">Total Credit: {fmt(drilldownData.total_credit)}</Badge>
                <Badge variant="outline">{drilldownData.entries?.length || 0} entries</Badge>
              </div>
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="p-2 text-left">Date</th>
                    <th className="p-2 text-left">Journal #</th>
                    <th className="p-2 text-left">Description</th>
                    <th className="p-2 text-left">Reference</th>
                    <th className="p-2 text-right">Debit</th>
                    <th className="p-2 text-right">Credit</th>
                  </tr>
                </thead>
                <tbody>
                  {(drilldownData.entries || []).map((e, i) => (
                    <tr key={i} className="border-b">
                      <td className="p-2">{e.date}</td>
                      <td className="p-2 font-mono">{e.journal_no}</td>
                      <td className="p-2">{e.line_memo || e.description}</td>
                      <td className="p-2 text-gray-500">{e.source_reference}</td>
                      <td className="p-2 text-right">{e.debit > 0 ? fmt(e.debit) : ''}</td>
                      <td className="p-2 text-right">{e.credit > 0 ? fmt(e.credit) : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export { AuditorPnLTab };
