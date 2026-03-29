"""
data_pipeline.py
================
Handles all data acquisition, preprocessing, normalization, and
time-series windowing for the LSTM stock-prediction system.

Supports both US and **Indian stock market** tickers (NSE / BSE).
  - NSE tickers use the `.NS` suffix  (e.g. RELIANCE.NS)
  - BSE tickers use the `.BO` suffix  (e.g. RELIANCE.BO)
  - Indian indices: ^NSEI (NIFTY 50), ^NSEBANK (BANK NIFTY), ^BSESN (SENSEX)

Author  : Stock-Prediction AI Pipeline
Version : 2.0.0
"""

import os
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, Optional
from datetime import datetime, timedelta
import joblib


# ─────────────────────────────────────────────
# INDIAN MARKET CONSTANTS
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# NIFTY 50 UNIVERSE  (all 50 NSE large-caps)
# ─────────────────────────────────────────────

NIFTY50_STOCKS = {
    # bare symbol → { name, sector }   (Yahoo Finance: append .NS for each)
    "ADANIENT":   {"name": "Adani Enterprises",              "sector": "Metals & Mining"},
    "ADANIPORTS": {"name": "Adani Ports and SEZ",            "sector": "Infrastructure"},
    "APOLLOHOSP": {"name": "Apollo Hospitals",               "sector": "Healthcare"},
    "ASIANPAINT": {"name": "Asian Paints",                   "sector": "Paints / Consumer"},
    "AXISBANK":   {"name": "Axis Bank",                      "sector": "Banking"},
    "BAJAJ-AUTO": {"name": "Bajaj Auto",                     "sector": "Automobile"},
    "BAJFINANCE": {"name": "Bajaj Finance",                  "sector": "Finance / NBFC"},
    "BAJAJFINSV": {"name": "Bajaj Finserv",                  "sector": "Finance / Insurance"},
    "BHARTIARTL": {"name": "Bharti Airtel",                  "sector": "Telecom"},
    "BRITANNIA":  {"name": "Britannia Industries",           "sector": "FMCG"},
    "CIPLA":      {"name": "Cipla",                          "sector": "Pharma"},
    "COALINDIA":  {"name": "Coal India",                     "sector": "Energy / Mining"},
    "DIVISLAB":   {"name": "Divi's Laboratories",            "sector": "Pharma"},
    "DRREDDY":    {"name": "Dr. Reddy's Laboratories",       "sector": "Pharma"},
    "EICHERMOT":  {"name": "Eicher Motors",                  "sector": "Automobile"},
    "GRASIM":     {"name": "Grasim Industries",              "sector": "Cement / Diversified"},
    "HCLTECH":    {"name": "HCL Technologies",               "sector": "IT Services"},
    "HDFCBANK":   {"name": "HDFC Bank",                      "sector": "Banking"},
    "HDFCLIFE":   {"name": "HDFC Life Insurance",            "sector": "Insurance"},
    "HEROMOTOCO": {"name": "Hero MotoCorp",                  "sector": "Automobile"},
    "HINDALCO":   {"name": "Hindalco Industries",            "sector": "Metals / Aluminium"},
    "HINDUNILVR": {"name": "Hindustan Unilever",             "sector": "FMCG"},
    "ICICIBANK":  {"name": "ICICI Bank",                     "sector": "Banking"},
    "ITC":        {"name": "ITC",                            "sector": "FMCG / Conglomerate"},
    "INDUSINDBK": {"name": "IndusInd Bank",                  "sector": "Banking"},
    "INFY":       {"name": "Infosys",                        "sector": "IT Services"},
    "JSWSTEEL":   {"name": "JSW Steel",                      "sector": "Metals / Steel"},
    "KOTAKBANK":  {"name": "Kotak Mahindra Bank",            "sector": "Banking"},
    "LT":         {"name": "Larsen & Toubro",                "sector": "Infrastructure"},
    "LTIM":       {"name": "LTIMindtree",                    "sector": "IT Services"},
    "M&M":        {"name": "Mahindra & Mahindra",            "sector": "Automobile"},
    "MARUTI":     {"name": "Maruti Suzuki",                  "sector": "Automobile"},
    "NESTLEIND":  {"name": "Nestle India",                   "sector": "FMCG"},
    "NTPC":       {"name": "NTPC",                           "sector": "Power / Utilities"},
    "ONGC":       {"name": "ONGC",                           "sector": "Energy / Oil & Gas"},
    "POWERGRID":  {"name": "Power Grid Corporation",         "sector": "Power / Utilities"},
    "RELIANCE":   {"name": "Reliance Industries",            "sector": "Energy / Conglomerate"},
    "SBILIFE":    {"name": "SBI Life Insurance",             "sector": "Insurance"},
    "SHRIRAMFIN": {"name": "Shriram Finance",                "sector": "Finance / NBFC"},
    "SBIN":       {"name": "State Bank of India",            "sector": "Banking"},
    "SUNPHARMA":  {"name": "Sun Pharmaceutical Industries",  "sector": "Pharma"},
    "TCS":        {"name": "Tata Consultancy Services",      "sector": "IT Services"},
    "TATACONSUM": {"name": "Tata Consumer Products",         "sector": "FMCG"},
    "TATASTEEL":  {"name": "Tata Steel",                     "sector": "Metals / Steel"},
    "TECHM":      {"name": "Tech Mahindra",                  "sector": "IT Services"},
    "TITAN":      {"name": "Titan Company",                  "sector": "Consumer Goods"},
    "ULTRACEMCO": {"name": "UltraTech Cement",               "sector": "Cement"},
    "WIPRO":      {"name": "Wipro",                          "sector": "IT Services"},
    "BPCL":       {"name": "Bharat Petroleum",               "sector": "Energy / Oil & Gas"},
}

