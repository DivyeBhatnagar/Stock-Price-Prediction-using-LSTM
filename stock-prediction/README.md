# Stock Price Prediction using LSTM 📈

> An end-to-end AI system for stock price forecasting powered by Long Short-Term Memory (LSTM) neural networks, a FastAPI backend, and a React + TailwindCSS dashboard. **Fully supports the Indian Stock Market (NSE/BSE)** with ₹ INR currency, 30+ curated Indian stocks, and NIFTY/SENSEX indices — alongside US market support.

---

## 🇮🇳 Indian Market Support

This project is **India-first** with full support for:

### Supported Indian Stocks (30+ NSE Stocks)
| Symbol | Company | Sector |
|--------|---------|--------|
| RELIANCE.NS | Reliance Industries | Energy / Conglomerate |
| TCS.NS | Tata Consultancy Services | IT Services |
| INFY.NS | Infosys | IT Services |
| HDFCBANK.NS | HDFC Bank | Banking |
| ICICIBANK.NS | ICICI Bank | Banking |
| SBIN.NS | State Bank of India | Banking |
| ITC.NS | ITC Limited | FMCG |
| LT.NS | Larsen & Toubro | Infrastructure |
| BHARTIARTL.NS | Bharti Airtel | Telecom |
| TATAMOTORS.NS | Tata Motors | Automobile |
| BAJFINANCE.NS | Bajaj Finance | Finance |
| WIPRO.NS | Wipro | IT Services |
| HCLTECH.NS | HCL Technologies | IT Services |
| MARUTI.NS | Maruti Suzuki | Automobile |
| SUNPHARMA.NS | Sun Pharma | Pharma |
| TITAN.NS | Titan Company | Consumer Goods |
| HINDUNILVR.NS | Hindustan Unilever | FMCG |
| AXISBANK.NS | Axis Bank | Banking |
| KOTAKBANK.NS | Kotak Mahindra Bank | Banking |
| ADANIENT.NS | Adani Enterprises | Conglomerate |
| *... and 10 more* | | |

### Indian Market Indices
| Symbol | Index | Description |
|--------|-------|-------------|
| ^NSEI | **NIFTY 50** | NSE benchmark (50 large-caps) |
| ^NSEBANK | **BANK NIFTY** | NSE banking sector index |
| ^BSESN | **SENSEX** | BSE benchmark (30 stocks) |

### Ticker Auto-Conversion
You can enter bare ticker names — they are automatically converted to NSE format:
- `RELIANCE` → `RELIANCE.NS`
- `TCS` → `TCS.NS`
- `INFY` → `INFY.NS`
- US tickers like `AAPL`, `TSLA` are kept as-is

### Currency Display
- **Indian stocks**: All prices shown in **₹ (INR)** with Indian numbering (lakhs/crores)
- **US stocks**: Prices shown in **$ (USD)**
- Automatic detection based on ticker suffix (.NS / .BO)

### Data Range
- **20 years** of historical data downloaded by default (vs. the previous 10 years)
- Provides richer training data for more accurate predictions

---

## 🏗️ Architecture

```
                    ┌─────────────────────┐
                    │   React Frontend     │
                    │  (Vite + Tailwind)   │
                    │                     │
                    │  • Price Charts      │
                    │  • Candlestick       │
                    │  • Technical Inds.   │
                    │  • Forecast Table    │
                    │  • Training Panel    │
                    └──────────┬──────────┘
                               │  HTTP/JSON
                    ┌──────────▼──────────┐
                    │    FastAPI Backend   │
                    │    (Port 8000)       │
                    │                     │
                    │  GET  /api/stock     │
                    │  POST /api/train     │
                    │  GET  /api/predict   │
                    │  GET  /api/metrics   │
                    └──────────┬──────────┘
                               │
              ┌────────────────▼──────────────────┐
              │          ML Pipeline               │
              │                                    │
              │  yfinance → Feature Eng.            │
              │  → Normalize → Window              │
              │  → LSTM+Attention → Forecast       │
              └────────────────────────────────────┘
```

