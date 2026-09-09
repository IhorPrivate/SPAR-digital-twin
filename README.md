# Battery Digital Twin

AI-enhanced digital-twin framework for Li-ion battery health management,
built around the NASA Ames Prognostics battery dataset. It implements the
three layers of the secondment plan:

| Layer | What it is | Where |
|---|---|---|
| 1. Physics | Empirical power-law capacity-fade model `Q(k) = Q0 − a·k^b`, fitted per cell and re-synced on every ingested cycle | `backend/app/models/physics.py` |
| 2. Sensing | Cycle-level schema fed by NASA `.mat` files (or a synthetic fallback), with a REST ingest endpoint for live measurements | `backend/app/data/`, `POST /api/twins/{id}/ingest` |
| 3. ML | Quantile gradient-boosting models for state of health (SOH) and remaining useful life (RUL) with 10–90 % uncertainty bands, evaluated leave-one-cell-out | `backend/app/models/ml.py` |

The `BatteryTwin` class (`backend/app/twin.py`) ties them together: it holds
one cell's history, keeps the physics fit current, and combines it with the
ML models to report SOH, RUL, a confidence band and a health status.

## Run it

```bash
# 1. (optional) copy B0005.mat, B0006.mat, ... into data/nasa/
# 2. build and start
docker compose up --build
```

- UI: http://localhost:8080
- API: http://localhost:8000/api/health (Swagger at /docs)

Without NASA files the backend uses a synthetic NASA-like dataset and says so
in `GET /api/health` and in the UI's left rail.

In the UI: pick a cell, press **Train models**, then inspect the capacity-fade
chart (measured vs predicted vs physics forecast) and the twin panel. Add a
discharge cycle in the form to push a new measurement into the twin and watch
it re-estimate.

## Tests

Everything is covered: backend 41 tests (99 % line coverage), frontend 18
tests (components, API client, formatting, app flow).

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
# or locally
make test-backend      # pytest + coverage
make test-frontend     # vitest + testing-library
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | data source, trained flag |
| GET | `/api/cells` | per-cell summary |
| GET | `/api/cells/{id}/cycles` | cycle rows with engineered features and labels |
| POST | `/api/train` | fit SOH/RUL models, run leave-one-cell-out CV |
| GET | `/api/metrics` | last training metrics |
| GET | `/api/cells/{id}/predictions` | per-cycle SOH/RUL predictions with quantiles |
| GET | `/api/twins/{id}?horizon=50` | twin state + physics trajectory |
| POST | `/api/twins/{id}/ingest` | push one discharge-cycle measurement |
| DELETE | `/api/twins/{id}` | reset the twin to the stored history |

## Layout

```
backend/
  app/data/        schema, NASA .mat loader, synthetic generator
  app/features/    causal cycle-level feature engineering + SOH/RUL labels
  app/models/      physics baseline, ML quantile models, LOCO evaluation
  app/twin.py      BatteryTwin
  app/service.py   dataset + models + twin registry (framework-independent)
  app/main.py      FastAPI routes
  tests/
frontend/
  src/components/  CellRail, HealthChart, MetricsPanel, TwinPanel
  src/api.js       REST client
  src/test/        vitest suites
docker-compose.yml       runtime stack (nginx serves the UI and proxies /api)
docker-compose.test.yml  both test suites in isolated containers
```

## Local development

```bash
cd backend && pip install -r requirements-dev.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev      # proxies /api to :8000
```

## Notes for the research plan

- Evaluation is leave-one-cell-out, so reported MAE/RMSE reflect
  generalisation to unseen cells, not memorised cycles.
- The hybrid design (physics baseline + ML) is the natural comparison axis
  for the paper: `rul_physics` vs `rul_predicted` per cell are both exposed.
- Sequence models (LSTM/GRU on raw voltage curves) slot in as another
  `HealthModel` implementation; the feature layer is already causal so the
  same twin loop applies.
- Add CALCE/Oxford loaders by emitting the same `CYCLE_COLUMNS` schema.
