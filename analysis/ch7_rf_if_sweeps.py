"""
ch7_rf_if_sweeps.py -- Chapter 7 hyperparameter sensitivity for Noam's two
models (Random Forest, Isolation Forest) on both datasets.

Companion to analysis/ch7_train.py (Ben's XGBoost/CNN sweeps). Differences,
both deliberate:

  * RF is cheap on the engineered features, so instead of one-at-a-time we run
    the FULL n_estimators x max_depth grid on the FULL training data -- no
    subsample caveat applies to these numbers.
  * The Isolation Forest contamination sweep CANNOT go through
    evaluate_holdout(): sklearn's `score_samples` does not depend on
    `contamination` (the trees are identical; contamination only sets
    `offset_`), and IsolationForestDetector.predict() thresholds a min-max
    normalised score at a fixed 0.5. Swept through the wrapper, all four
    contamination values would return byte-identical metrics. We therefore
    evaluate each contamination value at its OWN calibrated threshold
    (sklearn's `predict`, i.e. decision_function < 0), which is what the knob
    actually means: "flag the top-`contamination` fraction of benign training
    scores". The wrapper's fixed-0.5 production operating point is recorded
    once per dataset for comparison.

Outputs:
  results/ch7_rf_if_sensitivity.json
  report/figures/ch7_sensitivity_random_forest_<dataset>.png
  report/figures/ch7_sensitivity_isolation_forest_<dataset>.png

Run: python analysis/ch7_rf_if_sweeps.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import ingestion                                    # noqa: E402
from src.evaluation import compute_metrics, evaluate_holdout  # noqa: E402
from src.models import build_model                           # noqa: E402

RESULTS = ROOT / "results"
FIG = ROOT / "report" / "figures"
RESULTS.mkdir(exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid", font_scale=0.85)

# Okabe-Ito hues (colorblind-safe; validated with the dataviz six-checks
# script). Series identity is doubly encoded: hue + marker/linestyle.
C_BLUE, C_ORANGE, C_VERMIL = "#0072B2", "#E69F00", "#D55E00"

# --- sweep axes (docs/NOAM_TODO.md, Ch7) ---------------------------------- #
RF_N_ESTIMATORS = [50, 100, 200, 500]
RF_MAX_DEPTH = [None, 10, 20]
# pinned non-swept RF params = the production config in src/models.py
RF_FIXED = dict(min_samples_leaf=1, max_features="sqrt",
                class_weight="balanced_subsample")
IF_CONTAMINATION = [0.05, 0.10, 0.20, 0.30]
IF_FIXED = dict(n_estimators=300, max_samples=0.8, max_features=1.0)


def _xy(df):
    return df["command"].to_numpy(), df["label"].to_numpy()


def sweep_random_forest(dataset):
    train, test = ingestion.load(dataset)
    X, y = _xy(train)
    Xte, yte = _xy(test)
    rows = []
    for depth in RF_MAX_DEPTH:
        for n in RF_N_ESTIMATORS:
            t0 = time.time()
            m = evaluate_holdout(
                build_model("random_forest", n_estimators=n, max_depth=depth,
                            **RF_FIXED),
                X, y, Xte, yte)
            rows.append({"n_estimators": n, "max_depth": depth,
                         "f1": m["f1"], "recall": m["recall"],
                         "precision": m["precision"], "fpr": m["fpr"],
                         "roc_auc": m["roc_auc"]})
            print(f"    rf/{dataset} n={n} depth={depth}: F1={m['f1']:.4f} "
                  f"R={m['recall']:.4f} FPR={m['fpr']:.4f} "
                  f"({time.time() - t0:.1f}s)")
    return rows


def sweep_isolation_forest(dataset):
    train, test = ingestion.load(dataset)
    X, y = _xy(train)
    Xte, yte = _xy(test)
    rows = []
    wrapper_point = None
    for c in IF_CONTAMINATION:
        t0 = time.time()
        det = build_model("isolation_forest", contamination=c, **IF_FIXED)
        det.fit(X, y)                       # fits trees on benign rows only
        Xt = det.pipeline_.transform(Xte)
        # contamination-calibrated threshold: sklearn flags decision_function<0
        y_pred = (det.iso_.predict(Xt) == -1).astype(int)
        y_score = det.decision_scores(Xte)
        m = compute_metrics(yte, y_pred, y_score)
        rows.append({"contamination": c, "f1": m["f1"], "recall": m["recall"],
                     "precision": m["precision"], "fpr": m["fpr"],
                     "roc_auc": m["roc_auc"]})
        print(f"    if/{dataset} c={c}: F1={m['f1']:.4f} R={m['recall']:.4f} "
              f"FPR={m['fpr']:.4f} AUC={m['roc_auc']:.4f} "
              f"({time.time() - t0:.1f}s)")
        if wrapper_point is None:           # forest is identical across c --
            y_pred_w = det.predict(Xte)     # record the fixed-0.5 point once
            mw = compute_metrics(yte, y_pred_w, y_score)
            wrapper_point = {"f1": mw["f1"], "recall": mw["recall"],
                             "precision": mw["precision"], "fpr": mw["fpr"],
                             "roc_auc": mw["roc_auc"]}
    aucs = {round(r["roc_auc"], 6) for r in rows}
    if len(aucs) != 1:                      # sanity: trees must not vary with c
        raise AssertionError(f"IF ROC-AUC varies with contamination: {aucs}")
    return rows, wrapper_point


def plot_rf(dataset, rows):
    colors = {None: C_BLUE, 10: C_ORANGE, 20: C_VERMIL}
    markers = {None: "o", 10: "s", 20: "^"}
    styles = {None: "-", 10: "--", 20: ":"}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3))
    for metric, ax in zip(("f1", "fpr"), axes):
        for depth in RF_MAX_DEPTH:
            sub = [r for r in rows if r["max_depth"] == depth]
            ax.plot([str(r["n_estimators"]) for r in sub],
                    [r[metric] for r in sub],
                    marker=markers[depth], linestyle=styles[depth],
                    color=colors[depth], linewidth=2, markersize=6,
                    label=f"max_depth={depth}")
        ax.set_xlabel("n_estimators")
        ax.set_ylabel(metric.upper() if metric == "fpr" else "F1")
    axes[0].legend(fontsize=7)
    fig.suptitle(f"Random Forest sensitivity — {dataset}")
    fig.tight_layout()
    fig.savefig(FIG / f"ch7_sensitivity_random_forest_{dataset}.png", dpi=140)
    plt.close(fig)


def plot_if(dataset, rows):
    xs = [r["contamination"] for r in rows]
    fig, ax = plt.subplots(figsize=(4.2, 3))
    ax.plot(xs, xs, color="0.65", linewidth=1, linestyle=(0, (1, 3)))
    ax.annotate("FPR = contamination", (xs[-1], xs[-1]), fontsize=7,
                color="0.4", ha="right", va="bottom")
    for metric, color, marker, style, label in (
            ("f1", C_BLUE, "o", "-", "F1"),
            ("recall", C_ORANGE, "s", "--", "Recall"),
            ("fpr", C_VERMIL, "^", ":", "FPR")):
        ax.plot(xs, [r[metric] for r in rows], marker=marker, linestyle=style,
                color=color, linewidth=2, markersize=6, label=label)
    ax.set_xlabel("contamination")
    ax.set_ylabel("metric value")
    ax.set_xticks(xs)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=7)
    fig.suptitle(f"Isolation Forest sensitivity — {dataset}")
    fig.tight_layout()
    fig.savefig(FIG / f"ch7_sensitivity_isolation_forest_{dataset}.png",
                dpi=140)
    plt.close(fig)


def main():
    out = {"random_forest": {}, "isolation_forest": {},
           "rf_fixed": {**RF_FIXED},
           "if_fixed": {**IF_FIXED, "note": "wrapper_0.5 = production "
                        "fixed-threshold operating point (contamination-"
                        "independent)"}}
    for ds in ingestion.available_datasets():
        print(f"[ch7-rf-if] {ds}: RF grid "
              f"({len(RF_N_ESTIMATORS) * len(RF_MAX_DEPTH)} configs)")
        rf_rows = sweep_random_forest(ds)
        out["random_forest"][ds] = rf_rows
        plot_rf(ds, rf_rows)

        print(f"[ch7-rf-if] {ds}: IF contamination sweep")
        if_rows, wrapper = sweep_isolation_forest(ds)
        out["isolation_forest"][ds] = {"sweep": if_rows,
                                       "wrapper_0.5": wrapper}
        plot_if(ds, if_rows)

    path = RESULTS / "ch7_rf_if_sensitivity.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"[ch7-rf-if] wrote {path} + figures")


if __name__ == "__main__":
    main()
