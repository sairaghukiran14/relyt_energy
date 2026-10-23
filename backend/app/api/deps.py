"""Shared request parsing and validation for the API layer."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException, Query

from app.config import FIRST_DELIVERY_DAY, LAST_DELIVERY_DAY


def parse_range(
    start: date = Query(FIRST_DELIVERY_DAY),
    end: date = Query(LAST_DELIVERY_DAY),
) -> tuple[datetime, datetime]:
    """Validate a date range and return UTC [start, end) datetimes.

    `end` is inclusive of the whole delivery day, so we add one day.
    """
    if end < start:
        raise HTTPException(422, "end must be on or after start")
    start_dt = datetime.combine(start, time(), tzinfo=UTC)
    end_dt = datetime.combine(end + timedelta(days=1), time(), tzinfo=UTC)
    return start_dt, end_dt


def parse_mode(mode: str = Query("dayahead")) -> str:
    if mode not in ("dayahead", "horizon"):
        raise HTTPException(422, "mode must be 'dayahead' or 'horizon'")
    return mode


def parse_horizon(horizon_h: float = Query(24.0)) -> float:
    if not 0 <= horizon_h <= 48:
        raise HTTPException(422, "horizon_h must be between 0 and 48")
    return horizon_h


def parse_delivery_day(d: str) -> date:
    try:
        parsed = date.fromisoformat(d)
    except ValueError as exc:
        raise HTTPException(422, "date must be ISO format YYYY-MM-DD") from exc
    if not FIRST_DELIVERY_DAY <= parsed <= LAST_DELIVERY_DAY:
        raise HTTPException(
            422,
            f"date must be between {FIRST_DELIVERY_DAY} and {LAST_DELIVERY_DAY}",
        )
    return parsed
