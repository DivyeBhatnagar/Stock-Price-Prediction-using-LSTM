"""
evaluate.py
===========
Standalone evaluation module — load a saved model and produce a
comprehensive report with metrics + plots.

Usage
-----
    python evaluate.py --ticker AAPL
"""

import os, sys, json, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib

sys.path.insert(0, os.path.dirname(__file__))
from data_pipeline import (
    build_pipeline, FEATURE_COLS, LOG_RETURN_COL_IDX, inverse_transform_close,
    normalize_ticker, get_currency_symbol, DEFAULT_START_DATE,
)
from lstm_model import load_model


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--ticker",    default="RELIANCE.NS")
    p.add_argument("--window",    type=int, default=60)
    p.add_argument("--horizon",   type=int, default=1)
    p.add_argument("--model_dir", default="../backend/models")
    p.add_argument("--start",     default=DEFAULT_START_DATE)
    p.add_argument("--transaction-cost", type=float, default=0.0005)
    p.add_argument("--allow-short", action="store_true", default=False)
    p.add_argument("--strict-no-lookahead", action="store_true", default=False)
    return p.parse_args()


def _strategy_metrics_from_positions(positions: np.ndarray, future_log_returns: np.ndarray, transaction_cost: float = 0.0005):
    positions = np.asarray(positions, dtype=float).reshape(-1)
    future_log_returns = np.asarray(future_log_returns, dtype=float).reshape(-1)
    m = min(len(positions), len(future_log_returns))
    positions = positions[:m]
    future_log_returns = future_log_returns[:m]

    turns = np.abs(np.diff(np.r_[0.0, positions]))
    pnl = positions * future_log_returns - turns * float(transaction_cost)
    equity = np.exp(np.cumsum(pnl)) if len(pnl) else np.array([1.0])

    mean_p = float(np.mean(pnl)) if len(pnl) else 0.0
    std_p = float(np.std(pnl) + 1e-12)
    downside = pnl[pnl < 0]
    downside_std = float(np.std(downside) + 1e-12) if len(downside) else 1e-12
    running_max = np.maximum.accumulate(equity)
    drawdown = 1.0 - (equity / (running_max + 1e-12))
    max_dd = float(np.max(drawdown)) if len(drawdown) else 0.0

    return {
        "strategy_total_return": float(equity[-1] - 1.0),
        "strategy_sharpe": float((mean_p / std_p) * np.sqrt(252.0)),
        "strategy_sortino": float((mean_p / downside_std) * np.sqrt(252.0)),
        "strategy_max_drawdown": max_dd,
        "strategy_hit_rate": float(np.mean(pnl > 0)) if len(pnl) else 0.0,
    }


