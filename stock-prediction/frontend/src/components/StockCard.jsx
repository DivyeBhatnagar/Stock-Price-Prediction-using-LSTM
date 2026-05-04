import { formatCurrency, formatPercent } from "../utils/formatters.js";

export default function StockCard({ stock, onClick }) {
  const isUp = stock.changePercent >= 0;
  return (
    <div
      className="card card-hover p-5"
      role={onClick ? "button" : undefined}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted">{stock.symbol || stock.ticker}</p>
          <h3 className="text-lg font-semibold text-ink">
            {stock.name || stock.symbol}
          </h3>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
            isUp ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-500"
          }`}
        >
          {formatPercent(stock.changePercent)}
        </span>
      </div>
      <div className="mt-6 flex items-end justify-between">
        <div>
          <p className="text-xs text-muted">Price</p>
          <p className="text-xl font-semibold text-ink">
            {formatCurrency(stock.price)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted">Volume</p>
          <p className="text-sm font-medium text-ink">
            {stock.volume || "—"}
          </p>
        </div>
      </div>
    </div>
  );
}
