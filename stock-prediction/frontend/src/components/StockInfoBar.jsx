// StockInfoBar.jsx  —  Quick stats bar (light theme)

import { TrendingUp, TrendingDown, Minus, DollarSign, BarChart2, Calendar, IndianRupee } from "lucide-react";
import { useMemo } from "react";
import { getCurrencySymbol, isIndianTicker } from "../utils/currency";

export default function StockInfoBar({ stockData, ticker }) {
  const stats = useMemo(() => {
    if (!stockData?.data?.length) return null;
    const rows   = stockData.data;
    const latest = rows[rows.length - 1];
    const prev   = rows.length > 1 ? rows[rows.length - 2] : latest;

    const close  = parseFloat(latest.Close ?? latest.close);
    const pclose = parseFloat(prev.Close   ?? prev.close);
    const change = close - pclose;
    const pct    = (change / pclose) * 100;
    const high   = parseFloat(latest.High   ?? latest.high);
    const low    = parseFloat(latest.Low    ?? latest.low);
    const vol    = parseFloat(latest.Volume ?? latest.volume);
    const date   = latest.date ?? latest.Date;
    return { close, change, pct, high, low, vol, date };
  }, [stockData]);

  if (!stats) return null;

  const up       = stats.change >= 0;
  const Icon     = up ? TrendingUp : stats.change === 0 ? Minus : TrendingDown;
  const sym      = getCurrencySymbol(ticker);
  const CurrIcon = isIndianTicker(ticker) ? IndianRupee : DollarSign;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">

      {/* Ticker badge */}
      <div className="col-span-2 flex items-center gap-3 rounded-xl border border-surface-border bg-surface-card px-4 py-3 shadow-card sm:col-span-1">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50">
          <span className="text-[10px] font-bold text-brand-700 leading-none text-center">{ticker.split(".")[0]}</span>
        </div>
        <div>
          <p className="text-xs font-medium text-slate-400">Symbol</p>
          <p className="font-semibold text-slate-900 font-mono text-sm">{ticker}</p>
        </div>
      </div>

      {/* Last Close */}
      <StatCard icon={CurrIcon} label="Last Close" accentColor="border-brand-500">
        <span className="font-mono text-xl font-bold text-slate-900">{sym}{stats.close.toFixed(2)}</span>
      </StatCard>

      {/* Daily Change */}
      <StatCard
        icon={Icon}
        label="Daily Change"
        accentColor={up ? "border-green-500" : "border-red-500"}
      >
        <span className={`font-mono text-xl font-bold ${up ? "text-green-600" : "text-red-600"}`}>
          {up ? "+" : ""}{stats.change.toFixed(2)}
        </span>
        <span className={`ml-1 font-mono text-xs font-semibold ${up ? "text-green-600" : "text-red-600"}`}>
          ({stats.pct.toFixed(2)}%)
        </span>
      </StatCard>

      {/* Day Range */}
      <StatCard icon={BarChart2} label="Day Range" accentColor="border-violet-500">
        <span className="font-mono text-sm font-semibold text-green-600">{sym}{stats.high.toFixed(2)}</span>
        <span className="mx-1 text-slate-300">–</span>
        <span className="font-mono text-sm font-semibold text-red-600">{sym}{stats.low.toFixed(2)}</span>
      </StatCard>

      {/* Volume */}
      <StatCard icon={BarChart2} label="Volume" accentColor="border-cyan-500">
        <span className="font-mono text-lg font-bold text-slate-900">{fmtVol(stats.vol)}</span>
      </StatCard>

      {/* Last Date */}
      <StatCard icon={Calendar} label="Last Date" accentColor="border-amber-500">
        <span className="font-mono text-sm font-semibold text-slate-900">{stats.date}</span>
      </StatCard>
    </div>
  );
}

function StatCard({ icon: Icon, label, accentColor, children }) {
  return (
    <div className={`flex flex-col justify-between rounded-xl border border-surface-border bg-surface-card px-4 py-3 shadow-card border-l-2 ${accentColor}`}>
      <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="mt-1.5 flex flex-wrap items-baseline">{children}</div>
    </div>
  );
}

function fmtVol(v) {
  if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (v >= 1e3) return (v / 1e3).toFixed(1)  + "K";
  return v.toFixed(0);
}
