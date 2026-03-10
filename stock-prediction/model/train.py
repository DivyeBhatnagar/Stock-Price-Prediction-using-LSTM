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

# ─── project imports ─────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from data_pipeline import (
    build_pipeline, FEATURE_COLS, inverse_transform_close,
    normalize_ticker, get_currency_symbol, DEFAULT_START_DATE,
)
from lstm_model import build_lstm_model, get_callbacks, save_model


_ARTIFACT_CACHE: dict[str, dict] = {}
_ARTIFACT_CACHE_LOCK = Lock()


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


# ─────────────────────────────────────────────
# ARGUMENT PARSER
# ─────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Train LSTM stock-price predictor")
    p.add_argument("--ticker",    default="RELIANCE.NS",  help="Stock ticker symbol (e.g. RELIANCE.NS, TCS.NS, AAPL)")
    p.add_argument("--start",     default=DEFAULT_START_DATE, help="Start date (default: 20 years ago)")
    p.add_argument("--window",    type=int, default=60,  help="Look-back window")
    p.add_argument("--horizon",   type=int, default=1,   help="Days ahead to predict")
    p.add_argument("--epochs",    type=int, default=100, help="Max training epochs")
    p.add_argument("--batch",     type=int, default=32,  help="Batch size")
    p.add_argument("--lr",        type=float, default=1e-3, help="Learning rate")
    p.add_argument("--dropout",   type=float, default=0.2,  help="Dropout rate")
    p.add_argument("--attention", action="store_true", default=True,
                   help="Use temporal attention")
    p.add_argument("--bidir",     action="store_true", default=False,
                   help="Use Bidirectional LSTM")
    p.add_argument("--split",     type=float, default=0.80,  help="Train ratio")
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

    pipeline = build_pipeline(
        ticker         = ticker,
        window_size    = args.window,
        forecast_horizon = args.horizon,
        split_ratio    = args.split,
        start_date     = args.start,
        scaler_save_path = scaler_path,
    )

    X_train = pipeline["X_train"]
    X_test  = pipeline["X_test"]
    y_train = pipeline["y_train"]
    y_test  = pipeline["y_test"]
    scaler  = pipeline["scaler"]
    df_feat = pipeline["df_featured"]

    n_features = X_train.shape[2]

    # ── 2. Build Model ────────────────────────
    model = build_lstm_model(
        window_size      = args.window,
        n_features       = n_features,
        forecast_horizon = args.horizon,
        lstm_units       = (128, 64),
        dropout_rate     = args.dropout,
        learning_rate    = args.lr,
        use_attention    = args.attention,
        use_bidirectional = args.bidir,
    )

    # ── 3. Train ──────────────────────────────
    callbacks = get_callbacks(ckpt_path, patience=15)

    history = model.fit(
        X_train, y_train,
        validation_data = (X_test, y_test),
        epochs     = args.epochs,
        batch_size = args.batch,
        callbacks  = callbacks,
        verbose    = 1,
        shuffle    = False   # Time-series: NO shuffling
    )

    train_time = time.time() - t0
    print(f"\n[Train] Completed in {train_time:.1f}s")

    # ── 4. Evaluate ───────────────────────────
    metrics = evaluate_model(model, X_test, y_test, scaler,
                             n_features, args.horizon)
    print(f"\n[Eval] RMSE  = {metrics['rmse']:.4f}")
    print(f"[Eval] MAE   = {metrics['mae']:.4f}")
    print(f"[Eval] MAPE  = {metrics['mape']:.2f}%")
    print(f"[Eval] R²    = {metrics['r2']:.4f}")

    # ── 5. Save Artefacts ─────────────────────
    save_model(model, model_path)

    config = {
        "ticker":          ticker,
        "window_size":     args.window,
        "forecast_horizon": args.horizon,
        "n_features":      n_features,
        "feature_cols":    FEATURE_COLS,
        "split_ratio":     args.split,
        "epochs_trained":  len(history.history["loss"]),
        "metrics":         metrics,
        "train_time_sec":  round(train_time, 1),
        "model_path":      model_path,
        "scaler_path":     scaler_path,
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"[Train] Config saved → {config_path}")

    # ── 6. Plots ──────────────────────────────
    _plot_training_history(history, ticker_dir, ticker)
    _plot_predictions(
        model, X_test, y_test, scaler,
        df_feat, n_features, args.horizon,
        ticker, ticker_dir
    )

    return config


# ─────────────────────────────────────────────
# EVALUATION
# ─────────────────────────────────────────────

def evaluate_model(
    model,
    X_test:    np.ndarray,
    y_test:    np.ndarray,
    scaler,
    n_features: int,
    horizon:   int
) -> dict:
    """Compute RMSE, MAE, MAPE, R² on the test set (in original price scale)."""
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    y_pred_scaled = model.predict(X_test, verbose=0)

    # Inverse-transform to original price scale
    from data_pipeline import CLOSE_COL_IDX
    y_pred = inverse_transform_close(scaler, y_pred_scaled, CLOSE_COL_IDX, n_features)
    y_true = inverse_transform_close(scaler, y_test, CLOSE_COL_IDX, n_features)

    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae  = mean_absolute_error(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100
    r2   = r2_score(y_true, y_pred)
    da   = _directional_accuracy(y_true, y_pred)

    return {
        "rmse": round(float(rmse), 4),
        "mae":  round(float(mae),  4),
        "mape": round(float(mape), 4),
        "r2":   round(float(r2),   4),
        "directional_accuracy": round(float(da), 4),
    }


def _directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Fraction of days where predicted direction matches actual direction."""
    true_dir = np.diff(y_true)
    pred_dir = np.diff(y_pred)
    return np.mean(np.sign(true_dir) == np.sign(pred_dir))


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

    axes[1].plot(history.history["mae"],     label="Train MAE")
    axes[1].plot(history.history["val_mae"], label="Val MAE")
    axes[1].set_title("Mean Absolute Error")
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
    n_features, horizon, ticker, save_dir
):
    from data_pipeline import CLOSE_COL_IDX

    y_pred_sc = model.predict(X_test, verbose=0)
    y_pred = inverse_transform_close(scaler, y_pred_sc, CLOSE_COL_IDX, n_features)
    y_true = inverse_transform_close(scaler, y_test,    CLOSE_COL_IDX, n_features)

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
        normalize_data, FEATURE_COLS, CLOSE_COL_IDX,
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
    scaled, _ = normalize_data(df_feat, FEATURE_COLS, scaler_path)

    # Use the last `window` rows as starting sequence
    sequence = scaled[-window:]

    future_prices = []
    current_seq   = sequence.copy()

    for _ in range(n_days):
        x = current_seq[-window:].reshape(1, window, len(FEATURE_COLS))
        pred_scaled = model.predict(x, verbose=0)[0, 0]

        # Reconstruct full feature row for next step (repeat last row, update Close)
        next_row           = current_seq[-1].copy()
        next_row[CLOSE_COL_IDX] = pred_scaled
        current_seq        = np.vstack([current_seq, next_row])

        # Inverse-transform
        price = inverse_transform_close(scaler, np.array([[pred_scaled]]),
                                        CLOSE_COL_IDX, len(FEATURE_COLS))[0]
        future_prices.append(float(price))

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