# Backward-compatible alias
INDIAN_STOCKS = NIFTY50_STOCKS

# Ordered list of all 50 NSE tickers in Yahoo Finance format
NIFTY50_TICKERS = [f"{bare}.NS" for bare in NIFTY50_STOCKS.keys()]

INDIAN_INDICES = {
    "^NSEI":     {"name": "NIFTY 50",    "description": "NSE benchmark (50 large-caps)"},
    "^NSEBANK":  {"name": "BANK NIFTY",  "description": "NSE banking sector index"},
    "^BSESN":    {"name": "SENSEX",      "description": "BSE benchmark (30 stocks)"},
}

# Build a set of bare NIFTY 50 ticker names for fast lookup
_INDIAN_BARE_SET = set(NIFTY50_STOCKS.keys())

# Default: 10 years of historical data for NIFTY 50
DEFAULT_START_DATE = (datetime.now() - timedelta(days=10 * 365)).strftime("%Y-%m-%d")


# ─────────────────────────────────────────────
# TICKER NORMALISATION (NSE / BSE)
# ─────────────────────────────────────────────

def normalize_ticker(ticker: str) -> str:
    """
    Auto-convert bare Indian stock names to NSE Yahoo Finance format.

    Rules:
      • Already has `.NS` / `.BO` suffix or `^` prefix → keep as-is
      • Known Indian bare symbol (e.g. "RELIANCE")     → append `.NS`
      • Otherwise (e.g. "AAPL", "TSLA")                → keep as-is (US market)
    """
    t = ticker.strip().upper()
    # Already formatted
    if t.endswith(".NS") or t.endswith(".BO") or t.startswith("^"):
        return t
    # Known Indian stock
    if t in _INDIAN_BARE_SET:
        return f"{t}.NS"
    return t


def is_indian_ticker(ticker: str) -> bool:
    """Check whether a ticker belongs to the Indian market."""
    t = ticker.strip().upper()
    return (
        t.endswith(".NS") or
        t.endswith(".BO") or
        t in ("^NSEI", "^NSEBANK", "^BSESN") or
        t in _INDIAN_BARE_SET
    )


def get_currency(ticker: str) -> str:
    """Return 'INR' for Indian tickers, 'USD' otherwise."""
    return "INR" if is_indian_ticker(ticker) else "USD"


def get_currency_symbol(ticker: str) -> str:
    """Return '₹' for Indian tickers, '$' otherwise."""
    return "₹" if is_indian_ticker(ticker) else "$"


# ─────────────────────────────────────────────
# 1. DATA FETCHING
# ─────────────────────────────────────────────

