// api.js  —  Centralised Axios client for the Stock Prediction API

import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,   // Training can take a while
  headers: { "Content-Type": "application/json" },
});

// ── Interceptor: attach timestamps for debugging ──
api.interceptors.request.use((config) => {
  config._ts = Date.now();
  return config;
});

api.interceptors.response.use(
  (res) => {
    const ms = Date.now() - (res.config._ts || Date.now());
    console.debug(`[API] ${res.config.method?.toUpperCase()} ${res.config.url} → ${res.status} (${ms}ms)`);
    return res;
  },
  (err) => {
    console.error("[API] Error:", err.response?.data || err.message);
    return Promise.reject(err);
  }
);

// ─────────────────────────────────────────────
// DATA ENDPOINTS
// ─────────────────────────────────────────────

export const fetchStockData = (ticker, start) =>
  api.get(`/api/stock/${ticker}`, { params: start ? { start } : {} }).then((r) => r.data);

export const listTickers = () =>
  api.get("/api/tickers").then((r) => r.data);

// ─────────────────────────────────────────────
// INDIAN MARKET ENDPOINTS
// ─────────────────────────────────────────────

export const fetchIndiaTickers = () =>
  api.get("/api/india/tickers").then((r) => r.data);

export const fetchMarketInfo = (ticker) =>
  api.get(`/api/market/info/${ticker}`).then((r) => r.data);

// ─────────────────────────────────────────────
// TRAINING ENDPOINTS
// ─────────────────────────────────────────────

export const trainModel = (payload) =>
  api.post("/api/train", payload).then((r) => r.data);

export const getTrainingStatus = (ticker) =>
  api.get(`/api/train/status/${ticker}`).then((r) => r.data);

// ─────────────────────────────────────────────
// PREDICTION ENDPOINTS
// ─────────────────────────────────────────────

export const getPrediction = (ticker, nDays = 30) =>
  api.get(`/api/predict/${ticker}`, { params: { n_days: nDays } }).then((r) => r.data);

export const compareTickers = (tickers, nDays = 30) =>
  api.get("/api/compare", { params: { tickers: tickers.join(","), n_days: nDays } }).then((r) => r.data);

// ─────────────────────────────────────────────
// METRICS
// ─────────────────────────────────────────────

export const getMetrics = (ticker) =>
  api.get(`/api/metrics/${ticker}`).then((r) => r.data);

export default api;
