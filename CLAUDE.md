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
│   ├── strategy.py      # /api/strategy/* routes (technical buy/sell signals, strategy definitions)
│   └── comparison.py    # /api/comparison route (multi-stock comparison with normalization)
├── services/
│   ├── stock_service.py    # Data fetching (EastMoney primary, baostock fallback)
│   ├── history_loader.py   # Period resolution + warm-up window + local/remote orchestration
│   ├── indicator_service.py# Pure-python indicators: MACD/MA/EMA/RSI/KDJ/BOLL/ATR/Donchian
│   ├── strategy_service.py # 13 technical strategies, backtest, weighted composite scoring
│   ├── data_service.py     # Database CRUD, comparison logic, data normalization
│   └── cache_service.py    # Redis operations (30s realtime, 4h history, 1h strategy)
├── models/
│   ├── database.py      # SQLAlchemy SQLite engine, Stock & StockHistory ORM models
│   └── schemas.py       # Pydantic request/response models
├── scripts/
│   ├── verify_indicators.py # Indicator correctness + look-ahead-bias guard
│   └── verify_backtest.py   # Backtest stats vs random-signal baseline
└── tasks/
    └── scheduler.py     # APScheduler: realtime cache update every 30s (trading hours only), daily history update at 15:30
```

**Data flow for history requests:**
1. Check Redis cache
2. If miss, `load_history_with_warmup` reads SQLite over `[start - warmup, end]`
3. If local data is missing, incomplete at the head, or stale at the tail, refetch the whole window remotely (single source, avoids forward-adjusted price splicing jumps) and persist
4. Compute indicators on the full warm-up series, then trim back to the requested range

**Data flow for realtime requests:**
1. Check Redis cache
2. If miss, fetch from the Tencent quote API (`StockService.get_realtime_data`), cache to Redis

**Database:** SQLite file auto-created at `backend/data/stocks.db` on first run. Tables: `stocks` (basic info), `stock_history` (daily K-line). No migrations — schema is created via `Base.metadata.create_all()`.

**Redis configuration:** Defaults to `localhost:6379`. Override via `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` environment variables. The app runs without Redis (prints warning), but caching is disabled.

### Frontend Structure

```
frontend/src/
├── main.jsx              # React 18 root, BrowserRouter, Ant Design zh_CN locale
├── App.jsx               # Layout with Sider menu, Header search, Routes
├── pages/
│   ├── StockDetail.jsx   # Realtime stats + StrategySignalPanel + StockChart, polls every 30s
│   └── ComparisonPage.jsx # Wrapper that passes initial code from router state
└── components/
    ├── StockChart.jsx    # ECharts candlestick + MA lines + volume + MACD, buy/sell markPoints,
    │                     #   period (1m/3m/6m/1y/all), frequency (d/w/m), signal show/hide toggle
    ├── StrategySignalPanel.jsx # Composite verdict + confidence dial + fired strategies + ATR risk levels
    ├── StockComparison.jsx # Multi-line ECharts comparison, supports normalize (return %) vs raw price
    └── StockSearch.jsx   # AutoComplete search component, calls /api/stocks/search
```

**Routing:**
- `/` → redirects to `/detail/600519`
- `/detail/:code` → stock detail page
- `/comparison` → comparison page (can receive initial code via `location.state`)

**Proxy:** Vite dev server proxies `/api` to `http://localhost:8000`. In production, nginx handles the proxy (see `frontend/nginx.conf`).

### Notable Implementation Details

- **Market code convention:** `_market_prefix()` in `stock_service.py` maps codes to markets — `4/8/92xxxx` → Beijing, `6/5/9` → Shanghai (covers 6xxxxx stocks, 5xxxxx ETF/LOF, 900xxx B-shares), everything else → Shenzhen. EastMoney secid uses prefix `1.` for Shanghai and `0.` for Shenzhen/Beijing.
- **History data source:** EastMoney `push2his` is primary (covers stocks, ETFs, LOFs, indices, all of d/w/m); baostock is the fallback and only covers A-shares. Some networks reset HTTPS to EastMoney, so `_eastmoney_get()` retries over http then https.
- **Trading hours check:** Scheduler only fetches realtime data during 09:30–11:30 and 13:00–15:00.
- **Comparison normalization:** When `normalize=true`, comparison data is calculated as `(close - first_close) / first_close * 100` (percentage return).
- **Error handling pattern:** Services print errors to stdout and return `None`/`[]`. API routes translate missing data to `HTTPException(404)` or empty lists.

### Technical Strategy Signals

`/api/strategy/signals/{code}` returns per-strategy status, historical buy/sell markers, backtest stats, and a composite verdict (买入/观望/卖出) with a 0–100 confidence.

- **13 strategies across 4 families** registered in `strategy_service.STRATEGIES`: trend (MA cross, MA alignment, MA200 regime filter), momentum (MACD cross/zero-axis/divergence, RSI extremes, RSI regime), volatility (Bollinger squeeze breakout, Bollinger mean reversion, KDJ cross), breakout (Donchian 20/55).
- **No look-ahead bias is the hard invariant.** `Strategy.evaluate(rows, i)` may only read `rows[0..i]`; backtest entries are at the *next* bar's close; divergence detection only uses swing points already confirmed by bar `i`. `scripts/verify_indicators.py` enforces this by recomputing indicators on a truncated copy and requiring identical values.
- **Donchian channels use `rows[i-p:i]`, excluding the current bar** — including it makes `close > upper` mathematically impossible.
- **Bollinger squeeze uses a percentile rank of bandwidth**, not an absolute threshold, so it transfers across instruments (ETF volatility is roughly half that of a single stock).
- **Composite weighting is in-sample.** Weights come from full-sample backtest win rates, Bayesian-shrunk toward 0.5 and clamped to `[0.2, 1.0]`. This is disclosed in every response via `methodology.in_sample_weighting`. Do not add parameter optimization — it would turn a defensible heuristic into curve fitting.
- **Always framed as a research signal, never advice.** `DISCLAIMER` is hardcoded in the service (not the route) and the UI shows a non-dismissible warning banner.
- **Verification:** no test framework in the repo. Run `./venv/bin/python scripts/verify_indicators.py` (27 checks incl. pandas cross-validation and the look-ahead guard) and `scripts/verify_backtest.py` (win rates vs a random-signal baseline, since a bull sample can give random entries a 65% win rate).
