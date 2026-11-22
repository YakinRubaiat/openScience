"""Extended metrics skill: classification/regression reports and ROC points.

Operations
----------
- ``classification_report`` — precision/recall/F1 per class + confusion matrix
- ``regression_report``     — MAE/RMSE/R²/MAPE (zero-guarded)
- ``roc_auc_curve_points``  — ROC (fpr, tpr) points and AUC
"""

from __future__ import annotations

from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import skill_run, unwrap


def classification_report(**kwargs: Any) -> dict[str, Any]:
    """Per-class precision/recall/F1 plus a confusion matrix.

    Parameters: ``y_true``, ``y_pred`` (array-likes of labels).
    """
    kw = unwrap(kwargs)
    y_true = np.asarray(kw["y_true"])
    y_pred = np.asarray(kw["y_pred"])
    if y_true.shape != y_pred.shape:
        raise ValueError("y_true and y_pred must have the same shape")

    labels = np.unique(np.concatenate([y_true, y_pred]))
    n = y_true.shape[0]

    cm = np.zeros((len(labels), len(labels)), dtype=int)
    label_idx = {lab: i for i, lab in enumerate(labels)}
    for t, p in zip(y_true, y_pred):
        cm[label_idx[t], label_idx[p]] += 1

    per_class: dict[str, Any] = {}
    for i, lab in enumerate(labels):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum() - tp)
        fn = int(cm[i, :].sum() - tp)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class[str(lab)] = {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "support": int(cm[i, :].sum()),
        }

    accuracy = float(np.trace(cm) / n) if n else 0.0
    macro_precision = float(np.mean([v["precision"] for v in per_class.values()])) if per_class else 0.0
    macro_recall = float(np.mean([v["recall"] for v in per_class.values()])) if per_class else 0.0
    macro_f1 = float(np.mean([v["f1"] for v in per_class.values()])) if per_class else 0.0

    return {
        "n": int(n),
        "labels": [str(l) for l in labels],
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
    }


def regression_report(**kwargs: Any) -> dict[str, Any]:
    """MAE / RMSE / R² / MAPE. MAPE omits samples with |y_true| < ``eps``.

    Parameters: ``y_true``, ``y_pred``; ``eps`` (default 1e-8).
    """
    kw = unwrap(kwargs)
    y_true = np.asarray(kw["y_true"], dtype=float)
    y_pred = np.asarray(kw["y_pred"], dtype=float)
    if y_true.shape != y_pred.shape:
        raise ValueError("y_true and y_pred must have the same shape")
    eps = float(kw.get("eps", 1e-8))

    n = y_true.shape[0]
    err = y_true - y_pred
    mae = float(np.mean(np.abs(err))) if n else None
    rmse = float(np.sqrt(np.mean(err**2))) if n else None
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None

    nonzero = np.abs(y_true) > eps
    if nonzero.any():
        mape = float(np.mean(np.abs(err[nonzero] / y_true[nonzero])) * 100.0)
        n_mape = int(nonzero.sum())
    else:
        mape = None
        n_mape = 0

    return {
        "n": int(n),
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "mape_percent": mape,
        "n_mape_samples": n_mape,
    }


def roc_auc_curve_points(**kwargs: Any) -> dict[str, Any]:
    """ROC curve points (fpr, tpr) and AUC for binary scores.

    Parameters: ``y_true`` (0/1 or bool), ``y_score`` (continuous scores).
    """
    kw = unwrap(kwargs)
    y_true = np.asarray(kw["y_true"]).astype(int)
    y_score = np.asarray(kw["y_score"], dtype=float)
    if y_true.shape != y_score.shape:
        raise ValueError("y_true and y_score must have the same shape")
    if np.unique(y_true).size < 2:
        raise ValueError("y_true must contain both classes")

    pos = y_true == 1
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())

    order = np.argsort(-y_score)
    y_sorted = y_true[order]
    tps = np.cumsum(y_sorted == 1)
    fps = np.cumsum(y_sorted == 0)
    tpr = tps / max(n_pos, 1)
    fpr = fps / max(n_neg, 1)
    tpr = np.concatenate([[0.0], tpr])
    fpr = np.concatenate([[0.0], fpr])

    auc = float(np.trapezoid(tpr, fpr))
    return {
        "n": int(y_true.shape[0]),
        "n_positive": n_pos,
        "n_negative": n_neg,
        "fpr": [float(v) for v in fpr],
        "tpr": [float(v) for v in tpr],
        "thresholds": [float(v) for v in y_score[order]],
        "auc": auc,
    }


run = skill_run(
    {
        "classification_report": classification_report,
        "regression_report": regression_report,
        "roc_auc_curve_points": roc_auc_curve_points,
    }
)

register_skill("metrics_ext", run)
