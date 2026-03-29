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
    LOG_RETURN_COL_IDX, CLOSE_COL_IDX,
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
    p.add_argument("--epochs",    type=int, default=200, help="Max training epochs")
    p.add_argument("--batch",     type=int, default=64,  help="Batch size")
    p.add_argument("--lr",        type=float, default=3e-4, help="Learning rate")
    p.add_argument("--dropout",   type=float, default=0.15,  help="Dropout rate")
    p.add_argument("--attention", action="store_true", default=True,
                   help="Use temporal attention")
    p.add_argument("--bidir",     action="store_true", default=False,
                   help="Use Bidirectional LSTM")
    p.add_argument("--split",     type=float, default=0.85,  help="Train ratio")
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

    X_train          = pipeline["X_train"]
    X_test           = pipeline["X_test"]
    y_train          = pipeline["y_train"]
    y_test           = pipeline["y_test"]
    scaler           = pipeline["scaler"]
    df_feat          = pipeline["df_featured"]
    test_prev_closes = pipeline.get("test_prev_closes")

    n_features = X_train.shape[2]

    # ── 2. Build Model ────────────────────────
    model = build_lstm_model(
        window_size      = args.window,
        n_features       = n_features,
        forecast_horizon = args.horizon,
        lstm_units       = (256, 128, 64),
        dropout_rate     = args.dropout,
        learning_rate    = args.lr,
        use_attention    = args.attention,
        use_bidirectional = args.bidir,
    )

    # ── 3. Train ──────────────────────────────
    callbacks = get_callbacks(ckpt_path, patience=25)

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
                             n_features, args.horizon, test_prev_closes)
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
) -> dict:
    """
    Compute metrics on the test set.

    Target is next-day log return (stationary).  R² is measured on
    log returns — any model capturing a real signal scores > 0.
    RMSE / MAE / MAPE are reconstructed in price space via
        price_pred = prev_close * exp(log_return_pred).
    """
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    y_pred_scaled = model.predict(X_test, verbose=0)

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
    da   = _directional_accuracy(y_true_lr, y_pred_lr)

    return {
        "rmse": round(float(rmse), 4),
        "mae":  round(float(mae),  4),
        "mape": round(float(mape), 4),
        "r2":   round(float(r2),   4),
        "directional_accuracy": round(float(da), 4),
    }


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
    n_features, horizon, ticker, save_dir, test_prev_closes=None
):
    y_pred_sc = model.predict(X_test, verbose=0)
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
    scaled, _ = normalize_data(df_feat, FEATURE_COLS, scaler_path)

    # Use the last `window` rows as starting sequence
    sequence = scaled[-window:]

    future_prices = []
    current_seq   = sequence.copy()
    last_close    = df_feat["Close"].values[-1]   # seed with most recent actual close

    # Pre-compute close-column scale factors for fast re-scaling
    _min_c = scaler.data_min_[CLOSE_COL_IDX]
    _rng_c = scaler.data_max_[CLOSE_COL_IDX] - _min_c

    for _ in range(n_days):
        x = current_seq[-window:].reshape(1, window, len(FEATURE_COLS))
        pred_scaled = model.predict(x, verbose=0)[0, 0]

        # Inverse-transform scaled log return → actual log return → next price
        log_ret    = inverse_transform_close(scaler, np.array([[pred_scaled]]),
                                             LOG_RETURN_COL_IDX, len(FEATURE_COLS))[0]
        next_close = last_close * np.exp(float(log_ret))
        future_prices.append(float(next_close))

        # Advance sequence: copy last row, update log-return & close columns
        next_row = current_seq[-1].copy()
        next_row[LOG_RETURN_COL_IDX] = pred_scaled
        next_row[CLOSE_COL_IDX]      = (next_close - _min_c) / (_rng_c + 1e-10)
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
