"""
data_pipeline.py
================
Handles all data acquisition, preprocessing, normalization, and
time-series windowing for the LSTM stock-prediction system.

Supports **Indian stock market** tickers (NSE / BSE) only.
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
from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
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
      • Otherwise                                     → not supported
    """
    t = ticker.strip().upper()
    # Already formatted
    if t.endswith(".NS") or t.endswith(".BO") or t.startswith("^"):
        return t
    # Known Indian stock
    if t in _INDIAN_BARE_SET:
        return f"{t}.NS"
    raise ValueError(f"Only Indian tickers are supported: {ticker}")


def ensure_indian_ticker(ticker: str) -> str:
    """Normalize and validate ticker belongs to the Indian market."""
    t = normalize_ticker(ticker)
    if not is_indian_ticker(t):
        raise ValueError(f"Only Indian tickers are supported: {ticker}")
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
    df["SMA_10"]  = df["Close"].rolling(10).mean()
    df["SMA_20"]  = df["Close"].rolling(20).mean()
    df["SMA_50"]  = df["Close"].rolling(50).mean()
    df["SMA_200"] = df["Close"].rolling(200).mean()
    df["EMA_10"]  = df["Close"].ewm(span=10, adjust=False).mean()
    df["EMA_20"]  = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA_50"]  = df["Close"].ewm(span=50, adjust=False).mean()

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

    # ── Multi-horizon Returns / Momentum ──────
    df["Return_5"]  = df["Close"].pct_change(5)
    df["Return_10"] = df["Close"].pct_change(10)
    df["Return_20"] = df["Close"].pct_change(20)
    df["MOM_10"] = df["Close"].diff(10)
    df["ROC_10"] = df["Close"].pct_change(10)

    # ── Volatility (rolling) ──────────────────
    df["Volatility_10"] = df["Return"].rolling(10).std()
    df["Volatility_20"] = df["Return"].rolling(20).std()

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

    # ── Trend Strength ────────────────────────
    df["Trend_5_20"]  = df["SMA_20"] / (df["SMA_50"] + 1e-10) - 1
    df["Trend_20_50"] = df["EMA_20"] / (df["SMA_50"] + 1e-10) - 1

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

    return df


def add_lag_features(df: pd.DataFrame, close_lags: int = 10, return_lags: int = 5) -> pd.DataFrame:
    """Add lagged Close and Return features."""
    df = df.copy()
    for lag in range(1, close_lags + 1):
        df[f"Close_Lag_{lag}"] = df["Close"].shift(lag)
    for lag in range(1, return_lags + 1):
        df[f"Return_Lag_{lag}"] = df["Return"].shift(lag)
    return df


def add_rolling_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling statistics for Close and Volume."""
    df = df.copy()
    df["Close_Roll_Mean_10"] = df["Close"].rolling(10).mean()
    df["Close_Roll_Mean_20"] = df["Close"].rolling(20).mean()
    df["Close_Roll_Mean_50"] = df["Close"].rolling(50).mean()
    df["Close_Roll_Std_10"] = df["Close"].rolling(10).std()
    df["Close_Roll_Std_20"] = df["Close"].rolling(20).std()
    df["Volume_Roll_Mean_20"] = df["Volume"].rolling(20).mean()
    return df


def clean_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing/inf values in engineered features with light outlier control."""
    df = df.replace([np.inf, -np.inf], np.nan)

    # Winsorize heavy-tailed return features to reduce noise from extreme outliers.
    for col in ["Return", "Return_5", "Return_10", "Return_20", "Log_Return"]:
        if col in df.columns:
            q_low, q_hi = df[col].quantile([0.005, 0.995])
            df[col] = df[col].clip(lower=q_low, upper=q_hi)

    df = df.ffill()
    df = df.dropna()
    return df


def shift_feature_columns(df: pd.DataFrame, feature_cols: list, periods: int = 1) -> pd.DataFrame:
    """
    Shift selected feature columns forward in time (useful for strict no-look-ahead setups).

    Example: if predicting at market open for day t, shift end-of-day derived features by 1.
    """
    df = df.copy()
    for col in feature_cols:
        if col in df.columns:
            df[col] = df[col].shift(periods)
    return df


