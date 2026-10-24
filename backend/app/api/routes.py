from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.api import deps, schemas
from app.config import database_url
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


def _safe_target() -> str:
    """driver@host/db for the configured DB — no username or password."""
    try:
        u = make_url(database_url())
        return f"{u.drivername}@{u.host}/{u.database}"
    except Exception:
        return "unparseable DATABASE_URL"


@router.get("/health", response_model=schemas.HealthResponse)
def health(session: Session = Depends(get_session)) -> schemas.HealthResponse:
    detail = None
    try:
        session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_ok = False
        detail = f"{type(exc).__name__}: {str(exc)[:180]} | target={_safe_target()}"
    last_loaded = None
    if db_ok:
        last_loaded = session.execute(select(func.max(ActualGeneration.loaded_at))).scalar()
    return schemas.HealthResponse(
        status="ok" if db_ok else "degraded",
        database=db_ok,
        data_last_loaded=last_loaded,
        detail=detail,
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


def _series_for(session, rng, mode, horizon_h) -> pd.DataFrame:
    start, end = rng
    return selection.get_series(session, start, end, mode=mode, horizon_h=horizon_h)


@router.get("/metrics/by-horizon", response_model=list[schemas.GroupedMetric])
def metrics_by_horizon(
    rng: tuple[datetime, datetime] = Depends(deps.parse_range),
    mode: str = Depends(deps.parse_mode),
    horizon_h: float = Depends(deps.parse_horizon),
    session: Session = Depends(get_session),
) -> list[schemas.GroupedMetric]:
    df = _series_for(session, rng, mode, horizon_h)
    return [schemas.GroupedMetric(**g) for g in metrics_svc.metrics_by_horizon(df)]


@router.get("/metrics/by-hour", response_model=list[schemas.GroupedMetric])
def metrics_by_hour(
    rng: tuple[datetime, datetime] = Depends(deps.parse_range),
    mode: str = Depends(deps.parse_mode),
    horizon_h: float = Depends(deps.parse_horizon),
    session: Session = Depends(get_session),
) -> list[schemas.GroupedMetric]:
    df = _series_for(session, rng, mode, horizon_h)
    return [schemas.GroupedMetric(**g) for g in metrics_svc.metrics_by_hour(df)]


@router.get("/metrics/by-wind-level", response_model=list[schemas.WindLevelMetric])
def metrics_by_wind_level(
    rng: tuple[datetime, datetime] = Depends(deps.parse_range),
    mode: str = Depends(deps.parse_mode),
    horizon_h: float = Depends(deps.parse_horizon),
    session: Session = Depends(get_session),
) -> list[schemas.WindLevelMetric]:
    df = _series_for(session, rng, mode, horizon_h)
    return [schemas.WindLevelMetric(**g) for g in metrics_svc.metrics_by_wind_level(df)]


@router.get("/errors/histogram", response_model=schemas.Histogram)
def errors_histogram(
    rng: tuple[datetime, datetime] = Depends(deps.parse_range),
    mode: str = Depends(deps.parse_mode),
    horizon_h: float = Depends(deps.parse_horizon),
    bins: int = 20,
    session: Session = Depends(get_session),
) -> schemas.Histogram:
    df = _series_for(session, rng, mode, horizon_h)
    return schemas.Histogram(**metrics_svc.error_histogram(df, bins=bins))
