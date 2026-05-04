"""
stack_ensemble.py
================
Simple stacking utility:
- loads trained LSTM and tabular models,
- creates probability features,
- trains logistic meta-learner,
- reports classification + trading metrics.
"""

import os
import sys
import json
import argparse
import numpy as np
import joblib

sys.path.insert(0, os.path.dirname(__file__))
from data_pipeline import build_pipeline, normalize_ticker, DEFAULT_START_DATE
from lstm_model import load_model


def parse_args():
    p = argparse.ArgumentParser(description="Stack LSTM + tabular models")
    p.add_argument("--ticker", default="RELIANCE.NS")
    p.add_argument("--start", default=DEFAULT_START_DATE)
    p.add_argument("--window", type=int, default=60)
    p.add_argument("--horizon", type=int, default=1)
    p.add_argument("--split", type=float, default=0.85)
    p.add_argument("--transaction-cost", type=float, default=0.0005)
    p.add_argument("--allow-short", action="store_true", default=False)
    p.add_argument("--model_dir", default="../backend/models")
    return p.parse_args()


def _strategy_metrics_from_positions(positions, future_log_returns, transaction_cost=0.0005):
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

    return {
        "strategy_total_return": float(equity[-1] - 1.0),
        "strategy_sharpe": float((mean_p / std_p) * np.sqrt(252.0)),
        "strategy_sortino": float((mean_p / downside_std) * np.sqrt(252.0)),
        "strategy_max_drawdown": float(np.max(drawdown)) if len(drawdown) else 0.0,
        "strategy_hit_rate": float(np.mean(pnl > 0)) if len(pnl) else 0.0,
    }


def _extract_lstm_prob(model, X):
    pred = model.predict(X, verbose=0)
    if isinstance(pred, (list, tuple)) and len(pred) > 1:
        return pred[1].ravel()
    if isinstance(pred, np.ndarray) and pred.ndim == 2 and pred.shape[1] == 1:
        return pred.ravel()
    # Regression fallback: map returns to pseudo-probability
    r = pred.ravel()
    return 1.0 / (1.0 + np.exp(-10.0 * r))


def run_stack(args):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import precision_recall_fscore_support, roc_auc_score

    ticker = normalize_ticker(args.ticker)
    ticker_dir = os.path.join(os.path.abspath(args.model_dir), ticker)
    lstm_path = os.path.join(ticker_dir, "model.keras")
    tabular_path = os.path.join(ticker_dir, "tabular_model.pkl")

    if not os.path.exists(lstm_path):
        raise FileNotFoundError(f"LSTM model not found: {lstm_path}")
    if not os.path.exists(tabular_path):
        raise FileNotFoundError(f"Tabular model not found: {tabular_path}")

    pipeline = build_pipeline(
        ticker=ticker,
        window_size=args.window,
        forecast_horizon=args.horizon,
        split_ratio=args.split,
        start_date=args.start,
        target_mode="direction",
        scale_method="robust",
    )

    X_train_seq = pipeline["X_train"]
    X_test_seq = pipeline["X_test"]
    y_train = pipeline["y_train"].ravel().astype(int)
    y_test = pipeline["y_test"].ravel().astype(int)
    y_ret_test = pipeline["y_return_test"].ravel().astype(float)

    lstm = load_model(lstm_path)
    tab = joblib.load(tabular_path)

    lstm_train_p = _extract_lstm_prob(lstm, X_train_seq)
    lstm_test_p = _extract_lstm_prob(lstm, X_test_seq)

    X_train_tab = X_train_seq[:, -1, :]
    X_test_tab = X_test_seq[:, -1, :]

    if hasattr(tab, "predict_proba"):
        tab_train_p = tab.predict_proba(X_train_tab)[:, 1]
        tab_test_p = tab.predict_proba(X_test_tab)[:, 1]
    else:
        tab_train_s = tab.decision_function(X_train_tab)
        tab_test_s = tab.decision_function(X_test_tab)
        tab_train_p = 1.0 / (1.0 + np.exp(-tab_train_s))
        tab_test_p = 1.0 / (1.0 + np.exp(-tab_test_s))

    S_train = np.c_[lstm_train_p, tab_train_p]
    S_test = np.c_[lstm_test_p, tab_test_p]

    meta = LogisticRegression(max_iter=1000, class_weight="balanced")
    meta.fit(S_train, y_train)
    p_test = meta.predict_proba(S_test)[:, 1]
    pred = (p_test >= 0.5).astype(int)

    acc = float(np.mean(pred == y_test))
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, pred, average="binary", zero_division=0)
    auc = float(roc_auc_score(y_test, p_test)) if len(np.unique(y_test)) > 1 else 0.5

    if args.allow_short:
        pos = np.where(p_test >= 0.55, 1.0, np.where(p_test <= 0.45, -1.0, 0.0))
    else:
        pos = (p_test >= 0.55).astype(float)
    strat = _strategy_metrics_from_positions(pos, y_ret_test, args.transaction_cost)

    report = {
        "ticker": ticker,
        "meta_model": "LogisticRegression",
        "accuracy": round(acc, 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(auc), 4),
        **{k: round(float(v), 6) for k, v in strat.items()},
    }

    out_path = os.path.join(ticker_dir, "stack_report.json")
    meta_path = os.path.join(ticker_dir, "stack_meta.pkl")
    joblib.dump(meta, meta_path)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[Stack] Saved meta model → {meta_path}")
    print(f"[Stack] Saved report → {out_path}")
    print(json.dumps(report, indent=2))

    return report


if __name__ == "__main__":
    args = parse_args()
    run_stack(args)