def fetch_stock_data(
    ticker: str,
    start: str = None,
    end: Optional[str] = None,
    save_dir: str = "../data/stocks",
    incremental: bool = True,
) -> pd.DataFrame:
    """
    Download historical OHLCV data from Yahoo Finance.

    When ``incremental=True`` (default), uses LiveDataManager to perform
    smart incremental updates — only fetching missing days rather than
    re-downloading the entire history each time.

    Parameters
    ----------
    ticker      : Stock symbol — bare Indian names auto-converted (e.g. "RELIANCE" → "RELIANCE.NS")
    start       : Start date "YYYY-MM-DD"; defaults to 20 years ago
    end         : End date string; defaults to today
    save_dir    : Directory to cache raw CSV
    incremental : Use LiveDataManager for smart incremental updates (default True)

    Returns
    -------
    DataFrame with columns: Open, High, Low, Close, Volume
    """
    ticker = normalize_ticker(ticker)
    if start is None:
        start = DEFAULT_START_DATE

    # ── Incremental path (preferred) ─────────────
    if incremental:
        try:
            from live_data_manager import get_manager
            mgr = get_manager(os.path.abspath(save_dir))
            result = mgr.refresh_ticker(ticker, force=False, full_history_start=start)

            # Load the updated CSV
            safe_name = ticker.replace("^", "_IDX_").replace("&", "_AND_")
            path = os.path.join(save_dir, f"{safe_name}.csv")
            if os.path.exists(path):
                df = pd.read_csv(path, index_col=0, parse_dates=True)
                if not df.empty:
                    action = result.get("action", "unknown")
                    print(f"[DataPipeline] '{ticker}' via LiveDataManager ({action}): "
                          f"{len(df)} rows, latest={df.index.max().date()}")
                    return df
        except Exception as e:
            print(f"[DataPipeline] LiveDataManager fallback for '{ticker}': {e}")
            # Fall through to legacy path

    # ── Legacy full-download path ────────────────
    print(f"[DataPipeline] Fetching '{ticker}' from {start} …")
    df = yf.download(ticker, start=start, end=end, progress=False)

    if df.empty:
        raise ValueError(f"No data returned for ticker '{ticker}'. "
                         "Check the symbol or date range.")

    # yfinance ≥0.2 returns MultiIndex columns like ('Open', 'RELIANCE.NS')
    # Flatten them to simple column names: 'Open', 'High', …
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Keep only OHLCV columns
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)

    # Persist raw data
    os.makedirs(save_dir, exist_ok=True)
    safe_name = ticker.replace("^", "_IDX_").replace("&", "_AND_")   # Safe filenames
    path = os.path.join(save_dir, f"{safe_name}.csv")
    df.to_csv(path)
    print(f"[DataPipeline] Saved raw data → {path}  ({len(df)} rows)")
    return df


def load_raw_data(ticker: str, data_dir: str = "../data/stocks") -> pd.DataFrame:
    """Load previously cached raw CSV for a ticker."""
    ticker = normalize_ticker(ticker)
    safe_name = ticker.replace("^", "_IDX_").replace("&", "_AND_")
    path = os.path.join(data_dir, f"{safe_name}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No cached data for {ticker}. "
                                "Call fetch_stock_data first.")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df


