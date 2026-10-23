from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api import deps, schemas
from app.db.models import ActualGeneration
from app.db.session import get_session
from app.services import metrics as metrics_svc
from app.services import selection

router = APIRouter(prefix="/api")

# The comparison grid is hourly (WINDFOR is hourly), so each point represents one
# hour: day-total energy MWh = sum(MW) * 1h. Actual and forecast totals use the same
# matched hourly grid so they are directly comparable.
PERIOD_HOURS = 1.0


def _points(df: pd.DataFrame) -> list[schemas.SeriesPoint]:
    if df.empty:
        return []
    records = df.replace({float("nan"): None}).to_dict("records")
    return [
        schemas.SeriesPoint(
            start_time=r["start_time"],
            actual_mw=r["actual_mw"],
            forecast_mw=r["forecast_mw"],
            publish_time=r["publish_time"],
            error_mw=r["error_mw"],
        )
        for r in records
    ]


@router.get("/health", response_model=schemas.HealthResponse)
def health(session: Session = Depends(get_session)) -> schemas.HealthResponse:
    try:
        session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    last_loaded = None
    if db_ok:
        last_loaded = session.execute(select(func.max(ActualGeneration.loaded_at))).scalar()
    return schemas.HealthResponse(
        status="ok" if db_ok else "degraded",
        database=db_ok,
        data_last_loaded=last_loaded,
    )


@router.get("/series", response_model=schemas.SeriesResponse)
def series(
    rng: tuple[datetime, datetime] = Depends(deps.parse_range),
    mode: str = Depends(deps.parse_mode),
    horizon_h: float = Depends(deps.parse_horizon),
    session: Session = Depends(get_session),
) -> schemas.SeriesResponse:
    start, end = rng
    df = selection.get_series(session, start, end, mode=mode, horizon_h=horizon_h)
    return schemas.SeriesResponse(
        mode=mode,
        horizon_h=horizon_h if mode == "horizon" else None,
        points=_points(df),
    )


@router.get("/metrics", response_model=schemas.Metrics)
def metrics(
    rng: tuple[datetime, datetime] = Depends(deps.parse_range),
    mode: str = Depends(deps.parse_mode),
    horizon_h: float = Depends(deps.parse_horizon),
    session: Session = Depends(get_session),
) -> schemas.Metrics:
    start, end = rng
    df = selection.get_series(session, start, end, mode=mode, horizon_h=horizon_h)
    return schemas.Metrics(**metrics_svc.compute_metrics(df))


@router.get("/dayahead/{date}", response_model=schemas.DayAheadResponse)
def dayahead(
    date: str,
    session: Session = Depends(get_session),
) -> schemas.DayAheadResponse:
    day = deps.parse_delivery_day(date)
    start = datetime.combine(day, time(), tzinfo=UTC)
    end = start + timedelta(days=1)
    df = selection.get_series(session, start, end, mode="dayahead")

    actual_mwh = forecast_mwh = None
    if not df.empty:
        if df["actual_mw"].notna().any():
            actual_mwh = float(df["actual_mw"].sum() * PERIOD_HOURS)
        if df["forecast_mw"].notna().any():
            forecast_mwh = float(df["forecast_mw"].sum() * PERIOD_HOURS)

    return schemas.DayAheadResponse(
        date=day.isoformat(),
        cutoff=selection.dayahead_cutoff(day),
        points=_points(df),
        actual_mwh=actual_mwh,
        forecast_mwh=forecast_mwh,
        metrics=schemas.Metrics(**metrics_svc.compute_metrics(df)),
    )
