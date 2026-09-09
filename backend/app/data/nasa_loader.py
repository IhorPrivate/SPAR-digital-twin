"""Loader for the NASA Ames Prognostics Center battery dataset.

The dataset ships as MATLAB files (B0005.mat, B0006.mat, ...). Each file
contains a struct named after the cell with a ``cycle`` array; every element
has ``type`` ('charge' | 'discharge' | 'impedance'), ``ambient_temperature``,
``time`` and a ``data`` struct with per-sample measurements. Only discharge
cycles carry a ``Capacity`` field, which is the health label we use.

Download the "Battery Data Set" (BatteryAgingARC-FY08Q4) from the NASA
PCoE data repository and place the .mat files in ``data/nasa/``.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.data.schema import validate_cycles


def _scalar(x) -> float:
    """MATLAB scalars arrive as nested 1x1 arrays; flatten them."""
    return float(np.asarray(x).ravel()[0])


def _vector(x) -> np.ndarray:
    return np.asarray(x, dtype=float).ravel()


def parse_mat_struct(cell_id: str, cycles) -> pd.DataFrame:
    """Turn the ``cycle`` array of a NASA .mat file into cycle rows.

    ``cycles`` is the object array produced by ``scipy.io.loadmat`` with
    ``squeeze_me=True, struct_as_record=False``; any object exposing the same
    attributes (``type``, ``ambient_temperature``, ``data``) works, which is
    what the tests rely on.
    """
    rows = []
    discharge_idx = 0
    for c in np.atleast_1d(cycles):
        if str(c.type).strip() != "discharge":
            continue
        d = c.data
        discharge_idx += 1
        voltage = _vector(d.Voltage_measured)
        current = _vector(d.Current_measured)
        temp = _vector(d.Temperature_measured)
        t = _vector(d.Time)
        rows.append(
            {
                "cell_id": cell_id,
                "cycle": discharge_idx,
                "capacity_ah": _scalar(d.Capacity),
                "mean_voltage_v": float(voltage.mean()),
                "min_voltage_v": float(voltage.min()),
                "mean_current_a": float(np.abs(current).mean()),
                "mean_temp_c": float(temp.mean()),
                "max_temp_c": float(temp.max()),
                "discharge_time_s": float(t.max() - t.min()),
                "ambient_temp_c": _scalar(c.ambient_temperature),
            }
        )
    if not rows:
        raise ValueError(f"No discharge cycles found for {cell_id}")
    return pd.DataFrame(rows)


def load_mat_file(path: Path) -> pd.DataFrame:
    """Load one NASA battery file (e.g. B0005.mat) into the cycle schema."""
    from scipy.io import loadmat  # lazy: scipy is heavy to import

    path = Path(path)
    cell_id = path.stem
    mat = loadmat(path, squeeze_me=True, struct_as_record=False)
    if cell_id not in mat:
        raise ValueError(f"{path.name} does not contain a '{cell_id}' struct")
    return validate_cycles(parse_mat_struct(cell_id, mat[cell_id].cycle))


def load_nasa_directory(directory: Path) -> pd.DataFrame:
    """Load every ``*.mat`` file in a directory and concatenate the cells."""
    directory = Path(directory)
    files = sorted(directory.glob("*.mat"))
    if not files:
        raise FileNotFoundError(f"No .mat files found in {directory}")
    return validate_cycles(pd.concat([load_mat_file(f) for f in files], ignore_index=True))
