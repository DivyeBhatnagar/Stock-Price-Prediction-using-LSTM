/**
 * LivePriceChart.jsx — Streaming real-time price chart
 * ======================================================
 * Renders a continuously-updating line chart using Recharts.
 * - Updates in place without full re-render (Recharts ComposedChart)
 * - Preserves the X-axis window (sliding last N points)
 * - Debounced via requestAnimationFrame in useLivePrice hook
 * - WCAG AA accessible: ARIA label, keyboard-navigable tooltip
 */

import { memo, useMemo } from "react";
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from "recharts";
import { format, parseISO } from "date-fns";
import { Activity } from "lucide-react";
import { getCurrencySymbol } from "../utils/currency";

// ── Custom tooltip ──────────────────────────────────────────────────────────

function LiveTooltip({ active, payload, label, ticker }) {
  if (!active || !payload?.length) return null;
  const sym = getCurrencySymbol(ticker);

  let timeStr = label;
  try { timeStr = new Date(label).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }); }
  catch { /* keep raw */ }

  return (
    <div
      role="tooltip"
      className="rounded-xl border border-surface-border bg-white px-4 py-3 shadow-card-md"
    >
      <p className="mb-2 text-xs font-semibold text-slate-500">{timeStr}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2 text-sm">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} aria-hidden="true" />
          <span className="text-slate-600">{p.name}:</span>
          <span className="font-mono font-semibold text-slate-900">
            {sym}{Number(p.value).toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── No-data placeholder ─────────────────────────────────────────────────────

function EmptyState({ message }) {
  return (
    <div className="flex h-[300px] flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-200">
      <Activity className="h-8 w-8 text-slate-300" aria-hidden="true" />
      <p className="text-sm text-slate-400">{message}</p>
    </div>
  );
}

// ── Main chart ──────────────────────────────────────────────────────────────

function LivePriceChart({ priceHistory, latestPrice, ticker, height = 300 }) {
  const sym = getCurrencySymbol(ticker);

  // Build chart data — only re-derive when priceHistory changes
  const chartData = useMemo(() => priceHistory.map((p) => ({
    time:       p.time,
    price:      p.price,
    prediction: p.prediction,
  })), [priceHistory]);

  const hasPrediction = chartData.some((d) => d.prediction != null);

  // Determine Y-axis domain with 2% padding
  const prices = chartData.map((d) => d.price).filter(Boolean);
  const preds  = hasPrediction ? chartData.map((d) => d.prediction).filter(Boolean) : [];
  const all    = [...prices, ...preds];
  const minVal = all.length ? Math.min(...all) : "auto";
  const maxVal = all.length ? Math.max(...all) : "auto";
  const pad    = all.length ? (maxVal - minVal) * 0.05 : 0;
  const domain = all.length ? [minVal - pad, maxVal + pad] : ["auto", "auto"];

  const tickFormatter = (ts) => {
    try { return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
    catch { return ts; }
  };

  if (!priceHistory.length) {
    return <EmptyState message="Waiting for live data stream…" />;
  }

  return (
    <section
      aria-label={`Live streaming price chart for ${ticker}`}
      className="rounded-2xl border border-surface-border bg-surface-card p-5 shadow-card"
    >
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold text-slate-900">
            Live Stream — {ticker}
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            Teal = Live Price · Purple = LSTM Target · Last {priceHistory.length} ticks
          </p>
        </div>
        {latestPrice?.simulated && (
          <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
            Market closed — simulated
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={chartData}
          margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
          <XAxis
            dataKey="time"
            tickFormatter={tickFormatter}
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "#E2E8F0" }}
            interval="preserveStartEnd"
            minTickGap={40}
          />
          <YAxis
            domain={domain}
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${sym}${Number(v).toFixed(0)}`}
            width={62}
          />
          <Tooltip content={<LiveTooltip ticker={ticker} />} />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: "12px", paddingTop: "8px", color: "#475569" }}
          />

          {/* Live price line */}
          <Line
            type="monotone"
            dataKey="price"
            name="Live Price"
            stroke="#0891b2"      // cyan-600
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}    // ← critical: disables Recharts animation
            activeDot={{ r: 4, fill: "#0891b2", strokeWidth: 0 }}
          />

          {/* LSTM prediction line */}
          {hasPrediction && (
            <Line
              type="monotone"
              dataKey="prediction"
              name="LSTM Target"
              stroke="#7c3aed"    // violet-600
              strokeWidth={1.5}
              strokeDasharray="5 3"
              dot={false}
              isAnimationActive={false}
              activeDot={{ r: 3, fill: "#7c3aed" }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </section>
  );
}

export default memo(LivePriceChart);
