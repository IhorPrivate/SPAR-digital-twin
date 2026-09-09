import numpy as np
import pytest

from app.models.physics import FadeModel, fit_fade_model, power_law


def test_fit_recovers_parameters_on_clean_curve():
    k = np.arange(1, 150)
    q = power_law(k, 1.9, 0.002, 1.1)
    m = fit_fade_model(k, q)
    assert m.q0 == pytest.approx(1.9, abs=0.01)
    assert m.a == pytest.approx(0.002, rel=0.2)
    assert m.b == pytest.approx(1.1, abs=0.1)


def test_cycles_to_eol():
    m = FadeModel(q0=2.0, a=0.01, b=1.0)  # 2.0 - 0.01k = 1.4 -> k = 60
    assert m.cycles_to_eol() == 60
    assert FadeModel(2.0, 0.0, 1.0).cycles_to_eol() == 5000
    assert FadeModel(1.0, 0.01, 1.0).cycles_to_eol() == 0


def test_short_history_falls_back_to_flat():
    m = fit_fade_model(np.array([1, 2]), np.array([1.8, 1.79]))
    assert m.a == 0.0
    assert m.capacity(100) == pytest.approx(1.795)


def test_soh_uses_nominal_capacity():
    assert FadeModel(2.0, 0.0, 1.0).soh(10) == pytest.approx(1.0)
