from app.data.synthetic import generate_cell


def test_health_reports_source_and_training(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["data_source"] == "synthetic"
    assert r.json()["trained"] is True


def test_list_cells(client):
    cells = client.get("/api/cells").json()
    assert {c["cell_id"] for c in cells} == {"B0005", "B0006", "B0007", "B0018"}
    assert all(c["n_cycles"] == 80 for c in cells)


def test_cell_cycles_and_404(client):
    r = client.get("/api/cells/B0005/cycles")
    assert r.status_code == 200 and len(r.json()) == 80
    assert "soh" in r.json()[0]
    assert client.get("/api/cells/NOPE/cycles").status_code == 404


def test_train_and_metrics(untrained_client):
    assert untrained_client.get("/api/metrics").status_code == 409
    assert untrained_client.get("/api/cells/B0005/predictions").status_code == 409
    assert untrained_client.get("/api/twins/B0005").status_code == 409
    r = untrained_client.post("/api/train", json={"evaluate": True})
    assert r.status_code == 200
    body = r.json()
    assert body["n_cells"] == 4
    assert set(body["cv"]) == {"soh", "rul"}
    assert untrained_client.get("/api/metrics").json() == body


def test_predictions_endpoint(client):
    rows = client.get("/api/cells/B0005/predictions").json()
    assert len(rows) == 80
    assert {"soh_p10", "soh_p50", "soh_p90", "rul_p50"} <= set(rows[0])
    assert client.get("/api/cells/NOPE/predictions").status_code == 404


def test_twin_lifecycle(client):
    state = client.get("/api/twins/B0005?horizon=5").json()
    assert state["state"]["cycles_observed"] == 80
    assert len(state["trajectory"]) == 5

    row = generate_cell("B0005", 81, seed=1).iloc[-1]
    m = {k: float(row[k]) for k in row.index if k != "cell_id"}
    m["cycle"] = 81
    r = client.post("/api/twins/B0005/ingest", json=m)
    assert r.status_code == 200
    assert r.json()["state"]["cycles_observed"] == 81

    # same cycle again -> validation error from the twin
    assert client.post("/api/twins/B0005/ingest", json=m).status_code == 422
    # malformed body -> pydantic validation
    assert client.post("/api/twins/B0005/ingest", json={"capacity_ah": -1}).status_code == 422

    assert client.delete("/api/twins/B0005").json() == {"reset": "B0005"}
    assert client.get("/api/twins/B0005").json()["state"]["cycles_observed"] == 80


def test_twin_for_unknown_cell_starts_empty_then_accepts_data(client):
    m = generate_cell("FRESH", 1).iloc[0]
    body = {k: float(m[k]) for k in m.index if k != "cell_id"}
    body["cycle"] = 1
    r = client.post("/api/twins/FRESH/ingest", json=body)
    assert r.status_code == 200
    assert r.json()["state"]["cycles_observed"] == 1
    client.delete("/api/twins/FRESH")
