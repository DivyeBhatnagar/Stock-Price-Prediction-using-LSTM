// ForecastTable.jsx  —  Tabular view of predicted prices (light theme)

import { useMemo } from "react";
import { Download, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { getCurrencySymbol } from "../utils/currency";

export default function ForecastTable({ prediction, ticker }) {
  const rows = useMemo(() => {
    if (!prediction?.forecast?.length) return [];
    return prediction.forecast.map((r, i, arr) => {
      const prev = i > 0 ? arr[i - 1].price : r.price;
      const chg  = r.price - prev;
      const pct  = i > 0 ? (chg / prev) * 100 : 0;
      return { ...r, chg, pct, i };
    });
  }, [prediction]);

  if (!rows.length) return null;

  const sym = getCurrencySymbol(ticker);

  const downloadCSV = () => {
    const header = "date,price,change,pct_change\n";
    const body   = rows.map((r) =>
      `${r.date},${r.price.toFixed(4)},${r.chg.toFixed(4)},${r.pct.toFixed(4)}`
    ).join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `${ticker}_forecast.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card shadow-card">

      {/* Header */}
      <div className="flex items-center justify-between border-b border-surface-border px-5 py-4">
        <div>
          <h3 className="text-base font-semibold text-slate-900">
            {prediction.n_days}-Day Forecast — {ticker}
          </h3>
        </div>
        <button
          onClick={downloadCSV}
          className="flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-sm transition-colors duration-200 hover:border-brand-400 hover:text-brand-600"
        >
          <Download className="h-3.5 w-3.5" /> Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="max-h-72 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-slate-50">
            <tr className="border-b border-surface-border">
              {["#", "Date", "Predicted Price", "Change", "%"].map((h) => (
                <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {rows.map((r) => {
              const up = r.chg > 0;
              const dn = r.chg < 0;
              const Icon = up ? TrendingUp : dn ? TrendingDown : Minus;
              return (
                <tr key={r.i} className="transition-colors duration-150 hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-xs font-medium text-slate-400">{r.i + 1}</td>
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-700">{r.date}</td>
                  <td className="px-4 py-2.5 font-mono text-sm font-semibold text-slate-900">
                    {sym}{r.price.toFixed(2)}
                  </td>
                  <td className={`px-4 py-2.5 font-mono text-xs font-semibold ${
                    up ? "text-green-600" : dn ? "text-red-600" : "text-slate-400"
                  }`}>
                    <span className="flex items-center gap-1">
                      <Icon className="h-3 w-3" />
                      {up ? "+" : ""}{r.chg.toFixed(2)}
                    </span>
                  </td>
                  <td className={`px-4 py-2.5 font-mono text-xs font-semibold ${
                    up ? "text-green-600" : dn ? "text-red-600" : "text-slate-400"
                  }`}>
                    {r.i > 0 ? `${up ? "+" : ""}${r.pct.toFixed(2)}%` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
