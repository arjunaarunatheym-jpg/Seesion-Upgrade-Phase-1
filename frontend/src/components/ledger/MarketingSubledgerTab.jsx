/**
 * MarketingSubledgerTab Component - Extracted from ProfitLossLedger
 * Marketing commission breakdown by marketer
 */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import { Loader2, UserCheck, ChevronDown, ChevronRight } from 'lucide-react';

const MarketingSubledgerTab = ({
  selectedYear,
  marketingSubledger,
  expandedRows,
  toggleRow,
  formatCurrency,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserCheck className="w-5 h-5 text-pink-600" />
          Marketing Commission Sub-ledger - {selectedYear}
        </CardTitle>
        <CardDescription>Commission breakdown by marketer</CardDescription>
      </CardHeader>
      <CardContent>
        {!marketingSubledger ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin text-pink-600" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-pink-50">
                  <th className="text-left p-3">Marketer</th>
                  <th className="text-right p-3">Commission</th>
                  <th className="text-right p-3">Paid</th>
                  <th className="text-right p-3">Balance</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody>
                {(marketingSubledger?.marketers || []).map((m) => (
                  <React.Fragment key={m.user_id}>
                    <tr className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => toggleRow(`mkt-${m.user_id}`)}>
                      <td className="p-3 font-medium flex items-center gap-2">
                        {expandedRows[`mkt-${m.user_id}`] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        {m.name}
                      </td>
                      <td className="p-3 text-right text-green-600">{formatCurrency(m.total_commission)}</td>
                      <td className="p-3 text-right text-blue-600">{formatCurrency(m.total_paid)}</td>
                      <td className={`p-3 text-right font-semibold ${m.balance > 0 ? 'text-orange-600' : 'text-gray-600'}`}>
                        {formatCurrency(m.balance)}
                      </td>
                      <td className="p-3">
                        <Badge variant="outline">{m.clients?.length || 0}</Badge>
                      </td>
                    </tr>
                    {expandedRows[`mkt-${m.user_id}`] && m.clients?.length > 0 && (
                      <tr className="bg-gray-50">
                        <td colSpan={5} className="p-4">
                          <div className="text-xs space-y-2 max-h-40 overflow-y-auto">
                            {m.clients.slice(0, 10).map((c, idx) => (
                              <div key={idx} className="flex justify-between items-center bg-white p-2 rounded border">
                                <span>{c.date} - {c.client} ({c.programme})</span>
                                <div className="flex items-center gap-2">
                                  <span className="text-gray-500">{c.commission_rate}%</span>
                                  <span className="font-semibold">{formatCurrency(c.amount)}</span>
                                  <Badge className={c.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}>
                                    {c.status}
                                  </Badge>
                                </div>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-pink-100 font-bold">
                  <td className="p-3">TOTAL</td>
                  <td className="p-3 text-right text-green-700">{formatCurrency(marketingSubledger?.totals?.total_commission)}</td>
                  <td className="p-3 text-right text-blue-700">{formatCurrency(marketingSubledger?.totals?.total_paid)}</td>
                  <td className="p-3 text-right text-orange-700">{formatCurrency(marketingSubledger?.totals?.total_balance)}</td>
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

export { MarketingSubledgerTab };
