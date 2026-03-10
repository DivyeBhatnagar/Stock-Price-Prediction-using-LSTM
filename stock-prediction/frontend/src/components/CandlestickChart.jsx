// CandlestickChart.jsx  —  OHLC Candlestick chart (light theme)

import { useMemo } from "react";
import {
  ComposedChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from "recharts";
import { format, parseISO } from "date-fns";
import { getCurrencySymbol } from "../utils/currency";

const CandleTooltip = ({ active, payload, label, ticker }) => {
  if (!active || !payload?.length) return null;
  const d   = payload[0]?.payload;
  if (!d) return null;
  const sym = getCurrencySymbol(ticker);
  return (
    <div className="rounded-xl border border-surface-border bg-white px-4 py-3 shadow-card-md text-sm">
      <p className="mb-2 font-semibold text-slate-500">{label}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-xs">
        <span className="text-slate-500">Open</span>  <span className="text-slate-900">{sym}{d.open?.toFixed(2)}</span>
        <span className="text-slate-500">High</span>  <span className="text-green-600">{sym}{d.high?.toFixed(2)}</span>
        <span className="text-slate-500">Low</span>   <span className="text-red-600">{sym}{d.low?.toFixed(2)}</span>
        <span className="text-slate-500">Close</span> <span className="text-slate-900">{sym}{d.close?.toFixed(2)}</span>
      </div>
    </div>
  );
};

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
        date: d.date ?? d.Date,
        open, high, low, close,
        wick:      [low, high],
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
    <div className="rounded-2xl border border-surface-border bg-surface-card p-6 shadow-card">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-slate-900">
          {ticker} — Candlestick (Last 90 Days)
        </h3>
        <p className="mt-0.5 text-xs text-slate-500">Green = Bullish · Red = Bearish</p>
      </div>

      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={tickFmt}
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "#E2E8F0" }}
            interval={Math.floor(data.length / 8)}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fill: "#64748b", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${sym}${v.toFixed(0)}`}
          />
          <Tooltip content={<CandleTooltip ticker={ticker} />} />

          {/* Wick */}
          <Bar dataKey="wick" barSize={2} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.bullish ? "#16A34A" : "#DC2626"} />
            ))}
          </Bar>

          {/* Body */}
          <Bar dataKey="bodyRange" barSize={8} isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.bullish ? "#16A34A" : "#DC2626"} fillOpacity={0.85} />
            ))}
          </Bar>
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
