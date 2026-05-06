"""
main.py  —  FastAPI Backend for Stock Price Prediction
=======================================================
Endpoints
---------
GET  /                       Health check
GET  /api/stock/{ticker}     Historical OHLCV + indicators
POST /api/train              Train (or re-train) model for a ticker
GET  /api/predict/{ticker}   Next-N-day prediction
GET  /api/metrics/{ticker}   Saved evaluation metrics
GET  /api/tickers            List of trained models

Author  : Stock-Prediction AI Pipeline
Version : 1.0.0
"""

import os
import sys
import json
import time
import asyncio
import logging
import numpy as np
import pandas as pd
import glob
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import yfinance as yf

# ─── project imports ─────────────────────────
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "stocks")  # NIFTY 50 stock data
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "model"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("stock-api")


# ─────────────────────────────────────────────
# LIFESPAN (startup / shutdown)
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀  Stock-Prediction API starting …")
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Start the background data scheduler
    from scheduler import get_scheduler
    sched = get_scheduler(DATA_DIR)
    sched.start()
    log.info("📅  Data scheduler started.")

    # Start the WebSocket live-price publisher
    from ws_manager import get_ws_manager
    from ws_publisher import get_publisher
    publisher = get_publisher(get_ws_manager(), model_dir=MODEL_DIR)
    publisher.start()
    log.info("📡  WebSocket publisher started.")

    yield

    publisher.stop()
    sched.stop()
    log.info("👋  API shutting down.")


# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────

