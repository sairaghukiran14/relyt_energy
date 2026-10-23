# Wind Forecast Monitor: System Architecture

Derived from the Product Requirements Document (Oct 23, 2026). This document describes how the system is built, why, and how data moves through it.

## 1. Purpose and constraints

A web app that shows a UK day-ahead trading team the national wind forecast they would have seen at decision time, next to actual generation, with forecast-error metrics. Scope: GB national wind, January 2026 decisions (delivery days 2 Jan to 1 Feb 2026).

Architectural drivers:

| Driver | Consequence |
| --- | --- |
| Data is fixed history | Download once, load into PostgreSQL; the live app never calls Elexon |
| No look-ahead allowed | Forecast selection is a single, tested, back-end rule |
| Reviewer wants reproducibility | `docker compose up` runs everything; pinned dependencies |
| Free hosting, one URL | Single Vercel project; React static + FastAPI serverless; same origin, no CORS |
| Read-only, no personal data | No auth, no write endpoints, minimal security surface |

## 2. System context

```
 Elexon BMRS API          Ingestion script               PostgreSQL 16
 (FUELHH, WINDFOR)  --->  scripts/fetch_elexon.py  --->  actual_generation
 public, no key           clean + upsert (offline)       wind_forecast
                                                         (Neon in prod, Docker locally)
                                                              |
                                                              v
 +------------ Docker Compose (local) / Vercel (production) ------------+
 |                                                                       |
 |   React front end   <---- JSON over /api ----   FastAPI back end     |
 |   Vite, TypeScript,                             selection + metrics   |
 |   Recharts, React Query                         pandas, Pydantic      |
 +-----------------------------------------------------------------------+
          |
          v
   Buyer's browser (no login; charts; CSV download)
```

Two distinct phases:

1. **Offline ingestion** (run by a developer, not at request time): Elexon to PostgreSQL.
2. **Online serving** (read-only): browser to React to FastAPI to PostgreSQL.

Elexon is a build-time dependency only. If it is down, the app still works.

## 3. Components

### 3.1 Ingestion script (`scripts/fetch_elexon.py`)

- Fetches FUELHH (`fuelType=WIND`) for 1 Jan to 1 Feb 2026 and WINDFOR published 30 Dec 2025 to 1 Feb 2026, from `https://data.elexon.co.uk/bmrs/api/v1/datasets/{name}/stream`.
- Falls back to one-day chunks if a monthly call is too large or times out.
- Cleaning pipeline:
  1. Drop duplicates on (`startTime`, `publishTime`), keep last.
  2. Drop negative or missing values; log the count.
  3. Compute `horizon_h = startTime - publishTime` (hours); keep 0 to 48.
  4. If WINDFOR is hourly, keep matching hours only (no interpolation).
- Loads with upsert (`INSERT ... ON CONFLICT DO UPDATE`), so re-runs are idempotent. Stamps `loaded_at`.
- All timestamps UTC (January has no DST, so UK time equals UTC).
- Open item: stream field names are from Elexon docs and must be confirmed in the first exploration step.

### 3.2 Database (PostgreSQL 16)

| Table | Columns | Key / index |
| --- | --- | --- |
| `actual_generation` | `start_time`, `generation_mw`, `loaded_at` | PK `start_time` |
| `wind_forecast` | `start_time`, `publish_time`, `generation_mw`, `horizon_h`, `loaded_at` | PK (`start_time`, `publish_time`); index on `publish_time` |

- Managed by SQLAlchemy models and Alembic migrations.
- Neon free tier in production; a Docker container locally.
- Connection string comes from the `DATABASE_URL` environment variable only.

### 3.3 Back end (`backend/`, FastAPI)

Layered so business logic is independent of HTTP and the database driver:

```
backend/
  api/        Routers + Pydantic request/response models; validation (422 on bad input)
  services/   selection.py (forecast-at-cutoff), metrics.py (MAE, RMSE, bias, percentiles, ...)
  db/         SQLAlchemy models, session, Alembic migrations
  tests/      pytest
```

- **api**: thin; parses query params (`start`, `end`, `mode`, `horizon_h`), calls services, returns JSON.
- **services/selection**: the single place the no-look-ahead rule lives.
- **services/metrics**: pure pandas functions over a frame of (target time, actual, forecast, error); unit-testable with hand-computed values.
- **db**: all SQL, including the `DISTINCT ON` query.

All forecast selection and metric maths live here; the front end only renders.

### 3.4 Front end (`frontend/`, React + Vite + TypeScript)

```
frontend/
  pages/        Overview, DayAhead, Accuracy, Methodology
  components/   TopBar (date range, mode toggle, horizon slider), MetricTile, charts, CsvButton
  api/          typed client + React Query hooks
```

