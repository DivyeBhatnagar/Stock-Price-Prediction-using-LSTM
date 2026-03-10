// PriceChart.jsx  —  Combined historical + predicted price chart using Recharts

import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer, Brush
} from "recharts";
import { useMemo } from "react";
import { format, parseISO } from "date-fns";
import { getCurrencySymbol, formatPrice } from "../utils/currency";

// ─── Custom Tooltip ────────────────────────────
const CustomTooltip = ({ active, payload, label, ticker }) => {
  if (!active || !payload?.length) return null;
  const sym = getCurrencySymbol(ticker);
  return (
    <div className="rounded-xl border border-surface-border bg-surface-card px-4 py-3 shadow-2xl">
      <p className="mb-2 text-xs font-semibold text-slate-400">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2 text-sm">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          <span className="text-slate-300">{p.name}:</span>
          <span className="font-mono font-semibold text-white">
            {sym}{Number(p.value).toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
};

// ─── Main Chart ────────────────────────────────
export default function PriceChart({ stockData, prediction, ticker }) {
  // Merge historical + predicted data into a single series
  const chartData = useMemo(() => {
    const hist = (stockData?.data ?? []).map((d) => ({
      date:  d.date ?? d.Date,
      close: parseFloat(d.Close ?? d.close),
      open:  parseFloat(d.Open  ?? d.open),
      high:  parseFloat(d.High  ?? d.high),
      low:   parseFloat(d.Low   ?? d.low),
    }));

    // Show only the last 180 historical days for clarity
    const recent = hist.slice(-180);

    const pred = (prediction?.forecast ?? []).map((d) => ({
      date:      d.date,
      predicted: parseFloat(d.price),
    }));

    // Build a unified array with the split marker
    const all = [...recent];
    const splitDate = recent.length ? recent[recent.length - 1].date : null;

    pred.forEach((p) => {
      all.push({
        date:      p.date,
        predicted: p.predicted,
        isForecast: true,
      });
    });

    return { data: all, splitDate };
  }, [stockData, prediction]);

  if (!stockData && !prediction) return null;

  const { data, splitDate } = chartData;
  const tickFormatter = (d) => {
    try { return format(parseISO(d), "MMM d"); } catch { return d; }
  };
  const sym = getCurrencySymbol(ticker);

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card p-6 shadow-xl">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">
            {ticker} — Price History &amp; Forecast
          </h3>
          <p className="text-xs text-slate-500">
            Blue = Historical Close · Orange = AI Prediction
          </p>
        </div>
        {prediction && (
          <span className="rounded-full bg-orange-500/20 px-3 py-1 text-xs font-semibold text-orange-400">
            +{prediction.n_days}d Forecast
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={data} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={tickFormatter}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#334155" }}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${sym}${v.toFixed(0)}`}
          />
          <Tooltip content={<CustomTooltip ticker={ticker} />} />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: "12px", paddingTop: "12px" }}
          />
          <Brush
            dataKey="date"
            height={24}
            stroke="#334155"
            fill="#1e293b"
            travellerWidth={6}
          />

          {/* Split line between historical and predicted */}
          {splitDate && (
            <ReferenceLine
              x={splitDate}
              stroke="#64748b"
              strokeDasharray="4 4"
              label={{ value: "Forecast →", fill: "#94a3b8", fontSize: 10, position: "insideTopRight" }}
            />
          )}

          {/* Historical Close */}
          <Line
            type="monotone"
            dataKey="close"
            name="Historical Close"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#3b82f6" }}
          />

          {/* Predicted prices */}
          <Line
            type="monotone"
            dataKey="predicted"
            name="AI Forecast"
            stroke="#f97316"
            strokeWidth={2.5}
            strokeDasharray="6 3"
            dot={{ r: 3, fill: "#f97316" }}
            activeDot={{ r: 5 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
