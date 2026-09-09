from types import SimpleNamespace

import numpy as np
import pytest

from app.data.nasa_loader import load_mat_file, load_nasa_directory, parse_mat_struct


def _cycle(kind, capacity=1.8, amb=24):
    t = np.linspace(0, 3000, 50)
    data = SimpleNamespace(
        Voltage_measured=4.2 - 1.5 * t / 3000,
        Current_measured=np.full(50, -2.0),
        Temperature_measured=24 + 8 * t / 3000,
        Time=t,
        Capacity=np.array([[capacity]]),
    )
    return SimpleNamespace(type=kind, ambient_temperature=np.array([[amb]]), data=data)


def test_parse_mat_struct_keeps_only_discharge_cycles():
    cycles = np.array(
        [_cycle("charge"), _cycle("discharge", 1.85), _cycle("impedance"), _cycle("discharge", 1.80)],
        dtype=object,
    )
    df = parse_mat_struct("B0005", cycles)
    assert list(df["cycle"]) == [1, 2]
    assert df["capacity_ah"].tolist() == pytest.approx([1.85, 1.80])
    assert df["mean_current_a"].iloc[0] == pytest.approx(2.0)
    assert df["discharge_time_s"].iloc[0] == pytest.approx(3000)
    assert df["min_voltage_v"].iloc[0] == pytest.approx(2.7)
    assert df["ambient_temp_c"].iloc[0] == 24


def test_parse_mat_struct_raises_without_discharge():
    with pytest.raises(ValueError, match="No discharge"):
        parse_mat_struct("B0005", np.array([_cycle("charge")], dtype=object))


def test_load_nasa_directory_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_nasa_directory(tmp_path)


def test_load_mat_file_roundtrip(tmp_path):
    """Write a real .mat file mirroring the NASA layout and read it back."""
    from scipy.io import savemat

    def rec(kind, cap):
        t = np.linspace(0, 3000, 50)
        data = {
            "Voltage_measured": 4.2 - 1.5 * t / 3000,
            "Current_measured": np.full(50, -2.0),
            "Temperature_measured": 24 + 8 * t / 3000,
            "Time": t,
            "Capacity": cap,
        }
        return {"type": kind, "ambient_temperature": 24, "time": np.zeros(6), "data": data}

    cycle = np.empty(3, dtype=object)
    cycle[0], cycle[1], cycle[2] = rec("charge", 0), rec("discharge", 1.85), rec("discharge", 1.8)
    savemat(tmp_path / "B0005.mat", {"B0005": {"cycle": cycle}})

    df = load_mat_file(tmp_path / "B0005.mat")
    assert len(df) == 2
    assert df["capacity_ah"].tolist() == pytest.approx([1.85, 1.8])
    both = load_nasa_directory(tmp_path)
    assert both.equals(df)


def test_load_mat_file_wrong_struct_name(tmp_path):
    from scipy.io import savemat

    savemat(tmp_path / "B0005.mat", {"OTHER": np.zeros(1)})
    with pytest.raises(ValueError, match="does not contain"):
        load_mat_file(tmp_path / "B0005.mat")
