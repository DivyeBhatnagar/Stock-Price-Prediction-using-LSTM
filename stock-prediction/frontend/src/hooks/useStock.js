// useStock.js  —  Custom React hook for fetching stock data

import { useState, useCallback } from "react";
import { fetchStockData, getPrediction, getMetrics, trainModel, getTrainingStatus, refreshTicker } from "../utils/api";

/**
 * Central hook that manages all stock-related state.
 *
 * Returns:
 *   stockData      – historical OHLCV records
 *   prediction     – forecast records { date, price }
 *   metrics        – model evaluation metrics
 *   trainingStatus – current training job status
 *   loading        – map of loading flags per operation
 *   error          – last error message
 *   loadStock()    – fetch historical data
 *   loadPrediction() – fetch N-day forecast
 *   startTraining() – kick off model training
 *   pollTraining()  – poll training status
 */
export function useStock() {
  const [stockData,      setStockData]      = useState(null);
  const [prediction,     setPrediction]     = useState(null);
  const [metrics,        setMetrics]        = useState(null);
  const [trainingStatus, setTrainingStatus] = useState(null);
  const [error,          setError]          = useState(null);
  const [loading,        setLoading]        = useState({
    stock:    false,
    predict:  false,
    train:    false,
    metrics:  false,
  });

  const setLoad = (key, val) =>
    setLoading((prev) => ({ ...prev, [key]: val }));

  // ── Load historical data ────────────────────
  const loadStock = useCallback(async (ticker, start) => {
    setLoad("stock", true);
    setError(null);
    try {
      const data = await fetchStockData(ticker, start);
      setStockData(data);
      return data;
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      throw e;
    } finally {
      setLoad("stock", false);
    }
  }, []);

  // ── Load prediction ──────────────────────────
  const loadPrediction = useCallback(async (ticker, nDays = 30) => {
    setLoad("predict", true);
    setError(null);
    try {
      const data = await getPrediction(ticker, nDays);
      setPrediction(data);

      // Also fetch metrics
      setLoad("metrics", true);
      const m = await getMetrics(ticker);
      setMetrics(m);
      setLoad("metrics", false);

      return data;
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      throw e;
    } finally {
      setLoad("predict", false);
    }
  }, []);

  // ── Start training ───────────────────────────
  const startTraining = useCallback(async (params) => {
    setLoad("train", true);
    setError(null);
    setTrainingStatus({ status: "queued" });
    try {
      const resp = await trainModel(params);
      setTrainingStatus({ status: "running" });
      return resp;
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      setTrainingStatus({ status: "failed", error: e.message });
      throw e;
    } finally {
      setLoad("train", false);
    }
  }, []);

  // ── Poll training status ──────────────────────
  const pollTraining = useCallback(async (ticker) => {
    try {
      const status = await getTrainingStatus(ticker);
      setTrainingStatus(status);
      return status;
    } catch (e) {
      // ignore polling errors silently
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setStockData(null);
    setPrediction(null);
    setMetrics(null);
    setTrainingStatus(null);
    setError(null);
  }, []);

  // ── Refresh data for ticker ───────────────
  const refreshStockData = useCallback(async (ticker) => {
    setLoad("stock", true);
    setError(null);
    try {
      // First trigger a live data refresh on the backend
      await refreshTicker(ticker);
      // Then reload the stock data
      const data = await fetchStockData(ticker);
      setStockData(data);
      return data;
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
      throw e;
    } finally {
      setLoad("stock", false);
    }
  }, []);

  return {
    stockData,
    prediction,
    metrics,
    trainingStatus,
    loading,
    error,
    loadStock,
    loadPrediction,
    startTraining,
    pollTraining,
    refreshStockData,
    reset,
  };
}
