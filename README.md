# 📈 StockOracle: AI-Powered Stock Price Prediction

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2-blue?style=flat-square&logo=react)](https://react.dev)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.16%2B-orange?style=flat-square&logo=tensorflow)](https://tensorflow.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**An intelligent, end-to-end AI system for predictive stock price forecasting** powered by advanced LSTM neural networks, real-time WebSocket streaming, and a beautiful modern dashboard.

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [API Docs](#-api-documentation) • [Live Streaming](#-live-data-streaming)

</div>

---

## ✨ Highlights

- 🇮🇳 **India-First**: Full NSE/BSE support with ₹ currency, 30+ curated Indian stocks, NIFTY 50 indices
- 🤖 **Advanced ML**: LSTM with attention mechanism, 10+ years of historical data, real-time predictions
- 📡 **Live Streaming**: WebSocket-powered real-time price updates with instant model predictions
- 🎨 **Modern UI**: React + TailwindCSS dashboard with interactive charts and responsive design
- 🐳 **Docker Ready**: One-command deployment with Docker Compose
- 📊 **Comprehensive Analytics**: Historical OHLCV data, technical indicators, evaluation metrics
- ⚡ **Production Ready**: Background data scheduler, async WebSocket manager, error handling

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (optional)

### Install & Run (Local Development)

```bash
# Clone the repository
git clone <repo-url>
cd stock-prediction

# Run setup script (installs Python deps + builds frontend)
bash setup.sh

# Start the backend
cd backend
python -m uvicorn main:app --reload --port 8000

# In another terminal, start the frontend
cd frontend
npm run dev
```

**Access the dashboard**: `http://localhost:5173`  
**API Documentation**: `http://localhost:8000/docs`

### Docker Deployment

```bash
# Build and run all services (backend, frontend, nginx)
docker-compose up --build

# Services will be available at:
# - Frontend:  http://localhost:80
# - API:       http://localhost:8000
# - Docs:      http://localhost:8000/docs
```

---

## 🌟 Features

### 🇮🇳 Comprehensive Indian Stock Market Support

**30+ NSE Stocks** across all major sectors:

| Category | Symbols |
|----------|---------|
| **Banking** | HDFCBANK, ICICIBANK, SBIN, AXISBANK, KOTAKBANK, SBILIFE |
| **IT Services** | TCS, INFY, WIPRO, HCLTECH, TECHM, LTIM |
| **Energy** | RELIANCE, ONGC, BPCL, COALINDIA, POWERGRID |
| **Automobile** | MARUTI, TATAMOTORS, HEROMOTOCO, EICHERMOT, M_AND_M |
| **Finance** | BAJFINANCE, BAJAJFINSV, SHRIRAMFIN |
| **Conglomerate** | ADANIENT, ADANIPORTS, GRASIM |
| **Consumer** | HINDUNILVR, NESTLEIND, TITAN, ITC, BRITANNIA |
| **Pharma** | SUNPHARMA, DRREDDY, CIPLA, DIVISLAB |
| **Infrastructure** | LT, JSWSTEEL, ULTRACEMCO |
| **Telecom** | BHARTIARTL |

**Market Indices**: NIFTY 50 (^NSEI), BANK NIFTY (^NSEBANK), SENSEX (^BSESN)

**Ticker Auto-Conversion**: Enter bare names (`RELIANCE` → `RELIANCE.NS`), US tickers kept as-is

### 🤖 Advanced Machine Learning

- **LSTM Architecture**: Bidirectional LSTM cells with attention mechanism
- **Deep Learning Stack**:
  - Input normalization with StandardScaler
  - Dual LSTM layers (128 → 64 units) with dropout regularization
  - Multi-head attention for temporal pattern capture
  - Dense output layers for horizon-based predictions
- **Training Features**:
  - 10+ years historical OHLCV data
  - Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands)
  - Early stopping & learning rate reduction
  - 80/10/10 train/validation/test split
- **Prediction Capabilities**:
  - Multi-step ahead forecasting (configurable horizon)
  - Confidence intervals & trend analysis
  - Real-time model serving

### 📡 Real-Time Live Streaming

- **WebSocket Server**: Bi-directional communication for instant updates
- **Live Price Updates**: Direct feeds from Yahoo Finance API
- **Instant Predictions**: Model predictions alongside live market data
- **Market Status Detection**: Automatic fallback to simulated prices during market closure
- **Message Format**:
  ```json
  {
    "type": "price",
    "symbol": "RELIANCE.NS",
    "price": 2534.50,
    "prediction": 2550.00,
    "trend": "up",
    "change": 24.50,
    "timestamp": "2026-03-12T09:30:00Z"
  }
  ```

### 🎨 Beautiful Dashboard

- **Interactive Charts**: Real-time candlestick charts with Recharts
- **Technical Analysis**: Overlay multiple indicators on price charts
- **Stock Search**: Quick search with ticker autocomplete
- **Responsive Design**: Mobile-friendly TailwindCSS interface
- **Performance Metrics**: Display model accuracy, MAE, RMSE
- **Multi-Stock Comparison**: View and compare multiple stocks simultaneously

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  ├─ Interactive Dashboard                                  │
│  ├─ Live Chart Component (Recharts)                        │
│  ├─ Stock Search & Autocomplete                            │
│  └─ Real-time WebSocket Updates                            │
└────────────┬────────────────────────────┬──────────────────┘
             │ REST API                    │ WebSocket WS://
             │ /api/stock                  │ /ws/live/{ticker}
┌────────────▼────────────────────────────▼──────────────────┐
│              Backend (FastAPI)                              │
│  ├─ Stock Data Routes      (/api/stock/{ticker})          │
│  ├─ Prediction Routes      (/api/predict/{ticker})        │
│  ├─ Training Routes        (/api/train)                   │
│  ├─ WebSocket Manager      (ConnectionManager)            │
│  ├─ Live Price Publisher   (yfinance → WS)              │
│  └─ Background Scheduler   (APScheduler)                  │
└────────────┬──────────────────────────────────────────────┘
             │
        ┌────▼─────────────────┐
        │  Data Pipeline       │
        │  ├─ Data Fetch       │
        │  ├─ Preprocessing    │
        │  ├─ LSTM Training    │
        │  └─ Model Storage    │
        └──────────────────────┘
```

### Project Structure

```
stock-prediction/
├── backend/              # FastAPI Application
│   ├── main.py          # Core API endpoints
│   ├── scheduler.py      # Background data scheduler
│   ├── ws_manager.py     # WebSocket connection management
│   ├── ws_publisher.py   # Live price streaming
│   ├── routes/          # API route modules
│   ├── models/          # Trained LSTM weights
│   └── tests/           # Unit & integration tests
│
├── frontend/            # React + Vite Application
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Page layouts
│   │   ├── hooks/       # React custom hooks
│   │   └── utils/       # Helper functions
│   ├── public/          # Static assets
│   └── vite.config.js   # Build configuration
│
├── model/               # ML Pipeline
│   ├── lstm_model.py    # LSTM architecture
│   ├── train.py         # Training script
│   ├── evaluate.py      # Evaluation metrics
│   ├── data_pipeline.py # Data preprocessing
│   └── live_data_manager.py
│
├── data/                # Data Storage
│   ├── raw/            # Downloaded CSV files
│   ├── processed/      # Preprocessed data
│   └── stocks/         # NIFTY 50 stock CSVs
│
├── scripts/            # Utility Scripts
│   ├── download_data.py
│   ├── preprocess.py
│   └── train_all_stocks.py
│
├── notebooks/          # Jupyter Notebooks
│   └── lstm_exploration.ipynb
│
├── docker-compose.yml  # Multi-container setup
├── Dockerfile.backend  # Backend container
├── Dockerfile.frontend # Frontend container
└── nginx.conf         # Reverse proxy config
```

---

## 🔌 API Documentation

### REST API Endpoints

#### Get Stock Data
```http
GET /api/stock/{ticker}
```
Returns historical OHLCV data + technical indicators

**Example**: `GET /api/stock/RELIANCE.NS`

```json
{
  "ticker": "RELIANCE.NS",
  "data": [
    {
      "date": "2026-03-12",
      "open": 2510.00,
      "high": 2545.00,
      "low": 2505.00,
      "close": 2534.50,
      "volume": 1234567,
      "sma_20": 2520.00,
      "ema_12": 2525.50,
      "rsi": 65.4
    }
  ]
}
```

#### Make Predictions
```http
GET /api/predict/{ticker}?days=5
```
Get N-day ahead price predictions with confidence intervals

**Response**:
```json
{
  "ticker": "RELIANCE.NS",
  "current_price": 2534.50,
  "predictions": [
    {"day": 1, "price": 2545.00, "confidence": 0.92},
    {"day": 2, "price": 2558.50, "confidence": 0.88},
    {"day": 3, "price": 2575.00, "confidence": 0.85},
    {"day": 4, "price": 2590.50, "confidence": 0.82},
    {"day": 5, "price": 2605.00, "confidence": 0.78}
  ],
  "trend": "up"
}
```

#### Get Model Metrics
```http
GET /api/metrics/{ticker}
```
Returns model performance (MAE, RMSE, R² score)

#### Train/Retrain Model
```http
POST /api/train
Content-Type: application/json

{
  "ticker": "RELIANCE.NS",
  "epochs": 100,
  "batch_size": 32
}
```

#### List Trained Models
```http
GET /api/tickers
```
Returns all available trained models

**Interactive Docs**: Visit `http://localhost:8000/docs` (Swagger UI)

---

## 📡 Live Data Streaming

Connect to WebSocket for real-time price updates and instant predictions:

```javascript
// Frontend Example (React)
const socket = new WebSocket('ws://localhost:8000/ws/live/RELIANCE.NS');

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Current Price: ₹${data.price}`);
  console.log(`ML Prediction: ₹${data.prediction}`);
  console.log(`Trend: ${data.trend}`);
};
```

### WebSocket Message Schema

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"price"` |
| `symbol` | string | Stock ticker |
| `price` | float | Current market price |
| `prediction` | float | Next-period forecast |
| `trend` | string | `"up"` / `"down"` / `"flat"` |
| `change` | float | Price change (₹) |
| `change_pct` | float | Percentage change |
| `timestamp` | ISO 8601 | Event timestamp |
| `simulated` | bool | `true` if market closed |

