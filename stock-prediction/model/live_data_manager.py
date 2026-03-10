"""
live_data_manager.py
====================
Dynamic data pipeline that automatically fetches, validates, and
incrementally updates local stock price datasets from Yahoo Finance.

Features
--------
• Incremental updates  – only fetches missing days, not the full history
• Gap detection        – finds and fills gaps in existing CSV data
• Staleness tracking   – reports how fresh each ticker's data is
• Rate-limit handling  – exponential back-off on API errors
• Watchlist support    – track multiple tickers for scheduled refresh
• Thread-safe          – safe for concurrent use from scheduler + API

Author  : Stock-Prediction AI Pipeline
Version : 1.0.0
"""

import os
import time
import json
import threading
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

import pandas as pd
import yfinance as yf

from data_pipeline import normalize_ticker, is_indian_ticker

log = logging.getLogger("live-data")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

DEFAULT_DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
META_FILE         = "data_freshness.json"
MAX_RETRIES       = 3
BASE_BACKOFF_SEC  = 2.0        # exponential: 2, 4, 8 …
RATE_LIMIT_DELAY  = 1.5        # seconds between consecutive API calls
MIN_UPDATE_INTERVAL_SEC = 300  # 5 min — skip if refreshed within this window


# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class TickerFreshness:
    """Tracks the freshness state for a single ticker."""
    ticker:            str
    last_updated:      Optional[str] = None   # ISO timestamp of last successful update
    latest_date:       Optional[str] = None   # Most recent trading date in local CSV
    total_rows:        int           = 0
    gaps_filled:       int           = 0      # Cumulative gaps filled
    last_error:        Optional[str] = None
    consecutive_fails: int           = 0
    update_count:      int           = 0      # Total successful updates

    @property
    def is_stale(self) -> bool:
        """Data is stale if the latest date is > 1 trading day behind today."""
        if not self.latest_date:
            return True
        latest = pd.Timestamp(self.latest_date).date()
        today  = date.today()
        # Skip weekends when checking staleness
        bdays  = pd.bdate_range(latest, today)
        return len(bdays) > 2   # latest + today = 2, so >2 means missing days

    @property
    def days_behind(self) -> int:
        """Number of business days the data is behind."""
        if not self.latest_date:
            return -1
        latest = pd.Timestamp(self.latest_date).date()
        today  = date.today()
        bdays  = pd.bdate_range(latest, today)
        return max(0, len(bdays) - 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_stale"]    = self.is_stale
        d["days_behind"] = self.days_behind
        return d


# ─────────────────────────────────────────────
# LIVE DATA MANAGER
# ─────────────────────────────────────────────

class LiveDataManager:
    """
    Manages incremental updates for stock price CSV files.

    Usage:
        mgr = LiveDataManager("/path/to/data/raw")
        result = mgr.refresh_ticker("RELIANCE.NS")
        status = mgr.get_freshness("RELIANCE.NS")
        report = mgr.refresh_all_watched()
    """

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)

        self._lock        = threading.Lock()
        self._last_call_t = 0.0
        self._freshness:  Dict[str, TickerFreshness] = {}
        self._watchlist:  List[str] = []

        # In-memory freshness cache to avoid re-reading CSVs on every poll
        self._freshness_cache: Optional[Dict] = None
        self._freshness_cache_ts: float = 0.0
        self._FRESHNESS_CACHE_TTL = 60.0  # seconds

        self._meta_path = os.path.join(self.data_dir, META_FILE)
        self._load_meta()

    # ─── Persistence ──────────────────────────

    def _load_meta(self):
        """Load freshness metadata from disk."""
        if os.path.exists(self._meta_path):
            try:
                with open(self._meta_path, "r") as f:
                    data = json.load(f)
                for key, val in data.get("freshness", {}).items():
                    self._freshness[key] = TickerFreshness(**val)
                self._watchlist = data.get("watchlist", [])
                log.info(f"[LiveData] Loaded meta for {len(self._freshness)} tickers, "
                         f"watchlist={len(self._watchlist)}")
            except Exception as e:
                log.warning(f"[LiveData] Failed to load meta: {e}")

    def _save_meta(self):
        """Persist freshness metadata to disk."""
        data = {
            "freshness": {k: asdict(v) for k, v in self._freshness.items()},
            "watchlist":  self._watchlist,
            "saved_at":   datetime.now().isoformat(),
        }
        try:
            with open(self._meta_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            log.warning(f"[LiveData] Failed to save meta: {e}")

    # ─── CSV helpers ─────────────────────────

    def _csv_path(self, ticker: str) -> str:
        safe = ticker.replace("^", "_IDX_")
        return os.path.join(self.data_dir, f"{safe}.csv")

    def _load_csv(self, ticker: str) -> Optional[pd.DataFrame]:
        path = self._csv_path(ticker)
        if not os.path.exists(path):
            return None
        try:
            df = pd.read_csv(path, index_col=0, parse_dates=[0],
                             date_format="%Y-%m-%d")
            # Fallback if date_format didn't produce DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index, format="mixed", errors="coerce")

            # Drop rows with invalid/missing datetime index values
            if df.index.hasnans:
                df = df.loc[~df.index.isna()].copy()

            # Normalize timezone-aware indices to naive for consistency
            if getattr(df.index, "tz", None) is not None:
                df.index = df.index.tz_localize(None)

            df.index.name = "Date"
            return df
        except Exception as e:
            log.warning(f"[LiveData] Failed to read CSV for {ticker}: {e}")
            return None

    def _save_csv(self, ticker: str, df: pd.DataFrame):
        path = self._csv_path(ticker)
        df.to_csv(path)
        log.info(f"[LiveData] Saved {ticker} → {path}  ({len(df)} rows)")

    # ─── Rate limiter ────────────────────────

    def _rate_limit(self):
        """Enforce minimum delay between yfinance API calls."""
        elapsed = time.time() - self._last_call_t
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_call_t = time.time()

    # ─── Core: incremental fetch ─────────────

    def _fetch_incremental(
        self, ticker: str, start: str, end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Download data from yfinance with retries + exponential back-off.
        """
        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._rate_limit()
                df = yf.download(ticker, start=start, end=end, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df
            except Exception as e:
                last_err = e
                wait = BASE_BACKOFF_SEC * (2 ** (attempt - 1))
                log.warning(f"[LiveData] Attempt {attempt}/{MAX_RETRIES} for {ticker} failed: {e}. "
                            f"Retrying in {wait}s …")
                time.sleep(wait)
        raise ConnectionError(
            f"Failed to fetch {ticker} after {MAX_RETRIES} attempts: {last_err}"
        )

    # ─── Public: refresh a single ticker ─────

    def refresh_ticker(
        self,
        ticker: str,
        force: bool = False,
        full_history_start: str = "2006-01-01",
    ) -> Dict:
        """
        Incrementally update local CSV for a ticker.

        Parameters
        ----------
        ticker             : Stock symbol (auto-normalized)
        force              : If True, skip the MIN_UPDATE_INTERVAL check
        full_history_start : Start date if no local data exists

        Returns
        -------
        dict with keys: ticker, action, rows_before, rows_after, new_rows, gaps_filled
        """
        ticker = normalize_ticker(ticker)

        with self._lock:
            fresh = self._freshness.get(ticker, TickerFreshness(ticker=ticker))

            # Skip if recently updated
            if not force and fresh.last_updated:
                last_upd = datetime.fromisoformat(fresh.last_updated)
                if (datetime.now() - last_upd).total_seconds() < MIN_UPDATE_INTERVAL_SEC:
                    return {
                        "ticker": ticker,
                        "action": "skipped",
                        "reason": "recently updated",
                        "freshness": fresh.to_dict(),
                    }

        # Load existing data
        existing_df = self._load_csv(ticker)
        rows_before = len(existing_df) if existing_df is not None else 0

        try:
            if existing_df is not None and len(existing_df) > 0:
                # ── Incremental update ────────────
                last_date = existing_df.index.max()
                # Start 3 days before last date to handle corrections/adjustments
                fetch_start = (last_date - timedelta(days=3)).strftime("%Y-%m-%d")
                log.info(f"[LiveData] Incremental update for {ticker} from {fetch_start}")

                new_df = self._fetch_incremental(ticker, start=fetch_start)
                if new_df.empty:
                    action = "no_new_data"
                    merged_df = existing_df
                else:
                    # Keep OHLCV only from new data
                    ohlcv_cols = ["Open", "High", "Low", "Close", "Volume"]
                    available = [c for c in ohlcv_cols if c in new_df.columns]
                    new_df = new_df[available].copy()
                    new_df.dropna(inplace=True)

                    # Merge: new data overwrites overlapping rows (handles corrections)
                    merged_df = existing_df.copy()
                    merged_df.update(new_df)
                    # Append truly new rows
                    new_only = new_df.loc[~new_df.index.isin(existing_df.index)]
                    if len(new_only) > 0:
                        merged_df = pd.concat([merged_df, new_only])
                    merged_df.sort_index(inplace=True)
                    merged_df = merged_df[~merged_df.index.duplicated(keep="last")]
                    action = "incremental"

                # ── Gap detection & fill ──────────
                gaps_filled = self._fill_gaps(ticker, merged_df)

            else:
                # ── Full history download ─────────
                log.info(f"[LiveData] Full download for {ticker} from {full_history_start}")
                merged_df = self._fetch_incremental(ticker, start=full_history_start)
                if merged_df.empty:
                    raise ValueError(f"No data returned for {ticker}")
                ohlcv_cols = ["Open", "High", "Low", "Close", "Volume"]
                available = [c for c in ohlcv_cols if c in merged_df.columns]
                merged_df = merged_df[available].copy()
                merged_df.dropna(inplace=True)
                action = "full_download"
                gaps_filled = 0

            # Save
            self._save_csv(ticker, merged_df)
            rows_after = len(merged_df)

            # Update freshness
            with self._lock:
                fresh.last_updated      = datetime.now().isoformat()
                fresh.latest_date       = str(merged_df.index.max().date())
                fresh.total_rows        = rows_after
                fresh.gaps_filled      += gaps_filled
                fresh.last_error        = None
                fresh.consecutive_fails = 0
                fresh.update_count     += 1
                self._freshness[ticker] = fresh
                self._save_meta()

            # Invalidate freshness cache since data changed
            self._freshness_cache = None

            result = {
                "ticker":      ticker,
                "action":      action,
                "rows_before": rows_before,
                "rows_after":  rows_after,
                "new_rows":    rows_after - rows_before,
                "gaps_filled": gaps_filled,
                "freshness":   fresh.to_dict(),
            }
            log.info(f"[LiveData] {ticker}: {action}, "
                     f"{rows_before}→{rows_after} rows (+{rows_after - rows_before})")
            return result

        except Exception as e:
            with self._lock:
                fresh.last_error        = str(e)
                fresh.consecutive_fails += 1
                self._freshness[ticker] = fresh
                self._save_meta()

            log.error(f"[LiveData] Failed to refresh {ticker}: {e}")
            return {
                "ticker":  ticker,
                "action":  "error",
                "error":   str(e),
                "retries": fresh.consecutive_fails,
                "freshness": fresh.to_dict(),
            }

    # ─── Gap detection ───────────────────────

    def _fill_gaps(self, ticker: str, df: pd.DataFrame) -> int:
        """
        Detect and fill missing trading-day gaps in the DataFrame.
        Returns the number of gaps filled.
        """
        if len(df) < 2:
            return 0

        # Build business day range
        expected = pd.bdate_range(df.index.min(), df.index.max())
        actual   = df.index.normalize()
        missing  = expected.difference(actual)

        if len(missing) == 0:
            return 0

        # Only attempt to fill if there are reasonable-size gaps (< 30 days)
        # Large gaps (holidays, etc.) are normal — only fill small ones
        gap_groups = []
        current_group = [missing[0]]
        for i in range(1, len(missing)):
            if (missing[i] - missing[i - 1]).days <= 3:
                current_group.append(missing[i])
            else:
                gap_groups.append(current_group)
                current_group = [missing[i]]
        gap_groups.append(current_group)

        filled = 0
        for group in gap_groups:
            # Skip if gap is likely holidays (>5 consecutive days)
            if len(group) > 5:
                continue
            start = (group[0] - timedelta(days=1)).strftime("%Y-%m-%d")
            end   = (group[-1] + timedelta(days=2)).strftime("%Y-%m-%d")
            try:
                self._rate_limit()
                patch = yf.download(ticker, start=start, end=end, progress=False)
                if isinstance(patch.columns, pd.MultiIndex):
                    patch.columns = patch.columns.get_level_values(0)
                if not patch.empty:
                    ohlcv_cols = ["Open", "High", "Low", "Close", "Volume"]
                    available = [c for c in ohlcv_cols if c in patch.columns]
                    patch = patch[available]
                    new_rows = patch.loc[~patch.index.isin(df.index)]
                    if len(new_rows) > 0:
                        df = pd.concat([df, new_rows]).sort_index()
                        filled += len(new_rows)
            except Exception as e:
                log.warning(f"[LiveData] Gap fill failed for {ticker} "
                            f"({group[0].date()}–{group[-1].date()}): {e}")

        return filled

    # ─── Watchlist management ─────────────────

    def add_to_watchlist(self, ticker: str) -> List[str]:
        ticker = normalize_ticker(ticker)
        with self._lock:
            if ticker not in self._watchlist:
                self._watchlist.append(ticker)
                self._save_meta()
        return self._watchlist

    def remove_from_watchlist(self, ticker: str) -> List[str]:
        ticker = normalize_ticker(ticker)
        with self._lock:
            if ticker in self._watchlist:
                self._watchlist.remove(ticker)
                self._save_meta()
        return self._watchlist

    def get_watchlist(self) -> List[str]:
        return list(self._watchlist)

    def set_watchlist(self, tickers: List[str]) -> List[str]:
        self._watchlist = [normalize_ticker(t) for t in tickers]
        with self._lock:
            self._save_meta()
        return self._watchlist

    # ─── Bulk refresh ────────────────────────

    def refresh_all_watched(self, force: bool = False) -> Dict:
        """
        Refresh all tickers in the watchlist.
        Returns a summary dict with results per ticker.
        """
        results = {}
        errors  = []

        for ticker in self._watchlist:
            result = self.refresh_ticker(ticker, force=force)
            results[ticker] = result
            if result.get("action") == "error":
                errors.append(ticker)

        summary = {
            "total":     len(self._watchlist),
            "refreshed": len(results) - len(errors),
            "errors":    errors,
            "timestamp": datetime.now().isoformat(),
            "results":   results,
        }
        log.info(f"[LiveData] Bulk refresh: {summary['refreshed']}/{summary['total']} OK, "
                 f"{len(errors)} errors")
        return summary

    def refresh_all_local(self, force: bool = False) -> Dict:
        """
        Refresh ALL tickers that have a local CSV, not just the watchlist.
        """
        local_tickers = self._discover_local_tickers()
        results = {}
        errors  = []

        for ticker in local_tickers:
            result = self.refresh_ticker(ticker, force=force)
            results[ticker] = result
            if result.get("action") == "error":
                errors.append(ticker)

        return {
            "total":     len(local_tickers),
            "refreshed": len(results) - len(errors),
            "errors":    errors,
            "timestamp": datetime.now().isoformat(),
            "results":   results,
        }

    def _discover_local_tickers(self) -> List[str]:
        """Scan data_dir for existing CSV files and return ticker names."""
        tickers = []
        for fname in os.listdir(self.data_dir):
            if fname.endswith(".csv") and not fname.startswith("."):
                name = fname[:-4]  # remove .csv
                name = name.replace("_IDX_", "^")
                tickers.append(name)
        return sorted(tickers)

    # ─── Freshness queries ────────────────────

    def get_freshness(self, ticker: str) -> Dict:
        """Return freshness info for a single ticker."""
        ticker = normalize_ticker(ticker)

        # If we have metadata, use it
        if ticker in self._freshness:
            return self._freshness[ticker].to_dict()

        # Otherwise inspect CSV on disk
        df = self._load_csv(ticker)
        if df is not None and len(df) > 0:
            fresh = TickerFreshness(
                ticker=ticker,
                latest_date=str(df.index.max().date()),
                total_rows=len(df),
            )
            return fresh.to_dict()

        return TickerFreshness(ticker=ticker).to_dict()

    def get_all_freshness(self) -> Dict[str, Dict]:
        """Return freshness info for all known tickers (cached for 60s)."""
        now = time.time()
        if (self._freshness_cache is not None and
                now - self._freshness_cache_ts < self._FRESHNESS_CACHE_TTL):
            return self._freshness_cache

        # Merge metadata + local CSVs
        all_tickers = set(self._freshness.keys())
        for t in self._discover_local_tickers():
            all_tickers.add(t)

        result = {}
        for ticker in sorted(all_tickers):
            result[ticker] = self.get_freshness(ticker)

        self._freshness_cache = result
        self._freshness_cache_ts = now
        return result

    def get_summary(self) -> Dict:
        """High-level summary of the data pipeline state."""
        all_fresh = self.get_all_freshness()
        stale    = [t for t, f in all_fresh.items() if f.get("is_stale")]
        fresh    = [t for t, f in all_fresh.items() if not f.get("is_stale")]
        total_rows = sum(f.get("total_rows", 0) for f in all_fresh.values())

        return {
            "total_tickers":   len(all_fresh),
            "fresh_count":     len(fresh),
            "stale_count":     len(stale),
            "stale_tickers":   stale,
            "total_rows":      total_rows,
            "watchlist":       self._watchlist,
            "watchlist_count": len(self._watchlist),
            "freshness":       all_fresh,
        }


# ─────────────────────────────────────────────
# MODULE-LEVEL SINGLETON
# ─────────────────────────────────────────────

_manager: Optional[LiveDataManager] = None

def get_manager(data_dir: str = DEFAULT_DATA_DIR) -> LiveDataManager:
    """Get or create the singleton LiveDataManager."""
    global _manager
    if _manager is None:
        _manager = LiveDataManager(data_dir)
    return _manager
