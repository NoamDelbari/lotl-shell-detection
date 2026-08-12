"""
ch8_1_error_overlap.py -- Chapter 8.1: do the two headline models fail on the
same rows?

Section 8.1 claims the *identity* of the errors is largely model-independent.
That is a measured claim, so it needs its own artefact rather than an inline
calculation: this script refits XGBoost-hybrid and the 1D-CNN on Dataset 1's
training split, keeps every test-row prediction, and intersects the two error
sets exactly (no sampling, unlike the 40-row caps in `results/ch8_failures.json`
— see `failure_samples()` in src/evaluation.py).

The two models share no representation, no inductive bias and no training
procedure, so their overlap is the evidence for the "hard cases are a property
of the labels, not the learner" reading in 8.1.

Run: python analysis/ch8_1_error_overlap.py
Writes: results/ch8_1_error_overlap.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import ingestion                              # noqa: E402
from src.models import build_model                     # noqa: E402

DATASET = "dataset1"
MODELS = {"hybrid": "xgboost_hybrid", "cnn": "cnn1d"}
OUT = ROOT / "results" / "ch8_1_error_overlap.json"


def overlap(a: set, b: set) -> dict:
    both, either = a & b, a | b
    return {
        "hybrid": len(a),
        "cnn": len(b),
        "both": len(both),
        "either": len(either),
        "jaccard": round(len(both) / len(either), 4) if either else 0.0,
        "share_of_hybrid_shared": round(len(both) / len(a), 4) if a else 0.0,
        "share_of_cnn_shared": round(len(both) / len(b), 4) if b else 0.0,
    }


def main() -> None:
    train, test = ingestion.load(DATASET)
    Xtr, ytr = train["command"].to_numpy(), train["label"].to_numpy()
    Xte, yte = test["command"].to_numpy(), test["label"].to_numpy()
    sources = test["source"].to_numpy()

    preds = {}
    for key, name in MODELS.items():
        model = build_model(name)
        model.fit(Xtr, ytr)
        preds[key] = np.asarray(model.predict(Xte)).astype(int)
        print(f"  {DATASET}/{name}: fitted")

    # False negative = attack scored benign; false positive = the converse.
    fn = {k: {i for i in range(len(yte)) if yte[i] == 1 and p[i] == 0}
          for k, p in preds.items()}
    fp = {k: {i for i in range(len(yte)) if yte[i] == 0 and p[i] == 1}
          for k, p in preds.items()}
    both_fn = sorted(fn["hybrid"] & fn["cnn"])
    both_fp = sorted(fp["hybrid"] & fp["cnn"])

    out = {
        "n_test": int(len(yte)),
        "n_attack": int((yte == 1).sum()),
        "n_benign": int((yte == 0).sum()),
        "fn": overlap(fn["hybrid"], fn["cnn"]),
        "fp": overlap(fp["hybrid"], fp["cnn"]),
        "both_fn_by_source": dict(Counter(sources[i] for i in both_fn)),
        "both_fp_by_source": dict(Counter(sources[i] for i in both_fp)),
        "both_fn": [{"command": str(Xte[i]), "source": str(sources[i])}
                    for i in both_fn],
        "both_fp": [{"command": str(Xte[i]), "source": str(sources[i])}
                    for i in both_fp],
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(f"[8.1] FN: hybrid {out['fn']['hybrid']}, cnn {out['fn']['cnn']}, "
          f"both {out['fn']['both']} (Jaccard {out['fn']['jaccard']})")
    print(f"[8.1] FP: hybrid {out['fp']['hybrid']}, cnn {out['fp']['cnn']}, "
          f"both {out['fp']['both']} (Jaccard {out['fp']['jaccard']})")
    print(f"[8.1] wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
