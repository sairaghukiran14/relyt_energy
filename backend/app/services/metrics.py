"""Forecast-error metrics. All operate on a series frame from selection.get_series.

error = forecast - actual (MW). Positive means the forecast was too high (wind
fell short, so the team under-bought). Rows with no forecast (gaps) are excluded
from metrics but counted for coverage.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _paired(series: pd.DataFrame) -> pd.DataFrame:
    """Rows that have both an actual and a forecast."""
    if series.empty:
        return series
    return series.dropna(subset=["actual_mw", "forecast_mw"])


def compute_metrics(series: pd.DataFrame) -> dict:
    """Headline metrics over the whole series."""
    total = len(series)
    paired = _paired(series)
    n = len(paired)
    if n == 0:
        return {
            "n": 0,
            "coverage": 0.0,
            "mae": None,
            "rmse": None,
            "bias": None,
            "nmae": None,
            "p10": None,
            "p50": None,
            "p90": None,
            "p99": None,
            "max_abs_error": None,
            "p90_shortfall_mw": None,
        }

    err = paired["error_mw"].to_numpy()
    actual = paired["actual_mw"].to_numpy()
    mean_actual = float(np.mean(actual))

    # Shortfall = how far actual fell below forecast = max(error, 0).
    shortfall = np.clip(err, 0, None)

    return {
        "n": n,
        "coverage": n / total if total else 0.0,
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "bias": float(np.mean(err)),
        "nmae": float(np.mean(np.abs(err)) / mean_actual) if mean_actual else None,
        "p10": float(np.percentile(err, 10)),
        "p50": float(np.percentile(err, 50)),
        "p90": float(np.percentile(err, 90)),
        "p99": float(np.percentile(err, 99)),
        "max_abs_error": float(np.max(np.abs(err))),
        # Headline safety margin: 90th percentile of shortfall.
        "p90_shortfall_mw": float(np.percentile(shortfall, 90)),
    }


def _grouped(series: pd.DataFrame, key: pd.Series) -> list[dict]:
    paired = _paired(series)
    if paired.empty:
        return []
    out = []
    for group_val, g in paired.groupby(key.loc[paired.index]):
        err = g["error_mw"].to_numpy()
        out.append(
            {
                "key": int(group_val),
                "n": int(len(g)),
                "mae": float(np.mean(np.abs(err))),
                "rmse": float(np.sqrt(np.mean(err**2))),
                "bias": float(np.mean(err)),
            }
        )
    return out


def metrics_by_horizon(series: pd.DataFrame) -> list[dict]:
    """MAE, RMSE, bias per whole-hour forecast horizon."""
    paired = _paired(series)
    if paired.empty:
        return []
    buckets = paired["horizon_h"].round().astype(int)
    return _grouped(series, buckets.rename("key"))


def metrics_by_hour(series: pd.DataFrame) -> list[dict]:
    """Same metrics per hour of day (UTC = UK in January)."""
    paired = _paired(series)
    if paired.empty:
        return []
    hours = paired["start_time"].dt.hour
    return _grouped(series, hours.rename("key"))


def error_histogram(series: pd.DataFrame, bins: int = 20) -> dict:
    paired = _paired(series)
    if paired.empty:
        return {"bins": [], "counts": []}
    err = paired["error_mw"].to_numpy()
    counts, edges = np.histogram(err, bins=bins)
    return {
        "bins": [float(e) for e in edges],
        "counts": [int(c) for c in counts],
    }


# Wind-level bands, as fractions of the maximum actual output in the range.
# Low  = bottom third of capacity seen, Medium = middle, High = top.
_WIND_BANDS = (("low", 0.0, 1 / 3), ("medium", 1 / 3, 2 / 3), ("high", 2 / 3, 1.0))


def metrics_by_wind_level(series: pd.DataFrame) -> list[dict]:
    """MAE, RMSE, bias split by actual wind level (low / medium / high).

    Bands are thirds of the maximum actual output observed in the range, so a
    buyer can see whether the forecast is less trustworthy in high or low wind.
    """
    paired = _paired(series)
    if paired.empty:
        return []
    max_actual = float(paired["actual_mw"].max())
    if max_actual <= 0:
        return []

    out = []
    for name, lo, hi in _WIND_BANDS:
        lo_mw, hi_mw = lo * max_actual, hi * max_actual
        # Top band is inclusive of the max; lower bands are half-open.
        if name == "high":
            band = paired[paired["actual_mw"] >= lo_mw]
        else:
            band = paired[(paired["actual_mw"] >= lo_mw) & (paired["actual_mw"] < hi_mw)]
        if band.empty:
            out.append({"band": name, "lo_mw": lo_mw, "hi_mw": hi_mw, "n": 0,
                        "mae": None, "rmse": None, "bias": None})
            continue
        err = band["error_mw"].to_numpy()
        out.append(
            {
                "band": name,
                "lo_mw": lo_mw,
                "hi_mw": hi_mw,
                "n": int(len(band)),
                "mae": float(np.mean(np.abs(err))),
                "rmse": float(np.sqrt(np.mean(err**2))),
                "bias": float(np.mean(err)),
            }
        )
    return out
