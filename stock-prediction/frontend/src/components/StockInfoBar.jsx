// StockInfoBar.jsx  —  Quick stats bar (last price, change, volume, etc.)

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
    const pclose = parseFloat(prev.Close ?? prev.close);
    const change = close - pclose;
    const pct    = (change / pclose) * 100;
    const high   = parseFloat(latest.High ?? latest.high);
    const low    = parseFloat(latest.Low  ?? latest.low);
    const vol    = parseFloat(latest.Volume ?? latest.volume);
    const date   = latest.date ?? latest.Date;

    return { close, change, pct, high, low, vol, date };
  }, [stockData]);

  if (!stats) return null;

  const up   = stats.change >= 0;
  const Icon = up ? TrendingUp : stats.change === 0 ? Minus : TrendingDown;
  const clr  = up ? "text-green-400" : "text-red-400";
  const bg   = up ? "bg-green-500/10" : "bg-red-500/10";
  const sym  = getCurrencySymbol(ticker);
  const CurrIcon = isIndianTicker(ticker) ? IndianRupee : DollarSign;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {/* Ticker */}
      <div className="col-span-2 sm:col-span-1 flex items-center gap-3 rounded-xl border border-surface-border bg-surface-card px-4 py-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/20">
          <span className="text-sm font-bold text-blue-400">{ticker}</span>
        </div>
        <div>
          <p className="text-xs text-slate-500">Symbol</p>
          <p className="font-semibold text-white">{ticker}</p>
        </div>
      </div>

      {/* Last Close */}
      <StatCard icon={CurrIcon} label="Last Close" color="blue">
        <span className="text-xl font-bold text-white">{sym}{stats.close.toFixed(2)}</span>
      </StatCard>

      {/* Change */}
      <StatCard icon={Icon} label="Daily Change" color={up ? "green" : "red"}>
        <span className={`text-xl font-bold ${clr}`}>
          {up ? "+" : ""}{stats.change.toFixed(2)}
        </span>
        <span className={`ml-1 text-sm ${clr}`}>({stats.pct.toFixed(2)}%)</span>
      </StatCard>

      {/* High / Low */}
      <StatCard icon={BarChart2} label="Day Range" color="purple">
        <span className="text-sm font-semibold text-green-400">{sym}{stats.high.toFixed(2)}</span>
        <span className="mx-1 text-slate-500">–</span>
        <span className="text-sm font-semibold text-red-400">{sym}{stats.low.toFixed(2)}</span>
      </StatCard>

      {/* Volume */}
      <StatCard icon={BarChart2} label="Volume" color="teal">
        <span className="text-lg font-bold text-white">{fmtVol(stats.vol)}</span>
      </StatCard>

      {/* Date */}
      <StatCard icon={Calendar} label="Last Date" color="orange">
        <span className="text-sm font-semibold text-white">{stats.date}</span>
      </StatCard>
    </div>
  );
}

function StatCard({ icon: Icon, label, color, children }) {
  const colorMap = {
    blue:   "text-blue-400",
    green:  "text-green-400",
    red:    "text-red-400",
    purple: "text-purple-400",
    teal:   "text-teal-400",
    orange: "text-orange-400",
  };
  return (
    <div className="flex flex-col justify-between rounded-xl border border-surface-border bg-surface-card px-4 py-3">
      <div className="flex items-center gap-1.5 text-xs text-slate-500">
        <Icon className={`h-3.5 w-3.5 ${colorMap[color] || "text-slate-400"}`} />
        {label}
      </div>
      <div className="mt-1 flex flex-wrap items-baseline">{children}</div>
    </div>
  );
}

function fmtVol(v) {
  if (v >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (v >= 1e3) return (v / 1e3).toFixed(1) + "K";
  return v.toFixed(0);
}