app = FastAPI(
    title       = "NIFTY 50 Stock Prediction API",
    description = "LSTM-based stock price forecasting for all 50 NIFTY companies (NSE India) — 10 years of historical data",
    version     = "3.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],    # Tighten in production
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ─── In-memory training-status store ─────────
training_status: dict[str, dict] = {}


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class TrainRequest(BaseModel):
    ticker:     str         = Field("RELIANCE.NS",  description="Stock symbol (e.g. RELIANCE.NS, TCS.NS, AAPL)")
    start_date: str         = Field(None, description="Historical start date (default: 20 years ago)")
    window:     int         = Field(60,  ge=10,  le=200,  description="Look-back window in days")
    horizon:    int         = Field(1,   ge=1,   le=30,   description="Days ahead to predict")
    epochs:     int         = Field(100, ge=5,   le=500)
    batch_size: int         = Field(32,  ge=8,   le=256)
    learning_rate: float    = Field(1e-3, gt=0)
    dropout:    float       = Field(0.2, ge=0.0, le=0.5)
    attention:  bool        = Field(True,  description="Use temporal attention")
    bidirectional: bool     = Field(False, description="Bidirectional LSTM")


class PredictRequest(BaseModel):
    ticker: str = Field("RELIANCE.NS")
    n_days: int = Field(30, ge=1, le=90, description="Days to forecast")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _config_path(ticker: str) -> str:
    return os.path.join(MODEL_DIR, ticker, "config.json")


def _model_exists(ticker: str) -> bool:
    return os.path.exists(_config_path(ticker))


def _load_config(ticker: str) -> dict:
    with open(_config_path(ticker)) as f:
        return json.load(f)


def _normalize(ticker: str) -> str:
    """Normalize ticker using data_pipeline helper."""
    from data_pipeline import ensure_indian_ticker
    try:
        return ensure_indian_ticker(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _training_task(req: TrainRequest):
    """Runs in a background thread (not async) so it doesn't block the event loop."""
    import argparse
    from data_pipeline import ensure_indian_ticker, DEFAULT_START_DATE
    ticker = ensure_indian_ticker(req.ticker)
    training_status[ticker] = {
        "status": "running",
        "started_at": time.time(),
        "epochs_total": req.epochs,
        "epoch": 0,
    }
    log.info(f"[{ticker}] Training started (epochs={req.epochs}, window={req.window}, horizon={req.horizon})")

    try:
        from train import train, PROGRESS_CALLBACK

        def _progress(epoch, total, logs):
            training_status[ticker].update({
                "epoch": epoch,
                "epochs_total": total,
                "loss": float(logs.get("loss", 0.0)) if logs else None,
                "val_loss": float(logs.get("val_loss", 0.0)) if logs else None,
            })
            loss_val = training_status[ticker].get("loss")
            val_loss_val = training_status[ticker].get("val_loss")
            log.info(
                f"[{ticker}] Epoch {epoch}/{total}"
                + (f" loss={loss_val:.6f}" if loss_val is not None else "")
                + (f" val_loss={val_loss_val:.6f}" if val_loss_val is not None else "")
            )

        import train as train_module
        train_module.PROGRESS_CALLBACK = _progress

        class _Args:
            ticker       = req.ticker   # train() will call normalize_ticker itself
            start        = req.start_date or DEFAULT_START_DATE
            window       = req.window
            horizon      = req.horizon
            epochs       = req.epochs
            batch        = req.batch_size
            lr           = req.learning_rate
            dropout      = req.dropout
            attention    = req.attention
            bidir        = req.bidirectional
            single_task  = False
            split        = 0.80
            output       = MODEL_DIR
            val_ratio    = 0.10
            direction_only = False
            direction_bigmove = False
            direction_threshold = 0.0
            scale        = "minmax"
            lstm_units   = "256,128,64"
            cnn          = False
            walk_forward = False
            wf_splits    = 3
            wf_embargo   = 5
            wf_min_train = 300
            threshold_objective = "sharpe"
            transaction_cost = 0.0005
            allow_short  = False
            strict_no_lookahead = False

        result = train(_Args())
        training_status[ticker] = {
            "status":   "completed",
            "metrics":  result["metrics"],
            "duration": round(time.time() - training_status[ticker]["started_at"], 1),
            "epoch": training_status[ticker].get("epoch", req.epochs),
            "epochs_total": req.epochs,
        }
        log.info(f"[{ticker}] Training completed. Metrics: {result['metrics']}")

    except Exception as exc:
        training_status[ticker] = {
            "status": "failed",
            "error":  str(exc),
        }
        log.error(f"[{ticker}] Training failed: {exc}", exc_info=True)


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "message": "Stock Prediction API is running 🚀"}


# ── GET /api/stock/{ticker} ───────────────────

@app.get("/api/stock/{ticker}", tags=["Data"])
def get_stock_data(
    ticker:    str,
    start:     str = Query(None, description="Start date YYYY-MM-DD (default: 20 years ago)"),
    end:       Optional[str] = Query(None),
    indicators: bool = Query(True, description="Include technical indicators"),
):
    """
    Fetch historical OHLCV data (+ optional indicators) for a ticker.
    Bare Indian symbols are auto-converted (e.g. RELIANCE → RELIANCE.NS).
    """
    try:
        from data_pipeline import fetch_stock_data, add_technical_indicators, load_raw_data, is_indian_ticker, get_currency, DEFAULT_START_DATE
        ticker = _normalize(ticker)
        if start is None:
            start = DEFAULT_START_DATE

        # Fast path: use local CSV if it exists (avoid yfinance round-trip)
        try:
            df = load_raw_data(ticker, data_dir=DATA_DIR)
        except FileNotFoundError:
            df = fetch_stock_data(ticker, start=start, end=end,
                                  save_dir=DATA_DIR, incremental=False)

        if indicators:
            df = add_technical_indicators(df)

        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.astype(object).where(pd.notnull(df), None)

        df.index = df.index.strftime("%Y-%m-%d")
        records = df.reset_index().rename(columns={"index": "date", "Date": "date"}).to_dict("records")
        return {
            "ticker":   ticker,
            "count":    len(records),
            "currency": get_currency(ticker),
            "is_indian": is_indian_ticker(ticker),
            "data":     records,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.error(f"get_stock_data error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/info/{ticker}", tags=["Data"])
def get_stock_info(ticker: str):
    """Fetch stock fundamentals like market cap, PE, etc."""
    ticker = _normalize(ticker)
    try:
        info = yf.Ticker(ticker).info or {}

        def _clean(value):
            if value is None:
                return None
            if isinstance(value, (float, int)):
                if value != value or value in (float("inf"), float("-inf")):
                    return None
                return float(value)
            return value

        payload = {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "marketCap": _clean(info.get("marketCap")),
            "peRatio": _clean(info.get("trailingPE")),
            "forwardPE": _clean(info.get("forwardPE")),
            "priceToBook": _clean(info.get("priceToBook")),
            "dividendYield": _clean(info.get("dividendYield")),
            "beta": _clean(info.get("beta")),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "website": info.get("website"),
            "currency": info.get("currency"),
        }
        return payload
    except Exception as e:
        log.error(f"get_stock_info error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /api/train ───────────────────────────

@app.post("/api/train", tags=["Model"])
def train_model(req: TrainRequest, background_tasks: BackgroundTasks):
    """
    Kick off a background training job for the given ticker.
    Poll /api/train/status/{ticker} for progress.
    """
    ticker = _normalize(req.ticker)
    req.ticker = ticker          # Ensure normalized ticker flows into task

    if training_status.get(ticker, {}).get("status") == "running":
        raise HTTPException(status_code=409, detail=f"Training already running for {ticker}")

    training_status[ticker] = {"status": "queued"}
    background_tasks.add_task(_training_task, req)

    return {
        "message":    f"Training started for {ticker}",
        "ticker":     ticker,
        "poll_url":   f"/api/train/status/{ticker}",
    }


@app.get("/api/train/status/{ticker}", tags=["Model"])
def training_status_check(ticker: str):
    """Check the status of an ongoing or completed training job."""
    ticker = _normalize(ticker)
    status = training_status.get(ticker)
    if status is None:
        raise HTTPException(status_code=404, detail=f"No training job found for {ticker}")
    return {"ticker": ticker, **status}


@app.get("/api/data/tickers", tags=["Live Data"])
def list_data_tickers():
    """List tickers that have local CSV data available."""
    pattern = os.path.join(DATA_DIR, "*.csv")
    tickers = [os.path.splitext(os.path.basename(p))[0] for p in glob.glob(pattern)]
    filtered = [t for t in tickers if (t.endswith(".NS") or t.endswith(".BO") or t.startswith("_IDX_"))]
    return {"tickers": sorted(filtered)}


# ── GET /api/predict/{ticker} ─────────────────

@app.get("/api/predict/{ticker}", tags=["Prediction"])
def predict(
    ticker:    str,
    n_days:    int  = Query(30, ge=1, le=90),
    start:     str  = Query(None),
):
    """
    Return predicted stock prices for the next n_days business days.
    Model must be trained first via POST /api/train.
    """
    ticker = _normalize(ticker)
    if not _model_exists(ticker):
        raise HTTPException(
            status_code=404,
            detail=f"No trained model found for {ticker}. POST /api/train first."
        )
    try:
        from train import forecast_future
        result = forecast_future(
            ticker=ticker,
            n_days=n_days,
            model_dir=MODEL_DIR,
            data_start=start,
        )
        config = _load_config(ticker)
        return {
            "ticker":   ticker,
            "n_days":   n_days,
            "horizon":  config.get("forecast_horizon", 1),
            "forecast": [
                {"date": d, "price": round(p, 4)}
                for d, p in zip(result["dates"], result["prices"])
            ],
        }
    except Exception as e:
        log.error(f"predict error [{ticker}]: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/metrics/{ticker} ─────────────────

@app.get("/api/metrics/{ticker}", tags=["Evaluation"])
def get_metrics(ticker: str):
    """Return saved evaluation metrics for a trained model."""
    ticker = _normalize(ticker)
    if not _model_exists(ticker):
        raise HTTPException(status_code=404, detail=f"No model found for {ticker}")
    config = _load_config(ticker)
    from data_pipeline import get_currency, is_indian_ticker
    return {
        "ticker":          ticker,
        "metrics":         config.get("metrics", {}),
        "epochs_trained":  config.get("epochs_trained"),
        "train_time_sec":  config.get("train_time_sec"),
        "window_size":     config.get("window_size"),
        "forecast_horizon": config.get("forecast_horizon"),
        "currency":        get_currency(ticker),
        "is_indian":       is_indian_ticker(ticker),
    }


# ── GET /api/tickers ──────────────────────────

@app.get("/api/tickers", tags=["Model"])
def list_tickers():
    """List all tickers for which a trained model exists."""
    if not os.path.isdir(MODEL_DIR):
        return {"tickers": []}
    tickers = [
        d for d in os.listdir(MODEL_DIR)
        if os.path.isdir(os.path.join(MODEL_DIR, d)) and
           os.path.exists(os.path.join(MODEL_DIR, d, "config.json"))
    ]
    return {"tickers": sorted(tickers)}


# ── GET /api/compare ─────────────────────────

@app.get("/api/compare", tags=["Prediction"])
def compare_tickers(
    tickers: str = Query(..., description="Comma-separated tickers, e.g. AAPL,TSLA,MSFT"),
    n_days:  int = Query(30, ge=1, le=90),
):
    """Compare future predictions for multiple tickers side-by-side."""
    ticker_list = [_normalize(t.strip()) for t in tickers.split(",")]
    results = {}
    errors  = {}

    for ticker in ticker_list:
        if not _model_exists(ticker):
            errors[ticker] = f"No model trained for {ticker}"
            continue
        try:
            from train import forecast_future
            r = forecast_future(ticker, n_days, MODEL_DIR)
            results[ticker] = [
                {"date": d, "price": round(p, 4)}
                for d, p in zip(r["dates"], r["prices"])
            ]
        except Exception as e:
            errors[ticker] = str(e)

    return {"forecasts": results, "errors": errors}


# ── GET /api/india/tickers ────────────────────

@app.get("/api/india/tickers", tags=["Indian Market"])
def india_tickers():
    """
    Return the complete NIFTY 50 universe — all 50 NSE large-cap stocks
    with metadata (name, sector, Yahoo Finance symbol).
    """
    from data_pipeline import NIFTY50_STOCKS, INDIAN_INDICES

    pattern = os.path.join(DATA_DIR, "*.csv")
    local = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(pattern)}

    stocks = [
        {
            "symbol":   f"{bare}.NS",
            "bare":     bare,
            "name":     info["name"],
            "sector":   info["sector"],
            "exchange": "NSE",
        }
        for bare, info in NIFTY50_STOCKS.items()
        if f"{bare}.NS" in local
    ]

    indices = [
        {
            "symbol":      sym,
            "name":        info["name"],
            "description": info["description"],
        }
        for sym, info in INDIAN_INDICES.items()
        if sym.replace("^", "_IDX_") in local
    ]

    return {
        "stocks":  stocks,
        "indices": indices,
        "count":   len(stocks),
        "note":    "NIFTY 50 universe only. All symbols use Yahoo Finance NSE format (.NS).",
    }


# ── GET /api/market/info/{ticker} ─────────────

@app.get("/api/market/info/{ticker}", tags=["Indian Market"])
def market_info(ticker: str):
    """
    Return market metadata for a ticker: exchange, currency, trading hours.
    """
    from data_pipeline import is_indian_ticker, get_currency, INDIAN_STOCKS, INDIAN_INDICES

    ticker = _normalize(ticker)
    is_indian = is_indian_ticker(ticker)
    bare = ticker.replace(".NS", "").replace(".BO", "")

    info = {
        "ticker":    ticker,
        "is_indian": is_indian,
        "currency":  get_currency(ticker),
        "currency_symbol": "₹" if is_indian else "$",
    }

    if is_indian:
        info["exchange"]      = "NSE" if ticker.endswith(".NS") else "BSE" if ticker.endswith(".BO") else "NSE"
        info["trading_hours"] = "09:15 – 15:30 IST"
        info["timezone"]      = "Asia/Kolkata"

        if bare in INDIAN_STOCKS:
            info["name"]   = INDIAN_STOCKS[bare]["name"]
            info["sector"] = INDIAN_STOCKS[bare]["sector"]
        elif ticker in INDIAN_INDICES:
            info["name"]        = INDIAN_INDICES[ticker]["name"]
            info["description"] = INDIAN_INDICES[ticker]["description"]
    else:
        info["exchange"]      = "NYSE/NASDAQ"
        info["trading_hours"] = "09:30 – 16:00 ET"
        info["timezone"]      = "America/New_York"

    return info


# ── GET /api/market/metrics ──────────────────

@app.get("/api/market/metrics", tags=["Indian Market"])
def market_metrics():
    """
    Return live market snapshot metrics for the dashboard.
    """
    from data_pipeline import load_raw_data, fetch_stock_data, DEFAULT_START_DATE, NIFTY50_TICKERS

    def _load_series(ticker: str):
        try:
            return load_raw_data(ticker, data_dir=DATA_DIR)
        except FileNotFoundError:
            return fetch_stock_data(ticker, start=DEFAULT_START_DATE, save_dir=DATA_DIR, incremental=False)

    def _latest_change(df: pd.DataFrame):
        if df is None or df.empty or len(df) < 2:
            return None, None
        df = df.sort_index()
        last = float(df.iloc[-1]["Close"])
        prev = float(df.iloc[-2]["Close"])
        if prev == 0:
            return last, 0.0
        change = (last - prev) / prev * 100.0
        return last, change

    # NIFTY 50
    nifty_df = _load_series("^NSEI")
    nifty_last, nifty_change = _latest_change(nifty_df)

    # SENSEX
    sensex_df = _load_series("^BSESN")
    sensex_last, sensex_change = _latest_change(sensex_df)

    # Market breadth: count positive vs negative daily moves in NIFTY 50 universe
    positive = 0
    negative = 0
    for ticker in NIFTY50_TICKERS:
        try:
            df = load_raw_data(ticker, data_dir=DATA_DIR)
        except Exception:
            continue
        if df is None or df.empty or len(df) < 2:
            continue
        df = df.sort_index()
        last = float(df.iloc[-1]["Close"])
        prev = float(df.iloc[-2]["Close"])
        if last >= prev:
            positive += 1
        else:
            negative += 1

    # Volatility: 20-day std of daily returns for NIFTY 50
    volatility = None
    if nifty_df is not None and len(nifty_df) >= 21:
        returns = nifty_df["Close"].pct_change()
        volatility = float(returns.rolling(20).std().iloc[-1] * 100.0)

    def _fmt_value(value, decimals=0):
        if value is None:
            return "--"
        return f"{value:,.{decimals}f}"

    def _fmt_trend(value):
        if value is None:
            return "--"
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:.2f}%"

    vol_label = "--"
    vol_trend = "Stable"
    if volatility is not None:
        vol_label = f"{volatility:.1f}"
        vol_trend = "Rising" if volatility >= 20 else "Stable"

    breadth_label = f"{positive} / {negative}" if (positive + negative) > 0 else "--"
    breadth_trend = "Positive" if positive >= negative else "Negative"

    return {
        "as_of": (nifty_df.index.max().strftime("%Y-%m-%d") if nifty_df is not None and not nifty_df.empty else None),
        "metrics": [
            {"label": "NIFTY 50", "value": _fmt_value(nifty_last, 0), "trend": _fmt_trend(nifty_change)},
            {"label": "Sensex", "value": _fmt_value(sensex_last, 0), "trend": _fmt_trend(sensex_change)},
            {"label": "Market Breadth", "value": breadth_label, "trend": breadth_trend},
            {"label": "Volatility", "value": vol_label, "trend": vol_trend},
        ],
    }


# ─────────────────────────────────────────────
# LIVE DATA PIPELINE ENDPOINTS
# ─────────────────────────────────────────────

class RefreshRequest(BaseModel):
    tickers: Optional[List[str]] = Field(None, description="Specific tickers to refresh (None = all watched)")
    force:   bool               = Field(True, description="Force refresh even if recently updated")

class WatchlistRequest(BaseModel):
    tickers: List[str] = Field(..., description="Tickers to set/add/remove")

class ScheduleConfigRequest(BaseModel):
    enabled:          Optional[bool] = None
    mode:             Optional[str]  = Field(None, pattern="^(interval|cron)$")
    interval_minutes: Optional[int]  = Field(None, ge=5, le=1440)
    cron_hour:        Optional[str]  = None
    cron_minute:      Optional[str]  = None
    cron_day_of_week: Optional[str]  = None
    auto_add_trained: Optional[bool] = None


@app.get("/api/data/freshness", tags=["Live Data"])
def data_freshness_summary():
    """
    Get a high-level summary of data freshness across all tickers:
    how many are stale, how many are fresh, total rows, watchlist.
    """
    from live_data_manager import get_manager
    mgr = get_manager(DATA_DIR)
    return mgr.get_summary()


@app.get("/api/data/freshness/{ticker}", tags=["Live Data"])
def data_freshness_ticker(ticker: str):
    """Get freshness info for a specific ticker."""
    from live_data_manager import get_manager
    mgr = get_manager(DATA_DIR)
    ticker = _normalize(ticker)
    return {"ticker": ticker, **mgr.get_freshness(ticker)}


@app.post("/api/data/refresh", tags=["Live Data"])
def manual_refresh(req: RefreshRequest, background_tasks: BackgroundTasks):
    """
    Manually trigger a data refresh.
    Runs in the background if many tickers; returns immediately.
    """
    from scheduler import get_scheduler
    sched = get_scheduler(DATA_DIR)

    tickers = [_normalize(t) for t in req.tickers] if req.tickers else None

    # For single ticker, do it synchronously for immediate feedback
    if tickers and len(tickers) == 1:
        result = sched.manager.refresh_ticker(tickers[0], force=req.force)
        return {"mode": "sync", "result": result}

    # For multiple tickers, run in background
    background_tasks.add_task(sched.trigger_now, tickers)
    return {
        "mode":    "background",
        "message": f"Refresh started for {len(tickers) if tickers else 'all watched'} tickers",
        "poll":    "/api/data/freshness",
    }


@app.post("/api/data/refresh/{ticker}", tags=["Live Data"])
def refresh_single_ticker(ticker: str, force: bool = Query(True)):
    """
    Refresh data for a single ticker synchronously.
    Returns the updated freshness info.
    """
    from live_data_manager import get_manager
    mgr = get_manager(DATA_DIR)
    ticker = _normalize(ticker)
    result = mgr.refresh_ticker(ticker, force=force)
    return result


@app.get("/api/data/watchlist", tags=["Live Data"])
def get_watchlist():
    """Get the current auto-refresh watchlist."""
    from live_data_manager import get_manager
    mgr = get_manager(DATA_DIR)
    return {"watchlist": mgr.get_watchlist()}


@app.put("/api/data/watchlist", tags=["Live Data"])
def set_watchlist(req: WatchlistRequest):
    """Replace the entire watchlist."""
    from live_data_manager import get_manager
    mgr = get_manager(DATA_DIR)
    tickers = mgr.set_watchlist(req.tickers)
    return {"watchlist": tickers}


@app.post("/api/data/watchlist/add", tags=["Live Data"])
def add_to_watchlist(req: WatchlistRequest):
    """Add tickers to the watchlist."""
    from live_data_manager import get_manager
    mgr = get_manager(DATA_DIR)
    for t in req.tickers:
        mgr.add_to_watchlist(t)
    return {"watchlist": mgr.get_watchlist()}


@app.post("/api/data/watchlist/remove", tags=["Live Data"])
def remove_from_watchlist(req: WatchlistRequest):
    """Remove tickers from the watchlist."""
    from live_data_manager import get_manager
    mgr = get_manager(DATA_DIR)
    for t in req.tickers:
        mgr.remove_from_watchlist(t)
    return {"watchlist": mgr.get_watchlist()}


@app.get("/api/scheduler/status", tags=["Scheduler"])
def scheduler_status():
    """Get the current scheduler status, config, and next scheduled run."""
    from scheduler import get_scheduler
    sched = get_scheduler(DATA_DIR)
    return sched.get_status()


@app.put("/api/scheduler/config", tags=["Scheduler"])
def update_scheduler_config(req: ScheduleConfigRequest):
    """Update scheduler configuration and restart with new settings."""
    from scheduler import get_scheduler
    sched = get_scheduler(DATA_DIR)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No config fields provided")
    return sched.reschedule(**updates)


@app.get("/api/scheduler/history", tags=["Scheduler"])
def scheduler_history(limit: int = Query(20, ge=1, le=100)):
    """Get recent scheduler run history."""
    from scheduler import get_scheduler
    sched = get_scheduler(DATA_DIR)
    return {"history": sched.get_history(limit)}


# ─────────────────────────────────────────────
# WEBSOCKET — LIVE PRICE STREAMING
# ─────────────────────────────────────────────

@app.websocket("/ws/live/{ticker}")
async def ws_live(ws: WebSocket, ticker: str):
    """
    WebSocket endpoint for live stock-price streaming.

    Protocol
    --------
    • Client connects  → server starts emitting {type:"price", ...} every
      WS_PUBLISH_INTERVAL seconds (default 2 s).
    • Client may send  → "ping"  to check liveness; server replies {type:"pong"}.
    • Server sends     → {type:"price", symbol, price, change, change_pct,
                          prediction, trend, simulated, timestamp}
    """
    from ws_manager import get_ws_manager
    from ws_publisher import get_publisher

    mgr    = get_ws_manager()
    ticker = _normalize(ticker)
    await mgr.connect(ws, ticker)

    # Ensure publisher is running (idempotent)
    pub = get_publisher(mgr, model_dir=MODEL_DIR)
    pub.start()

    try:
        while True:
            raw = await ws.receive_text()
            if raw.strip() == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning("WS error [%s]: %s", ticker, exc)
    finally:
        await mgr.disconnect(ws)


@app.get("/api/ws/stats", tags=["WebSocket"])
def ws_stats():
    """Return current WebSocket connection stats (useful for monitoring)."""
    from ws_manager import get_ws_manager
    return get_ws_manager().stats()


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
