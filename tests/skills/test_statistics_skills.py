"""Tests for the statistics skill modules."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from openscience.skills import get_skill
from openscience.skills.statistics import (
    bayesian,
    curve_fitting,
    design_of_experiments,
    doe,
    dose_response,
    forest_plot,
    longitudinal,
    meta_analysis,
    model_training,
    numpy_stats,
    power_analysis,
    reporting,
)

ALL_SKILLS = [
    "numpy_stats",
    "power_analysis",
    "pyDOE2",
    "design_of_experiments",
    "curve_fitting",
    "dose_response_analysis",
    "longitudinal_analysis",
    "bayesian_inference",
    "statsmodels_meta",
    "forest_plot",
    "statistical_reporting",
    "model_training",
]


# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------


def test_all_statistics_skills_registered():
    for name in ALL_SKILLS:
        assert callable(get_skill(name)), f"skill {name!r} not registered"


def test_unknown_operation_raises():
    with pytest.raises(ValueError):
        numpy_stats.run("nope")


def test_parameters_wrapper_unwrapped():
    out = numpy_stats.run("descriptive", parameters={"data": [1, 2, 3, 4]})
    assert out["mean"] == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# numpy_stats
# ---------------------------------------------------------------------------


def test_numpy_stats_descriptive():
    out = numpy_stats.run("descriptive", data=[1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert out["status"] == "ok"
    assert out["n"] == 9
    assert out["mean"] == pytest.approx(5.0)
    assert out["std"] == pytest.approx(np.std(range(1, 10), ddof=1))
    assert out["percentiles"]["50"] == pytest.approx(5.0)
    assert out["percentiles"]["25"] == pytest.approx(3.0)
    assert out["percentiles"]["75"] == pytest.approx(7.0)


def test_numpy_stats_ttest_1samp():
    rng = np.random.default_rng(0)
    out = numpy_stats.run("ttest_1samp", data=list(rng.normal(2.0, 1.0, 100)), popmean=0.0)
    assert out["t_statistic"] > 5
    assert out["p_value"] < 0.001
    assert out["significant_at_005"] is True


def test_numpy_stats_correlation():
    x = list(range(50))
    y = list(2 * np.arange(50) + np.random.default_rng(1).normal(0, 0.1, 50))
    out = numpy_stats.run("correlation", x=x, y=y)
    assert out["r"] > 0.99
    assert out["p_value"] < 0.001
    out_s = numpy_stats.run("correlation", x=x, y=y, method="spearman")
    assert out_s["method"] == "spearman"
    assert out_s["r"] > 0.99


def test_numpy_stats_regression_slope():
    x = np.linspace(0, 10, 30)
    rng = np.random.default_rng(2)
    y = 3.0 * x + 2.0 + rng.normal(0, 0.1, 30)
    out = numpy_stats.run("regression_slope", x=x.tolist(), y=y.tolist())
    assert out["slope"] == pytest.approx(3.0, abs=0.05)
    assert out["intercept"] == pytest.approx(2.0, abs=0.1)
    assert out["r_squared"] > 0.99


# ---------------------------------------------------------------------------
# power_analysis
# ---------------------------------------------------------------------------


def test_power_sample_size_medium_effect():
    out = power_analysis.run("sample_size", effect_size=0.5, alpha=0.05, power=0.8)
    # classic textbook value: ~64 per group for d=0.5
    assert out["n_per_group"] == pytest.approx(64, abs=2)
    assert out["n_total"] >= 2 * out["n_per_group"] - 1


def test_power_ttest_power_solve():
    out = power_analysis.run("ttest_power", effect_size=0.5, nobs1=64, alpha=0.05)
    assert out["solved_for"] == "power"
    assert out["power"] == pytest.approx(0.8, abs=0.02)


def test_power_curve_is_list_of_dicts():
    out = power_analysis.run("power_curve", effect_size=0.5)
    assert isinstance(out["curve"], list) and out["curve"]
    for pt in out["curve"]:
        assert set(pt) == {"n_per_group", "power"}
        assert 0 < pt["power"] <= 1
    powers = [p["power"] for p in out["curve"]]
    assert powers == sorted(powers)  # monotonic in n


def test_power_proportion_power():
    # Cohen's h for 0.5 vs 0.7 ≈ 0.411
    h = 2 * np.arcsin(np.sqrt(0.7)) - 2 * np.arcsin(np.sqrt(0.5))
    out = power_analysis.run("proportion_power", effect_size=float(h), alpha=0.05, power=0.8)
    assert out["solved_for"] == "nobs1"
    assert out["nobs1"] == pytest.approx(93, abs=5)


# ---------------------------------------------------------------------------
# pyDOE2 (doe.py)
# ---------------------------------------------------------------------------


def test_doe_full_factorial_pure_python():
    out = doe.run("full_factorial", levels=[2, 3])
    assert out["n_runs"] == 6
    assert out["n_factors"] == 2
    assert sorted(tuple(r) for r in out["design"]) == [
        (0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2),
    ]


def test_doe_full_factorial_backend_flag():
    from openscience.skills._common import has_module

    out = doe.run("full_factorial", levels=[2, 2])
    expected = "pyDOE2" if has_module("pyDOE2") else "pure-python"
    assert out["backend"] == expected
    assert out["n_runs"] == 4


def test_doe_fractional_factorial_falls_back_to_full():
    out = doe.run("fractional_factorial", levels=[2, 2, 2])
    assert out["n_runs"] == 8  # full 2^3 as fallback
    assert "fallback" in out["design_type"] or out.get("generator")


def test_doe_design_matrix_df():
    out = doe.run("design_matrix_df", design=[[0, 1], [1, 0]], factor_names=["temp", "pH"])
    assert out["columns"] == ["temp", "pH"]
    assert out["records"] == [{"temp": 0.0, "pH": 1.0}, {"temp": 1.0, "pH": 0.0}]


# ---------------------------------------------------------------------------
# design_of_experiments
# ---------------------------------------------------------------------------


def test_design_randomize_runs_deterministic():
    design = [[0, 0], [0, 1], [1, 0], [1, 1]]
    a = design_of_experiments.run("randomize_runs", design=design, seed=42)
    b = design_of_experiments.run("randomize_runs", design=design, seed=42)
    assert a["run_order"] == b["run_order"]
    assert sorted(map(tuple, a["design"])) == sorted(map(tuple, design))


def test_design_block_design():
    design = [[i] for i in range(8)]
    out = design_of_experiments.run("block_design", design=design, n_blocks=4, seed=1)
    assert out["block_sizes"] == [2, 2, 2, 2]
    assert sorted(out["block_labels"]) == [0, 0, 1, 1, 2, 2, 3, 3]


def test_design_alias_structure_detects_confounding():
    # columns 0 and 1 perfectly correlated -> aliased; column 2 independent
    design = [[0, 0, 0], [0, 0, 1], [1, 1, 0], [1, 1, 1], [0, 0, 0], [0, 0, 1], [1, 1, 0], [1, 1, 1]]
    out = design_of_experiments.run("alias_structure", design=design)
    aliased = {(p["factor_i"], p["factor_j"]) for p in out["aliased_pairs"]}
    assert (0, 1) in aliased
    indep = [p for p in out["pairwise_correlations"] if (p["factor_i"], p["factor_j"]) == (0, 2)]
    assert abs(indep[0]["correlation"]) < 0.99


# ---------------------------------------------------------------------------
# curve_fitting
# ---------------------------------------------------------------------------


def _hill_curve(x, bottom=0.0, top=100.0, ec50=5.0, n=1.5, noise=0.0):
    y = bottom + (top - bottom) / (1 + (ec50 / x) ** n)
    if noise:
        y = y + np.random.default_rng(0).normal(0, noise, size=len(x))
    return y


def test_curve_fitting_hill_equation():
    x = np.linspace(0.1, 50, 25)
    y = _hill_curve(x)
    out = curve_fitting.run("hill_equation", x=x.tolist(), y=y.tolist())
    assert out["EC50"] == pytest.approx(5.0, abs=0.5)
    assert out["Emax"] == pytest.approx(100.0, abs=2.0)
    assert out["r_squared"] > 0.99


def test_curve_fitting_four_pl():
    x = np.linspace(0.1, 50, 25)
    y = _hill_curve(x)  # Hill == 4PL reparameterized
    out = curve_fitting.run("four_pl", x=x.tolist(), y=y.tolist())
    assert out["EC50"] == pytest.approx(5.0, abs=1.0)
    assert out["r_squared"] > 0.98


def test_curve_fitting_linear_fit_and_goodness():
    x = np.arange(10, dtype=float)
    y = 2 * x + 1
    out = curve_fitting.run("linear_fit", x=x.tolist(), y=y.tolist())
    assert out["slope"] == pytest.approx(2.0)
    assert out["r_squared"] == pytest.approx(1.0)
    g = curve_fitting.run("goodness", y=y.tolist(), yhat=y.tolist())
    assert g["r_squared"] == pytest.approx(1.0)
    assert g["rmse"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# dose_response_analysis
# ---------------------------------------------------------------------------


def test_drc_fit_returns_ic50():
    dose = [0.01, 0.1, 1, 10, 100]
    resp = _hill_curve(np.array(dose), bottom=5, top=100, ec50=10, n=1.0)
    out = dose_response.run("fit_drc", dose=dose, response=resp.tolist())
    assert out["IC50"] == pytest.approx(10.0, abs=2.0)
    assert out["r_squared"] > 0.95


def test_drc_ic50_interpolation_fallback():
    # perfectly monotone decreasing data
    dose = [1, 10, 100]
    resp = [90.0, 50.0, 10.0]
    out = dose_response.run("ic50", dose=dose, response=resp)
    assert 5.0 < out["IC50"] < 15.0


def test_drc_summarize_table_per_compound():
    rng = np.random.default_rng(3)
    records = []
    for comp, ec in [("A", 5.0), ("B", 20.0)]:
        doses = np.array([0.1, 1, 10, 100])
        resp = _hill_curve(doses, bottom=0, top=100, ec50=ec, n=1.2, noise=0.5)
        for d, r in zip(doses, resp):
            records.append({"compound": comp, "dose": float(d), "response": float(r)})
    out = dose_response.run("summarize_table", records=records)
    assert out["n_compounds"] == 2
    by_comp = {c["compound"]: c for c in out["compounds"]}
    assert by_comp["A"]["IC50"] == pytest.approx(5.0, abs=2.0)
    assert by_comp["B"]["IC50"] == pytest.approx(20.0, abs=5.0)
    assert all(c["fit_ok"] for c in out["compounds"])


# ---------------------------------------------------------------------------
# longitudinal_analysis
# ---------------------------------------------------------------------------


def _longitudinal_data():
    rng = np.random.default_rng(5)
    records = []
    for subj in range(12):
        grp = "trt" if subj < 6 else "ctrl"
        base = rng.normal(10, 1)
        for t in [0, 1, 2, 3]:
            y = base + (2.0 if grp == "trt" else 0.5) * t + rng.normal(0, 0.3)
            records.append({"subject": f"s{subj}", "time": t, "y": y, "group": grp})
    return records


def test_longitudinal_lmm():
    out = longitudinal.run("lmm", records=_longitudinal_data())
    assert out["formula"] == "y ~ time + group"
    assert out["n_obs"] == 48
    assert out["converged"] is True
    time_eff = out["fixed_effects"]["time"]
    assert "coef" in time_eff and "p_value" in time_eff


def test_longitudinal_auc_and_slope():
    subject = ["s1"] * 4 + ["s2"] * 4
    time = [0, 1, 2, 3] * 2
    y = [0, 1, 2, 3, 0, 2, 4, 6]  # s1 slope 1, s2 slope 2
    auc = longitudinal.run("auc_per_subject", subject=subject, time=time, y=y)
    assert auc["auc_per_subject"]["s1"] == pytest.approx(4.5)
    assert auc["auc_per_subject"]["s2"] == pytest.approx(9.0)
    slope = longitudinal.run("slope_per_subject", subject=subject, time=time, y=y)
    assert slope["slope_per_subject"]["s1"] == pytest.approx(1.0)
    assert slope["slope_per_subject"]["s2"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# bayesian_inference
# ---------------------------------------------------------------------------


def test_bayesian_beta_binomial():
    out = bayesian.run("beta_binomial", successes=8, failures=2, alpha_prior=1, beta_prior=1)
    assert out["posterior_alpha"] == 9.0
    assert out["posterior_beta"] == 3.0
    assert out["posterior_mean"] == pytest.approx(9 / 12)
    assert out["hdpi_lower"] < out["posterior_mean"] < out["hdpi_upper"]
    assert 0 <= out["hdpi_lower"] and out["hdpi_upper"] <= 1


def test_bayesian_normal_normal():
    out = bayesian.run("normal_normal", data_mean=5.0, data_sd=2.0, n=10,
                       prior_mean=0.0, prior_sd=10.0)
    # posterior pulled strongly toward data mean
    assert out["posterior_mean"] == pytest.approx(5.0, abs=0.1)
    assert out["posterior_sd"] < 2.0 / np.sqrt(10) + 0.01
    assert out["hdpi_lower"] < out["posterior_mean"] < out["hdpi_upper"]


def test_bayesian_summary_from_beta():
    out = bayesian.run("summary", alpha=9, beta=3, threshold=0.5)
    assert out["posterior_mean"] == pytest.approx(0.75)
    assert out["p_greater_than_threshold"] > 0.9
    assert out["hdpi_lower"] < out["hdpi_upper"]


# ---------------------------------------------------------------------------
# statsmodels_meta
# ---------------------------------------------------------------------------

META_ES = [0.5, 0.6, 0.4, 0.55]
META_SE = [0.1, 0.15, 0.12, 0.11]


def test_meta_fixed_effect():
    out = meta_analysis.run("fixed_effect", effect_sizes=META_ES, standard_errors=META_SE)
    # inverse-variance pooled estimate ~0.51
    assert out["pooled_effect"] == pytest.approx(0.52, abs=0.02)
    assert out["ci_lower"] < out["pooled_effect"] < out["ci_upper"]
    assert out["n_studies"] == 4


def test_meta_random_effects_dl():
    out = meta_analysis.run("random_effects", effect_sizes=META_ES, standard_errors=META_SE)
    assert out["model"] == "random_effects_dersimonian_laird"
    assert out["tau2"] >= 0.0
    assert 0.0 <= out["I2"] <= 1.0
    # RE CIs are at least as wide as FE CIs
    fe = meta_analysis.run("fixed_effect", effect_sizes=META_ES, standard_errors=META_SE)
    assert (out["ci_upper"] - out["ci_lower"]) >= (fe["ci_upper"] - fe["ci_lower"]) - 1e-9


def test_meta_heterogeneity():
    out = meta_analysis.run("heterogeneity", effect_sizes=META_ES, standard_errors=META_SE)
    assert out["Q_df"] == 3
    assert 0.0 <= out["I2"] <= 1.0
    assert out["Q"] >= 0.0


def test_meta_forest_data_structure():
    out = meta_analysis.run("forest_data", effect_sizes=META_ES, standard_errors=META_SE,
                            study_labels=["s1", "s2", "s3", "s4"])
    assert len(out["studies"]) == 4
    assert out["studies"][0]["label"] == "s1"
    assert out["studies"][0]["ci_lower"] < out["studies"][0]["effect"] < out["studies"][0]["ci_upper"]
    assert out["pooled"]["label"].startswith("Pooled")


# ---------------------------------------------------------------------------
# forest_plot
# ---------------------------------------------------------------------------


def test_forest_plot_draw_png(tmp_path: Path):
    data = meta_analysis.run("forest_data", effect_sizes=META_ES, standard_errors=META_SE)
    out = forest_plot.run("draw", studies=data["studies"], pooled=data["pooled"],
                          path=str(tmp_path / "forest.png"))
    p = Path(out["path"])
    assert p.exists() and p.stat().st_size > 0
    assert out["format"] == "png"


def test_forest_plot_save_svg(tmp_path: Path):
    data = meta_analysis.run("forest_data", effect_sizes=META_ES, standard_errors=META_SE)
    out = forest_plot.run("save_svg", studies=data["studies"], pooled=data["pooled"],
                          path=str(tmp_path / "forest"))
    assert Path(out["path"]).suffix == ".svg"
    assert Path(out["path"]).exists()


def test_forest_plot_from_meta(tmp_path: Path):
    meta = meta_analysis.run("forest_data", effect_sizes=META_ES, standard_errors=META_SE)
    out = forest_plot.run("from_meta", meta=meta, path=str(tmp_path / "fp.png"))
    assert Path(out["path"]).exists()
    assert out["n_studies"] == 4


# ---------------------------------------------------------------------------
# statistical_reporting
# ---------------------------------------------------------------------------


def test_reporting_apa_ttest_from_values():
    out = reporting.run("apa_ttest", t_statistic=2.3, df=18, p_value=0.034, cohens_d=1.05)
    assert out["apa"] == "t(18) = 2.30, p = .034, d = 1.05"


def test_reporting_apa_ttest_from_arrays():
    rng = np.random.default_rng(7)
    g1 = list(rng.normal(0, 1, 30))
    g2 = list(rng.normal(1, 1, 30))
    out = reporting.run("apa_ttest", group1=g1, group2=g2)
    assert out["apa"].startswith("t(")
    assert ", p " in out["apa"] and "d = " in out["apa"]


def test_reporting_apa_anova():
    rng = np.random.default_rng(8)
    groups = [list(rng.normal(0, 1, 20)), list(rng.normal(0.3, 1, 20)), list(rng.normal(0.8, 1, 20))]
    out = reporting.run("apa_anova", groups=groups)
    assert out["apa"].startswith("F(2, 57)")
    assert "eta2 = " in out["apa"]


def test_reporting_p_to_stars():
    assert reporting.run("p_to_stars", p_value=0.0005)["stars"] == "***"
    assert reporting.run("p_to_stars", p_value=0.005)["stars"] == "**"
    assert reporting.run("p_to_stars", p_value=0.03)["stars"] == "*"
    assert reporting.run("p_to_stars", p_value=0.2)["stars"] == "ns"


def test_reporting_effect_size_label():
    assert reporting.run("effect_size_label", d=0.1)["magnitude"] == "negligible"
    assert reporting.run("effect_size_label", d=0.25)["magnitude"] == "small"
    assert reporting.run("effect_size_label", d=0.6)["magnitude"] == "medium"
    assert reporting.run("effect_size_label", d=0.9)["magnitude"] == "large"
    assert reporting.run("effect_size_label", d=0.4, metric="r")["magnitude"] == "medium"


# ---------------------------------------------------------------------------
# model_training
# ---------------------------------------------------------------------------


def _classification_data():
    rng = np.random.default_rng(11)
    X0 = rng.normal(0, 0.8, (40, 3))
    X1 = rng.normal(2, 0.8, (40, 3))
    X = np.vstack([X0, X1])
    y = np.array([0] * 40 + [1] * 40)
    return X, y


def test_model_training_classifier():
    X, y = _classification_data()
    out = model_training.run("train_classifier", X=X.tolist(), y=y.tolist(),
                             model_type="logistic", cv=5)
    assert out["task"] == "classification"
    assert out["model"] == "logistic_regression"
    assert out["cv_mean"] > 0.9
    assert len(out["cv_scores"]) == 5
    assert out["feature_importance"] is not None


def test_model_training_rf_classifier_and_importance():
    X, y = _classification_data()
    out = model_training.run("train_classifier", X=X.tolist(), y=y.tolist(), model_type="rf",
                             feature_names=["a", "b", "c"])
    assert out["model"] == "random_forest"
    assert out["cv_mean"] > 0.9
    names = [f["feature"] for f in out["feature_importance"]]
    assert sorted(names) == ["a", "b", "c"]


def test_model_training_regressor():
    rng = np.random.default_rng(12)
    X = rng.normal(0, 1, (80, 2))
    y = 3 * X[:, 0] - X[:, 1] + rng.normal(0, 0.1, 80)
    out = model_training.run("train_regressor", X=X.tolist(), y=y.tolist(), model_type="linear")
    assert out["model"] == "linear_regression"
    assert out["cv_mean"] > 0.95  # R^2
    out_rf = model_training.run("train_regressor", X=X.tolist(), y=y.tolist(), model_type="rf")
    assert out_rf["train_r2"] > 0.8


def test_model_training_feature_importance_wrappers():
    X, y = _classification_data()
    out = model_training.run("feature_importance", X=X.tolist(), y=y.tolist(), model_type="rf",
                             feature_names=["a", "b", "c"])
    assert out["task"] == "classification"
    fracs = [f["importance_fraction"] for f in out["feature_importance"]]
    assert sum(fracs) == pytest.approx(1.0)
