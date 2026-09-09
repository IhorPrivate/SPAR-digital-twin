"""Machine-learning layer: SOH and RUL predictors with uncertainty.

Two estimators per target (median and upper/lower quantiles) built on
scikit-learn's HistGradientBoostingRegressor. Evaluation is strictly
leave-one-cell-out so cycles of the same cell never leak across the split.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from app.features.engineering import FEATURE_COLUMNS, build_features, feature_matrix

QUANTILES = (0.1, 0.5, 0.9)


def _make(quantile: float, seed: int) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        loss="quantile",
        quantile=quantile,
        max_iter=200,
        learning_rate=0.05,
        max_depth=4,
        min_samples_leaf=10,
        random_state=seed,
    )


@dataclass
class HealthModel:
    """Quantile ensemble predicting one target (soh or rul)."""

    target: str
    seed: int = 0
    estimators: dict[float, HistGradientBoostingRegressor] = field(default_factory=dict)

    def fit(self, features: pd.DataFrame) -> "HealthModel":
        X = feature_matrix(features)
        y = features[self.target].to_numpy(dtype=float)
        self.estimators = {q: _make(q, self.seed).fit(X, y) for q in QUANTILES}
        return self

    @property
    def is_fitted(self) -> bool:
        return len(self.estimators) == len(QUANTILES)

    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        if not self.is_fitted:
            raise RuntimeError(f"{self.target} model is not trained")
        X = feature_matrix(features)
        cols = {f"{self.target}_p{int(q * 100)}": self.estimators[q].predict(X) for q in QUANTILES}
        out = pd.DataFrame(cols, index=features.index)
        # Quantile regressors are fitted independently; enforce ordering.
        lo, med, hi = (f"{self.target}_p10", f"{self.target}_p50", f"{self.target}_p90")
        out[lo] = np.minimum(out[lo], out[med])
        out[hi] = np.maximum(out[hi], out[med])
        if self.target == "rul":
            out[[lo, med, hi]] = out[[lo, med, hi]].clip(lower=0)
        return out


@dataclass
class CVResult:
    target: str
    per_cell: dict[str, dict[str, float]]
    mae: float
    rmse: float

    def to_dict(self) -> dict:
        return {"target": self.target, "mae": self.mae, "rmse": self.rmse, "per_cell": self.per_cell}


def leave_one_cell_out(cycles: pd.DataFrame, target: str, seed: int = 0) -> CVResult:
    """Train on all cells but one, test on the held-out cell, repeat."""
    feats = build_features(cycles)
    per_cell: dict[str, dict[str, float]] = {}
    all_true, all_pred = [], []
    for cell in feats["cell_id"].unique():
        train, test = feats[feats["cell_id"] != cell], feats[feats["cell_id"] == cell]
        if train.empty:
            continue
        pred = HealthModel(target, seed).fit(train).predict(test)[f"{target}_p50"]
        y = test[target]
        per_cell[str(cell)] = {
            "mae": float(mean_absolute_error(y, pred)),
            "rmse": float(np.sqrt(mean_squared_error(y, pred))),
            "n_cycles": int(len(test)),
        }
        all_true.append(y.to_numpy())
        all_pred.append(pred.to_numpy())
    if not all_true:
        raise ValueError("Need at least two cells for leave-one-cell-out CV")
    yt, yp = np.concatenate(all_true), np.concatenate(all_pred)
    return CVResult(
        target=target,
        per_cell=per_cell,
        mae=float(mean_absolute_error(yt, yp)),
        rmse=float(np.sqrt(mean_squared_error(yt, yp))),
    )


def feature_names() -> list[str]:
    return list(FEATURE_COLUMNS)
