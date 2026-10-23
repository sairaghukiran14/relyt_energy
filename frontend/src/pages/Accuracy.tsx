import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { GroupedMetric, Range } from "../api";
import { useByHorizon, useByHour, useByWindLevel, useHistogram, useMetrics } from "../api";
import { Empty, ErrorState, Loading, fmt } from "../components";
import { downloadCsv } from "../csv";

const tipStyle = { background: "var(--panel)", border: "1px solid var(--border)" };

function GroupedBar({
  data,
  xLabel,
  xUnit,
}: {
  data: GroupedMetric[];
  xLabel: string;
  xUnit?: string;
}) {
  if (data.length === 0) return <Empty message="No data for this range." />;
  const rows = data.map((d) => ({ ...d, label: `${d.key}${xUnit ?? ""}` }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
        <CartesianGrid stroke="var(--border)" />
        <XAxis
          dataKey="label"
          stroke="var(--muted)"
          label={{ value: xLabel, position: "insideBottom", offset: -8, fill: "var(--muted)" }}
        />
        <YAxis stroke="var(--muted)" width={56} />
        <Tooltip
          formatter={(v: number, name) => [`${fmt(v)} MW`, name]}
          contentStyle={tipStyle}
        />
        <Bar dataKey="mae" name="MAE" fill="var(--error)" />
        <Bar dataKey="bias" name="Bias" fill="var(--forecast)" />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function Accuracy({ range }: { range: Range }) {
  const metrics = useMetrics(range);
  const byHorizon = useByHorizon(range);
  const byHour = useByHour(range);
  const byWind = useByWindLevel(range);
  const hist = useHistogram(range);

  if (metrics.isLoading) return <Loading />;
  if (metrics.error) return <ErrorState error={metrics.error} />;
  const m = metrics.data!;

  const percentileRows = [
    { percentile: "P10", error_mw: m.p10 },
    { percentile: "P50 (median)", error_mw: m.p50 },
    { percentile: "P90", error_mw: m.p90 },
    { percentile: "P99", error_mw: m.p99 },
    { percentile: "Max abs error", error_mw: m.max_abs_error },
  ];

  const histRows =
    hist.data?.counts.map((c, i) => ({
      from_mw: Math.round(hist.data!.bins[i]),
      to_mw: Math.round(hist.data!.bins[i + 1]),
      count: c,
    })) ?? [];

  return (
    <div className="page">
      <div className="card">
        <h2>Error by forecast horizon</h2>
        <p className="hint">How accuracy changes with lead time. MAE (teal) and bias (orange).</p>
        {byHorizon.isLoading ? (
          <Loading />
        ) : byHorizon.error ? (
          <ErrorState error={byHorizon.error} />
        ) : (
          <GroupedBar data={byHorizon.data!} xLabel="Horizon (hours)" xUnit="h" />
        )}
      </div>

      <div className="card">
        <h2>Error by hour of day</h2>
        <p className="hint">Times in UTC (= UK in January).</p>
        {byHour.isLoading ? (
          <Loading />
        ) : byHour.error ? (
          <ErrorState error={byHour.error} />
        ) : (
          <GroupedBar data={byHour.data!} xLabel="Hour of day" />
        )}
      </div>

      <div className="card">
        <h2>Error histogram</h2>
        <p className="hint">Distribution of forecast − actual (MW). Right of zero = forecast too high.</p>
        {hist.isLoading ? (
          <Loading />
        ) : hist.error ? (
          <ErrorState error={hist.error} />
        ) : histRows.length === 0 ? (
          <Empty message="No data for this range." />
        ) : (
          <>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={histRows.map((r) => ({ ...r, mid: Math.round((r.from_mw + r.to_mw) / 2) }))}
                margin={{ top: 8, right: 16, bottom: 20, left: 8 }}
              >
                <CartesianGrid stroke="var(--border)" />
                <XAxis
                  dataKey="mid"
                  stroke="var(--muted)"
                  label={{ value: "Error (MW)", position: "insideBottom", offset: -8, fill: "var(--muted)" }}
                />
                <YAxis stroke="var(--muted)" width={56} />
                <Tooltip contentStyle={tipStyle} formatter={(v: number) => [v, "Count"]} />
                <Bar dataKey="count" name="Count" fill="var(--actual)" />
              </BarChart>
            </ResponsiveContainer>
            <button onClick={() => downloadCsv("error-histogram.csv", histRows)}>
              Download CSV
            </button>
          </>
        )}
      </div>

      <div className="card">
        <h2>Error percentiles</h2>
        <table className="tbl">
          <thead>
            <tr>
              <th>Percentile</th>
              <th>Error (MW)</th>
            </tr>
          </thead>
          <tbody>
            {percentileRows.map((r) => (
              <tr key={r.percentile}>
                <td>{r.percentile}</td>
                <td>{fmt(r.error_mw)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <button onClick={() => downloadCsv("error-percentiles.csv", percentileRows)}>
          Download CSV
        </button>
      </div>

      <div className="card">
        <h2>Error by wind level</h2>
        <p className="hint">Actual output split into thirds of the month's peak.</p>
        {byWind.isLoading ? (
          <Loading />
        ) : byWind.error ? (
          <ErrorState error={byWind.error} />
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>Band</th>
                <th>Range (MW)</th>
                <th>n</th>
                <th>MAE</th>
                <th>Bias</th>
              </tr>
            </thead>
            <tbody>
              {byWind.data!.map((b) => (
                <tr key={b.band}>
                  <td style={{ textTransform: "capitalize" }}>{b.band}</td>
                  <td>
                    {fmt(b.lo_mw)}–{fmt(b.hi_mw)}
                  </td>
                  <td>{b.n}</td>
                  <td>{fmt(b.mae)}</td>
                  <td>{fmt(b.bias)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
