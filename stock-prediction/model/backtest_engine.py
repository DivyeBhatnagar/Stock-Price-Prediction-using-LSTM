"""
backtest_engine.py
==================
Unified backtest engine with portfolio-level risk management:
- Volatility targeting
- Position sizing with max exposure caps
- Multi-asset correlation control
- Stop-loss / take-profit logic
- Portfolio-level drawdown control
"""

import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, os.path.dirname(__file__))
from data_pipeline import build_pipeline, normalize_ticker, DEFAULT_START_DATE
from lstm_model import load_model
from risk_manager import RiskManager, calculate_position_sizes


def parse_args():
    p = argparse.ArgumentParser(description="Run portfolio backtest with risk management")
    p.add_argument("--tickers", nargs="+", default=["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS"])
    p.add_argument("--start", default="2018-01-01")
    p.add_argument("--end", default=None)
    p.add_argument("--window", type=int, default=60)
    p.add_argument("--horizon", type=int, default=1)
    p.add_argument("--model-dir", default="../backend/models")
    p.add_argument("--transaction-cost", type=float, default=0.0005)
    p.add_argument("--slippage", type=float, default=0.0002)
    p.add_argument("--target-vol", type=float, default=0.15)
    p.add_argument("--max-position", type=float, default=0.20)
    p.add_argument("--max-leverage", type=float, default=1.5)
    p.add_argument("--stop-loss", type=float, default=0.08)
    p.add_argument("--take-profit", type=float, default=0.12)
    p.add_argument("--max-drawdown", type=float, default=0.25)
    p.add_argument("--corr-threshold", type=float, default=0.7)
    p.add_argument("--signal-buy-threshold", type=float, default=0.55)
    p.add_argument("--signal-sell-threshold", type=float, default=0.45)
    p.add_argument("--min-trade-change", type=float, default=0.01)
    p.add_argument("--vol-window", type=int, default=20)
    p.add_argument("--rebalance-days", type=int, default=5)
    p.add_argument("--strict-no-lookahead", action="store_true", default=False)
    p.add_argument("--output", default="../backtest_results")
    return p.parse_args()


def load_model_predictions(
    ticker: str,
    model_dir: str,
    start_date: str,
    window: int,
    horizon: int,
    strict_no_lookahead: bool = False,
) -> Tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    """Load model and return aligned probabilities, realized returns, and dates."""
    ticker = normalize_ticker(ticker)
    ticker_dir = os.path.join(os.path.abspath(model_dir), ticker)

    model_path = os.path.join(ticker_dir, "model.keras")
    scaler_path = os.path.join(ticker_dir, "scaler.pkl")
    config_path = os.path.join(ticker_dir, "config.json")

    if not all(os.path.exists(p) for p in [model_path, scaler_path, config_path]):
        raise FileNotFoundError(f"Model files not found for {ticker}")

    with open(config_path) as f:
        config = json.load(f)

    pipeline = build_pipeline(
        ticker=ticker,
        window_size=window,
        forecast_horizon=horizon,
        start_date=start_date,
        target_mode="direction",
        scale_method=config.get("scale_method", "minmax"),
        strict_no_lookahead=strict_no_lookahead,
    )
    
    X_test = pipeline["X_test"]
    y_return_test = pipeline["y_return_test"].ravel()
    df_feat = pipeline["df_featured"]
    n_train = len(pipeline["X_train"])
    base_offset = window + n_train
    dates = df_feat.index[base_offset: base_offset + len(X_test)]

    model = load_model(model_path)
    preds = model.predict(X_test, verbose=0)

    if isinstance(preds, (list, tuple)) and len(preds) > 1:
        probs = preds[1].ravel()
    else:
        raw = preds.ravel()
        probs = 1.0 / (1.0 + np.exp(-8.0 * raw))

    return probs, y_return_test, dates


def _cap_gross_exposure(weights: Dict[str, float], max_leverage: float) -> Dict[str, float]:
    """Scale weights so gross exposure does not exceed max leverage."""
    gross = float(sum(abs(v) for v in weights.values()))
    if gross <= max_leverage or gross <= 1e-12:
        return weights
    scale = max_leverage / gross
    return {k: float(v * scale) for k, v in weights.items()}


def _series_to_common_dates(
    probs: np.ndarray,
    realized_returns: np.ndarray,
    dates: pd.DatetimeIndex,
    common_dates: pd.DatetimeIndex,
) -> Tuple[np.ndarray, np.ndarray]:
    """Align ticker arrays to common date index."""
    s_prob = pd.Series(probs, index=dates)
    s_ret = pd.Series(realized_returns, index=dates)
    a_prob = s_prob.reindex(common_dates).dropna()
    a_ret = s_ret.reindex(common_dates).dropna()
    idx = a_prob.index.intersection(a_ret.index)
    return a_prob.reindex(idx).values, a_ret.reindex(idx).values


