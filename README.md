# Wind Forecast Monitor

Shows a UK day-ahead trading team the national wind forecast they would have seen at
decision time, next to what actually happened, and quantifies how wrong the forecast
usually is. Scope: GB national wind, January 2026 delivery days (2 Jan – 1 Feb 2026),
using Elexon BMRS data (FUELHH actuals, WINDFOR forecasts).

See [system_architecture.md](system_architecture.md) for the full design and the
two-phase plan. **This repo implements Phase 1 and Phase 2.**

## What it does

- Downloads and loads one month of Elexon data into PostgreSQL (offline; the live app
  never calls Elexon).
- Selects, for each target hour, the latest forecast published **at or before** the
  cutoff — no look-ahead. Two cutoff modes: **day-ahead** (11:00 UK on D-1) and
  **fixed-horizon** (T − H, H = 0–48 h).
- Computes error metrics: MAE, RMSE, bias, normalised MAE, P10/P50/P90/P99, max error,
  coverage, and the headline P90 shortfall ("safety margin"), plus breakdowns by
  horizon, by hour of day, by wind level, and an error histogram.
- Four screens: **Overview** (metric tiles + actual-vs-forecast line chart, with the
  mode toggle), **Day-ahead** (one delivery day at the cutoff, error bars per hour, day
  totals in MWh), **Accuracy** (the breakdowns + a percentile table, each table
  downloadable as CSV), and **Methodology** (data sources, cutoff rule, definitions).
- Deploys to Vercel (React static + FastAPI serverless under `/api`, single origin) with
  Neon Postgres; GitHub Actions runs lint + tests on every push.

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
| `GET /api/metrics/by-horizon` | MAE, RMSE, bias per forecast-horizon hour |
| `GET /api/metrics/by-hour` | the same, per hour of day |
| `GET /api/metrics/by-wind-level` | the same, split into low/medium/high actual wind |
| `GET /api/errors/histogram` | error bins and counts |

Common query params: `start`, `end` (ISO dates), `mode` (`dayahead` \| `horizon`),
`horizon_h` (0–48). Invalid input returns HTTP 422.

## Tests and linting

```bash
cd backend
createdb relyt_test                           # one-time
uv run pytest                                 # unit + end-to-end smoke tests
uv run ruff check .

cd ../frontend
npm test                                      # Vitest (CSV + query-string logic)
npm run lint
npm run build                                 # type-checks via tsc, then bundles
```

`backend/tests/test_selection.py` proves no forecast published after the cutoff is ever
used; `test_metrics.py` checks metrics against hand-computed values;
`test_smoke.py` drives the full HTTP stack against a seeded database. GitHub Actions
([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs all of this on every push.

## Layout

```
relyt_energy/
  backend/    FastAPI app (api/, services/ selection+metrics, db/ models+migrations), tests
  frontend/   React + Vite + TypeScript + Recharts + React Query
  scripts/    fetch_elexon.py (download + load)
  api/        index.py — Vercel entry point loading the FastAPI app
  vercel.json routes /api/* to FastAPI, everything else to the React build
  .github/    workflows/ci.yml (lint + tests on every push)
  docker-compose.yml
  system_architecture.md
```

## Deploying to Vercel

One Vercel project serves the React build as a static site and the FastAPI app as a
Python serverless function under `/api` (`api/index.py`, routed by `vercel.json`), so
both share one origin. Set `DATABASE_URL` (a Neon pooled connection string) in the
project's environment variables, then run migrations and load data against that database
once. The app is read-only and never calls Elexon at request time.

## AI tools

This project was built with the help of AI coding tools (Claude Code).
