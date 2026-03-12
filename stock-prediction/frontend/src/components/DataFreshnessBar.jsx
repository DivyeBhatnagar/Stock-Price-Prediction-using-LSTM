// DataFreshnessBar.jsx — Data freshness status (light theme)

import { useState, useEffect, useCallback } from "react";
import {
  RefreshCw, CheckCircle2, AlertTriangle, Clock, Database,
  Wifi, WifiOff, ChevronDown, ChevronUp, Eye
} from "lucide-react";
import { getDataFreshness, refreshTicker, getSchedulerStatus } from "../utils/api";

function StatusDot({ stale }) {
  return (
    <span className={`inline-block h-2 w-2 rounded-full ${
      stale ? "bg-amber-500 animate-pulse" : "bg-green-500"
    }`} />
  );
}

function timeSince(iso) {
  if (!iso) return "never";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)    return `${Math.floor(diff)}s ago`;
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function DataFreshnessBar({ ticker, onDataRefreshed }) {
  const [summary,   setSummary]   = useState(null);
  const [scheduler, setScheduler] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [expanded,  setExpanded]  = useState(false);
  const [error,     setError]     = useState(null);

  const loadStatus = useCallback(async () => {
    try {
      const [fresh, sched] = await Promise.all([getDataFreshness(), getSchedulerStatus()]);
      setSummary(fresh); setScheduler(sched); setError(null);
    } catch { setError("Could not load data status"); }
  }, []);

  useEffect(() => { loadStatus(); }, [loadStatus]);
  useEffect(() => {
    const id = setInterval(loadStatus, 120_000);
    return () => clearInterval(id);
  }, [loadStatus]);

  const handleRefresh = async (t) => {
    setRefreshing(true); setError(null);
    try {
      await refreshTicker(t || ticker);
      await loadStatus();
      onDataRefreshed?.();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally { setRefreshing(false); }
  };

  const tickerInfo = summary?.freshness?.[ticker];

  return (
    <div className="rounded-xl border border-surface-border bg-surface-card shadow-sm">

      {/* Compact bar */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5 text-xs">

        {/* Scheduler status */}
        <div className="flex items-center gap-1.5">
          {scheduler?.running
            ? <><Wifi className="h-3.5 w-3.5 text-green-500" /><span className="font-medium text-green-600">Auto-sync ON</span></>
            : <><WifiOff className="h-3.5 w-3.5 text-slate-400" /><span className="text-slate-500">Auto-sync off</span></>}
        </div>

        {/* Freshness counts */}
        {summary && (
          <div className="flex items-center gap-3 text-slate-500">
            <span className="flex items-center gap-1">
              <Database className="h-3.5 w-3.5" />{summary.total_tickers} tickers
            </span>
            <span className="flex items-center gap-1 text-green-600 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />{summary.fresh_count} fresh
            </span>
            {summary.stale_count > 0 && (
              <span className="flex items-center gap-1 text-amber-600 font-medium">
                <AlertTriangle className="h-3.5 w-3.5" />{summary.stale_count} stale
              </span>
            )}
          </div>
        )}

        {/* Active ticker freshness */}
        {tickerInfo && (
          <div className="flex items-center gap-2 rounded-lg border border-surface-border bg-surface px-2.5 py-1">
            <StatusDot stale={tickerInfo.is_stale} />
            <span className="font-semibold text-slate-900">{ticker}</span>
            <span className="text-slate-500">
              {tickerInfo.latest_date
                ? <>latest: {tickerInfo.latest_date} · {tickerInfo.total_rows.toLocaleString()} rows</>
                : "no data"}
            </span>
            {tickerInfo.days_behind > 0 && (
              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700 font-semibold">
                {tickerInfo.days_behind}d behind
              </span>
            )}
          </div>
        )}

        {/* Refresh button */}
        <button
          onClick={() => handleRefresh(ticker)}
          disabled={refreshing}
          className="ml-auto flex cursor-pointer items-center gap-1.5 rounded-lg border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-600 transition-colors duration-200 hover:bg-brand-100 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Updating…" : "Refresh"}
        </button>

        {/* Expand toggle */}
        <button onClick={() => setExpanded(!expanded)} className="cursor-pointer text-slate-400 hover:text-slate-600">
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="border-t border-surface-border bg-red-50 px-4 py-2 text-xs font-medium text-red-600">
          {error}
        </div>
      )}

      {/* Expanded panel */}
      {expanded && summary && (
        <div className="border-t border-surface-border bg-slate-50 px-4 py-3">
          {scheduler && (
            <div className="mb-3 flex flex-wrap gap-4 text-xs text-slate-500">
              <span>Mode: <strong className="text-slate-900">{scheduler.config?.mode}</strong></span>
              {scheduler.config?.mode === "interval" && (
                <span>Every: <strong className="text-slate-900">{scheduler.config?.interval_minutes}min</strong></span>
              )}
              {scheduler.next_run && (
                <span>Next run: <strong className="text-slate-900">{new Date(scheduler.next_run).toLocaleTimeString()}</strong></span>
              )}
              {scheduler.last_run && (
                <span>Last run: <strong className="text-slate-900">{timeSince(scheduler.last_run?.timestamp)}</strong>
                  {scheduler.last_run?.refreshed !== undefined && ` (${scheduler.last_run.refreshed}/${scheduler.last_run.total} OK)`}
                </span>
              )}
            </div>
          )}

          {/* Ticker table */}
          <div className="max-h-48 overflow-y-auto rounded-lg border border-surface-border bg-white">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-slate-50">
                <tr className="border-b border-surface-border">
                  {["Ticker","Latest Date","Rows","Updated","Status","Action"].map((h) => (
                    <th key={h} className="px-3 py-1.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border text-slate-700">
                {Object.entries(summary.freshness || {}).map(([t, f]) => (
                  <tr key={t} className="hover:bg-slate-50">
                    <td className="px-3 py-1.5 font-mono font-semibold text-slate-900">{t}</td>
                    <td className="px-3 py-1.5">{f.latest_date || "—"}</td>
                    <td className="px-3 py-1.5 text-right">{f.total_rows?.toLocaleString() || 0}</td>
                    <td className="px-3 py-1.5 text-slate-500">{timeSince(f.last_updated)}</td>
                    <td className="px-3 py-1.5 text-center"><StatusDot stale={f.is_stale} /></td>
                    <td className="px-3 py-1.5 text-center">
                      <button
                        onClick={() => handleRefresh(t)}
                        disabled={refreshing}
                        className="cursor-pointer text-brand-600 hover:text-brand-700 disabled:opacity-40"
                        title={`Refresh ${t}`}
                      >
                        <RefreshCw className="inline h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {summary.watchlist?.length > 0 && (
            <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
              <Eye className="h-3.5 w-3.5" />
              Watchlist: <span className="font-medium text-slate-700">{summary.watchlist.join(", ")}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}