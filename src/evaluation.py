"""
evaluation.py -- dataset-agnostic metrics, stratified k-fold CV, and the
per-source / confusion breakdowns Ch8 needs.

Metric set is the one the assignment mandates: Precision, Recall, F1, ROC-AUC,
FPR -- plus PR-AUC and TPR-at-low-FPR, which matter at this 1:3 prevalence
(accuracy alone is misleading; see BASELINE.md on the do-nothing floor).

Nothing here references a dataset by name.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             f1_score, precision_score, recall_score,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold

from . import SEED


def _proba(model, X):
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(X))[:, 1]
    # fall back to decision scores
    return np.asarray(model.decision_scores(X))


def compute_metrics(y_true, y_pred, y_score) -> dict:
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    out = {
        "accuracy": float((tp + tn) / len(y_true)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "fpr": float(fpr),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }
    if len(np.unique(y_true)) == 2:
        out["roc_auc"] = float(roc_auc_score(y_true, y_score))
        out["pr_auc"] = float(average_precision_score(y_true, y_score))
        out["tpr_at_fpr_1e-2"] = float(tpr_at_fpr(y_true, y_score, 1e-2))
        out["tpr_at_fpr_1e-3"] = float(tpr_at_fpr(y_true, y_score, 1e-3))
    return out


def tpr_at_fpr(y_true, y_score, target_fpr: float) -> float:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    ok = fpr <= target_fpr
    return float(tpr[ok].max()) if ok.any() else 0.0


def evaluate_holdout(model, X_train, y_train, X_test, y_test) -> dict:
    """Fit on train, score on test. Returns the standard metric dict."""
    model.fit(X_train, y_train)
    y_score = _proba(model, X_test)
    y_pred = np.asarray(model.predict(X_test)).astype(int)
    return compute_metrics(y_test, y_pred, y_score)


def cross_validate(build_fn, X, y, n_splits: int = 5) -> dict:
    """Stratified k-fold CV. `build_fn` returns a FRESH model each fold so no
    state leaks across folds. Returns per-fold metrics + mean/std summary."""
    X = np.asarray(X, dtype=object)
    y = np.asarray(y).astype(int)
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    fold_metrics = []
    for tr, va in skf.split(X, y):
        model = build_fn()
        model.fit(X[tr], y[tr])
        y_score = _proba(model, X[va])
        y_pred = np.asarray(model.predict(X[va])).astype(int)
        fold_metrics.append(compute_metrics(y[va], y_pred, y_score))
    keys = [k for k in fold_metrics[0] if k not in ("tn", "fp", "fn", "tp")]
    summary = {k: {"mean": float(np.mean([m[k] for m in fold_metrics])),
                   "std": float(np.std([m[k] for m in fold_metrics]))}
               for k in keys}
    return {"folds": fold_metrics, "summary": summary}


def per_source_breakdown(model, X_test, y_test, sources) -> dict:
    """Recall for each malicious source, FPR for each benign source -- the
    breakdown Ch8.1 uses to prove the model learned the technique, not one
    generator."""
    y_score = _proba(model, X_test)
    y_pred = np.asarray(model.predict(X_test)).astype(int)
    y_test = np.asarray(y_test).astype(int)
    sources = np.asarray(sources, dtype=object)
    rows = {}
    for src in np.unique(sources):
        m = sources == src
        yt, yp = y_test[m], y_pred[m]
        if yt.sum() > 0:                       # malicious source -> recall
            rows[src] = {"class": "malicious", "n": int(m.sum()),
                         "recall": float((yp[yt == 1] == 1).mean())}
        else:                                  # benign source -> FPR
            rows[src] = {"class": "benign", "n": int(m.sum()),
                         "fpr": float((yp == 1).mean())}
    return rows


def failure_samples(model, X_test, y_test, sources=None, max_each: int = 40) -> dict:
    """Return the actual misclassified command strings (FN / FP) for Ch8.1
    sample-level forensics."""
    X_test = np.asarray(X_test, dtype=object)
    y_test = np.asarray(y_test).astype(int)
    y_pred = np.asarray(model.predict(X_test)).astype(int)
    y_score = _proba(model, X_test)
    src = np.asarray(sources, dtype=object) if sources is not None else None

    def pack(mask):
        idx = np.where(mask)[0][:max_each]
        return [{"command": str(X_test[i]), "score": float(y_score[i]),
                 "source": (str(src[i]) if src is not None else None)}
                for i in idx]

    return {
        "false_negatives": pack((y_test == 1) & (y_pred == 0)),
        "false_positives": pack((y_test == 0) & (y_pred == 1)),
    }
