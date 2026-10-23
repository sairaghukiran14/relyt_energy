"""Forecast selection: the no-look-ahead rule.

For every target time T, use only the latest forecast published at or before the
cutoff for T. No forecast published after the cutoff is ever used, so the numbers
match what a buyer really had at decision time.

  Day-ahead mode: cutoff(T) = 11:00 UK time on the day before T's delivery date.
  Horizon mode:   cutoff(T) = T - H hours.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import DAYAHEAD_CUTOFF_HOUR, LOCAL_TZ

_UK = ZoneInfo(LOCAL_TZ)


def dayahead_cutoff(delivery_day: date) -> datetime:
    """11:00 UK time on the day before the delivery day, returned in UTC."""
    d_minus_1 = delivery_day - timedelta(days=1)
    local = datetime.combine(d_minus_1, time(DAYAHEAD_CUTOFF_HOUR), tzinfo=_UK)
    return local.astimezone(UTC)


def _series_dayahead(session: Session, start: datetime, end: datetime) -> pd.DataFrame:
    """Latest forecast at the per-day 11:00 D-1 cutoff, joined to actuals.

    Each target time's cutoff depends on its own delivery day, so the cutoff is
    computed in SQL from start_time in UK time.
    """
    sql = text(
        """
        WITH targets AS (
            SELECT DISTINCT start_time
            FROM   wind_forecast
            WHERE  start_time >= :start AND start_time < :end
        ),
        picked AS (
            SELECT DISTINCT ON (f.start_time)
                   f.start_time, f.publish_time, f.generation_mw AS forecast_mw, f.horizon_h
            FROM   wind_forecast f
            WHERE  f.start_time >= :start AND f.start_time < :end
              AND  f.publish_time <= (
                       date_trunc('day', (f.start_time AT TIME ZONE 'Europe/London'))
                       - interval '1 day'
                       + make_interval(hours => :cutoff_hour)
                   ) AT TIME ZONE 'Europe/London'
            ORDER BY f.start_time, f.publish_time DESC
        )
        SELECT t.start_time, a.generation_mw AS actual_mw,
               p.forecast_mw, p.publish_time, p.horizon_h
        FROM   targets t
        LEFT JOIN actual_generation a ON a.start_time = t.start_time
        LEFT JOIN picked p ON p.start_time = t.start_time
        ORDER BY t.start_time
        """
    )
    rows = session.execute(
        sql, {"start": start, "end": end, "cutoff_hour": DAYAHEAD_CUTOFF_HOUR}
    ).mappings().all()
    return _to_frame(rows)


def _series_horizon(
    session: Session, start: datetime, end: datetime, horizon_h: float
) -> pd.DataFrame:
    """Latest forecast published at or before T - H, joined to actuals."""
    sql = text(
        """
        WITH targets AS (
            SELECT DISTINCT start_time
            FROM   wind_forecast
            WHERE  start_time >= :start AND start_time < :end
        ),
        picked AS (
            SELECT DISTINCT ON (f.start_time)
                   f.start_time, f.publish_time, f.generation_mw AS forecast_mw, f.horizon_h
            FROM   wind_forecast f
            WHERE  f.start_time >= :start AND f.start_time < :end
              AND  f.publish_time <= f.start_time - make_interval(hours => :h)
            ORDER BY f.start_time, f.publish_time DESC
        )
        SELECT t.start_time, a.generation_mw AS actual_mw,
               p.forecast_mw, p.publish_time, p.horizon_h
        FROM   targets t
        LEFT JOIN actual_generation a ON a.start_time = t.start_time
        LEFT JOIN picked p ON p.start_time = t.start_time
        ORDER BY t.start_time
        """
    )
    rows = session.execute(
        sql, {"start": start, "end": end, "h": int(horizon_h)}
    ).mappings().all()
    return _to_frame(rows)


def _to_frame(rows) -> pd.DataFrame:
    df = pd.DataFrame(
        rows,
        columns=["start_time", "actual_mw", "forecast_mw", "publish_time", "horizon_h"],
    )
    if df.empty:
        return df
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    for col in ("actual_mw", "forecast_mw", "horizon_h"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # error = forecast - actual (positive => forecast too high, wind fell short)
    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]
    return df


def get_series(
    session: Session,
    start: datetime,
    end: datetime,
    mode: str = "dayahead",
    horizon_h: float = 24.0,
) -> pd.DataFrame:
    """Return per-target-time actual, forecast used, publish time and error.

    The target-time grid is the set of start_times present in WINDFOR (hourly in v1),
    so comparison happens only at matching hours, with no interpolation. Rows where no
    forecast existed before the cutoff keep forecast_mw / error_mw as NaN (gaps);
    callers drop them for metrics and report coverage.
    """
    if mode == "horizon":
        return _series_horizon(session, start, end, horizon_h)
    return _series_dayahead(session, start, end)
