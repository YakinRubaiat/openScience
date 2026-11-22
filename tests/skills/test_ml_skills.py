"""Tests for openscience.skills.ml skills."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# Force registration of the ml skill modules.
from openscience.skills import get_skill, list_skills
from openscience.skills import load_default_skills

load_default_skills()


SKILL_NAMES = [
    "image_analysis",
    "cellprofiler_output",
    "flow_gating",
    "survival_ml",
    "multimodal_integration",
    "feature_selection",
    "dimensionality_reduction",
    "cross_validation",
    "metrics_ext",
    "calibration",
    "forecasting",
]


@pytest.mark.parametrize("name", SKILL_NAMES)
def test_skill_registered(name):
    assert name in list_skills()
    assert callable(get_skill(name))


def run_skill(name, operation, **kwargs):
    fn = get_skill(name)
    assert fn is not None
    return fn(operation=operation, **kwargs)


# ---------------------------------------------------------------------------
# image_analysis
# ---------------------------------------------------------------------------


def _simple_blobs(n=5, size=64):
    img = np.zeros((size, size), dtype=float)
    rng = np.random.default_rng(0)
    for _ in range(n):
        r = rng.integers(5, size - 10)
        c = rng.integers(5, size - 10)
        img[r : r + 5, c : c + 5] = 1.0
    return img


def test_image_analysis_threshold_otsu_numpy():
    img = _simple_blobs()
    out = run_skill("image_analysis", "threshold_otsu", parameters={"array": img.tolist()})
    assert 0.0 <= out["threshold"] <= 1.0
    assert out["foreground_fraction"] > 0


def test_image_analysis_count_objects():
    img = _simple_blobs(n=4)
    mask = (img > 0.5)
    out = run_skill("image_analysis", "count_objects", parameters={"mask": mask.tolist()})
    assert out["n_objects"] == 4
    assert "labels" in out


def test_image_analysis_intensity_summary():
    img = np.zeros((10, 10), dtype=float)
    img[:5, :] = 10.0
    img[5:, :] = 20.0
    labels = np.zeros((10, 10), dtype=int)
    labels[:5, :] = 1
    labels[5:, :] = 2
    out = run_skill(
        "image_analysis",
        "intensity_summary",
        parameters={"array": img.tolist(), "labels": labels.tolist()},
    )
    assert out["n_regions"] == 2
    assert out["regions"]["1"]["mean"] == pytest.approx(10.0)
    assert out["regions"]["2"]["mean"] == pytest.approx(20.0)


def test_image_analysis_load_tiff(tmp_path):
    pytest.importorskip("tifffile")
    import tifffile

    img = (np.arange(64).reshape(8, 8)).astype(np.uint16)
    path = tmp_path / "test.tif"
    tifffile.imwrite(str(path), img)
    out = run_skill("image_analysis", "load_tiff", parameters={"path": str(path)})
    assert out["shape"] == [8, 8]
    assert out["max"] == pytest.approx(63.0)


def test_image_analysis_load_tiff_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_skill("image_analysis", "load_tiff", parameters={"path": str(tmp_path / "no.tif")})


# ---------------------------------------------------------------------------
# cellprofiler_output
# ---------------------------------------------------------------------------


def _cp_df(n=10):
    rng = np.random.default_rng(1)
    return pd.DataFrame(
        {
            "ImageNumber": [1, 1, 1, 2, 2, 2, 2, 3, 3, 3][:n],
            "ObjectNumber": list(range(1, n + 1)),
            "AreaShape_Center_X": rng.uniform(0, 100, n),
            "AreaShape_Center_Y": rng.uniform(0, 100, n),
            "AreaShape_Area": rng.uniform(10, 100, n),
            "Intensity_Mean": rng.uniform(0, 1, n),
        }
    )


def test_cp_read_objects_csv(tmp_path):
    df = _cp_df()
    path = tmp_path / "objects.csv"
    df.to_csv(path, index=False)
    out = run_skill("cellprofiler_output", "read_objects_csv", parameters={"path": str(path)})
    assert out["n_rows"] == len(df)
    assert "AreaShape_Area" in out["columns"]


def test_cp_per_image_aggregates():
    df = _cp_df()
    out = run_skill(
        "cellprofiler_output",
        "per_image_aggregates",
        parameters={"dataframe": df.to_dict(orient="list")},
    )
    assert set(out["per_image"].keys()) == {"1", "2", "3"}
    assert out["per_image"]["1"]["n_objects"] == 3
    assert "AreaShape_Area" in out["per_image"]["1"]


def test_cp_filter_border_cells():
    df = pd.DataFrame(
        {
            "ImageNumber": [1] * 4,
            "ObjectNumber": [1, 2, 3, 4],
            "AreaShape_Center_X": [0.5, 50.0, 99.5, 50.0],
            "AreaShape_Center_Y": [50.0, 50.0, 50.0, 0.5],
            "AreaShape_Area": [10, 10, 10, 10],
        }
    )
    out = run_skill(
        "cellprofiler_output",
        "filter_border_cells",
        parameters={"dataframe": df.to_dict(orient="list"), "width": 100, "height": 100, "margin": 1},
    )
    assert out["n_input"] == 4
    assert out["n_kept"] == 1
    assert out["n_removed"] == 3


# ---------------------------------------------------------------------------
# flow_gating
# ---------------------------------------------------------------------------


def _flow_df(n=100):
    rng = np.random.default_rng(2)
    return pd.DataFrame(
        {
            "FSC": rng.normal(100, 10, n),
            "SSC": rng.normal(50, 5, n),
            "CD3": rng.normal(10, 2, n),
            "CD4": rng.normal(5, 1, n),
        }
    )


def test_flow_rectangle_gate():
    df = _flow_df()
    out = run_skill(
        "flow_gating",
        "rectangle_gate",
        parameters={
            "dataframe": df.to_dict(orient="list"),
            "gates": {"FSC": {"min": 90, "max": 110}},
        },
    )
    assert out["n_input"] == len(df)
    assert 0 < out["n_kept"] < len(df)
    for rec in out["records"]:
        assert 90 <= rec["FSC"] <= 110


def test_flow_percentage_positive():
    df = pd.DataFrame({"CD3": [0.1, 5.0, 20.0, 30.0], "CD4": [1, 2, 3, 4]})
    out = run_skill(
        "flow_gating",
        "percentage_positive",
        parameters={"dataframe": df.to_dict(orient="list"), "thresholds": {"CD3": 10.0}},
    )
    res = out["channels"]["CD3"]
    assert res["n_positive"] == 2
    assert res["pct_positive"] == pytest.approx(50.0)


def test_flow_gate_tree_apply():
    df = _flow_df()
    out = run_skill(
        "flow_gating",
        "gate_tree_apply",
        parameters={
            "dataframe": df.to_dict(orient="list"),
            "gates": [
                {"name": "singlets", "type": "rectangle", "channel": "FSC", "min": 80, "max": 120},
                {"name": "cd3_pos", "type": "threshold", "channel": "CD3", "threshold": 10, "direction": "above"},
            ],
        },
    )
    assert out["n_start"] == len(df)
    assert len(out["steps"]) == 2
    assert out["steps"][0]["name"] == "singlets"
    assert out["steps"][1]["fraction_of_total"] <= out["steps"][0]["fraction_of_total"]


# ---------------------------------------------------------------------------
# survival_ml
# ---------------------------------------------------------------------------


def _surv_df(n=40):
    rng = np.random.default_rng(3)
    x1 = rng.normal(0, 1, n)
    t = rng.uniform(1, 20, n) + x1 * 5
    e = rng.binomial(1, 0.7, n)
    return pd.DataFrame({"duration": t, "event": e, "x1": x1})


def test_cox_cv_score():
    df = _surv_df()
    out = run_skill(
        "survival_ml",
        "cox_cv_score",
        parameters={
            "dataframe": df.to_dict(orient="list"),
            "duration_col": "duration",
            "event_col": "event",
            "n_splits": 3,
        },
    )
    assert out["n_splits"] == 3
    assert len(out["fold_scores"]) == 3
    assert out["mean_concordance"] is None or 0.0 <= out["mean_concordance"] <= 1.0


def test_km_auc_at_time():
    rng = np.random.default_rng(4)
    durations = rng.uniform(1, 30, 30)
    events = rng.binomial(1, 0.7, 30)
    groups = np.array(["a"] * 15 + ["b"] * 15)
    out = run_skill(
        "survival_ml",
        "km_auc_at_time",
        parameters={"durations": durations.tolist(), "events": events.tolist(), "groups": groups.tolist(), "time": 20.0},
    )
    assert set(out["groups"].keys()) == {"a", "b"}
    for g in ("a", "b"):
        assert 0 <= out["groups"][g]["auc"] <= 20.0


def test_risk_groups_significant():
    rng = np.random.default_rng(5)
    n = 60
    risk = np.concatenate([rng.normal(0, 0.5, n // 2), rng.normal(2, 0.5, n // 2)])
    durations = 30.0 - risk * 5 + rng.normal(0, 1, n)
    durations = np.clip(durations, 0.5, None)
    events = np.ones(n, dtype=int)
    out = run_skill(
        "survival_ml",
        "risk_groups",
        parameters={
            "durations": durations.tolist(),
            "events": events.tolist(),
            "risk_scores": risk.tolist(),
        },
    )
    assert out["n_high"] == 30
    assert out["n_low"] == 30
    assert out["logrank"]["p_value"] < 0.05


# ---------------------------------------------------------------------------
# multimodal_integration
# ---------------------------------------------------------------------------


def _modalities():
    rng = np.random.default_rng(6)
    idx = pd.Index([f"s{i}" for i in range(20)], name="sample")
    rna = pd.DataFrame({"g1": rng.normal(size=20), "g2": rng.normal(size=20)}, index=idx)
    protein = pd.DataFrame(
        {"p1": 2 * rng.normal(size=20), "p2": rng.normal(size=20)}, index=idx
    )
    return rna, protein


def test_late_fusion_concat():
    rna, protein = _modalities()
    out = run_skill(
        "multimodal_integration",
        "late_fusion_concat",
        parameters={
            "modalities": {"rna": rna.to_dict(orient="list"), "protein": protein.to_dict(orient="list")}
        },
    )
    assert out["n_samples"] == 20
    assert set(out["columns"]) == {"rna__g1", "rna__g2", "protein__p1", "protein__p2"}


def test_early_fusion_pca():
    rna, protein = _modalities()
    out = run_skill(
        "multimodal_integration",
        "early_fusion_pca",
        parameters={
            "modalities": {"rna": rna.to_dict(orient="list"), "protein": protein.to_dict(orient="list")},
            "n_components": 2,
        },
    )
    assert out["n_components"] == 2
    assert len(out["scores"]) == 20
    assert len(out["scores"][0]) == 2
    assert abs(sum(out["explained_variance_ratio"]) - 1.0) < 1e-6 or sum(out["explained_variance_ratio"]) <= 1.0 + 1e-6


def test_correlation_between_modalities():
    rng = np.random.default_rng(7)
    idx = pd.Index([f"s{i}" for i in range(30)], name="sample")
    base = rng.normal(size=30)
    a = pd.DataFrame({"a1": base, "a2": rng.normal(size=30)}, index=idx)
    b = pd.DataFrame({"a1": base * 2, "a2": rng.normal(size=30)}, index=idx)
    out = run_skill(
        "multimodal_integration",
        "correlation_between_modalities",
        parameters={"df_a": a.to_dict(orient="list"), "df_b": b.to_dict(orient="list")},
    )
    pair = [p for p in out["pairs"] if p["feature_a"] == "a1" and p["feature_b"] == "a1"][0]
    assert pair["r"] == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# feature_selection
# ---------------------------------------------------------------------------


def _features(n=60):
    rng = np.random.default_rng(8)
    x1 = rng.normal(size=n)
    x2 = x1 * 0.5 + rng.normal(scale=0.5, size=n)
    x3 = rng.normal(size=n)
    y = (x1 > 0).astype(int)
    df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "target": y})
    return df


def test_variance_filter():
    rng = np.random.default_rng(9)
    df = pd.DataFrame(
        {
            "flat": np.full(50, 1.0),
            "varied": rng.normal(size=50),
        }
    )
    out = run_skill(
        "feature_selection",
        "variance_filter",
        parameters={"dataframe": df.to_dict(orient="list"), "threshold": 0.01},
    )
    assert out["kept_features"] == ["varied"]
    assert out["dropped_features"] == ["flat"]


def test_univariate_anova():
    df = _features()
    out = run_skill(
        "feature_selection",
        "univariate_anova",
        parameters={"dataframe": df.to_dict(orient="list"), "target_col": "target", "k": 2},
    )
    assert len(out["kept_features"]) == 2
    assert "x1" in out["kept_features"]


def test_rfe():
    df = _features()
    out = run_skill(
        "feature_selection",
        "rfe",
        parameters={
            "dataframe": df.to_dict(orient="list"),
            "target_col": "target",
            "cv": 3,
            "min_features": 1,
        },
    )
    assert out["n_selected"] >= 1
    assert "x1" in out["selected_features"]


def test_correlate_with_target():
    rng = np.random.default_rng(10)
    x = rng.normal(size=40)
    noise = rng.normal(scale=0.01, size=40)
    df = pd.DataFrame({"sig": x, "noise": noise, "target": x + noise})
    out = run_skill(
        "feature_selection",
        "correlate_with_target",
        parameters={"dataframe": df.to_dict(orient="list"), "target_col": "target"},
    )
    sig = [c for c in out["correlations"] if c["feature"] == "sig"][0]
    assert sig["r"] == pytest.approx(1.0, abs=0.05)


# ---------------------------------------------------------------------------
# dimensionality_reduction
# ---------------------------------------------------------------------------


def _matrix(n=40):
    rng = np.random.default_rng(11)
    return rng.normal(size=(n, 5))


def test_pca():
    X = _matrix()
    out = run_skill("dimensionality_reduction", "pca", parameters={"array": X.tolist(), "n_components": 3})
    assert out["n_components"] == 3
    assert len(out["scores"]) == X.shape[0]
    assert len(out["scores"][0]) == 3
    evr = out["explained_variance_ratio"]
    assert all(v >= 0 for v in evr)
    assert 0.0 < sum(evr) <= 1.0 + 1e-6
    assert out["cumulative_explained_variance"][-1] == pytest.approx(sum(evr))


def test_tsne_small_guard():
    X = _matrix(n=10)
    out = run_skill(
        "dimensionality_reduction",
        "tsne",
        parameters={"array": X.tolist(), "n_components": 2, "perplexity": 30},
    )
    assert out["n_samples"] == 10
    # perplexity should be clamped below (n-1)/3
    assert out["perplexity"] <= (10 - 1) / 3.0 + 1e-6
    assert len(out["embedding"]) == 10


def test_tsne_too_small():
    X = [[0.0, 1.0], [1.0, 0.0]]
    with pytest.raises(ValueError):
        run_skill("dimensionality_reduction", "tsne", parameters={"array": X})


def test_umap_graceful():
    X = _matrix(n=15)
    from openscience.skills._common import has_module

    if has_module("umap"):
        out = run_skill(
            "dimensionality_reduction",
            "umap",
            parameters={"array": X.tolist(), "n_components": 2, "n_neighbors": 5},
        )
        assert len(out["embedding"]) == 15
    else:
        with pytest.raises(RuntimeError, match="umap"):
            run_skill("dimensionality_reduction", "umap", parameters={"array": X.tolist()})


def test_knn_graph():
    X = _matrix(n=20)
    out = run_skill("dimensionality_reduction", "knn_graph", parameters={"array": X.tolist(), "k": 3})
    assert out["k"] == 3
    assert len(out["indices"]) == 20
    assert all(len(row) == 3 for row in out["indices"])


# ---------------------------------------------------------------------------
# cross_validation
# ---------------------------------------------------------------------------


def test_kfold_indices():
    out = run_skill("cross_validation", "kfold_indices", parameters={"n_samples": 20, "n_splits": 4})
    assert out["n_splits"] == 4
    assert len(out["folds"]) == 4
    all_test = sorted(i for f in out["folds"] for i in f["test"])
    assert all_test == list(range(20))


def test_stratified_kfold_indices():
    y = [0] * 20 + [1] * 20
    out = run_skill(
        "cross_validation",
        "stratified_kfold_indices",
        parameters={"y": y, "n_splits": 4},
    )
    assert out["n_splits"] == 4
    for fold in out["folds"]:
        test_labels = [y[i] for i in fold["test"]]
        assert test_labels.count(0) >= 4
        assert test_labels.count(1) >= 4


def test_repeated_scores():
    rng = np.random.default_rng(12)
    x1 = rng.normal(size=80)
    X = np.column_stack([x1, rng.normal(size=80)])
    y = (x1 > 0).astype(int)
    out = run_skill(
        "cross_validation",
        "repeated_scores",
        parameters={"X": X.tolist(), "y": y.tolist(), "n_splits": 4, "metric": "accuracy"},
    )
    assert out["metric"] == "accuracy"
    assert len(out["fold_scores"]) == 4
    assert 0.0 <= out["mean_score"] <= 1.0


def test_holdout_split():
    out = run_skill(
        "cross_validation",
        "holdout_split",
        parameters={"n_samples": 40, "test_size": 0.25},
    )
    assert out["n_train"] + out["n_test"] == 40
    assert out["n_test"] == 10


# ---------------------------------------------------------------------------
# metrics_ext
# ---------------------------------------------------------------------------


def test_classification_report():
    y_true = [0, 0, 1, 1, 1, 0]
    y_pred = [0, 1, 1, 1, 0, 0]
    out = run_skill(
        "metrics_ext",
        "classification_report",
        parameters={"y_true": y_true, "y_pred": y_pred},
    )
    assert out["n"] == 6
    assert out["accuracy"] == pytest.approx(4 / 6)
    assert set(out["labels"]) == {"0", "1"}
    assert out["confusion_matrix"] == [[2, 1], [1, 2]]


def test_regression_report():
    y_true = [1.0, 2.0, 3.0, 4.0]
    y_pred = [1.1, 1.9, 3.2, 3.8]
    out = run_skill(
        "metrics_ext",
        "regression_report",
        parameters={"y_true": y_true, "y_pred": y_pred},
    )
    assert out["n"] == 4
    assert out["mae"] == pytest.approx(0.15)
    assert out["rmse"] == pytest.approx(np.sqrt(np.mean([0.01, 0.01, 0.04, 0.04])))
    assert out["r2"] is not None and 0 <= out["r2"] <= 1


def test_regression_report_mape_guard():
    y_true = [0.0, 0.0, 0.0]
    y_pred = [0.1, 0.2, 0.3]
    out = run_skill(
        "metrics_ext",
        "regression_report",
        parameters={"y_true": y_true, "y_pred": y_pred},
    )
    assert out["mape_percent"] is None
    assert out["n_mape_samples"] == 0


def test_roc_auc_curve_points_perfect():
    y_true = [0, 0, 1, 1]
    y_score = [0.1, 0.2, 0.8, 0.9]
    out = run_skill(
        "metrics_ext",
        "roc_auc_curve_points",
        parameters={"y_true": y_true, "y_score": y_score},
    )
    assert out["auc"] == pytest.approx(1.0)
    assert out["n_positive"] == 2
    assert out["n_negative"] == 2


def test_roc_auc_curve_points_random():
    y_true = [0, 0, 1, 1]
    y_score = [0.4, 0.6, 0.4, 0.6]
    out = run_skill(
        "metrics_ext",
        "roc_auc_curve_points",
        parameters={"y_true": y_true, "y_score": y_score},
    )
    assert 0.0 <= out["auc"] <= 1.0


# ---------------------------------------------------------------------------
# calibration
# ---------------------------------------------------------------------------


def test_reliability_bins():
    probs = [0.05, 0.15, 0.25, 0.55, 0.85, 0.95]
    truth = [0, 0, 0, 1, 1, 1]
    out = run_skill(
        "calibration",
        "reliability_bins",
        parameters={"probabilities": probs, "y_true": truth, "n_bins": 10},
    )
    assert out["n_bins"] == 10
    assert len(out["bins"]) == 10
    nonempty = [b for b in out["bins"] if b["n"] > 0]
    assert len(nonempty) == 6


def test_ece_perfect():
    probs = [0.0, 0.0, 1.0, 1.0]
    truth = [0, 0, 1, 1]
    out = run_skill(
        "calibration",
        "ece",
        parameters={"probabilities": probs, "y_true": truth},
    )
    assert out["ece"] == pytest.approx(0.0)


def test_ece_miscalibrated():
    probs = [0.1, 0.1, 0.9, 0.9]
    truth = [1, 1, 0, 0]
    out = run_skill(
        "calibration",
        "ece",
        parameters={"probabilities": probs, "y_true": truth},
    )
    assert out["ece"] > 0


def test_brier_perfect():
    probs = [0.0, 0.0, 1.0, 1.0]
    truth = [0, 0, 1, 1]
    out = run_skill(
        "calibration",
        "brier",
        parameters={"probabilities": probs, "y_true": truth},
    )
    assert out["brier_score"] == pytest.approx(0.0)
    assert out["brier_skill_score"] == pytest.approx(1.0)


def test_brier_miscalibrated():
    probs = [0.5] * 4
    truth = [0, 0, 1, 1]
    out = run_skill(
        "calibration",
        "brier",
        parameters={"probabilities": probs, "y_true": truth},
    )
    assert out["brier_score"] == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# forecasting
# ---------------------------------------------------------------------------


def test_naive_forecast():
    out = run_skill(
        "forecasting",
        "naive_forecast",
        parameters={"series": [1.0, 2.0, 3.0, 4.0], "horizon": 3},
    )
    assert out["forecast"] == [4.0, 4.0, 4.0]


def test_naive_forecast_seasonal():
    out = run_skill(
        "forecasting",
        "naive_forecast",
        parameters={"series": [1.0, 2.0, 3.0, 1.5, 2.5, 3.5], "horizon": 5, "season_length": 3},
    )
    assert out["forecast"] == pytest.approx([1.5, 2.5, 3.5, 1.5, 2.5])


def test_moving_average_forecast():
    out = run_skill(
        "forecasting",
        "moving_average_forecast",
        parameters={"series": [1.0, 2.0, 3.0, 4.0], "horizon": 2, "window": 2},
    )
    assert out["forecast"] == pytest.approx([3.5, 3.5])


def test_linear_trend_forecast():
    out = run_skill(
        "forecasting",
        "linear_trend_forecast",
        parameters={"series": [1.0, 2.0, 3.0, 4.0], "horizon": 3},
    )
    assert out["forecast"] == pytest.approx([5.0, 6.0, 7.0], abs=1e-6)
    assert out["slope"] == pytest.approx(1.0, abs=1e-6)


def test_forecast_metrics():
    out = run_skill(
        "forecasting",
        "forecast_metrics",
        parameters={"y_true": [1.0, 2.0, 3.0], "y_pred": [1.0, 2.0, 3.0]},
    )
    assert out["mae"] == pytest.approx(0.0)
    assert out["rmse"] == pytest.approx(0.0)


def test_forecast_metrics_mape_guard():
    out = run_skill(
        "forecasting",
        "forecast_metrics",
        parameters={"y_true": [0.0, 1.0], "y_pred": [0.5, 1.5]},
    )
    assert out["mape_percent"] is not None


def test_skill_run_unknown_operation():
    with pytest.raises(ValueError):
        run_skill("metrics_ext", "does_not_exist")