# ─────────────────────────────────────────────
# 2. FEATURE ENGINEERING
# ─────────────────────────────────────────────

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich OHLCV data with technical indicators:
        - SMA  : Simple Moving Averages (20, 50 days)
        - EMA  : Exponential Moving Average (20 days)
        - RSI  : Relative Strength Index (14 days)
        - MACD : Moving Average Convergence Divergence
        - BB   : Bollinger Bands (20-day, 2σ)
        - ATR  : Average True Range (14 days)

    These features give the LSTM richer market context.
    """
    df = df.copy()

    # ── Moving Averages ──────────────────────
    df["SMA_20"] = df["Close"].rolling(20).mean()
    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()

    # ── RSI ──────────────────────────────────
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / (loss + 1e-10)
    df["RSI"] = 100 - (100 / (1 + rs))

    # ── MACD ─────────────────────────────────
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # ── Bollinger Bands ───────────────────────
    sma20 = df["Close"].rolling(20).mean()
    std20 = df["Close"].rolling(20).std()
    df["BB_Upper"] = sma20 + 2 * std20
    df["BB_Lower"] = sma20 - 2 * std20
    df["BB_Width"] = df["BB_Upper"] - df["BB_Lower"]

    # ── ATR ───────────────────────────────────
    hl   = df["High"] - df["Low"]
    hc   = (df["High"] - df["Close"].shift()).abs()
    lc   = (df["Low"]  - df["Close"].shift()).abs()
    df["ATR"] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()

    # ── Daily Returns ─────────────────────────
    df["Return"] = df["Close"].pct_change()

    # ── Volume Indicators ─────────────────────
    df["Vol_SMA20"] = df["Volume"].rolling(20).mean()
    df["Vol_Ratio"] = df["Volume"] / (df["Vol_SMA20"] + 1e-10)

    # ── Stochastic Oscillator ─────────────────
    low14          = df["Low"].rolling(14).min()
    high14         = df["High"].rolling(14).max()
    df["STOCH_K"]  = 100 * (df["Close"] - low14) / (high14 - low14 + 1e-10)
    df["STOCH_D"]  = df["STOCH_K"].rolling(3).mean()

    # ── Williams %R ───────────────────────────
    df["Williams_R"] = -100 * (high14 - df["Close"]) / (high14 - low14 + 1e-10)

    # ── CCI (Commodity Channel Index) ─────────
    tp             = (df["High"] + df["Low"] + df["Close"]) / 3
    df["CCI"]      = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std() + 1e-10)

    # ── Price vs Moving Average Ratios ────────
    df["Price_SMA20_Ratio"] = df["Close"] / (df["SMA_20"] + 1e-10) - 1
    df["Price_SMA50_Ratio"] = df["Close"] / (df["SMA_50"] + 1e-10) - 1

    # ── Log Return ────────────────────────────
    df["Log_Return"] = np.log(df["Close"] / df["Close"].shift(1).clip(lower=1e-10))

    # ── OBV (On-Balance Volume) ───────────────
    df["OBV"] = (np.sign(df["Close"].diff().fillna(0)) * df["Volume"]).cumsum()

    # ── ADX (Average Directional Index) ───────
    _tr   = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    _atr  = _tr.ewm(alpha=1/14, adjust=False).mean()
    _dm_p = np.where(
        (df["High"] - df["High"].shift(1)) > (df["Low"].shift(1) - df["Low"]),
        np.maximum(df["High"] - df["High"].shift(1), 0), 0)
    _dm_m = np.where(
        (df["Low"].shift(1) - df["Low"]) > (df["High"] - df["High"].shift(1)),
        np.maximum(df["Low"].shift(1) - df["Low"], 0), 0)
    _di_p = 100 * pd.Series(_dm_p, index=df.index).ewm(alpha=1/14, adjust=False).mean() / (_atr + 1e-10)
    _di_m = 100 * pd.Series(_dm_m, index=df.index).ewm(alpha=1/14, adjust=False).mean() / (_atr + 1e-10)
    _dx   = 100 * (_di_p - _di_m).abs() / (_di_p + _di_m + 1e-10)
    df["ADX"] = _dx.ewm(alpha=1/14, adjust=False).mean()

    df.dropna(inplace=True)
    return df


# ─────────────────────────────────────────────
# 3. NORMALIZATION
# ─────────────────────────────────────────────

def normalize_data(
    df: pd.DataFrame,
    feature_cols: list,
    scaler_path: Optional[str] = None
) -> Tuple[np.ndarray, MinMaxScaler]:
    """
    Apply Min-Max scaling (0–1) to selected feature columns.

    Parameters
    ----------
    df           : DataFrame with feature columns
    feature_cols : List of column names to scale
    scaler_path  : If provided, load an existing scaler from disk

    Returns
    -------
    scaled_array : ndarray of shape (n_samples, n_features)
    scaler       : Fitted MinMaxScaler (needed for inverse_transform)
    """
    data = df[feature_cols].values

    if scaler_path and os.path.exists(scaler_path):
        scaler = joblib.load(scaler_path)
        scaled = scaler.transform(data)
        print(f"[DataPipeline] Loaded existing scaler from {scaler_path}")
    else:
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled = scaler.fit_transform(data)
        if scaler_path:
            os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
            joblib.dump(scaler, scaler_path)
            print(f"[DataPipeline] Scaler saved → {scaler_path}")

    return scaled, scaler


def inverse_transform_close(
    scaler: MinMaxScaler,
    values: np.ndarray,
    close_col_idx: int,
    n_features: int
) -> np.ndarray:
    """
    Inverse-transform ONLY the Close column from scaled predictions.

    Because we scaled multiple features together, we must reconstruct a
    dummy full-feature array before calling inverse_transform.
    """
    dummy = np.zeros((len(values), n_features))
    dummy[:, close_col_idx] = values.ravel()
    return scaler.inverse_transform(dummy)[:, close_col_idx]


# ─────────────────────────────────────────────
# 4. TIME-SERIES WINDOW CREATION
# ─────────────────────────────────────────────

def create_sequences(
    data: np.ndarray,
    window_size: int = 60,
    target_col_idx: int = 3,        # 'Close' index in feature_cols
    forecast_horizon: int = 1
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Slide a rolling window over the scaled data to build (X, y) pairs.

    Parameters
    ----------
    data             : Scaled array of shape (T, n_features)
    window_size      : Number of past time-steps fed to LSTM
    target_col_idx   : Column index of the target variable (Close)
    forecast_horizon : How many days ahead to predict

    Returns
    -------
    X : (n_samples, window_size, n_features)
    y : (n_samples, forecast_horizon)  – scaled Close prices
    """
    X, y = [], []
    total = len(data)

    for i in range(window_size, total - forecast_horizon + 1):
        X.append(data[i - window_size: i, :])          # look-back window
        y.append(data[i: i + forecast_horizon, target_col_idx])

    X = np.array(X)   # (samples, window, features)
    y = np.array(y)   # (samples, horizon)
    print(f"[DataPipeline] Sequences: X={X.shape}  y={y.shape}")
    return X, y


