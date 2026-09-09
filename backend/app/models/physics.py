"""Empirical capacity-fade model standing in for the multi-physics layer.

Li-ion capacity loss driven by SEI growth is commonly approximated by a
power law in cycle number: Q(k) = Q0 - a * k**b, with b ~ 0.5-1.2. Fitting
this per cell gives a smooth, physically motivated baseline. The ML model
in ``ml.py`` learns the *residual* between this curve and reality, which is
what makes the framework a hybrid twin rather than a black-box regressor.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import curve_fit

from app.data.schema import EOL_THRESHOLD, NOMINAL_CAPACITY_AH


def power_law(k: np.ndarray, q0: float, a: float, b: float) -> np.ndarray:
    return q0 - a * np.power(np.asarray(k, dtype=float), b)


@dataclass(frozen=True)
class FadeModel:
    q0: float
    a: float
    b: float

    def capacity(self, cycle) -> np.ndarray:
        return power_law(np.asarray(cycle, dtype=float), self.q0, self.a, self.b)

    def soh(self, cycle) -> np.ndarray:
        return self.capacity(cycle) / NOMINAL_CAPACITY_AH

    def cycles_to_eol(self, threshold: float = EOL_THRESHOLD, max_cycles: int = 5000) -> int:
        """First cycle at which the fitted curve crosses the EOL threshold."""
        if self.a <= 0:
            return max_cycles
        target = self.q0 - threshold * NOMINAL_CAPACITY_AH
        if target <= 0:
            return 0
        k = (target / self.a) ** (1.0 / self.b)
        return int(min(max(np.ceil(k - 1e-9), 0), max_cycles))


def fit_fade_model(cycle: np.ndarray, capacity: np.ndarray) -> FadeModel:
    """Least-squares fit of the power law; robust to short histories."""
    cycle = np.asarray(cycle, dtype=float)
    capacity = np.asarray(capacity, dtype=float)
    if len(cycle) < 3:
        # Not enough points for a curve: flat line at the observed capacity.
        return FadeModel(q0=float(capacity.mean()), a=0.0, b=1.0)
    p0 = (float(capacity[0]), 1e-3, 1.0)
    bounds = ([0.0, 0.0, 0.3], [5.0, 1.0, 2.0])
    try:
        params, _ = curve_fit(power_law, cycle, capacity, p0=p0, bounds=bounds, maxfev=20_000)
    except (RuntimeError, ValueError):
        slope = np.polyfit(cycle, capacity, 1)[0]
        return FadeModel(q0=float(capacity[0]), a=float(max(-slope, 0.0)), b=1.0)
    return FadeModel(*map(float, params))
