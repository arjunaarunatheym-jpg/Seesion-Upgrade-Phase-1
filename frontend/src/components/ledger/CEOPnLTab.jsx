/**
 * CEOPnLTab Component - Extracted from ProfitLossLedger
 * CEO-level P&L view with programme profitability breakdown
 */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import { Loader2, Briefcase, ChevronDown, ChevronRight } from 'lucide-react';

const CEOPnLTab = ({
  selectedYear,
  programmeData,
  expandedRows,
  toggleRow,
  formatCurrency,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Briefcase className="w-5 h-5 text-blue-600" />
          CEO P&L View - {selectedYear}
        </CardTitle>
        <CardDescription>Profitability by programme with margins and insights</CardDescription>
      </CardHeader>
      <CardContent>
        {!programmeData ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Programme Breakdown Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-blue-50">
                    <th className="text-left p-3 font-semibold">Programme</th>
                    <th className="text-center p-3 font-semibold">Sessions</th>
                    <th className="text-right p-3 font-semibold text-green-600">Revenue</th>
                    <th className="text-right p-3 font-semibold text-red-600">Direct Costs</th>
                    <th className="text-right p-3 font-semibold text-blue-600">Gross Profit</th>
                    <th className="text-center p-3 font-semibold">Margin %</th>
                  </tr>
                </thead>
                <tbody>
                  {(programmeData?.programmes || []).map((prog) => (
                    <React.Fragment key={prog.programme_id}>
                      <tr 
                        className="border-b hover:bg-gray-50 cursor-pointer"
                        onClick={() => toggleRow(prog.programme_id)}
                      >
                        <td className="p-3 font-medium flex items-center gap-2">
                          {expandedRows[prog.programme_id] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          {prog.programme_name}
                        </td>
                        <td className="p-3 text-center">
                          <Badge variant="outline">{prog.session_count}</Badge>
                        </td>
                        <td className="p-3 text-right text-green-600">{formatCurrency(prog.income)}</td>
                        <td className="p-3 text-right text-red-600">{formatCurrency(prog.expenses.total)}</td>
                        <td className={`p-3 text-right font-semibold ${prog.gross_profit >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>
                          {formatCurrency(prog.gross_profit)}
                        </td>
                        <td className="p-3 text-center">
                          <Badge className={prog.gross_margin_pct >= 30 ? 'bg-green-100 text-green-700' : prog.gross_margin_pct >= 15 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}>
                            {prog.gross_margin_pct}%
                          </Badge>
                        </td>
                      </tr>
                      {expandedRows[prog.programme_id] && (
                        <tr className="bg-gray-50">
                          <td colSpan={6} className="p-4">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                              <div className="bg-white p-3 rounded border">
                                <p className="text-gray-500 text-xs">Trainer Fees</p>
                                <p className="font-semibold">{formatCurrency(prog.expenses.trainer_fees)}</p>
                              </div>
                              <div className="bg-white p-3 rounded border">
                                <p className="text-gray-500 text-xs">Coordinator Fees</p>
                                <p className="font-semibold">{formatCurrency(prog.expenses.coordinator_fees)}</p>
                              </div>
                              <div className="bg-white p-3 rounded border">
                                <p className="text-gray-500 text-xs">Marketing Commission</p>
                                <p className="font-semibold">{formatCurrency(prog.expenses.marketing_commissions)}</p>
                              </div>
                              <div className="bg-white p-3 rounded border">
                                <p className="text-gray-500 text-xs">Session Expenses</p>
                                <p className="font-semibold">{formatCurrency(prog.expenses.session_expenses)}</p>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="bg-blue-100 font-bold">
                    <td className="p-3" colSpan={2}>PROGRAMME TOTAL</td>
                    <td className="p-3 text-right text-green-700">{formatCurrency(programmeData?.summary?.total_programme_income)}</td>
                    <td className="p-3 text-right text-red-700">{formatCurrency(programmeData?.summary?.total_direct_costs)}</td>
                    <td className="p-3 text-right text-blue-700">{formatCurrency(programmeData?.summary?.gross_profit)}</td>
                    <td className="p-3 text-center">
                      <Badge className="bg-blue-600 text-white">{programmeData?.summary?.gross_margin_pct}%</Badge>
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card className="bg-green-50 border-green-200">
                <CardContent className="pt-4">
                  <p className="text-xs text-green-600 font-medium">Total Revenue</p>
                  <p className="text-xl font-bold text-green-700">{formatCurrency(programmeData?.summary?.total_income)}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Programme: {formatCurrency(programmeData?.summary?.total_programme_income)} | 
                    Other: {formatCurrency(programmeData?.summary?.other_income)}
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-red-50 border-red-200">
                <CardContent className="pt-4">
                  <p className="text-xs text-red-600 font-medium">Total Expenses</p>
                  <p className="text-xl font-bold text-red-700">{formatCurrency(programmeData?.summary?.total_expenses)}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Direct: {formatCurrency(programmeData?.summary?.total_direct_costs)} | 
                    Overhead: {formatCurrency(programmeData?.summary?.overhead?.total)}
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-blue-50 border-blue-200">
                <CardContent className="pt-4">
                  <p className="text-xs text-blue-600 font-medium">Net Profit</p>
                  <p className={`text-xl font-bold ${programmeData?.summary?.net_profit >= 0 ? 'text-blue-700' : 'text-orange-700'}`}>
                    {formatCurrency(programmeData?.summary?.net_profit)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Net Margin: {programmeData?.summary?.net_margin_pct}%
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-purple-50 border-purple-200">
                <CardContent className="pt-4">
                  <p className="text-xs text-purple-600 font-medium">Overhead Breakdown</p>
                  <div className="text-xs mt-1 space-y-1">
                    <div className="flex justify-between">
                      <span>Payroll:</span>
                      <span className="font-semibold">{formatCurrency(programmeData?.summary?.overhead?.payroll)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Petty Cash:</span>
                      <span className="font-semibold">{formatCurrency(programmeData?.summary?.overhead?.petty_cash)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Manual:</span>
                      <span className="font-semibold">{formatCurrency(programmeData?.summary?.overhead?.manual)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { CEOPnLTab };
