"""
tune_tabular.py
===============
Bayesian hyperparameter tuning for tabular direction models with a
strategy-aware objective (Sharpe) on walk-forward splits.
"""

import os
import sys
import json
import argparse
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from data_pipeline import build_pipeline, normalize_ticker, DEFAULT_START_DATE


def parse_args():
    p = argparse.ArgumentParser(description="Tune tabular model with Optuna")
    p.add_argument("--ticker", default="RELIANCE.NS")
    p.add_argument("--start", default=DEFAULT_START_DATE)
    p.add_argument("--window", type=int, default=60)
    p.add_argument("--horizon", type=int, default=1)
    p.add_argument("--split", type=float, default=0.85)
    p.add_argument("--trials", type=int, default=40)
    p.add_argument("--transaction-cost", type=float, default=0.0005)
    p.add_argument("--output", default="../backend/models")
    return p.parse_args()


def _purged_walk_forward_splits(n_samples: int, n_splits: int = 4, embargo: int = 5, min_train_size: int = 300):
    usable = max(0, n_samples - min_train_size - embargo)
    step = max(1, usable // max(1, n_splits + 1))
    splits = []
    train_end = min_train_size
    for _ in range(max(2, n_splits)):
        val_start = train_end + embargo
        val_end = min(n_samples, val_start + step)
        if val_start >= n_samples or (val_end - val_start) < 15:
            break
        splits.append((np.arange(0, train_end), np.arange(val_start, val_end)))
        train_end = val_end
    return splits


def _strategy_sharpe(prob, y_ret, threshold=0.55, cost=0.0005):
    pos = (prob >= threshold).astype(float)
    turns = np.abs(np.diff(np.r_[0.0, pos]))
    pnl = pos * y_ret - turns * float(cost)
    return float(np.mean(pnl) / (np.std(pnl) + 1e-12) * np.sqrt(252.0))


def tune(args):
    import optuna
    from sklearn.ensemble import HistGradientBoostingClassifier

    ticker = normalize_ticker(args.ticker)
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
    y_train = pipeline["y_train"].ravel().astype(int)
    y_ret_train = pipeline["y_return_train"].ravel().astype(float)
    X = X_train_seq[:, -1, :]

    splits = _purged_walk_forward_splits(len(X), n_splits=4, embargo=5, min_train_size=min(300, max(100, len(X)//2)))

    def objective(trial):
        lr = trial.suggest_float("learning_rate", 0.01, 0.2, log=True)
        depth = trial.suggest_int("max_depth", 2, 8)
        iters = trial.suggest_int("max_iter", 150, 900)
        l2 = trial.suggest_float("l2_regularization", 1e-3, 20.0, log=True)
        threshold = trial.suggest_float("threshold", 0.50, 0.70)

        fold_scores = []
        for tr_idx, val_idx in splits:
            model = HistGradientBoostingClassifier(
                learning_rate=lr,
                max_depth=depth,
                max_iter=iters,
                l2_regularization=l2,
                random_state=42,
            )
            model.fit(X[tr_idx], y_train[tr_idx])
            p = model.predict_proba(X[val_idx])[:, 1]
            s = _strategy_sharpe(p, y_ret_train[val_idx], threshold=threshold, cost=args.transaction_cost)
            fold_scores.append(s)

        return float(np.mean(fold_scores)) if fold_scores else -999.0

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=max(5, int(args.trials)))

    out_dir = os.path.join(os.path.abspath(args.output), ticker)
    os.makedirs(out_dir, exist_ok=True)
    report = {
        "ticker": ticker,
        "best_value_sharpe": float(study.best_value),
        "best_params": study.best_params,
        "trials": int(args.trials),
    }

    out_path = os.path.join(out_dir, "optuna_tuning_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[Tune] Saved report → {out_path}")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    args = parse_args()
    tune(args)