def full_evaluation(
    ticker,
    window=60,
    horizon=1,
    model_dir="../backend/models",
    start="2015-01-01",
    transaction_cost=0.0005,
    allow_short=False,
    strict_no_lookahead=False,
):
    """Load model + scaler, rebuild test set, return comprehensive report."""
    ticker = normalize_ticker(ticker)
    ticker_dir  = os.path.join(os.path.abspath(model_dir), ticker)
    model_path  = os.path.join(ticker_dir, "model.keras")
    scaler_path = os.path.join(ticker_dir, "scaler.pkl")
    config_path = os.path.join(ticker_dir, "config.json")

    # Load config
    with open(config_path) as f:
        config = json.load(f)
    window  = config.get("window_size",  window)
    horizon = config.get("forecast_horizon", horizon)

    # Rebuild dataset
    pipeline = build_pipeline(
        ticker=ticker, window_size=window,
        forecast_horizon=horizon, start_date=start,
        scaler_save_path=scaler_path,
        strict_no_lookahead=strict_no_lookahead,
    )
    X_test, y_test = pipeline["X_test"], pipeline["y_test"]
    y_return_test  = pipeline.get("y_return_test")
    scaler         = pipeline["scaler"]
    test_prev_closes = pipeline.get("test_prev_closes")
    n_features     = X_test.shape[2]

    # Load model
    model = load_model(model_path)

    # Predict
    y_pred_raw = model.predict(X_test, verbose=0)
    if isinstance(y_pred_raw, (list, tuple)):
        y_pred_sc = y_pred_raw[0]
        y_pred_prob = y_pred_raw[1].ravel()
    else:
        y_pred_sc = y_pred_raw
        y_pred_prob = None

    y_pred_lr = inverse_transform_close(scaler, y_pred_sc, LOG_RETURN_COL_IDX, n_features)
    y_true_lr = inverse_transform_close(scaler, y_test,    LOG_RETURN_COL_IDX, n_features)

    if test_prev_closes is not None and len(test_prev_closes) == len(y_pred_lr):
        y_pred = test_prev_closes * np.exp(y_pred_lr)
        y_true = test_prev_closes * np.exp(y_true_lr)
    else:
        y_pred = np.exp(np.cumsum(y_pred_lr))
        y_true = np.exp(np.cumsum(y_true_lr))

    # Metrics
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, precision_recall_fscore_support, roc_auc_score
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae  = float(mean_absolute_error(y_true, y_pred))
    mape = float(np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + 1e-10))) * 100)
    r2   = float(r2_score(y_true, y_pred))
    y_true_dir = (y_true_lr.ravel() >= 0).astype(int)
    if y_pred_prob is not None:
        y_pred_dir = (y_pred_prob >= 0.5).astype(int)
        auc = float(roc_auc_score(y_true_dir, y_pred_prob)) if len(np.unique(y_true_dir)) > 1 else 0.5
    else:
        y_pred_dir = (y_pred_lr.ravel() >= 0).astype(int)
        y_pred_prob = 1.0 / (1.0 + np.exp(-10.0 * y_pred_lr.ravel()))
        auc = float(roc_auc_score(y_true_dir, y_pred_prob)) if len(np.unique(y_true_dir)) > 1 else 0.5

    precision, recall, f1, _ = precision_recall_fscore_support(y_true_dir, y_pred_dir, average="binary", zero_division=0)
    da = float(np.mean(y_true_dir == y_pred_dir))

    realized_lr = y_return_test.ravel() if y_return_test is not None else y_true_lr.ravel()
    if allow_short:
        positions = np.where(y_pred_prob >= 0.55, 1.0, np.where(y_pred_prob <= 0.45, -1.0, 0.0))
    else:
        positions = (y_pred_prob >= 0.55).astype(float)
    strat = _strategy_metrics_from_positions(positions, realized_lr, transaction_cost=transaction_cost)

    report = {
        "ticker": ticker,
        "rmse":  round(rmse, 4),
        "mae":   round(mae,  4),
        "mape":  round(mape, 4),
        "r2":    round(r2,   4),
        "directional_accuracy": round(da, 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(auc), 4),
        "test_samples": len(y_true),
        **{k: round(float(v), 6) for k, v in strat.items()},
    }

    # Save evaluation plot
    _plot_eval(y_true, y_pred, ticker, ticker_dir)

    return report, y_true.tolist(), y_pred.tolist()


def _plot_eval(y_true, y_pred, ticker, save_dir):
    currency = get_currency_symbol(ticker)
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    fig.suptitle(f"{ticker} — Evaluation Report", fontsize=15, fontweight="bold")

    # Line plot
    axes[0].plot(y_true, label="Actual",    color="#1976D2", lw=1.5)
    axes[0].plot(y_pred, label="Predicted", color="#E53935", lw=1.5, alpha=0.85)
    axes[0].set_title("Actual vs Predicted Prices")
    axes[0].set_ylabel(f"Price ({currency})")
    axes[0].legend(); axes[0].grid(True, alpha=0.3)

    # Residual plot
    residuals = np.array(y_true) - np.array(y_pred)
    axes[1].bar(range(len(residuals)), residuals, color="#7B1FA2", alpha=0.6, width=0.8)
    axes[1].axhline(0, color="black", linewidth=0.8)
    axes[1].set_title("Residuals (Actual − Predicted)")
    axes[1].set_xlabel("Test Sample")
    axes[1].set_ylabel(f"Error ({currency})")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(save_dir, "evaluation.png")
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"[Eval] Plot saved → {path}")


if __name__ == "__main__":
    args   = parse_args()
    report, _, _ = full_evaluation(
        args.ticker, args.window, args.horizon, args.model_dir, args.start,
        transaction_cost=args.transaction_cost,
        allow_short=args.allow_short,
        strict_no_lookahead=args.strict_no_lookahead,
    )
    print("\n📊 Evaluation Report")
    print(json.dumps(report, indent=2))
