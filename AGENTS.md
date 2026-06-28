# AGENTS.md

## Cursor Cloud specific instructions

This repo is a Chinese A-share stock/fund analysis tool: a FastAPI backend (`backend/`) plus a React + Vite frontend (`frontend/`). Standard setup/run commands are documented in `README.md` and `CLAUDE.md` — refer to those. The notes below are the non-obvious caveats discovered during environment setup.

### Services
- **Backend (FastAPI/Uvicorn)** on port `8000`. Run from the `backend/` dir. Console scripts (`uvicorn`) install to `~/.local/bin`, which is not on `PATH`, so start it via the module form: `python3 -m uvicorn main:app --reload --port 8000`.
- **Frontend (Vite dev server)** on port `5173`. Run `npm run dev` from `frontend/`. Vite proxies `/api` → `http://localhost:8000`, so the backend must be running for any stock/fund data to render.
- The update script handles dependency installation (`pip install` + `npm install`); do not re-run those to "fix" a running service.

### Non-obvious caveats
- **Outbound internet is required for real data.** The backend pulls live quotes from `akshare` / `baostock` / EastMoney HTTP endpoints (no API key). Both servers will *start* without internet, but pages will show empty/404 data. Internet access works in this environment.
- **Redis is optional.** Defaults to `localhost:6379`; if unreachable the app logs a warning and runs with caching disabled (everything still works). No Redis is installed by default here, and it is not needed for development/testing.
- **SQLite is embedded** — `backend/data/stocks.db` and tables are auto-created on first run; no migrations.
- **First history request for a stock is slow** and may briefly 404 in the browser console while the backend fetches from akshare and caches to SQLite; data appears on retry. This is expected on-demand behavior, not a bug.
- **Trading-hours scheduler:** the 30s realtime prefetch only runs during China market hours (09:30–11:30, 13:00–15:00). Outside those hours on-demand API requests still fetch live data, so testing is unaffected.

### Lint / Test / Build
- **No linter** is configured (no ESLint config, no Python lint setup) and **no automated test suite** exists in this repo.
- Frontend production build: `npm run build` (from `frontend/`) — succeeds; warns about a large (>500 kB) chunk, which is pre-existing and harmless.
