"""
tabular_baseline.py
===================
Train a strong tabular baseline for direction prediction using the same
feature pipeline as the LSTM system.

This is useful for:
- sanity-checking whether DL is actually helping,
- fast iteration on feature engineering,
- model stacking with sequence models.
"""

import os
import sys
import json
import argparse
import numpy as np
import joblib

sys.path.insert(0, os.path.dirname(__file__))
from data_pipeline import (
    build_pipeline,
    FEATURE_COLS,
    normalize_ticker,
    DEFAULT_START_DATE,
)


def parse_args():
    p = argparse.ArgumentParser(description="Train tabular baseline for direction prediction")
    p.add_argument("--ticker", default="RELIANCE.NS")
    p.add_argument("--start", default=DEFAULT_START_DATE)
    p.add_argument("--window", type=int, default=60)
    p.add_argument("--horizon", type=int, default=1)
    p.add_argument("--split", type=float, default=0.85)
    p.add_argument("--scale", choices=["minmax", "standard", "robust"], default="robust")
    p.add_argument("--direction-threshold", type=float, default=0.0)
    p.add_argument("--model", choices=["xgboost", "lightgbm", "rf", "histgb"], default="histgb")
    p.add_argument("--top-k-features", type=int, default=0,
                   help="If >0, select top-K features via mutual information")
    p.add_argument("--transaction-cost", type=float, default=0.0005)
    p.add_argument("--allow-short", action="store_true", default=False)
    p.add_argument("--strict-no-lookahead", action="store_true", default=False)
    p.add_argument("--output", default="../backend/models")
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


def _build_model(name: str):
    if name == "xgboost":
        try:
            from xgboost import XGBClassifier
            return XGBClassifier(
                n_estimators=500,
                learning_rate=0.03,
                max_depth=4,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_lambda=1.0,
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=42,
            )
        except Exception:
            pass

    if name == "lightgbm":
        try:
            from lightgbm import LGBMClassifier
            return LGBMClassifier(
                n_estimators=600,
                learning_rate=0.03,
                num_leaves=31,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_lambda=1.0,
                random_state=42,
            )
        except Exception:
            pass

    if name == "rf":
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(
            n_estimators=600,
            max_depth=8,
            min_samples_leaf=10,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )

    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(
        learning_rate=0.03,
        max_depth=5,
        max_iter=500,
        l2_regularization=1.0,
        random_state=42,
    )


def train_tabular(args):
    ticker = normalize_ticker(args.ticker)
    out_dir = os.path.abspath(args.output)
    ticker_dir = os.path.join(out_dir, ticker)
    os.makedirs(ticker_dir, exist_ok=True)

    pipeline = build_pipeline(
        ticker=ticker,
        window_size=args.window,
        forecast_horizon=args.horizon,
        split_ratio=args.split,
        start_date=args.start,
        target_mode="direction",
        direction_threshold=args.direction_threshold,
        scale_method=args.scale,
        strict_no_lookahead=args.strict_no_lookahead,
    )

    X_train_seq = pipeline["X_train"]
    X_test_seq = pipeline["X_test"]
    y_train = pipeline["y_train"].ravel().astype(int)
    y_test = pipeline["y_test"].ravel().astype(int)
    y_ret_test = pipeline["y_return_test"].ravel().astype(float)

    # Tabular representation: last timestep of each sequence.
    X_train = X_train_seq[:, -1, :]
    X_test = X_test_seq[:, -1, :]
    selected_features = FEATURE_COLS

    if args.top_k_features and args.top_k_features > 0:
        from sklearn.feature_selection import mutual_info_classif
        mi = mutual_info_classif(X_train, y_train, random_state=42)
        k = min(int(args.top_k_features), X_train.shape[1])
        idx = np.argsort(mi)[::-1][:k]
        X_train = X_train[:, idx]
        X_test = X_test[:, idx]
        selected_features = [FEATURE_COLS[int(i)] for i in idx]

    model = _build_model(args.model)
    model.fit(X_train, y_train)

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_test)[:, 1]
    else:
        score = model.decision_function(X_test)
        proba = 1.0 / (1.0 + np.exp(-score))

    pred = (proba >= 0.5).astype(int)

    from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
    acc = float(np.mean(pred == y_test))
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, pred, average="binary", zero_division=0)
    auc = float(roc_auc_score(y_test, proba)) if len(np.unique(y_test)) > 1 else 0.5

    if args.allow_short:
        positions = np.where(proba >= 0.55, 1.0, np.where(proba <= 0.45, -1.0, 0.0))
    else:
        positions = (proba >= 0.55).astype(float)
    strat = _strategy_metrics_from_positions(positions, y_ret_test, args.transaction_cost)

    report = {
        "ticker": ticker,
        "model": type(model).__name__,
        "n_features_used": int(X_train.shape[1]),
        "accuracy": round(acc, 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(auc), 4),
        "samples_test": int(len(y_test)),
        **{k: round(float(v), 6) for k, v in strat.items()},
    }

    # Feature importance (when available)
    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
        top_idx = np.argsort(imp)[::-1][:20]
        report["top_features"] = [
            {"feature": selected_features[int(i)], "importance": float(imp[int(i)])}
            for i in top_idx
        ]

    report["selected_features"] = selected_features

    model_path = os.path.join(ticker_dir, "tabular_model.pkl")
    report_path = os.path.join(ticker_dir, "tabular_report.json")
    joblib.dump(model, model_path)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[Tabular] Saved model → {model_path}")
    print(f"[Tabular] Saved report → {report_path}")
    print(json.dumps(report, indent=2))

    return report


if __name__ == "__main__":
    args = parse_args()
    train_tabular(args)
