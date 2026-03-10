// MarketInfoBar.jsx  —  Indian / US market metadata banner (light theme)

import { Globe, Clock, IndianRupee, DollarSign, Building2, Activity } from "lucide-react";
import { isIndianTicker, getCurrencyCode } from "../utils/currency";

export default function MarketInfoBar({ ticker, stockData }) {
  if (!ticker) return null;

  const indian   = isIndianTicker(ticker);
  const currency = getCurrencyCode(ticker);
  const CurrIcon = indian ? IndianRupee : DollarSign;

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

  const tradingStatus = getTradingStatus(indian);

  const pills = [
    { icon: Building2, label: "Exchange", value: exchange, variant: "blue"                              },
    { icon: CurrIcon,  label: "Currency", value: currency, variant: indian ? "orange" : "green"         },
    { icon: Clock,     label: "Hours",    value: hours,    variant: "purple"                            },
    { icon: Activity,  label: "Status",   value: tradingStatus.label,
      variant: tradingStatus.open ? "green" : "red" },
  ];

  const variantMap = {
    blue:   "border-blue-200   bg-blue-50   text-blue-700",
    orange: "border-orange-200 bg-orange-50 text-orange-700",
    green:  "border-green-200  bg-green-50  text-green-700",
    purple: "border-violet-200 bg-violet-50 text-violet-700",
    red:    "border-red-200    bg-red-50    text-red-700",
  };

  return (
    <div className="flex flex-wrap items-center gap-2.5">
      {/* Flag + ticker badge */}
      <div className="flex items-center gap-2 rounded-xl border border-surface-border bg-surface-card px-4 py-2.5 shadow-card">
        <span className="text-lg">{flag}</span>
        <div>
          <p className="text-sm font-bold text-slate-900 font-mono">{ticker}</p>
          <p className="text-[10px] font-medium text-slate-400">{indian ? "Indian Market" : "US Market"}</p>
        </div>
      </div>

      {/* Info pills */}
      {pills.map(({ icon: Icon, label, value, variant }) => (
        <div
          key={label}
          className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium shadow-sm ${variantMap[variant]}`}
        >
          <Icon className="h-3.5 w-3.5 shrink-0" />
          <span className="text-slate-500">{label}:</span>
          <span className="font-semibold">{value}</span>
        </div>
      ))}
    </div>
  );
}

function getTradingStatus(isIndian) {
  const now = new Date();
  const utcH = now.getUTCHours();
  const utcM = now.getUTCMinutes();
  const minutesSinceMidnightUTC = utcH * 60 + utcM;
  const day = now.getUTCDay();

  if (day === 0 || day === 6) return { open: false, label: "Closed (Weekend)" };

  if (isIndian) {
    const openUTC  = 3 * 60 + 45;
    const closeUTC = 10 * 60;
    return minutesSinceMidnightUTC >= openUTC && minutesSinceMidnightUTC < closeUTC
      ? { open: true,  label: "Market Open" }
      : { open: false, label: "Closed" };
  } else {
    const openUTC  = 13 * 60 + 30;
    const closeUTC = 20 * 60;
    return minutesSinceMidnightUTC >= openUTC && minutesSinceMidnightUTC < closeUTC
      ? { open: true,  label: "Market Open" }
      : { open: false, label: "Closed" };
  }
}
