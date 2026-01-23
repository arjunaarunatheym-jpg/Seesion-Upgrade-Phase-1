/**
 * TrainerSubledgerTab Component - Extracted from ProfitLossLedger
 * Trainer and Coordinator earnings breakdown
 */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Badge } from '../ui/badge';
import { Loader2, Users, UserCheck, ChevronDown, ChevronRight } from 'lucide-react';

const TrainerSubledgerTab = ({
  selectedYear,
  trainerSubledger,
  expandedRows,
  toggleRow,
  formatCurrency,
}) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="w-5 h-5 text-purple-600" />
          Trainer & Coordinator Sub-ledger - {selectedYear}
        </CardTitle>
        <CardDescription>Earnings breakdown by trainer and coordinator</CardDescription>
      </CardHeader>
      <CardContent>
        {!trainerSubledger ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Trainers */}
            <div>
              <h4 className="font-semibold text-purple-700 mb-3 flex items-center gap-2">
                <Users className="w-4 h-4" /> Trainers
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-purple-50">
                      <th className="text-left p-3">Name</th>
                      <th className="text-right p-3">Earned</th>
                      <th className="text-right p-3">Paid</th>
                      <th className="text-right p-3">Balance</th>
                      <th className="w-10"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(trainerSubledger?.trainers || []).map((t) => (
                      <React.Fragment key={t.user_id}>
                        <tr className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => toggleRow(`trainer-${t.user_id}`)}>
                          <td className="p-3 font-medium flex items-center gap-2">
                            {expandedRows[`trainer-${t.user_id}`] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                            {t.name}
                          </td>
                          <td className="p-3 text-right text-green-600">{formatCurrency(t.total_earned)}</td>
                          <td className="p-3 text-right text-blue-600">{formatCurrency(t.total_paid)}</td>
                          <td className={`p-3 text-right font-semibold ${t.balance > 0 ? 'text-orange-600' : 'text-gray-600'}`}>
                            {formatCurrency(t.balance)}
                          </td>
                          <td className="p-3">
                            <Badge variant="outline">{t.sessions?.length || 0}</Badge>
                          </td>
                        </tr>
                        {expandedRows[`trainer-${t.user_id}`] && t.sessions?.length > 0 && (
                          <tr className="bg-gray-50">
                            <td colSpan={5} className="p-4">
                              <div className="text-xs space-y-2 max-h-40 overflow-y-auto">
                                {t.sessions.slice(0, 10).map((s, idx) => (
                                  <div key={idx} className="flex justify-between items-center bg-white p-2 rounded border">
                                    <span>{s.date} - {s.programme}</span>
                                    <div className="flex items-center gap-2">
                                      <span className="font-semibold">{formatCurrency(s.amount)}</span>
                                      <Badge className={s.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}>
                                        {s.status}
                                      </Badge>
                                    </div>
                                  </div>
                                ))}
                                {t.sessions.length > 10 && <p className="text-gray-500 text-center">...and {t.sessions.length - 10} more</p>}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-purple-100 font-bold">
                      <td className="p-3">TOTAL</td>
                      <td className="p-3 text-right text-green-700">{formatCurrency(trainerSubledger?.totals?.trainer_earned)}</td>
                      <td className="p-3 text-right text-blue-700">{formatCurrency(trainerSubledger?.totals?.trainer_paid)}</td>
                      <td className="p-3 text-right text-orange-700">{formatCurrency(trainerSubledger?.totals?.trainer_balance)}</td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Coordinators */}
            <div>
              <h4 className="font-semibold text-blue-700 mb-3 flex items-center gap-2">
                <UserCheck className="w-4 h-4" /> Coordinators
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-blue-50">
                      <th className="text-left p-3">Name</th>
                      <th className="text-right p-3">Earned</th>
                      <th className="text-right p-3">Paid</th>
                      <th className="text-right p-3">Balance</th>
                      <th className="w-10"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(trainerSubledger?.coordinators || []).map((c) => (
                      <React.Fragment key={c.user_id}>
                        <tr className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => toggleRow(`coord-${c.user_id}`)}>
                          <td className="p-3 font-medium flex items-center gap-2">
                            {expandedRows[`coord-${c.user_id}`] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                            {c.name}
                          </td>
                          <td className="p-3 text-right text-green-600">{formatCurrency(c.total_earned)}</td>
                          <td className="p-3 text-right text-blue-600">{formatCurrency(c.total_paid)}</td>
                          <td className={`p-3 text-right font-semibold ${c.balance > 0 ? 'text-orange-600' : 'text-gray-600'}`}>
                            {formatCurrency(c.balance)}
                          </td>
                          <td className="p-3">
                            <Badge variant="outline">{c.sessions?.length || 0}</Badge>
                          </td>
                        </tr>
                        {expandedRows[`coord-${c.user_id}`] && c.sessions?.length > 0 && (
                          <tr className="bg-gray-50">
                            <td colSpan={5} className="p-4">
                              <div className="text-xs space-y-2 max-h-40 overflow-y-auto">
                                {c.sessions.slice(0, 10).map((s, idx) => (
                                  <div key={idx} className="flex justify-between items-center bg-white p-2 rounded border">
                                    <span>{s.date} - {s.programme}</span>
                                    <div className="flex items-center gap-2">
                                      <span className="font-semibold">{formatCurrency(s.amount)}</span>
                                      <Badge className={s.status === 'paid' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}>
                                        {s.status}
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
                    <tr className="bg-blue-100 font-bold">
                      <td className="p-3">TOTAL</td>
                      <td className="p-3 text-right text-green-700">{formatCurrency(trainerSubledger?.totals?.coordinator_earned)}</td>
                      <td className="p-3 text-right text-blue-700">{formatCurrency(trainerSubledger?.totals?.coordinator_paid)}</td>
                      <td className="p-3 text-right text-orange-700">{formatCurrency(trainerSubledger?.totals?.coordinator_balance)}</td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { TrainerSubledgerTab };
