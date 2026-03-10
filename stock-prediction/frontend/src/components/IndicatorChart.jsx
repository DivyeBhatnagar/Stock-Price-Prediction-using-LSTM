// IndicatorChart.jsx  —  Technical indicator charts (RSI, MACD, Volume) - light theme

import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer
} from "recharts";
import { useMemo } from "react";
import { format, parseISO } from "date-fns";

const SimpleTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-surface-border bg-white px-3 py-2 shadow-card-md text-xs">
      <p className="mb-1 font-semibold text-slate-500">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }} className="font-mono font-medium">
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
    }));
  }, [stockData]);

  if (!data.length) return null;

  const tickFmt = (d) => { try { return format(parseISO(d), "MMM d"); } catch { return d; } };

  const gridProps  = { strokeDasharray: "3 3", stroke: "#E2E8F0", vertical: false };
  const xProps     = (interval) => ({
    dataKey: "date", tickFormatter: tickFmt,
    tick: { fill: "#64748b", fontSize: 9 }, tickLine: false,
    axisLine: { stroke: "#E2E8F0" }, interval: interval ?? Math.floor(data.length / 5),
  });
  const yProps = { tick: { fill: "#64748b", fontSize: 10 }, tickLine: false, axisLine: false };

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">

      {/* RSI */}
      <div className="rounded-2xl border border-surface-border bg-surface-card p-5 shadow-card">
        <h4 className="mb-3 text-sm font-semibold text-slate-900">RSI (14)</h4>
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={data} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
            <CartesianGrid {...gridProps} />
            <XAxis {...xProps()} />
            <YAxis domain={[0, 100]} {...yProps} />
            <Tooltip content={<SimpleTooltip />} />
            <ReferenceLine y={70} stroke="#DC2626" strokeDasharray="4 2"
              label={{ value: "OB", fill: "#DC2626", fontSize: 9 }} />
            <ReferenceLine y={30} stroke="#16A34A" strokeDasharray="4 2"
              label={{ value: "OS", fill: "#16A34A", fontSize: 9 }} />
            <Line type="monotone" dataKey="rsi" name="RSI" stroke="#7C3AED" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* MACD */}
      <div className="rounded-2xl border border-surface-border bg-surface-card p-5 shadow-card">
        <h4 className="mb-3 text-sm font-semibold text-slate-900">MACD</h4>
        <ResponsiveContainer width="100%" height={180}>
          <ComposedChart data={data} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
            <CartesianGrid {...gridProps} />
            <XAxis {...xProps()} />
            <YAxis {...yProps} />
            <Tooltip content={<SimpleTooltip />} />
            <ReferenceLine y={0} stroke="#CBD5E1" />
            <Bar  dataKey="macd"        name="MACD Hist." fill="#2563EB" fillOpacity={0.35} barSize={3} />
            <Line dataKey="macd"        name="MACD"       stroke="#2563EB" strokeWidth={1.5} dot={false} />
            <Line dataKey="macd_signal" name="Signal"     stroke="#F97316" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Volume */}
      <div className="rounded-2xl border border-surface-border bg-surface-card p-5 shadow-card lg:col-span-2">
        <h4 className="mb-3 text-sm font-semibold text-slate-900">Volume (M shares)</h4>
        <ResponsiveContainer width="100%" height={140}>
          <ComposedChart data={data} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
            <CartesianGrid {...gridProps} />
            <XAxis {...xProps(Math.floor(data.length / 8))} />
            <YAxis {...yProps} tickFormatter={(v) => `${v.toFixed(0)}M`} />
            <Tooltip content={<SimpleTooltip />} />
            <Bar dataKey="volume" name="Volume (M)" fill="#0EA5E9" fillOpacity={0.6} barSize={3} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

