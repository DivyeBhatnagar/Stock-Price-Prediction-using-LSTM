// MetricsPanel.jsx  —  Model performance metrics (light theme)

import { useMemo } from "react";
import { BarChart2, Target, TrendingUp, Percent, Activity, Clock } from "lucide-react";
import { getCurrencySymbol } from "../utils/currency";

const variantMap = {
  blue:   { card: "border-l-brand-500  bg-brand-50",  icon: "text-brand-600",  val: "text-brand-700"  },
  green:  { card: "border-l-green-500  bg-green-50",  icon: "text-green-600",  val: "text-green-700"  },
  orange: { card: "border-l-amber-500  bg-amber-50",  icon: "text-amber-600",  val: "text-amber-700"  },
  purple: { card: "border-l-violet-500 bg-violet-50", icon: "text-violet-600", val: "text-violet-700" },
  red:    { card: "border-l-red-500    bg-red-50",    icon: "text-red-600",    val: "text-red-700"    },
  teal:   { card: "border-l-cyan-500   bg-cyan-50",   icon: "text-cyan-600",   val: "text-cyan-700"   },
};

const MetricCard = ({ icon: Icon, label, value, description, color = "blue" }) => {
  const v = variantMap[color] || variantMap.blue;
  return (
    <div className={`flex items-start gap-3 rounded-xl border border-surface-border border-l-2 p-4 shadow-sm ${v.card}`}>
      <div className={`mt-0.5 rounded-lg bg-white p-2 shadow-sm ${v.icon}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <p className={`mt-0.5 font-mono text-xl font-bold tracking-tight ${v.val}`}>{value ?? "—"}</p>
        {description && <p className="mt-0.5 text-[11px] text-slate-400">{description}</p>}
      </div>
    </div>
  );
};

const r2Quality = (r2) => {
  if (r2 >= 0.95) return { label: "Excellent", color: "green"  };
  if (r2 >= 0.85) return { label: "Good",      color: "teal"   };
  if (r2 >= 0.70) return { label: "Fair",       color: "orange" };
  return             { label: "Needs Work",  color: "red"    };
};

const qualityBadge = {
  green:  "border-green-200  bg-green-100  text-green-700",
  teal:   "border-cyan-200   bg-cyan-100   text-cyan-700",
  orange: "border-amber-200  bg-amber-100  text-amber-700",
  red:    "border-red-200    bg-red-100    text-red-700",
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
    <div className="rounded-2xl border border-surface-border bg-surface-card p-6 shadow-card">
      <div className="mb-5 flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-900">
          Model Performance — {ticker}
        </h3>
        <span className={`rounded-full border px-3 py-1 text-xs font-bold ${qualityBadge[q.color] || qualityBadge.red}`}>
          {q.label}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <MetricCard
          icon={Target}    label="RMSE"
          value={m.rmse  != null ? `${sym}${m.rmse.toFixed(2)}`  : "—"}
          description="Root Mean Squared Error" color="blue"
        />
        <MetricCard
          icon={Activity}  label="MAE"
          value={m.mae   != null ? `${sym}${m.mae.toFixed(2)}`   : "—"}
          description="Mean Absolute Error"     color="purple"
        />
        <MetricCard
          icon={Percent}   label="MAPE"
          value={m.mape  != null ? `${m.mape.toFixed(2)}%`       : "—"}
          description="Mean Absolute % Error"
          color={m.mape < 5 ? "green" : m.mape < 10 ? "teal" : "orange"}
        />
        <MetricCard
          icon={BarChart2} label="R² Score"
          value={r2 != null ? r2.toFixed(4) : "—"}
          description="Coefficient of determination" color={q.color}
        />
        <MetricCard
          icon={TrendingUp} label="Directional Acc."
          value={da}
          description="Correct trend direction"  color="teal"
        />
        <MetricCard
          icon={Clock}     label="Epochs Trained"
          value={metrics.epochs_trained ?? "—"}
          description={`Window: ${metrics.window_size ?? "?"}d · Horizon: ${metrics.forecast_horizon ?? "?"}d`}
          color="orange"
        />
      </div>
    </div>
  );
}
