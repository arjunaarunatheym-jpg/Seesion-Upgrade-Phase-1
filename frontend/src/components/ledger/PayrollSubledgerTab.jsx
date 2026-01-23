/**
 * PayrollSubledgerTab Component - Extracted from ProfitLossLedger
 * Staff payroll register breakdown by employee
 */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import { Loader2, Building2, ChevronDown, ChevronRight } from 'lucide-react';

const PayrollSubledgerTab = ({
  selectedYear,
  payrollSubledger,
  expandedRows,
  toggleRow,
  formatCurrency,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building2 className="w-5 h-5 text-blue-600" />
          Staff Payroll Register - {selectedYear}
        </CardTitle>
        <CardDescription>Payroll breakdown by employee</CardDescription>
      </CardHeader>
      <CardContent>
        {!payrollSubledger ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-blue-50">
                  <th className="text-left p-3">Employee</th>
                  <th className="text-right p-3">Gross</th>
                  <th className="text-right p-3">EPF</th>
                  <th className="text-right p-3">SOCSO</th>
                  <th className="text-right p-3">EIS</th>
                  <th className="text-right p-3">Net</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody>
                {(payrollSubledger?.employees || []).map((e) => (
                  <React.Fragment key={e.staff_id}>
                    <tr className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => toggleRow(`emp-${e.staff_id}`)}>
                      <td className="p-3 font-medium flex items-center gap-2">
                        {expandedRows[`emp-${e.staff_id}`] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        <div>
                          <p>{e.name}</p>
                          <p className="text-xs text-gray-500">{e.designation}</p>
                        </div>
                      </td>
                      <td className="p-3 text-right">{formatCurrency(e.total_gross)}</td>
                      <td className="p-3 text-right text-red-600">{formatCurrency(e.total_epf)}</td>
                      <td className="p-3 text-right text-red-600">{formatCurrency(e.total_socso)}</td>
                      <td className="p-3 text-right text-red-600">{formatCurrency(e.total_eis)}</td>
                      <td className="p-3 text-right font-semibold text-green-600">{formatCurrency(e.total_net)}</td>
                      <td className="p-3">
                        <Badge variant="outline">{e.months?.length || 0}mo</Badge>
                      </td>
                    </tr>
                    {expandedRows[`emp-${e.staff_id}`] && e.months?.length > 0 && (
                      <tr className="bg-gray-50">
                        <td colSpan={7} className="p-4">
                          <div className="text-xs overflow-x-auto">
                            <table className="w-full">
                              <thead>
                                <tr className="text-gray-500">
                                  <th className="text-left p-1">Month</th>
                                  <th className="text-right p-1">Gross</th>
                                  <th className="text-right p-1">EPF</th>
                                  <th className="text-right p-1">SOCSO</th>
                                  <th className="text-right p-1">EIS</th>
                                  <th className="text-right p-1">Net</th>
                                </tr>
                              </thead>
                              <tbody>
                                {e.months.map((m, idx) => (
                                  <tr key={idx} className="border-t">
                                    <td className="p-1">{m.month_name}</td>
                                    <td className="p-1 text-right">{formatCurrency(m.gross)}</td>
                                    <td className="p-1 text-right text-red-600">{formatCurrency(m.epf)}</td>
                                    <td className="p-1 text-right text-red-600">{formatCurrency(m.socso)}</td>
                                    <td className="p-1 text-right text-red-600">{formatCurrency(m.eis)}</td>
                                    <td className="p-1 text-right text-green-600">{formatCurrency(m.net)}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-blue-100 font-bold">
                  <td className="p-3">TOTAL</td>
                  <td className="p-3 text-right">{formatCurrency(payrollSubledger?.totals?.total_gross)}</td>
                  <td className="p-3 text-right text-red-700">{formatCurrency(payrollSubledger?.totals?.total_epf)}</td>
                  <td className="p-3 text-right text-red-700">{formatCurrency(payrollSubledger?.totals?.total_socso)}</td>
                  <td className="p-3 text-right text-red-700">{formatCurrency(payrollSubledger?.totals?.total_eis)}</td>
                  <td className="p-3 text-right text-green-700">{formatCurrency(payrollSubledger?.totals?.total_net)}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { PayrollSubledgerTab };
