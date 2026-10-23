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
import { ANIM, COLORS, ChartTooltip, axisProps } from "../chart";
import { Empty, ErrorState, Loading, MetricTile, fmt } from "../components";
import { MAX_DATE, MIN_DATE } from "../TopBar";

function hh(iso: string | number): string {
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
        <h1 className="page-title">Day-ahead view</h1>
        <p className="page-sub">What the buyer saw at the 11:00 D-1 cutoff, next to the actual.</p>
        {q.isLoading && <Loading />}
        {q.error && <ErrorState error={q.error} />}
        {q.data && <DayAheadBody data={q.data} />}
      </div>
    </>
  );
}

function DayAheadBody({ data }: { data: NonNullable<ReturnType<typeof useDayAhead>["data"]> }) {
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
        <MetricTile label="Forecast total" value={fmt(data.forecast_mwh)} unit="MWh" delay={0} />
        <MetricTile label="Actual total" value={fmt(data.actual_mwh)} unit="MWh" delay={0.06} />
        <MetricTile label="MAE this day" value={fmt(data.metrics.mae)} unit="MW" delay={0.12} tip="Mean absolute error across the day's hours." />
        <MetricTile label="Coverage" value={fmt(data.metrics.coverage * 100)} unit="%" delay={0.18} tip="Share of target hours with a forecast at the cutoff." />
      </div>
      <p className="hint" style={{ marginTop: 12 }}>
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
          <div className="card rise">
            <h2>Forecast at cutoff vs actual</h2>
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={points} margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
                <CartesianGrid stroke={COLORS.grid} vertical={false} />
                <XAxis dataKey="t" tickFormatter={hh} minTickGap={34} {...axisProps} />
                <YAxis width={64} unit=" MW" {...axisProps} />
                <Tooltip
                  content={<ChartTooltip labelFormat={hh} />}
                  cursor={{ stroke: COLORS.axis, strokeDasharray: "3 3" }}
                />
                <Line type="monotone" dataKey="actual" name="Actual" stroke={COLORS.actual} dot={false} strokeWidth={2.5} activeDot={{ r: 4 }} connectNulls {...ANIM} />
                <Line type="monotone" dataKey="forecast" name="Forecast" stroke={COLORS.forecast} strokeDasharray="6 4" dot={false} strokeWidth={2.5} activeDot={{ r: 4 }} connectNulls {...ANIM} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="card rise" style={{ animationDelay: "0.08s" }}>
            <h2>Error per hour</h2>
            <p className="hint">Positive (amber) = forecast too high, wind fell short. Negative (blue) = forecast too low.</p>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={points} margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
                <CartesianGrid stroke={COLORS.grid} vertical={false} />
                <XAxis dataKey="t" tickFormatter={hh} minTickGap={34} {...axisProps} />
                <YAxis width={64} unit=" MW" {...axisProps} />
                <Tooltip
                  content={<ChartTooltip labelFormat={hh} unit="MW" />}
                  cursor={{ fill: "rgba(31,111,214,0.06)" }}
                />
                <Bar dataKey="error" name="Error" radius={[3, 3, 0, 0]} {...ANIM}>
                  {points.map((p, i) => (
                    <Cell key={i} fill={(p.error ?? 0) >= 0 ? COLORS.forecast : COLORS.actual} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </>
  );
}