def add_external_signals(df: pd.DataFrame, start: str = None) -> pd.DataFrame:
    """
    Add external market signals (indices, FX, crude) aligned to the stock dates.
    """
    df = df.copy()
    if start is None:
        start = DEFAULT_START_DATE

    tickers = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "SENSEX": "^BSESN",
        "USDINR": "INR=X",
        "CRUDE": "CL=F",
    }

    for name, tkr in tickers.items():
        try:
            ext = yf.download(tkr, start=start, progress=False)
            if ext.empty:
                continue
            if isinstance(ext.columns, pd.MultiIndex):
                ext.columns = ext.columns.get_level_values(0)
            if getattr(ext.index, "tz", None) is not None:
                ext.index = ext.index.tz_localize(None)
            ext = ext[["Close"]].rename(columns={"Close": f"{name}_Close"})
            ext = ext.reindex(df.index).ffill()
            df[f"{name}_Return"] = ext[f"{name}_Close"].pct_change().fillna(0.0)
            df[f"{name}_SMA20_Ratio"] = (
                ext[f"{name}_Close"].rolling(20).mean() / (ext[f"{name}_Close"] + 1e-10) - 1
            ).fillna(0.0)
        except Exception as e:
            print(f"[DataPipeline] External signal '{tkr}' skipped: {e}")

    # Ensure external feature columns exist and do not introduce all-NaN rows.
    for name in tickers.keys():
        return_col = f"{name}_Return"
        ratio_col = f"{name}_SMA20_Ratio"
        if return_col not in df.columns:
            df[return_col] = 0.0
        if ratio_col not in df.columns:
            df[ratio_col] = 0.0
        df[return_col] = df[return_col].fillna(0.0)
        df[ratio_col] = df[ratio_col].fillna(0.0)

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


def create_sequences_direction(
    data: np.ndarray,
    window_size: int = 60,
    target_col_idx: int = 3,
    forecast_horizon: int = 1,
    direction_threshold: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build (X, y) pairs where y is a binary direction label.

    The label is 1 if the future target value exceeds the current target
    by more than the threshold, else 0.
    """
    X, y = [], []
    total = len(data)

    for i in range(window_size, total - forecast_horizon + 1):
        X.append(data[i - window_size: i, :])
        current = data[i - 1, target_col_idx]
        future = data[i + forecast_horizon - 1, target_col_idx]
        y.append(1.0 if (future - current) > direction_threshold else 0.0)

    X = np.array(X)
    y = np.array(y).reshape(-1, 1)
    print(f"[DataPipeline] Direction sequences: X={X.shape}  y={y.shape}")
    return X, y


def create_direction_labels(
    log_returns: np.ndarray,
    window_size: int,
    forecast_horizon: int,
    direction_threshold: float = 0.0,
    big_move_only: bool = False,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Create direction labels using cumulative log returns over the horizon.
    Returns labels and indices kept; coverage is fraction kept.
    """
    labels = []
    indices = []
    total = len(log_returns)

    for i in range(window_size, total - forecast_horizon + 1):
        future = np.sum(log_returns[i: i + forecast_horizon])
        if big_move_only and abs(future) <= direction_threshold:
            continue
        label = 1.0 if future > direction_threshold else 0.0
        labels.append(label)
        indices.append(i - window_size)

    labels = np.array(labels).reshape(-1, 1)
    indices = np.array(indices)
    coverage = len(labels) / max(1, (total - window_size - forecast_horizon + 1))
    return labels, indices, coverage


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
    "SMA_10", "SMA_20", "SMA_50", "SMA_200",
    "EMA_10", "EMA_20", "EMA_50",
    "RSI", "MACD", "MACD_Signal",
    "BB_Upper", "BB_Lower", "BB_Width",
    "ATR", "Return",
    "Return_5", "Return_10", "Return_20",
    "MOM_10", "ROC_10",
    "Volatility_10", "Volatility_20",
    # Extended features
    "Vol_SMA20", "Vol_Ratio",
    "STOCH_K", "STOCH_D",
    "Williams_R", "CCI",
    "Price_SMA20_Ratio", "Price_SMA50_Ratio",
    "Trend_5_20", "Trend_20_50",
    "Log_Return", "OBV",
    "ADX",
    "Close_Roll_Mean_10", "Close_Roll_Mean_20", "Close_Roll_Mean_50",
    "Close_Roll_Std_10", "Close_Roll_Std_20",
    "Volume_Roll_Mean_20",
    "Close_Lag_1", "Close_Lag_2", "Close_Lag_3", "Close_Lag_4", "Close_Lag_5",
    "Close_Lag_6", "Close_Lag_7", "Close_Lag_8", "Close_Lag_9", "Close_Lag_10",
    "Return_Lag_1", "Return_Lag_2", "Return_Lag_3", "Return_Lag_4", "Return_Lag_5",
    "NIFTY_Return", "NIFTY_SMA20_Ratio",
    "BANKNIFTY_Return", "BANKNIFTY_SMA20_Ratio",
    "SENSEX_Return", "SENSEX_SMA20_Ratio",
    "USDINR_Return", "USDINR_SMA20_Ratio",
    "CRUDE_Return", "CRUDE_SMA20_Ratio",
]
CLOSE_COL_IDX     = FEATURE_COLS.index("Close")       # = 3
LOG_RETURN_COL_IDX = FEATURE_COLS.index("Log_Return")  # stationary target