---

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (async, modern, fast)
- **ML/DL**: TensorFlow/Keras (LSTM, attention mechanisms)
- **Data**: pandas, NumPy, scikit-learn
- **Real-time**: WebSockets, APScheduler
- **Data Source**: yfinance (live market data)

### Frontend
- **Framework**: React 19 with Hooks
- **Build**: Vite (lightning-fast bundling)
- **Styling**: TailwindCSS (utility-first)
- **Charts**: Recharts (interactive visualizations)
- **HTTP**: Axios (REST client)

### Deployment
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Nginx
- **ASGI Server**: Uvicorn

---

## 📊 Training & Evaluation

### Data Pipeline

1. **Download** (10+ years): Yahoo Finance → CSV
2. **Preprocess**: Normalization, technical indicators, sequence creation
3. **Train/Val/Test**: 80/10/10 split with time-series awareness
4. **Model Training**: LSTM with early stopping & learning rate scheduling
5. **Evaluation**: MAE, RMSE, R² on test set

### Usage

```bash
# Download all NIFTY 50 stock data
python scripts/download_data.py

# Preprocess data
python scripts/preprocess.py

# Train models for all stocks
python scripts/train_all_stocks.py

# Or train a single stock
python model/train.py --ticker RELIANCE.NS --epochs 100
```

