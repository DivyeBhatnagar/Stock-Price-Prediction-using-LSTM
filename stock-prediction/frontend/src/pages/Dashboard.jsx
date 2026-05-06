import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import SectionHeader from "../components/SectionHeader.jsx";
import StockCard from "../components/StockCard.jsx";
import MetricCard from "../components/MetricCard.jsx";
import ChartCard from "../components/ChartCard.jsx";
import ErrorState from "../components/ErrorState.jsx";
import { SkeletonCard, SkeletonChart } from "../components/Skeleton.jsx";
import { fetchDashboardData } from "../services/api.js";
import LiveTicker from "../components/LiveTicker.jsx";
import { useLiveQuotes } from "../utils/useLiveQuotes.js";

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [watchlist, setWatchlist] = useState([
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "TSLA"
  ]);
  const [search, setSearch] = useState("");

  const {
    quotes,
    loading: quotesLoading,
    error: quotesError
  } = useLiveQuotes({ symbols: watchlist, intervalMs: 15000 });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetchDashboardData();
      setData(response);
    } catch (err) {
      setError("Unable to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (error) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  return (
    <div className="space-y-10">
      <section className="card overflow-hidden p-0">
        <LiveTicker quotes={quotes} />
      </section>

      <section className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Market Dashboard</h1>
          <p className="text-sm text-muted">
            Real-time snapshots powered by Alpha Vantage.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value.toUpperCase())}
            placeholder="Add symbol (e.g. NFLX)"
            className="rounded-full border border-border bg-white px-4 py-2 text-sm text-ink shadow-soft focus:outline-none"
          />
          <button
            className="rounded-full border border-border bg-ink px-4 py-2 text-sm text-white transition hover:opacity-80"
            onClick={() => {
              if (!search) {
                return;
              }
              if (!watchlist.includes(search)) {
                setWatchlist((prev) => [search, ...prev].slice(0, 8));
              }
              setSearch("");
            }}
          >
            Add
          </button>
        </div>
      </section>
      <section>
        <SectionHeader
          title="Market Overview"
          subtitle="Latest snapshot of the NIFTY market sentiment"
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {loading
            ? Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="card p-4 animate-pulse">
                  <div className="h-3 w-20 rounded bg-gray-200" />
                  <div className="mt-3 h-6 w-24 rounded bg-gray-200" />
                </div>
              ))
            : data.marketMetrics.map((metric) => (
                <MetricCard key={metric.label} {...metric} />
              ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        {loading ? (
          <SkeletonChart />
        ) : (
          <ChartCard
            title="NIFTY 50"
            subtitle="Past 10 years (monthly close)"
            data={data.overviewSeries}
            lines={[{ dataKey: "value", color: "#007AFF" }]}
          />
        )}
        <div className="card p-5">
          <p className="text-sm font-semibold text-ink">Market Pulse</p>
          <p className="mt-2 text-sm text-muted">
            Tech and financials are leading the session. Volatility remains
            contained with steady volumes across large caps.
          </p>
          <div className="mt-6 grid gap-3">
            {loading
              ? Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="h-10 rounded bg-gray-200 animate-pulse" />
                ))
              : [
                  "Institutional inflows remain positive",
                  "Banking stocks show strong momentum",
                  "Energy sector stabilizes after a rally"
                ].map((item) => (
                  <div
                    key={item}
                    className="rounded-xl border border-border px-4 py-3 text-sm text-muted"
                  >
                    {item}
                  </div>
                ))}
          </div>
        </div>
      </section>

      <section>
        <SectionHeader
          title="Live Quotes"
          subtitle={
            quotesError
              ? "Showing fallback data"
              : "Auto-refreshes every 15 seconds"
          }
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {quotesLoading
            ? Array.from({ length: 4 }).map((_, index) => (
                <SkeletonCard key={index} />
              ))
            : quotes.map((stock) => (
                <StockCard
                  key={stock.symbol}
                  stock={stock}
                  onClick={() =>
                    navigate(`/stocks?ticker=${encodeURIComponent(stock.symbol)}`)
                  }
                />
              ))}
        </div>
      </section>
    </div>
  );
}
