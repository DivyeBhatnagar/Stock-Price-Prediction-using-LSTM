// TickerSearch.jsx  —  NIFTY 50 Stock Search & Prediction Panel (light theme)

import { useState, useMemo, useRef, useEffect } from "react";
import { Search, Zap, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";

// ── NIFTY 50 Universe (all 50 NSE stocks) ────────────────────────────────────
const NIFTY50 = [
  // Banking & Finance
  { symbol: "HDFCBANK.NS",   label: "HDFC Bank",        sector: "Banking" },
  { symbol: "ICICIBANK.NS",  label: "ICICI Bank",        sector: "Banking" },
  { symbol: "KOTAKBANK.NS",  label: "Kotak Bank",        sector: "Banking" },
  { symbol: "AXISBANK.NS",   label: "Axis Bank",         sector: "Banking" },
  { symbol: "SBIN.NS",       label: "SBI",               sector: "Banking" },
  { symbol: "INDUSINDBK.NS", label: "IndusInd Bank",     sector: "Banking" },
  { symbol: "BAJFINANCE.NS", label: "Bajaj Finance",     sector: "Finance" },
  { symbol: "BAJAJFINSV.NS", label: "Bajaj Finserv",     sector: "Finance" },
  { symbol: "SHRIRAMFIN.NS", label: "Shriram Finance",   sector: "Finance" },
  { symbol: "HDFCLIFE.NS",   label: "HDFC Life",         sector: "Insurance" },
  { symbol: "SBILIFE.NS",    label: "SBI Life",          sector: "Insurance" },
  // IT Services
  { symbol: "TCS.NS",        label: "TCS",               sector: "IT" },
  { symbol: "INFY.NS",       label: "Infosys",           sector: "IT" },
  { symbol: "HCLTECH.NS",    label: "HCL Tech",          sector: "IT" },
  { symbol: "WIPRO.NS",      label: "Wipro",             sector: "IT" },
  { symbol: "TECHM.NS",      label: "Tech Mahindra",     sector: "IT" },
  { symbol: "LTIM.NS",       label: "LTIMindtree",       sector: "IT" },
  // Energy & Oil
  { symbol: "RELIANCE.NS",   label: "Reliance",          sector: "Energy" },
  { symbol: "ONGC.NS",       label: "ONGC",              sector: "Energy" },
  { symbol: "BPCL.NS",       label: "BPCL",              sector: "Energy" },
  { symbol: "NTPC.NS",       label: "NTPC",              sector: "Power" },
  { symbol: "POWERGRID.NS",  label: "Power Grid",        sector: "Power" },
  { symbol: "COALINDIA.NS",  label: "Coal India",        sector: "Energy" },
  // Automobile
  { symbol: "MARUTI.NS",     label: "Maruti Suzuki",     sector: "Auto" },
  { symbol: "BAJAJ-AUTO.NS", label: "Bajaj Auto",        sector: "Auto" },
  { symbol: "HEROMOTOCO.NS", label: "Hero MotoCorp",     sector: "Auto" },
  { symbol: "EICHERMOT.NS",  label: "Eicher Motors",     sector: "Auto" },
  { symbol: "M&M.NS",        label: "M&M",               sector: "Auto" },
  // FMCG & Consumer
  { symbol: "HINDUNILVR.NS", label: "HUL",               sector: "FMCG" },
  { symbol: "ITC.NS",        label: "ITC",               sector: "FMCG" },
  { symbol: "NESTLEIND.NS",  label: "Nestle India",      sector: "FMCG" },
  { symbol: "BRITANNIA.NS",  label: "Britannia",         sector: "FMCG" },
  { symbol: "TATACONSUM.NS", label: "Tata Consumer",     sector: "FMCG" },
  { symbol: "TITAN.NS",      label: "Titan",             sector: "Consumer" },
  { symbol: "ASIANPAINT.NS", label: "Asian Paints",      sector: "Consumer" },
  // Pharma & Healthcare
  { symbol: "SUNPHARMA.NS",  label: "Sun Pharma",        sector: "Pharma" },
  { symbol: "DRREDDY.NS",    label: "Dr. Reddy's",       sector: "Pharma" },
  { symbol: "CIPLA.NS",      label: "Cipla",             sector: "Pharma" },
  { symbol: "DIVISLAB.NS",   label: "Divi's Labs",       sector: "Pharma" },
  { symbol: "APOLLOHOSP.NS", label: "Apollo Hospitals",  sector: "Healthcare" },
  // Metals & Cement
  { symbol: "TATASTEEL.NS",  label: "Tata Steel",        sector: "Metals" },
  { symbol: "JSWSTEEL.NS",   label: "JSW Steel",         sector: "Metals" },
  { symbol: "HINDALCO.NS",   label: "Hindalco",          sector: "Metals" },
  { symbol: "ULTRACEMCO.NS", label: "UltraTech Cement",  sector: "Cement" },
  { symbol: "GRASIM.NS",     label: "Grasim",            sector: "Cement" },
  // Infrastructure & Conglomerate
  { symbol: "LT.NS",         label: "L&T",               sector: "Infra" },
  { symbol: "ADANIENT.NS",   label: "Adani Enterprises", sector: "Infra" },
  { symbol: "ADANIPORTS.NS", label: "Adani Ports",       sector: "Infra" },
  { symbol: "BHARTIARTL.NS", label: "Bharti Airtel",     sector: "Telecom" },
];

// Featured / quick-pick stocks (top 12 most traded)
const FEATURED = [
  "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS","SBIN.NS",
  "ITC.NS","LT.NS","BHARTIARTL.NS","BAJFINANCE.NS","AXISBANK.NS","KOTAKBANK.NS",
];

const HORIZONS = [7, 14, 30, 60, 90];

// Sector accent colours (light theme)
const SECTOR_COLOR = {
  Banking: "blue", Finance: "blue", Insurance: "blue",
  IT: "violet",
  Energy: "amber", Power: "amber",
  Auto: "green",
  FMCG: "orange", Consumer: "orange",
  Pharma: "pink", Healthcare: "pink",
  Metals: "slate", Cement: "slate",
  Infra: "cyan", Telecom: "cyan",
};

const colorCls = (sector, active) => {
  const c = SECTOR_COLOR[sector] ?? "slate";
  return active
    ? `border-${c}-400 bg-${c}-50 text-${c}-700`
    : `border-slate-200 text-slate-500 hover:border-${c}-400 hover:text-${c}-700`;
};

// ── Component ────────────────────────────────────────────────────────────────
export default function TickerSearch({ onSearch, onTrain, loading }) {
  const [ticker,     setTicker]     = useState("RELIANCE.NS");
  const [horizon,    setHorizon]    = useState(30);
  const [showAll,    setShowAll]    = useState(false);
  const [query,      setQuery]      = useState("");
  const [dropdown,   setDropdown]   = useState(false);
  const inputRef = useRef(null);

  // Autocomplete: filter NIFTY50 by query
  const suggestions = useMemo(() => {
    const q = query.trim().toUpperCase();
    if (!q) return [];
    return NIFTY50.filter(
      (s) => s.symbol.includes(q) || s.label.toUpperCase().includes(q)
    ).slice(0, 8);
  }, [query]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (!inputRef.current?.closest("form")?.contains(e.target)) {
        setDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const commitTicker = (sym) => {
    setTicker(sym);
    setQuery("");
    setDropdown(false);
    onSearch(sym, horizon);
  };

  const submit = (e) => {
    e?.preventDefault();
    if (suggestions.length > 0) { commitTicker(suggestions[0].symbol); return; }
    const t = (query || ticker).trim().toUpperCase();
    if (!t.endsWith(".NS")) {
      const match = NIFTY50.find((s) => s.symbol.startsWith(t + "."));
      if (match) { commitTicker(match.symbol); return; }
    }
    commitTicker(t);
  };

  const trainClick = () => { if (ticker) onTrain(ticker); };

  const featured = NIFTY50.filter((s) => FEATURED.includes(s.symbol));

  // Sector-grouped view for "Browse all"
  const grouped = useMemo(() => {
    const map = {};
    NIFTY50.forEach((s) => {
      (map[s.sector] = map[s.sector] ?? []).push(s);
    });
    return map;
  }, []);

  const currentStock = NIFTY50.find((s) => s.symbol === ticker);

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card p-6 shadow-card">

      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">NIFTY 50 — Stock Search</h2>
          <p className="text-xs text-slate-400 mt-0.5">50 NSE large-cap stocks · 10 years of data</p>
        </div>
        <span className="rounded-full border border-orange-200 bg-orange-50 px-3 py-1 text-xs font-semibold text-orange-600">
          🇮🇳 NSE India
        </span>
      </div>

      {/* Search form with autocomplete */}
      <form onSubmit={submit} className="relative flex gap-2.5" ref={inputRef}>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={query || ticker}
            onChange={(e) => { setQuery(e.target.value.toUpperCase()); setDropdown(true); }}
            onFocus={() => setDropdown(true)}
            placeholder="Search NIFTY 50 — e.g. RELIANCE, TCS, HDFCBANK"
            className="w-full rounded-xl border border-surface-border bg-white py-2.5 pl-9 pr-4 font-mono text-sm text-slate-900 placeholder-slate-400 shadow-sm outline-none transition-all focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20"
          />
          {/* Autocomplete dropdown */}
          {dropdown && suggestions.length > 0 && (
            <ul className="absolute top-full left-0 z-50 mt-1 w-full rounded-xl border border-surface-border bg-white shadow-card-md overflow-hidden">
              {suggestions.map((s) => (
                <li key={s.symbol}>
                  <button
                    type="button"
                    onMouseDown={() => commitTicker(s.symbol)}
                    className="flex w-full items-center justify-between px-4 py-2.5 text-sm hover:bg-slate-50 transition-colors"
                  >
                    <span className="font-mono font-semibold text-slate-900">{s.label}</span>
                    <span className="text-xs text-slate-400">{s.symbol} · {s.sector}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <select
          value={horizon}
          onChange={(e) => setHorizon(Number(e.target.value))}
          className="cursor-pointer rounded-xl border border-surface-border bg-white px-3 py-2.5 text-sm font-medium text-slate-700 shadow-sm outline-none transition-all focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20"
        >
          {HORIZONS.map((h) => <option key={h} value={h}>{h}d</option>)}
        </select>

        <button
          type="submit"
          disabled={loading.stock || loading.predict}
          className="flex cursor-pointer items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-700 active:scale-[.98] disabled:opacity-50"
        >
          {(loading.stock || loading.predict)
            ? <RefreshCw className="h-4 w-4 animate-spin" />
            : <Search className="h-4 w-4" />}
          Predict
        </button>
      </form>

      {/* Quick-pick: top 12 NIFTY stocks */}
      <div className="mt-4 flex flex-wrap items-center gap-1.5">
        <span className="text-xs font-medium text-slate-400 shrink-0">Quick:</span>
        {featured.map((s) => (
          <button
            key={s.symbol}
            onClick={() => commitTicker(s.symbol)}
            className={`cursor-pointer rounded-md border px-2.5 py-1 font-mono text-xs font-semibold transition-colors ${
              ticker === s.symbol
                ? "border-brand-400 bg-brand-50 text-brand-700"
                : "border-slate-200 text-slate-500 hover:border-brand-400 hover:text-brand-700"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Browse all 50 — sector grouped toggle */}
      <div className="mt-3">
        <button
          onClick={() => setShowAll((v) => !v)}
          className="cursor-pointer flex items-center gap-1.5 text-xs font-semibold text-brand-600 hover:text-brand-700 transition-colors"
        >
          {showAll ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          {showAll ? "Hide" : "Browse all 50 NIFTY stocks"}
        </button>

        {showAll && (
          <div className="mt-3 space-y-3 rounded-xl border border-surface-border bg-slate-50 p-4">
            {Object.entries(grouped).map(([sector, stocks]) => (
              <div key={sector}>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">{sector}</p>
                <div className="flex flex-wrap gap-1.5">
                  {stocks.map((s) => (
                    <button
                      key={s.symbol}
                      onClick={() => { commitTicker(s.symbol); setShowAll(false); }}
                      className={`cursor-pointer rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors ${colorCls(sector, ticker === s.symbol)}`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Train button */}
      <div className="mt-4 flex items-center gap-3 border-t border-surface-border pt-4">
        <button
          onClick={trainClick}
          disabled={loading.train}
          className="flex cursor-pointer items-center gap-2 rounded-xl border border-brand-200 bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-700 transition-colors hover:bg-brand-100 disabled:opacity-50"
        >
          {loading.train
            ? <RefreshCw className="h-4 w-4 animate-spin" />
            : <Zap className="h-4 w-4" />}
          Train LSTM for {currentStock?.label ?? ticker}
        </button>
        <p className="text-xs text-slate-400">Requires training on first use · ~2–5 min</p>
      </div>
    </div>
  );
}
