"""
ch7_train.py -- Chapter 7 training, k-fold CV, and hyperparameter sensitivity
for Ben's two models (XGBoost, 1D-CNN) on both datasets.

Everything runs through the shared skeleton (src/), so scaling and the imbalance
remedy are fit inside each CV fold -- no leakage, by construction.

For each (model, dataset) it records:
  * stratified k-fold CV summary (mean +/- std of every metric)
  * a train-split -> test-split holdout result
  * a ONE-AT-A-TIME hyperparameter sensitivity sweep from an explicit base
    config (the rubric: "no library defaults", "document how altering key
    hyperparameters affects accuracy and stability")

Outputs:
  results/ch7_cv.json              CV summaries
  results/ch7_holdout.json         holdout metrics
  results/ch7_sensitivity.json     full sweep grid
  report/ch7_sensitivity.md        readable sensitivity report + base configs
  report/figures/ch7_sensitivity_*.png

Run: python analysis/ch7_train.py
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
from src import ingestion                                   # noqa: E402
from src.evaluation import cross_validate, evaluate_holdout  # noqa: E402
from src.models import build_model                          # noqa: E402

RESULTS = ROOT / "results"
FIG = ROOT / "report" / "figures"
REP = ROOT / "report"
RESULTS.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid", font_scale=0.85)

# --- explicit base configs (NO library defaults) -------------------------- #
BASE = {
    "xgboost": dict(n_estimators=400, max_depth=6, learning_rate=0.1,
                    subsample=0.9, colsample_bytree=0.9, min_child_weight=1.0,
                    reg_lambda=1.0, scale_pos_weight=3.0),
    # CNN kept CPU-tractable: max_len 192 covers p99 of both datasets.
    "cnn1d": dict(max_len=192, embed_dim=32, n_filters=128,
                  kernel_sizes=(3, 5, 7), dropout=0.3, lr=1e-3, epochs=6,
                  batch_size=256, pos_weight=3.0),
}

# one-at-a-time sensitivity axes per model
SWEEPS = {
    "xgboost": {
        "max_depth": [3, 6, 9, 12],
        "learning_rate": [0.03, 0.1, 0.3],
        "n_estimators": [100, 400, 800],
        "scale_pos_weight": [1.0, 3.0, 6.0],
    },
    "cnn1d": {
        "n_filters": [64, 128, 256],
        "dropout": [0.1, 0.3, 0.5],
        "lr": [5e-4, 1e-3, 2e-3],
        "pos_weight": [1.0, 3.0, 6.0],
    },
}
# folds: XGBoost is cheap so 5; the CNN is CPU-heavy so 3 (still stratified CV).
CV_FOLDS = {"xgboost": 5, "cnn1d": 3}
# sweeps use fewer CNN epochs to stay tractable; noted in the report.
SWEEP_OVERRIDE = {"cnn1d": dict(epochs=4)}


def _xy(df):
    return df["command"].to_numpy(), df["label"].to_numpy()


def run_cv_and_holdout(model, dataset):
    train, test = ingestion.load(dataset)
    X, y = _xy(train)
    Xte, yte = _xy(test)
    cfg = BASE[model]
    t0 = time.time()
    cv = cross_validate(lambda: build_model(model, **cfg), X, y,
                        n_splits=CV_FOLDS[model])
    ho = evaluate_holdout(build_model(model, **cfg), X, y, Xte, yte)
    dt = round(time.time() - t0, 1)
    s = cv["summary"]
    print(f"[ch7] {model}/{dataset} CV F1={s['f1']['mean']:.4f}"
          f"+/-{s['f1']['std']:.4f} ROC-AUC={s['roc_auc']['mean']:.4f} | "
          f"holdout F1={ho['f1']:.4f} R={ho['recall']:.4f} FPR={ho['fpr']:.4f} "
          f"({dt}s)")
    return cv["summary"], ho


def run_sensitivity(model, dataset):
    train, test = ingestion.load(dataset)
    X, y = _xy(train)
    Xte, yte = _xy(test)
    base = dict(BASE[model])
    base.update(SWEEP_OVERRIDE.get(model, {}))
    grid = {}
    for param, values in SWEEPS[model].items():
        rows = []
        for v in values:
            cfg = dict(base)
            cfg[param] = v
            m = evaluate_holdout(build_model(model, **cfg), X, y, Xte, yte)
            rows.append({"value": v, "f1": m["f1"], "recall": m["recall"],
                         "fpr": m["fpr"], "roc_auc": m["roc_auc"]})
            print(f"    {model}/{dataset} {param}={v}: "
                  f"F1={m['f1']:.4f} R={m['recall']:.4f} FPR={m['fpr']:.4f}")
        grid[param] = rows
    return grid


def plot_sensitivity(model, dataset, grid):
    params = list(grid)
    fig, axes = plt.subplots(1, len(params), figsize=(3.2 * len(params), 3))
    for ax, param in zip(np.atleast_1d(axes), params):
        rows = grid[param]
        xs = [str(r["value"]) for r in rows]
        ax.plot(xs, [r["f1"] for r in rows], "o-", label="F1")
        ax.plot(xs, [r["recall"] for r in rows], "s--", label="Recall")
        ax.plot(xs, [r["fpr"] for r in rows], "^:", label="FPR")
        ax.set_title(param, fontsize=9)
        ax.set_ylim(0, 1)
    axes[0].legend(fontsize=7)
    fig.suptitle(f"{model} sensitivity — {dataset}")
    fig.tight_layout()
    fig.savefig(FIG / f"ch7_sensitivity_{model}_{dataset}.png", dpi=140)
    plt.close(fig)


def main():
    cv_out, ho_out, sens_out = {}, {}, {}
    for model in ("xgboost", "cnn1d"):
        for ds in ingestion.available_datasets():
            key = f"{model}/{ds}"
            summ, ho = run_cv_and_holdout(model, ds)
            cv_out[key], ho_out[key] = summ, ho
            grid = run_sensitivity(model, ds)
            sens_out[key] = grid
            plot_sensitivity(model, ds, grid)

    (RESULTS / "ch7_cv.json").write_text(json.dumps(cv_out, indent=2))
    (RESULTS / "ch7_holdout.json").write_text(json.dumps(ho_out, indent=2))
    (RESULTS / "ch7_sensitivity.json").write_text(json.dumps(sens_out, indent=2))

    # readable sensitivity report
    lines = ["# Chapter 7 — Hyperparameter configuration & sensitivity (Ben)",
             "",
             "All configs are explicit (no library defaults). CNN sensitivity "
             "sweeps use 4 epochs for tractability; the headline CV/holdout use "
             "the full base config below.",
             "",
             "## Base configurations",
             ""]
    for model in ("xgboost", "cnn1d"):
        lines.append(f"**{model}** — `{BASE[model]}`  "
                     f"(CV: {CV_FOLDS[model]}-fold stratified)")
        lines.append("")
    lines.append("## Headline results (base config)")
    lines.append("")
    lines.append("| model / dataset | CV F1 (mean±std) | CV ROC-AUC | "
                 "holdout F1 | holdout Recall | holdout FPR |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for key in cv_out:
        s, h = cv_out[key], ho_out[key]
        lines.append(f"| {key} | {s['f1']['mean']:.4f}±{s['f1']['std']:.4f} | "
                     f"{s['roc_auc']['mean']:.4f} | {h['f1']:.4f} | "
                     f"{h['recall']:.4f} | {h['fpr']:.4f} |")
    lines.append("")
    lines.append("## Sensitivity sweeps (one axis at a time, holdout)")
    lines.append("")
    for key, grid in sens_out.items():
        lines.append(f"### {key}")
        lines.append("")
        for param, rows in grid.items():
            cells = ", ".join(f"{r['value']}→F1 {r['f1']:.3f}/FPR {r['fpr']:.3f}"
                              for r in rows)
            lines.append(f"- **{param}**: {cells}")
        lines.append("")
    # Name the figures this run actually wrote. A `ch7_sensitivity_*.png` glob
    # also matches two pre-redesign orphans and Noam's four RF/IF figures, none
    # of which this chapter discusses.
    lines.append("Figures: " + ", ".join(
        f"`report/figures/ch7_sensitivity_{key.replace('/', '_')}.png`"
        for key in sens_out) + ".")
    (REP / "ch7_sensitivity.md").write_text("\n".join(lines), encoding="utf-8")
    print("[ch7] wrote results/ch7_*.json + report/ch7_sensitivity.md")


if __name__ == "__main__":
    main()
