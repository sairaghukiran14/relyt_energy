import type { ReactNode } from "react";

export function InfoTip({ text }: { text: string }) {
  return (
    <span className="info" tabIndex={0} aria-label={text}>
      i<span className="bubble">{text}</span>
    </span>
  );
}

export function MetricTile({
  label,
  value,
  unit,
  tip,
  delay = 0,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  tip?: string;
  delay?: number;
}) {
  return (
    <div className="tile rise" style={{ animationDelay: `${delay}s` }}>
      <div className="label">
        {label}
        {tip ? <InfoTip text={tip} /> : null}
      </div>
      <div className="value">
        {value}
        {unit ? <span className="unit"> {unit}</span> : null}
      </div>
    </div>
  );
}

export function Loading() {
  return <div className="state fade">Loading…</div>;
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
