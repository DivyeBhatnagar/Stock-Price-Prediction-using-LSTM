// currency.js  —  Currency detection and formatting for Indian (INR) / US (USD) markets

/**
 * Determine if a ticker belongs to the Indian market.
 * Indian tickers: end with .NS / .BO, or are Indian indices (^NSEI, ^NSEBANK, ^BSESN),
 * or are bare known NSE symbols.
 */

const INDIAN_BARE_SYMBOLS = new Set([
  "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "ITC", "LT",
  "BHARTIARTL", "AXISBANK", "KOTAKBANK", "WIPRO", "HCLTECH", "MARUTI",
  "TATASTEEL", "SUNPHARMA", "BAJFINANCE", "ADANIENT",
  "POWERGRID", "NTPC", "ONGC", "ULTRACEMCO", "TITAN", "ASIANPAINT",
  "HINDUNILVR", "BAJAJFINSV", "TECHM", "JSWSTEEL", "DRREDDY",
]);

const INDIAN_INDICES = new Set(["^NSEI", "^NSEBANK", "^BSESN"]);

export function isIndianTicker(ticker) {
  if (!ticker) return false;
  const t = ticker.toUpperCase().trim();
  return (
    t.endsWith(".NS") ||
    t.endsWith(".BO") ||
    INDIAN_INDICES.has(t) ||
    INDIAN_BARE_SYMBOLS.has(t)
  );
}

/**
 * Get currency symbol: "₹" for Indian tickers, "$" for others.
 */
export function getCurrencySymbol(ticker) {
  return isIndianTicker(ticker) ? "₹" : "$";
}

/**
 * Get currency code: "INR" or "USD".
 */
export function getCurrencyCode(ticker) {
  return isIndianTicker(ticker) ? "INR" : "USD";
}

/**
 * Format a price with the correct currency symbol.
 * @param {number} price
 * @param {string} ticker
 * @param {number} decimals — default 2
 * @returns {string} e.g. "₹2,456.78" or "$185.32"
 */
export function formatPrice(price, ticker, decimals = 2) {
  const sym = getCurrencySymbol(ticker);
  const val = Number(price);
  if (isNaN(val)) return `${sym}—`;

  if (isIndianTicker(ticker)) {
    // Indian numbering: 1,23,456.78
    return sym + formatIndianNumber(val, decimals);
  }
  return sym + val.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format number in Indian numbering system (lakhs/crores).
 * e.g. 1234567.89 → "12,34,567.89"
 */
function formatIndianNumber(num, decimals = 2) {
  const [intPart, decPart] = Math.abs(num).toFixed(decimals).split(".");
  const sign = num < 0 ? "-" : "";

  if (intPart.length <= 3) {
    return sign + intPart + (decPart ? "." + decPart : "");
  }

  // Last 3 digits
  const last3 = intPart.slice(-3);
  let rest = intPart.slice(0, -3);

  // Group remaining digits in pairs (Indian system: lakhs, crores)
  const groups = [];
  while (rest.length > 0) {
    groups.unshift(rest.slice(-2));
    rest = rest.slice(0, -2);
  }

  return sign + groups.join(",") + "," + last3 + (decPart ? "." + decPart : "");
}

/**
 * Auto-convert a bare Indian ticker to NSE format.
 * "RELIANCE" → "RELIANCE.NS"  |  "AAPL" → "AAPL" (unchanged)
 */
export function autoConvertTicker(ticker) {
  if (!ticker) return ticker;
  const t = ticker.toUpperCase().trim();
  if (t.endsWith(".NS") || t.endsWith(".BO") || t.startsWith("^")) return t;
  if (INDIAN_BARE_SYMBOLS.has(t)) return `${t}.NS`;
  return t;
}
