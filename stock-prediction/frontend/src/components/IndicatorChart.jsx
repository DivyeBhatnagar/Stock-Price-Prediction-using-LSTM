// IndicatorChart.jsx  —  Technical indicator charts (RSI, MACD, Volume)

import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer
} from "recharts";
import { useMemo } from "react";
import { format, parseISO } from "date-fns";

const SimpleTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-surface-border bg-surface-card px-3 py-2 shadow-xl text-xs">
      <p className="mb-1 text-slate-400">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }} className="font-mono">
          {p.name}: {Number(p.value).toFixed(2)}
        </p>
      ))}
    </div>
  );
};

export default function IndicatorChart({ stockData }) {
  const data = useMemo(() => {
    if (!stockData?.data) return [];
    return stockData.data.slice(-120).map((d) => ({
      date:        d.date ?? d.Date,
      rsi:         parseFloat(d.RSI ?? 50),
      macd:        parseFloat(d.MACD ?? 0),
      macd_signal: parseFloat(d.MACD_Signal ?? 0),
      volume:      parseFloat(d.Volume ?? d.volume ?? 0) / 1e6,
      sma20:       parseFloat(d.SMA_20),
      ema20:       parseFloat(d.EMA_20),
    }));
  }, [stockData]);

  if (!data.length) return null;
  const tickFmt = (d) => { try { return format(parseISO(d), "MMM d"); } catch { return d; } };

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {/* RSI */}
      <div className="rounded-2xl border border-surface-border bg-surface-card p-5 shadow-xl">
        <h4 className="mb-3 font-semibold text-white text-sm">RSI (14)</h4>
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={data} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis dataKey="date" tickFormatter={tickFmt} tick={{ fill: "#94a3b8", fontSize: 9 }}
              tickLine={false} axisLine={{ stroke: "#334155" }} interval={Math.floor(data.length / 5)} />
            <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 10 }} tickLine={false} axisLine={false} />
            <Tooltip content={<SimpleTooltip />} />
            <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="4 2" label={{ value: "OB", fill: "#ef4444", fontSize: 9 }} />
            <ReferenceLine y={30} stroke="#22c55e" strokeDasharray="4 2" label={{ value: "OS", fill: "#22c55e", fontSize: 9 }} />
            <Line type="monotone" dataKey="rsi" name="RSI" stroke="#a855f7" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* MACD */}
      <div className="rounded-2xl border border-surface-border bg-surface-card p-5 shadow-xl">
        <h4 className="mb-3 font-semibold text-white text-sm">MACD</h4>
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={data} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis dataKey="date" tickFormatter={tickFmt} tick={{ fill: "#94a3b8", fontSize: 9 }}
              tickLine={false} axisLine={{ stroke: "#334155" }} interval={Math.floor(data.length / 5)} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} tickLine={false} axisLine={false} />
            <Tooltip content={<SimpleTooltip />} />
            <ReferenceLine y={0} stroke="#475569" />
            <Bar dataKey="macd" name="MACD Hist." fill="#3b82f6" fillOpacity={0.5} barSize={3} />
            <Line type="monotone" dataKey="macd"        name="MACD"   stroke="#3b82f6" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="macd_signal" name="Signal" stroke="#f97316" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Volume */}
      <div className="rounded-2xl border border-surface-border bg-surface-card p-5 shadow-xl lg:col-span-2">
        <h4 className="mb-3 font-semibold text-white text-sm">Volume (M shares)</h4>
        <ResponsiveContainer width="100%" height={140}>
          <ComposedChart data={data} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis dataKey="date" tickFormatter={tickFmt} tick={{ fill: "#94a3b8", fontSize: 9 }}
              tickLine={false} axisLine={{ stroke: "#334155" }} interval={Math.floor(data.length / 8)} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} tickLine={false} axisLine={false}
              tickFormatter={(v) => `${v.toFixed(0)}M`} />
            <Tooltip content={<SimpleTooltip />} />
            <Bar dataKey="volume" name="Volume (M)" fill="#0ea5e9" fillOpacity={0.6} barSize={3} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
