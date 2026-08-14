"""Ch6 §6.6 — is the Isolation Forest paper's recommended sub-sample size better
than our production `max_samples=0.8`?

Liu, Ting & Zhou (ICDM 2008; ACM TKDD 6(1) art. 3, 2012) recommend a small fixed
sub-sample, psi=256, with t=100 trees, arguing that small sub-samples suppress
*swamping* and *masking*. Production uses `max_samples=0.8` of the benign
training rows -- roughly 30x larger -- so before citing that paper in Ch6 we
check whether the published default would actually be an improvement.

ROC-AUC is the metric of record here: it is threshold-independent, so it isolates
ranking quality from the operating point. Ch7 already establishes that the
operating point is set elsewhere entirely (the wrapper's fixed 0.5 threshold, or
the cascade's recall-retention calibration), so F1 at sklearn's calibrated
threshold is reported alongside only for continuity with the Ch7 tables.

Result (see report/ch6_rf_if_justification.md §6.6): the paper's default is the
WORST cell on both datasets and production sits within 0.003 AUC of the best, so
Ch6 cites the paper for the isolation principle but explicitly declines its
sub-sampling recommendation, with the measurement as the reason.

The production rows here reproduce results/summary.json's Isolation Forest
ROC-AUC exactly, which doubles as an independent check on both.

Run: python analysis/ch6_if_subsample_probe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import ingestion                     # noqa: E402
from src.evaluation import compute_metrics    # noqa: E402
from src.models import build_model            # noqa: E402

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

# (label, max_samples, n_estimators). `contamination` is held at the production
# value throughout and is irrelevant to ROC-AUC by construction (Ch7).
SETTINGS = [
    ("paper default (psi=256, t=100)", 256, 100),
    ("psi=256, t=300", 256, 300),
    ("psi=1024, t=300", 1024, 300),
    ("psi=4096, t=300", 4096, 300),
    ("production (0.8, t=300)", 0.8, 300),
    ("psi=all (1.0, t=300)", 1.0, 300),
]


def probe(dataset):
    train, test = ingestion.load(dataset)
    X, y = train["command"].to_numpy(), train["label"].to_numpy()
    Xte, yte = test["command"].to_numpy(), test["label"].to_numpy()
    n_benign = int((y == 0).sum())
    print(f"\n[ch6-if-psi] {dataset}: {n_benign} benign training rows "
          f"(production psi = 0.8 x {n_benign} = {int(0.8 * n_benign)})")
    rows = []
    for label, ms, n_est in SETTINGS:
        det = build_model("isolation_forest", contamination=0.25,
                          max_features=1.0, max_samples=ms, n_estimators=n_est)
        det.fit(X, y)                    # fits trees on benign rows only
        Xt = det.pipeline_.transform(Xte)
        y_pred = (det.iso_.predict(Xt) == -1).astype(int)
        m = compute_metrics(yte, y_pred, det.decision_scores(Xte))
        rows.append({"setting": label, "max_samples": ms,
                     "n_estimators": n_est, "roc_auc": m["roc_auc"],
                     "f1": m["f1"], "recall": m["recall"], "fpr": m["fpr"]})
        print(f"    {label:32s} ROC-AUC={m['roc_auc']:.4f}  F1={m['f1']:.4f}  "
              f"R={m['recall']:.4f}  FPR={m['fpr']:.4f}")
    return {"n_benign_train": n_benign, "rows": rows}


def main():
    out = {ds: probe(ds) for ds in ("dataset1", "dataset2")}
    for ds, res in out.items():
        best = max(res["rows"], key=lambda r: r["roc_auc"])
        prod = next(r for r in res["rows"] if r["max_samples"] == 0.8)
        paper = res["rows"][0]
        print(f"\n[ch6-if-psi] {ds}: best={best['setting']} "
              f"({best['roc_auc']:.4f}); production={prod['roc_auc']:.4f} "
              f"(gap {best['roc_auc'] - prod['roc_auc']:+.4f}); "
              f"paper default={paper['roc_auc']:.4f} "
              f"(gap {paper['roc_auc'] - prod['roc_auc']:+.4f})")
    path = RESULTS / "ch6_if_subsample_probe.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n[ch6-if-psi] wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
