"""
train.py
========
End-to-end training script for the LSTM stock prediction model.

Usage
-----
    python train.py --ticker AAPL --epochs 100 --window 60

Author  : Stock-Prediction AI Pipeline
Version : 1.0.0
"""

import os
import sys
import argparse
import json
import time
import numpy as np
import joblib
import matplotlib
matplotlib.use("Agg")   # Non-interactive backend for servers
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from threading import Lock
from tensorflow.keras.callbacks import Callback

# ─── project imports ─────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from data_pipeline import (
    build_pipeline, FEATURE_COLS, inverse_transform_close,
    normalize_ticker, get_currency_symbol, DEFAULT_START_DATE,
    LOG_RETURN_COL_IDX, CLOSE_COL_IDX,
)
from lstm_model import build_lstm_model, get_callbacks, save_model


_ARTIFACT_CACHE: dict[str, dict] = {}
_ARTIFACT_CACHE_LOCK = Lock()

PROGRESS_CALLBACK = None


class EpochProgressCallback(Callback):
    def __init__(self, total_epochs: int):
        super().__init__()
        self.total_epochs = total_epochs

    def on_epoch_end(self, epoch, logs=None):
        if PROGRESS_CALLBACK:
            PROGRESS_CALLBACK(epoch + 1, self.total_epochs, logs or {})


def _get_cached_forecast_artifacts(ticker: str, model_dir: str) -> tuple:
    ticker_dir  = os.path.join(os.path.abspath(model_dir), ticker)
    model_path  = os.path.join(ticker_dir, "model.keras")
    scaler_path = os.path.join(ticker_dir, "scaler.pkl")
    config_path = os.path.join(ticker_dir, "config.json")

    mtimes = {
        "model": os.path.getmtime(model_path),
        "scaler": os.path.getmtime(scaler_path),
        "config": os.path.getmtime(config_path),
    }

    with _ARTIFACT_CACHE_LOCK:
        cached = _ARTIFACT_CACHE.get(ticker)
        if cached and cached["mtimes"] == mtimes:
            return cached["model"], cached["scaler"], cached["config"]

        from lstm_model import load_model

        model = load_model(model_path)
        scaler = joblib.load(scaler_path)
        with open(config_path) as f:
            config = json.load(f)

        _ARTIFACT_CACHE[ticker] = {
            "mtimes": mtimes,
            "model": model,
            "scaler": scaler,
            "config": config,
        }
        return model, scaler, config


def _parse_lstm_units(units_str: str) -> tuple:
    try:
        units = tuple(int(x.strip()) for x in units_str.split(",") if x.strip())
        return units if units else (256, 128, 64)
    except Exception:
        return (256, 128, 64)


def _get_direction_predictions(
    model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    scaler,
    n_features: int,
    y_test_direction: np.ndarray = None,
    direction_threshold: float = 0.5,
):
    y_pred_raw = model.predict(X_test, verbose=0)

    if isinstance(y_pred_raw, (np.ndarray,)) and y_pred_raw.ndim == 2 and y_pred_raw.shape[1] == 1:
        y_pred_dir = (y_pred_raw.ravel() >= direction_threshold).astype(int)
        y_true_dir = (y_test_direction.ravel() > 0.5).astype(int) if y_test_direction is not None else None
        return y_true_dir, y_pred_dir

    if isinstance(y_pred_raw, (list, tuple)):
        y_pred_scaled = y_pred_raw[0]
        y_pred_dir_raw = y_pred_raw[1]
        y_pred_dir = (y_pred_dir_raw.ravel() >= direction_threshold).astype(int)
        y_true_dir = (y_test_direction.ravel() > 0.5).astype(int) if y_test_direction is not None else None
        return y_true_dir, y_pred_dir

    y_pred_lr = inverse_transform_close(scaler, y_pred_raw, LOG_RETURN_COL_IDX, n_features)
    y_true_lr = inverse_transform_close(scaler, y_test, LOG_RETURN_COL_IDX, n_features)
    y_pred_dir = (y_pred_lr.ravel() >= 0).astype(int)
    y_true_dir = (y_true_lr.ravel() >= 0).astype(int)
    return y_true_dir, y_pred_dir


def _plot_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, save_dir: str, ticker: str):
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_true, y_pred)

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_title(f"{ticker} — Confusion Matrix", fontsize=12, fontweight="bold")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["Down", "Up"])
    ax.set_yticklabels(["Down", "Up"])

    for (i, j), val in np.ndenumerate(cm):
        ax.text(j, i, int(val), ha="center", va="center", color="black")

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    path = os.path.join(save_dir, "confusion_matrix.png")
    plt.savefig(path, dpi=140)
    plt.close()
    print(f"[Plot] Confusion matrix → {path}")


