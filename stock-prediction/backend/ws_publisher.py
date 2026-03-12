"""
ws_publisher.py — Live Stock Price Publisher
=============================================
Background service that continuously fetches near-real-time prices via
yfinance and broadcasts them through the WebSocket ConnectionManager.

Behaviour
---------
• During market hours  → yfinance `fast_info` (last_price / Ticker.info)
• Outside market hours → last cached price + tiny random-walk simulation
• Per-ticker price cache (TTL = CACHE_TTL_S) avoids hammering yfinance
• requestAnimationFrame-style batching is handled on the *frontend*;
  here we just throttle at PUBLISH_INTERVAL_S (configurable via env).
• If a trained LSTM model exists for the ticker the latest forecast
  price + trend are attached to every price message.

WebSocket message schema
------------------------
{
  "type":        "price",
  "symbol":      "RELIANCE.NS",
  "price":       2534.50,
  "open":        2510.00,
  "high":        2545.00,
  "low":         2505.00,
  "volume":      1234567,
  "change":      24.50,
  "change_pct":  0.98,
  "prediction":  2550.00,         # null when no model exists
  "trend":       "up",            # "up" | "down" | "flat" | null
  "simulated":   false,
  "timestamp":   "2026-03-12T09:30:00+00:00"
}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from typing import Dict, Optional

log = logging.getLogger("stock-publisher")

# ── Configuration ──────────────────────────────────────────────────────────

PUBLISH_INTERVAL_S = float(os.getenv("WS_PUBLISH_INTERVAL", "2"))   # seconds between broadcasts
CACHE_TTL_S        = float(os.getenv("WS_CACHE_TTL",        "5"))   # yfinance fetch cooldown per ticker
SIMULATE_NOISE     = float(os.getenv("WS_SIMULATE_NOISE",   "0.0003"))  # max ±% random walk


# ── In-memory price cache ──────────────────────────────────────────────────

_price_cache: Dict[str, dict] = {}


# ── Prediction cache (loaded once from saved model config) ────────────────

_pred_cache: Dict[str, dict] = {}


def _load_prediction(ticker: str, model_dir: str) -> Optional[dict]:
    """Read last saved LSTM forecast from config.json (no model inference)."""
    cached = _pred_cache.get(ticker)
    if cached:
        return cached
    try:
        cfg_path = os.path.join(model_dir, ticker, "config.json")
        if not os.path.exists(cfg_path):
            return None
        with open(cfg_path) as f:
            cfg = json.load(f)
        result = {
            "prediction": cfg.get("last_forecast_price"),
            "trend":      cfg.get("last_forecast_trend"),
        }
        _pred_cache[ticker] = result
        return result
    except Exception as e:
        log.debug("No forecast cache for %s: %s", ticker, e)
        return None


# ── Live price fetch ───────────────────────────────────────────────────────

async def fetch_live_price(ticker: str) -> Optional[dict]:
    """
    Fetch the most recent trade price for *ticker*.

    Returns a dict suitable for JSON serialisation or **None** on total failure.
    """
    import yfinance as yf

    now    = time.monotonic()
    cached = _price_cache.get(ticker)

    # ── Serve from cache with micro-noise while TTL is valid ──────────
    if cached and (now - cached["_fetched_at"]) < CACHE_TTL_S:
        noise  = 1.0 + random.uniform(-SIMULATE_NOISE, SIMULATE_NOISE)
        price  = round(cached["price"] * noise, 4)
        return {**cached, "price": price, "simulated": True,
                "timestamp": datetime.now(timezone.utc).isoformat()}

    # ── Real fetch via yfinance ───────────────────────────────────────
    try:
        t    = yf.Ticker(ticker)
        fi   = t.fast_info          # lightweight; doesn't hit heavy /quoteSummary

        raw_price = fi.last_price or fi.previous_close
        if not raw_price:
            raise ValueError("No price in fast_info")

        prev     = float(fi.previous_close or raw_price)
        price    = float(raw_price)
        chg      = round(price - prev, 4)
        chg_pct  = round((chg / prev) * 100, 4) if prev else None

        result = {
            "price":      round(price, 4),
            "open":       _safe_float(fi.open),
            "high":       _safe_float(fi.day_high),
            "low":        _safe_float(fi.day_low),
            "volume":     _safe_int(getattr(fi, "three_month_average_volume", None)),
            "change":     chg,
            "change_pct": chg_pct,
            "simulated":  False,
            "_fetched_at": now,
        }
        _price_cache[ticker] = result
        return {
            **result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        log.warning("yfinance fetch failed for %s: %s", ticker, exc)

        # Fall back to cached price with noise if available
        if cached:
            noise  = 1.0 + random.uniform(-SIMULATE_NOISE * 3, SIMULATE_NOISE * 3)
            price  = round(cached["price"] * noise, 4)
            return {**cached, "price": price, "simulated": True,
                    "timestamp": datetime.now(timezone.utc).isoformat()}
        return None


def _safe_float(v) -> Optional[float]:
    try:
        return round(float(v), 4)
    except Exception:
        return None


def _safe_int(v) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


# ── Publisher ──────────────────────────────────────────────────────────────

class LivePublisher:
    """
    Async background service that:
      1. Discovers which tickers have active WebSocket subscribers.
      2. Fetches current prices (or simulates them).
      3. Enriches the payload with the latest LSTM prediction.
      4. Broadcasts to all subscribers via the ConnectionManager.
    """

    def __init__(self, manager, model_dir: str = "models") -> None:
        self._manager   = manager
        self._model_dir = model_dir
        self._task:     asyncio.Task | None = None
        self._running   = False

    # ── Public control ─────────────────────────────────────────────────

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._task    = asyncio.create_task(self._run(), name="live-publisher")
            log.info("LivePublisher started  interval=%.1fs", PUBLISH_INTERVAL_S)

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        log.info("LivePublisher stopped")

    # ── Main loop ──────────────────────────────────────────────────────

    async def _run(self) -> None:
        while self._running:
            try:
                tickers = self._manager.active_tickers()
                if tickers:
                    await asyncio.gather(
                        *[self._publish_one(t) for t in tickers],
                        return_exceptions=True,
                    )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.error("Publisher loop error: %s", exc, exc_info=True)
            await asyncio.sleep(PUBLISH_INTERVAL_S)

    async def _publish_one(self, ticker: str) -> None:
        data = await fetch_live_price(ticker)
        if data is None:
            return

        # Attach LSTM forecast if available
        pred = _load_prediction(ticker, self._model_dir)
        prediction_price = None
        trend = None
        if pred and data["price"]:
            prediction_price = pred.get("prediction")
            # Derive trend from comparison when no explicit trend stored
            explicit_trend = pred.get("trend")
            if explicit_trend:
                trend = explicit_trend
            elif prediction_price:
                diff  = prediction_price - data["price"]
                trend = "up" if diff > 0.01 else ("down" if diff < -0.01 else "flat")

        payload = {
            "type":        "price",
            "symbol":      ticker,
            "price":       data["price"],
            "open":        data.get("open"),
            "high":        data.get("high"),
            "low":         data.get("low"),
            "volume":      data.get("volume"),
            "change":      data.get("change"),
            "change_pct":  data.get("change_pct"),
            "prediction":  round(float(prediction_price), 4) if prediction_price else None,
            "trend":       trend,
            "simulated":   data.get("simulated", False),
            "timestamp":   data.get("timestamp"),
        }
        await self._manager.broadcast(ticker, payload)


# ── Singleton accessor ──────────────────────────────────────────────────────

_publisher: LivePublisher | None = None


def get_publisher(manager, model_dir: str = "models") -> LivePublisher:
    """Return (and lazily create) the process-level singleton LivePublisher."""
    global _publisher
    if _publisher is None:
        _publisher = LivePublisher(manager, model_dir)
    return _publisher
