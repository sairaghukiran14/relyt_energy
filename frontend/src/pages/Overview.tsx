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
import { Empty, ErrorState, Loading, MetricTile, fmt } from "../components";

function hhmm(iso: string): string {
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
      <div className="tiles">
        <MetricTile label="MAE" value={fmt(m.mae)} unit="MW" tip="Mean absolute error: typical miss size" />
        <MetricTile
          label="Bias (mean error)"
          value={fmt(m.bias)}
          unit="MW"
          tip="Mean of forecast − actual. Positive = forecast leans high"
        />
        <MetricTile
          label="P90 shortfall"
          value={fmt(m.p90_shortfall_mw)}
          unit="MW"
          tip="In 9 of 10 hours, wind was no more than this far below forecast"
        />
        <MetricTile
          label="Coverage"
          value={fmt(m.coverage * 100, 0)}
          unit="%"
          tip="Share of target hours with a usable forecast at the cutoff"
        />
      </div>

      <div className="card">
        <h2>Actual vs forecast (MW)</h2>
        {points.length === 0 ? (
          <Empty message="No data for this range." />
        ) : (
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={points} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
              <CartesianGrid stroke="var(--border)" />
              <XAxis
                dataKey="t"
                tickFormatter={hhmm}
                stroke="var(--muted)"
                minTickGap={60}
              />
              <YAxis stroke="var(--muted)" width={64} />
              <Tooltip
                labelFormatter={(v) => hhmm(String(v))}
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
            </LineChart>
          </ResponsiveContainer>
        )}
        <p className="hint">Actual = solid blue, forecast = dashed orange. Times in UTC (= UK in January).</p>
      </div>
    </div>
  );
}
