"""Step 2: train a solubility regressor through the openScience agent pattern.

Invokes the orchestrator-backed ml_modeler pipeline:
  1. Compute Morgan fingerprints for all ESOL molecules via the RDKit skill.
  2. Split train/test.
  3. Fit several regressors (RF, GradientBoosting, Ridge) on descriptors+fingerprints.
  4. Evaluate R^2, RMSE, MAE on held-out test.
  5. Pick best model and percentile-rank predictions for solubility triage.

Saves:
  - models/solubility_best.pkl
  - models/all_models_metrics.json
  - figures/predicted_vs_observed.png
  - figures/feature_importance.png
"""

from __future__ import annotations

import csv
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor  # noqa: E402
from sklearn.linear_model import Ridge  # noqa: E402
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from openscience.core.rdkit_orchestrator import RDKitOrchestrator  # noqa: E402
from openscience.skills.cheminformatics.rdkit_skill import batch_fingerprints  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE.parent / "data"
FIG_DIR = HERE.parent / "figures"
MODEL_DIR = HERE.parent / "models"
FIG_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def load_esol_with_descriptors():
    with (DATA_DIR / "descriptors_esol.csv").open() as fh:
        return list(csv.DictReader(fh))


DESCRIPTOR_FEATURES = [
    "mw",
    "logp",
    "mr",
    "hbd",
    "hba",
    "tpsa",
    "rotatable_bonds",
    "aromatic_rings",
    "ring_count",
    "fraction_csp3",
    "heavy_atom_count",
    "formal_charge",
    "qed",
]


