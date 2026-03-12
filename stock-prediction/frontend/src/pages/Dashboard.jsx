// Dashboard.jsx  —  Main page component wiring everything together

import { useState, useCallback } from "react";
import { AlertCircle, X, TrendingUp, CandlestickChart as CandleIcon, BarChart2, Settings, Activity } from "lucide-react";

import TickerSearch     from "../components/TickerSearch";
import PriceChart       from "../components/PriceChart";
import CandlestickChart from "../components/CandlestickChart";
import MetricsPanel     from "../components/MetricsPanel";
import TrainingPanel    from "../components/TrainingPanel";
import StockInfoBar     from "../components/StockInfoBar";
import IndicatorChart   from "../components/IndicatorChart";
import ForecastTable    from "../components/ForecastTable";
import MarketInfoBar    from "../components/MarketInfoBar";
import DataFreshnessBar from "../components/DataFreshnessBar";
import LivePriceChart   from "../components/LivePriceChart";
import LivePriceTicker  from "../components/LivePriceTicker";
import { useStock }     from "../hooks/useStock";
import { useLivePrice } from "../hooks/useLivePrice";

export default function Dashboard() {
  const [activeTicker, setActiveTicker] = useState("RELIANCE.NS");
  const [activeTab, setActiveTab]       = useState("overview");
  const [liveEnabled, setLiveEnabled]   = useState(false);

  const {
    stockData, prediction, metrics,
    trainingStatus, loading, error,
    loadStock, loadPrediction,
    startTraining, pollTraining,
  } = useStock();

  const { latestPrice, priceHistory, wsStatus, STATUS } = useLivePrice(
    activeTicker,
    { enabled: liveEnabled }
  );

  const handleSearch = useCallback(async (ticker, horizon) => {
    setActiveTicker(ticker);
    try {
      await loadStock(ticker);
      await loadPrediction(ticker, horizon);
    } catch { /* Errors captured inside the hook */ }
  }, [loadStock, loadPrediction]);

  const handleTrain = useCallback(async (ticker) => {
    setActiveTicker(ticker);
    try { await startTraining({ ticker }); } catch { /* handled by hook */ }
  }, [startTraining]);

  const handleTrainWithParams = useCallback(async (params) => {
    try { await startTraining(params); } catch {}
  }, [startTraining]);

  const TABS = [
    { id: "overview",   label: "Overview",    Icon: TrendingUp  },
    { id: "candles",    label: "Candlestick", Icon: CandleIcon  },
    { id: "indicators", label: "Indicators",  Icon: BarChart2   },
    { id: "live",       label: "Live",        Icon: Activity    },
    { id: "training",   label: "Train Model", Icon: Settings    },
  ];

  return (
    <div className="min-h-screen bg-surface">
      <div className="mx-auto max-w-7xl space-y-5 px-4 py-6 sm:px-6 lg:px-8">

        {/* ── Hero ──────────────────────────── */}
        <div className="pt-2 pb-1 text-center">
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            Stock Price{" "}
            <span className="text-brand-600">Prediction</span>
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Powered by LSTM Neural Networks · Indian &amp; US Markets · NSE / BSE / NASDAQ
          </p>
        </div>

        {/* ── Search ────────────────────────── */}
        <TickerSearch
          onSearch={handleSearch}
          onTrain={handleTrain}
          loading={loading}
        />

        {/* ── Data freshness bar ────────────── */}
        <DataFreshnessBar
          ticker={activeTicker}
          onDataRefreshed={() => {
            if (activeTicker) loadStock(activeTicker).catch(() => {});
          }}
        />

        {/* ── Error banner ──────────────────── */}
        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
            <p className="flex-1 text-sm text-red-700">{error}</p>
            <button onClick={() => {}} className="cursor-pointer text-red-400 hover:text-red-600">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* ── Stock info bar ────────────────── */}
        {stockData && <StockInfoBar stockData={stockData} ticker={activeTicker} />}

        {/* ── Market info bar ───────────────── */}
        {stockData && <MarketInfoBar ticker={activeTicker} stockData={stockData} />}

        {/* ── Tab navigation ────────────────── */}
        {stockData && (
          <div
            role="tablist"
            aria-label="Dashboard views"
            className="flex gap-1 rounded-xl border border-surface-border bg-surface-card p-1 shadow-card"
          >
            {TABS.map(({ id, label, Icon }) => (
              <button
                key={id}
                role="tab"
                id={`tab-${id}`}
                aria-selected={activeTab === id}
                aria-controls={`tabpanel-${id}`}
                onClick={() => {
                  setActiveTab(id);
                  if (id === "live") setLiveEnabled(true);
                }}
                className={`flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-semibold transition-colors duration-200
                  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600
                  ${activeTab === id
                    ? "bg-brand-600 text-white shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>
        )}

        {/* ── Tab content ───────────────────── */}
        {activeTab === "overview" && (
          <div
            role="tabpanel"
            id="tabpanel-overview"
            aria-labelledby="tab-overview"
            className="space-y-5"
          >
            <PriceChart stockData={stockData} prediction={prediction} ticker={activeTicker} />
            {prediction && (
              <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                <ForecastTable prediction={prediction} ticker={activeTicker} />
                <MetricsPanel  metrics={metrics}       ticker={activeTicker} />
              </div>
            )}
          </div>
        )}

        {activeTab === "candles" && (
          <div role="tabpanel" id="tabpanel-candles" aria-labelledby="tab-candles">
            <CandlestickChart stockData={stockData} ticker={activeTicker} />
          </div>
        )}

        {activeTab === "indicators" && (
          <div role="tabpanel" id="tabpanel-indicators" aria-labelledby="tab-indicators">
            <IndicatorChart stockData={stockData} />
          </div>
        )}

        {activeTab === "live" && (
          <div
            role="tabpanel"
            id="tabpanel-live"
            aria-labelledby="tab-live"
            className="space-y-4"
          >
            {/* Enable / Disable toggle */}
            <div className="flex items-center justify-between rounded-xl border border-surface-border bg-surface-card px-4 py-3 shadow-card">
              <div>
                <p className="text-sm font-semibold text-slate-800">Live Data Stream</p>
                <p className="text-xs text-slate-500">
                  WebSocket — price updates every ~2 s
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={liveEnabled}
                aria-label={liveEnabled ? "Disable live stream" : "Enable live stream"}
                onClick={() => setLiveEnabled((v) => !v)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
                  ${liveEnabled ? "bg-brand-600" : "bg-slate-200"}`}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform duration-200
                    ${liveEnabled ? "translate-x-5" : "translate-x-0.5"}`}
                />
              </button>
            </div>

            {/* Live price ticker */}
            <LivePriceTicker
              latestPrice={latestPrice}
              wsStatus={wsStatus}
              ticker={activeTicker}
            />

            {/* Streaming chart */}
            <LivePriceChart
              priceHistory={priceHistory}
              latestPrice={latestPrice}
              ticker={activeTicker}
              height={360}
            />
          </div>
        )}

        {activeTab === "training" && (
          <div role="tabpanel" id="tabpanel-training" aria-labelledby="tab-training">
            <TrainingPanel
              ticker={activeTicker}
              onTrain={handleTrainWithParams}
              trainingStatus={trainingStatus}
              onPollStatus={pollTraining}
            />
          </div>
        )}

        {/* ── Empty state ───────────────────── */}
        {!stockData && !loading.stock && (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white py-20 text-center shadow-card">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-50">
              <TrendingUp className="h-8 w-8 text-brand-600" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900">Search for a Stock</h3>
            <p className="mt-2 max-w-xs text-sm text-slate-500">
              Enter an Indian (NSE/BSE) or US ticker symbol to load data and AI predictions
            </p>
          </div>
        )}

        {/* ── Loading skeleton ──────────────── */}
        {(loading.stock || loading.predict) && (
          <div className="space-y-4">
            {[400, 200, 200].map((h, i) => (
              <div key={i} className="animate-pulse rounded-2xl bg-slate-100 border border-surface-border"
                style={{ height: `${h}px` }} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
