"""
test_websocket.py — Unit tests for WebSocket connection handling
================================================================
Tests cover:
  1. ConnectionManager lifecycle (connect / disconnect / stats)
  2. Broadcast fan-out and dead-connection pruning
  3. WebSocket HTTP endpoint (ping/pong)
  4. /api/ws/stats REST endpoint

Run with:
  cd stock-prediction/backend
  pip install pytest pytest-asyncio httpx
  pytest tests/test_websocket.py -v
"""

import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Make sure the backend package is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
# ConnectionManager unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestConnectionManager:
    """Directly test ws_manager.ConnectionManager without HTTP layer."""

    def _make_mock_ws(self):
        ws = AsyncMock()
        ws.accept       = AsyncMock()
        ws.send_text    = AsyncMock()
        ws.readyState   = 1   # OPEN
        return ws

    @pytest.mark.asyncio
    async def test_connect_registers_ticker(self):
        from ws_manager import ConnectionManager
        mgr = ConnectionManager()
        ws  = self._make_mock_ws()

        await mgr.connect(ws, "RELIANCE.NS")

        assert "RELIANCE.NS" in mgr.active_tickers()
        assert mgr.subscriber_count("RELIANCE.NS") == 1
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_ticker(self):
        from ws_manager import ConnectionManager
        mgr = ConnectionManager()
        ws  = self._make_mock_ws()

        await mgr.connect(ws, "TCS.NS")
        await mgr.disconnect(ws)

        assert "TCS.NS" not in mgr.active_tickers()
        assert mgr.subscriber_count("TCS.NS") == 0

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_subscribers(self):
        from ws_manager import ConnectionManager
        mgr = ConnectionManager()
        ws1, ws2 = self._make_mock_ws(), self._make_mock_ws()

        await mgr.connect(ws1, "INFY.NS")
        await mgr.connect(ws2, "INFY.NS")

        payload = {"type": "price", "symbol": "INFY.NS", "price": 1500.0}
        await mgr.broadcast("INFY.NS", payload)

        expected = json.dumps(payload, default=str)
        ws1.send_text.assert_awaited_once_with(expected)
        ws2.send_text.assert_awaited_once_with(expected)

    @pytest.mark.asyncio
    async def test_broadcast_prunes_dead_connections(self):
        from ws_manager import ConnectionManager
        mgr = ConnectionManager()
        dead_ws = self._make_mock_ws()
        dead_ws.send_text = AsyncMock(side_effect=RuntimeError("connection closed"))

        await mgr.connect(dead_ws, "HDFC.NS")
        await mgr.broadcast("HDFC.NS", {"type": "price"})

        # Dead connection must be pruned
        assert mgr.subscriber_count("HDFC.NS") == 0

    @pytest.mark.asyncio
    async def test_multiple_tickers_isolated(self):
        from ws_manager import ConnectionManager
        mgr = ConnectionManager()
        ws_r = self._make_mock_ws()
        ws_t = self._make_mock_ws()

        await mgr.connect(ws_r, "RELIANCE.NS")
        await mgr.connect(ws_t, "TCS.NS")

        await mgr.broadcast("RELIANCE.NS", {"type": "price", "symbol": "RELIANCE.NS"})

        ws_r.send_text.assert_awaited_once()
        ws_t.send_text.assert_not_awaited()   # TCS should NOT receive RELIANCE message

    @pytest.mark.asyncio
    async def test_stats_returns_correct_shape(self):
        from ws_manager import ConnectionManager
        mgr = ConnectionManager()
        ws  = self._make_mock_ws()

        await mgr.connect(ws, "AAPL")
        stats = mgr.stats()

        assert stats["total_connections"] == 1
        assert "AAPL" in stats["active_tickers"]
        assert stats["per_ticker"]["AAPL"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint integration tests (via FastAPI TestClient)
# ─────────────────────────────────────────────────────────────────────────────

class TestWebSocketEndpoint:
    """Integration tests that exercise the /ws/live/{ticker} endpoint."""

    def test_ws_ping_pong(self, client):
        """Client sends 'ping', server must respond with {type:'pong'}."""
        with client.websocket_connect("/ws/live/RELIANCE.NS") as ws:
            ws.send_text("ping")
            raw  = ws.receive_text()
            data = json.loads(raw)
            assert data["type"] == "pong"

    def test_ws_connect_and_disconnect(self, client):
        """Connection lifecycle must not raise."""
        with client.websocket_connect("/ws/live/TCS.NS") as ws:
            # Just connecting and immediately closing should be fine
            pass  # __exit__ triggers close

    def test_ws_stats_endpoint(self, client):
        """/api/ws/stats must return the stats dict."""
        resp = client.get("/api/ws/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert "total_connections" in body
        assert "active_tickers" in body
        assert "per_ticker" in body

    def test_health_check(self, client):
        """Sanity check that the API is up."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ─────────────────────────────────────────────────────────────────────────────
# LivePublisher unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLivePublisher:
    """Test the publisher dispatch logic without real yfinance calls."""

    @pytest.mark.asyncio
    async def test_publisher_broadcasts_price_message(self):
        from ws_manager import ConnectionManager
        from ws_publisher import LivePublisher

        mgr = ConnectionManager()
        ws  = AsyncMock()
        ws.accept    = AsyncMock()
        ws.send_text = AsyncMock()
        await mgr.connect(ws, "RELIANCE.NS")

        publisher = LivePublisher(mgr, model_dir="/nonexistent")

        # Patch fetch_live_price to return a predictable value
        fake_price = {
            "price": 2500.0, "open": 2490.0, "high": 2510.0, "low": 2485.0,
            "volume": 1_000_000, "change": 10.0, "change_pct": 0.4,
            "simulated": True, "timestamp": "2026-03-12T10:00:00+00:00",
        }
        with patch("ws_publisher.fetch_live_price", new=AsyncMock(return_value=fake_price)):
            await publisher._publish_one("RELIANCE.NS")

        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args[0][0])
        assert sent["type"]   == "price"
        assert sent["symbol"] == "RELIANCE.NS"
        assert sent["price"]  == 2500.0

    @pytest.mark.asyncio
    async def test_publisher_skips_on_none_price(self):
        from ws_manager import ConnectionManager
        from ws_publisher import LivePublisher

        mgr = ConnectionManager()
        ws  = AsyncMock()
        ws.accept    = AsyncMock()
        ws.send_text = AsyncMock()
        await mgr.connect(ws, "SBIN.NS")

        publisher = LivePublisher(mgr, model_dir="/nonexistent")

        with patch("ws_publisher.fetch_live_price", new=AsyncMock(return_value=None)):
            await publisher._publish_one("SBIN.NS")

        # No broadcast should happen when price fetch returns None
        ws.send_text.assert_not_awaited()


# ─────────────────────────────────────────────────────────────────────────────
# fetch_live_price unit test (mocked yfinance)
# ─────────────────────────────────────────────────────────────────────────────

class TestFetchLivePrice:
    @pytest.mark.asyncio
    async def test_returns_expected_keys(self):
        import ws_publisher
        # Clear cache to force a real fetch attempt
        ws_publisher._price_cache.clear()

        fake_fast_info = MagicMock()
        fake_fast_info.last_price       = 2534.5
        fake_fast_info.previous_close   = 2510.0
        fake_fast_info.open             = 2515.0
        fake_fast_info.day_high         = 2545.0
        fake_fast_info.day_low          = 2505.0
        fake_fast_info.three_month_average_volume = 2_000_000

        mock_ticker = MagicMock()
        mock_ticker.fast_info = fake_fast_info

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await ws_publisher.fetch_live_price("RELIANCE.NS")

        assert result is not None
        for key in ("price", "change", "change_pct", "simulated", "timestamp"):
            assert key in result, f"Missing key: {key}"
        assert result["simulated"] is False
        assert result["price"] == round(2534.5, 4)
