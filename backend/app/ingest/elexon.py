"""Download FUELHH (wind actuals) and WINDFOR (wind forecasts) from Elexon BMRS,
clean them, and upsert into PostgreSQL.

January 2026 is fixed history, so this runs offline (not at request time). Re-running
is safe: loading is idempotent via INSERT ... ON CONFLICT DO UPDATE.

Observed Elexon stream shapes (confirmed against the live API):
  FUELHH:  {startTime, generation, fuelType, settlementPeriod, ...}
  WINDFOR: {startTime, publishTime, generation, ...}
All times are UTC. January has no DST, so UK time equals UTC.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx
import pandas as pd
from sqlalchemy import Engine, text

from app.db.session import get_engine

log = logging.getLogger("ingest")

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

# Data window from the PRD (one day of padding so day-ahead forecasts are present).
ACTUALS_FROM = datetime(2025, 12, 31, tzinfo=UTC)
ACTUALS_TO = datetime(2026, 2, 2, tzinfo=UTC)
FORECAST_FROM = datetime(2025, 12, 30, tzinfo=UTC)
FORECAST_TO = datetime(2026, 2, 2, tzinfo=UTC)

MAX_HORIZON_H = 48.0
CHUNK_DAYS = 1  # split the window to avoid large/slow single calls


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_stream(client: httpx.Client, dataset: str, params: dict) -> list[dict]:
    resp = client.get(f"{BASE_URL}/datasets/{dataset}/stream", params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _fetch_chunked(dataset: str, start: datetime, end: datetime, extra: dict) -> list[dict]:
    """Fetch a dataset one day at a time, filtered by publish time."""
    rows: list[dict] = []
    with httpx.Client() as client:
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end)
            params = {
                "publishDateTimeFrom": _iso(cursor),
                "publishDateTimeTo": _iso(chunk_end),
                **extra,
            }
            batch = _fetch_stream(client, dataset, params)
            log.info("%s %s..%s -> %d rows", dataset, _iso(cursor), _iso(chunk_end), len(batch))
            rows.extend(batch)
            cursor = chunk_end
    return rows


def _clean_actuals(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["startTime", "generation"])
    df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
    df["generation_mw"] = pd.to_numeric(df["generation"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["generation_mw"])
    df = df[df["generation_mw"] >= 0]
    log.info("actuals: dropped %d missing/negative rows", before - len(df))

    # Keep the last row per settlement period (same start_time).
    df = df.sort_values("start_time").drop_duplicates("start_time", keep="last")
    return df[["start_time", "generation_mw"]]


def _clean_forecasts(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["startTime", "publishTime", "generation"])
    df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation_mw"] = pd.to_numeric(df["generation"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["generation_mw"])
    df = df[df["generation_mw"] >= 0]
    log.info("forecasts: dropped %d missing/negative rows", before - len(df))

    # Drop duplicates on (start_time, publish_time), keep last.
    df = df.sort_values(["start_time", "publish_time"]).drop_duplicates(
        ["start_time", "publish_time"], keep="last"
    )

    df["horizon_h"] = (
        df["start_time"] - df["publish_time"]
    ).dt.total_seconds() / 3600.0
    before = len(df)
    df = df[(df["horizon_h"] >= 0) & (df["horizon_h"] <= MAX_HORIZON_H)]
    log.info("forecasts: dropped %d rows outside 0..48h horizon", before - len(df))
    return df[["start_time", "publish_time", "generation_mw", "horizon_h"]]


def _upsert_actuals(engine: Engine, df: pd.DataFrame) -> None:
    stmt = text(
        """
        INSERT INTO actual_generation (start_time, generation_mw, loaded_at)
        VALUES (:start_time, :generation_mw, now())
        ON CONFLICT (start_time)
        DO UPDATE SET generation_mw = EXCLUDED.generation_mw, loaded_at = now()
        """
    )
    with engine.begin() as conn:
        conn.execute(stmt, df.to_dict("records"))


def _upsert_forecasts(engine: Engine, df: pd.DataFrame) -> None:
    stmt = text(
        """
        INSERT INTO wind_forecast (start_time, publish_time, generation_mw, horizon_h, loaded_at)
        VALUES (:start_time, :publish_time, :generation_mw, :horizon_h, now())
        ON CONFLICT (start_time, publish_time)
        DO UPDATE SET generation_mw = EXCLUDED.generation_mw,
                      horizon_h = EXCLUDED.horizon_h,
                      loaded_at = now()
        """
    )
    with engine.begin() as conn:
        conn.execute(stmt, df.to_dict("records"))


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    engine = get_engine()

    log.info("Fetching FUELHH (wind actuals)...")
    actuals = _clean_actuals(
        _fetch_chunked("FUELHH", ACTUALS_FROM, ACTUALS_TO, {"fuelType": "WIND"})
    )
    _upsert_actuals(engine, actuals)
    log.info("Loaded %d actual rows", len(actuals))

    log.info("Fetching WINDFOR (wind forecasts)...")
    forecasts = _clean_forecasts(_fetch_chunked("WINDFOR", FORECAST_FROM, FORECAST_TO, {}))
    _upsert_forecasts(engine, forecasts)
    log.info("Loaded %d forecast rows", len(forecasts))


if __name__ == "__main__":
    run()
