#!/usr/bin/env bash
# setup.sh  —  One-command project setup
# Usage: bash setup.sh

set -e

echo "=================================================="
echo "  StockOracle — LSTM Stock Prediction Setup"
echo "=================================================="

# ── 1. Backend ────────────────────────────────────────
echo ""
echo "→ Setting up Python backend …"
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate
cd ..
echo "✅ Backend dependencies installed."

# ── 2. Frontend ───────────────────────────────────────
echo ""
echo "→ Installing frontend dependencies …"
cd frontend
npm install -q
cp .env.example .env 2>/dev/null || true
cd ..
echo "✅ Frontend dependencies installed."

# ── 3. Directories ────────────────────────────────────
mkdir -p data/raw data/processed backend/models
echo "✅ Data directories created."

echo ""
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "  To train a model:"
echo "    cd model && python train.py --ticker AAPL"
echo ""
echo "  To start the backend:"
echo "    cd backend && source .venv/bin/activate"
echo "    uvicorn main:app --reload --port 8000"
echo ""
echo "  To start the frontend:"
echo "    cd frontend && npm run dev"
echo ""
echo "  Open: http://localhost:5173"
echo "=================================================="