### Sample Outputs

```
Training RELIANCE.NS...
Epoch 1/100: loss=0.0124, val_loss=0.0156
...
Epoch 100/100: loss=0.0089, val_loss=0.0122

Evaluation Metrics:
├─ MAE:  ₹15.23
├─ RMSE: ₹18.94
└─ R²:   0.94
```

---

## 🧪 Testing

### Run Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend end-to-end tests
cd frontend
npm run test:e2e
```

### Test Coverage

- ✅ Stock data fetching
- ✅ Model prediction API
- ✅ WebSocket connections
- ✅ Training pipeline
- ✅ Live chart rendering
- ✅ Ticker autocomplete

---

## 🚀 Deployment

### Local Development

```bash
bash setup.sh
bash start.sh
```

### Docker Deployment

```bash
docker-compose up --build -d
```

### Environment Variables

Create `.env` in project root:

```bash
# Backend
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
LOG_LEVEL=INFO

# Frontend
VITE_API_BASE_URL=http://localhost:8000

# Data
DATA_DIR=./data
MODEL_DIR=./backend/models
```

---

## 📈 Performance Benchmarks

| Metric | Value | Notes |
|--------|-------|-------|
| **API Response Time** | <100ms | Cached predictions |
| **WebSocket Latency** | <50ms | Real-time price updates |
| **Model Training** | ~2-5 min | Single stock (GPU) |
| **Dashboard Load Time** | <2s | Optimized bundle |
| **Prediction Accuracy (R²)** | 0.85-0.94 | Varies by stock |

---

## 📚 Resources

- **FastAPI Docs**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Keras/TensorFlow**: [keras.io](https://keras.io)
- **React Documentation**: [react.dev](https://react.dev)
- **WebSocket Protocol**: [RFC 6455](https://tools.ietf.org/html/rfc6455)
- **Yahoo Finance API**: [yfinance docs](https://github.com/ranaroussi/yfinance)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### Development Guidelines

- ✅ Follow PEP 8 (Python) and ESLint (JavaScript)
- ✅ Write tests for new features
- ✅ Update documentation
- ✅ Keep commits atomic and descriptive

---

## 📝 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Stock-Prediction AI Pipeline** v3.0.0  
Created with ❤️ for Indian markets

---

## 📞 Support

- 📖 **Documentation**: See [LIVE_STREAMING.md](LIVE_STREAMING.md) for WebSocket setup
- 🐛 **Issues**: [GitHub Issues](issues)
- 💬 **Discussions**: [GitHub Discussions](discussions)

---

<div align="center">

**Made with 🚀 by traders, for traders**

If you find this project helpful, please ⭐ it!

</div>
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