- Recharts for charts; React Query for caching and loading/empty/error states.
- Shared visual encoding: actual = solid line, forecast = dashed line, error = bars; colour-blind-safe palette.
- Top-bar state (range, mode, horizon) is shared across screens (URL query params are a good home so views are linkable).
- CSV export serialises the currently displayed table client-side.

### 3.5 Hosting and packaging

| Environment | Layout |
| --- | --- |
| Local | `docker-compose.yml`: `frontend`, `backend`, `postgres` services; one Dockerfile per service |
| Production | One Vercel project: React built as static site; FastAPI exposed via `api/index.py` as a Python serverless function; `vercel.json` routes `/api/*` to FastAPI, everything else to React |
| CI | GitHub Actions: Ruff, ESLint, pytest, Vitest on every push |

Same origin in both environments (local via a dev proxy or reverse proxy), so no CORS configuration.

## 4. Core logic

### 4.1 Forecast selection (no look-ahead)

For each target time `T`, use the newest forecast with `publish_time <= cutoff(T)`:

- **Day-ahead mode (default):** `cutoff(T) = 11:00 UK time on D-1`, where D is the delivery date of `T`. One decision per day.
- **Fixed-horizon mode:** `cutoff(T) = T - H`, H in 0 to 48 hours (default 24).

```sql
SELECT DISTINCT ON (f.start_time)
       f.start_time, f.publish_time, f.generation_mw AS forecast_mw
FROM   wind_forecast f
WHERE  f.start_time >= :start AND f.start_time < :end
  AND  f.publish_time <= :cutoff_expr      -- per-row cutoff, never after
ORDER  BY f.start_time, f.publish_time DESC;
```

The result is joined to `actual_generation` on `start_time`. Target times with no forecast before the cutoff appear as gaps, are excluded from metrics, and are counted (shown on screen as coverage).

### 4.2 Metrics

Error = forecast minus actual (MW); positive means forecast too high (wind fell short).

- MAE, RMSE, mean error (bias), normalised MAE (% of mean actual)
- Percentiles P10, P50, P90, P99; max absolute error; coverage
- Headline safety margin: P90 of shortfall (actual below forecast)
- Breakdowns: by horizon (hourly buckets 0 to 48), by hour of day, histogram, by wind level (low/medium/high)
- MAPE is deliberately excluded (unstable near zero actuals)

## 5. API surface

All `GET`, JSON, auto docs at `/docs`. Common params: `start`, `end`, `mode` (`dayahead` | `horizon`), `horizon_h` (0 to 48). Invalid input returns HTTP 422.

| Endpoint | Returns | Used by |
| --- | --- | --- |
| `/api/health` | status, DB connectivity, data last-loaded time | ops / smoke test |
| `/api/series` | per target time: actual, forecast used, publish time, error | Overview |
| `/api/dayahead/{date}` | one delivery day at the 11:00 D-1 cutoff + day totals (MWh) | Day-ahead view |
| `/api/metrics` | headline metrics | Overview tiles |
| `/api/metrics/by-horizon` | MAE, RMSE, bias per horizon hour | Accuracy |
| `/api/metrics/by-hour` | same per hour of day | Accuracy |
| `/api/errors/histogram` | bins and counts | Accuracy |

## 6. Request flow (example: Day-ahead view)

1. Buyer picks 15 Jan 2026 in the delivery date picker.
2. React Query calls `GET /api/dayahead/2026-01-15` (cached by key).
3. Router validates the date (within 2 Jan to 1 Feb 2026) and calls `services.selection`.
4. Selection computes cutoff = 14 Jan 2026 11:00 UK, runs the `DISTINCT ON` query, joins actuals.
5. `services.metrics` computes day totals and per-half-hour errors.
6. Pydantic serialises the response, including the "forecast published at" timestamp(s).
7. The page renders forecast (dashed) vs actual (solid), error bars, and totals.

Target: each API call under 500 ms; first page load under 3 s.

## 7. Cross-cutting concerns

| Concern | Approach |
| --- | --- |
| Correctness | Unit tests prove no forecast after the cutoff is ever used; metrics tested against hand-computed values; one end-to-end smoke test |
| Performance | PK/index on lookup columns; month-sized dataset (about 1.5k actuals, tens of thousands of forecast rows) is small; React Query caching |
| Reliability | Data pre-loaded; no runtime dependency on Elexon; idempotent ingestion |
| Security | Read-only; no PII; `DATABASE_URL` in env vars, never in code; same origin |
| Code quality | Type hints and Pydantic (Python), TypeScript, Ruff, ESLint, formatted code |
| Accessibility | Readable contrast, keyboard-usable controls, colour-blind-safe chart colours |
| Reproducibility | Pinned dependencies; `docker compose up` |