## 🧠 ML Architecture

```
Input (60 days × 16 features)
       ↓
LSTM Layer 1 (128 units, return_sequences=True)
       ↓
BatchNorm + Dropout (0.2)
       ↓
LSTM Layer 2 (64 units, return_sequences=True)
       ↓
BatchNorm + Dropout (0.2)
       ↓
Temporal Attention Layer
       ↓
Dense (64) → Dropout → Dense (32)
       ↓
Output: N-day forecast
```

**16 Input Features:**
`Open, High, Low, Close, Volume, SMA_20, SMA_50, EMA_20, RSI, MACD, MACD_Signal, BB_Upper, BB_Lower, BB_Width, ATR, Return`

---

## 📦 Tech Stack

| Layer       | Technology                      | Why                                     |
|-------------|----------------------------------|------------------------------------------|
| ML          | TensorFlow / Keras              | Production-grade LSTM support            |
| Data        | yfinance, Pandas, NumPy         | Free real-time financial data            |
| Preprocessing | Scikit-learn (MinMaxScaler)   | Reliable normalization                   |
| Backend     | FastAPI + Uvicorn               | Async, auto-docs, Pydantic validation    |
| Frontend    | React + Vite                    | Fast HMR, modern ecosystem               |
| Styling     | TailwindCSS v3                  | Utility-first, dark theme                |
| Charts      | Recharts                        | React-native charts, composable          |
| Icons       | Lucide React                    | Consistent icon set                      |

---

## 📁 Project Structure

```
stock-prediction/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── models/              # Saved models (auto-created)
│       └── {TICKER}/
│           ├── model.keras
│           ├── scaler.pkl
│           └── config.json
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── TickerSearch.jsx
│   │   │   ├── PriceChart.jsx
│   │   │   ├── CandlestickChart.jsx
│   │   │   ├── IndicatorChart.jsx
│   │   │   ├── MetricsPanel.jsx
│   │   │   ├── TrainingPanel.jsx
│   │   │   ├── StockInfoBar.jsx
│   │   │   └── ForecastTable.jsx
│   │   ├── hooks/
│   │   │   └── useStock.js
│   │   ├── pages/
│   │   │   └── Dashboard.jsx
│   │   └── utils/
│   │       └── api.js
│   ├── index.html
│   ├── tailwind.config.js
│   └── package.json
├── model/
│   ├── data_pipeline.py     # Data fetch + feature engineering
│   ├── lstm_model.py        # LSTM architecture
│   ├── train.py             # Training script (CLI)
│   └── evaluate.py          # Evaluation report
├── data/
│   ├── raw/                 # Downloaded CSVs
│   └── processed/           # Scalers
├── notebooks/
│   └── lstm_exploration.ipynb
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python ≥ 3.10
- Node.js ≥ 18
- pip

---

### 1. Backend Setup

```bash
cd stock-prediction/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: **http://localhost:8000/docs**

---

### 2. Train a Model

**Option A — CLI (recommended for first run):**
```bash
cd stock-prediction/model
python train.py --ticker RELIANCE.NS --epochs 100 --window 60 --horizon 1
```

**Option B — From the frontend:**
1. Open the dashboard
2. Enter a ticker
3. Click **"Train Model"** tab → **"Start Training"**

**Option C — Jupyter Notebook:**
```bash
cd stock-prediction/notebooks
jupyter notebook lstm_exploration.ipynb
```

---

### 3. Frontend Setup

```bash
cd stock-prediction/frontend

# Install dependencies
npm install

# Copy env file
cp .env.example .env

# Start dev server
npm run dev
```

Dashboard available at: **http://localhost:5173**

---

## 📊 API Reference

