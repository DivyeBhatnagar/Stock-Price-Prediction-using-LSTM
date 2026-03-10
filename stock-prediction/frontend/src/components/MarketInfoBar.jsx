// MarketInfoBar.jsx  —  Indian / US market metadata banner

import { Globe, Clock, IndianRupee, DollarSign, Building2, TrendingUp } from "lucide-react";
import { isIndianTicker, getCurrencyCode } from "../utils/currency";

export default function MarketInfoBar({ ticker, stockData }) {
  if (!ticker) return null;

  const indian   = isIndianTicker(ticker);
  const currency = getCurrencyCode(ticker);
  const CurrIcon = indian ? IndianRupee : DollarSign;

  // Derive exchange name
  let exchange = "NYSE / NASDAQ";
  let flag     = "🇺🇸";
  let hours    = "09:30 – 16:00 ET";

  if (indian) {
    flag = "🇮🇳";
    hours = "09:15 – 15:30 IST";
    if (ticker.endsWith(".BO"))       exchange = "BSE (Bombay Stock Exchange)";
    else if (ticker.startsWith("^"))  exchange = "Index";
    else                              exchange = "NSE (National Stock Exchange)";
  }

  // Simple trading-hours status (IST = UTC+5:30, ET = UTC-5/-4)
  const tradingStatus = getTradingStatus(indian);

  const pills = [
    { icon: Globe,     label: "Exchange",  value: exchange,    color: "blue"   },
    { icon: CurrIcon,  label: "Currency",  value: currency,    color: indian ? "orange" : "green" },
    { icon: Clock,     label: "Hours",     value: hours,       color: "purple" },
    {
      icon: TrendingUp,
      label: "Status",
      value: tradingStatus.label,
      color: tradingStatus.open ? "green" : "red",
    },
  ];

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Flag + ticker badge */}
      <div className="flex items-center gap-2 rounded-xl border border-surface-border bg-surface-card px-4 py-2.5 shadow">
        <span className="text-xl">{flag}</span>
        <div>
          <p className="text-sm font-bold text-white">{ticker}</p>
          <p className="text-[10px] text-slate-500">{indian ? "Indian Market" : "US Market"}</p>
        </div>
      </div>

      {/* Info pills */}
      {pills.map(({ icon: Icon, label, value, color }) => (
        <div
          key={label}
          className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs
            ${color === "blue"   ? "border-blue-500/30   bg-blue-500/10   text-blue-400"   :
              color === "orange" ? "border-orange-500/30 bg-orange-500/10 text-orange-400" :
              color === "green"  ? "border-green-500/30  bg-green-500/10  text-green-400"  :
              color === "purple" ? "border-purple-500/30 bg-purple-500/10 text-purple-400" :
              "border-red-500/30 bg-red-500/10 text-red-400"
            }`}
        >
          <Icon className="h-3.5 w-3.5" />
          <span className="font-medium text-slate-400">{label}:</span>
          <span className="font-semibold">{value}</span>
        </div>
      ))}
    </div>
  );
}

/** Approximate check whether the market is currently open */
function getTradingStatus(isIndian) {
  const now = new Date();
  const utcH = now.getUTCHours();
  const utcM = now.getUTCMinutes();
  const minutesSinceMidnightUTC = utcH * 60 + utcM;
  const day = now.getUTCDay(); // 0=Sun, 6=Sat

  if (day === 0 || day === 6) return { open: false, label: "Closed (Weekend)" };

  if (isIndian) {
    // IST = UTC + 5:30 → Market 09:15–15:30 IST = 03:45–10:00 UTC
    const openUTC  = 3 * 60 + 45;
    const closeUTC = 10 * 60;
    if (minutesSinceMidnightUTC >= openUTC && minutesSinceMidnightUTC < closeUTC) {
      return { open: true, label: "Market Open 🟢" };
    }
    return { open: false, label: "Closed" };
  } else {
    // ET ≈ UTC - 4 (EDT) → Market 09:30–16:00 ET = 13:30–20:00 UTC
    const openUTC  = 13 * 60 + 30;
    const closeUTC = 20 * 60;
    if (minutesSinceMidnightUTC >= openUTC && minutesSinceMidnightUTC < closeUTC) {
      return { open: true, label: "Market Open 🟢" };
    }
    return { open: false, label: "Closed" };
  }
}
