"""Unified cycle-level schema shared by every data source.

One row per discharge cycle. Every loader (NASA .mat files, synthetic
generator, future CALCE/Oxford loaders) must produce exactly these columns
so the feature and model layers are source-agnostic.
"""
from __future__ import annotations

import pandas as pd

CYCLE_COLUMNS: list[str] = [
    "cell_id",          # e.g. "B0005"
    "cycle",            # 1-based discharge cycle index
    "capacity_ah",      # measured discharge capacity (Ah)
    "mean_voltage_v",   # mean terminal voltage during discharge
    "min_voltage_v",    # minimum terminal voltage reached
    "mean_current_a",   # mean discharge current (positive magnitude)
    "mean_temp_c",      # mean cell temperature
    "max_temp_c",       # peak cell temperature
    "discharge_time_s", # duration of the discharge step
    "ambient_temp_c",   # chamber ambient temperature
]

NOMINAL_CAPACITY_AH = 2.0   # NASA 18650 cells
EOL_THRESHOLD = 0.70        # NASA defines EOL at 30 % fade (1.4 Ah)


def validate_cycles(df: pd.DataFrame) -> pd.DataFrame:
    """Check that a DataFrame conforms to the cycle schema.

    Returns the frame sorted by (cell_id, cycle) and restricted to the schema
    columns. Raises ValueError with an actionable message otherwise.
    """
    missing = [c for c in CYCLE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Cycle frame is missing columns: {missing}")
    if df.empty:
        raise ValueError("Cycle frame is empty")
    if (df["capacity_ah"] <= 0).any():
        raise ValueError("capacity_ah must be positive")
    if df.duplicated(subset=["cell_id", "cycle"]).any():
        raise ValueError("Duplicate (cell_id, cycle) rows found")
    return df.sort_values(["cell_id", "cycle"]).reset_index(drop=True)[CYCLE_COLUMNS]