def build_pipeline(
    ticker: str,
    window_size: int = 60,
    forecast_horizon: int = 1,
    split_ratio: float = 0.80,
    start_date: str = None,
    scaler_save_path: Optional[str] = None,
    target_mode: str = "regression",
    direction_threshold: float = 0.0,
    scale_method: str = "minmax",
    strict_no_lookahead: bool = False,
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

    # Step 1 – Load local data if available; fall back to download
    try:
        df_raw = load_raw_data(ticker)
        if start_date is not None:
            df_raw = df_raw[df_raw.index >= start_date]
        if df_raw.empty:
            raise ValueError(f"No data returned for ticker '{ticker}'. Check the symbol or date range.")
        print(f"[DataPipeline] Loaded local data for {ticker}: {len(df_raw)} rows")
    except FileNotFoundError:
        # During training, prefer direct download/cache path to avoid long
        # incremental gap-filling delays that can stall experiments.
        df_raw = fetch_stock_data(ticker, start=start_date, incremental=False)

    # Step 2 – Feature Engineering
    df_feat = add_technical_indicators(df_raw)
    df_feat = add_lag_features(df_feat, close_lags=10, return_lags=5)
    df_feat = add_rolling_stats(df_feat)
    df_feat = add_external_signals(df_feat, start=start_date)
    df_feat = clean_feature_frame(df_feat)

    min_required = window_size + forecast_horizon + 1
    if len(df_feat) < min_required:
        raise ValueError(
            f"Not enough data after feature engineering for {ticker}. "
            f"Need at least {min_required} rows, got {len(df_feat)}. "
            "Increase training history or reduce window/indicators."
        )

    # Optional strict no-look-ahead mode: shift all model features by one bar.
    # Keep labels based on unshifted future log returns from original timeline.
    if strict_no_lookahead:
        shift_cols = [c for c in FEATURE_COLS if c != "Log_Return"]
        df_feat = shift_feature_columns(df_feat, shift_cols, periods=1)
        df_feat = clean_feature_frame(df_feat)

    # Step 3 – Scale (fit ONLY on training portion — no future leakage)
    data    = df_feat[FEATURE_COLS].values
    n_train = int(len(data) * split_ratio)

    scaler = None
    if scaler_save_path and os.path.exists(scaler_save_path):
        scaler = joblib.load(scaler_save_path)
        if hasattr(scaler, "n_features_in_") and scaler.n_features_in_ != data.shape[1]:
            print("[DataPipeline] Feature count changed — refitting scaler.")
            scaler = None
        else:
            print(f"[DataPipeline] Loaded existing scaler from {scaler_save_path}")

    if scaler is None:
        if scale_method == "standard":
            scaler = StandardScaler()
        elif scale_method == "robust":
            scaler = RobustScaler()
        else:
            scaler = MinMaxScaler(feature_range=(0, 1))
        scaler.fit(data[:n_train])          # ← fit on train only
        if scaler_save_path:
            os.makedirs(os.path.dirname(scaler_save_path), exist_ok=True)
            joblib.dump(scaler, scaler_save_path)
            print(f"[DataPipeline] Scaler saved → {scaler_save_path}")
    scaled = scaler.transform(data)

    # Step 4 – Windowing
    # Always build a return target stream aligned with X to support
    # threshold tuning and trading-metric evaluation.
    X_all, y_returns_all = create_sequences(scaled, window_size, LOG_RETURN_COL_IDX, forecast_horizon)
    if X_all.size == 0 or y_returns_all.size == 0:
        raise ValueError(
            f"Not enough sequences for {ticker} with window={window_size} and horizon={forecast_horizon}. "
            "Increase training history or reduce window."
        )

    if target_mode in ("direction", "direction_bigmove"):
        labels, indices, coverage = create_direction_labels(
            df_feat["Log_Return"].values,
            window_size,
            forecast_horizon,
            direction_threshold,
            big_move_only=(target_mode == "direction_bigmove"),
        )
        X = X_all[indices]
        y_returns = y_returns_all[indices]
        y = labels
    else:
        # target = next-day log return — stationary signal
        X, y = X_all, y_returns_all
        y_returns = y_returns_all

    # Step 5 – Split
    X_train, X_test, y_train, y_test = split_data(X, y, split_ratio)
    _, _, y_return_train, y_return_test = split_data(X, y_returns, split_ratio)

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
        "y_return_train":   y_return_train,
        "y_return_test":    y_return_test,
        "scaler":           scaler,
        "feature_cols":     FEATURE_COLS,
        "close_col_idx":    CLOSE_COL_IDX,
        "df_raw":           df_raw,
        "df_featured":      df_feat,
        "test_prev_closes": test_prev_closes,
        "coverage":         coverage if target_mode in ("direction", "direction_bigmove") else None,
    }


if __name__ == "__main__":
    result = build_pipeline("RELIANCE.NS", window_size=60)
    print("Pipeline complete.")
    print(f"  X_train : {result['X_train'].shape}")
    print(f"  X_test  : {result['X_test'].shape}")
