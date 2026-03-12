"""
scripts/train_all_stocks.py
===========================
Automated pipeline that downloads, preprocesses, trains an LSTM model,
and saves results for ALL 50 NIFTY companies in one shot.

Usage
-----
    # Train all 50 stocks
    python scripts/train_all_stocks.py

    # Train a single stock
    python scripts/train_all_stocks.py --ticker RELIANCE.NS

    # Resume (skip already-trained tickers)
    python scripts/train_all_stocks.py --skip-trained

    # Custom hyperparameters
    python scripts/train_all_stocks.py --epochs 30 --batch 32 --window 60

Pipeline per stock
------------------
    1. download_data()   → data/stocks/{TICKER}.NS.csv
    2. preprocess_data() → features + scaling + sequences
    3. train_model()     → LSTM with attention
    4. evaluate()        → RMSE, MAE, MAPE, R²
    5. save_model()      → backend/models/{TICKER}/

Author  : Stock-Prediction AI Pipeline
Version : 2.0.0
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime

# ── project root on path ─────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "model"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from data_pipeline import NIFTY50_TICKERS, NIFTY50_STOCKS, normalize_ticker, DEFAULT_START_DATE

# ── paths ────────────────────────────────────
DATA_DIR   = os.path.join(ROOT, "data",    "stocks")
MODEL_DIR  = os.path.join(ROOT, "backend", "models")
LOG_FILE   = os.path.join(ROOT, "data",    "training_log.json")

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s  %(message)s",
    handlers= [logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("nifty50-trainer")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _model_exists(ticker: str) -> bool:
    config_path = os.path.join(MODEL_DIR, ticker, "config.json")
    return os.path.exists(config_path)


def _print_banner(title: str, width: int = 65):
    log.info("=" * width)
    log.info(f"  {title}")
    log.info("=" * width)


# ─────────────────────────────────────────────
# SINGLE STOCK PIPELINE
# ─────────────────────────────────────────────

def train_stock(ticker: str, args) -> dict:
    """
    Run the full pipeline for one ticker:
        download → preprocess → train → evaluate → save

    Returns a result dict with metrics and timing.
    """
    from train import train as lstm_train
    from download_data import download_ticker

    t_start = time.time()
    bare    = ticker.replace(".NS", "")
    name    = NIFTY50_STOCKS.get(bare, {}).get("name", ticker)
    sector  = NIFTY50_STOCKS.get(bare, {}).get("sector", "—")

    log.info(f"\n{'─'*65}")
    log.info(f"  Stock : {ticker}  |  {name}  |  {sector}")
    log.info(f"{'─'*65}")

    # ── Step 1: Download data ─────────────────
    log.info(f"  [1/3] Downloading {ticker} …")
    dl_result = download_ticker(ticker, start=DEFAULT_START_DATE, force=args.force_download)
    if dl_result["status"] == "failed":
        return {
            "ticker": ticker, "name": name, "status": "failed",
            "error":  dl_result.get("error", "download failed"),
            "duration_sec": round(time.time() - t_start, 1),
        }

    log.info(f"  [1/3] ✅ {dl_result['rows']} rows  "
             f"[{dl_result.get('start_date', '?')} → {dl_result.get('end_date', '?')}]")

    # ── Step 2 + 3: Preprocess + Train ────────
    log.info(f"  [2/3] Building pipeline + training LSTM …")

    class _Args:
        ticker         = None
        start          = DEFAULT_START_DATE
        window         = args.window
        horizon        = args.horizon
        epochs         = args.epochs
        batch          = args.batch
        lr             = args.lr
        dropout        = args.dropout
        attention      = True
        bidir          = False
        split          = 0.80
        output         = MODEL_DIR

    _Args.ticker = ticker

    try:
        result = lstm_train(_Args())
    except Exception as e:
        log.error(f"  [2/3] ❌ Training failed for {ticker}: {e}")
        return {
            "ticker": ticker, "name": name, "status": "failed",
            "error":  str(e),
            "duration_sec": round(time.time() - t_start, 1),
        }

    metrics  = result.get("metrics", {})
    duration = round(time.time() - t_start, 1)

    log.info(f"  [3/3] ✅ Trained in {duration}s")
    log.info(f"         RMSE={metrics.get('rmse','?'):.4f}  "
             f"MAE={metrics.get('mae','?'):.4f}  "
             f"R²={metrics.get('r2','?'):.4f}  "
             f"Dir.Acc={metrics.get('directional_accuracy','?'):.4f}")

    return {
        "ticker":       ticker,
        "name":         name,
        "sector":       sector,
        "status":       "success",
        "metrics":      metrics,
        "rows":         dl_result["rows"],
        "duration_sec": duration,
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Train LSTM models for all 50 NIFTY companies."
    )
    parser.add_argument("--ticker",        default=None,
                        help="Train a single ticker (e.g. RELIANCE.NS)")
    parser.add_argument("--skip-trained",  action="store_true",
                        help="Skip tickers that already have a trained model")
    parser.add_argument("--force-download",action="store_true",
                        help="Re-download data even if already cached")
    parser.add_argument("--window",        type=int,   default=60,
                        help="Look-back window in trading days (default: 60)")
    parser.add_argument("--horizon",       type=int,   default=1,
                        help="Forecast horizon in days (default: 1)")
    parser.add_argument("--epochs",        type=int,   default=50,
                        help="Max training epochs (default: 50, early-stops)")
    parser.add_argument("--batch",         type=int,   default=32,
                        help="Batch size (default: 32)")
    parser.add_argument("--lr",            type=float, default=1e-3,
                        help="Learning rate (default: 0.001)")
    parser.add_argument("--dropout",       type=float, default=0.2,
                        help="Dropout rate (default: 0.2)")
    args = parser.parse_args()

    # Build ticker list
    if args.ticker:
        tickers = [normalize_ticker(args.ticker)]
    else:
        tickers = NIFTY50_TICKERS

    if args.skip_trained:
        before = len(tickers)
        tickers = [t for t in tickers if not _model_exists(t)]
        skipped = before - len(tickers)
        if skipped:
            log.info(f"  Skipping {skipped} already-trained tickers.")

    _print_banner(f"NIFTY 50 — LSTM TRAINING PIPELINE  ({len(tickers)} stocks)")
    log.info(f"  Config: window={args.window}  horizon={args.horizon}  "
             f"epochs={args.epochs}  batch={args.batch}  lr={args.lr}")
    log.info(f"  Data  : {DEFAULT_START_DATE} → today  (10 years)")
    log.info(f"  Models: {MODEL_DIR}")

    results   = []
    t_overall = time.time()

    iterable = tqdm(tickers, desc="Training NIFTY 50", unit="stock") if HAS_TQDM else tickers

    for ticker in iterable:
        if HAS_TQDM:
            iterable.set_postfix({"stock": ticker})          # type: ignore
        result = train_stock(ticker, args)
        results.append(result)

    # ── Summary ────────────────────────────────
    elapsed   = round(time.time() - t_overall, 1)
    successes = [r for r in results if r["status"] == "success"]
    failures  = [r for r in results if r["status"] == "failed"]

    _print_banner("TRAINING SUMMARY")
    log.info(f"  Total stocks   : {len(results)}")
    log.info(f"  ✅ Successful  : {len(successes)}")
    log.info(f"  ❌ Failed      : {len(failures)}")
    log.info(f"  ⏱  Total time  : {elapsed:.0f}s  ({elapsed/60:.1f} min)")

    if successes:
        avg_rmse = sum(r["metrics"].get("rmse", 0) for r in successes) / len(successes)
        avg_r2   = sum(r["metrics"].get("r2",   0) for r in successes) / len(successes)
        avg_da   = sum(r["metrics"].get("directional_accuracy", 0) for r in successes) / len(successes)
        log.info(f"\n  Average metrics across all trained stocks:")
        log.info(f"    RMSE : {avg_rmse:.4f}")
        log.info(f"    R²   : {avg_r2:.4f}")
        log.info(f"    Dir. Accuracy : {avg_da:.4f}")

    if failures:
        log.warning(f"\n  Failed stocks:")
        for r in failures:
            log.warning(f"    • {r['ticker']:20s}  {r.get('error', 'unknown')}")

    # ── Save log ────────────────────────────────
    log_data = {
        "timestamp":      datetime.now().isoformat(),
        "total":          len(results),
        "success_count":  len(successes),
        "failure_count":  len(failures),
        "elapsed_sec":    elapsed,
        "config": {
            "window":  args.window,
            "horizon": args.horizon,
            "epochs":  args.epochs,
            "batch":   args.batch,
        },
        "results": results,
    }
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=2, default=str)
    log.info(f"\n  📋 Full log → {LOG_FILE}")

    return len(failures) == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