def main() -> None:
    orch = RDKitOrchestrator()  # validates orchestrator pattern works
    assert orch.execute_skill("rdkit", "validate", smiles="CCO")["valid"]

    rows = load_esol_with_descriptors()
    print(f"Loaded {len(rows)} ESOL rows with descriptors")

    smiles_list = [r["canonical_smiles"] for r in rows]
    smiles_valid, fps = batch_fingerprints(smiles_list, radius=2, n_bits=2048)
    print(f"Fingerprint matrix: {fps.shape}")

    # Keep rows aligned with fingerprint matrix
    valid_set = set(smiles_valid)
    rows = [r for r in rows if r["canonical_smiles"] in valid_set]

    desc_feats = np.array([[float(r[k]) for k in DESCRIPTOR_FEATURES] for r in rows])
    y = np.array([float(r["measured_logS"]) for r in rows])

    # Two feature sets; we keep only "descriptors" and "fingerprints" paths

    # Single index-based split so both feature spaces see the same train/test rows
    idx = np.arange(len(y))
    tr_idx, te_idx = train_test_split(idx, test_size=0.2, random_state=42)

    Xd_train, Xd_test = desc_feats[tr_idx], desc_feats[te_idx]
    Xf_train, Xf_test = fps[tr_idx], fps[te_idx]
    y_train, y_test = y[tr_idx], y[te_idx]

    scaler = StandardScaler().fit(Xd_train)
    Xd_train_s = scaler.transform(Xd_train)
    Xd_test_s = scaler.transform(Xd_test)

    models = {
        "Ridge_descriptors": Ridge(alpha=1.0),
        "RF_descriptors": RandomForestRegressor(
            n_estimators=200, max_depth=20, n_jobs=-1, random_state=42
        ),
        "GBM_descriptors": GradientBoostingRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.08, random_state=42
        ),
        # Fingerprint-only baseline uses unscaled FP columns
        "RF_fingerprints": RandomForestRegressor(
            n_estimators=200, max_depth=25, n_jobs=-1, random_state=42
        ),
    }

    predictions = {}
    metrics = {}

    predictions["Ridge_descriptors"] = models["Ridge_descriptors"].fit(
        Xd_train_s, y_train
    ).predict(Xd_test_s)
    predictions["RF_descriptors"] = models["RF_descriptors"].fit(
        Xd_train, y_train
    ).predict(Xd_test)
    predictions["GBM_descriptors"] = models["GBM_descriptors"].fit(
        Xd_train, y_train
    ).predict(Xd_test)
    predictions["RF_fingerprints"] = models["RF_fingerprints"].fit(
        Xf_train, y_train
    ).predict(Xf_test)

    for name, pred in predictions.items():
        metrics[name] = {
            "r2": float(r2_score(y_test, pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, pred))),
            "mae": float(mean_absolute_error(y_test, pred)),
        }

    print(json.dumps(metrics, indent=2))

    best_name = max(metrics, key=lambda k: metrics[k]["r2"])
    best_pred = predictions[best_name]
    best_model = models[best_name]
    with (MODEL_DIR / "solubility_best.pkl").open("wb") as fh:
        pickle.dump(
            {
                "model": best_model,
                "scaler": scaler if "Ridge" in best_name else None,
                "feature_names": DESCRIPTOR_FEATURES,
                "name": best_name,
            },
            fh,
        )

    (MODEL_DIR / "all_models_metrics.json").write_text(
        json.dumps({"metrics": metrics, "best": best_name}, indent=2)
    )

    # Predicted vs observed
    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
    ax.scatter(y_test, best_pred, alpha=0.35, s=14, edgecolor="none")
    lims = [min(y_test.min(), best_pred.min()), max(y_test.max(), best_pred.max())]
    ax.plot(lims, lims, "r--", lw=1)
    ax.set_xlabel("Measured log S (mol/L)")
    ax.set_ylabel("Predicted log S (mol/L)")
    ax.set_title(
        f"ESOL solubility — {best_name}  R²={metrics[best_name]['r2']:.3f}, RMSE={metrics[best_name]['rmse']:.3f}"
    )
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "predicted_vs_observed.png")

    # Feature importance from the best tree model (or ridge coefficients)
    if hasattr(best_model, "feature_importances_"):
        imp = best_model.feature_importances_
        if len(imp) > len(DESCRIPTOR_FEATURES):
            imp, names = imp[: len(DESCRIPTOR_FEATURES)], DESCRIPTOR_FEATURES
        else:
            names = DESCRIPTOR_FEATURES
    else:
        imp = np.abs(best_model.coef_)
        names = DESCRIPTOR_FEATURES
    order = np.argsort(imp)[::-1]
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    ax.barh([names[i] for i in order[::-1]], imp[order[::-1]], color="steelblue")
    ax.set_xlabel("Feature importance")
    ax.set_title(f"Descriptor importance ({best_name})")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "feature_importance.png")

    # Percentile-rank every molecule for solubility triage
    all_X = desc_feats
    if "Ridge" in best_name:
        all_pred = best_model.predict(scaler.transform(all_X))
    else:
        all_pred = best_model.predict(all_X)

    ranked = sorted(
        zip([r["compound_id"] for r in rows], [r["canonical_smiles"] for r in rows], all_pred, y),
        key=lambda t: t[2],
    )
    with (HERE.parent / "predictions_ranked.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            ["compound_id", "canonical_smiles", "predicted_logS", "measured_logS", "rank"]
        )
        for rank, (cid, smi, pred, meas) in enumerate(ranked, 1):
            w.writerow([cid, smi, round(pred, 3), meas, rank])

    print(f"\nBest model: {best_name}  -> models/solubility_best.pkl")
    print(f"Rank 1-5 (LEAST soluble, most negative logS):")
    for cid, smi, pred, meas in ranked[:5]:
        print(f"  {cid:30s} pred={pred:+.3f}  meas={meas:+.3f}  {smi[:60]}")
    print(f"Rank N-4 to N (MOST soluble, most positive logS):")
    for cid, smi, pred, meas in ranked[-5:]:
        print(f"  {cid:30s} pred={pred:+.3f}  meas={meas:+.3f}  {smi[:60]}")


if __name__ == "__main__":
    main()
