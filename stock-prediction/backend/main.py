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
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ─── project imports ─────────────────────────
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
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
    yield
    log.info("👋  API shutting down.")


# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────

app = FastAPI(
    title       = "Stock Price Prediction API",
    description = "LSTM-based stock price forecasting — supports US & Indian (NSE/BSE) markets",
    version     = "2.0.0",
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
    from data_pipeline import normalize_ticker
    return normalize_ticker(ticker)


def _training_task(req: TrainRequest):
    """Runs in a background thread (not async) so it doesn't block the event loop."""
    import argparse
    from data_pipeline import normalize_ticker, DEFAULT_START_DATE
    ticker = normalize_ticker(req.ticker)
    training_status[ticker] = {"status": "running", "started_at": time.time()}

    try:
        from train import train

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
            split        = 0.80
            output       = MODEL_DIR

        result = train(_Args())
        training_status[ticker] = {
            "status":   "completed",
            "metrics":  result["metrics"],
            "duration": round(time.time() - training_status[ticker]["started_at"], 1),
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
        from data_pipeline import fetch_stock_data, add_technical_indicators, normalize_ticker, is_indian_ticker, get_currency, DEFAULT_START_DATE
        ticker = normalize_ticker(ticker)
        if start is None:
            start = DEFAULT_START_DATE
        df = fetch_stock_data(ticker, start=start, end=end,
                              save_dir=os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
        if indicators:
            df = add_technical_indicators(df)

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
    status = training_status.get(ticker.upper())
    if status is None:
        raise HTTPException(status_code=404, detail=f"No training job found for {ticker.upper()}")
    return {"ticker": ticker.upper(), **status}


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
    Return curated list of popular Indian NSE stocks and indices
    with metadata (name, sector, Yahoo Finance symbol).
    """
    from data_pipeline import INDIAN_STOCKS, INDIAN_INDICES

    stocks = [
        {
            "symbol":   f"{bare}.NS",
            "bare":     bare,
            "name":     info["name"],
            "sector":   info["sector"],
            "exchange": "NSE",
        }
        for bare, info in INDIAN_STOCKS.items()
    ]

    indices = [
        {
            "symbol":      sym,
            "name":        info["name"],
            "description": info["description"],
        }
        for sym, info in INDIAN_INDICES.items()
    ]

    return {
        "stocks":  stocks,
        "indices": indices,
        "count":   len(stocks),
        "note":    "All symbols use Yahoo Finance format. "
                   "NSE stocks end with .NS, BSE with .BO.",
    }


# ── GET /api/market/info/{ticker} ─────────────

@app.get("/api/market/info/{ticker}", tags=["Indian Market"])
def market_info(ticker: str):
    """
    Return market metadata for a ticker: exchange, currency, trading hours.
    """
    from data_pipeline import normalize_ticker, is_indian_ticker, get_currency, INDIAN_STOCKS, INDIAN_INDICES

    ticker = normalize_ticker(ticker)
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


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
