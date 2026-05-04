"""
Train a selected list of stocks and save metrics to a table file.

Usage:
    python scripts/train_selected_stocks.py
    python scripts/train_selected_stocks.py --tickers RELIANCE.NS,TCS.NS,HDFCBANK.NS,TITAN.NS,SBIN.NS
    python scripts/train_selected_stocks.py --out ../data/metrics_selected_stocks.md
"""

import os
import sys
import json
import argparse
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "model"))

from data_pipeline import normalize_ticker, DEFAULT_START_DATE
from train import train as lstm_train

DEFAULT_TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "TITAN.NS",
    "SBIN.NS",
]


class _Args:
    pass


def _build_args(cli_args, ticker: str):
    a = _Args()
    a.ticker = ticker
    a.start = cli_args.start
    a.window = cli_args.window
    a.horizon = cli_args.horizon
    a.epochs = cli_args.epochs
    a.batch = cli_args.batch
    a.lr = cli_args.lr
    a.dropout = cli_args.dropout
    a.attention = cli_args.attention
    a.bidir = cli_args.bidir
    a.single_task = cli_args.single_task
    a.split = cli_args.split
    a.val_ratio = cli_args.val_ratio
    a.direction_only = cli_args.direction_only
    a.direction_bigmove = cli_args.direction_bigmove
    a.direction_threshold = cli_args.direction_threshold
    a.output = cli_args.output
    a.scale = cli_args.scale
    a.lstm_units = cli_args.lstm_units
    a.cnn = cli_args.cnn
    a.walk_forward = cli_args.walk_forward
    a.wf_splits = cli_args.wf_splits
    return a


def _to_markdown_table(rows):
    headers = [
        "Ticker", "RMSE", "MAE", "MAPE", "R2",
        "DirAcc", "Precision", "Recall", "F1", "Coverage",
        "TrainTimeSec",
    ]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        line = "| {ticker} | {rmse} | {mae} | {mape} | {r2} | {diracc} | {precision} | {recall} | {f1} | {coverage} | {train_time} |".format(**r)
        lines.append(line)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Train selected stocks and save metrics to a table file")
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS),
                        help="Comma-separated tickers")
    parser.add_argument("--start", default=DEFAULT_START_DATE,
                        help="Start date (default: 10 years ago)")
    parser.add_argument("--window", type=int, default=60)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--dropout", type=float, default=0.15)
    parser.add_argument("--attention", action="store_true", default=True)
    parser.add_argument("--bidir", action="store_true", default=True)
    parser.add_argument("--single-task", action="store_true", default=False)
    parser.add_argument("--split", type=float, default=0.85)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--direction-only", action="store_true", default=False)
    parser.add_argument("--direction-bigmove", action="store_true", default=False)
    parser.add_argument("--direction-threshold", type=float, default=0.0)
    parser.add_argument("--scale", choices=["minmax", "standard", "robust"], default="standard")
    parser.add_argument("--lstm-units", default="256,128,64")
    parser.add_argument("--cnn", action="store_true", default=False)
    parser.add_argument("--walk-forward", action="store_true", default=False)
    parser.add_argument("--wf-splits", type=int, default=3)
    parser.add_argument("--output", default=os.path.join(ROOT, "backend", "models"))
    parser.add_argument("--out", default=os.path.join(ROOT, "data", "metrics_selected_stocks.md"),
                        help="Output metrics table file")
    args = parser.parse_args()

    tickers = [normalize_ticker(t.strip()) for t in args.tickers.split(",") if t.strip()]
    results = []

    for tkr in tickers:
        result = lstm_train(_build_args(args, tkr))
        metrics = result.get("metrics", {})
        results.append({
            "ticker": tkr,
            "rmse": metrics.get("rmse", "-"),
            "mae": metrics.get("mae", "-"),
            "mape": metrics.get("mape", "-"),
            "r2": metrics.get("r2", "-"),
            "diracc": metrics.get("directional_accuracy", "-"),
            "precision": metrics.get("precision", "-"),
            "recall": metrics.get("recall", "-"),
            "f1": metrics.get("f1", "-"),
            "coverage": metrics.get("coverage", "-"),
            "train_time": result.get("train_time_sec", "-"),
        })

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    md = _to_markdown_table(results)
    with open(args.out, "w") as f:
        f.write("# Stock Training Metrics\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write(md)
        f.write("\n")

    # Also save raw JSON next to the table
    json_path = os.path.splitext(args.out)[0] + ".json"
    with open(json_path, "w") as f:
        json.dump({"generated": datetime.now().isoformat(), "results": results}, f, indent=2)

    print(f"Saved metrics table → {args.out}")
    print(f"Saved raw metrics  → {json_path}")


if __name__ == "__main__":
    main()
