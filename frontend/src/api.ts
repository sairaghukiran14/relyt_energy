import { useQuery } from "@tanstack/react-query";

export type Mode = "dayahead" | "horizon";

export interface SeriesPoint {
  start_time: string;
  actual_mw: number | null;
  forecast_mw: number | null;
  publish_time: string | null;
  error_mw: number | null;
}

export interface Metrics {
  n: number;
  coverage: number;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  nmae: number | null;
  p10: number | null;
  p50: number | null;
  p90: number | null;
  p99: number | null;
  max_abs_error: number | null;
  p90_shortfall_mw: number | null;
}

export interface SeriesResponse {
  mode: Mode;
  horizon_h: number | null;
  points: SeriesPoint[];
}

export interface DayAheadResponse {
  date: string;
  cutoff: string;
  points: SeriesPoint[];
  actual_mwh: number | null;
  forecast_mwh: number | null;
  metrics: Metrics;
}

export interface Range {
  start: string;
  end: string;
  mode: Mode;
  horizonH: number;
}

function qs(range: Range): string {
  const p = new URLSearchParams({
    start: range.start,
    end: range.end,
    mode: range.mode,
  });
  if (range.mode === "horizon") p.set("horizon_h", String(range.horizonH));
  return p.toString();
}

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export function useSeries(range: Range) {
  return useQuery({
    queryKey: ["series", range],
    queryFn: () => getJSON<SeriesResponse>(`/api/series?${qs(range)}`),
  });
}

export function useMetrics(range: Range) {
  return useQuery({
    queryKey: ["metrics", range],
    queryFn: () => getJSON<Metrics>(`/api/metrics?${qs(range)}`),
  });
}

export function useDayAhead(date: string) {
  return useQuery({
    queryKey: ["dayahead", date],
    queryFn: () => getJSON<DayAheadResponse>(`/api/dayahead/${date}`),
  });
}