# ─────────────────────────────────────────────
# 5. TRAIN / TEST SPLIT
# ─────────────────────────────────────────────

def split_data(
    X: np.ndarray,
    y: np.ndarray,
    split_ratio: float = 0.80
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Chronological train/test split — NO shuffling, to preserve time order.

    Returns
    -------
    X_train, X_test, y_train, y_test
    """
    n = int(len(X) * split_ratio)
    X_train, X_test = X[:n], X[n:]
    y_train, y_test = y[:n], y[n:]
    print(f"[DataPipeline] Train: {X_train.shape}  Test: {X_test.shape}")
    return X_train, X_test, y_train, y_test


# ─────────────────────────────────────────────
# 6. FULL PIPELINE ENTRY POINT
# ─────────────────────────────────────────────

FEATURE_COLS = [
    "Open", "High", "Low", "Close", "Volume",
    "SMA_20", "SMA_50", "EMA_20",
    "RSI", "MACD", "MACD_Signal",
    "BB_Upper", "BB_Lower", "BB_Width",
    "ATR", "Return",
    # Extended features
    "Vol_SMA20", "Vol_Ratio",
    "STOCH_K", "STOCH_D",
    "Williams_R", "CCI",
    "Price_SMA20_Ratio", "Price_SMA50_Ratio",
    "Log_Return", "OBV",
    "ADX",
]
CLOSE_COL_IDX     = FEATURE_COLS.index("Close")       # = 3
LOG_RETURN_COL_IDX = FEATURE_COLS.index("Log_Return")  # stationary target


def build_pipeline(
    ticker: str,
    window_size: int = 60,
    forecast_horizon: int = 1,
    split_ratio: float = 0.80,
    start_date: str = None,
    scaler_save_path: Optional[str] = None
) -> dict:
    """
    End-to-end pipeline: fetch → engineer → scale → sequence → split.

    Ticker is auto-normalized (e.g. "RELIANCE" → "RELIANCE.NS").

    Returns a dict with keys:
        X_train, X_test, y_train, y_test,
        scaler, feature_cols, df_raw, df_featured
    """
    ticker = normalize_ticker(ticker)
    if start_date is None:
        start_date = DEFAULT_START_DATE

    # Step 1 – Fetch
    df_raw = fetch_stock_data(ticker, start=start_date)

    # Step 2 – Feature Engineering
    df_feat = add_technical_indicators(df_raw)

    # Step 3 – Scale (fit ONLY on training portion — no future leakage)
    data    = df_feat[FEATURE_COLS].values
    n_train = int(len(data) * split_ratio)

    if scaler_save_path and os.path.exists(scaler_save_path):
        scaler = joblib.load(scaler_save_path)
        print(f"[DataPipeline] Loaded existing scaler from {scaler_save_path}")
    else:
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaler.fit(data[:n_train])          # ← fit on train only
        if scaler_save_path:
            os.makedirs(os.path.dirname(scaler_save_path), exist_ok=True)
            joblib.dump(scaler, scaler_save_path)
            print(f"[DataPipeline] Scaler saved → {scaler_save_path}")
    scaled = scaler.transform(data)

    # Step 4 – Windowing (target = next-day log return — stationary signal)
    X, y = create_sequences(scaled, window_size, LOG_RETURN_COL_IDX, forecast_horizon)

    # Step 5 – Split
    X_train, X_test, y_train, y_test = split_data(X, y, split_ratio)

    # Previous-close prices for each test sample (needed to reconstruct prices from log returns)
    n_train_seqs = len(X_train)
    test_prev_closes = df_feat["Close"].values[
        n_train_seqs + window_size - 1 :
        n_train_seqs + window_size - 1 + len(X_test)
    ]

    return {
        "X_train":          X_train,
        "X_test":           X_test,
        "y_train":          y_train,
        "y_test":           y_test,
        "scaler":           scaler,
        "feature_cols":     FEATURE_COLS,
        "close_col_idx":    CLOSE_COL_IDX,
        "df_raw":           df_raw,
        "df_featured":      df_feat,
        "test_prev_closes": test_prev_closes,
    }


if __name__ == "__main__":
    result = build_pipeline("RELIANCE.NS", window_size=60)
    print("Pipeline complete.")
    print(f"  X_train : {result['X_train'].shape}")
    print(f"  X_test  : {result['X_test'].shape}")
