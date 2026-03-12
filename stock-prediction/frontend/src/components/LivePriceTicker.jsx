/**
 * LivePriceTicker.jsx — Real-time price badge with WS status indicator
 * =====================================================================
 * Shows the latest streaming price, change %, trend badge, and a
 * colour-coded connection dot.  Fully keyboard-accessible and WCAG AA.
 */

import { memo } from "react";
import { TrendingUp, TrendingDown, Minus, Wifi, WifiOff, Loader2, AlertCircle } from "lucide-react";
import { WS_STATUS } from "../hooks/useWebSocket";
import { getCurrencySymbol } from "../utils/currency";

// ── WS status chip ──────────────────────────────────────────────────────────

const STATUS_META = {
  [WS_STATUS.OPEN]:       { color: "bg-green-500",  label: "Live",         Icon: Wifi      },
  [WS_STATUS.CONNECTING]: { color: "bg-amber-400",  label: "Connecting…",  Icon: Loader2   },
  [WS_STATUS.CLOSED]:     { color: "bg-slate-400",  label: "Disconnected", Icon: WifiOff   },
  [WS_STATUS.ERROR]:      { color: "bg-red-500",    label: "Error",        Icon: AlertCircle },
  [WS_STATUS.IDLE]:       { color: "bg-slate-300",  label: "Idle",         Icon: WifiOff   },
};

function WsStatusDot({ status }) {
  const meta = STATUS_META[status] ?? STATUS_META[WS_STATUS.IDLE];
  const { color, label, Icon } = meta;
  const isSpinning = status === WS_STATUS.CONNECTING;

  return (
    <span
      role="status"
      aria-label={`WebSocket: ${label}`}
      className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 shadow-sm"
    >
      <span
        className={`relative flex h-2 w-2 items-center justify-center`}
        aria-hidden="true"
      >
        {status === WS_STATUS.OPEN && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
        )}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${color}`} />
      </span>
      <Icon className={`h-3 w-3 ${isSpinning ? "animate-spin" : ""}`} />
      {label}
    </span>
  );
}

// ── Trend badge ─────────────────────────────────────────────────────────────

function TrendBadge({ trend }) {
  if (!trend) return null;
  const cfg = {
    up:   { label: "↑ Bullish", className: "border-green-200 bg-green-50 text-green-700" },
    down: { label: "↓ Bearish", className: "border-red-200   bg-red-50   text-red-700"   },
    flat: { label: "→ Neutral", className: "border-slate-200 bg-slate-50 text-slate-600"  },
  };
  const { label, className } = cfg[trend] ?? cfg.flat;
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${className}`}>
      {label}
    </span>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

function LivePriceTicker({ latestPrice, wsStatus, ticker }) {
  if (!latestPrice) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-surface-border bg-surface-card px-4 py-3 shadow-card">
        <WsStatusDot status={wsStatus} />
        <p className="text-sm text-slate-400">
          {wsStatus === WS_STATUS.CONNECTING ? "Connecting to live feed…" : "Waiting for live data…"}
        </p>
      </div>
    );
  }

  const sym      = getCurrencySymbol(ticker);
  const up       = (latestPrice.change ?? 0) >= 0;
  const TrendIcon = up ? TrendingUp : TrendingDown;
  const changeColor = up ? "text-green-600" : "text-red-600";

  // Format timestamp
  let timeStr = "";
  try {
    timeStr = new Date(latestPrice.timestamp).toLocaleTimeString([], {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch { /* ignore */ }

  return (
    <div
      role="region"
      aria-label={`Live price for ${ticker}`}
      aria-live="polite"
      aria-atomic="true"
      className="flex flex-wrap items-center gap-3 rounded-xl border border-surface-border bg-surface-card px-4 py-3 shadow-card"
    >
      {/* WS status */}
      <WsStatusDot status={wsStatus} />

      {/* Simulated badge */}
      {latestPrice.simulated && (
        <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-600">
          simulated
        </span>
      )}

      {/* Price */}
      <div className="flex items-baseline gap-1.5">
        <span className="font-mono text-2xl font-extrabold text-slate-900">
          {sym}{latestPrice.price?.toFixed(2)}
        </span>
        <span className={`flex items-center gap-0.5 font-mono text-sm font-semibold ${changeColor}`}>
          <TrendIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {up ? "+" : ""}{latestPrice.change?.toFixed(2)} ({up ? "+" : ""}{latestPrice.change_pct?.toFixed(2)}%)
        </span>
      </div>

      {/* LSTM prediction */}
      {latestPrice.prediction && (
        <div className="flex items-center gap-1.5 border-l border-slate-200 pl-3">
          <span className="text-xs text-slate-500">AI target:</span>
          <span className="font-mono text-sm font-bold text-brand-600">
            {sym}{latestPrice.prediction.toFixed(2)}
          </span>
          <TrendBadge trend={latestPrice.trend} />
        </div>
      )}

      {/* Timestamp */}
      {timeStr && (
        <time
          dateTime={latestPrice.timestamp}
          className="ml-auto text-xs text-slate-400"
          aria-label={`Last updated at ${timeStr}`}
        >
          {timeStr}
        </time>
      )}
    </div>
  );
}

export default memo(LivePriceTicker);
