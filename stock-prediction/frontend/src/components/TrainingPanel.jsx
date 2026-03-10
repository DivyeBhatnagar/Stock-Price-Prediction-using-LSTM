// TrainingPanel.jsx  —  Training configuration form + status tracker

import { useState, useEffect, useRef } from "react";
import { Settings, Play, CheckCircle, XCircle, Loader, ChevronDown, ChevronUp } from "lucide-react";

const SliderField = ({ label, value, onChange, min, max, step = 1, suffix = "" }) => (
  <div>
    <div className="flex justify-between text-xs text-slate-400 mb-1">
      <span>{label}</span>
      <span className="font-mono font-semibold text-white">{value}{suffix}</span>
    </div>
    <input
      type="range" min={min} max={max} step={step} value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full accent-blue-500"
    />
  </div>
);

const STATUS_ICONS = {
  queued:    <Loader   className="h-4 w-4 animate-spin text-yellow-400" />,
  running:   <Loader   className="h-4 w-4 animate-spin text-blue-400"   />,
  completed: <CheckCircle className="h-4 w-4 text-green-400"            />,
  failed:    <XCircle  className="h-4 w-4 text-red-400"                 />,
};

export default function TrainingPanel({ ticker, onTrain, trainingStatus, onPollStatus }) {
  const [open, setOpen] = useState(false);
  const [params, setParams] = useState({
    window:     60,
    horizon:    1,
    epochs:     100,
    batch_size: 32,
    learning_rate: 0.001,
    dropout:    0.2,
    attention:  true,
    bidirectional: false,
  });
  const pollRef = useRef(null);

  // Auto-poll while training is running
  useEffect(() => {
    if (trainingStatus?.status === "running" || trainingStatus?.status === "queued") {
      pollRef.current = setInterval(() => onPollStatus(ticker), 4000);
    } else {
      clearInterval(pollRef.current);
    }
    return () => clearInterval(pollRef.current);
  }, [trainingStatus?.status, ticker]);

  const set = (key) => (val) => setParams((p) => ({ ...p, [key]: val }));

  const handleTrain = () => {
    onTrain({ ticker, ...params });
  };

  const status = trainingStatus?.status;

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card shadow-xl">
      {/* Header toggle */}
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between p-5 text-left"
      >
        <div className="flex items-center gap-3">
          <Settings className="h-5 w-5 text-blue-400" />
          <span className="font-semibold text-white">⚙️ Training Configuration</span>
          {status && (
            <span className={`flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold
              ${status === "completed" ? "bg-green-500/20 text-green-400" :
                status === "failed"    ? "bg-red-500/20   text-red-400"   :
                "bg-blue-500/20 text-blue-400"
              }`}
            >
              {STATUS_ICONS[status]}
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </span>
          )}
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
      </button>

      {open && (
        <div className="border-t border-surface-border px-5 pb-5">
          <div className="mt-4 grid grid-cols-1 gap-5 sm:grid-cols-2">
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
          <div className="mt-4 flex gap-6">
            {[
              ["Temporal Attention", "attention"],
              ["Bidirectional LSTM", "bidirectional"],
            ].map(([label, key]) => (
              <label key={key} className="flex cursor-pointer items-center gap-2">
                <div
                  onClick={() => set(key)(!params[key])}
                  className={`relative h-5 w-9 rounded-full transition ${params[key] ? "bg-blue-600" : "bg-slate-600"}`}
                >
                  <div className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all
                    ${params[key] ? "left-4" : "left-0.5"}`} />
                </div>
                <span className="text-sm text-slate-300">{label}</span>
              </label>
            ))}
          </div>

          {/* Train button */}
          <button
            onClick={handleTrain}
            disabled={status === "running" || status === "queued"}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/30 transition hover:opacity-90 active:scale-[.98] disabled:opacity-50"
          >
            {(status === "running" || status === "queued") ? (
              <><Loader className="h-4 w-4 animate-spin" /> Training in progress…</>
            ) : (
              <><Play className="h-4 w-4" /> Start Training for {ticker}</>
            )}
          </button>

          {/* Training result metrics */}
          {status === "completed" && trainingStatus.metrics && (
            <div className="mt-4 rounded-xl bg-green-500/10 border border-green-500/30 p-4">
              <p className="mb-2 text-sm font-semibold text-green-400">✅ Training Complete!</p>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                {Object.entries(trainingStatus.metrics).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-slate-400">{k.toUpperCase()}</span>
                    <span className="text-white">{typeof v === "number" ? v.toFixed(4) : v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {status === "failed" && (
            <div className="mt-4 rounded-xl bg-red-500/10 border border-red-500/30 p-4">
              <p className="text-sm font-semibold text-red-400">❌ Training Failed</p>
              <p className="mt-1 text-xs text-red-300">{trainingStatus.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
