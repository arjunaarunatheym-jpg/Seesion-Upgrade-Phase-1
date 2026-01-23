/**
 * GeneralLedgerTab Component - Extracted from ProfitLossLedger
 * Displays double-entry journal entries and trial balance
 */
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Loader2, BookOpen, Printer, FileSpreadsheet, BarChart3 } from 'lucide-react';

const GeneralLedgerTab = ({
  selectedYear,
  selectedMonth,
  setSelectedMonth,
  generalLedger,
  months,
  formatCurrency,
  handlePrintGL,
  handleDownloadGL,
}) => {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between flex-wrap gap-4">
        <div>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-emerald-600" />
            General Ledger - {selectedYear}
          </CardTitle>
          <CardDescription>Double-entry journal with trial balance</CardDescription>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Select value={selectedMonth?.toString() || 'all'} onValueChange={(v) => setSelectedMonth(v === 'all' ? null : parseInt(v))}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="All Months" />
            </SelectTrigger>
            <SelectContent>
              {months.map((m) => (
                <SelectItem key={m.value || 'all'} value={m.value?.toString() || 'all'}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handlePrintGL} disabled={!generalLedger}>
            <Printer className="w-4 h-4 mr-2" /> Print
          </Button>
          <Button variant="outline" onClick={handleDownloadGL} disabled={!generalLedger} className="text-emerald-600 border-emerald-300 hover:bg-emerald-50">
            <FileSpreadsheet className="w-4 h-4 mr-2" /> Download CSV
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {!generalLedger ? (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Status Badge */}
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                {generalLedger.entries?.length || 0} journal entries
              </p>
              <Badge className={generalLedger.totals?.is_balanced ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                {generalLedger.totals?.is_balanced ? '✓ Balanced' : '✗ Unbalanced'}
              </Badge>
            </div>

            {/* Journal Entries Table */}
            <div className="overflow-x-auto border rounded-lg">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-emerald-50 border-b">
                    <th className="text-center p-2 font-semibold w-16">#</th>
                    <th className="text-left p-2 font-semibold w-24">Date</th>
                    <th className="text-left p-2 font-semibold w-24">Reference</th>
                    <th className="text-left p-2 font-semibold w-20">Account</th>
                    <th className="text-left p-2 font-semibold">Account Name</th>
                    <th className="text-left p-2 font-semibold">Description</th>
                    <th className="text-right p-2 font-semibold w-24 text-red-600">Debit</th>
                    <th className="text-right p-2 font-semibold w-24 text-green-600">Credit</th>
                  </tr>
                </thead>
                <tbody>
                  {(generalLedger.entries || []).slice(0, 200).map((entry, idx) => (
                    <tr key={idx} className={`border-b hover:bg-gray-50 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}`}>
                      <td className="p-2 text-center text-gray-400">{entry.entry_id}</td>
                      <td className="p-2">{entry.date}</td>
                      <td className="p-2 font-mono text-xs">{entry.reference}</td>
                      <td className="p-2 font-mono">{entry.account_code}</td>
                      <td className="p-2">{entry.account_name}</td>
                      <td className="p-2 text-gray-600">{entry.description}</td>
                      <td className="p-2 text-right text-red-600 font-mono">
                        {entry.debit > 0 ? formatCurrency(entry.debit) : ''}
                      </td>
                      <td className="p-2 text-right text-green-600 font-mono">
                        {entry.credit > 0 ? formatCurrency(entry.credit) : ''}
                      </td>
                    </tr>
                  ))}
                  {generalLedger.entries?.length > 200 && (
                    <tr className="bg-yellow-50">
                      <td colSpan={8} className="p-3 text-center text-yellow-700">
                        Showing first 200 of {generalLedger.entries.length} entries. Download CSV for full data.
                      </td>
                    </tr>
                  )}
                </tbody>
                <tfoot>
                  <tr className="bg-emerald-600 text-white font-bold">
                    <td colSpan={6} className="p-3 text-right">TOTALS:</td>
                    <td className="p-3 text-right">{formatCurrency(generalLedger.totals?.total_debit)}</td>
                    <td className="p-3 text-right">{formatCurrency(generalLedger.totals?.total_credit)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>

            {/* Trial Balance */}
            <div>
              <h4 className="font-semibold text-emerald-700 mb-3 flex items-center gap-2">
                <BarChart3 className="w-4 h-4" /> Trial Balance
              </h4>
              <div className="overflow-x-auto border rounded-lg">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-100 border-b">
                      <th className="text-left p-2 font-semibold">Account Code</th>
                      <th className="text-left p-2 font-semibold">Account Name</th>
                      <th className="text-left p-2 font-semibold">Type</th>
                      <th className="text-right p-2 font-semibold text-red-600">Debit</th>
                      <th className="text-right p-2 font-semibold text-green-600">Credit</th>
                      <th className="text-right p-2 font-semibold">Net</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(generalLedger.trial_balance || []).map((tb) => (
                      <tr key={tb.account_code} className="border-b hover:bg-gray-50">
                        <td className="p-2 font-mono">{tb.account_code}</td>
                        <td className="p-2">{tb.account_name}</td>
                        <td className="p-2">
                          <Badge variant="outline" className={
                            tb.account_type === 'Asset' ? 'border-blue-300 text-blue-600' :
                            tb.account_type === 'Liability' ? 'border-purple-300 text-purple-600' :
                            tb.account_type === 'Income' ? 'border-green-300 text-green-600' :
                            'border-red-300 text-red-600'
                          }>{tb.account_type}</Badge>
                        </td>
                        <td className="p-2 text-right font-mono text-red-600">
                          {tb.debit > 0 ? formatCurrency(tb.debit) : '-'}
                        </td>
                        <td className="p-2 text-right font-mono text-green-600">
                          {tb.credit > 0 ? formatCurrency(tb.credit) : '-'}
                        </td>
                        <td className={`p-2 text-right font-mono font-semibold ${tb.net >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                          {formatCurrency(Math.abs(tb.net))} {tb.net >= 0 ? 'DR' : 'CR'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export { GeneralLedgerTab };
