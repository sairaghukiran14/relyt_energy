"""Metrics checked against hand-computed values."""

import numpy as np
import pandas as pd

from app.services import metrics as m


def _series(actuals, forecasts, start="2026-01-15 00:00"):
    idx = pd.date_range(start, periods=len(actuals), freq="30min", tz="UTC")
    df = pd.DataFrame(
        {
            "start_time": idx,
            "actual_mw": actuals,
            "forecast_mw": forecasts,
            "publish_time": idx,
            "horizon_h": [24.0] * len(actuals),
        }
    )
    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]
    return df


def test_mae_rmse_bias_hand_computed():
    # errors: +100, -200, +300  (forecast - actual)
    df = _series([1000, 1200, 900], [1100, 1000, 1200])
    r = m.compute_metrics(df)
    assert r["bias"] == (100 - 200 + 300) / 3
    assert r["mae"] == (100 + 200 + 300) / 3
    assert r["rmse"] == np.sqrt((100**2 + 200**2 + 300**2) / 3)


def test_nmae_is_mae_over_mean_actual():
    df = _series([1000, 2000], [1100, 1800])  # errors +100, -200
    r = m.compute_metrics(df)
    mae = (100 + 200) / 2
    assert r["nmae"] == mae / 1500


def test_p90_shortfall_only_counts_actual_below_forecast():
    # errors: +100 (short), -50 (over), +300 (short). Shortfall clips negatives to 0.
    df = _series([900, 1050, 700], [1000, 1000, 1000])
    r = m.compute_metrics(df)
    shortfall = [100, 0, 300]
    assert r["p90_shortfall_mw"] == np.percentile(shortfall, 90)


def test_coverage_excludes_gaps():
    df = _series([1000, 1200, 900], [1100, np.nan, 1200])  # one gap
    r = m.compute_metrics(df)
    assert r["n"] == 2
    assert r["coverage"] == 2 / 3


def test_empty_series_returns_nones():
    df = _series([], [])
    r = m.compute_metrics(df)
    assert r["n"] == 0
    assert r["mae"] is None


def test_by_horizon_groups():
    df = _series([1000, 1000], [1100, 1300])
    df["horizon_h"] = [10.0, 10.4]  # both round to 10
    out = m.metrics_by_horizon(df)
    assert len(out) == 1
    assert out[0]["key"] == 10
    assert out[0]["n"] == 2


def test_by_hour_uses_hour_of_day():
    df = _series([1000, 1000, 1000], [1100, 1200, 1300])
    # 30-min cadence => 00:00, 00:30, 01:00 => hours 0, 0, 1.
    out = {g["key"]: g for g in m.metrics_by_hour(df)}
    assert out[0]["n"] == 2
    assert out[1]["n"] == 1


def test_wind_level_bands_split_by_actual():
    # max actual = 3000 => bands at 0-1000 (low), 1000-2000 (medium), 2000-3000 (high).
    df = _series([500, 1500, 3000], [600, 1400, 2800])
    out = {g["band"]: g for g in m.metrics_by_wind_level(df)}
    assert out["low"]["n"] == 1
    assert out["medium"]["n"] == 1
    assert out["high"]["n"] == 1
    # high band: actual 3000, forecast 2800 => error -200.
    assert out["high"]["bias"] == -200


def test_wind_level_empty_band_reports_zero():
    # All actuals high => low/medium bands are empty but still listed.
    df = _series([2800, 3000], [2900, 2900])
    out = {g["band"]: g for g in m.metrics_by_wind_level(df)}
    assert out["low"]["n"] == 0
    assert out["low"]["mae"] is None
    assert out["high"]["n"] == 2


def test_histogram_counts_sum_to_n():
    df = _series([1000, 1200, 900, 1100], [1100, 1000, 1200, 1050])
    h = m.error_histogram(df, bins=5)
    assert sum(h["counts"]) == 4
    assert len(h["bins"]) == 6  # edges = bins + 1
