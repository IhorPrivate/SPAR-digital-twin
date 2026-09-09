"""The digital twin of a single cell.

A ``BatteryTwin`` holds the observed cycle history of one physical cell,
keeps a fitted physics baseline in sync with it, and combines that baseline
with the trained ML models to report current state of health, remaining
useful life and an uncertainty band. New measurements are pushed in with
``ingest`` and the twin re-synchronises itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.data.schema import CYCLE_COLUMNS, EOL_THRESHOLD, NOMINAL_CAPACITY_AH, validate_cycles
from app.features.engineering import build_features
from app.models.ml import HealthModel
from app.models.physics import FadeModel, fit_fade_model


@dataclass
class TwinState:
    cell_id: str
    cycles_observed: int
    latest_capacity_ah: float
    soh_measured: float
    soh_predicted: float
    soh_p10: float
    soh_p90: float
    rul_predicted: float
    rul_p10: float
    rul_p90: float
    rul_physics: int
    physics: dict
    health_status: str
    source: str = "twin"

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _status(soh: float) -> str:
    if soh < EOL_THRESHOLD:
        return "end_of_life"
    if soh < EOL_THRESHOLD + 0.08:
        return "maintenance_due"
    return "healthy"


@dataclass
class BatteryTwin:
    cell_id: str
    soh_model: HealthModel
    rul_model: HealthModel
    history: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=CYCLE_COLUMNS))
    fade: FadeModel | None = None

    def ingest(self, measurement: dict) -> "BatteryTwin":
        """Append one discharge-cycle measurement and re-sync the baseline."""
        row = {"cell_id": self.cell_id, **measurement}
        if "cycle" not in row or row["cycle"] is None:
            row["cycle"] = int(self.history["cycle"].max()) + 1 if len(self.history) else 1
        missing = [c for c in CYCLE_COLUMNS if c not in row]
        if missing:
            raise ValueError(f"Measurement is missing fields: {missing}")
        if len(self.history) and int(row["cycle"]) <= int(self.history["cycle"].max()):
            raise ValueError("cycle must be greater than the last observed cycle")
        new = pd.DataFrame([row])
        merged = new if self.history.empty else pd.concat([self.history, new], ignore_index=True)
        self.history = validate_cycles(merged)
        self._sync()
        return self

    def load_history(self, cycles: pd.DataFrame) -> "BatteryTwin":
        cycles = validate_cycles(cycles[cycles["cell_id"] == self.cell_id])
        self.history = cycles
        self._sync()
        return self

    def _sync(self) -> None:
        self.fade = fit_fade_model(self.history["cycle"].to_numpy(), self.history["capacity_ah"].to_numpy())

    def state(self) -> TwinState:
        if self.history.empty:
            raise RuntimeError(f"Twin {self.cell_id} has no observations")
        feats = build_features(self.history)
        latest = feats.iloc[[-1]]
        soh = self.soh_model.predict(latest).iloc[0]
        rul = self.rul_model.predict(latest).iloc[0]
        assert self.fade is not None
        current_cycle = int(latest["cycle"].iloc[0])
        rul_physics = max(self.fade.cycles_to_eol() - current_cycle, 0)
        soh_measured = float(latest["soh"].iloc[0])
        return TwinState(
            cell_id=self.cell_id,
            cycles_observed=int(len(self.history)),
            latest_capacity_ah=float(latest["capacity_ah"].iloc[0]),
            soh_measured=soh_measured,
            soh_predicted=float(soh["soh_p50"]),
            soh_p10=float(soh["soh_p10"]),
            soh_p90=float(soh["soh_p90"]),
            rul_predicted=float(rul["rul_p50"]),
            rul_p10=float(rul["rul_p10"]),
            rul_p90=float(rul["rul_p90"]),
            rul_physics=int(rul_physics),
            physics={"q0": self.fade.q0, "a": self.fade.a, "b": self.fade.b},
            health_status=_status(soh_measured),
        )

    def trajectory(self, horizon: int = 50) -> list[dict]:
        """Physics-baseline forecast of SOH for the next ``horizon`` cycles."""
        assert self.fade is not None
        start = int(self.history["cycle"].max()) if len(self.history) else 0
        cycles = range(start + 1, start + horizon + 1)
        return [
            {"cycle": k, "soh_forecast": float(self.fade.soh(k)), "capacity_forecast_ah": float(self.fade.capacity(k))}
            for k in cycles
        ]


def nominal_capacity() -> float:
    return NOMINAL_CAPACITY_AH
