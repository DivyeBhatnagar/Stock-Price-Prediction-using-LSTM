import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import SectionHeader from "../components/SectionHeader.jsx";
import ChartCard from "../components/ChartCard.jsx";
import ErrorState from "../components/ErrorState.jsx";
import { SkeletonChart } from "../components/Skeleton.jsx";
import { formatCurrency } from "../utils/formatters.js";
import { fetchStockDetail, fetchStockFull } from "../services/api.js";

const timeFilters = ["1D", "1W", "1M", "1Y", "10Y"];

export default function StockDetail() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState("RELIANCE");
  const [filter, setFilter] = useState("1M");
  const [data, setData] = useState(null);
  const [fullInfo, setFullInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadStock = async (ticker) => {
    try {
      setLoading(true);
      setError(null);
      const [response, info] = await Promise.all([
        fetchStockDetail(ticker),
        fetchStockFull(ticker)
      ]);
      setData(response);
      setFullInfo(info);
      setSearchParams({ ticker });
    } catch (err) {
      setError("Unable to load stock detail.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const initial = searchParams.get("ticker");
    if (initial) {
      setQuery(initial.toUpperCase());
      loadStock(initial);
      return;
    }
    loadStock(query);
  }, []);

  if (error) {
    return <ErrorState message={error} onRetry={() => loadStock(query)} />;
  }

  return (
    <div className="space-y-8">
      <SectionHeader
        title="Stock Detail"
        subtitle="Search and analyze individual stocks"
        action={
          <div className="flex items-center gap-2 rounded-full border border-border bg-white px-4 py-2 text-sm text-muted shadow-soft">
            <span className="text-xs text-muted">🔍</span>
            <input
              className="w-40 bg-transparent text-sm text-ink placeholder:text-muted focus:outline-none"
              value={query}
              onChange={(event) => setQuery(event.target.value.toUpperCase())}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  loadStock(query);
                }
              }}
              placeholder="Search ticker"
            />
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-3">
        <div className="card p-5">
          <p className="text-sm text-muted">Price</p>
          <p className="mt-2 text-2xl font-semibold text-ink">
            {loading ? "--" : formatCurrency(data.price)}
          </p>
          <p className="mt-2 text-xs text-muted">
            {fullInfo?.marketInfo?.exchange || "Market"}
          </p>
        </div>
        <div className="card p-5">
          <p className="text-sm text-muted">Market Cap</p>
          <p className="mt-2 text-2xl font-semibold text-ink">
            {loading
              ? "--"
              : fullInfo?.info?.marketCap
              ? formatCurrency(fullInfo.info.marketCap)
              : "--"}
          </p>
          <p className="mt-2 text-xs text-muted">
            {fullInfo?.marketInfo?.currency_symbol || "₹"} currency
          </p>
        </div>
        <div className="card p-5">
          <p className="text-sm text-muted">P/E Ratio</p>
          <p className="mt-2 text-2xl font-semibold text-ink">
            {loading ? "--" : fullInfo?.info?.peRatio ?? "--"}
          </p>
          <p className="mt-2 text-xs text-muted">
            {fullInfo?.marketInfo?.timezone || "Local time"}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {timeFilters.map((item) => (
          <button
            key={item}
            className={`rounded-full border px-4 py-1.5 text-sm transition ${
              filter === item
                ? "border-accent bg-accent/10 text-accent"
                : "border-border text-muted hover:text-ink"
            }`}
            onClick={() => setFilter(item)}
          >
            {item}
          </button>
        ))}
      </div>

      {loading ? (
        <SkeletonChart />
      ) : (
        <ChartCard
          title={`${data.name} (${data.ticker})`}
          subtitle={`Performance view: ${filter}`}
          data={(() => {
            const records = fullInfo?.records || [];
            const sliceBy = {
              "1D": 1,
              "1W": 5,
              "1M": 22,
              "1Y": 252,
              "10Y": records.length
            };
            const count = sliceBy[filter] || 22;
            return records.slice(-count).map((row) => ({
              label: row.date || row.Date,
              actual: row.Close ?? row.close ?? row["Adj Close"]
            }));
          })()}
          lines={[{ dataKey: "actual", color: "#007AFF" }]}
        />
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <p className="text-sm font-semibold text-ink">Latest Metrics</p>
          <div className="mt-4 grid gap-3 text-sm text-muted">
            {fullInfo?.latest ? (
              Object.entries(fullInfo.latest).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="text-ink">
                    {typeof value === "number" ? value.toFixed(2) : value}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">No metrics available.</p>
            )}
          </div>
        </div>
        <div className="card p-5">
          <p className="text-sm font-semibold text-ink">Model Evaluation</p>
          <div className="mt-4 grid gap-3 text-sm text-muted">
            {fullInfo?.metrics?.metrics ? (
              Object.entries(fullInfo.metrics.metrics).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="text-ink">
                    {typeof value === "number" ? value.toFixed(4) : value}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">
                Train the model to view evaluation metrics.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="card p-5">
        <p className="text-sm font-semibold text-ink">Original Historical Data</p>
        <p className="mt-1 text-xs text-muted">Last 10 sessions from source data</p>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm text-muted">
            <thead className="border-b border-border text-xs text-muted">
              <tr>
                <th className="py-2 pr-4 font-medium">Date</th>
                <th className="py-2 pr-4 font-medium">Open</th>
                <th className="py-2 pr-4 font-medium">High</th>
                <th className="py-2 pr-4 font-medium">Low</th>
                <th className="py-2 pr-4 font-medium">Close</th>
                <th className="py-2 pr-4 font-medium">Volume</th>
              </tr>
            </thead>
            <tbody>
              {(fullInfo?.records || [])
                .slice(-10)
                .reverse()
                .map((row, index) => (
                  <tr key={`${row.date || row.Date}-${index}`} className="border-b border-border/50">
                    <td className="py-2 pr-4 text-ink">{row.date || row.Date}</td>
                    <td className="py-2 pr-4">{row.Open ?? row.open ?? "--"}</td>
                    <td className="py-2 pr-4">{row.High ?? row.high ?? "--"}</td>
                    <td className="py-2 pr-4">{row.Low ?? row.low ?? "--"}</td>
                    <td className="py-2 pr-4">{row.Close ?? row.close ?? "--"}</td>
                    <td className="py-2 pr-4">{row.Volume ?? row.volume ?? "--"}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
