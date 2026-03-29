#!/usr/bin/env bash
# start.sh — Start the StockOracle backend
# Usage: bash start.sh

VENV="/Users/divyebhatnagar/Desktop/Stock Market/stock-prediction/.venv"
BACKEND="/Users/divyebhatnagar/Desktop/Stock Market/stock-prediction/backend"

echo "🚀 Starting StockOracle backend (Python 3.12 venv)..."
cd "$BACKEND"
"$VENV/bin/uvicorn" main:app --reload --host 0.0.0.0 --port 8000
