// ForecastTable.jsx  —  Tabular view of predicted prices with download

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
    a.href     = url;
    a.download = `${ticker}_forecast.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card shadow-xl">
      <div className="flex items-center justify-between border-b border-surface-border px-5 py-4">
        <h3 className="font-semibold text-white">
          📅 {prediction.n_days}-Day Forecast — {ticker}
        </h3>
        <button
          onClick={downloadCSV}
          className="flex items-center gap-1.5 rounded-lg border border-surface-border px-3 py-1.5 text-xs font-semibold text-slate-400 transition hover:border-blue-500 hover:text-blue-400"
        >
          <Download className="h-3.5 w-3.5" /> Export CSV
        </button>
      </div>

      <div className="max-h-72 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-surface-card">
            <tr className="border-b border-surface-border">
              {["#", "Date", "Predicted Price", "Change", "%"].map((h) => (
                <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const up  = r.chg > 0;
              const dn  = r.chg < 0;
              const Icon = up ? TrendingUp : dn ? TrendingDown : Minus;
              return (
                <tr key={r.i}
                  className="border-b border-surface-border/50 transition hover:bg-white/5"
                >
                  <td className="px-4 py-2.5 text-xs text-slate-500">{r.i + 1}</td>
                  <td className="px-4 py-2.5 font-mono text-slate-300">{r.date}</td>
                  <td className="px-4 py-2.5 font-mono font-semibold text-white">
                    {sym}{r.price.toFixed(2)}
                  </td>
                  <td className={`px-4 py-2.5 font-mono text-xs ${up ? "text-green-400" : dn ? "text-red-400" : "text-slate-400"}`}>
                    <span className="flex items-center gap-1">
                      <Icon className="h-3 w-3" />
                      {up ? "+" : ""}{r.chg.toFixed(2)}
                    </span>
                  </td>
                  <td className={`px-4 py-2.5 font-mono text-xs ${up ? "text-green-400" : dn ? "text-red-400" : "text-slate-400"}`}>
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
