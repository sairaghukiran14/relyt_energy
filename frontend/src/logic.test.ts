import { describe, expect, it } from "vitest";
import { qs } from "./api";
import { toCsv } from "./csv";

describe("qs", () => {
  it("omits horizon_h in day-ahead mode", () => {
    const s = qs({ start: "2026-01-02", end: "2026-02-01", mode: "dayahead", horizonH: 24 });
    expect(s).toContain("mode=dayahead");
    expect(s).not.toContain("horizon_h");
  });

  it("includes horizon_h in horizon mode", () => {
    const s = qs({ start: "2026-01-02", end: "2026-02-01", mode: "horizon", horizonH: 36 });
    expect(s).toContain("mode=horizon");
    expect(s).toContain("horizon_h=36");
  });
});

describe("toCsv", () => {
  it("writes a header row then data rows", () => {
    const csv = toCsv([
      { a: 1, b: 2 },
      { a: 3, b: 4 },
    ]);
    expect(csv).toBe("a,b\n1,2\n3,4");
  });

  it("quotes values containing commas or quotes", () => {
    const csv = toCsv([{ name: "a,b", note: 'he said "hi"' }]);
    expect(csv).toBe('name,note\n"a,b","he said ""hi"""');
  });

  it("returns empty string for no rows", () => {
    expect(toCsv([])).toBe("");
  });
});
