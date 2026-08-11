"""
ch8_1_rf_if_forensics.py -- deeper Chapter 8.1 forensics for Noam's two models.

`analysis/ch8_error_analysis.py` emits the confusion matrices and per-source
error counts that both 8.1 write-ups quote. This script answers the questions
those counts cannot: *are the two models failing on the same rows*, *does the
headline supervised model recover Random Forest's misses* (the 8.4 cascade
premise), and *what distinguishes a missed attack from a caught one in feature
space*.

It refits Random Forest, Isolation Forest and XGBoost-hybrid on each dataset's
training split and keeps the full per-row test predictions, so every overlap
figure below is exact rather than sampled from the 40-row caps in
`results/ch8_failures.json`.

Run: python analysis/ch8_1_rf_if_forensics.py
Writes: results/ch8_1_rf_if_forensics.json
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
from src.features import FEATURE_NAMES, featurize      # noqa: E402
from src.models import build_model                     # noqa: E402

MODELS = ("random_forest", "isolation_forest", "xgboost_hybrid")
OUT = ROOT / "results" / "ch8_1_rf_if_forensics.json"


def predictions(dataset: str) -> dict:
    """Fit every model on the training split; return per-row test predictions."""
    train, test = ingestion.load(dataset)
    Xtr, ytr = train["command"].to_numpy(), train["label"].to_numpy()
    Xte, yte = test["command"].to_numpy(), test["label"].to_numpy()

    preds = {}
    for name in MODELS:
        model = build_model(name)
        model.fit(Xtr, ytr)
        preds[name] = np.asarray(model.predict(Xte)).astype(int)
        print(f"  {dataset}/{name}: fitted")
    return {
        "y": yte,
        "commands": Xte,
        "sources": test["source"].to_numpy(),
        "preds": preds,
        "train": (Xtr, ytr),
    }


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 0.0


def analyse(dataset: str) -> dict:
    d = predictions(dataset)
    y, src, cmds = d["y"], d["sources"], d["commands"]
    rf, iso, hyb = (d["preds"][m] for m in MODELS)

    att = np.flatnonzero(y == 1)
    ben = np.flatnonzero(y == 0)
    fn = {m: set(np.flatnonzero((y == 1) & (p == 0))) for m, p in d["preds"].items()}
    fp = {m: set(np.flatnonzero((y == 0) & (p == 1))) for m, p in d["preds"].items()}

    rf_fn, if_fn, hy_fn = fn["random_forest"], fn["isolation_forest"], fn["xgboost_hybrid"]
    rf_fp, if_fp = fp["random_forest"], fp["isolation_forest"]

    # --- the cascade premise: does the hybrid recover what RF misses? ---------
    recovered = rf_fn - hy_fn
    shared_fn = rf_fn & hy_fn
    hybrid_only = hy_fn - rf_fn

    # --- feature-space signature of RF's missed attacks ----------------------
    F = np.asarray(featurize(cmds)[list(FEATURE_NAMES)], dtype=float)  # (n, 43)
    caught = np.array(sorted(set(att) - rf_fn), dtype=int)
    missed = np.array(sorted(rf_fn), dtype=int)
    benign = ben
    sig = []
    for j, fname in enumerate(FEATURE_NAMES):
        m_missed, m_caught, m_benign = (F[missed, j].mean(), F[caught, j].mean(),
                                        F[benign, j].mean())
        # how far the missed attacks sit from caught attacks, in units of the
        # caught-attack spread -- large negative => the missed ones look benign
        sd = F[caught, j].std() or 1.0
        sig.append({"feature": fname, "missed": round(float(m_missed), 4),
                    "caught": round(float(m_caught), 4),
                    "benign": round(float(m_benign), 4),
                    "z_missed_vs_caught": round(float((m_missed - m_caught) / sd), 3)})
    sig.sort(key=lambda r: r["z_missed_vs_caught"])

    # --- how benign do RF's misses look? -------------------------------------
    # fraction of missed attacks whose exact command string also appears in the
    # BENIGN training rows (unlearnable-overlap check from Ch1.1)
    Xtr, ytr = d["train"]
    benign_train = set(Xtr[ytr == 0])
    attack_train = set(Xtr[ytr == 1])
    miss_in_benign = sum(1 for i in missed if cmds[i] in benign_train)
    miss_in_attack = sum(1 for i in missed if cmds[i] in attack_train)

    lens = {"missed": float(np.mean([len(cmds[i]) for i in missed])),
            "caught": float(np.mean([len(cmds[i]) for i in caught])),
            "benign": float(np.mean([len(cmds[i]) for i in benign]))}

    return {
        "n_test": int(len(y)), "n_attack": int(len(att)), "n_benign": int(len(ben)),
        "counts": {m: {"fn": len(fn[m]), "fp": len(fp[m])} for m in MODELS},
        "rf_vs_if": {
            "fn_overlap": len(rf_fn & if_fn),
            "fn_jaccard": round(jaccard(rf_fn, if_fn), 3),
            "fn_rf_only": len(rf_fn - if_fn), "fn_if_only": len(if_fn - rf_fn),
            "fp_overlap": len(rf_fp & if_fp),
            "fp_jaccard": round(jaccard(rf_fp, if_fp), 3),
            "fp_rf_only": len(rf_fp - if_fp), "fp_if_only": len(if_fp - rf_fp),
            "if_fp_sources": dict(Counter(src[i] for i in sorted(if_fp)).most_common()),
            "rf_fp_sources": dict(Counter(src[i] for i in sorted(rf_fp)).most_common()),
        },
        "cascade_premise": {
            "rf_fn": len(rf_fn),
            "recovered_by_hybrid": len(recovered),
            "recovery_rate": round(len(recovered) / len(rf_fn), 3) if rf_fn else None,
            "missed_by_both": len(shared_fn),
            "hybrid_only_fn": len(hybrid_only),
            "recovered_sources": dict(Counter(src[i] for i in sorted(recovered)).most_common()),
            "missed_by_both_sources": dict(Counter(src[i] for i in sorted(shared_fn)).most_common()),
            "examples_recovered": [cmds[i][:90] for i in sorted(recovered)[:8]],
            "examples_missed_by_both": [cmds[i][:90] for i in sorted(shared_fn)[:8]],
        },
        "rf_fn_signature": {
            "most_benign_looking_features": sig[:8],
            "mean_len_chars": {k: round(v, 1) for k, v in lens.items()},
            "missed_str_in_benign_train": miss_in_benign,
            "missed_str_in_attack_train": miss_in_attack,
            "n_missed": len(missed),
        },
    }


def main() -> None:
    out = {}
    for ds in ingestion.available_datasets():
        print(f"[{ds}]")
        out[ds] = analyse(ds)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")

    for ds, r in out.items():
        c = r["cascade_premise"]
        v = r["rf_vs_if"]
        print(f"\n=== {ds} ===")
        print(f"  RF FN {c['rf_fn']} -> hybrid recovers {c['recovered_by_hybrid']} "
              f"({c['recovery_rate']}), both miss {c['missed_by_both']}")
        print(f"  RF/IF FN overlap {v['fn_overlap']} (Jaccard {v['fn_jaccard']}); "
              f"FP overlap {v['fp_overlap']} (Jaccard {v['fp_jaccard']})")
        print(f"  RF misses look benign on: "
              + ", ".join(f"{s['feature']}({s['z_missed_vs_caught']})"
                          for s in r["rf_fn_signature"]["most_benign_looking_features"][:5]))
        print(f"  mean len: {r['rf_fn_signature']['mean_len_chars']}")
        print(f"  missed strings also in benign TRAIN: "
              f"{r['rf_fn_signature']['missed_str_in_benign_train']}"
              f"/{r['rf_fn_signature']['n_missed']}")


if __name__ == "__main__":
    main()
