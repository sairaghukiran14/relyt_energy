"""The critical correctness property: no forecast published after the cutoff is used."""


from app.db.models import ActualGeneration, WindForecast
from app.services import selection
from tests.conftest import utc


def _add_actual(session, start, mw):
    session.add(ActualGeneration(start_time=start, generation_mw=mw))


def _add_forecast(session, start, publish, mw):
    horizon = (start - publish).total_seconds() / 3600.0
    session.add(
        WindForecast(start_time=start, publish_time=publish, generation_mw=mw, horizon_h=horizon)
    )


def test_dayahead_uses_latest_before_cutoff(session):
    # Delivery 15 Jan 2026, so cutoff is 14 Jan 11:00 UK = 11:00 UTC in January.
    target = utc(2026, 1, 15, 12, 0)
    _add_actual(session, target, 1000.0)
    # Three forecasts: two before the cutoff, one after.
    _add_forecast(session, target, utc(2026, 1, 14, 6, 0), 900.0)  # before
    _add_forecast(session, target, utc(2026, 1, 14, 10, 30), 950.0)  # latest before cutoff
    _add_forecast(session, target, utc(2026, 1, 14, 11, 30), 980.0)  # after cutoff: ignored
    session.commit()

    df = selection.get_series(session, utc(2026, 1, 15), utc(2026, 1, 16), mode="dayahead")
    row = df.iloc[0]
    assert row["forecast_mw"] == 950.0
    assert row["publish_time"] == utc(2026, 1, 14, 10, 30)


def test_dayahead_cutoff_is_11_uk_on_d_minus_1(session):
    assert selection.dayahead_cutoff(utc(2026, 1, 15).date()) == utc(2026, 1, 14, 11, 0)


def test_no_forecast_before_cutoff_is_a_gap(session):
    target = utc(2026, 1, 15, 12, 0)
    _add_actual(session, target, 1000.0)
    # Only a forecast published after the cutoff exists.
    _add_forecast(session, target, utc(2026, 1, 14, 15, 0), 980.0)
    session.commit()

    df = selection.get_series(session, utc(2026, 1, 15), utc(2026, 1, 16), mode="dayahead")
    assert df.iloc[0]["actual_mw"] == 1000.0
    assert df.iloc[0]["forecast_mw"] != df.iloc[0]["forecast_mw"]  # NaN


def test_horizon_mode_uses_latest_before_t_minus_h(session):
    target = utc(2026, 1, 15, 12, 0)
    _add_actual(session, target, 1000.0)
    # Horizon 6h => cutoff is 06:00. Latest at/before that wins.
    _add_forecast(session, target, utc(2026, 1, 15, 3, 0), 900.0)
    _add_forecast(session, target, utc(2026, 1, 15, 6, 0), 940.0)   # latest before T-6h
    _add_forecast(session, target, utc(2026, 1, 15, 9, 0), 980.0)   # after T-6h, ignored
    session.commit()

    df = selection.get_series(
        session, utc(2026, 1, 15), utc(2026, 1, 16), mode="horizon", horizon_h=6
    )
    assert df.iloc[0]["forecast_mw"] == 940.0


def test_error_is_forecast_minus_actual(session):
    target = utc(2026, 1, 15, 12, 0)
    _add_actual(session, target, 1000.0)
    _add_forecast(session, target, utc(2026, 1, 14, 9, 0), 1100.0)
    session.commit()

    df = selection.get_series(session, utc(2026, 1, 15), utc(2026, 1, 16), mode="dayahead")
    assert df.iloc[0]["error_mw"] == 100.0  # forecast high => under-bought
