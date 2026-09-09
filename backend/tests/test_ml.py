import pytest

from app.data.synthetic import generate_cell
from app.features.engineering import build_features
from app.models.ml import HealthModel, feature_names, leave_one_cell_out


def test_soh_model_predicts_close_to_truth(cycles):
    feats = build_features(cycles)
    model = HealthModel("soh").fit(feats)
    pred = model.predict(feats)
    err = (pred["soh_p50"] - feats["soh"]).abs().mean()
    assert err < 0.02
    assert (pred["soh_p10"] <= pred["soh_p50"]).all()
    assert (pred["soh_p90"] >= pred["soh_p50"]).all()


def test_rul_model_is_nonnegative(cycles):
    feats = build_features(cycles)
    pred = HealthModel("rul").fit(feats).predict(feats)
    assert (pred[["rul_p10", "rul_p50", "rul_p90"]] >= 0).all().all()


def test_predict_before_fit_raises(cycles):
    with pytest.raises(RuntimeError, match="not trained"):
        HealthModel("soh").predict(build_features(cycles))


def test_leave_one_cell_out_reports_every_cell(cycles):
    res = leave_one_cell_out(cycles, "soh")
    assert set(res.per_cell) == set(cycles["cell_id"].unique())
    assert res.mae < 0.05
    d = res.to_dict()
    assert {"target", "mae", "rmse", "per_cell"} <= set(d)


def test_leave_one_cell_out_needs_two_cells():
    with pytest.raises(ValueError, match="at least two"):
        leave_one_cell_out(generate_cell("only", 20), "soh")


def test_feature_names_nonempty():
    assert "cycle" in feature_names()
