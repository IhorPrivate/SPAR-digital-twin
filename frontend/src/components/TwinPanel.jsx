import { useState } from "react";
import { STATUS_LABEL, cyclesLabel, num, pct } from "../format";

const FIELDS = [
  ["capacity_ah", "Capacity (Ah)", 1.7],
  ["mean_voltage_v", "Mean voltage (V)", 3.4],
  ["min_voltage_v", "Min voltage (V)", 2.7],
  ["mean_current_a", "Mean current (A)", 2.0],
  ["mean_temp_c", "Mean temperature (°C)", 31],
  ["max_temp_c", "Max temperature (°C)", 34],
  ["discharge_time_s", "Discharge time (s)", 3000],
  ["ambient_temp_c", "Ambient (°C)", 24],
];

export function IngestForm({ onSubmit, onReset, busy }) {
  const [values, setValues] = useState(Object.fromEntries(FIELDS.map(([k, , d]) => [k, d])));
  const update = (k) => (e) => setValues((v) => ({ ...v, [k]: e.target.value }));
  const submit = () => {
    const body = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, Number(v)]));
    onSubmit(body);
  };
  return (
    <div className="ingest">
      <h3>Add a discharge cycle</h3>
      {FIELDS.map(([k, label]) => (
        <label key={k}>
          {label}
          <input type="number" step="any" value={values[k]} onChange={update(k)} aria-label={label} />
        </label>
      ))}
      <div className="actions">
        <button onClick={submit} disabled={busy}>Add cycle</button>
        <button className="secondary" onClick={onReset} disabled={busy}>Reset twin</button>
      </div>
    </div>
  );
}

export default function TwinPanel({ twin, trained, busy, onIngest, onReset }) {
  if (!trained) {
    return (
      <aside className="side">
        <h3>Twin</h3>
        <p className="notice">Train the models to bring the twin online.</p>
      </aside>
    );
  }
  const s = twin?.state;
  return (
    <aside className="side" aria-label="Twin state">
      <h3>Twin of {s?.cell_id ?? "…"}</h3>
      {s && (
        <>
          <span className={`status status-${s.health_status}`}>{STATUS_LABEL[s.health_status]}</span>
          <dl className="kv">
            <dt>Cycles observed</dt><dd>{s.cycles_observed}</dd>
            <dt>Latest capacity</dt><dd>{num(s.latest_capacity_ah)} Ah</dd>
            <dt>SOH, measured</dt><dd>{pct(s.soh_measured)}</dd>
            <dt>SOH, predicted</dt>
            <dd className="pred">{pct(s.soh_predicted)}<div className="range">{pct(s.soh_p10)} – {pct(s.soh_p90)}</div></dd>
            <dt>Remaining life, ML</dt>
            <dd className="pred">{cyclesLabel(s.rul_predicted)}<div className="range">{Math.round(s.rul_p10)} – {Math.round(s.rul_p90)}</div></dd>
            <dt>Remaining life, physics</dt><dd className="phys">{cyclesLabel(s.rul_physics)}</dd>
            <dt>Fade fit Q₀ − a·kᵇ</dt>
            <dd className="phys">{num(s.physics.q0, 3)} − {s.physics.a.toExponential(2)}·k<sup>{num(s.physics.b, 2)}</sup></dd>
          </dl>
        </>
      )}
      <IngestForm onSubmit={onIngest} onReset={onReset} busy={busy} />
    </aside>
  );
}
