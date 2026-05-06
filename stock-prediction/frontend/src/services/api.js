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
    const today = new Date();
    const tenYearsAgo = new Date(today);
    tenYearsAgo.setFullYear(today.getFullYear() - 10);
    const startDate = tenYearsAgo.toISOString().slice(0, 10);

    const [tickersResponse, niftyResponse, metricsResponse] = await Promise.all([
      api.get("/tickers"),
      api.get(`/stock/${encodeURIComponent("^NSEI")}`, {
        params: {
          start: startDate,
          indicators: false
        }
      }),
      api.get("/market/metrics").catch(() => ({ data: null }))
    ]);

    const niftyRecords = niftyResponse.data?.data || [];
    const parsed = niftyRecords
      .map((entry) => {
        const date = entry.date || entry.Date;
        const value = Number.parseFloat(
          entry.Close ?? entry["Adj Close"] ?? entry.close
        );
        return {
          date,
          value,
          ts: date ? Date.parse(date) : NaN
        };
      })
      .filter((item) => Number.isFinite(item.ts) && Number.isFinite(item.value))
      .sort((a, b) => a.ts - b.ts);

    const monthlyMap = new Map();
    parsed.forEach((item) => {
      const monthKey = item.date.slice(0, 7); // YYYY-MM
      monthlyMap.set(monthKey, item); // keep latest entry per month
    });

    const tenYearSeries = Array.from(monthlyMap.values()).map((item) => ({
      label: item.date,
      value: item.value
    }));

    const liveMetrics = metricsResponse.data?.metrics?.length
      ? metricsResponse.data.metrics
      : marketMetrics;

    if (tickersResponse.data?.tickers?.length) {
      const sliced = tickersResponse.data.tickers.slice(0, 4);
      return {
        topStocks: sliced.map((ticker, index) => ({
          ...topStocks[index % topStocks.length],
          ticker: ticker.replace(".NS", ""),
          name: ticker
        })),
        marketMetrics: liveMetrics,
        overviewSeries: tenYearSeries.length ? tenYearSeries : overviewSeries
      };
    }
    return {
      topStocks,
      marketMetrics: liveMetrics,
      overviewSeries: tenYearSeries.length ? tenYearSeries : overviewSeries
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

    const toDateKey = (value) => {
      if (!value) return "";
      const parsed = new Date(value);
      if (Number.isNaN(parsed.getTime())) return String(value).slice(0, 10);
      return parsed.toISOString().slice(0, 10);
    };

    const actualByDate = new Map(
      actualRecords.map((record) => {
        const date = toDateKey(record.date || record.Date);
        const price = toNumber(
          record.Close ?? record["Adj Close"] ?? record.close
        );
        return [date, price];
      })
    );

    const series = forecast.map((item) => {
      const dateKey = toDateKey(item.date);
      const actual = actualByDate.has(dateKey) ? actualByDate.get(dateKey) : null;
      return {
        label: item.date,
        predicted: item.price,
        actual
      };
    });

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

const rangeToStartDate = (range) => {
  const now = new Date();
  if (range.endsWith("D")) {
    const days = Number.parseInt(range.replace("D", ""), 10);
    const start = new Date(now);
    start.setDate(now.getDate() - days);
    return start.toISOString().slice(0, 10);
  }
  if (range.endsWith("Y")) {
    const years = Number.parseInt(range.replace("Y", ""), 10);
    const start = new Date(now.getFullYear() - years, now.getMonth(), now.getDate());
    return start.toISOString().slice(0, 10);
  }
  if (range.endsWith("M")) {
    const months = Number.parseInt(range.replace("M", ""), 10);
    const start = new Date(now.getFullYear(), now.getMonth() - months, now.getDate());
    return start.toISOString().slice(0, 10);
  }
  return undefined;
};

const downsampleMonthly = (records) => {
  const parsed = records
    .map((entry) => {
      const date = entry.date || entry.Date;
      const value = Number.parseFloat(
        entry.Close ?? entry["Adj Close"] ?? entry.close
      );
      return {
        date,
        value,
        ts: date ? Date.parse(date) : NaN
      };
    })
    .filter((item) => Number.isFinite(item.ts) && Number.isFinite(item.value))
    .sort((a, b) => a.ts - b.ts);

  const monthlyMap = new Map();
  parsed.forEach((item) => {
    const monthKey = item.date.slice(0, 7); // YYYY-MM
    monthlyMap.set(monthKey, item); // keep latest entry per month
  });

  return Array.from(monthlyMap.values()).map((item) => ({
    label: item.date,
    value: item.value
  }));
};

export async function fetchPriceHistory(ticker, range = "1Y") {
  try {
    const startDate =
      range === "1D" ? rangeToStartDate("10D") : rangeToStartDate(range);
    const response = await api.get(`/stock/${encodeURIComponent(ticker)}`, {
      params: {
        start: startDate,
        indicators: false
      }
    });

    const records = response.data?.data || [];
    let series = records.map((entry) => ({
      label: entry.date || entry.Date,
      value: Number.parseFloat(
        entry.Close ?? entry["Adj Close"] ?? entry.close
      )
    }));

    if (range === "1D" && series.length > 2) {
      series = series.slice(-2);
    }

    const years = range.endsWith("Y")
      ? Number.parseInt(range.replace("Y", ""), 10)
      : 0;
    if (years >= 5) {
      series = downsampleMonthly(records);
    }

    const lastDate = records.length
      ? records[records.length - 1].date || records[records.length - 1].Date
      : null;

    return {
      ticker: response.data?.ticker || ticker,
      series,
      lastDate
    };
  } catch (error) {
    await wait(300);
    return { ticker, series: [], lastDate: null };
  }
}
