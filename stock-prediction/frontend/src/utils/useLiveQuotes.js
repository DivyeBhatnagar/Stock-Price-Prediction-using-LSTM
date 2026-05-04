import { useEffect, useMemo, useRef, useState } from "react";
import { fetchAlphaVantageQuote } from "../services/alphaVantage.js";
import { topStocks } from "../data/dummyData.js";

const DEFAULT_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"];
const FALLBACK_QUOTES = topStocks.map((stock) => ({
  symbol: stock.ticker,
  name: stock.name,
  price: stock.price,
  changePercent: stock.changePercent
}));

const clampInterval = (value) => Math.max(12000, value || 12000);

export function useLiveQuotes({ symbols = DEFAULT_SYMBOLS, intervalMs = 15000 }) {
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const pointerRef = useRef(0);
  const latestRef = useRef({});

  const uniqueSymbols = useMemo(
    () => Array.from(new Set(symbols.map((s) => s.toUpperCase()))),
    [symbols]
  );

  const hydrateFromFallback = () => {
    setQuotes(FALLBACK_QUOTES);
  };

  const updateQuote = async (symbol) => {
    try {
      const data = await fetchAlphaVantageQuote(symbol);
      latestRef.current[symbol] = data;
      setQuotes((prev) => {
        const others = prev.filter((item) => item.symbol !== symbol);
        return [...others, data];
      });
    } catch (err) {
      setError("Live pricing is temporarily unavailable.");
      hydrateFromFallback();
    }
  };

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    const boot = async () => {
      const initialSymbols = uniqueSymbols.slice(0, 3);
      try {
        await Promise.all(initialSymbols.map((symbol) => updateQuote(symbol)));
        if (mounted) {
          setLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setLoading(false);
          setError("Live pricing is temporarily unavailable.");
          hydrateFromFallback();
        }
      }
    };

    boot();

    const interval = setInterval(() => {
      const currentSymbol = uniqueSymbols[pointerRef.current % uniqueSymbols.length];
      pointerRef.current += 1;
      updateQuote(currentSymbol);
    }, clampInterval(intervalMs));

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [uniqueSymbols, intervalMs]);

  useEffect(() => {
    if (!quotes.length && Object.keys(latestRef.current).length) {
      setQuotes(Object.values(latestRef.current));
    }
  }, [quotes.length]);

  return {
    quotes: quotes.length ? quotes : FALLBACK_QUOTES,
    loading,
    error
  };
}
