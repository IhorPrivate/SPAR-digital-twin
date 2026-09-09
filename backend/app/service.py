"""Application service: owns the dataset, trained models and live twins.

Kept independent of FastAPI so it can be exercised directly in tests.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

import pandas as pd

from app.data.nasa_loader import load_nasa_directory
from app.data.synthetic import generate_dataset
from app.features.engineering import build_features
from app.models.ml import HealthModel, leave_one_cell_out
from app.twin import BatteryTwin


class BatteryService:
    def __init__(self, data_dir: str | os.PathLike | None = None):
        self._lock = threading.Lock()
        self.data_dir = Path(data_dir) if data_dir else None
        self.cycles, self.source = self._load()
        self.soh_model = HealthModel("soh")
        self.rul_model = HealthModel("rul")
        self.twins: dict[str, BatteryTwin] = {}
        self.metrics: dict | None = None

    # ---- data -------------------------------------------------------------
    def _load(self) -> tuple[pd.DataFrame, str]:
        if self.data_dir and self.data_dir.exists() and any(self.data_dir.glob("*.mat")):
            return load_nasa_directory(self.data_dir), "nasa"
        return generate_dataset(), "synthetic"

    def cell_ids(self) -> list[str]:
        return sorted(self.cycles["cell_id"].unique().tolist())

    def cell_summary(self) -> list[dict]:
        feats = build_features(self.cycles)
        out = []
        for cell, g in feats.groupby("cell_id"):
            out.append(
                {
                    "cell_id": str(cell),
                    "n_cycles": int(len(g)),
                    "initial_capacity_ah": float(g["capacity_ah"].iloc[0]),
                    "latest_capacity_ah": float(g["capacity_ah"].iloc[-1]),
                    "latest_soh": float(g["soh"].iloc[-1]),
                    "ambient_temp_c": float(g["ambient_temp_c"].iloc[0]),
                }
            )
        return out

    def cell_cycles(self, cell_id: str) -> pd.DataFrame:
        if cell_id not in self.cell_ids():
            raise KeyError(cell_id)
        return build_features(self.cycles[self.cycles["cell_id"] == cell_id])

    # ---- models -----------------------------------------------------------
    @property
    def is_trained(self) -> bool:
        return self.soh_model.is_fitted and self.rul_model.is_fitted

    def train(self, evaluate: bool = True) -> dict:
        with self._lock:
            feats = build_features(self.cycles)
            self.soh_model.fit(feats)
            self.rul_model.fit(feats)
            self.metrics = {
                "n_cells": len(self.cell_ids()),
                "n_cycles": int(len(feats)),
                "source": self.source,
                "cv": {},
            }
            if evaluate and len(self.cell_ids()) > 1:
                self.metrics["cv"] = {
                    t: leave_one_cell_out(self.cycles, t).to_dict() for t in ("soh", "rul")
                }
            # Twins hold model references; nothing else to refresh.
            return self.metrics

    def predict_history(self, cell_id: str) -> pd.DataFrame:
        """Per-cycle predictions for a cell, for plotting against truth."""
        self._require_trained()
        feats = self.cell_cycles(cell_id)
        soh = self.soh_model.predict(feats)
        rul = self.rul_model.predict(feats)
        return pd.concat([feats[["cycle", "capacity_ah", "soh", "rul"]], soh, rul], axis=1)

    # ---- twins ------------------------------------------------------------
    def twin(self, cell_id: str) -> BatteryTwin:
        self._require_trained()
        with self._lock:
            if cell_id not in self.twins:
                twin = BatteryTwin(cell_id, self.soh_model, self.rul_model)
                if cell_id in self.cell_ids():
                    twin.load_history(self.cycles)
                self.twins[cell_id] = twin
            return self.twins[cell_id]

    def reset_twin(self, cell_id: str) -> None:
        with self._lock:
            self.twins.pop(cell_id, None)

    def _require_trained(self) -> None:
        if not self.is_trained:
            raise RuntimeError("Models are not trained yet. Call POST /api/train first.")
