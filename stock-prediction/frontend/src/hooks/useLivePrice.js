/**
 * useLivePrice.js — Real-time price stream hook
 * ===============================================
 * Subscribes to a ticker's WebSocket feed and maintains a sliding window
 * of price history.  All chart state mutations are batched through
 * requestAnimationFrame to prevent UI jank during rapid updates.
 *
 * Usage
 * -----
 *   const { latestPrice, priceHistory, wsStatus, STATUS } =
 *     useLivePrice("RELIANCE.NS", { enabled: true, maxHistory: 120 });
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { useWebSocket, WS_STATUS } from "./useWebSocket";

const DEFAULT_MAX_HISTORY = 120;   // keep last N streaming data-points

/**
 * @param {string|null} ticker
 * @param {{ enabled?: boolean, maxHistory?: number }} opts
 */
export function useLivePrice(ticker, { enabled = true, maxHistory = DEFAULT_MAX_HISTORY } = {}) {
  const [latestPrice, setLatestPrice] = useState(null);
  const [priceHistory, setPriceHistory] = useState([]);

  // rAF batch ref — stores the last received frame while waiting for paint
  const rafRef     = useRef(null);
  const pendingRef = useRef(null);

  const handleMessage = useCallback((data) => {
    if (data.type !== "price") return;
    pendingRef.current = data;

    if (rafRef.current) return; // already queued

    rafRef.current = requestAnimationFrame(() => {
      const d = pendingRef.current;
      if (d) {
        setLatestPrice(d);
        setPriceHistory((prev) => {
          const point = {
            time:       d.timestamp,
            price:      d.price,
            prediction: d.prediction ?? null,
            simulated:  d.simulated ?? false,
          };
          const next = [...prev, point];
          return next.length > maxHistory ? next.slice(next.length - maxHistory) : next;
        });
      }
      rafRef.current  = null;
      pendingRef.current = null;
    });
  }, [maxHistory]);

  // Reset history when ticker changes
  useEffect(() => {
    setLatestPrice(null);
    setPriceHistory([]);
  }, [ticker]);

  // Cleanup pending rAF on unmount
  useEffect(() => () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
  }, []);

  const { status, STATUS, disconnect } = useWebSocket(
    ticker ? `/ws/live/${ticker}` : null,
    { enabled: enabled && !!ticker, onMessage: handleMessage }
  );

  return {
    latestPrice,    // latest full price message object
    priceHistory,   // array of { time, price, prediction, simulated }
    wsStatus:  status,
    STATUS:    WS_STATUS,
    disconnect,
    isConnected:  status === WS_STATUS.OPEN,
    isConnecting: status === WS_STATUS.CONNECTING,
  };
}
