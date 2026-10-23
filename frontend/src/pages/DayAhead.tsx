import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useDayAhead } from "../api";
import { Empty, ErrorState, Loading, MetricTile, fmt } from "../components";
import { MAX_DATE, MIN_DATE } from "../TopBar";

function hh(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}

export function DayAhead() {
  const [date, setDate] = useState("2026-01-15");
  const q = useDayAhead(date);

  return (
    <>
      <div className="topbar">
        <div className="field">
          <label htmlFor="day">Delivery date</label>
          <input
            id="day"
            type="date"
            min={MIN_DATE}
            max={MAX_DATE}
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
      </div>

      <div className="page">
        {q.isLoading && <Loading />}
        {q.error && <ErrorState error={q.error} />}
        {q.data && <DayAheadBody data={q.data} hh={hh} />}
      </div>
    </>
  );
}

function DayAheadBody({
  data,
  hh,
}: {
  data: NonNullable<ReturnType<typeof useDayAhead>["data"]>;
  hh: (iso: string) => string;
}) {
  const points = data.points.map((p) => ({
    t: p.start_time,
    actual: p.actual_mw,
    forecast: p.forecast_mw,
    error: p.error_mw,
  }));
  const publishTimes = Array.from(
    new Set(data.points.map((p) => p.publish_time).filter(Boolean)),
  ) as string[];

  return (
    <>
      <div className="tiles">
        <MetricTile label="Forecast total" value={fmt(data.forecast_mwh)} unit="MWh" />
        <MetricTile label="Actual total" value={fmt(data.actual_mwh)} unit="MWh" />
        <MetricTile
          label="MAE this day"
          value={fmt(data.metrics.mae)}
          unit="MW"
          tip="Mean absolute error across the day's hours"
        />
        <MetricTile
          label="Coverage"
          value={fmt(data.metrics.coverage * 100)}
          unit="%"
          tip="Share of target hours with a forecast at the 11:00 D-1 cutoff"
        />
      </div>
      <p className="hint">
        Cutoff (gate closure): {new Date(data.cutoff).toISOString().replace(".000Z", "Z")}.{" "}
        {publishTimes.length === 1
          ? `Forecast published at ${publishTimes[0]!.replace(".000Z", "Z").replace("T", " ")}.`
          : `Forecasts published at ${publishTimes.length} times at/before cutoff.`}
      </p>

      {points.length === 0 ? (
        <div className="card">
          <Empty message="No forecast/actual data for this day." />
        </div>
      ) : (
        <>
          <div className="card">
            <h2>Forecast at cutoff vs actual (MW)</h2>
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={points} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="var(--border)" />
                <XAxis dataKey="t" tickFormatter={hh} stroke="var(--muted)" minTickGap={30} />
                <YAxis stroke="var(--muted)" width={64} />
                <Tooltip
                  labelFormatter={(v) => hh(String(v))}
                  formatter={(val: number, name) => [`${fmt(val)} MW`, name]}
                  contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)" }}
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual"
                  stroke="var(--actual)"
                  dot={false}
                  strokeWidth={2}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="forecast"
                  name="Forecast"
                  stroke="var(--forecast)"
                  strokeDasharray="6 4"
                  dot={false}
                  strokeWidth={2}
                  connectNulls
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <h2>Error per hour (forecast − actual, MW)</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={points} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
                <CartesianGrid stroke="var(--border)" />
                <XAxis dataKey="t" tickFormatter={hh} stroke="var(--muted)" minTickGap={30} />
                <YAxis stroke="var(--muted)" width={64} />
                <Tooltip
                  labelFormatter={(v) => hh(String(v))}
                  formatter={(val: number) => [`${fmt(val)} MW`, "Error"]}
                  contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)" }}
                />
                <Bar dataKey="error" name="Error">
                  {points.map((p, i) => (
                    <Cell
                      key={i}
                      fill={(p.error ?? 0) >= 0 ? "var(--forecast)" : "var(--actual)"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <p className="hint">
              Positive (orange) = forecast too high, wind fell short (under-bought). Negative (blue)
              = forecast too low.
            </p>
          </div>
        </>
      )}
    </>
  );
}
