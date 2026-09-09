"""Cycle-level feature engineering.

Every feature is computed causally: a row at cycle k only uses cycles <= k,
so the same function serves offline training and the online twin.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.data.schema import EOL_THRESHOLD, NOMINAL_CAPACITY_AH

FEATURE_COLUMNS: list[str] = [
    "cycle",
    "mean_voltage_v",
    "min_voltage_v",
    "mean_current_a",
    "mean_temp_c",
    "max_temp_c",
    "discharge_time_s",
    "ambient_temp_c",
    "soh_lag1",
    "soh_lag5",
    "soh_roll_mean5",
    "soh_roll_std5",
    "fade_rate5",
    "temp_delta",
]


def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Add SOH and RUL labels.

    SOH = capacity / nominal. RUL = cycles remaining until SOH first drops
    below the EOL threshold; cells that never reach EOL get RUL measured to
    their last observed cycle (right-censored).
    """
    out = df.copy()
    out["soh"] = out["capacity_ah"] / NOMINAL_CAPACITY_AH

    rul = pd.Series(0.0, index=out.index)
    for _, group in out.groupby("cell_id"):
        below = group.index[group["soh"] < EOL_THRESHOLD]
        eol_cycle = group.loc[below[0], "cycle"] if len(below) else group["cycle"].max()
        rul.loc[group.index] = (eol_cycle - group["cycle"]).clip(lower=0)
    out["rul"] = rul
    return out


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute lagged/rolling health features per cell.

    Input must follow the cycle schema and be sorted by (cell_id, cycle).
    Output keeps all input columns and adds targets + FEATURE_COLUMNS.
    """
    out = add_targets(df)
    g = out.groupby("cell_id")["soh"]
    out["soh_lag1"] = g.shift(1)
    out["soh_lag5"] = g.shift(5)
    out["soh_roll_mean5"] = g.transform(lambda s: s.rolling(5, min_periods=1).mean())
    out["soh_roll_std5"] = g.transform(lambda s: s.rolling(5, min_periods=2).std())
    out["fade_rate5"] = (out["soh"] - out["soh_lag5"]) / 5.0
    out["temp_delta"] = out["max_temp_c"] - out["ambient_temp_c"]

    # First cycles have no history: fall back to the current value / zero
    # rather than dropping them so the twin can predict from cycle 1.
    out["soh_lag1"] = out["soh_lag1"].fillna(out["soh"])
    out["soh_lag5"] = out["soh_lag5"].fillna(out["soh"])
    out["soh_roll_std5"] = out["soh_roll_std5"].fillna(0.0)
    out["fade_rate5"] = out["fade_rate5"].fillna(0.0)
    return out


def feature_matrix(df: pd.DataFrame) -> np.ndarray:
    return df[FEATURE_COLUMNS].to_numpy(dtype=float)
