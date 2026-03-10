"""
download_data.py
================
Download 20 years of historical data for key Indian stocks, indices,
and a few US stocks for comparison. Verifies the data pipeline works
correctly with the Indian market support.
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "model"))

from data_pipeline import (
    fetch_stock_data, add_technical_indicators, normalize_ticker,
    is_indian_ticker, get_currency_symbol, INDIAN_STOCKS, INDIAN_INDICES,
    DEFAULT_START_DATE,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")

# ── Tickers to download ──────────────────────────────
# Top 10 Indian stocks
INDIAN_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "ITC.NS", "LT.NS", "BHARTIARTL.NS", "BAJFINANCE.NS",
]

# Indian indices
INDEX_TICKERS = ["^NSEI", "^NSEBANK", "^BSESN"]

# A couple US stocks (for comparison / testing US path still works)
US_TICKERS = ["AAPL", "TSLA"]

ALL_TICKERS = INDIAN_TICKERS + INDEX_TICKERS + US_TICKERS


def main():
    print("=" * 60)
    print("  📥  DOWNLOADING STOCK DATA")
    print(f"  Start date : {DEFAULT_START_DATE}  (20 years)")
    print(f"  Tickers    : {len(ALL_TICKERS)}")
    print("=" * 60)

    success = []
    failed  = []

    for i, ticker in enumerate(ALL_TICKERS, 1):
        sym = get_currency_symbol(ticker)
        market = "🇮🇳 India" if is_indian_ticker(ticker) else "🇺🇸 US"
        print(f"\n[{i}/{len(ALL_TICKERS)}] {ticker}  ({market}, {sym})")
        print("-" * 40)
        try:
            df = fetch_stock_data(ticker, start=DEFAULT_START_DATE, save_dir=DATA_DIR)
            df_feat = add_technical_indicators(df)
            print(f"  ✅  {len(df)} raw rows  →  {len(df_feat)} rows with indicators")
            print(f"  📊  Date range: {df.index[0].strftime('%Y-%m-%d')} → {df.index[-1].strftime('%Y-%m-%d')}")
            latest_close = float(df['Close'].iloc[-1])
            print(f"  💰  Latest close: {sym}{latest_close:.2f}")
            success.append(ticker)
        except Exception as e:
            print(f"  ❌  FAILED: {e}")
            failed.append((ticker, str(e)))

    # ── Summary ───────────────────────────────
    print("\n" + "=" * 60)
    print("  📊  DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"  ✅ Success : {len(success)} / {len(ALL_TICKERS)}")
    for t in success:
        print(f"      • {t}")
    if failed:
        print(f"\n  ❌ Failed  : {len(failed)}")
        for t, err in failed:
            print(f"      • {t}: {err}")

    # List files in data/raw
    print(f"\n  📁 Files in {DATA_DIR}:")
    if os.path.isdir(DATA_DIR):
        for f in sorted(os.listdir(DATA_DIR)):
            size = os.path.getsize(os.path.join(DATA_DIR, f))
            print(f"      {f:30s}  {size/1024:.0f} KB")

    print("\n✅  Data download complete! You can now train a model.")
    print("   Example:  python model/train.py --ticker RELIANCE.NS --epochs 50")


if __name__ == "__main__":
    main()
