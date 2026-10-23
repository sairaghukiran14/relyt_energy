# Wind Forecast Monitor

Shows a UK day-ahead trading team the national wind forecast they would have seen at
decision time, next to what actually happened, and quantifies how wrong the forecast
usually is. Scope: GB national wind, January 2026 delivery days (2 Jan – 1 Feb 2026),
using Elexon BMRS data (FUELHH actuals, WINDFOR forecasts).

See [system_architecture.md](system_architecture.md) for the full design and the
two-phase plan. **This repo currently implements Phase 1.**

## What Phase 1 does

- Downloads and loads one month of Elexon data into PostgreSQL (offline; the live app
  never calls Elexon).
- Selects, for each target hour, the latest forecast published **at or before** the
  day-ahead cutoff (11:00 UK on D-1) — no look-ahead.
- Computes error metrics: MAE, RMSE, bias, normalised MAE, P10/P50/P90/P99, max error,
  coverage, and the headline P90 shortfall ("safety margin").
- Two screens: **Overview** (metric tiles + actual-vs-forecast line chart over a date
  range) and **Day-ahead** (one delivery day at the cutoff, error bars per hour, day
  totals in MWh).

Phase 2 (fixed-horizon mode, the Accuracy-analysis screen, Methodology page, CSV
download, Vercel/Neon deployment, CI) is designed but not yet built.

## Quick start (Docker)

```bash
docker compose up --build
```

Then load the data once (in another terminal):

```bash
docker compose exec backend uv run python ../scripts/fetch_elexon.py
```

Open http://localhost:5173. The browser talks only to that origin; `/api` is proxied
to the backend, so there is no CORS setup — the same single-origin model Vercel uses.

## Quick start (without Docker)

Requires Python 3.12, Node 20, and a local PostgreSQL.

```bash
# 1. Database
createdb relyt
export DATABASE_URL=postgresql+psycopg://localhost/relyt

# 2. Backend
cd backend
uv sync
uv run alembic upgrade head
uv run python ../scripts/fetch_elexon.py     # download + load Elexon data
uv run uvicorn app.main:app --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev                                   # proxies /api to :8000
```

Open http://localhost:5173.

## Data notes

- All times are UTC. January has no daylight saving, so UK time equals UTC.
- WINDFOR is hourly; FUELHH actuals are half-hourly. Per the spec, v1 compares only at
  matching hours (no interpolation), so the comparison grid is hourly and coverage is
  the share of those hours with a usable forecast at the cutoff.
- `error = forecast − actual` (MW). Positive means the forecast was too high (wind fell
  short, so the team under-bought).

## API

FastAPI, JSON, auto docs at http://localhost:8000/docs.

| Endpoint | Returns |
| --- | --- |
| `GET /api/health` | status, DB connectivity, data last-loaded time |
| `GET /api/series` | per target hour: actual, forecast used, publish time, error |
| `GET /api/dayahead/{date}` | one delivery day at the 11:00 D-1 cutoff + day totals |
| `GET /api/metrics` | MAE, RMSE, bias, normalised MAE, P10/P50/P90/P99, max, coverage |

Common query params: `start`, `end` (ISO dates), `mode` (`dayahead` \| `horizon`),
`horizon_h` (0–48). Invalid input returns HTTP 422. (`mode=horizon` is wired in the API
for Phase 2; the Phase 1 UI uses day-ahead only.)

## Tests and linting

```bash
cd backend
createdb relyt_test                           # one-time
uv run pytest                                 # includes the no-look-ahead proof
uv run ruff check .

cd ../frontend
npm run build                                 # type-checks via tsc
```

`backend/tests/test_selection.py` proves no forecast published after the cutoff is ever
used; `test_metrics.py` checks metrics against hand-computed values.

## Layout

```
relyt_energy/
  backend/    FastAPI app (api/, services/ selection+metrics, db/ models+migrations), tests
  frontend/   React + Vite + TypeScript + Recharts + React Query
  scripts/    fetch_elexon.py (download + load)
  docker-compose.yml
  system_architecture.md
```

## AI tools

This project was built with the help of AI coding tools (Claude Code).
