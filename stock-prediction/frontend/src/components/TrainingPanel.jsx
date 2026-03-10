// TrainingPanel.jsx  —  Training configuration form + status tracker (light theme)

import { useState, useEffect, useRef } from "react";
import { Settings, Play, CheckCircle, XCircle, Loader, ChevronDown, ChevronUp } from "lucide-react";

const SliderField = ({ label, value, onChange, min, max, step = 1, suffix = "" }) => (
  <div>
    <div className="mb-1.5 flex justify-between text-xs">
      <span className="font-medium text-slate-600">{label}</span>
      <span className="font-mono font-bold text-brand-600">{value}{suffix}</span>
    </div>
    <input
      type="range" min={min} max={max} step={step} value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full cursor-pointer accent-brand-600"
    />
  </div>
);

const STATUS_ICONS = {
  queued:    <Loader      className="h-4 w-4 animate-spin text-amber-500" />,
  running:   <Loader      className="h-4 w-4 animate-spin text-brand-600" />,
  completed: <CheckCircle className="h-4 w-4 text-green-600"              />,
  failed:    <XCircle     className="h-4 w-4 text-red-600"                />,
};

const STATUS_BADGE = {
  queued:    "bg-amber-50  border-amber-200  text-amber-700",
  running:   "bg-brand-50  border-brand-200  text-brand-700",
  completed: "bg-green-50  border-green-200  text-green-700",
  failed:    "bg-red-50    border-red-200    text-red-700",
};

export default function TrainingPanel({ ticker, onTrain, trainingStatus, onPollStatus }) {
  const [open, setOpen] = useState(false);
  const [params, setParams] = useState({
    window:        60,
    horizon:        1,
    epochs:       100,
    batch_size:    32,
    learning_rate: 0.001,
    dropout:       0.2,
    attention:     true,
    bidirectional: false,
  });
  const pollRef = useRef(null);

  useEffect(() => {
    if (trainingStatus?.status === "running" || trainingStatus?.status === "queued") {
      pollRef.current = setInterval(() => onPollStatus(ticker), 4000);
    } else {
      clearInterval(pollRef.current);
    }
    return () => clearInterval(pollRef.current);
  }, [trainingStatus?.status, ticker]);

  const set = (key) => (val) => setParams((p) => ({ ...p, [key]: val }));
  const status = trainingStatus?.status;

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card shadow-card">

      {/* Header toggle */}
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full cursor-pointer items-center justify-between p-5 text-left"
      >
        <div className="flex items-center gap-3">
          <Settings className="h-5 w-5 text-brand-600" />
          <span className="font-semibold text-slate-900">Training Configuration</span>
          {status && (
            <span className={`flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
              STATUS_BADGE[status] || STATUS_BADGE.running
            }`}>
              {STATUS_ICONS[status]}
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </span>
          )}
        </div>
        {open
          ? <ChevronUp   className="h-4 w-4 text-slate-400" />
          : <ChevronDown className="h-4 w-4 text-slate-400" />}
      </button>

      {open && (
        <div className="border-t border-surface-border px-5 pb-5">
          <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2">
            <SliderField label="Look-back Window (days)" value={params.window}
              onChange={set("window")} min={20} max={200} step={10} suffix="d" />
            <SliderField label="Forecast Horizon (days)" value={params.horizon}
              onChange={set("horizon")} min={1} max={30} suffix="d" />
            <SliderField label="Max Epochs" value={params.epochs}
              onChange={set("epochs")} min={10} max={500} step={10} />
            <SliderField label="Batch Size" value={params.batch_size}
              onChange={set("batch_size")} min={8} max={256} step={8} />
            <SliderField label="Learning Rate" value={params.learning_rate}
              onChange={set("learning_rate")} min={0.0001} max={0.01} step={0.0001} />
            <SliderField label="Dropout Rate" value={params.dropout}
              onChange={set("dropout")} min={0} max={0.5} step={0.05} />
          </div>

          {/* Toggle switches */}
          <div className="mt-5 flex gap-6">
            {[
              ["Temporal Attention", "attention"],
              ["Bidirectional LSTM", "bidirectional"],
            ].map(([label, key]) => (
              <label key={key} className="flex cursor-pointer items-center gap-2">
                <div
                  onClick={() => set(key)(!params[key])}
                  className={`relative h-5 w-9 rounded-full transition-colors duration-200 ${
                    params[key] ? "bg-brand-600" : "bg-slate-300"
                  }`}
                >
                  <div className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all duration-200 ${
                    params[key] ? "left-4" : "left-0.5"
                  }`} />
                </div>
                <span className="text-sm font-medium text-slate-700">{label}</span>
              </label>
            ))}
          </div>

          {/* Train button */}
          <button
            onClick={() => onTrain({ ticker, ...params })}
            disabled={status === "running" || status === "queued"}
            className="mt-5 flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-brand-600 py-3 text-sm font-semibold text-white shadow-sm transition-colors duration-200 hover:bg-brand-700 active:scale-[.98] disabled:opacity-50"
          >
            {(status === "running" || status === "queued") ? (
              <><Loader className="h-4 w-4 animate-spin" /> Training in progress…</>
            ) : (
              <><Play className="h-4 w-4" /> Start Training for {ticker}</>
            )}
          </button>

          {/* Training complete */}
          {status === "completed" && trainingStatus.metrics && (
            <div className="mt-4 rounded-xl border border-green-200 bg-green-50 p-4">
              <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-green-700">
                <CheckCircle className="h-4 w-4" /> Training Complete!
              </p>
              <div className="grid grid-cols-2 gap-2 font-mono text-xs">
                {Object.entries(trainingStatus.metrics).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-slate-500">{k.toUpperCase()}</span>
                    <span className="font-semibold text-slate-900">{typeof v === "number" ? v.toFixed(4) : v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Training failed */}
          {status === "failed" && (
            <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4">
              <p className="flex items-center gap-1.5 text-sm font-semibold text-red-700">
                <XCircle className="h-4 w-4" /> Training Failed
              </p>
              <p className="mt-1 text-xs text-red-600">{trainingStatus.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
