import type { ReactNode } from "react";

export function MetricTile({
  label,
  value,
  unit,
  tip,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  tip?: string;
}) {
  return (
    <div className="tile">
      <div className="label">
        {tip ? (
          <span className="tip" title={tip}>
            {label}
          </span>
        ) : (
          label
        )}
      </div>
      <div className="value">
        {value}
        {unit ? <span className="unit"> {unit}</span> : null}
      </div>
    </div>
  );
}

export function Loading() {
  return <div className="state">Loading…</div>;
}

export function Empty({ message }: { message: string }) {
  return <div className="state">{message}</div>;
}

export function ErrorState({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : "Something went wrong";
  return <div className="state">⚠ {msg}</div>;
}

export function fmt(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
