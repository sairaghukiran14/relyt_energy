import type { TooltipProps } from "recharts";
import { fmt } from "./components";

// Shared chart constants so every chart animates and reads the same way.
export const COLORS = {
  actual: "#1f6fd6",
  forecast: "#e08a00",
  accent: "#0e9f6e",
  danger: "#d1495b",
  grid: "#eef1f5",
  axis: "#98a2b3",
};

export const ANIM = { isAnimationActive: true, animationDuration: 800, animationEasing: "ease-out" as const };

export const axisProps = {
  stroke: COLORS.axis,
  tick: { fill: COLORS.axis, fontSize: 12 },
  tickLine: false,
  axisLine: { stroke: COLORS.grid },
};

// A styled tooltip card shared across line and bar charts. `labelFormat` turns the
// raw axis key into a human label; `unit` is appended to each value.
export function ChartTooltip({
  active,
  payload,
  label,
  labelFormat,
  unit = "MW",
}: TooltipProps<number, string> & {
  labelFormat?: (v: string | number) => string;
  unit?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="chart-tip">
      {label !== undefined && (
        <div className="tip-label">{labelFormat ? labelFormat(label) : String(label)}</div>
      )}
      {payload.map((p, i) => (
        <div className="tip-row" key={i}>
          <span className="swatch" style={{ background: p.color }} />
          <span className="name">{p.name}</span>
          <span className="val">
            {fmt(typeof p.value === "number" ? p.value : null)} {unit}
          </span>
        </div>
      ))}
    </div>
  );
}
