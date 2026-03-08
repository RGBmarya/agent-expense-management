"use client";

import clsx from "clsx";
import { Download, FileSpreadsheet, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { departmentCosts, invoiceData } from "@/lib/mock-data";
import { formatCurrency, formatNumber, formatTokens } from "@/lib/format";

function exportCSV(headers: string[], rows: string[][], filename: string) {
  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  // Group department costs
  const departments = departmentCosts.reduce<
    Record<string, { teams: typeof departmentCosts; total: number }>
  >((acc, row) => {
    if (!acc[row.department]) acc[row.department] = { teams: [], total: 0 };
    acc[row.department].teams.push(row);
    acc[row.department].total += row.spend;
    return acc;
  }, {});

  const grandTotal = departmentCosts.reduce((s, r) => s + r.spend, 0);

  function handleExportDepartments() {
    const headers = ["Department", "Team", "Spend", "Tokens", "Requests", "Avg Cost/Req"];
    const rows = departmentCosts.map((r) => [
      r.department,
      r.team,
      r.spend.toFixed(2),
      String(r.tokens),
      String(r.requests),
      r.avgCostPerRequest.toFixed(4),
    ]);
    exportCSV(headers, rows, "department-costs.csv");
  }

  function handleExportInvoice() {
    const headers = ["Provider", "Invoice Amount", "Tracked Amount", "Delta"];
    const rows = invoiceData.invoices.map((r) => [
      r.provider,
      r.invoiceAmount.toFixed(2),
      r.trackedAmount.toFixed(2),
      r.delta.toFixed(2),
    ]);
    exportCSV(headers, rows, "invoice-reconciliation.csv");
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Reports</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Monthly cost breakdowns and invoice reconciliation.
        </p>
      </div>

      {/* Monthly Cost Report */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-text-primary">
            Monthly Cost Report &mdash; March 2026
          </h3>
          <button
            onClick={handleExportDepartments}
            className="inline-flex items-center gap-2 rounded-lg border border-surface-border px-3 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:bg-surface-secondary"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border">
                <th className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Department / Team
                </th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Spend
                </th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Tokens
                </th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Requests
                </th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Avg $/Req
                </th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                  % of Total
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {Object.entries(departments).map(([dept, { teams, total }]) => (
                <>
                  <tr key={dept} className="bg-surface-secondary/50">
                    <td className="px-3 py-2.5 font-semibold text-text-primary">{dept}</td>
                    <td className="px-3 py-2.5 text-right font-semibold text-text-primary">
                      {formatCurrency(total)}
                    </td>
                    <td className="px-3 py-2.5 text-right font-medium text-text-secondary">
                      {formatTokens(teams.reduce((s, t) => s + t.tokens, 0))}
                    </td>
                    <td className="px-3 py-2.5 text-right font-medium text-text-secondary">
                      {formatNumber(teams.reduce((s, t) => s + t.requests, 0))}
                    </td>
                    <td className="px-3 py-2.5 text-right text-text-secondary">&mdash;</td>
                    <td className="px-3 py-2.5 text-right font-medium text-text-secondary">
                      {((total / grandTotal) * 100).toFixed(1)}%
                    </td>
                  </tr>
                  {teams.map((t) => (
                    <tr key={t.team} className="hover:bg-surface-secondary/30">
                      <td className="px-3 py-2 pl-8 text-text-secondary">{t.team}</td>
                      <td className="px-3 py-2 text-right text-text-primary">
                        {formatCurrency(t.spend)}
                      </td>
                      <td className="px-3 py-2 text-right text-text-secondary">
                        {formatTokens(t.tokens)}
                      </td>
                      <td className="px-3 py-2 text-right text-text-secondary">
                        {formatNumber(t.requests)}
                      </td>
                      <td className="px-3 py-2 text-right text-text-secondary">
                        {formatCurrency(t.avgCostPerRequest)}
                      </td>
                      <td className="px-3 py-2 text-right text-text-muted">
                        {((t.spend / grandTotal) * 100).toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-surface-border">
                <td className="px-3 py-3 text-sm font-bold text-text-primary">Total</td>
                <td className="px-3 py-3 text-right text-sm font-bold text-text-primary">
                  {formatCurrency(grandTotal)}
                </td>
                <td className="px-3 py-3 text-right font-semibold text-text-secondary">
                  {formatTokens(departmentCosts.reduce((s, r) => s + r.tokens, 0))}
                </td>
                <td className="px-3 py-3 text-right font-semibold text-text-secondary">
                  {formatNumber(departmentCosts.reduce((s, r) => s + r.requests, 0))}
                </td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Invoice Reconciliation */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-text-primary">
            Invoice Reconciliation
          </h3>
          <button
            onClick={handleExportInvoice}
            className="inline-flex items-center gap-2 rounded-lg border border-surface-border px-3 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:bg-surface-secondary"
          >
            <FileSpreadsheet className="h-4 w-4" />
            Export CSV
          </button>
        </div>
        <p className="mt-1 text-sm text-text-muted">
          Compare tracked usage against actual provider invoices.
        </p>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border">
                <th className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Provider
                </th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Invoice Amount
                </th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Tracked Amount
                </th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Delta
                </th>
                <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Delta %
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {invoiceData.invoices.map((inv) => {
                const deltaPct = (inv.delta / inv.invoiceAmount) * 100;
                return (
                  <tr key={inv.provider} className="hover:bg-surface-secondary/30">
                    <td className="px-3 py-3 font-medium text-text-primary">{inv.provider}</td>
                    <td className="px-3 py-3 text-right text-text-primary">
                      {formatCurrency(inv.invoiceAmount)}
                    </td>
                    <td className="px-3 py-3 text-right text-text-primary">
                      {formatCurrency(inv.trackedAmount)}
                    </td>
                    <td className="px-3 py-3 text-right">
                      <span className="inline-flex items-center gap-1 text-warning">
                        <ArrowUpRight className="h-3.5 w-3.5" />
                        {formatCurrency(inv.delta)}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right text-warning font-medium">
                      {deltaPct.toFixed(1)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-surface-border">
                <td className="px-3 py-3 font-bold text-text-primary">Total</td>
                <td className="px-3 py-3 text-right font-bold text-text-primary">
                  {formatCurrency(invoiceData.invoices.reduce((s, i) => s + i.invoiceAmount, 0))}
                </td>
                <td className="px-3 py-3 text-right font-bold text-text-primary">
                  {formatCurrency(invoiceData.invoices.reduce((s, i) => s + i.trackedAmount, 0))}
                </td>
                <td className="px-3 py-3 text-right font-bold text-warning">
                  {formatCurrency(invoiceData.invoices.reduce((s, i) => s + i.delta, 0))}
                </td>
                <td />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}
