import { useEffect, useState } from "react";
import SectionHeader from "../components/SectionHeader.jsx";
import ChartCard from "../components/ChartCard.jsx";
import ErrorState from "../components/ErrorState.jsx";
import { SkeletonChart } from "../components/Skeleton.jsx";
import { formatCurrency } from "../utils/formatters.js";
import {
  fetchPrediction,
  fetchLocalTickers,
  trainModel,
  refreshTickerData,
  fetchTrainingStatus,
  fetchPriceHistory
} from "../services/api.js";

export default function Prediction() {
  const [ticker, setTicker] = useState("RELIANCE.NS");
  const [available, setAvailable] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [training, setTraining] = useState(false);
  const [trainingStatus, setTrainingStatus] = useState(null);
  const [historyWindow, setHistoryWindow] = useState("5Y");
  const [epochs, setEpochs] = useState(60);
  const [priceRange, setPriceRange] = useState("1Y");
  const [priceSeries, setPriceSeries] = useState([]);
  const [priceLoading, setPriceLoading] = useState(true);
  const [priceLastDate, setPriceLastDate] = useState(null);

  const loadPrediction = async (symbol) => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetchPrediction(symbol);
      setData(response);
    } catch (err) {
      setError("Unable to load prediction.");
    } finally {
      setLoading(false);
    }
  };

  const handleTrain = async () => {
    try {
      setTraining(true);
      setTrainingStatus({ status: "running", epoch: 0, epochs_total: epochs });
      refreshTickerData(ticker).catch(() => null);

      const now = new Date();
      const years = Number.parseInt(historyWindow.replace("Y", ""), 10);
      const start = new Date(now.getFullYear() - years, now.getMonth(), now.getDate());
      const startDate = start.toISOString().slice(0, 10);

      await trainModel(ticker, { start_date: startDate, epochs });

      const poll = setInterval(async () => {
        try {
          const status = await fetchTrainingStatus(ticker);
          if (status.status === "completed") {
            clearInterval(poll);
            setTraining(false);
            setTrainingStatus(status);
            loadPrediction(ticker);
          } else if (status.status === "failed") {
            clearInterval(poll);
            setTraining(false);
            setTrainingStatus(status);
          } else {
            setTrainingStatus(status);
          }
        } catch (err) {
          if (err?.response?.status === 404) {
            setTrainingStatus({ status: "running", epoch: 0, epochs_total: epochs });
            return;
          }
          clearInterval(poll);
          setTraining(false);
          setTrainingStatus({ status: "failed", error: "Unable to fetch training status." });
        }
      }, 5000);
    } catch (err) {
      setTraining(false);
      setTrainingStatus({ status: "failed", error: "Unable to start training." });
    }
  };

  const loadPriceHistory = async (symbol, range) => {
    try {
      setPriceLoading(true);
      const response = await fetchPriceHistory(symbol, range);
      setPriceSeries(response.series || []);
      setPriceLastDate(response.lastDate || null);
    } catch (err) {
      setPriceSeries([]);
      setPriceLastDate(null);
    } finally {
      setPriceLoading(false);
    }
  };

  useEffect(() => {
    loadPrediction(ticker);
    fetchLocalTickers()
      .then((tickers) => {
        if (tickers.length) {
          setAvailable(tickers.map((symbol) => ({ symbol, name: symbol })));
        }
      })
      .catch(() => {
        setAvailable([]);
      });
  }, []);

  useEffect(() => {
    loadPriceHistory(ticker, priceRange);
  }, [ticker, priceRange]);

  if (error) {
    return <ErrorState message={error} onRetry={() => loadPrediction(ticker)} />;
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        title="Prediction"
        subtitle="ML-based price projections"
        action={
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={ticker}
              onChange={(event) => setTicker(event.target.value)}
              className="rounded-full border border-border bg-white px-4 py-2 text-sm text-ink shadow-soft focus:outline-none"
            >
              {available.length ? (
                available.map((stock) => (
                  <option key={stock.symbol} value={stock.symbol}>
                    {stock.name} ({stock.symbol})
                  </option>
                ))
              ) : (
                <option value={ticker}>{ticker}</option>
              )}
            </select>
            <button
              className="rounded-full border border-border bg-ink px-4 py-2 text-sm text-white transition hover:opacity-80"
              onClick={() => loadPrediction(ticker)}
            >
              Predict
            </button>
            <button
              className="rounded-full border border-border px-4 py-2 text-sm text-ink transition hover:opacity-70"
              onClick={handleTrain}
              disabled={training}
            >
              {training ? "Training..." : "Train Model"}
            </button>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="card p-4">
          <p className="text-xs text-muted">Training History</p>
          <select
            value={historyWindow}
            onChange={(event) => setHistoryWindow(event.target.value)}
            className="mt-2 w-full rounded-xl border border-border bg-white px-3 py-2 text-sm text-ink"
          >
            {["1Y", "2Y", "5Y", "10Y"].map((item) => (
              <option key={item} value={item}>
                {item} of data
              </option>
            ))}
          </select>
        </div>
        <div className="card p-4">
          <p className="text-xs text-muted">Epochs</p>
          <input
            type="number"
            min={10}
            max={300}
            value={epochs}
            onChange={(event) => setEpochs(Number(event.target.value))}
            className="mt-2 w-full rounded-xl border border-border bg-white px-3 py-2 text-sm text-ink"
          />
        </div>
        <div className="card p-4">
          <p className="text-xs text-muted">Tip</p>
          <p className="mt-2 text-sm text-muted">
            Smaller windows and fewer epochs train faster.
          </p>
        </div>
      </div>

      {trainingStatus && (
        <div className="card max-w-sm p-4 text-sm">
          <p className="text-xs text-muted">Training Status</p>
          <p className="mt-1 font-semibold text-ink">
            {trainingStatus.status === "failed"
              ? "Failed"
              : trainingStatus.status === "completed"
              ? "Completed"
              : "Running"}
          </p>
          {trainingStatus.epoch !== undefined && (
            <p className="mt-2 text-sm text-muted">
              Epoch {trainingStatus.epoch}/{trainingStatus.epochs_total || "--"}
            </p>
          )}
          {trainingStatus.error && (
            <p className="mt-2 text-xs text-rose-500">{trainingStatus.error}</p>
          )}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
        <div className="card p-6">
          <p className="text-sm text-muted">Predicted Price</p>
          <p className="mt-2 text-3xl font-semibold text-ink">
            {loading ? "--" : formatCurrency(data.predictedPrice)}
          </p>
          <div className="mt-6">
            <p className="text-xs text-muted">Confidence Level</p>
            <div className="mt-2 h-2 w-full rounded-full bg-gray-200">
              <div
                className="h-2 rounded-full bg-accent"
                style={{ width: `${loading ? 0 : data.confidence * 100}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-muted">
              {loading ? "" : `${Math.round(data.confidence * 100)}% confidence`}
            </p>
          </div>
        </div>

        <div className="card p-6">
          <p className="text-sm text-muted">Model Insights</p>
          <ul className="mt-4 space-y-3 text-sm text-muted">
            <li>• LSTM ensemble with 30-day lookback window</li>
            <li>• Momentum + volume features prioritized</li>
            <li>• Model refresh cadence: daily</li>
          </ul>
        </div>
      </div>

      {loading ? (
        <SkeletonChart />
      ) : (
        <ChartCard
          title="Actual vs Predicted"
          subtitle="Next 5 trading sessions"
          data={data.series}
          lines={[
            { dataKey: "actual", color: "#111111" },
            { dataKey: "predicted", color: "#007AFF" }
          ]}
        />
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-semibold text-ink">Live Price</p>
        <div className="flex flex-wrap items-center gap-2">
          {[
            { label: "1D", value: "1D" },
            { label: "10Y", value: "10Y" },
            { label: "5Y", value: "5Y" },
            { label: "1Y", value: "1Y" },
            { label: "1M", value: "1M" }
          ].map((range) => (
            <button
              key={range.value}
              onClick={() => setPriceRange(range.value)}
              className={`rounded-full border px-3 py-1 text-xs transition ${
                priceRange === range.value
                  ? "border-ink bg-ink text-white"
                  : "border-border bg-white text-ink hover:opacity-80"
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {priceLoading ? (
        <SkeletonChart />
      ) : (
        <ChartCard
          title="Real Price"
          subtitle={
            priceLastDate
              ? `Latest close: ${priceLastDate}`
              : "Latest close"
          }
          data={priceSeries}
          lines={[{ dataKey: "value", color: "#16A34A" }]}
        />
      )}
    </div>
  );
}
