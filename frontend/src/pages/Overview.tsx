import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Range } from "../api";
import { useMetrics, useSeries } from "../api";
import { ANIM, COLORS, ChartTooltip, axisProps } from "../chart";
import { Empty, ErrorState, Loading, MetricTile, fmt } from "../components";
import { downloadCsv } from "../csv";

function hhmm(iso: string | number): string {
  return new Date(iso).toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}

export function Overview({ range }: { range: Range }) {
  const metrics = useMetrics(range);
  const series = useSeries(range);

  if (metrics.isLoading || series.isLoading) return <Loading />;
  if (metrics.error) return <ErrorState error={metrics.error} />;
  if (series.error) return <ErrorState error={series.error} />;

  const m = metrics.data!;
  const points = (series.data?.points ?? []).map((p) => ({
    t: p.start_time,
    actual: p.actual_mw,
    forecast: p.forecast_mw,
  }));

  return (
    <div className="page">
      <h1 className="page-title">Overview</h1>
      <p className="page-sub">
        Forecast accuracy across the selected range{range.mode === "horizon" ? ` · ${range.horizonH}h horizon` : " · day-ahead"}.
      </p>

      <div className="tiles">
        <MetricTile label="MAE" value={fmt(m.mae)} unit="MW" delay={0} tip="Mean absolute error: the typical miss size." />
        <MetricTile label="Bias (mean error)" value={fmt(m.bias)} unit="MW" delay={0.06} tip="Mean of forecast − actual. Positive means the forecast leans high." />
        <MetricTile label="P90 shortfall" value={fmt(m.p90_shortfall_mw)} unit="MW" delay={0.12} tip="In 9 of 10 hours, wind was no more than this far below forecast." />
        <MetricTile label="Coverage" value={fmt(m.coverage * 100)} unit="%" delay={0.18} tip="Share of target hours with a usable forecast at the cutoff." />
      </div>

      <div className="card rise" style={{ animationDelay: "0.2s" }}>
        <h2>Actual vs forecast</h2>
        <p className="hint">Solid = actual, dashed = forecast. Times in UTC (= UK in January).</p>
        {points.length === 0 ? (
          <Empty message="No data for this range." />
        ) : (
          <ResponsiveContainer width="100%" height={380}>
            <LineChart data={points} margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
              <CartesianGrid stroke={COLORS.grid} vertical={false} />
              <XAxis dataKey="t" tickFormatter={hhmm} minTickGap={70} {...axisProps} />
              <YAxis width={64} unit=" MW" {...axisProps} />
              <Tooltip
                content={<ChartTooltip labelFormat={hhmm} />}
                cursor={{ stroke: COLORS.axis, strokeDasharray: "3 3" }}
              />
              <Line
                type="monotone"
                dataKey="actual"
                name="Actual"
                stroke={COLORS.actual}
                dot={false}
                strokeWidth={2.5}
                activeDot={{ r: 4 }}
                connectNulls
                {...ANIM}
              />
              <Line
                type="monotone"
                dataKey="forecast"
                name="Forecast"
                stroke={COLORS.forecast}
                strokeDasharray="6 4"
                dot={false}
                strokeWidth={2.5}
                activeDot={{ r: 4 }}
                connectNulls
                {...ANIM}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
        {points.length > 0 && (
          <button
            className="btn-sm"
            onClick={() =>
              downloadCsv(
                "series.csv",
                (series.data?.points ?? []).map((p) => ({
                  start_time: p.start_time,
                  actual_mw: p.actual_mw,
                  forecast_mw: p.forecast_mw,
                  publish_time: p.publish_time,
                  error_mw: p.error_mw,
                })),
              )
            }
          >
            ↓ Download CSV
          </button>
        )}
      </div>
    </div>
  );
}
