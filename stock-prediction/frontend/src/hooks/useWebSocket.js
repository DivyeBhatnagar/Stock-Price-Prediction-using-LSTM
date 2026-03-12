/**
 * useWebSocket.js — Reconnecting WebSocket hook
 * ===============================================
 * Manages a single WebSocket connection with automatic exponential-backoff
 * reconnection, heartbeat pings, and clean unmount teardown.
 *
 * Usage
 * -----
 *   const { status, STATUS } = useWebSocket("/ws/live/RELIANCE.NS", {
 *     enabled:   true,
 *     onMessage: (data) => console.log(data),
 *   });
 */

import { useState, useEffect, useRef, useCallback } from "react";

const WS_BASE = (import.meta.env.VITE_WS_URL || "ws://localhost:8000");

export const WS_STATUS = Object.freeze({
  IDLE:        "idle",
  CONNECTING:  "connecting",
  OPEN:        "open",
  CLOSED:      "closed",
  ERROR:       "error",
});

const MAX_RETRIES     = 12;          // give up after ~5 min of attempts
const HEARTBEAT_MS    = 25_000;      // send "ping" every 25 s
const BASE_BACKOFF_MS = 1_000;       // first retry delay

/**
 * @param {string|null} path  - e.g. "/ws/live/RELIANCE.NS"
 * @param {{ enabled?: boolean, onMessage?: (data: object) => void }} opts
 */
export function useWebSocket(path, { enabled = true, onMessage } = {}) {
  const [status, setStatus] = useState(WS_STATUS.IDLE);

  const wsRef        = useRef(null);
  const retryRef     = useRef(0);
  const heartbeatRef = useRef(null);
  const mountedRef   = useRef(true);
  const onMsgRef     = useRef(onMessage);

  // Keep onMessage ref fresh without triggering reconnects
  useEffect(() => { onMsgRef.current = onMessage; }, [onMessage]);

  const cleanup = useCallback(() => {
    clearInterval(heartbeatRef.current);
    heartbeatRef.current = null;
    if (wsRef.current) {
      wsRef.current.onopen    = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror   = null;
      wsRef.current.onclose   = null;
      if (wsRef.current.readyState < WebSocket.CLOSING) {
        wsRef.current.close(1000, "component unmounted");
      }
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current || !enabled || !path) return;

    cleanup();
    const url = `${WS_BASE}${path}`;
    setStatus(WS_STATUS.CONNECTING);

    let ws;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      console.error("[WS] Constructor error:", err);
      setStatus(WS_STATUS.ERROR);
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      retryRef.current = 0;
      setStatus(WS_STATUS.OPEN);

      // Heartbeat to keep connection alive through proxies / load balancers
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, HEARTBEAT_MS);
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.type !== "pong" && onMsgRef.current) onMsgRef.current(data);
      } catch { /* skip malformed frames */ }
    };

    ws.onerror = () => {
      if (mountedRef.current) setStatus(WS_STATUS.ERROR);
    };

    ws.onclose = (evt) => {
      clearInterval(heartbeatRef.current);
      if (!mountedRef.current) return;

      // Normal close → don't reconnect
      if (evt.code === 1000 || evt.code === 1001) {
        setStatus(WS_STATUS.CLOSED);
        return;
      }

      setStatus(WS_STATUS.CLOSED);

      if (retryRef.current >= MAX_RETRIES) {
        console.warn("[WS] Max retries reached for", path);
        return;
      }

      // Exponential backoff: 1s, 2s, 4s, … capped at 30s
      const delay = Math.min(BASE_BACKOFF_MS * 2 ** retryRef.current, 30_000);
      retryRef.current += 1;
      console.info(`[WS] Reconnecting in ${delay}ms (attempt ${retryRef.current})`);
      setTimeout(connect, delay);
    };
  }, [path, enabled, cleanup]); // onMessage excluded intentionally (via ref)

  useEffect(() => {
    mountedRef.current = true;
    if (enabled && path) connect();
    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [connect, enabled, path, cleanup]);

  const disconnect = useCallback(() => {
    cleanup();
    setStatus(WS_STATUS.CLOSED);
  }, [cleanup]);

  return { status, STATUS: WS_STATUS, disconnect };
}
