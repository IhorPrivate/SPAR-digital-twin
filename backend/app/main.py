"""REST API for the battery digital-twin framework."""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.service import BatteryService
from app.twin import nominal_capacity


class Measurement(BaseModel):
    cycle: int | None = Field(default=None, description="Omit to auto-increment")
    capacity_ah: float = Field(gt=0)
    mean_voltage_v: float
    min_voltage_v: float
    mean_current_a: float
    mean_temp_c: float
    max_temp_c: float
    discharge_time_s: float = Field(gt=0)
    ambient_temp_c: float


class TrainRequest(BaseModel):
    evaluate: bool = True


def create_app(service: BatteryService | None = None) -> FastAPI:
    svc = service or BatteryService(os.environ.get("NASA_DATA_DIR", "data/nasa"))
    app = FastAPI(title="Battery Digital Twin API", version="0.1.0")
    app.state.service = svc
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
    )

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "data_source": svc.source,
            "trained": svc.is_trained,
            "nominal_capacity_ah": nominal_capacity(),
        }

    @app.get("/api/cells")
    def cells():
        return svc.cell_summary()

    @app.get("/api/cells/{cell_id}/cycles")
    def cell_cycles(cell_id: str):
        try:
            df = svc.cell_cycles(cell_id)
        except KeyError:
            raise HTTPException(404, f"Unknown cell {cell_id}")
        return df.to_dict(orient="records")

    @app.post("/api/train")
    def train(req: TrainRequest):
        return svc.train(evaluate=req.evaluate)

    @app.get("/api/metrics")
    def metrics():
        if svc.metrics is None:
            raise HTTPException(409, "Models are not trained yet")
        return svc.metrics

    @app.get("/api/cells/{cell_id}/predictions")
    def predictions(cell_id: str):
        try:
            return svc.predict_history(cell_id).to_dict(orient="records")
        except RuntimeError as e:
            raise HTTPException(409, str(e))
        except KeyError:
            raise HTTPException(404, f"Unknown cell {cell_id}")

    @app.get("/api/twins/{cell_id}")
    def twin_state(cell_id: str, horizon: int = 50):
        try:
            twin = svc.twin(cell_id)
            return {"state": twin.state().to_dict(), "trajectory": twin.trajectory(horizon)}
        except RuntimeError as e:
            raise HTTPException(409, str(e))

    @app.post("/api/twins/{cell_id}/ingest")
    def twin_ingest(cell_id: str, m: Measurement):
        try:
            twin = svc.twin(cell_id)
            twin.ingest(m.model_dump(exclude_none=True))
            return {"state": twin.state().to_dict(), "trajectory": twin.trajectory(50)}
        except RuntimeError as e:
            raise HTTPException(409, str(e))
        except ValueError as e:
            raise HTTPException(422, str(e))

    @app.delete("/api/twins/{cell_id}")
    def twin_reset(cell_id: str):
        svc.reset_twin(cell_id)
        return {"reset": cell_id}

    return app


app = create_app()