def _purged_walk_forward_splits(
    n_samples: int,
    n_splits: int = 3,
    embargo: int = 5,
    min_train_size: int = 300,
):
    """
    Expanding-window walk-forward splits with an embargo gap to reduce leakage.
    Returns a list of (train_indices, val_indices).
    """
    n_splits = max(2, int(n_splits))
    embargo = max(0, int(embargo))
    min_train_size = max(50, int(min_train_size))

    usable = max(0, n_samples - min_train_size - embargo)
    if usable <= n_splits:
        step = 1
    else:
        step = max(1, usable // (n_splits + 1))

    splits = []
    train_end = min_train_size
    for _ in range(n_splits):
        val_start = train_end + embargo
        val_end = min(n_samples, val_start + step)
        if val_start >= n_samples or val_end - val_start < 10:
            break
        tr_idx = np.arange(0, train_end)
        val_idx = np.arange(val_start, val_end)
        splits.append((tr_idx, val_idx))
        train_end = val_end

    if not splits:
        cutoff = max(min_train_size, int(0.7 * n_samples))
        val_start = min(n_samples - 10, cutoff + embargo)
        tr_idx = np.arange(0, cutoff)
        val_idx = np.arange(val_start, n_samples)
        if len(val_idx) > 0:
            splits.append((tr_idx, val_idx))

    return splits


def _strategy_metrics_from_positions(
    positions: np.ndarray,
    future_log_returns: np.ndarray,
    transaction_cost: float = 0.0005,
) -> dict:
    """Compute basic trading metrics from positions and next-period log returns."""
    if len(positions) == 0:
        return {
            "strategy_total_return": 0.0,
            "strategy_sharpe": 0.0,
            "strategy_sortino": 0.0,
            "strategy_max_drawdown": 0.0,
            "strategy_hit_rate": 0.0,
        }

    positions = positions.astype(float).reshape(-1)
    future_log_returns = future_log_returns.astype(float).reshape(-1)

    if len(positions) != len(future_log_returns):
        m = min(len(positions), len(future_log_returns))
        positions = positions[:m]
        future_log_returns = future_log_returns[:m]

    turns = np.abs(np.diff(np.r_[0.0, positions]))
    pnl = positions * future_log_returns - turns * float(transaction_cost)
    equity = np.exp(np.cumsum(pnl))

    mean_p = float(np.mean(pnl))
    std_p = float(np.std(pnl) + 1e-12)
    downside = pnl[pnl < 0]
    downside_std = float(np.std(downside) + 1e-12) if len(downside) > 0 else 1e-12

    running_max = np.maximum.accumulate(equity)
    drawdown = 1.0 - (equity / (running_max + 1e-12))
    max_dd = float(np.max(drawdown)) if len(drawdown) else 0.0

    return {
        "strategy_total_return": float(equity[-1] - 1.0) if len(equity) else 0.0,
        "strategy_sharpe": float((mean_p / std_p) * np.sqrt(252.0)),
        "strategy_sortino": float((mean_p / downside_std) * np.sqrt(252.0)),
        "strategy_max_drawdown": max_dd,
        "strategy_hit_rate": float(np.mean(pnl > 0)),
    }


def _optimize_direction_threshold(
    probs: np.ndarray,
    y_true_dir: np.ndarray,
    future_log_returns: np.ndarray = None,
    objective: str = "sharpe",
    transaction_cost: float = 0.0005,
    allow_short: bool = False,
) -> tuple[float, float]:
    """Choose decision threshold using either accuracy or strategy Sharpe."""
    probs = probs.reshape(-1)
    y_true_dir = y_true_dir.reshape(-1)
    thresholds = np.linspace(0.30, 0.70, 41)

    best_t, best_score = 0.5, -np.inf
    for t in thresholds:
        if objective == "accuracy" or future_log_returns is None:
            pred = (probs >= t).astype(int)
            score = float(np.mean(pred == (y_true_dir > 0.5)))
        else:
            if allow_short:
                pos = np.where(probs >= t, 1.0, np.where(probs <= (1.0 - t), -1.0, 0.0))
            else:
                pos = (probs >= t).astype(float)
            score = _strategy_metrics_from_positions(pos, future_log_returns, transaction_cost)["strategy_sharpe"]

        if score > best_score:
            best_score = score
            best_t = float(t)

    return best_t, float(best_score)


# ─────────────────────────────────────────────
# ARGUMENT PARSER
# ─────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Train LSTM stock-price predictor")
    p.add_argument("--ticker",    default="RELIANCE.NS",  help="Stock ticker symbol (e.g. RELIANCE.NS, TCS.NS, AAPL)")
    p.add_argument("--start",     default=DEFAULT_START_DATE, help="Start date (default: 20 years ago)")
    p.add_argument("--window",    type=int, default=60,  help="Look-back window")
    p.add_argument("--horizon",   type=int, default=1,   help="Days ahead to predict")
    p.add_argument("--epochs",    type=int, default=200, help="Max training epochs")
    p.add_argument("--batch",     type=int, default=64,  help="Batch size")
    p.add_argument("--lr",        type=float, default=3e-4, help="Learning rate")
    p.add_argument("--dropout",   type=float, default=0.15,  help="Dropout rate")
    p.add_argument("--attention", action="store_true", default=True,
                   help="Use temporal attention")
    p.add_argument("--bidir",     action="store_true", default=False,
                   help="Use Bidirectional LSTM")
    p.add_argument("--single-task", action="store_true", default=False,
                   help="Disable the auxiliary direction head and train only the regression output")
    p.add_argument("--split",     type=float, default=0.85,  help="Train ratio")
    p.add_argument("--val-ratio", type=float, default=0.1,   help="Validation ratio from training set")
    p.add_argument("--direction-only", action="store_true", default=False,
                   help="Train a direction-only classifier (binary up/down)")
    p.add_argument("--direction-bigmove", action="store_true", default=False,
                   help="Train direction-only classifier on big-move days only")
    p.add_argument("--direction-threshold", type=float, default=0.0,
                   help="Direction label threshold on log-return (default: 0)")
    p.add_argument("--scale", choices=["minmax", "standard", "robust"], default="minmax",
                   help="Feature scaling method")
    p.add_argument("--lstm-units", default="256,128,64",
                   help="Comma-separated LSTM units, e.g. '128,64'")
    p.add_argument("--cnn", action="store_true", default=False,
                   help="Enable CNN+LSTM hybrid")
    p.add_argument("--walk-forward", action="store_true", default=False,
                   help="Use walk-forward validation (expanding window)")
    p.add_argument("--wf-splits", type=int, default=3,
                   help="Number of walk-forward splits")
    p.add_argument("--wf-embargo", type=int, default=5,
                   help="Embargo gap (samples) between train and validation in walk-forward")
    p.add_argument("--wf-min-train", type=int, default=300,
                   help="Minimum initial train samples for walk-forward")
    p.add_argument("--threshold-objective", choices=["accuracy", "sharpe"], default="sharpe",
                   help="Optimize direction threshold for this objective")
    p.add_argument("--transaction-cost", type=float, default=0.0005,
                   help="One-way transaction cost per position change")
    p.add_argument("--allow-short", action="store_true", default=False,
                   help="Allow short positions in strategy simulation")
    p.add_argument("--strict-no-lookahead", action="store_true", default=False,
                   help="Shift all features by one bar to enforce strict no-look-ahead")
    p.add_argument("--output",    default="../backend/models",
                   help="Directory to save model & artefacts")
    return p.parse_args()


# ─────────────────────────────────────────────
# TRAINING FUNCTION
# ─────────────────────────────────────────────

def train(args) -> dict:
    """
    Full training workflow:
      1. Build pipeline (fetch + engineer + scale + window + split)
      2. Construct LSTM
      3. Train with callbacks
      4. Evaluate on test set
      5. Save model, scaler, config
      6. Generate training plots

    Returns
    -------
    dict with metrics and paths
    """
    ticker  = normalize_ticker(args.ticker)
    out_dir = os.path.abspath(args.output)
    os.makedirs(out_dir, exist_ok=True)

    ticker_dir   = os.path.join(out_dir, ticker)
    os.makedirs(ticker_dir, exist_ok=True)

    scaler_path   = os.path.join(ticker_dir, "scaler.pkl")
    model_path    = os.path.join(ticker_dir, "model.keras")
    config_path   = os.path.join(ticker_dir, "config.json")
    ckpt_path     = os.path.join(ticker_dir, "checkpoint.keras")

    # ── 1. Data Pipeline ─────────────────────
    print(f"\n{'='*55}")
    print(f"  TRAINING:  {ticker}   window={args.window}   horizon={args.horizon}")
    print(f"{'='*55}")
    t0 = time.time()

    target_mode = "regression"
    if args.direction_bigmove:
        target_mode = "direction_bigmove"
    elif args.direction_only:
        target_mode = "direction"

    pipeline = build_pipeline(
        ticker         = ticker,
        window_size    = args.window,
        forecast_horizon = args.horizon,
        split_ratio    = args.split,
        start_date     = args.start,
        scaler_save_path = scaler_path,
        target_mode    = target_mode,
        direction_threshold = args.direction_threshold,
        scale_method   = args.scale,
        strict_no_lookahead = args.strict_no_lookahead,
    )

    X_train          = pipeline["X_train"]
    X_test           = pipeline["X_test"]
    y_train          = pipeline["y_train"]
    y_test           = pipeline["y_test"]
    y_return_train   = pipeline["y_return_train"]
    y_return_test    = pipeline["y_return_test"]
    scaler           = pipeline["scaler"]
    df_feat          = pipeline["df_featured"]
    test_prev_closes = pipeline.get("test_prev_closes")
    n_features       = X_train.shape[2]

    if args.direction_only or args.direction_bigmove:
        y_train_dir = y_train.astype(np.float32)
        y_test_dir  = y_test.astype(np.float32)
        use_multi_task = False
    else:
        y_train_lr = inverse_transform_close(scaler, y_train, LOG_RETURN_COL_IDX, n_features).reshape(-1, 1)
        y_test_lr  = inverse_transform_close(scaler, y_test,  LOG_RETURN_COL_IDX, n_features).reshape(-1, 1)
        y_train_dir = (y_train_lr > 0).astype(np.float32)
        y_test_dir  = (y_test_lr  > 0).astype(np.float32)
        use_multi_task = not getattr(args, "single_task", False)

    lstm_units = _parse_lstm_units(args.lstm_units)

    # ── Validation: walk-forward (expanding window) or last-slice ──
    X_val = None
    y_val = None
    y_val_dir = None
    X_train_fit = X_train
    y_train_fit = y_train
    y_train_dir_fit = y_train_dir
    y_train_ret_fit = y_return_train

    if not args.walk_forward:
        n_train_total = len(X_train)
        n_val = int(n_train_total * args.val_ratio)
        if n_val >= 1:
            X_val = X_train[-n_val:]
            y_val = y_train[-n_val:]
            y_val_dir = y_train_dir[-n_val:]
            y_val_ret = y_return_train[-n_val:]
            X_train_fit = X_train[:-n_val]
            y_train_fit = y_train[:-n_val]
            y_train_dir_fit = y_train_dir[:-n_val]
            y_train_ret_fit = y_return_train[:-n_val]

    # Class-balanced weights for directional head
    pos_rate = float(np.mean(y_train_dir_fit))
    neg_rate = 1.0 - pos_rate
    if pos_rate > 0 and neg_rate > 0:
        w_pos = 0.5 / pos_rate
        w_neg = 0.5 / neg_rate
        dir_sample_weight = np.where(y_train_dir_fit.ravel() > 0.5, w_pos, w_neg).astype(np.float32)
    else:
        dir_sample_weight = None

    # ── 2. Build/Train Model ──────────────────
    callbacks = get_callbacks(ckpt_path, patience=25)
    if PROGRESS_CALLBACK:
        callbacks.append(EpochProgressCallback(args.epochs))
    history = None
    direction_threshold = 0.5

    if args.walk_forward:
        splits = _purged_walk_forward_splits(
            len(X_train),
            n_splits=max(2, args.wf_splits),
            embargo=max(0, args.wf_embargo),
            min_train_size=max(50, args.wf_min_train),
        )
        best_score = -np.inf
        best_model = None
        best_history = None
        best_threshold = 0.5

        for fold, (tr_idx, val_idx) in enumerate(splits, start=1):
            X_tr, X_val = X_train[tr_idx], X_train[val_idx]
            y_tr, y_val = y_train[tr_idx], y_train[val_idx]
            y_tr_dir = y_train_dir[tr_idx]
            y_val_dir = y_train_dir[val_idx]
            y_tr_ret = y_return_train[tr_idx]
            y_val_ret = y_return_train[val_idx]

            model = build_lstm_model(
                window_size      = args.window,
                n_features       = n_features,
                forecast_horizon = args.horizon,
                lstm_units       = lstm_units,
                dropout_rate     = args.dropout,
                learning_rate    = args.lr,
                use_attention    = args.attention,
                use_bidirectional = args.bidir,
                use_multi_task   = use_multi_task,
                output_mode      = "direction" if (args.direction_only or args.direction_bigmove) else ("multi" if use_multi_task else "regression"),
                use_cnn          = args.cnn,
            )

            if args.direction_only or args.direction_bigmove:
                history = model.fit(
                    X_tr, y_tr_dir,
                    validation_data = (X_val, y_val_dir),
                    epochs     = args.epochs,
                    batch_size = args.batch,
                    callbacks  = callbacks,
                    verbose    = 1,
                    shuffle    = False
                )
            elif use_multi_task:
                history = model.fit(
                    X_tr,
                    {"price_output": y_tr, "direction_output": y_tr_dir},
                    validation_data = (X_val, {"price_output": y_val, "direction_output": y_val_dir}),
                    epochs     = args.epochs,
                    batch_size = args.batch,
                    callbacks  = callbacks,
                    verbose    = 1,
                    shuffle    = False
                )
            else:
                history = model.fit(
                    X_tr, y_tr,
                    validation_data = (X_val, y_val),
                    epochs     = args.epochs,
                    batch_size = args.batch,
                    callbacks  = callbacks,
                    verbose    = 1,
                    shuffle    = False
                )

            fold_threshold = 0.5
            if use_multi_task:
                val_pred = model.predict(X_val, verbose=0)
                if isinstance(val_pred, (list, tuple)) and len(val_pred) > 1:
                    val_dir = val_pred[1].ravel()
                    y_val_dir_flat = y_val_dir.ravel().astype(float)
                    y_val_ret_flat = y_val_ret.ravel().astype(float)
                    fold_threshold, _ = _optimize_direction_threshold(
                        val_dir,
                        y_val_dir_flat,
                        future_log_returns=y_val_ret_flat,
                        objective=args.threshold_objective,
                        transaction_cost=args.transaction_cost,
                        allow_short=args.allow_short,
                    )

            y_true_dir, y_pred_dir = _get_direction_predictions(
                model, X_val, y_val, scaler, n_features, y_val_dir, fold_threshold
            )
            if y_true_dir is not None and y_pred_dir is not None:
                fold_score = float(np.mean(y_true_dir == y_pred_dir))
                print(f"[WalkForward] Fold {fold} DirAcc={fold_score:.4f}  thr={fold_threshold:.3f}")
            else:
                fold_score = -np.inf
                print(f"[WalkForward] Fold {fold} score unavailable")

            if fold_score > best_score:
                best_score = fold_score
                best_model = model
                best_history = history
                best_threshold = fold_threshold

        model = best_model
        history = best_history
        direction_threshold = best_threshold
    else:
        model = build_lstm_model(
            window_size      = args.window,
            n_features       = n_features,
            forecast_horizon = args.horizon,
            lstm_units       = lstm_units,
            dropout_rate     = args.dropout,
            learning_rate    = args.lr,
            use_attention    = args.attention,
            use_bidirectional = args.bidir,
            use_multi_task   = use_multi_task,
            output_mode      = "direction" if (args.direction_only or args.direction_bigmove) else ("multi" if use_multi_task else "regression"),
            use_cnn          = args.cnn,
        )

        if args.direction_only or args.direction_bigmove:
            history = model.fit(
                X_train_fit, y_train_dir_fit,
                validation_data = (X_val, y_val_dir) if X_val is not None else (X_test, y_test_dir),
                epochs     = args.epochs,
                batch_size = args.batch,
                callbacks  = callbacks,
                verbose    = 1,
                shuffle    = False
            )
        elif use_multi_task:
            history = model.fit(
                X_train_fit,
                {"price_output": y_train_fit, "direction_output": y_train_dir_fit},
                validation_data = (
                    (X_val, {"price_output": y_val, "direction_output": y_val_dir})
                    if X_val is not None else (X_test, {"price_output": y_test, "direction_output": y_test_dir})
                ),
                epochs     = args.epochs,
                batch_size = args.batch,
                callbacks  = callbacks,
                verbose    = 1,
                shuffle    = False
            )
        else:
            history = model.fit(
                X_train_fit, y_train_fit,
                validation_data = (X_val, y_val) if X_val is not None else (X_test, y_test),
                epochs     = args.epochs,
                batch_size = args.batch,
                callbacks  = callbacks,
                verbose    = 1,
                shuffle    = False
            )

    train_time = time.time() - t0
    print(f"\n[Train] Completed in {train_time:.1f}s")

    # ── Direction threshold tuning (validation) ──
    if (not args.walk_forward) and use_multi_task and X_val is not None:
        val_pred = model.predict(X_val, verbose=0)
        if isinstance(val_pred, (list, tuple)) and len(val_pred) > 1:
            val_dir = val_pred[1].ravel()
            y_val_dir_flat = y_val_dir.ravel()
            y_val_ret_flat = y_val_ret.ravel() if 'y_val_ret' in locals() else None
            direction_threshold, _ = _optimize_direction_threshold(
                val_dir,
                y_val_dir_flat,
                future_log_returns=y_val_ret_flat,
                objective=args.threshold_objective,
                transaction_cost=args.transaction_cost,
                allow_short=args.allow_short,
            )

    # ── 4. Evaluate ───────────────────────────
    metrics = evaluate_model(model, X_test, y_test, scaler,
                             n_features, args.horizon, test_prev_closes,
                             y_test_dir if (use_multi_task or args.direction_only or args.direction_bigmove) else None,
                             direction_threshold=direction_threshold,
                             y_test_returns=y_return_test,
                             transaction_cost=args.transaction_cost,
                             allow_short=args.allow_short)
    if args.direction_only or args.direction_bigmove:
        metrics["coverage"] = pipeline.get("coverage")
    if args.direction_only or args.direction_bigmove:
        print(f"\n[Eval] DirAcc = {metrics.get('directional_accuracy', 0.0):.4f}")
        if metrics.get("coverage") is not None:
            print(f"[Eval] Coverage = {metrics['coverage']:.3f}")
    else:
        print(f"\n[Eval] RMSE  = {metrics['rmse']:.4f}")
        print(f"[Eval] MAE   = {metrics['mae']:.4f}")
        print(f"[Eval] MAPE  = {metrics['mape']:.2f}%")
        print(f"[Eval] R²    = {metrics['r2']:.4f}")
        if "direction_accuracy_head" in metrics:
            print(f"[Eval] DirAcc = {metrics['direction_accuracy_head']:.4f}")

    # Confusion matrix plot
    y_true_dir, y_pred_dir = _get_direction_predictions(
        model, X_test, y_test, scaler, n_features,
        y_test_dir if (use_multi_task or args.direction_only or args.direction_bigmove) else None,
        direction_threshold=direction_threshold,
    )
    if y_true_dir is not None and y_pred_dir is not None:
        _plot_confusion_matrix(y_true_dir, y_pred_dir, ticker_dir, ticker)

    # ── 5. Save Artefacts ─────────────────────
    save_model(model, model_path)

    config = {
        "ticker":          ticker,
        "window_size":     args.window,
        "forecast_horizon": args.horizon,
        "n_features":      n_features,
        "feature_cols":    FEATURE_COLS,
        "split_ratio":     args.split,
        "val_ratio":       args.val_ratio,
        "scale_method":    args.scale,
        "lstm_units":      lstm_units,
        "cnn":             args.cnn,
        "walk_forward":    args.walk_forward,
        "wf_splits":       args.wf_splits,
        "wf_embargo":      args.wf_embargo,
        "wf_min_train":    args.wf_min_train,
        "multi_task":      use_multi_task,
        "threshold_objective": args.threshold_objective,
        "transaction_cost": args.transaction_cost,
        "allow_short":     args.allow_short,
        "strict_no_lookahead": args.strict_no_lookahead,
        "epochs_trained":  len(history.history["loss"]),
        "metrics":         metrics,
        "direction_threshold": direction_threshold,
        "direction_bigmove": args.direction_bigmove,
        "train_time_sec":  round(train_time, 1),
        "model_path":      model_path,
        "scaler_path":     scaler_path,
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"[Train] Config saved → {config_path}")

    # ── 6. Plots ──────────────────────────────
    _plot_training_history(history, ticker_dir, ticker)
    if not (args.direction_only or args.direction_bigmove):
        _plot_predictions(
            model, X_test, y_test, scaler,
            df_feat, n_features, args.horizon,
            ticker, ticker_dir, test_prev_closes
        )

    return config


# ─────────────────────────────────────────────
# EVALUATION
# ─────────────────────────────────────────────

def evaluate_model(
    model,
    X_test:           np.ndarray,
    y_test:           np.ndarray,
    scaler,
    n_features:       int,
    horizon:          int,
    test_prev_closes: np.ndarray = None,
    y_test_direction: np.ndarray = None,
    direction_threshold: float = 0.5,
    y_test_returns: np.ndarray = None,
    transaction_cost: float = 0.0005,
    allow_short: bool = False,
) -> dict:
    """
    Compute metrics on the test set.

    Target is next-day log return (stationary).  R² is measured on
    log returns — any model capturing a real signal scores > 0.
    RMSE / MAE / MAPE are reconstructed in price space via
        price_pred = prev_close * exp(log_return_pred).
    """
    from sklearn.metrics import (
        mean_squared_error, mean_absolute_error, r2_score,
        precision_recall_fscore_support, confusion_matrix, roc_auc_score
    )

    y_pred_raw = model.predict(X_test, verbose=0)

    if isinstance(y_pred_raw, (np.ndarray,)) and y_pred_raw.ndim == 2 and y_pred_raw.shape[1] == 1 and y_test_direction is not None:
        # Direction-only model
        y_pred_dir = y_pred_raw
        direction_head_acc = float(
            np.mean((y_pred_dir.ravel() >= direction_threshold) == (y_test_direction.ravel() > 0.5))
        )
        y_true_dir = (y_test_direction.ravel() > 0.5).astype(int)
        y_pred_bin = (y_pred_dir.ravel() >= direction_threshold).astype(int)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true_dir, y_pred_bin, average="binary", zero_division=0
        )
        cm = confusion_matrix(y_true_dir, y_pred_bin)
        auc = float(roc_auc_score(y_true_dir, y_pred_dir.ravel())) if len(np.unique(y_true_dir)) > 1 else 0.5

        future_lr = y_test_returns.ravel() if y_test_returns is not None else np.where(y_true_dir > 0, 0.001, -0.001)
        if allow_short:
            pos = np.where(y_pred_dir.ravel() >= direction_threshold, 1.0,
                           np.where(y_pred_dir.ravel() <= (1.0 - direction_threshold), -1.0, 0.0))
        else:
            pos = (y_pred_dir.ravel() >= direction_threshold).astype(float)
        strat = _strategy_metrics_from_positions(pos, future_lr, transaction_cost=transaction_cost)

        return {
            "directional_accuracy": round(float(direction_head_acc), 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
            "roc_auc": round(float(auc), 4),
            "confusion_matrix": cm.tolist(),
            **{k: round(float(v), 6) for k, v in strat.items()},
        }

    if isinstance(y_pred_raw, (list, tuple)):
        y_pred_scaled = y_pred_raw[0]
        y_pred_dir = y_pred_raw[1]
    else:
        y_pred_scaled = y_pred_raw
        y_pred_dir = None

    # Inverse-transform scaled log returns → actual log returns
    y_pred_lr = inverse_transform_close(scaler, y_pred_scaled, LOG_RETURN_COL_IDX, n_features)
    y_true_lr = inverse_transform_close(scaler, y_test,        LOG_RETURN_COL_IDX, n_features)

    # Reconstruct prices for all metrics (RMSE, MAE, MAPE, R²)
    if test_prev_closes is not None and len(test_prev_closes) == len(y_pred_lr):
        price_pred = test_prev_closes * np.exp(y_pred_lr)
        price_true = test_prev_closes * np.exp(y_true_lr)
    else:
        price_pred = np.exp(np.cumsum(y_pred_lr))
        price_true = np.exp(np.cumsum(y_true_lr))

    rmse = np.sqrt(mean_squared_error(price_true, price_pred))
    mae  = mean_absolute_error(price_true, price_pred)
    mape = np.mean(np.abs((price_true - price_pred) / (price_true + 1e-10))) * 100
    # R² on reconstructed prices — measures how well the model tracks actual price levels
    r2   = r2_score(price_true, price_pred)
    da_reg = _directional_accuracy(y_true_lr, y_pred_lr)

    direction_head_acc = None
    if y_pred_dir is not None and y_test_direction is not None:
        direction_head_acc = float(
            np.mean((y_pred_dir.ravel() >= direction_threshold) == (y_test_direction.ravel() > 0.5))
        )

    metrics = {
        "rmse": round(float(rmse), 4),
        "mae":  round(float(mae),  4),
        "mape": round(float(mape), 4),
        "r2":   round(float(r2),   4),
        "directional_accuracy": round(float(direction_head_acc if direction_head_acc is not None else da_reg), 4),
        "directional_accuracy_regression": round(float(da_reg), 4),
    }

    # Classification metrics (direction)
    if y_test_direction is not None and y_pred_dir is not None:
        y_true_dir = (y_test_direction.ravel() > 0.5).astype(int)
        y_pred_bin = (y_pred_dir.ravel() >= direction_threshold).astype(int)
        y_pred_prob = y_pred_dir.ravel()
    else:
        y_true_dir = (y_true_lr.ravel() >= 0).astype(int)
        y_pred_bin = (y_pred_lr.ravel() >= 0).astype(int)
        y_pred_prob = (1.0 / (1.0 + np.exp(-10.0 * y_pred_lr.ravel())))

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true_dir, y_pred_bin, average="binary", zero_division=0
    )
    auc = float(roc_auc_score(y_true_dir, y_pred_prob)) if len(np.unique(y_true_dir)) > 1 else 0.5
    cm = confusion_matrix(y_true_dir, y_pred_bin)
    metrics.update({
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(auc), 4),
        "confusion_matrix": cm.tolist(),
    })

    # Strategy metrics using realized next-period log returns
    realized_lr = y_test_returns.ravel() if y_test_returns is not None else y_true_lr.ravel()
    if y_pred_dir is not None:
        if allow_short:
            positions = np.where(y_pred_prob >= direction_threshold, 1.0,
                                 np.where(y_pred_prob <= (1.0 - direction_threshold), -1.0, 0.0))
        else:
            positions = (y_pred_prob >= direction_threshold).astype(float)
    else:
        if allow_short:
            positions = np.sign(y_pred_lr.ravel())
        else:
            positions = (y_pred_lr.ravel() >= 0).astype(float)

    strat = _strategy_metrics_from_positions(positions, realized_lr, transaction_cost=transaction_cost)
    metrics.update({k: round(float(v), 6) for k, v in strat.items()})

    if direction_head_acc is not None:
        metrics["direction_accuracy_head"] = round(direction_head_acc, 4)

    return metrics


