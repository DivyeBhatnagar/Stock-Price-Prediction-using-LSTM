"""
scripts/preprocess.py
=====================
Preprocessing module for NIFTY 50 stock data.

Provides a standalone entry point to verify preprocessing works for a given
ticker without running the full training pipeline. Also serves as a reference
for the preprocessing steps applied to all 50 NIFTY stocks.

Usage
-----
    python scripts/preprocess.py
    python scripts/preprocess.py --ticker TCS.NS

Steps
-----
    1. Load raw OHLCV CSV from data/stocks/
    2. Add technical indicators (SMA, EMA, RSI, MACD, BB, ATR)
    3. MinMax normalize all features
    4. Create sliding windows (60 timesteps × 16 features)
    5. Train/test split (80/20, chronological)

Author  : Stock-Prediction AI Pipeline
Version : 2.0.0
"""

import os
import sys
import argparse

# ── project root on path ─────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "model"))

from data_pipeline import (
    load_raw_data, add_technical_indicators,
    normalize_data, create_sequences, split_data,
    FEATURE_COLS, CLOSE_COL_IDX,
    normalize_ticker, DEFAULT_START_DATE,
    NIFTY50_TICKERS,
)


def preprocess_ticker(
    ticker: str,
    window_size: int = 60,
    forecast_horizon: int = 1,
    split_ratio: float = 0.80,
    data_dir: str = None,
    verbose: bool = True,
) -> dict:
    """
    Run the full preprocessing pipeline for a single NIFTY 50 stock.

    Parameters
    ----------
    ticker           : Yahoo Finance NSE ticker (e.g. "RELIANCE.NS")
    window_size      : Look-back window in trading days
    forecast_horizon : Days ahead to predict
    split_ratio      : Fraction used for training (rest for testing)
    data_dir         : Directory with raw CSVs (defaults to data/stocks/)
    verbose          : Print progress steps

    Returns
    -------
    dict with keys:
        X_train, X_test, y_train, y_test,
        scaler, df_raw, df_featured, feature_cols
    """
    if data_dir is None:
        data_dir = os.path.join(ROOT, "data", "stocks")

    ticker = normalize_ticker(ticker)

    if verbose:
        print(f"\n{'─'*55}")
        print(f"  Preprocessing: {ticker}")
        print(f"{'─'*55}")

    # 1. Load raw data
    df_raw = load_raw_data(ticker, data_dir=data_dir)
    if verbose:
        print(f"  [1] Raw data:  {len(df_raw)} rows  "
              f"[{df_raw.index.min().date()} → {df_raw.index.max().date()}]")

    # 2. Technical indicators
    df_feat = add_technical_indicators(df_raw)
    if verbose:
        print(f"  [2] Features:  {len(df_feat)} rows  ×  {len(FEATURE_COLS)} features")
        print(f"      Columns: {', '.join(FEATURE_COLS)}")

    # 3. Normalize
    scaled, scaler = normalize_data(df_feat, FEATURE_COLS)
    if verbose:
        print(f"  [3] Scaled:    min={scaled.min():.4f}  max={scaled.max():.4f}")

    # 4. Sliding windows
    X, y = create_sequences(scaled, window_size, CLOSE_COL_IDX, forecast_horizon)
    if verbose:
        print(f"  [4] Windows:   X={X.shape}  y={y.shape}")

    # 5. Train/test split
    X_train, X_test, y_train, y_test = split_data(X, y, split_ratio)
    if verbose:
        print(f"  [5] Split:     train={X_train.shape[0]}  test={X_test.shape[0]}")

    return {
        "X_train":      X_train,
        "X_test":       X_test,
        "y_train":      y_train,
        "y_test":       y_test,
        "scaler":       scaler,
        "df_raw":       df_raw,
        "df_featured":  df_feat,
        "feature_cols": FEATURE_COLS,
        "close_col_idx": CLOSE_COL_IDX,
    }


def verify_all_stocks(data_dir: str = None) -> dict:
    """
    Verify preprocessing works for all 50 NIFTY stocks that have been downloaded.

    Returns a summary dict with success/failure counts.
    """
    if data_dir is None:
        data_dir = os.path.join(ROOT, "data", "stocks")

    success, failed = [], []

    for ticker in NIFTY50_TICKERS:
        csv_path = os.path.join(
            data_dir,
            ticker.replace("^", "_IDX_").replace("&", "_AND_") + ".csv"
        )
        if not os.path.exists(csv_path):
            print(f"  ⚠  {ticker:20s} CSV not found — run download_data.py first")
            failed.append({"ticker": ticker, "error": "no CSV"})
            continue
        try:
            result = preprocess_ticker(ticker, data_dir=data_dir, verbose=False)
            rows = result["df_raw"].shape[0]
            print(f"  ✅  {ticker:20s}  {rows:5d} rows  "
                  f"X_train={result['X_train'].shape}  "
                  f"X_test={result['X_test'].shape}")
            success.append(ticker)
        except Exception as e:
            print(f"  ❌  {ticker:20s}  ERROR: {e}")
            failed.append({"ticker": ticker, "error": str(e)})

    print(f"\n  Results: ✅ {len(success)} / {len(NIFTY50_TICKERS)}  ❌ {len(failed)}")
    return {"success": success, "failed": failed}


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Preprocess NIFTY 50 stock data and verify pipeline."
    )
    parser.add_argument("--ticker",  default=None,
                        help="Single ticker to preprocess (default: all downloaded)")
    parser.add_argument("--window",  type=int, default=60,
                        help="Look-back window (default: 60)")
    parser.add_argument("--horizon", type=int, default=1,
                        help="Forecast horizon (default: 1)")
    args = parser.parse_args()

    if args.ticker:
        result = preprocess_ticker(
            normalize_ticker(args.ticker),
            window_size      = args.window,
            forecast_horizon = args.horizon,
            verbose          = True,
        )
        print("\n  ✅  Preprocessing complete.")
        print(f"      X_train : {result['X_train'].shape}")
        print(f"      X_test  : {result['X_test'].shape}")
    else:
        print("\n  Verifying preprocessing for all downloaded NIFTY 50 stocks …\n")
        verify_all_stocks()


if __name__ == "__main__":
    main()
