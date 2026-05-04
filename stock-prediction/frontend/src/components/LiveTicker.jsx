import { formatCurrency, formatPercent } from "../utils/formatters.js";

export default function LiveTicker({ quotes }) {
  const items = quotes?.length ? quotes : [];
  const tickerItems = [...items, ...items];

  return (
    <div className="overflow-hidden border-b border-border bg-white">
      <div className="container-width">
        <div className="relative py-3">
          <div className="ticker-track flex items-center gap-6">
            {tickerItems.map((item, index) => {
              const isUp = item.changePercent >= 0;
              return (
                <div
                  key={`${item.symbol}-${index}`}
                  className="flex items-center gap-2 text-sm text-muted"
                >
                  <span className="font-semibold text-ink">{item.symbol}</span>
                  <span>{formatCurrency(item.price)}</span>
                  <span
                    className={`text-xs font-medium ${
                      isUp ? "text-emerald-600" : "text-rose-500"
                    }`}
                  >
                    {formatPercent(item.changePercent)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
