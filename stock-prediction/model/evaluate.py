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
    build_pipeline, FEATURE_COLS, CLOSE_COL_IDX, inverse_transform_close,
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
    return p.parse_args()


def full_evaluation(ticker, window=60, horizon=1, model_dir="../backend/models", start="2015-01-01"):
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
        scaler_save_path=scaler_path
    )
    X_test, y_test = pipeline["X_test"], pipeline["y_test"]
    scaler         = pipeline["scaler"]
    n_features     = X_test.shape[2]

    # Load model
    model = load_model(model_path)

    # Predict
    y_pred_sc = model.predict(X_test, verbose=0)
    y_pred = inverse_transform_close(scaler, y_pred_sc, CLOSE_COL_IDX, n_features)
    y_true = inverse_transform_close(scaler, y_test,    CLOSE_COL_IDX, n_features)

    # Metrics
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae  = float(mean_absolute_error(y_true, y_pred))
    mape = float(np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + 1e-10))) * 100)
    r2   = float(r2_score(y_true, y_pred))
    da   = float(np.mean(np.sign(np.diff(y_true)) == np.sign(np.diff(y_pred))))

    report = {
        "ticker": ticker,
        "rmse":  round(rmse, 4),
        "mae":   round(mae,  4),
        "mape":  round(mape, 4),
        "r2":    round(r2,   4),
        "directional_accuracy": round(da, 4),
        "test_samples": len(y_true),
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
        args.ticker, args.window, args.horizon, args.model_dir, args.start
    )
    print("\n📊 Evaluation Report")
    print(json.dumps(report, indent=2))