## 8. Technology choices

| Layer | Choice | Rationale |
| --- | --- | --- |
| Front end | React, Vite, TypeScript, Recharts, React Query | Fast build, typed, simple charts, cached calls |
| Back end | FastAPI, pandas, Pydantic | Typed, quick, auto docs; pandas suits metric maths |
| Storage | PostgreSQL 16, SQLAlchemy, Alembic | `DISTINCT ON` makes cutoff query one statement; Neon integrates with Vercel |
| Containers | Docker, Docker Compose | One-command local run |
| Hosting | Vercel (static + Python serverless) | Free, single URL, no CORS |
| CI | GitHub Actions | Lint and tests on each push |

## 9. Repository layout

```
relyt/
  frontend/            React + Vite + TypeScript
  backend/             FastAPI: api/, services/, db/, tests/, Dockerfile
  api/index.py         Vercel entry point loading the FastAPI app
  scripts/             fetch_elexon.py
  vercel.json          /api/* -> FastAPI, else React
  docker-compose.yml   frontend, backend, postgres
  README.md            setup, architecture notes, AI-tool-use disclosure
```

## 10. Risks and open questions

| Risk / question | Mitigation |
| --- | --- |
| Elexon stream field names unverified | Confirm in first data-exploration step before finalising schema |
| WINDFOR may be hourly vs half-hourly actuals | Compare only at matching hours in v1; no interpolation |
| Vercel serverless cold starts / DB connections | Use Neon pooled connection string; keep the function lightweight; avoid heavy imports at module load |
| Large monthly download timeouts | Chunk by day in the script |
| Day-ahead cutoff vs DST | Not an issue in January (UK = UTC); store UTC and convert only for cutoff rule |
| Missing forecasts before cutoff | Show gaps, exclude from metrics, display coverage |

## 11. Out of scope (v1)

Other data (demand, prices, solar, regional, weather), own forecast model, trading/alerts, login/roles, months other than January 2026.

## 12. Delivery phases

### Phase 1: Core slice (a buyer can answer "what did I see, and how wrong was it?")

Goal: meets the PRD success criterion end to end, running locally with one Docker command.

| Area | Features |
| --- | --- |
| Data | Data exploration to confirm Elexon fields; `fetch_elexon.py` with cleaning and idempotent upsert; Postgres schema + Alembic migrations |
| Back end | Day-ahead selection (11:00 D-1 cutoff, no look-ahead); core metrics (MAE, RMSE, bias, normalised MAE, P10/P50/P90/P99, max error, coverage); safety-margin number; `/api/health`, `/api/series`, `/api/dayahead/{date}`, `/api/metrics`; 422 validation |
| Front end | Top bar (date range, day-ahead only); Screen 1 Overview (metric tiles + actual vs forecast chart); Screen 2 Day-ahead view (error bars, "published at" label, MWh totals); loading/empty states |
| Packaging | Docker Compose (frontend, backend, Postgres); pinned dependencies |
| Quality | pytest proving no forecast after cutoff is used; metric tests against hand-computed values; Ruff + ESLint |

### Phase 2: Analysis, polish and production

Goal: team-lead analysis views, fixed-horizon mode, and a public, reviewed deployment.

| Area | Features |
| --- | --- |
| Back end | Fixed-horizon mode (`mode=horizon`, `horizon_h` 0 to 48); `/api/metrics/by-horizon`, `/api/metrics/by-hour`, `/api/errors/histogram`; error by wind level |
| Front end | Mode toggle and horizon slider; Screen 3 Accuracy analysis (by horizon, by hour, histogram, percentile table); Methodology page; CSV download; metric formula tooltips; mobile-friendly layout; accessibility pass (contrast, keyboard, colour-blind-safe palette) |
| Platform | Vercel deployment (`api/index.py`, `vercel.json`, Neon); GitHub Actions CI (lint + tests); Vitest for key front-end logic; end-to-end smoke test |
| Docs | README (setup, architecture, AI-tools-used note); public GitHub repo `relyt` |

### Rationale for the split

- Phase 1 contains everything on the critical path (data, selection rule, core metrics) and the two screens that deliver the PRD's 30-second success test.
- Fixed-horizon mode and the breakdowns are additive: they reuse the Phase 1 selection and metrics services with a different cutoff or grouping.
- Deployment is deferred so the Vercel/Neon constraints (cold starts, pooled connections) are tackled against a stable app, while Docker Compose keeps Phase 1 reproducible.
