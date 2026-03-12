"""
ws_manager.py — WebSocket Connection Manager
=============================================
Manages active WebSocket connections, per-ticker subscriptions, and
fan-out broadcasting with graceful cleanup of dead connections.
"""

import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import WebSocket

log = logging.getLogger("stock-ws")


class ConnectionManager:
    """
    Thread-safe (async-safe) hub that tracks every live WebSocket
    connection and routes messages to the right ticker subscribers.

    Subscription model
    ------------------
    • Each connection is keyed to exactly one ticker.
    • Multiple connections may share the same ticker (fan-out broadcast).
    • Dead connections are removed automatically during broadcast.
    """

    def __init__(self) -> None:
        # ticker → set of active WebSocket objects
        self._subscriptions: Dict[str, Set[WebSocket]] = {}
        # WebSocket → ticker  (for O(1) cleanup on disconnect)
        self._conn_ticker: Dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def connect(self, ws: WebSocket, ticker: str) -> None:
        """Accept a new WebSocket and register it under *ticker*."""
        await ws.accept()
        async with self._lock:
            self._subscriptions.setdefault(ticker, set()).add(ws)
            self._conn_ticker[ws] = ticker
        n = len(self._subscriptions.get(ticker, set()))
        log.info("WS  CONNECTED  ticker=%s  total_subs=%d", ticker, n)

    async def disconnect(self, ws: WebSocket) -> None:
        """Unregister *ws* and clean up empty ticker buckets."""
        async with self._lock:
            ticker = self._conn_ticker.pop(ws, None)
            if ticker:
                self._subscriptions.get(ticker, set()).discard(ws)
                if not self._subscriptions.get(ticker):
                    self._subscriptions.pop(ticker, None)
        log.info("WS  DISCONNECTED  ticker=%s", ticker)

    # ── Broadcasting ───────────────────────────────────────────────────

    async def broadcast(self, ticker: str, data: dict) -> None:
        """
        Send *data* (serialised as JSON) to all connections subscribed to
        *ticker*.  Dead connections are pruned silently.
        """
        payload = json.dumps(data, default=str)
        async with self._lock:
            subs = list(self._subscriptions.get(ticker, set()))

        dead: list[WebSocket] = []
        for ws in subs:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

    async def broadcast_all(self, data: dict) -> None:
        """Broadcast *data* to every connected client regardless of ticker."""
        for ticker in list(self._subscriptions.keys()):
            await self.broadcast(ticker, data)

    # ── Introspection ──────────────────────────────────────────────────

    def subscriber_count(self, ticker: str) -> int:
        return len(self._subscriptions.get(ticker, set()))

    def active_tickers(self) -> list[str]:
        return list(self._subscriptions.keys())

    def total_connections(self) -> int:
        return len(self._conn_ticker)

    def stats(self) -> dict:
        return {
            "total_connections": self.total_connections(),
            "active_tickers": self.active_tickers(),
            "per_ticker": {
                t: len(subs) for t, subs in self._subscriptions.items()
            },
        }


# ── Singleton accessor ─────────────────────────────────────────────────────

_manager: ConnectionManager | None = None


def get_ws_manager() -> ConnectionManager:
    """Return the process-level singleton ConnectionManager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
