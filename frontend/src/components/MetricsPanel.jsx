import { num } from "../format";

export default function MetricsPanel({ metrics }) {
  if (!metrics) return null;
  const cv = metrics.cv || {};
  const soh = cv.soh;
  const rul = cv.rul;
  return (
    <section aria-label="Model evaluation">
      <dl className="metrics">
        <div className="metric"><dt>Cells in training set</dt><dd>{metrics.n_cells}</dd></div>
        <div className="metric"><dt>Cycles</dt><dd>{metrics.n_cycles}</dd></div>
        {soh && <div className="metric"><dt>SOH MAE, leave-one-cell-out</dt><dd>{num(soh.mae, 4)}</dd></div>}
        {rul && <div className="metric"><dt>RUL MAE, cycles</dt><dd>{num(rul.mae, 1)}</dd></div>}
      </dl>
      {soh && (
        <table className="metrics-table">
          <thead>
            <tr><th>Held-out cell</th><th>SOH MAE</th><th>SOH RMSE</th><th>RUL MAE</th><th>RUL RMSE</th></tr>
          </thead>
          <tbody>
            {Object.keys(soh.per_cell).map((id) => (
              <tr key={id}>
                <td>{id}</td>
                <td>{num(soh.per_cell[id].mae, 4)}</td>
                <td>{num(soh.per_cell[id].rmse, 4)}</td>
                <td>{num(rul?.per_cell[id]?.mae, 1)}</td>
                <td>{num(rul?.per_cell[id]?.rmse, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
