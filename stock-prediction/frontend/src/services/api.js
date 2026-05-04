import axios from "axios";
import {
  topStocks,
  marketMetrics,
  overviewSeries,
  detailSeries,
  predictionSeries
} from "../data/dummyData.js";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api"
});

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export async function fetchDashboardData() {
  try {
    const [tickersResponse, niftyResponse] = await Promise.all([
      api.get("/tickers"),
      api.get(`/stock/${encodeURIComponent("^NSEI")}`)
    ]);

    const niftyRecords = niftyResponse.data?.data || [];
    const lastFive = niftyRecords.slice(-5).map((entry) => ({
      label: entry.date || entry.Date,
      value: Number.parseFloat(entry.Close ?? entry["Adj Close"] ?? entry.close)
    }));

    if (tickersResponse.data?.tickers?.length) {
      const sliced = tickersResponse.data.tickers.slice(0, 4);
      return {
        topStocks: sliced.map((ticker, index) => ({
          ...topStocks[index % topStocks.length],
          ticker: ticker.replace(".NS", ""),
          name: ticker
        })),
        marketMetrics,
        overviewSeries: lastFive.length ? lastFive : overviewSeries
      };
    }
    return {
      topStocks,
      marketMetrics,
      overviewSeries: lastFive.length ? lastFive : overviewSeries
    };
  } catch (error) {
    await wait(300);
    return { topStocks, marketMetrics, overviewSeries };
  }
}

export async function fetchStockDetail(ticker) {
  try {
    const response = await api.get(`/stock/${encodeURIComponent(ticker)}`);
    const records = response.data?.data || [];
    const slice = records.slice(-30);
    const toNumber = (value) =>
      typeof value === "number" ? value : Number.parseFloat(value || 0);
    const series = slice.map((entry) => ({
      label: entry.date || entry.Date,
      actual:
        toNumber(entry.Close ?? entry["Adj Close"] ?? entry.close ?? entry.price)
    }));

    const latest = series[series.length - 1]?.actual || 0;

    return {
      ticker: response.data?.ticker || ticker,
      name: response.data?.ticker || ticker,
      price: latest,
      marketCap: "--",
      peRatio: "--",
      series: series.length ? series : detailSeries
    };
  } catch (error) {
    await wait(300);
    return {
      ticker,
      name: "Reliance Industries",
      price: 2856.4,
      marketCap: "₹19.3T",
      peRatio: 24.2,
      series: detailSeries
    };
  }
}

export async function fetchStockFull(ticker) {
  const [stockResponse, marketResponse, metricsResponse] = await Promise.all([
    api.get(`/stock/${encodeURIComponent(ticker)}`),
    api.get(`/market/info/${encodeURIComponent(ticker)}`),
    api.get(`/metrics/${encodeURIComponent(ticker)}`).catch(() => ({ data: null }))
  ]);
  const infoResponse = await api
    .get(`/stock/info/${encodeURIComponent(ticker)}`)
    .catch(() => ({ data: null }));

  const records = stockResponse.data?.data || [];
  const latest = records[records.length - 1] || {};
  return {
    ticker: stockResponse.data?.ticker || ticker,
    latest,
    records,
    marketInfo: marketResponse.data,
    metrics: metricsResponse.data,
    info: infoResponse.data
  };
}

export async function fetchIndiaTickers() {
  const response = await api.get("/india/tickers");
  return response.data?.stocks || [];
}

export async function fetchLocalTickers() {
  const response = await api.get("/data/tickers");
  return response.data?.tickers || [];
}

export async function trainModel(ticker, options = {}) {
  const response = await api.post("/train", { ticker, ...options });
  return response.data;
}

export async function refreshTickerData(ticker) {
  const response = await api.post(`/data/refresh/${encodeURIComponent(ticker)}?force=true`);
  return response.data;
}

export async function fetchTrainingStatus(ticker) {
  const response = await api.get(`/train/status/${encodeURIComponent(ticker)}`);
  return response.data;
}

export async function fetchPrediction(ticker) {
  try {
    const [predictedResponse, actualResponse] = await Promise.all([
      api.get(`/predict/${ticker}`),
      api.get(`/stock/${ticker}`)
    ]);

    const forecast = predictedResponse.data?.forecast || [];
    const actualRecords = actualResponse.data?.data || [];
    const toNumber = (value) =>
      typeof value === "number" ? value : Number.parseFloat(value || 0);

    const actualSlice = actualRecords.slice(-forecast.length);

    const series = forecast.map((item, index) => ({
      label: item.date,
      predicted: item.price,
      actual:
        toNumber(
          actualSlice[index]?.Close ??
            actualSlice[index]?.["Adj Close"] ??
            actualSlice[index]?.close
        )
    }));

    return {
      ticker: predictedResponse.data?.ticker || ticker,
      predictedPrice: forecast[forecast.length - 1]?.price || 0,
      confidence: 0.82,
      series: series.length ? series : predictionSeries
    };
  } catch (error) {
    await wait(300);
    return {
      ticker,
      predictedPrice: 1698.3,
      confidence: 0.82,
      series: predictionSeries
    };
  }
}
