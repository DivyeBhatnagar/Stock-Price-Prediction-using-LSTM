import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_ALPHA_VANTAGE_BASE_URL || "https://www.alphavantage.co"
});

const API_KEY = import.meta.env.VITE_ALPHA_VANTAGE_KEY;

const parseNumber = (value) => {
  const parsed = Number.parseFloat(value);
  return Number.isNaN(parsed) ? 0 : parsed;
};

export async function fetchAlphaVantageQuote(symbol) {
  if (!API_KEY) {
    throw new Error("Missing Alpha Vantage API key");
  }

  const response = await api.get("/query", {
    params: {
      function: "GLOBAL_QUOTE",
      symbol,
      apikey: API_KEY
    }
  });

  const quote = response.data?.["Global Quote"];
  if (!quote || !quote["05. price"]) {
    throw new Error("Invalid Alpha Vantage response");
  }

  return {
    symbol: quote["01. symbol"] || symbol,
    name: quote["01. symbol"] || symbol,
    price: parseNumber(quote["05. price"]),
    changePercent: parseNumber(quote["10. change percent"].replace("%", ""))
  };
}
