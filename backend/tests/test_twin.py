import pytest

from app.data.synthetic import generate_cell
from app.twin import BatteryTwin, _status


def _measurement(row):
    return {k: row[k] for k in row.index if k not in ("cell_id",)}


def test_twin_ingests_and_reports_state(trained_service):
    twin = BatteryTwin("NEW", trained_service.soh_model, trained_service.rul_model)
    cell = generate_cell("NEW", 30, seed=9)
    for _, r in cell.iterrows():
        twin.ingest(_measurement(r))
    s = twin.state()
    assert s.cycles_observed == 30
    assert s.soh_measured == pytest.approx(cell["capacity_ah"].iloc[-1] / 2.0)
    assert s.soh_p10 <= s.soh_predicted <= s.soh_p90
    assert s.rul_predicted >= 0
    assert s.health_status in {"healthy", "maintenance_due", "end_of_life"}
    assert len(twin.trajectory(10)) == 10
    assert twin.trajectory(3)[0]["cycle"] == 31


def test_twin_auto_increments_cycle(trained_service):
    twin = BatteryTwin("NEW", trained_service.soh_model, trained_service.rul_model)
    row = generate_cell("NEW", 1).iloc[0]
    m = _measurement(row)
    m.pop("cycle")
    twin.ingest(m).ingest(m)
    assert twin.history["cycle"].tolist() == [1, 2]


def test_twin_rejects_out_of_order_cycle(trained_service):
    twin = BatteryTwin("NEW", trained_service.soh_model, trained_service.rul_model)
    row = _measurement(generate_cell("NEW", 1).iloc[0])
    twin.ingest(row)
    with pytest.raises(ValueError, match="greater than"):
        twin.ingest(row)


def test_twin_rejects_incomplete_measurement(trained_service):
    twin = BatteryTwin("NEW", trained_service.soh_model, trained_service.rul_model)
    with pytest.raises(ValueError, match="missing fields"):
        twin.ingest({"capacity_ah": 1.8})


def test_twin_state_without_history(trained_service):
    twin = BatteryTwin("NEW", trained_service.soh_model, trained_service.rul_model)
    with pytest.raises(RuntimeError, match="no observations"):
        twin.state()


def test_status_thresholds():
    assert _status(0.95) == "healthy"
    assert _status(0.75) == "maintenance_due"
    assert _status(0.65) == "end_of_life"