def run_portfolio_backtest(args) -> Dict:
    """Run complete multi-asset backtest with portfolio risk sizing."""
    os.makedirs(args.output, exist_ok=True)

    rm = RiskManager(
        target_vol=args.target_vol,
        max_position=args.max_position,
        max_leverage=args.max_leverage,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        max_drawdown=args.max_drawdown,
        corr_threshold=args.corr_threshold,
    )

    # Load predictions for all tickers
    ticker_data = {}
    for ticker in args.tickers:
        try:
            probs, returns, dates = load_model_predictions(
                ticker,
                args.model_dir,
                args.start,
                args.window,
                args.horizon,
                strict_no_lookahead=args.strict_no_lookahead,
            )
            ticker_data[ticker] = {
                "probs": probs,
                "returns": returns,
                "dates": dates
            }
        except Exception as e:
            print(f"Skipping {ticker}: {e}")

    if not ticker_data:
        raise ValueError("No valid ticker data found")

    # Align all series to common dates
    common_dates = pd.DatetimeIndex(sorted(set.intersection(*[set(data["dates"]) for data in ticker_data.values()])))
    if len(common_dates) < max(40, args.vol_window + 2):
        raise ValueError("Insufficient overlapping dates across tickers for backtest")

    aligned = {}
    final_dates = common_dates
    for ticker, data in ticker_data.items():
        p, r = _series_to_common_dates(data["probs"], data["returns"], data["dates"], common_dates)
        aligned[ticker] = {"probs": p, "returns": r}
        final_dates = final_dates[:len(p)] if len(final_dates) > len(p) else final_dates

    # force all aligned arrays to same length by reindexing to final_dates
    matrix_returns = {}
    matrix_probs = {}
    for ticker, data in ticker_data.items():
        s_p = pd.Series(data["probs"], index=data["dates"]).reindex(final_dates)
        s_r = pd.Series(data["returns"], index=data["dates"]).reindex(final_dates)
        if s_p.isna().any() or s_r.isna().any():
            continue
        matrix_probs[ticker] = s_p.values
        matrix_returns[ticker] = s_r.values

    if not matrix_returns:
        raise ValueError("No fully aligned ticker time series for backtest")

    tickers = sorted(matrix_returns.keys())
    ret_df = pd.DataFrame({t: matrix_returns[t] for t in tickers}, index=final_dates)
    prob_df = pd.DataFrame({t: matrix_probs[t] for t in tickers}, index=final_dates)

    # Portfolio state
    current_weights = {t: 0.0 for t in tickers}
    entry_cumret = {t: 0.0 for t in tickers}
    equity = [1.0]
    peak_equity = 1.0
    daily_net_returns: List[float] = []
    trades: List[dict] = []
    weights_records: List[dict] = []

    for i, dt in enumerate(ret_df.index):
        if i < args.vol_window:
            continue

        # Apply PnL from previous holdings on today's realized returns
        today_ret = ret_df.iloc[i]
        gross_port_ret = float(sum(current_weights[t] * float(today_ret[t]) for t in tickers))

        # Update per-position cumulative return (for stop/take-profit)
        for t in tickers:
            if abs(current_weights[t]) > 1e-8:
                signed_ret = float(np.sign(current_weights[t]) * today_ret[t])
                entry_cumret[t] = (1.0 + entry_cumret[t]) * (1.0 + signed_ret) - 1.0
            else:
                entry_cumret[t] = 0.0

        # Signal generation
        probs = prob_df.iloc[i]
        signals = {}
        for t in tickers:
            p = float(probs[t])
            if p >= args.signal_buy_threshold:
                signals[t] = 1.0
            elif p <= args.signal_sell_threshold:
                signals[t] = -1.0
            else:
                signals[t] = 0.0

        # Stop-loss / take-profit override
        for t in tickers:
            if abs(current_weights[t]) > 1e-8:
                if entry_cumret[t] <= -abs(args.stop_loss):
                    signals[t] = 0.0
                elif entry_cumret[t] >= abs(args.take_profit):
                    signals[t] = 0.0

        # Rebalance schedule
        do_rebalance = ((i - args.vol_window) % max(1, args.rebalance_days) == 0)
        trade_cost_ret = 0.0
        if do_rebalance:
            hist = ret_df.iloc[max(0, i - args.vol_window):i]
            recent_vols = {t: float(np.std(hist[t].values) * np.sqrt(252.0) + 1e-8) for t in tickers}
            corr = hist.corr() if len(hist) > 5 else None

            target_weights = calculate_position_sizes(
                signals=signals,
                volatilities=recent_vols,
                correlations=corr,
                target_vol=args.target_vol,
                max_position=args.max_position,
            )
            target_weights = _cap_gross_exposure(target_weights, args.max_leverage)

            # drawdown-aware scaling
            dd_scale = rm.update_drawdown(equity[-1], peak_equity)
            target_weights = {t: float(w * dd_scale) for t, w in target_weights.items()}

            # Execute weight changes
            turnover = 0.0
            for t in tickers:
                new_w = float(target_weights.get(t, 0.0))
                old_w = float(current_weights.get(t, 0.0))
                delta = new_w - old_w
                if abs(delta) < args.min_trade_change:
                    continue
                turnover += abs(delta)
                current_weights[t] = new_w
                trades.append({
                    "date": str(dt.date()),
                    "ticker": t,
                    "old_weight": old_w,
                    "new_weight": new_w,
                    "delta": delta,
                })

                # reset entry tracker when position flips/opens/closes
                if np.sign(old_w) != np.sign(new_w) or abs(new_w) < 1e-8:
                    entry_cumret[t] = 0.0

            trade_cost_ret = turnover * (args.transaction_cost + args.slippage)

        # Net return and equity update
        net_ret = gross_port_ret - trade_cost_ret
        new_equity = float(equity[-1] * (1.0 + net_ret))
        equity.append(new_equity)
        peak_equity = max(peak_equity, new_equity)
        daily_net_returns.append(net_ret)

        weights_records.append({
            "date": str(dt.date()),
            **{f"w_{t}": float(current_weights[t]) for t in tickers},
            "gross_exposure": float(sum(abs(current_weights[t]) for t in tickers)),
            "net_exposure": float(sum(current_weights[t] for t in tickers)),
            "portfolio_return": net_ret,
            "equity": new_equity,
        })

        if rm.should_stop_trading():
            print(f"Stopped at {dt.date()}: max drawdown breached")
            break

    # Metrics
    eq = np.array(equity)
    rets = np.array(daily_net_returns) if daily_net_returns else np.array([0.0])
    downside = rets[rets < 0]
    total_return = float(eq[-1] - 1.0)
    ann_return = float((eq[-1]) ** (252.0 / max(1.0, len(rets))) - 1.0)
    sharpe = float(np.mean(rets) / (np.std(rets) + 1e-12) * np.sqrt(252.0))
    sortino = float(np.mean(rets) / (np.std(downside) + 1e-12) * np.sqrt(252.0))

    running_max = np.maximum.accumulate(eq)
    drawdowns = 1.0 - (eq / (running_max + 1e-12))
    max_dd = float(np.max(drawdowns)) if len(drawdowns) else 0.0
    hit_rate = float(np.mean(rets > 0)) if len(rets) else 0.0

    report = {
        "tickers": tickers,
        "period": f"{str(ret_df.index[0].date())} to {str(ret_df.index[-1].date())}",
        "total_return": float(total_return),
        "annualized_return": ann_return,
        "sharpe_ratio": float(sharpe),
        "sortino_ratio": float(sortino),
        "max_drawdown": max_dd,
        "final_equity": float(eq[-1]),
        "hit_rate": hit_rate,
        "total_trades": len(trades),
        "avg_daily_turnover": float(np.mean(np.abs(np.diff(eq) / (eq[:-1] + 1e-12))) if len(eq) > 1 else 0.0),
        "total_costs": float(sum(abs(t["delta"]) for t in trades) * (args.transaction_cost + args.slippage)),
        "risk_parameters": {
            "target_vol": args.target_vol,
            "max_position": args.max_position,
            "max_leverage": args.max_leverage,
            "stop_loss": args.stop_loss,
            "take_profit": args.take_profit,
            "max_drawdown": args.max_drawdown,
            "corr_threshold": args.corr_threshold,
            "rebalance_days": args.rebalance_days,
        },
        "risk_state": rm.get_risk_report(),
    }

    # Save results
    result_path = os.path.join(args.output, "portfolio_backtest_report.json")
    with open(result_path, "w") as f:
        json.dump(report, f, indent=2)

    equity_path = os.path.join(args.output, "equity_curve.csv")
    eq_dates = [str(d.date()) for d in ret_df.index[:len(eq)-1]]
    pd.DataFrame({"date": [str(ret_df.index[0].date())] + eq_dates, "equity": eq}).to_csv(equity_path, index=False)

    w_path = os.path.join(args.output, "weights_timeseries.csv")
    pd.DataFrame(weights_records).to_csv(w_path, index=False)

    t_path = os.path.join(args.output, "trades.csv")
    pd.DataFrame(trades).to_csv(t_path, index=False)

    print(f"Backtest complete. Results saved to {args.output}")
    print(json.dumps(report, indent=2))

    return report


def main():
    args = parse_args()
    run_portfolio_backtest(args)


if __name__ == "__main__":
    main()