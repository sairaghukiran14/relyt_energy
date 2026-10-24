from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: bool
    data_last_loaded: datetime | None
    # Short reason when the DB check fails (no credentials), for ops diagnosis.
    detail: str | None = None


class SeriesPoint(BaseModel):
    start_time: datetime
    actual_mw: float | None
    forecast_mw: float | None
    publish_time: datetime | None
    error_mw: float | None


class SeriesResponse(BaseModel):
    mode: str
    horizon_h: float | None
    points: list[SeriesPoint]


class Metrics(BaseModel):
    n: int
    coverage: float
    mae: float | None
    rmse: float | None
    bias: float | None
    nmae: float | None
    p10: float | None
    p50: float | None
    p90: float | None
    p99: float | None
    max_abs_error: float | None
    p90_shortfall_mw: float | None


class DayAheadResponse(BaseModel):
    date: str
    cutoff: datetime
    points: list[SeriesPoint]
    actual_mwh: float | None
    forecast_mwh: float | None
    metrics: Metrics


class GroupedMetric(BaseModel):
    key: int
    n: int
    mae: float
    rmse: float
    bias: float


class WindLevelMetric(BaseModel):
    band: str
    lo_mw: float
    hi_mw: float
    n: int
    mae: float | None
    rmse: float | None
    bias: float | None


class Histogram(BaseModel):
    bins: list[float]
    counts: list[int]
