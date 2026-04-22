# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an A-share stock analysis tool with real-time quotes, historical K-line charts, and multi-stock comparison. The backend fetches data from the free `akshare` data source (no API key needed). Data has a slight delay (seconds to minutes).

## Development Commands

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

API docs available at http://localhost:8000/docs after starting.

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev        # dev server on http://localhost:5173
npm run build      # production build to dist/
npm run preview    # preview production build
```

### Docker Compose

```bash
docker-compose up -d   # starts redis, backend, and frontend
```

Access at http://localhost. Frontend nginx proxies `/api` to the backend service.

### Redis

Required for caching. Start locally with `redis-server`, or via Docker:

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

## Architecture

### Backend Structure

```
backend/
├── main.py              # FastAPI app entry, CORS, lifespan (init DB + scheduler)
├── api/
│   ├── stocks.py        # /api/stocks/* routes (realtime, history, info, list, search, batch-realtime)
│   └── comparison.py    # /api/comparison route (multi-stock comparison with normalization)
├── services/
│   ├── stock_service.py # Data fetching from akshare (external A-share data source)
│   ├── data_service.py  # Database CRUD, comparison logic, data normalization
│   └── cache_service.py # Redis operations (30s TTL for realtime, 1h for history)
├── models/
│   ├── database.py      # SQLAlchemy SQLite engine, Stock & StockHistory ORM models
│   └── schemas.py       # Pydantic request/response models
└── tasks/
    └── scheduler.py     # APScheduler: realtime cache update every 30s (trading hours only), daily history update at 15:30
```

**Data flow for history requests:**
1. Check Redis cache
2. If miss, query SQLite (`DataService.load_from_database`)
3. If DB data insufficient (< 5 records), fetch from akshare (`StockService.get_historical_data`), save to DB, then cache to Redis

**Data flow for realtime requests:**
1. Check Redis cache
2. If miss, fetch from akshare (`StockService.get_realtime_data`), cache to Redis

**Database:** SQLite file auto-created at `backend/data/stocks.db` on first run. Tables: `stocks` (basic info), `stock_history` (daily K-line). No migrations — schema is created via `Base.metadata.create_all()`.

**Redis configuration:** Defaults to `localhost:6379`. Override via `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` environment variables. The app runs without Redis (prints warning), but caching is disabled.

### Frontend Structure

```
frontend/src/
├── main.jsx              # React 18 root, BrowserRouter, Ant Design zh_CN locale
├── App.jsx               # Layout with Sider menu, Header search, Routes
├── pages/
│   ├── StockDetail.jsx   # Realtime stats + StockChart, polls every 30s
│   └── ComparisonPage.jsx # Wrapper that passes initial code from router state
└── components/
    ├── StockChart.jsx    # ECharts candlestick + volume chart, period selector (1m/3m/6m/1y/all)
    ├── StockComparison.jsx # Multi-line ECharts comparison, supports normalize (return %) vs raw price
    └── StockSearch.jsx   # AutoComplete search component, calls /api/stocks/search
```

**Routing:**
- `/` → redirects to `/detail/600519`
- `/detail/:code` → stock detail page
- `/comparison` → comparison page (can receive initial code via `location.state`)

**Proxy:** Vite dev server proxies `/api` to `http://localhost:8000`. In production, nginx handles the proxy (see `frontend/nginx.conf`).

### Notable Implementation Details

- **akshare market convention:** Codes starting with `6` are `.SH` (Shanghai), all others are `.SZ` (Shenzhen). This logic lives in `stock_service.py`.
- **Trading hours check:** Scheduler only fetches realtime data during 09:30–11:30 and 13:00–15:00.
- **Comparison normalization:** When `normalize=true`, comparison data is calculated as `(close - first_close) / first_close * 100` (percentage return).
- **StockComparison component:** The Select dropdown for adding stocks is currently hardcoded with a few stock options. In production, it should ideally use the search API for a dynamic list.
- **Error handling pattern:** Services print errors to stdout and return `None`/`[]`. API routes translate missing data to `HTTPException(404)` or empty lists.