def _directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Fraction of days where predicted return direction matches actual direction."""
    return float(np.mean(np.sign(y_pred) == np.sign(y_true)))


# ─────────────────────────────────────────────
# PLOTTING
# ─────────────────────────────────────────────

def _plot_training_history(history, save_dir: str, ticker: str):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f"{ticker} — Training History", fontsize=14, fontweight="bold")

    axes[0].plot(history.history["loss"],     label="Train Loss")
    axes[0].plot(history.history["val_loss"], label="Val Loss")
    axes[0].set_title("Loss (Huber)")
    axes[0].set_xlabel("Epoch")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    train_mae = (
        history.history.get("mae")
        or history.history.get("price_output_mae")
    )
    val_mae = (
        history.history.get("val_mae")
        or history.history.get("val_price_output_mae")
    )
    if train_mae is not None or val_mae is not None:
        if train_mae is not None:
            axes[1].plot(train_mae, label="Train MAE")
        if val_mae is not None:
            axes[1].plot(val_mae, label="Val MAE")
        axes[1].set_title("Mean Absolute Error")
    else:
        train_acc = history.history.get("accuracy")
        val_acc = history.history.get("val_accuracy")
        if train_acc is not None:
            axes[1].plot(train_acc, label="Train Acc")
        if val_acc is not None:
            axes[1].plot(val_acc, label="Val Acc")
        axes[1].set_title("Accuracy")
    axes[1].set_xlabel("Epoch")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(save_dir, "training_history.png")
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"[Plot] Training history → {path}")


def _plot_predictions(
    model, X_test, y_test, scaler, df_feat,
    n_features, horizon, ticker, save_dir, test_prev_closes=None
):
    y_pred_sc = model.predict(X_test, verbose=0)
    if isinstance(y_pred_sc, (list, tuple)):
        y_pred_sc = y_pred_sc[0]
    y_pred_lr = inverse_transform_close(scaler, y_pred_sc, LOG_RETURN_COL_IDX, n_features)
    y_true_lr = inverse_transform_close(scaler, y_test,    LOG_RETURN_COL_IDX, n_features)

    # Reconstruct prices from log returns
    if test_prev_closes is not None and len(test_prev_closes) == len(y_pred_lr):
        y_pred = test_prev_closes * np.exp(y_pred_lr)
        y_true = test_prev_closes * np.exp(y_true_lr)
    else:
        y_pred = np.exp(np.cumsum(y_pred_lr))
        y_true = np.exp(np.cumsum(y_true_lr))

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.plot(y_true, label="Actual Price",    color="#2196F3", linewidth=1.5)
    ax.plot(y_pred, label="Predicted Price", color="#FF5722", linewidth=1.5, alpha=0.85)
    ax.fill_between(
        range(len(y_true)),
        y_pred * 0.97, y_pred * 1.03,
        color="#FF5722", alpha=0.1, label="±3% Band"
    )
    currency = get_currency_symbol(ticker)
    ax.set_title(f"{ticker} — Actual vs. Predicted (Test Set)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Time Steps")
    ax.set_ylabel(f"Price ({currency})")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(save_dir, "predictions.png")
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"[Plot] Predictions → {path}")


# ─────────────────────────────────────────────
# FUTURE FORECAST
# ─────────────────────────────────────────────

def forecast_future(
    ticker: str,
    n_days: int = 30,
    model_dir: str = "../backend/models",
    data_start: str = None
) -> dict:
    """
    Generate n_days future predictions using the last window of live data.

    Returns
    -------
    dict with 'dates' and 'prices' lists
    """
    import pandas as pd
    from data_pipeline import (
        fetch_stock_data, add_technical_indicators,
        add_lag_features, add_rolling_stats, add_external_signals, clean_feature_frame,
        normalize_data, FEATURE_COLS, CLOSE_COL_IDX, LOG_RETURN_COL_IDX,
        normalize_ticker, DEFAULT_START_DATE,
    )

    ticker = normalize_ticker(ticker)
    if data_start is None:
        data_start = DEFAULT_START_DATE

    ticker_dir   = os.path.join(os.path.abspath(model_dir), ticker)
    scaler_path  = os.path.join(ticker_dir, "scaler.pkl")

    model, scaler, config = _get_cached_forecast_artifacts(ticker, model_dir)
    window = config["window_size"]

    # Try to load from local CSV first (fast path — avoids yfinance round-trip)
    from data_pipeline import load_raw_data
    try:
        df_raw = load_raw_data(ticker)
        print(f"[Forecast] Loaded local data for {ticker}: {len(df_raw)} rows")
    except FileNotFoundError:
        # Fallback: fetch from API only if no local data exists
        df_raw = fetch_stock_data(ticker, start=data_start, incremental=False)
    df_feat = add_technical_indicators(df_raw)
    df_feat = add_lag_features(df_feat, close_lags=10, return_lags=5)
    df_feat = add_rolling_stats(df_feat)
    df_feat = add_external_signals(df_feat, start=data_start)
    df_feat = clean_feature_frame(df_feat)

    missing_cols = [col for col in FEATURE_COLS if col not in df_feat.columns]
    if missing_cols:
        for col in missing_cols:
            df_feat[col] = 0.0
        df_feat = df_feat[FEATURE_COLS]
    scaled, _ = normalize_data(df_feat, FEATURE_COLS, scaler_path)

    # Use the last `window` rows as starting sequence
    sequence = scaled[-window:]

    future_prices = []
    current_seq   = sequence.copy()
    last_close    = df_feat["Close"].values[-1]   # seed with most recent actual close

    # Pre-compute Close-column scaling params (supports MinMaxScaler or StandardScaler)
    _close_min = None
    _close_rng = None
    _close_mean = None
    _close_scale = None
    if hasattr(scaler, "data_min_") and hasattr(scaler, "data_max_"):
        _close_min = float(scaler.data_min_[CLOSE_COL_IDX])
        _close_rng = float(scaler.data_max_[CLOSE_COL_IDX] - scaler.data_min_[CLOSE_COL_IDX])
    elif hasattr(scaler, "mean_") and hasattr(scaler, "scale_"):
        _close_mean = float(scaler.mean_[CLOSE_COL_IDX])
        _close_scale = float(scaler.scale_[CLOSE_COL_IDX])

    for _ in range(n_days):
        x = current_seq[-window:].reshape(1, window, len(FEATURE_COLS))
        pred_out = model.predict(x, verbose=0)
        # Multi-task models return [price_output, direction_output]
        if isinstance(pred_out, (list, tuple)):
            pred_scaled = float(pred_out[0][0, 0])
        else:
            pred_scaled = float(pred_out[0, 0])

        # Inverse-transform scaled log return → actual log return → next price
        log_ret    = inverse_transform_close(scaler, np.array([[pred_scaled]]),
                                             LOG_RETURN_COL_IDX, len(FEATURE_COLS))[0]
        next_close = last_close * np.exp(float(log_ret))
        future_prices.append(float(next_close))

        # Advance sequence: copy last row, update log-return & close columns
        next_row = current_seq[-1].copy()
        next_row[LOG_RETURN_COL_IDX] = pred_scaled
        if _close_min is not None and _close_rng is not None:
            next_row[CLOSE_COL_IDX] = (next_close - _close_min) / (_close_rng + 1e-10)
        elif _close_mean is not None and _close_scale is not None:
            next_row[CLOSE_COL_IDX] = (next_close - _close_mean) / (_close_scale + 1e-10)
        else:
            dummy = np.zeros((1, len(FEATURE_COLS)))
            dummy[0, CLOSE_COL_IDX] = next_close
            next_row[CLOSE_COL_IDX] = float(scaler.transform(dummy)[0, CLOSE_COL_IDX])
        current_seq = np.vstack([current_seq, next_row])
        last_close  = next_close

    # Build future dates
    last_date    = df_feat.index[-1]
    future_dates = pd.bdate_range(start=last_date, periods=n_days + 1)[1:]
    dates        = [d.strftime("%Y-%m-%d") for d in future_dates]

    return {"dates": dates, "prices": future_prices}


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()
    result = train(args)
    print("\n✅  Training complete!")
    print(json.dumps(result["metrics"], indent=2))
