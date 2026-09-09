import { describe, expect, it } from "vitest";
import { cyclesLabel, mergeSeries, num, pct, withForecast } from "../format";

describe("formatters", () => {
  it("formats percentages and numbers", () => {
    expect(pct(0.8532)).toBe("85.3 %");
    expect(pct(0.8532, 0)).toBe("85 %");
    expect(pct(null)).toBe("—");
    expect(num(1.23456)).toBe("1.235");
    expect(num(undefined)).toBe("—");
    expect(cyclesLabel(41.6)).toBe("42 cycles");
    expect(cyclesLabel(null)).toBe("—");
  });

  it("merges predictions into chart rows", () => {
    const rows = mergeSeries([{ cycle: 1, soh: 0.9, soh_p10: 0.88, soh_p50: 0.9, soh_p90: 0.92 }]);
    expect(rows).toEqual([{ cycle: 1, measured: 0.9, predicted: 0.9, band: [0.88, 0.92] }]);
    expect(mergeSeries(undefined)).toEqual([]);
  });

  it("appends forecast rows", () => {
    const out = withForecast([{ cycle: 1, measured: 0.9 }], [{ cycle: 2, soh_forecast: 0.89 }]);
    expect(out).toHaveLength(2);
    expect(out[1]).toEqual({ cycle: 2, forecast: 0.89 });
    expect(withForecast([], null)).toEqual([]);
  });
});
