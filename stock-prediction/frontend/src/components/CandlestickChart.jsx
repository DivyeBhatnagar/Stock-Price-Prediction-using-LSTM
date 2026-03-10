// CandlestickChart.jsx  —  OHLC Candlestick chart built with Recharts

import { useMemo } from "react";
import {
  ComposedChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from "recharts";
import { format, parseISO } from "date-fns";
import { getCurrencySymbol } from "../utils/currency";

const CandleTooltip = ({ active, payload, label, ticker }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  const sym = getCurrencySymbol(ticker);
  return (
    <div className="rounded-xl border border-surface-border bg-surface-card px-4 py-3 shadow-2xl text-sm">
      <p className="mb-2 font-semibold text-slate-400">{label}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-xs">
        <span className="text-slate-400">Open</span>  <span className="text-white">{sym}{d.open?.toFixed(2)}</span>
        <span className="text-slate-400">High</span>  <span className="text-green-400">{sym}{d.high?.toFixed(2)}</span>
        <span className="text-slate-400">Low</span>   <span className="text-red-400">{sym}{d.low?.toFixed(2)}</span>
        <span className="text-slate-400">Close</span> <span className="text-white">{sym}{d.close?.toFixed(2)}</span>
      </div>
    </div>
  );
};

// Recharts doesn't have a native candlestick — we simulate with a composed chart
// using a "range" bar (high–low) plus a "body" bar (open–close).
export default function CandlestickChart({ stockData, ticker }) {
  const data = useMemo(() => {
    if (!stockData?.data) return [];
    return stockData.data.slice(-90).map((d) => {
      const open  = parseFloat(d.Open  ?? d.open);
      const high  = parseFloat(d.High  ?? d.high);
      const low   = parseFloat(d.Low   ?? d.low);
      const close = parseFloat(d.Close ?? d.close);
      const bullish = close >= open;
      return {
        date:      d.date ?? d.Date,
        open, high, low, close,
        // For the wick bar: [low, high]
        wick:      [low, high],
        // For the body bar: [min(open,close), max(open,close)]
        bodyLow:   Math.min(open, close),
        bodyHigh:  Math.max(open, close),
        bodyRange: Math.max(open, close) - Math.min(open, close),
        bullish,
      };
    });
  }, [stockData]);

  if (!data.length) return null;

  const tickFmt = (d) => { try { return format(parseISO(d), "MMM d"); } catch { return d; } };
  const sym = getCurrencySymbol(ticker);

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card p-6 shadow-xl">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white">{ticker} — Candlestick (Last 90 Days)</h3>
        <p className="text-xs text-slate-500">Green = Bullish · Red = Bearish</p>
      </div>

      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={tickFmt}
            tick={{ fill: "#94a3b8", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
            interval={Math.floor(data.length / 8)}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${sym}${v.toFixed(0)}`}
          />
          <Tooltip content={<CandleTooltip ticker={ticker} />} />

          {/* Wick — thin bar from low to high */}
          <Bar dataKey="wick" barSize={2} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.bullish ? "#22c55e" : "#ef4444"} />
            ))}
          </Bar>

          {/* Body — bar from bodyLow to bodyHigh */}
          <Bar dataKey="bodyRange" barSize={8} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.bullish ? "#22c55e" : "#ef4444"} fillOpacity={0.85} />
            ))}
          </Bar>
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
