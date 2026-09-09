"""Synthetic NASA-like degradation data.

Used for tests, demos and CI where the real .mat files are absent. The
generator mimics the qualitative behaviour of NASA cells B0005-B0018:
roughly power-law capacity fade, periodic capacity regeneration after rest
(the characteristic sawtooth in the NASA curves) and measurement noise.
It is not a physics model; it exists so the pipeline runs end to end
without a download. The app reports which source is active.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.data.schema import NOMINAL_CAPACITY_AH, validate_cycles

# cell_id: (initial capacity Ah, fade coefficient, fade exponent, ambient °C)
DEFAULT_CELLS = {
    "B0005": (1.86, 0.0016, 1.15, 24.0),
    "B0006": (2.04, 0.0030, 1.10, 24.0),
    "B0007": (1.89, 0.0012, 1.18, 24.0),
    "B0018": (1.86, 0.0035, 1.05, 24.0),
}


def generate_cell(
    cell_id: str,
    n_cycles: int = 168,
    initial_capacity: float = 1.86,
    fade_coeff: float = 0.0016,
    fade_exp: float = 1.15,
    ambient_temp_c: float = 24.0,
    seed: int = 0,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    k = np.arange(1, n_cycles + 1)
    fade = fade_coeff * k**fade_exp
    regen = np.zeros(n_cycles)
    for start in range(25, n_cycles, 25):
        span = min(5, n_cycles - start)
        regen[start : start + span] += 0.04 * np.exp(-np.arange(span) / 2.0)
    capacity = initial_capacity - fade + regen + rng.normal(0, 0.004, n_cycles)
    capacity = np.clip(capacity, 0.5, None)

    soh = capacity / NOMINAL_CAPACITY_AH
    discharge_time = 3600 * capacity / 2.0 + rng.normal(0, 20, n_cycles)
    mean_temp = ambient_temp_c + 6 + 4 * (1 - soh) + rng.normal(0, 0.3, n_cycles)
    return pd.DataFrame(
        {
            "cell_id": cell_id,
            "cycle": k,
            "capacity_ah": capacity,
            "mean_voltage_v": 3.45 - 0.25 * (1 - soh) + rng.normal(0, 0.005, n_cycles),
            "min_voltage_v": 2.70 - 0.05 * (1 - soh) + rng.normal(0, 0.01, n_cycles),
            "mean_current_a": 2.0 + rng.normal(0, 0.01, n_cycles),
            "mean_temp_c": mean_temp,
            "max_temp_c": mean_temp + 3 + rng.normal(0, 0.3, n_cycles),
            "discharge_time_s": discharge_time,
            "ambient_temp_c": ambient_temp_c,
        }
    )


def generate_dataset(cells: dict | None = None, n_cycles: int = 168) -> pd.DataFrame:
    cells = cells or DEFAULT_CELLS
    frames = [
        generate_cell(cid, n_cycles, q0, a, b, amb, seed=i)
        for i, (cid, (q0, a, b, amb)) in enumerate(cells.items())
    ]
    return validate_cycles(pd.concat(frames, ignore_index=True))
