import numpy as np

from app.data.schema import EOL_THRESHOLD
from app.data.synthetic import generate_cell, generate_dataset
from app.features.engineering import FEATURE_COLUMNS, add_targets, build_features, feature_matrix


def test_targets_soh_and_rul():
    df = generate_cell("X", 100, initial_capacity=1.9, fade_coeff=0.01, fade_exp=1.0)
    out = add_targets(df)
    assert (out["soh"] == out["capacity_ah"] / 2.0).all()
    first_eol = out.index[out["soh"] < EOL_THRESHOLD][0]
    assert out.loc[first_eol, "rul"] == 0
    assert out.loc[0, "rul"] == out.loc[first_eol, "cycle"] - 1
    assert (out["rul"] >= 0).all()


def test_rul_censored_when_cell_never_reaches_eol():
    df = generate_cell("X", 30, fade_coeff=0.0001)
    out = add_targets(df)
    assert out["rul"].iloc[-1] == 0
    assert out["rul"].iloc[0] == 29


def test_build_features_has_no_nans_and_all_columns():
    out = build_features(generate_dataset(n_cycles=30))
    assert set(FEATURE_COLUMNS) <= set(out.columns)
    assert not out[FEATURE_COLUMNS].isna().any().any()
    assert feature_matrix(out).shape == (len(out), len(FEATURE_COLUMNS))


def test_features_are_causal():
    """Features at cycle k must not change when later cycles are appended."""
    full = generate_cell("X", 40)
    a = build_features(full.iloc[:20])
    b = build_features(full)
    np.testing.assert_allclose(feature_matrix(a), feature_matrix(b.iloc[:20]))
