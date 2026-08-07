"""
ch8_error_analysis.py -- Chapter 8.1 (forensic error analysis on Ben's models)
and 8.2 (cross-dataset variance table).

Ben's scope (WORK_DIVISION.md): 8.1 on his own models (XGBoost, 1D-CNN);
8.2 assembles the cross-dataset comparison table across all four models.

Produces:
  results/ch8_confusion.json          confusion matrices, both models x datasets
  results/ch8_failures.json           sample-level FN/FP command strings
  results/ch8_cross_dataset.json      in-distribution + transfer metrics, 4 models
  report/figures/ch8_confusion_*.png  confusion-matrix heatmaps (Ben's models)
  report/ch8_2_cross_dataset_table.md the comprehensive 8.2 table
  report/ch8_1_error_forensics_ben.md written FN/FP forensics for XGB + CNN

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
ALL_MODELS = tuple(MODEL_BUILDERS)


def _xy(df):
    return df["command"].to_numpy(), df["label"].to_numpy()


def _proba(model, X):
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(X))[:, 1]
    return np.asarray(model.decision_scores(X))


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
        for name in BEN_MODELS:
            m = fitted[ds][name]
            y_score = _proba(m, Xte)
            y_pred = np.asarray(m.predict(Xte)).astype(int)
            cm = confusion_matrix(yte, y_pred, labels=[0, 1])
            key = f"{name}/{ds}"
            confusion[key] = {"matrix": cm.tolist(),
                              "metrics": compute_metrics(yte, y_pred, y_score),
                              "per_source": per_source_breakdown(
                                  m, Xte, yte, test["source"].to_numpy())}
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
    _write_81_forensics(confusion, failures)
    print("[ch8] wrote confusion/failures/cross-dataset json + report drafts")


def _write_82_table(cross, dsets):
    lines = ["# Chapter 8.2 — Cross-dataset variance (all four models)", "",
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
    (REP / "ch8_2_cross_dataset_table.md").write_text("\n".join(lines))


def _write_81_forensics(confusion, failures):
    lines = ["# Chapter 8.1 — Forensic error analysis (Ben's models)", "",
             "Confusion matrices: `report/figures/ch8_confusion_*.png`. "
             "Sample-level FN/FP: `results/ch8_failures.json`.", ""]
    for key in [f"{n}/{d}" for n in BEN_MODELS
                for d in ingestion.available_datasets()]:
        c = confusion[key]
        m = c["metrics"]
        fn = failures[key]["false_negatives"]
        fp = failures[key]["false_positives"]
        fn_src = Counter(s["source"] for s in fn)
        fp_src = Counter(s["source"] for s in fp)
        lines += [
            f"## {key}",
            "",
            f"- Confusion [tn, fp, fn, tp] = "
            f"[{m['tn']}, {m['fp']}, {m['fn']}, {m['tp']}]; "
            f"F1 {m['f1']:.3f}, Recall {m['recall']:.3f}, FPR {m['fpr']:.3f}.",
            f"- **False negatives** dominated by source(s): "
            f"{dict(fn_src.most_common(4)) or 'none'}.",
            f"- **False positives** dominated by source(s): "
            f"{dict(fp_src.most_common(4)) or 'none'}.",
            "- Example missed attacks (FN): " +
            (" ; ".join(f"`{s['command'][:70]}`" for s in fn[:3]) or "none"),
            "- Example benign flagged (FP): " +
            (" ; ".join(f"`{s['command'][:70]}`" for s in fp[:3]) or "none"),
            "",
        ]
    lines.append("**Cross-model contrast to write up:** compare which commands "
                 "XGBoost misses that the CNN catches and vice-versa — the CNN "
                 "reads raw char motifs (catches obfuscated/adjacent payloads), "
                 "XGBoost reads engineered conjunctions (catches family "
                 "co-occurrence). The disagreement set is exactly what the "
                 "cascade (8.4) and the LLM triage (bonus) are designed to "
                 "resolve.")
    (REP / "ch8_1_error_forensics_ben.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
