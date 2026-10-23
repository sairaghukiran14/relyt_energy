"""End-to-end smoke test: seed a day of data, then drive the real HTTP app
(routing, selection, metrics, Pydantic serialization) through FastAPI's TestClient.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db.models import ActualGeneration, WindForecast
from app.db.session import get_session
from app.main import app
from tests.conftest import utc


@pytest.fixture
def client(engine):
    """TestClient wired to the test database via a dependency override."""
    Session = sessionmaker(bind=engine)

    def _override():
        with Session() as s:
            yield s

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _seed_full_day(engine, day):
    """24 hourly target times for one delivery day, each with a before- and an
    after-cutoff forecast, plus actuals."""
    Session = sessionmaker(bind=engine)
    cutoff = utc(day.year, day.month, day.day) - timedelta(hours=13)  # 11:00 D-1
    with Session() as s:
        for h in range(24):
            target = utc(day.year, day.month, day.day, h)
            s.add(ActualGeneration(start_time=target, generation_mw=1000.0 + h))
            # Latest before cutoff (should be used): forecast 1200.
            s.add(
                WindForecast(
                    start_time=target,
                    publish_time=cutoff - timedelta(hours=1),
                    generation_mw=1200.0 + h,
                    horizon_h=(target - (cutoff - timedelta(hours=1))).total_seconds() / 3600,
                )
            )
            # After cutoff (must be ignored even though it is "better").
            s.add(
                WindForecast(
                    start_time=target,
                    publish_time=cutoff + timedelta(hours=1),
                    generation_mw=1000.0 + h,
                    horizon_h=(target - (cutoff + timedelta(hours=1))).total_seconds() / 3600,
                )
            )
        s.commit()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"] is True


def test_dayahead_end_to_end(client, engine):
    day = utc(2026, 1, 15).date()
    _seed_full_day(engine, day)

    r = client.get(f"/api/dayahead/{day.isoformat()}")
    assert r.status_code == 200
    body = r.json()

    assert len(body["points"]) == 24
    assert body["metrics"]["coverage"] == 1.0
    # The before-cutoff forecast (1200+h) was used, not the after-cutoff one (1000+h).
    assert body["points"][0]["forecast_mw"] == 1200.0
    # error = forecast - actual = 1200 - 1000 = 200 at hour 0.
    assert body["points"][0]["error_mw"] == 200.0
    assert body["metrics"]["bias"] == 200.0


def test_breakdowns_end_to_end(client, engine):
    day = utc(2026, 1, 16).date()
    _seed_full_day(engine, day)
    params = {"start": day.isoformat(), "end": day.isoformat()}

    assert client.get("/api/metrics/by-hour", params=params).status_code == 200
    assert len(client.get("/api/metrics/by-hour", params=params).json()) == 24
    wind = client.get("/api/metrics/by-wind-level", params=params).json()
    assert {b["band"] for b in wind} == {"low", "medium", "high"}
    hist = client.get("/api/errors/histogram", params=params).json()
    assert sum(hist["counts"]) == 24


def test_invalid_inputs_return_422(client):
    assert client.get("/api/series?mode=nope").status_code == 422
    assert client.get("/api/dayahead/2025-06-01").status_code == 422
    assert client.get("/api/series?mode=horizon&horizon_h=99").status_code == 422
