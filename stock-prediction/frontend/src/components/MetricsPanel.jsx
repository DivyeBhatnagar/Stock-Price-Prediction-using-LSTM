// MetricsPanel.jsx  —  Model performance metrics display

import { useMemo } from "react";
import { BarChart2, Target, TrendingUp, Percent, Activity, Clock } from "lucide-react";
import { getCurrencySymbol } from "../utils/currency";

const MetricCard = ({ icon: Icon, label, value, description, color = "blue" }) => {
  const colorMap = {
    blue:   "text-blue-400  bg-blue-500/10  border-blue-500/30",
    green:  "text-green-400 bg-green-500/10 border-green-500/30",
    orange: "text-orange-400 bg-orange-500/10 border-orange-500/30",
    purple: "text-purple-400 bg-purple-500/10 border-purple-500/30",
    red:    "text-red-400   bg-red-500/10   border-red-500/30",
    teal:   "text-teal-400  bg-teal-500/10  border-teal-500/30",
  };
  const cls = colorMap[color] || colorMap.blue;

  return (
    <div className={`flex items-start gap-4 rounded-xl border p-4 ${cls}`}>
      <div className={`mt-0.5 rounded-lg p-2 ${cls}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1">
        <p className="text-xs font-medium text-slate-400">{label}</p>
        <p className="mt-0.5 text-xl font-bold tracking-tight text-white">{value ?? "—"}</p>
        {description && <p className="mt-0.5 text-[11px] text-slate-500">{description}</p>}
      </div>
    </div>
  );
};

// Quality band for R²
const r2Quality = (r2) => {
  if (r2 >= 0.95) return { label: "Excellent", color: "green" };
  if (r2 >= 0.85) return { label: "Good",      color: "teal" };
  if (r2 >= 0.70) return { label: "Fair",       color: "orange" };
  return             { label: "Needs Work",  color: "red" };
};

export default function MetricsPanel({ metrics, ticker }) {
  if (!metrics) return null;

  const m  = metrics.metrics ?? {};
  const r2 = m.r2 ?? null;
  const q  = r2 !== null ? r2Quality(r2) : { label: "N/A", color: "blue" };

  const da = m.directional_accuracy != null
    ? `${(m.directional_accuracy * 100).toFixed(1)}%`
    : "—";

  const sym = getCurrencySymbol(ticker);

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card p-6 shadow-xl">
      <div className="mb-5 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">
          📊 Model Performance — {ticker}
        </h3>
        <span className={`rounded-full border px-3 py-1 text-xs font-bold
          ${q.color === "green"  ? "border-green-500/40 bg-green-500/10 text-green-400"  :
            q.color === "teal"   ? "border-teal-500/40  bg-teal-500/10  text-teal-400"   :
            q.color === "orange" ? "border-orange-500/40 bg-orange-500/10 text-orange-400":
            "border-red-500/40 bg-red-500/10 text-red-400"
          }`}
        >
          {q.label}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <MetricCard
          icon={Target}
          label="RMSE"
          value={m.rmse != null ? `${sym}${m.rmse.toFixed(2)}` : "—"}
          description="Root Mean Squared Error"
          color="blue"
        />
        <MetricCard
          icon={Activity}
          label="MAE"
          value={m.mae != null ? `${sym}${m.mae.toFixed(2)}` : "—"}
          description="Mean Absolute Error"
          color="purple"
        />
        <MetricCard
          icon={Percent}
          label="MAPE"
          value={m.mape != null ? `${m.mape.toFixed(2)}%` : "—"}
          description="Mean Absolute % Error"
          color={m.mape < 5 ? "green" : m.mape < 10 ? "teal" : "orange"}
        />
        <MetricCard
          icon={BarChart2}
          label="R² Score"
          value={r2 != null ? r2.toFixed(4) : "—"}
          description="Coefficient of determination"
          color={q.color}
        />
        <MetricCard
          icon={TrendingUp}
          label="Directional Acc."
          value={da}
          description="Correct trend direction"
          color="teal"
        />
        <MetricCard
          icon={Clock}
          label="Epochs Trained"
          value={metrics.epochs_trained ?? "—"}
          description={`Window: ${metrics.window_size ?? "?"}d · Horizon: ${metrics.forecast_horizon ?? "?"}d`}
          color="orange"
        />
      </div>
    </div>
  );
}
