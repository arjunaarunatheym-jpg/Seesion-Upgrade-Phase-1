import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Loader2, TrendingUp, TrendingDown, Minus, Printer, ArrowRightLeft } from 'lucide-react';
import { axiosInstance } from '../../App';

const YoYComparisonTab = ({ selectedYear, companySettings }) => {
  const [compareYear, setCompareYear] = useState(selectedYear - 1);
  const [currentData, setCurrentData] = useState(null);
  const [prevData, setPrevData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fmt = (val) => `RM ${(val || 0).toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const variance = (curr, prev) => {
    const diff = (curr || 0) - (prev || 0);
    const pct = prev ? ((diff / Math.abs(prev)) * 100) : (curr ? 100 : 0);
    return { diff: Math.round(diff * 100) / 100, pct: Math.round(pct * 100) / 100 };
  };

  const TrendIcon = ({ val, inverse }) => {
    const isPositive = inverse ? val < 0 : val > 0;
    if (val === 0) return <Minus className="w-4 h-4 text-gray-400" />;
    return isPositive 
      ? <TrendingUp className="w-4 h-4 text-green-600" />
      : <TrendingDown className="w-4 h-4 text-red-600" />;
  };

  const loadComparison = async () => {
    setLoading(true);
    try {
      const [currRes, prevRes] = await Promise.all([
        axiosInstance.get(`/finance/profit-loss/by-programme?year=${selectedYear}`),
        axiosInstance.get(`/finance/profit-loss/by-programme?year=${compareYear}`)
      ]);
      setCurrentData(currRes.data);
      setPrevData(prevRes.data);
    } catch (err) {
      console.error("Failed to load YoY data:", err);
    }
    setLoading(false);
  };

  useEffect(() => { loadComparison(); }, [selectedYear, compareYear]);

  const handlePrint = async () => {
    const { printYoYComparison } = await import('../../utils/printPnL');
    const settings = companySettings || {};
    let logoUrl = '';
    if (settings.logo_url) {
      logoUrl = settings.logo_url.startsWith('http') ? settings.logo_url 
        : `${process.env.REACT_APP_BACKEND_URL}${settings.logo_url.startsWith('/') ? '' : '/'}${settings.logo_url}`;
    }
    printYoYComparison(currentData, prevData, selectedYear, compareYear, settings, logoUrl);
  };

  if (loading) return <div className="flex items-center justify-center p-12"><Loader2 className="w-8 h-8 animate-spin text-blue-600" /></div>;

  const curr = currentData?.summary || {};
  const prev = prevData?.summary || {};
  const currProgs = currentData?.programmes || [];
  const prevProgs = prevData?.programmes || [];

  // Build combined programme list
  const allProgNames = [...new Set([...currProgs.map(p => p.programme_name), ...prevProgs.map(p => p.programme_name)])];
  const progComparison = allProgNames.map(name => {
    const c = currProgs.find(p => p.programme_name === name) || {};
    const p = prevProgs.find(p => p.programme_name === name) || {};
    return { name, curr: c, prev: p };
  });

  const rows = [
    { label: 'Training Programme Income', curr: curr.total_programme_income, prev: prev.total_programme_income, bold: false, section: 'income' },
    { label: 'Other Income', curr: curr.other_income, prev: prev.other_income, bold: false, section: 'income' },
    { label: 'Total Revenue', curr: curr.total_income, prev: prev.total_income, bold: true, section: 'total' },
    { divider: true, label: 'DIRECT COSTS' },
    { label: 'Total Direct Costs', curr: curr.total_direct_costs, prev: prev.total_direct_costs, bold: true, section: 'expense', inverse: true },
    { label: 'Gross Profit', curr: curr.gross_profit, prev: prev.gross_profit, bold: true, section: 'profit' },
    { divider: true, label: 'OPERATING EXPENSES' },
    { label: 'Payroll', curr: curr.overhead?.payroll, prev: prev.overhead?.payroll, indent: true, section: 'expense', inverse: true },
    { label: 'Petty Cash', curr: curr.overhead?.petty_cash, prev: prev.overhead?.petty_cash, indent: true, section: 'expense', inverse: true },
    { label: 'Other Expenses', curr: curr.overhead?.manual, prev: prev.overhead?.manual, indent: true, section: 'expense', inverse: true },
    { label: 'Total Operating Expenses', curr: curr.overhead?.total, prev: prev.overhead?.total, bold: true, section: 'expense', inverse: true },
    { divider: true, label: 'BOTTOM LINE' },
    { label: 'Total Expenses', curr: curr.total_expenses, prev: prev.total_expenses, bold: true, section: 'expense', inverse: true },
    { label: 'Net Profit', curr: curr.net_profit, prev: prev.net_profit, bold: true, section: 'net', highlight: true },
  ];

  const years = [];
  for (let y = 2024; y <= new Date().getFullYear() + 1; y++) years.push(y);

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle className="flex items-center gap-2">
              <ArrowRightLeft className="w-5 h-5 text-purple-600" />
              Year-over-Year Comparison
            </CardTitle>
            <CardDescription>Compare financial performance between two years</CardDescription>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium">{selectedYear}</span>
              <span className="text-gray-400">vs</span>
              <Select value={String(compareYear)} onValueChange={(v) => setCompareYear(parseInt(v))}>
                <SelectTrigger className="w-24" data-testid="yoy-compare-year">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {years.filter(y => y !== selectedYear).map(y => (
                    <SelectItem key={y} value={String(y)}>{y}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handlePrint} variant="outline" size="sm" data-testid="print-yoy-btn">
              <Printer className="w-4 h-4 mr-2" />
              Print Comparison
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Summary Cards */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: 'Revenue', curr: curr.total_income, prev: prev.total_income, color: 'green' },
            { label: 'Expenses', curr: curr.total_expenses, prev: prev.total_expenses, color: 'red', inverse: true },
            { label: 'Net Profit', curr: curr.net_profit, prev: prev.net_profit, color: 'blue' },
          ].map((card) => {
            const v = variance(card.curr, card.prev);
            return (
              <div key={card.label} className={`p-4 rounded-lg border bg-${card.color}-50 border-${card.color}-200`}>
                <div className={`text-xs font-semibold text-${card.color}-700 uppercase mb-1`}>{card.label}</div>
                <div className="flex items-end justify-between">
                  <div>
                    <div className="text-lg font-bold">{fmt(card.curr)}</div>
                    <div className="text-xs text-gray-500">was {fmt(card.prev)}</div>
                  </div>
                  <div className="text-right">
                    <Badge className={v.diff >= 0 ? (card.inverse ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700') : (card.inverse ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700')}>
                      {v.diff >= 0 ? '+' : ''}{v.pct}%
                    </Badge>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Detailed Comparison Table */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="text-left p-3 font-semibold">Description</th>
                <th className="text-right p-3 font-semibold">{selectedYear}</th>
                <th className="text-right p-3 font-semibold">{compareYear}</th>
                <th className="text-right p-3 font-semibold">Variance (RM)</th>
                <th className="text-right p-3 font-semibold">Variance (%)</th>
                <th className="text-center p-3 font-semibold">Trend</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => {
                if (row.divider) {
                  return (
                    <tr key={i} className="bg-gray-50">
                      <td colSpan={6} className="p-2 text-xs font-bold text-gray-500 uppercase tracking-wider">{row.label}</td>
                    </tr>
                  );
                }
                const v = variance(row.curr, row.prev);
                return (
                  <tr key={i} className={`${row.highlight ? 'bg-blue-50 border-t-2 border-blue-300' : ''} ${row.bold ? 'font-semibold' : ''}`}>
                    <td className={`p-3 ${row.indent ? 'pl-8 text-gray-600' : ''}`}>{row.label}</td>
                    <td className="p-3 text-right">{fmt(row.curr)}</td>
                    <td className="p-3 text-right text-gray-500">{fmt(row.prev)}</td>
                    <td className={`p-3 text-right ${v.diff >= 0 ? (row.inverse ? 'text-red-600' : 'text-green-600') : (row.inverse ? 'text-green-600' : 'text-red-600')}`}>
                      {v.diff >= 0 ? '+' : ''}{fmt(v.diff).replace('RM ', '')}
                    </td>
                    <td className={`p-3 text-right ${v.diff >= 0 ? (row.inverse ? 'text-red-600' : 'text-green-600') : (row.inverse ? 'text-green-600' : 'text-red-600')}`}>
                      {v.diff >= 0 ? '+' : ''}{v.pct}%
                    </td>
                    <td className="p-3 text-center"><TrendIcon val={v.diff} inverse={row.inverse} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Programme Comparison */}
        {progComparison.length > 0 && (
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wider">Programme-Wise Comparison</h3>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="text-left p-2 font-semibold">Programme</th>
                    <th className="text-right p-2 font-semibold">{selectedYear} Revenue</th>
                    <th className="text-right p-2 font-semibold">{compareYear} Revenue</th>
                    <th className="text-right p-2 font-semibold">Change</th>
                    <th className="text-right p-2 font-semibold">{selectedYear} Profit</th>
                    <th className="text-right p-2 font-semibold">{compareYear} Profit</th>
                    <th className="text-right p-2 font-semibold">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {progComparison.map((p, i) => {
                    const revV = variance(p.curr.income, p.prev.income);
                    const profV = variance(p.curr.gross_profit, p.prev.gross_profit);
                    return (
                      <tr key={i} className="border-b">
                        <td className="p-2 font-medium">{p.name || 'Other'}</td>
                        <td className="p-2 text-right">{fmt(p.curr.income)}</td>
                        <td className="p-2 text-right text-gray-500">{fmt(p.prev.income)}</td>
                        <td className={`p-2 text-right ${revV.diff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {revV.diff >= 0 ? '+' : ''}{revV.pct}%
                        </td>
                        <td className="p-2 text-right">{fmt(p.curr.gross_profit)}</td>
                        <td className="p-2 text-right text-gray-500">{fmt(p.prev.gross_profit)}</td>
                        <td className={`p-2 text-right ${profV.diff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {profV.diff >= 0 ? '+' : ''}{profV.pct}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { YoYComparisonTab };
