# Live Data Streaming — Setup & Operations Guide

## Overview

This document explains how to run the **live data streaming** features
of StockOracle: the backend WebSocket server, the frontend real-time chart,
and how to deploy everything with Docker.

---

## Architecture

```
Browser (React)
  │
  │  REST  /api/*          ──►  FastAPI (main.py)
  │  WS    ws://host/ws/live/{ticker}
  │                              │
  │                        ws_manager.py   ◄── ConnectionManager
  │                        ws_publisher.py ◄── LivePublisher (yfinance)
  └──────────────────────────────────────────────────────────────
```

### WebSocket message format

```json
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
  "prediction":  2550.00,
  "trend":       "up",
  "simulated":   false,
  "timestamp":   "2026-03-12T09:30:00+00:00"
}
```

| Field        | Description |
|-------------|-------------|
| `prediction` | LSTM model's next-period forecast; `null` if no model trained |
| `trend`      | `"up"` / `"down"` / `"flat"` derived from forecast vs. live price |
| `simulated`  | `true` when market is closed or yfinance is rate-limited; price is last-known + tiny random walk |

---

## Running Locally

### 1 — Prerequisites

```bash
# Python 3.11+
python --version

# Node 20+
node --version
```

### 2 — Backend

```bash
cd stock-prediction/backend

# Create virtual environment (or use existing .venv)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API now exposes:

| Path | Description |
|------|-------------|
| `GET /` | Health check |
| `WS /ws/live/{ticker}` | Live streaming WebSocket |
| `GET /api/ws/stats` | WS connection statistics |

### 3 — Frontend

```bash
cd stock-prediction/frontend

# Install dependencies
npm install

# Install Playwright browsers (for E2E tests only)
npx playwright install --with-deps chromium

# Start the dev server
npm run dev
# → http://localhost:5173
```

Open the dashboard, search for a stock (e.g. `RELIANCE.NS`), then click the
**Live** tab and flip the toggle to start streaming.

---

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp stock-prediction/.env.example stock-prediction/.env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | REST API base URL |
| `VITE_WS_URL` | `ws://localhost:8000` | WebSocket base URL |
| `WS_PUBLISH_INTERVAL` | `2` | Seconds between broadcasts |
| `WS_CACHE_TTL` | `5` | yfinance fetch cooldown per ticker |
| `WS_SIMULATE_NOISE` | `0.0003` | Max ±% random walk outside market hours |
| `FINNHUB_API_KEY` | _(empty)_ | Optional: Finnhub real-time data key |
| `ALPHAVANTAGE_API_KEY` | _(empty)_ | Optional: Alpha Vantage intraday key |

---

## Docker Deployment

```bash
cd stock-prediction

# Build and start both services
docker compose --env-file .env up --build

# Frontend → http://localhost:80
# Backend  → http://localhost:8000
```

For **production**, update `docker-compose.yml` to:
1. Set `VITE_API_URL` and `VITE_WS_URL` to your public domain.
2. Use `wss://` (WebSocket Secure) in `VITE_WS_URL`.
3. Add TLS termination in front of nginx (e.g. Caddy or AWS ALB).

---

## Running Tests

### Backend unit tests

```bash
cd stock-prediction/backend
source .venv/bin/activate
pytest tests/test_websocket.py -v
```

Expected output:

```
tests/test_websocket.py::TestConnectionManager::test_connect_registers_ticker     PASSED
tests/test_websocket.py::TestConnectionManager::test_disconnect_removes_ticker    PASSED
tests/test_websocket.py::TestConnectionManager::test_broadcast_sends_to_all_subscribers PASSED
tests/test_websocket.py::TestConnectionManager::test_broadcast_prunes_dead_connections PASSED
tests/test_websocket.py::TestConnectionManager::test_multiple_tickers_isolated    PASSED
tests/test_websocket.py::TestConnectionManager::test_stats_returns_correct_shape  PASSED
tests/test_websocket.py::TestWebSocketEndpoint::test_ws_ping_pong                 PASSED
tests/test_websocket.py::TestWebSocketEndpoint::test_ws_connect_and_disconnect    PASSED
tests/test_websocket.py::TestWebSocketEndpoint::test_ws_stats_endpoint            PASSED
tests/test_websocket.py::TestWebSocketEndpoint::test_health_check                 PASSED
tests/test_websocket.py::TestLivePublisher::test_publisher_broadcasts_price_message PASSED
tests/test_websocket.py::TestLivePublisher::test_publisher_skips_on_none_price    PASSED
tests/test_websocket.py::TestFetchLivePrice::test_returns_expected_keys           PASSED
```

### Frontend E2E tests (Playwright)

```bash
cd stock-prediction/frontend

# Run all E2E tests (requires backend running on :8000)
npm run test:e2e

# Interactive UI mode
npm run test:e2e:ui

# View HTML report
npm run test:e2e:report
```

---

## Accessibility Checklist (WCAG AA)

| Check | Status |
|-------|--------|
| All interactive elements have `aria-label` or visible text | ✅ |
| Color contrast ≥ 4.5:1 for normal text | ✅ (`text-slate-900` on `bg-white`) |
| Color contrast ≥ 3:1 for large text and UI components | ✅ |
| Keyboard navigation: full Tab/Enter/Space support | ✅ |
| Visible focus rings on all interactive elements (`focus-visible`) | ✅ |
| `role="tablist"` / `role="tab"` with `aria-selected` | ✅ |
| `role="switch"` with `aria-checked` for toggle | ✅ |
| `aria-live="polite"` on live price region | ✅ |
| `role="banner"` on `<header>` | ✅ |
| Mobile nav drawer: focus trapped, `aria-label`, close button | ✅ |
| Minimum 44×44 px touch targets | ✅ |
| `<time>` element for timestamps | ✅ |
| Alt text on all icon-only buttons | ✅ (`aria-label` / `aria-hidden`) |
| `prefers-reduced-motion` respected | ✅ |

### Running Lighthouse

```bash
# Install Lighthouse CLI
npm install -g lighthouse

# Audit the running frontend
lighthouse http://localhost:5173 \
  --only-categories=accessibility,performance,best-practices \
  --output=html --output-path=./lighthouse-report.html
```

Target scores: **Accessibility ≥ 95, Performance ≥ 80**.

---

## Switching to Dark Mode

The app supports dark mode via the `"class"` strategy in `tailwind.config.js`.

1. Add `class="dark"` to `<html>` in `index.html`.
2. Uncomment the dark-mode overrides at the bottom of `src/index.css`.
3. Extend component classes with `dark:` variants as needed.

To build a theme toggle switch, set `document.documentElement.classList.toggle("dark")` in a button's `onClick` handler and persist the preference in `localStorage`.

---

## Troubleshooting

### WebSocket shows "Disconnected"

- Confirm the backend is running: `curl http://localhost:8000/`
- Check browser console for WS errors
- If running behind a reverse proxy, ensure the proxy forwards `Upgrade` headers (see `nginx.conf`)

### Prices are always `simulated: true`

- yfinance returns `simulated` prices when the market is closed (NSE hours: 09:15–15:30 IST)
- During market hours, set `WS_CACHE_TTL=1` for fresher data
- Consider adding a Finnhub API key for 24/7 real-time quotes

### `yfinance.fast_info` returns `None` for price

- Some tickers may need the `.NS` suffix: `RELIANCE` → `RELIANCE.NS`
- yfinance may rate-limit; the publisher will fall back to cached+noise automatically
