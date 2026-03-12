"""
scripts/download_data.py
========================
Download 10 years of historical OHLCV data for 49 NIFTY companies
from Yahoo Finance and save them to data/stocks/{TICKER}.NS.csv.

Usage
-----
    python scripts/download_data.py
    python scripts/download_data.py --ticker RELIANCE.NS     # single stock
    python scripts/download_data.py --force                  # re-download all

Output
------
    data/stocks/RELIANCE.NS.csv
    data/stocks/TCS.NS.csv
    data/stocks/HDFCBANK.NS.csv
    ... (49 files total)

Author  : Stock-Prediction AI Pipeline
Version : 2.0.0
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta

# ── project root on path ─────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "model"))

import pandas as pd
import yfinance as yf

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from data_pipeline import (
    NIFTY50_TICKERS, NIFTY50_STOCKS,
    add_technical_indicators,
    normalize_ticker,
    DEFAULT_START_DATE,
)

# ── config ───────────────────────────────────
DATA_DIR   = os.path.join(ROOT, "data", "stocks")
LOG_FILE   = os.path.join(ROOT, "data", "download_log.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w"),
    ],
)
log = logging.getLogger("nifty50-download")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _safe_filename(ticker: str) -> str:
    """Convert ticker to a filesystem-safe filename."""
    return ticker.replace("^", "_IDX_").replace("&", "_AND_")


def _ticker_to_csv(ticker: str) -> str:
    return os.path.join(DATA_DIR, f"{_safe_filename(ticker)}.csv")


def _needs_download(ticker: str, force: bool) -> bool:
    path = _ticker_to_csv(ticker)
    if not os.path.exists(path):
        return True
    if force:
        return True
    # Re-download if data is older than 1 day
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if df.empty:
        return True
    latest = df.index.max()
    days_old = (datetime.now() - latest.to_pydatetime()).days
    return days_old > 1


def download_ticker(ticker: str, start: str, force: bool = False) -> dict:
    """
    Download 10 years of OHLCV data for a single NSE ticker.

    Returns a result dict: { ticker, rows, start_date, end_date, status, error }
    """
    path = _ticker_to_csv(ticker)

    if not _needs_download(ticker, force):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return {
            "ticker": ticker, "rows": len(df),
            "start_date": str(df.index.min().date()),
            "end_date":   str(df.index.max().date()),
            "status": "cached",
        }

    try:
        log.info(f"  ⬇  {ticker:20s}  downloading from {start} …")
        df = yf.download(ticker, start=start, progress=False, auto_adjust=False)

        if df.empty:
            raise ValueError("No data returned from Yahoo Finance")

        # Flatten MultiIndex columns (yfinance ≥0.2)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Keep standard OHLCV + Adj Close
        cols = [c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
                if c in df.columns]
        df = df[cols].copy()
        df.dropna(inplace=True)

        os.makedirs(DATA_DIR, exist_ok=True)
        df.to_csv(path)

        result = {
            "ticker":     ticker,
            "rows":       len(df),
            "start_date": str(df.index.min().date()),
            "end_date":   str(df.index.max().date()),
            "status":     "downloaded",
        }
        log.info(f"  ✅  {ticker:20s}  {len(df):5d} rows  "
                 f"[{result['start_date']} → {result['end_date']}]")
        return result

    except Exception as e:
        log.error(f"  ❌  {ticker:20s}  FAILED: {e}")
        return {"ticker": ticker, "rows": 0, "status": "failed", "error": str(e)}


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download 10 years of NSE stock data for all NIFTY 50 companies."
    )
    parser.add_argument("--ticker", default=None,
                        help="Download a single ticker (e.g. RELIANCE.NS)")
    parser.add_argument("--force",  action="store_true",
                        help="Force re-download even if data already exists")
    parser.add_argument("--start",  default=DEFAULT_START_DATE,
                        help=f"Start date (default: {DEFAULT_START_DATE})")
    args = parser.parse_args()

    tickers = [normalize_ticker(args.ticker)] if args.ticker else NIFTY50_TICKERS

    print("=" * 65)
    print("   📥  NIFTY 50 — HISTORICAL DATA DOWNLOAD")
    print(f"   Start date : {args.start}  (10 years)")
    print(f"   Tickers    : {len(tickers)}")
    print(f"   Output dir : {DATA_DIR}")
    print("=" * 65)

    success, cached, failed = [], [], []

    iterable = tqdm(tickers, desc="Downloading", unit="stock") if HAS_TQDM else tickers

    for ticker in iterable:
        if HAS_TQDM:
            iterable.set_postfix({"stock": ticker})          # type: ignore
        result = download_ticker(ticker, start=args.start, force=args.force)

        if result["status"] == "downloaded":
            success.append(result)
        elif result["status"] == "cached":
            cached.append(result)
        else:
            failed.append(result)

    # ── Summary ────────────────────────────────
    print("\n" + "=" * 65)
    print("   📊  DOWNLOAD SUMMARY")
    print("=" * 65)
    total = len(tickers)
    print(f"   ✅ Downloaded  : {len(success):3d} / {total}")
    print(f"   📦 Cached      : {len(cached):3d} / {total}")
    print(f"   ❌ Failed      : {len(failed):3d} / {total}")

    if failed:
        print("\n   Failed tickers:")
        for r in failed:
            print(f"      • {r['ticker']:20s}  {r.get('error', 'unknown error')}")

    # ── File listing ────────────────────────────
    all_csvs = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    total_size_mb = sum(
        os.path.getsize(os.path.join(DATA_DIR, f))
        for f in all_csvs
    ) / 1_048_576

    print(f"\n   📁 {len(all_csvs)} CSV files in {DATA_DIR}")
    print(f"   💾 Total size : {total_size_mb:.1f} MB")
    print(f"   📋 Log saved  → {LOG_FILE}")

    return len(failed) == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
