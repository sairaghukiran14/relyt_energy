import type { Mode, Range } from "./api";

// Shared controls. Day-ahead is the default; the horizon slider is only relevant
// in horizon mode. Date bounds match the loaded data window (Jan 2026 deliveries).
export const MIN_DATE = "2026-01-02";
export const MAX_DATE = "2026-02-01";

export function TopBar({
  range,
  onChange,
  showMode = true,
}: {
  range: Range;
  onChange: (r: Range) => void;
  showMode?: boolean;
}) {
  return (
    <div className="topbar">
      <div className="field">
        <label htmlFor="start">Start</label>
        <input
          id="start"
          type="date"
          min={MIN_DATE}
          max={MAX_DATE}
          value={range.start}
          onChange={(e) => onChange({ ...range, start: e.target.value })}
        />
      </div>
      <div className="field">
        <label htmlFor="end">End</label>
        <input
          id="end"
          type="date"
          min={MIN_DATE}
          max={MAX_DATE}
          value={range.end}
          onChange={(e) => onChange({ ...range, end: e.target.value })}
        />
      </div>
      {showMode && (
        <div className="field">
          <label htmlFor="mode">Mode</label>
          <select
            id="mode"
            value={range.mode}
            onChange={(e) => onChange({ ...range, mode: e.target.value as Mode })}
          >
            <option value="dayahead">Day-ahead (11:00 D-1)</option>
            <option value="horizon">Fixed horizon</option>
          </select>
        </div>
      )}
      {showMode && range.mode === "horizon" && (
        <div className="field">
          <label htmlFor="horizon">Horizon: {range.horizonH}h</label>
          <input
            id="horizon"
            type="range"
            min={0}
            max={48}
            step={1}
            value={range.horizonH}
            onChange={(e) => onChange({ ...range, horizonH: Number(e.target.value) })}
          />
        </div>
      )}
    </div>
  );
}
