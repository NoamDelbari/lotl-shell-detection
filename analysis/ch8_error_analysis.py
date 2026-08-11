"""
ch8_error_analysis.py -- Chapter 8.1 (forensic error analysis on Ben's models)
and 8.2 (cross-dataset variance table).

Ben's scope (WORK_DIVISION.md): 8.1 on his own models (XGBoost, 1D-CNN);
8.2 assembles the cross-dataset comparison table across every registry model.

Produces:
  results/ch8_confusion.json          confusion matrices + full FN/FP source
                                      counts, ALL models x datasets
  results/ch8_failures.json           sample-level FN/FP command strings
                                      (capped at 40 each -- samples, not counts)
  results/ch8_cross_dataset.json      in-distribution + transfer metrics
  report/figures/ch8_confusion_*.png  confusion-matrix heatmaps, every model
  report/ch8_2_cross_dataset_table.md the comprehensive 8.2 table
  report/ch8_1_error_forensics_ben.md written FN/FP forensics for XGB + CNN
  report/ch8_1_error_forensics_noam.md  ditto for Random Forest + Isolation Forest

Run: python analysis/ch8_error_analysis.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import ingestion                                    # noqa: E402
from src.evaluation import (compute_metrics, evaluate_holdout,  # noqa: E402
                            failure_samples, per_source_breakdown)
from src.models import MODEL_BUILDERS, build_model           # noqa: E402

RESULTS = ROOT / "results"
FIG = ROOT / "report" / "figures"
REP = ROOT / "report"
sns.set_theme(style="white", font_scale=0.85)

BEN_MODELS = ("xgboost_hybrid", "cnn1d")
NOAM_MODELS = ("random_forest", "isolation_forest")
ALL_MODELS = tuple(MODEL_BUILDERS)

# 8.1 confusion matrices are emitted for EVERY model, not just Ben's two: the
# rubric asks for all four headline models on both datasets, and the plain
# `xgboost` variant is cheap to include since fit_on() already fits it.
CONFUSION_MODELS = ALL_MODELS


def _xy(df):
    return df["command"].to_numpy(), df["label"].to_numpy()


def _proba(model, X):
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(X))[:, 1]
    return np.asarray(model.decision_scores(X))


def _error_sources(y_true, y_pred, sources) -> dict:
    """Full FN/FP source distributions, counted over EVERY error.

    Ch8.1 used to derive these from `failure_samples()`, but that helper caps
    each list at `max_each=40` for readability -- so every "dominated by
    source(s)" line summed to exactly 40 and silently contradicted the fn/fp
    counts printed one line above it. The counts belong with the confusion
    matrix, not with the sample dump.
    """
    y_true = np.asarray(y_true).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    sources = np.asarray(sources, dtype=object)
    fn = sources[(y_true == 1) & (y_pred == 0)]
    fp = sources[(y_true == 0) & (y_pred == 1)]
    return {"fn_sources": dict(Counter(fn.tolist()).most_common()),
            "fp_sources": dict(Counter(fp.tolist()).most_common())}


def fit_on(dataset):
    train, test = ingestion.load(dataset)
    Xtr, ytr = _xy(train)
    fitted = {}
    for name in ALL_MODELS:
        m = build_model(name)
        m.fit(Xtr, ytr)
        fitted[name] = m
    return fitted, train, test


def main():
    # fit every model once per (training) dataset, reuse for in-dist + transfer
    fitted = {}
    tests = {}
    for ds in ingestion.available_datasets():
        f, _, test = fit_on(ds)
        fitted[ds] = f
        tests[ds] = test
        print(f"[ch8] fitted {len(f)} models on {ds}")

    # ---- 8.1 confusion + forensics for Ben's models, in-distribution ----
    confusion, failures = {}, {}
    for ds in ingestion.available_datasets():
        test = tests[ds]
        Xte, yte = _xy(test)
        for name in CONFUSION_MODELS:
            m = fitted[ds][name]
            y_score = _proba(m, Xte)
            y_pred = np.asarray(m.predict(Xte)).astype(int)
            cm = confusion_matrix(yte, y_pred, labels=[0, 1])
            key = f"{name}/{ds}"
            confusion[key] = {"matrix": cm.tolist(),
                              "metrics": compute_metrics(yte, y_pred, y_score),
                              "per_source": per_source_breakdown(
                                  m, Xte, yte, test["source"].to_numpy()),
                              **_error_sources(yte, y_pred,
                                               test["source"].to_numpy())}
            failures[key] = failure_samples(m, Xte, yte,
                                            test["source"].to_numpy())
            # heatmap
            fig, ax = plt.subplots(figsize=(3.4, 3))
            sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                        xticklabels=["benign", "malic."],
                        yticklabels=["benign", "malic."], ax=ax)
            ax.set_title(f"{name} — {ds}")
            ax.set_xlabel("predicted"); ax.set_ylabel("actual")
            fig.tight_layout()
            fig.savefig(FIG / f"ch8_confusion_{name}_{ds}.png", dpi=140)
            plt.close(fig)
    (RESULTS / "ch8_confusion.json").write_text(json.dumps(confusion, indent=2))
    (RESULTS / "ch8_failures.json").write_text(json.dumps(failures, indent=2))

    # ---- 8.2 cross-dataset variance: in-distribution + transfer, 4 models ----
    cross = {}
    dsets = ingestion.available_datasets()
    for train_ds in dsets:
        for test_ds in dsets:
            test = tests[test_ds]
            Xte, yte = _xy(test)
            for name in ALL_MODELS:
                m = fitted[train_ds][name]
                y_score = _proba(m, Xte)
                y_pred = np.asarray(m.predict(Xte)).astype(int)
                met = compute_metrics(yte, y_pred, y_score)
                cross[f"{name}|train={train_ds}|test={test_ds}"] = met
    (RESULTS / "ch8_cross_dataset.json").write_text(json.dumps(cross, indent=2))

    _write_82_table(cross, dsets)
    _write_81_forensics(confusion, failures, BEN_MODELS,
                        "ch8_1_error_forensics_ben.md", "Ben's models",
                        _BEN_CONTRAST)
    _write_81_forensics(confusion, failures, NOAM_MODELS,
                        "ch8_1_error_forensics_noam.md", "Noam's models",
                        _NOAM_CONTRAST)
    print("[ch8] wrote confusion/failures/cross-dataset json + report drafts")


def _write_82_table(cross, dsets):
    lines = [f"# Chapter 8.2 — Cross-dataset variance "
             f"(all {len(ALL_MODELS)} registry models)", "",
             "In-distribution (train and test on the same dataset's splits) and "
             "cross-dataset transfer. Diagonal = in-distribution; off-diagonal = "
             "transfer. Metrics at threshold 0.5.", "",
             "| model | train → test | Accuracy | Precision | Recall/DR | FPR | F1 | ROC-AUC |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for name in ALL_MODELS:
        for tr in dsets:
            for te in dsets:
                m = cross[f"{name}|train={tr}|test={te}"]
                tag = "in-dist" if tr == te else "transfer"
                lines.append(
                    f"| {name} | {tr}→{te} ({tag}) | {m['accuracy']:.3f} | "
                    f"{m['precision']:.3f} | {m['recall']:.3f} | {m['fpr']:.3f} | "
                    f"{m['f1']:.3f} | {m.get('roc_auc', float('nan')):.3f} |")
    lines += ["",
              "**Reading the table (diagnosis seed):** a large diagonal→off-"
              "diagonal drop is either *Environmental Distribution Shift* "
              "(curated Dataset 1 vs real honeypot Dataset 2 — different attack "
              "surface form) or *Model Overfitting* to the training source. The "
              "asymmetry (D1→D2 vs D2→D1) tells them apart: if D1→D2 >> D2→D1, "
              "the curated set has broader coverage and the honeypot model is "
              "narrow (overfit), not just shifted."]
    (REP / "ch8_2_cross_dataset_table.md").write_text("\n".join(lines),
                                                      encoding="utf-8")


_BEN_CONTRAST = (
    "**Cross-model contrast to write up:** compare which commands XGBoost "
    "misses that the CNN catches and vice-versa — the CNN reads raw char "
    "motifs (catches obfuscated/adjacent payloads), XGBoost reads engineered "
    "conjunctions (catches family co-occurrence). The disagreement set is "
    "exactly what the cascade (8.4) and the LLM triage (bonus) are designed "
    "to resolve.")

_NOAM_CONTRAST = (
    "**The write-up lives in `report/ch8_1_rf_if_forensics.md`** — this file is "
    "generated evidence, so put prose there, not here. The overlap, recovery "
    "and feature-signature figures it quotes come from "
    "`analysis/ch8_1_rf_if_forensics.py`, which keeps every test-row "
    "prediction instead of the 40-row samples below. Headline results: RF and "
    "IF have *nested* false negatives (on Dataset 1 IF catches nothing RF "
    "misses) but *near-disjoint* false positives, so their complementarity is "
    "about benign traffic; XGBoost-hybrid recovers ~58% of RF's misses, which "
    "is the 8.4 cascade premise. Note RF is the lowest-FPR supervised model on "
    "Dataset 1 only — on Dataset 2 the hybrid and the TF-IDF baseline both run "
    "cleaner. Cross-reference "
    "`report/ch7_rf_if_sensitivity_findings.md` for why IF's shipped operating "
    "point sits in an extreme-precision corner rather than re-deriving it.")


def _write_81_forensics(confusion, failures, models, filename, who, contrast):
    keys = [f"{n}/{d}" for n in models for d in ingestion.available_datasets()]
    # Name this section's own figures. A `ch8_confusion_*.png` glob matches all
    # ten (both owners, five models), only four of which are discussed here.
    lines = [f"# Chapter 8.1 — Forensic error analysis ({who})", "",
             "Confusion matrices: " + ", ".join(
                 f"`report/figures/ch8_confusion_{k.replace('/', '_')}.png`"
                 for k in keys) + ". "
             "Sample-level FN/FP command strings (capped at 40 per cell): "
             "`results/ch8_failures.json`. The by-source counts below are "
             "over every error, from `results/ch8_confusion.json`.", ""]
    for key in keys:
        c = confusion[key]
        m = c["metrics"]
        fn = failures[key]["false_negatives"]
        fp = failures[key]["false_positives"]
        # Counted over every error (see _error_sources), NOT over the 40-sample
        # cap in `failures` -- these have to reconcile with m['fn'] / m['fp'].
        fn_src = c["fn_sources"]
        fp_src = c["fp_sources"]
        lines += [
            f"## {key}",
            "",
            f"- Confusion [tn, fp, fn, tp] = "
            f"[{m['tn']}, {m['fp']}, {m['fn']}, {m['tp']}]; "
            f"F1 {m['f1']:.3f}, Recall {m['recall']:.3f}, FPR {m['fpr']:.3f}.",
            f"- **False negatives** by source (all {m['fn']}): "
            f"{fn_src or 'none'}.",
            f"- **False positives** by source (all {m['fp']}): "
            f"{fp_src or 'none'}.",
            "- Example missed attacks (FN): " +
            (" ; ".join(f"`{s['command'][:70]}`" for s in fn[:3]) or "none"),
            "- Example benign flagged (FP): " +
            (" ; ".join(f"`{s['command'][:70]}`" for s in fp[:3]) or "none"),
            "",
        ]
    lines.append(contrast)
    (REP / filename).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
