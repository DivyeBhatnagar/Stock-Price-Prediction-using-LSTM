// TickerSearch.jsx  —  Search bar + horizon selector + action buttons (light theme)

import { useState } from "react";
import { Search, Zap, RefreshCw, IndianRupee, DollarSign } from "lucide-react";
import { autoConvertTicker, isIndianTicker } from "../utils/currency";

const POPULAR_INDIAN = [
  { symbol: "RELIANCE.NS",   label: "RELIANCE"    },
  { symbol: "TCS.NS",        label: "TCS"         },
  { symbol: "INFY.NS",       label: "INFY"        },
  { symbol: "HDFCBANK.NS",   label: "HDFC Bank"   },
  { symbol: "ICICIBANK.NS",  label: "ICICI"       },
  { symbol: "SBIN.NS",       label: "SBI"         },
  { symbol: "ITC.NS",        label: "ITC"         },
  { symbol: "LT.NS",         label: "L&T"         },
  { symbol: "BHARTIARTL.NS", label: "Airtel"      },
  { symbol: "TATAMOTORS.NS", label: "Tata Motors" },
];

const POPULAR_US = [
  { symbol: "AAPL",  label: "AAPL"  },
  { symbol: "TSLA",  label: "TSLA"  },
  { symbol: "MSFT",  label: "MSFT"  },
  { symbol: "GOOGL", label: "GOOGL" },
  { symbol: "AMZN",  label: "AMZN"  },
  { symbol: "NVDA",  label: "NVDA"  },
];

const INDICES = [
  { symbol: "^NSEI",    label: "NIFTY 50"   },
  { symbol: "^NSEBANK", label: "BANK NIFTY" },
  { symbol: "^BSESN",   label: "SENSEX"     },
];

const HORIZONS = [7, 14, 30, 60, 90];

