// PriceChart.jsx  —  Combined historical + predicted price chart (light theme)

import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer, Brush
} from "recharts";
import { useMemo } from "react";
import { format, parseISO } from "date-fns";
import { getCurrencySymbol, formatPrice } from "../utils/currency";

const CustomTooltip = ({ active, payload, label, ticker }) => {
  if (!active || !payload?.length) return null;
  const sym = getCurrencySymbol(ticker);
  return (
    <div className="rounded-xl border border-surface-border bg-white px-4 py-3 shadow-card-md">
      <p className="mb-2 text-xs font-semibold text-slate-500">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2 text-sm">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          <span className="text-slate-600">{p.name}:</span>
          <span className="font-mono font-semibold text-slate-900">
            {sym}{Number(p.value).toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
};

export default function PriceChart({ stockData, prediction, ticker }) {
  const chartData = useMemo(() => {
    const hist = (stockData?.data ?? []).map((d) => ({
      date:  d.date ?? d.Date,
      close: parseFloat(d.Close ?? d.close),
      open:  parseFloat(d.Open  ?? d.open),
      high:  parseFloat(d.High  ?? d.high),
      low:   parseFloat(d.Low   ?? d.low),
    }));
    const recent    = hist.slice(-180);
    const pred      = (prediction?.forecast ?? []).map((d) => ({ date: d.date, predicted: parseFloat(d.price) }));
    const all       = [...recent];
    const splitDate = recent.length ? recent[recent.length - 1].date : null;
    pred.forEach((p) => all.push({ date: p.date, predicted: p.predicted, isForecast: true }));
    return { data: all, splitDate };
  }, [stockData, prediction]);

  if (!stockData && !prediction) return null;

  const { data, splitDate } = chartData;
  const tickFormatter = (d) => { try { return format(parseISO(d), "MMM d"); } catch { return d; } };
  const sym = getCurrencySymbol(ticker);

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card p-6 shadow-card">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-900">
            {ticker} — Price History &amp; Forecast
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">Blue = Historical Close · Orange = AI Prediction</p>
        </div>
        {prediction && (
          <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
            +{prediction.n_days}d Forecast
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={data} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={tickFormatter}
            tick={{ fill: "#64748b", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#E2E8F0" }}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fill: "#64748b", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${sym}${v.toFixed(0)}`}
          />
          <Tooltip content={<CustomTooltip ticker={ticker} />} />
          <Legend iconType="circle" iconSize={8}
            wrapperStyle={{ fontSize: "12px", paddingTop: "12px", color: "#475569" }}
          />
          <Brush dataKey="date" height={24} stroke="#E2E8F0" fill="#F8FAFC" travellerWidth={6} />

          {splitDate && (
            <ReferenceLine x={splitDate} stroke="#94A3B8" strokeDasharray="4 4"
              label={{ value: "Forecast →", fill: "#64748b", fontSize: 10, position: "insideTopRight" }}
            />
          )}

          <Line type="monotone" dataKey="close" name="Historical Close"
            stroke="#2563EB" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: "#2563EB" }}
          />

          <Line type="monotone" dataKey="predicted" name="AI Forecast"
            stroke="#F97316" strokeWidth={2.5} strokeDasharray="6 3"
            dot={{ r: 3, fill: "#F97316" }} activeDot={{ r: 5 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
