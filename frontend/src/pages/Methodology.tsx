export function Methodology() {
  return (
    <div className="page prose">
      <h1 className="page-title">Methodology</h1>
      <p className="page-sub">How the forecast is selected and how each metric is defined.</p>
      <div className="card rise">
        <h2>Data sources</h2>
        <p>
          Two public Elexon BMRS datasets, stored in UTC (January has no daylight saving, so UK
          time equals UTC):
        </p>
        <ul>
          <li>
            <strong>Actuals — FUELHH</strong> (<code>fuelType = WIND</code>): metered national wind
            output per 30-minute settlement period, in MW.
          </li>
          <li>
            <strong>Forecasts — WINDFOR</strong>: forecast wind output (MW) for a target time, made
            at a publish time. One target time has many forecasts at different publish times.
          </li>
        </ul>
        <p className="hint">
          Data covers January 2026 delivery days (2 Jan – 1 Feb 2026). It is downloaded once and
          loaded into PostgreSQL; the live app never calls Elexon.
        </p>
      </div>

      <div className="card">
        <h2>Forecast selection (no look-ahead)</h2>
        <p>
          For every target time, the app uses only the latest forecast published{" "}
          <strong>at or before</strong> the cutoff. No forecast published after the cutoff is ever
          used, so the numbers match what a buyer really had.
        </p>
        <ul>
          <li>
            <strong>Day-ahead mode</strong> (default): cutoff = 11:00 UK time on the day before
            delivery (D-1), the GB day-ahead auction gate closure.
          </li>
          <li>
            <strong>Fixed-horizon mode</strong>: for each target time T, use the newest forecast
            published at or before T − H, where H is 0–48 hours.
          </li>
        </ul>
        <p className="hint">
          WINDFOR is hourly; actuals are half-hourly. In v1 we compare only at matching hours (no
          interpolation), so coverage is the share of hourly target times with a usable forecast.
        </p>
      </div>

      <div className="card">
        <h2>Metric definitions</h2>
        <p>
          All metrics use <code>error = forecast − actual</code> (MW). Positive means the forecast
          was too high (wind fell short, so the team under-bought).
        </p>
        <ul>
          <li>
            <strong>MAE</strong> — mean absolute error: typical miss size.
          </li>
          <li>
            <strong>RMSE</strong> — like MAE but punishes big misses more.
          </li>
          <li>
            <strong>Bias (mean error)</strong> — does the forecast lean high (+) or low (−)?
          </li>
          <li>
            <strong>Normalised MAE</strong> — MAE as a share of mean actual output.
          </li>
          <li>
            <strong>P10/P50/P90/P99</strong> — percentiles of error: the spread of misses.
          </li>
          <li>
            <strong>P90 shortfall</strong> — the headline safety margin: in 9 of 10 hours, wind was
            no more than this far below forecast.
          </li>
          <li>
            <strong>Coverage</strong> — share of target hours with a usable forecast at the cutoff.
          </li>
        </ul>
        <p className="hint">
          MAPE is deliberately not used: it explodes when actual wind is near zero.
        </p>
      </div>

      <div className="card">
        <h2>Reading the bias</h2>
        <p>
          In January 2026 the day-ahead forecast ran about 1.7 GW above actual output on average.
          This is not a one-off weather miss: the lean is positive in every week of the month
          (roughly +1.2 to +2.4 GW) and at every horizon, including about +1.5 GW for forecasts made
          under 8 hours ahead.
        </p>
        <p>
          A gap that does not shrink as the forecast gets closer to delivery points to a systematic
          difference between the two datasets (for example, what generation each series counts)
          rather than to forecast skill alone. We have not corrected for it and cannot confirm the
          cause from these two datasets alone.
        </p>
        <p className="hint">
          Practical reading: treat the median error (P50) as a standing discount on the forecast,
          and the P90 shortfall as the extra margin on top. Bias is shown separately so it is
          never hidden inside MAE.
        </p>
      </div>
    </div>
  );
}