export default function TickerSearch({ onSearch, onTrain, loading }) {
  const [ticker,  setTicker]  = useState("RELIANCE.NS");
  const [horizon, setHorizon] = useState(30);
  const [market,  setMarket]  = useState("india");

  const submit = (e) => {
    e?.preventDefault();
    const t = autoConvertTicker(ticker.trim());
    if (t) { setTicker(t); onSearch(t, horizon); }
  };

  const trainClick = () => {
    const t = autoConvertTicker(ticker.trim());
    if (t) { setTicker(t); onTrain(t); }
  };

  const selectTicker = (sym) => { setTicker(sym); onSearch(sym, horizon); };

  const popularList = market === "india" ? POPULAR_INDIAN : POPULAR_US;

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card p-6 shadow-card">

      {/* Header row */}
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">
          Stock Search &amp; Prediction
        </h2>

        {/* Market toggle */}
        <div className="flex items-center gap-0.5 rounded-lg border border-surface-border bg-surface p-0.5">
          <button
            onClick={() => setMarket("india")}
            className={`cursor-pointer flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors duration-200 ${
              market === "india"
                ? "bg-orange-500 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-900"
            }`}
          >
            🇮🇳 India
          </button>
          <button
            onClick={() => setMarket("us")}
            className={`cursor-pointer flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors duration-200 ${
              market === "us"
                ? "bg-brand-600 text-white shadow-sm"
                : "text-slate-500 hover:text-slate-900"
            }`}
          >
            🇺🇸 US
          </button>
        </div>
      </div>

      {/* Search form */}
      <form onSubmit={submit} className="flex gap-2.5">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder={market === "india" ? "Enter ticker — e.g. RELIANCE, TCS, INFY" : "Enter ticker — e.g. AAPL, TSLA"}
            className="w-full rounded-xl border border-surface-border bg-white py-2.5 pl-9 pr-4 font-mono text-sm text-slate-900 placeholder-slate-400 shadow-sm outline-none ring-brand-600 transition-all focus:border-brand-600 focus:ring-2"
          />
        </div>

        <select
          value={horizon}
          onChange={(e) => setHorizon(Number(e.target.value))}
          className="cursor-pointer rounded-xl border border-surface-border bg-white px-3 py-2.5 text-sm font-medium text-slate-700 shadow-sm outline-none ring-brand-600 transition-all focus:border-brand-600 focus:ring-2"
        >
          {HORIZONS.map((h) => <option key={h} value={h}>{h}d</option>)}
        </select>

        <button
          type="submit"
          disabled={loading.stock || loading.predict}
          className="flex cursor-pointer items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors duration-200 hover:bg-brand-700 active:scale-[.98] disabled:opacity-50"
        >
          {(loading.stock || loading.predict)
            ? <RefreshCw className="h-4 w-4 animate-spin" />
            : <Search className="h-4 w-4" />}
          Predict
        </button>
      </form>

      {/* Indian Indices */}
      {market === "india" && (
        <div className="mt-4 flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-medium text-slate-400">Indices:</span>
          {INDICES.map((idx) => (
            <button
              key={idx.symbol}
              onClick={() => selectTicker(idx.symbol)}
              className={`cursor-pointer rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors duration-200 ${
                ticker === idx.symbol
                  ? "border-orange-400 bg-orange-50 text-orange-600"
                  : "border-slate-200 text-slate-500 hover:border-orange-400 hover:text-orange-600"
              }`}
            >
              {idx.label}
            </button>
          ))}
        </div>
      )}

      {/* Popular tickers */}
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        <span className="text-xs font-medium text-slate-400">Popular:</span>
        {popularList.map((t) => (
          <button
            key={t.symbol}
            onClick={() => selectTicker(t.symbol)}
            className={`cursor-pointer rounded-md border px-2.5 py-1 font-mono text-xs font-semibold transition-colors duration-200 ${
              ticker === t.symbol
                ? "border-brand-400 bg-brand-50 text-brand-700"
                : "border-slate-200 text-slate-500 hover:border-brand-400 hover:text-brand-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Train button */}
      <div className="mt-5 flex items-center gap-3 border-t border-surface-border pt-4">
        <button
          onClick={trainClick}
          disabled={loading.train}
          className="flex cursor-pointer items-center gap-2 rounded-xl border border-brand-200 bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-700 transition-colors duration-200 hover:bg-brand-100 disabled:opacity-50"
        >
          {loading.train
            ? <RefreshCw className="h-4 w-4 animate-spin" />
            : <Zap className="h-4 w-4" />}
          Train Model for {ticker || "…"}
        </button>
        <p className="text-xs text-slate-400">
          First-time use requires training. Takes ~2-5 min.
        </p>
      </div>
    </div>
  );
}

const POPULAR_INDIAN = [
  { symbol: "RELIANCE.NS",  label: "RELIANCE" },
  { symbol: "TCS.NS",       label: "TCS" },
  { symbol: "INFY.NS",      label: "INFY" },
  { symbol: "HDFCBANK.NS",  label: "HDFC Bank" },
  { symbol: "ICICIBANK.NS", label: "ICICI" },
  { symbol: "SBIN.NS",      label: "SBI" },
  { symbol: "ITC.NS",       label: "ITC" },
  { symbol: "LT.NS",        label: "L&T" },
  { symbol: "BHARTIARTL.NS",label: "Airtel" },
  { symbol: "TATAMOTORS.NS",label: "Tata Motors" },
];

const POPULAR_US = [
  { symbol: "AAPL",  label: "AAPL" },
  { symbol: "TSLA",  label: "TSLA" },
  { symbol: "MSFT",  label: "MSFT" },
  { symbol: "GOOGL", label: "GOOGL" },
  { symbol: "AMZN",  label: "AMZN" },
  { symbol: "NVDA",  label: "NVDA" },
];

const INDICES = [
  { symbol: "^NSEI",     label: "NIFTY 50" },
  { symbol: "^NSEBANK",  label: "BANK NIFTY" },
  { symbol: "^BSESN",    label: "SENSEX" },
];

const HORIZONS = [7, 14, 30, 60, 90];

export default function TickerSearch({ onSearch, onTrain, loading }) {
  const [ticker,  setTicker]  = useState("RELIANCE.NS");
  const [horizon, setHorizon] = useState(30);
  const [market,  setMarket]  = useState("india"); // "india" | "us"

  const submit = (e) => {
    e?.preventDefault();
    const t = autoConvertTicker(ticker.trim());
    if (t) {
      setTicker(t);
      onSearch(t, horizon);
    }
  };

  const trainClick = () => {
    const t = autoConvertTicker(ticker.trim());
    if (t) {
      setTicker(t);
      onTrain(t);
    }
  };

  const selectTicker = (sym) => {
    setTicker(sym);
    onSearch(sym, horizon);
  };

  const popularList = market === "india" ? POPULAR_INDIAN : POPULAR_US;
  const CurrIcon    = isIndianTicker(ticker) ? IndianRupee : DollarSign;

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card p-6 shadow-xl">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">
          🔍 Stock Search &amp; Prediction
        </h2>
        {/* Market toggle */}
        <div className="flex items-center gap-1 rounded-lg border border-surface-border bg-surface p-0.5">
          <button
            onClick={() => setMarket("india")}
            className={`flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
              market === "india"
                ? "bg-orange-500/20 text-orange-400"
                : "text-slate-400 hover:text-white"
            }`}
          >
            🇮🇳 India
          </button>
          <button
            onClick={() => setMarket("us")}
            className={`flex items-center gap-1 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
              market === "us"
                ? "bg-blue-500/20 text-blue-400"
                : "text-slate-400 hover:text-white"
            }`}
          >
            🇺🇸 US
          </button>
        </div>
      </div>

      {/* Ticker input */}
      <form onSubmit={submit} className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder={market === "india" ? "Enter ticker — e.g. RELIANCE, TCS, INFY" : "Enter ticker — e.g. AAPL, TSLA"}
            className="w-full rounded-xl border border-surface-border bg-surface py-3 pl-10 pr-4 text-sm font-mono text-white placeholder-slate-500 outline-none ring-blue-500 transition focus:border-blue-500 focus:ring-2"
          />
        </div>

        {/* Horizon selector */}
        <select
          value={horizon}
          onChange={(e) => setHorizon(Number(e.target.value))}
          className="rounded-xl border border-surface-border bg-surface px-3 py-3 text-sm text-white outline-none ring-blue-500 transition focus:border-blue-500 focus:ring-2"
        >
          {HORIZONS.map((h) => (
            <option key={h} value={h}>
              {h}d
            </option>
          ))}
        </select>

        <button
          type="submit"
          disabled={loading.stock || loading.predict}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/30 transition hover:bg-blue-500 active:scale-95 disabled:opacity-50"
        >
          {(loading.stock || loading.predict) ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          Predict
        </button>
      </form>

      {/* Indian Indices (only shown in India mode) */}
      {market === "india" && (
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-xs text-slate-500">Indices:</span>
          {INDICES.map((idx) => (
            <button
              key={idx.symbol}
              onClick={() => selectTicker(idx.symbol)}
              className={`rounded-lg border px-3 py-1 text-xs font-semibold transition hover:border-orange-500 hover:text-orange-400 ${
                ticker === idx.symbol
                  ? "border-orange-500 text-orange-400 bg-orange-500/10"
                  : "border-surface-border text-slate-400"
              }`}
            >
              {idx.label}
            </button>
          ))}
        </div>
      )}

      {/* Popular tickers */}
      <div className="mt-3 flex flex-wrap gap-2">
        <span className="text-xs text-slate-500">Popular:</span>
        {popularList.map((t) => (
          <button
            key={t.symbol}
            onClick={() => selectTicker(t.symbol)}
            className={`rounded-lg border px-3 py-1 text-xs font-mono font-semibold transition hover:border-blue-500 hover:text-blue-400 ${
              ticker === t.symbol
                ? "border-blue-500 text-blue-400"
                : "border-surface-border text-slate-400"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Train button */}
      <div className="mt-5 flex items-center gap-3 border-t border-surface-border pt-5">
        <button
          onClick={trainClick}
          disabled={loading.train}
          className="flex items-center gap-2 rounded-xl border border-blue-500/40 bg-blue-500/10 px-5 py-2.5 text-sm font-semibold text-blue-400 transition hover:bg-blue-500/20 disabled:opacity-50"
        >
          {loading.train ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : (
            <Zap className="h-4 w-4" />
          )}
          Train Model for {ticker || "…"}
        </button>
        <p className="text-xs text-slate-500">
          First-time use requires training. Takes ~2-5 min.
        </p>
      </div>
    </div>
  );
}
