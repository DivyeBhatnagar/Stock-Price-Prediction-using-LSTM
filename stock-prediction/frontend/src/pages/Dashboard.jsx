// Dashboard.jsx  —  Main page component wiring everything together

import { useState, useCallback } from "react";
import { AlertCircle, X } from "lucide-react";

import TickerSearch     from "../components/TickerSearch";
import PriceChart       from "../components/PriceChart";
import CandlestickChart from "../components/CandlestickChart";
import MetricsPanel     from "../components/MetricsPanel";
import TrainingPanel    from "../components/TrainingPanel";
import StockInfoBar     from "../components/StockInfoBar";
import IndicatorChart   from "../components/IndicatorChart";
import ForecastTable    from "../components/ForecastTable";
import MarketInfoBar    from "../components/MarketInfoBar";
import { useStock }     from "../hooks/useStock";

export default function Dashboard() {
  const [activeTicker, setActiveTicker] = useState("RELIANCE.NS");
  const [activeTab, setActiveTab]       = useState("overview"); // overview | indicators | training

  const {
    stockData, prediction, metrics,
    trainingStatus, loading, error,
    loadStock, loadPrediction,
    startTraining, pollTraining,
  } = useStock();

  // ── Search handler ─────────────────────────
  const handleSearch = useCallback(async (ticker, horizon) => {
    setActiveTicker(ticker);
    try {
      await loadStock(ticker);
      await loadPrediction(ticker, horizon);
    } catch {
      // Errors are already captured inside the hook
    }
  }, [loadStock, loadPrediction]);

  // ── Train handler ───────────────────────────
  const handleTrain = useCallback(async (ticker) => {
    setActiveTicker(ticker);
    try {
      await startTraining({ ticker });
    } catch {
      // handled by hook
    }
  }, [startTraining]);

  const handleTrainWithParams = useCallback(async (params) => {
    try {
      await startTraining(params);
    } catch {}
  }, [startTraining]);

  const TABS = [
    { id: "overview",    label: "📈 Overview"   },
    { id: "candles",     label: "🕯 Candlestick" },
    { id: "indicators",  label: "📊 Indicators"  },
    { id: "training",    label: "⚙️ Train Model" },
  ];

  return (
    <div className="min-h-screen bg-surface text-white">
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">

        {/* Hero */}
        <div className="text-center">
          <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Stock Price{" "}
            <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              Prediction
            </span>
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Powered by LSTM Neural Networks · Indian & US Markets · NSE / BSE / NASDAQ
          </p>
        </div>

        {/* Search */}
        <TickerSearch
          onSearch={handleSearch}
          onTrain={handleTrain}
          loading={loading}
        />

        {/* Error banner */}
        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
            <p className="flex-1 text-sm text-red-300">{error}</p>
            <button onClick={() => {}} className="text-red-400 hover:text-red-300">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Stock info bar */}
        {stockData && (
          <StockInfoBar stockData={stockData} ticker={activeTicker} />
        )}

        {/* Market info bar (exchange, currency, trading hours) */}
        {stockData && (
          <MarketInfoBar ticker={activeTicker} stockData={stockData} />
        )}

        {/* Tab navigation */}
        {stockData && (
          <div className="flex gap-1 rounded-xl border border-surface-border bg-surface-card p-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex-1 rounded-lg py-2 text-sm font-medium transition
                  ${activeTab === t.id
                    ? "bg-blue-600 text-white shadow"
                    : "text-slate-400 hover:text-white"
                  }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        {/* Tab content */}
        {activeTab === "overview" && (
          <div className="space-y-5">
            <PriceChart
              stockData={stockData}
              prediction={prediction}
              ticker={activeTicker}
            />
            {prediction && (
              <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                <ForecastTable prediction={prediction} ticker={activeTicker} />
                <MetricsPanel  metrics={metrics}       ticker={activeTicker} />
              </div>
            )}
          </div>
        )}

        {activeTab === "candles" && (
          <CandlestickChart stockData={stockData} ticker={activeTicker} />
        )}

        {activeTab === "indicators" && (
          <IndicatorChart stockData={stockData} />
        )}

        {activeTab === "training" && (
          <TrainingPanel
            ticker={activeTicker}
            onTrain={handleTrainWithParams}
            trainingStatus={trainingStatus}
            onPollStatus={pollTraining}
          />
        )}

        {/* Empty state */}
        {!stockData && !loading.stock && (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-surface-border bg-surface-card/50 py-20 text-center">
            <div className="mb-4 text-5xl">📈</div>
            <h3 className="text-lg font-semibold text-white">Search for a Stock</h3>
            <p className="mt-2 text-sm text-slate-500">
              Enter an Indian (NSE/BSE) or US ticker symbol to load data and AI predictions
            </p>
          </div>
        )}

        {/* Loading skeleton */}
        {(loading.stock || loading.predict) && (
          <div className="space-y-4">
            {[400, 200, 200].map((h, i) => (
              <div key={i} className={`h-${h === 400 ? "[400px]" : "[200px]"} animate-pulse rounded-2xl bg-surface-card`}
                style={{ height: `${h}px` }} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
