export const pct = (x, digits = 1) => (x == null || Number.isNaN(x) ? "—" : `${(x * 100).toFixed(digits)} %`);
export const num = (x, digits = 3) => (x == null || Number.isNaN(x) ? "—" : Number(x).toFixed(digits));
export const cyclesLabel = (x) => (x == null ? "—" : `${Math.round(x)} cycles`);

export const STATUS_LABEL = {
  healthy: "Healthy",
  maintenance_due: "Maintenance due",
  end_of_life: "End of life",
};

/** Merge measured cycles with per-cycle predictions for the chart. */
export function mergeSeries(predictions) {
  return (predictions || []).map((p) => ({
    cycle: p.cycle,
    measured: p.soh,
    predicted: p.soh_p50,
    band: [p.soh_p10, p.soh_p90],
  }));
}

/** Append the physics forecast after the measured history. */
export function withForecast(series, trajectory) {
  const tail = (trajectory || []).map((t) => ({ cycle: t.cycle, forecast: t.soh_forecast }));
  return [...series, ...tail];
}
