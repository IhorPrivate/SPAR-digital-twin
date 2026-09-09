import { pct } from "../format";

export default function CellRail({ cells, selected, onSelect, source, trained, training, onTrain }) {
  return (
    <aside className="rail" aria-label="Cells">
      <h1>Battery digital twin</h1>
      <p className="source">
        Data: {source === "nasa" ? "NASA PCoE Li-ion set" : "synthetic NASA-like set"}
      </p>
      <ul className="cell-list">
        {cells.map((c) => (
          <li key={c.cell_id}>
            <button
              className="cell-btn"
              aria-current={c.cell_id === selected ? "true" : undefined}
              onClick={() => onSelect(c.cell_id)}
            >
              <span>{c.cell_id}</span>
              <span className="soh">{pct(c.latest_soh, 0)}</span>
            </button>
          </li>
        ))}
      </ul>
      <button className="train" onClick={onTrain} disabled={training}>
        {training ? "Training…" : trained ? "Retrain models" : "Train models"}
      </button>
    </aside>
  );
}