| Method | Endpoint                    | Description                         |
|--------|-----------------------------|--------------------------------------|
| GET    | `/`                         | Health check                         |
| GET    | `/api/stock/{ticker}`       | Historical OHLCV + indicators        |
| POST   | `/api/train`                | Start background training job        |
| GET    | `/api/train/status/{ticker}`| Check training progress              |
| GET    | `/api/predict/{ticker}`     | Get N-day price forecast             |
| GET    | `/api/metrics/{ticker}`     | Model evaluation metrics             |
| GET    | `/api/tickers`              | List trained models                  |
| GET    | `/api/compare`              | Multi-ticker forecast comparison     |
| GET    | `/api/india/tickers`        | 🇮🇳 Curated Indian NSE stocks + indices |
| GET    | `/api/market/info/{ticker}` | 🇮🇳 Market metadata (exchange, currency, hours) |

### Train Request Body
```json
{
  "ticker": "RELIANCE.NS",
  "window": 60,
  "horizon": 1,
  "epochs": 100,
  "batch_size": 32,
  "learning_rate": 0.001,
  "dropout": 0.2,
  "attention": true,
  "bidirectional": false
}
```

---

## 🧪 Evaluation Metrics

| Metric | Description                              | Good Value     |
|--------|-------------------------------------------|----------------|
| RMSE   | Root Mean Squared Error (₹ / $)           | < ₹50 / $5     |
| MAE    | Mean Absolute Error (₹ / $)               | < ₹30 / $3     |
| MAPE   | Mean Absolute Percentage Error            | < 5%           |
| R²     | Coefficient of Determination              | > 0.90         |
| DA     | Directional Accuracy                      | > 55%          |

---

## ⚡ Advanced Features

- **🇮🇳 Indian Market First** — NSE/BSE tickers, ₹ INR display, NIFTY/SENSEX indices
- **Auto Ticker Conversion** — Enter "RELIANCE" and it auto-converts to "RELIANCE.NS"
- **20-Year Data** — Downloads 20 years of historical data for richer training
- **Temporal Attention** — Self-attention over LSTM outputs (focuses on important time-steps)
- **Bidirectional LSTM** — Processes sequences in both directions (optional)
- **16 Technical Indicators** — Gives the model rich market context
- **Multi-ticker comparison** — Compare forecasts across tickers
- **Candlestick charts** — Professional OHLC visualization
- **CSV export** — Download prediction results
- **Hyperparameter tuning** — Adjust all parameters via the UI
- **Market Info Bar** — Shows exchange, currency, trading hours, market status

---

## 🔧 CLI Training Options

```
python train.py [OPTIONS]

Options:
  --ticker   TEXT    Stock symbol         [default: RELIANCE.NS]
  --start    TEXT    Start date           [default: 20 years ago]
  --window   INT     Look-back window     [default: 60]
  --horizon  INT     Days ahead           [default: 1]
  --epochs   INT     Max epochs           [default: 100]
  --batch    INT     Batch size           [default: 32]
  --lr       FLOAT   Learning rate        [default: 0.001]
  --dropout  FLOAT   Dropout rate         [default: 0.2]
  --attention        Enable attention     [flag]
  --bidir            Bidirectional LSTM   [flag]
```

### Quick Examples — Indian Stocks
```bash
# Train on Reliance Industries (NSE)
python train.py --ticker RELIANCE.NS --epochs 100

# Train on TCS
python train.py --ticker TCS.NS --epochs 80 --window 90

# Train on NIFTY 50 index
python train.py --ticker ^NSEI --epochs 120

# Train on US stock (still works)
python train.py --ticker AAPL --epochs 100
```

---

## 🐳 Docker (Optional)

```bash
# Backend
docker build -t stock-backend ./backend
docker run -p 8000:8000 stock-backend

# Frontend
docker build -t stock-frontend ./frontend
docker run -p 5173:5173 stock-frontend
```

---

## ⚠️ Disclaimer

This tool is for **educational purposes only**. Stock price predictions are inherently uncertain. Do **not** use these predictions for actual investment decisions.

---

## 📜 License

MIT — Free to use, modify, and distribute.
