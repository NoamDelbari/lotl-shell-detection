"""
ch8_4_cascade_forensics.py -- stage-level audit of the Ch8.4 cascade (Noam).

`analysis/ch8_4_cascade.py` reports what the cascade scores. This script asks
the question the write-up actually needs answering: *which stage is responsible
for each of the cascade's errors, and would removing that stage help?*

It fits Isolation Forest + XGBoost-hybrid ONCE per dataset, caches the stage-1
anomaly scores and the stage-2 probabilities for every test row, then derives
every routing variant from those cached arrays. That reproduces
`CascadeDetector.predict_with_trace` exactly (the routing rule is deterministic
given s1 and p2) while making four ablations affordable:

  hybrid_alone      stage 2 on its own -- the reference the cascade must beat
  cascade_no_s3     stage 1 + stage 2 (uncertain band decided at p >= 0.5)
  cascade_no_s1     stage 2 + stage 3 (no unsupervised pre-filter)
  cascade_full      all three stages, as shipped
  cascade_oracle_s3 all three stages with a PERFECT arbitrator on the band
                    -- the ceiling a live LLM could reach, for the bonus chapter

Plus: out-of-sample stage-1 recall retention (does the 0.99 calibration hold on
held-out attacks?), the composition of the uncertainty band, and a per-decision
audit of the offline stub.

Outputs: results/ch8_4_cascade_forensics.json
Run: python analysis/ch8_4_cascade_forensics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import ingestion                              # noqa: E402
from src.evaluation import compute_metrics             # noqa: E402
from src.llm_triage import stub_arbitrator             # noqa: E402
from src.models import build_model                     # noqa: E402

RESULTS = ROOT / "results"
LO, HI = 0.35, 0.65          # stage2_uncertain, as shipped in ch8_4_cascade.py
RETAIN = 0.99                # stage1_retain_recall, as shipped


def _xy(df):
    return df["command"].to_numpy(), df["label"].to_numpy().astype(int)


def _counts(y, pred):
    y, pred = np.asarray(y), np.asarray(pred)
    return {"tn": int(((y == 0) & (pred == 0)).sum()),
            "fp": int(((y == 0) & (pred == 1)).sum()),
            "fn": int(((y == 1) & (pred == 0)).sum()),
            "tp": int(((y == 1) & (pred == 1)).sum())}


def _score(y, pred, scores):
    m = compute_metrics(y, np.asarray(pred).astype(int), scores)
    return {k: float(m[k]) for k in ("f1", "precision", "recall", "fpr",
                                     "roc_auc", "pr_auc")} | _counts(y, pred)


def analyse(dataset: str) -> dict:
    train, test = ingestion.load(dataset)
    Xtr, ytr = _xy(train)
    Xte, yte = _xy(test)

    m1 = build_model("isolation_forest").fit(Xtr, ytr)
    m2 = build_model("xgboost_hybrid").fit(Xtr, ytr)

    s1_tr = np.asarray(m1.decision_scores(Xtr))
    s1 = np.asarray(m1.decision_scores(Xte))
    p2 = np.asarray(m2.predict_proba(Xte))[:, 1]

    # --- stage-1 threshold, calibrated exactly as CascadeDetector.fit does ----
    thr = float(np.quantile(s1_tr[ytr == 1], 1.0 - RETAIN))
    cleared = s1 < thr
    band = (p2 >= LO) & (p2 <= HI)

    # --- the offline stub's verdict on every band row ------------------------
    stub = np.array([int(stub_arbitrator(str(c), {})["label"]) for c in Xte])

    # --- the five routing variants, all derived from the cached arrays -------
    hyb = (p2 >= 0.5).astype(int)

    full = hyb.copy()
    full[band & ~cleared] = stub[band & ~cleared]
    full[cleared] = 0

    no_s3 = hyb.copy()
    no_s3[cleared] = 0

    no_s1 = hyb.copy()
    no_s1[band] = stub[band]

    oracle = hyb.copy()
    oracle[band & ~cleared] = yte[band & ~cleared]
    oracle[cleared] = 0

    # cascade score vector: stage-2 probability where reached, else s1 (matches
    # CascadeDetector.predict_proba) -- used for the ranking metrics only.
    casc_scores = np.where(cleared, s1, p2)

    variants = {
        "hybrid_alone": _score(yte, hyb, p2),
        "cascade_no_s1": _score(yte, no_s1, p2),
        "cascade_no_s3": _score(yte, no_s3, casc_scores),
        "cascade_full": _score(yte, full, casc_scores),
        "cascade_oracle_s3": _score(yte, oracle, casc_scores),
    }

    # --- stage-1 audit -------------------------------------------------------
    atk_cleared = int((cleared & (yte == 1)).sum())
    ben_cleared = int((cleared & (yte == 0)).sum())
    # of the benign rows stage 1 removed, how many would the hybrid have
    # false-alarmed on?  that is the FP saving stage 1 actually delivers.
    fp_saved = int((cleared & (yte == 0) & (hyb == 1)).sum())
    stage1 = {
        "threshold": thr,
        "n_cleared": int(cleared.sum()),
        "pct_traffic_cleared": float(cleared.mean()),
        "attacks_cleared": atk_cleared,
        "benign_cleared": ben_cleared,
        "recall_retained_test": float(1.0 - atk_cleared / max(int((yte == 1).sum()), 1)),
        "recall_retained_target": RETAIN,
        "hybrid_fps_removed": fp_saved,
        "hybrid_tps_destroyed": int((cleared & (yte == 1) & (hyb == 1)).sum()),
        "train_score_exactly_zero": float((s1_tr == 0.0).mean()),
        "test_score_exactly_zero": float((s1 == 0.0).mean()),
    }

    # --- stage-3 audit -------------------------------------------------------
    b = band & ~cleared
    stage3 = {
        "n_routed": int(b.sum()),
        "pct_traffic_routed": float(b.mean()),
        "attack_prevalence_in_band": float(yte[b].mean()) if b.any() else 0.0,
        "attack_prevalence_overall": float(yte.mean()),
        "hybrid_accuracy_in_band": float((hyb[b] == yte[b]).mean()) if b.any() else 0.0,
        "hybrid_accuracy_off_band": float((hyb[~b] == yte[~b]).mean()),
        "stub_says_malicious": int(stub[b].sum()),
        "stub_accuracy": float((stub[b] == yte[b]).mean()) if b.any() else 0.0,
        "hybrid_accuracy_on_same_rows": float((hyb[b] == yte[b]).mean()) if b.any() else 0.0,
        "flips_vs_hybrid": int((stub[b] != hyb[b]).sum()),
        "flips_that_helped": int(((stub[b] != hyb[b]) & (stub[b] == yte[b])).sum()),
        "flips_that_hurt": int(((stub[b] != hyb[b]) & (stub[b] != yte[b])).sum()),
    }

    # --- the dominance test --------------------------------------------------
    # The stub labels (almost) the whole uncertain band benign, which is a
    # threshold shift wearing an architecture costume. So: can a single scalar
    # threshold on stage 2 alone reach the cascade's operating point? If some
    # threshold matches or beats the cascade on BOTH precision and recall, the
    # three-stage machinery is buying nothing a `>=` sign could not.
    f_p, f_r, f_f1 = variants["cascade_full"]["precision"], \
        variants["cascade_full"]["recall"], variants["cascade_full"]["f1"]
    sweep, dominators = [], []
    for t in np.round(np.arange(0.05, 0.96, 0.01), 2):
        pred = (p2 >= t).astype(int)
        c = _counts(yte, pred)
        prec = c["tp"] / max(c["tp"] + c["fp"], 1)
        rec = c["tp"] / max(c["tp"] + c["fn"], 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-12)
        row = {"threshold": float(t), "precision": prec, "recall": rec,
               "f1": f1, "fpr": c["fp"] / max(c["tn"] + c["fp"], 1)}
        sweep.append(row)
        if prec >= f_p and rec >= f_r:
            dominators.append(row)
    best = max(sweep, key=lambda r: r["f1"])
    dominance = {
        "cascade_precision": f_p, "cascade_recall": f_r, "cascade_f1": f_f1,
        "n_thresholds_dominating_cascade": len(dominators),
        "dominating_thresholds": dominators,
        "best_single_threshold": best,
        "f1_gain_over_cascade_from_threshold_alone": best["f1"] - f_f1,
    }

    # --- error attribution: which stage owns each cascade error --------------
    decided = np.where(cleared, "stage1_clear",
                       np.where(b, "stage3_llm", "stage2_supervised"))
    attribution = {}
    for stage in ("stage1_clear", "stage2_supervised", "stage3_llm"):
        m = decided == stage
        attribution[stage] = {"n": int(m.sum())} | _counts(yte[m], full[m])

    return {
        "dataset": dataset,
        "n_test": int(len(yte)),
        "n_attacks_test": int((yte == 1).sum()),
        "variants": variants,
        "stage1": stage1,
        "stage3": stage3,
        "dominance": dominance,
        "error_attribution": attribution,
    }


def main():
    out = {}
    for ds in ingestion.available_datasets():
        r = analyse(ds)
        out[ds] = r
        v = r["variants"]
        print(f"\n[8.4-forensics] {ds}  (n={r['n_test']}, attacks={r['n_attacks_test']})")
        for name, m in v.items():
            print(f"  {name:<18} F1={m['f1']:.4f} P={m['precision']:.4f} "
                  f"R={m['recall']:.4f} FPR={m['fpr']:.4f} "
                  f"[{m['tn']},{m['fp']},{m['fn']},{m['tp']}]")
        s1, s3 = r["stage1"], r["stage3"]
        print(f"  stage1: thr={s1['threshold']:.6f} cleared={s1['n_cleared']} "
              f"({s1['pct_traffic_cleared']:.1%}) attacks_lost={s1['attacks_cleared']} "
              f"recall_retained={s1['recall_retained_test']:.4f} "
              f"hybrid_FPs_removed={s1['hybrid_fps_removed']} "
              f"hybrid_TPs_destroyed={s1['hybrid_tps_destroyed']}")
        print(f"  stage3: n={s3['n_routed']} ({s3['pct_traffic_routed']:.1%}) "
              f"band_prevalence={s3['attack_prevalence_in_band']:.3f} "
              f"(overall {s3['attack_prevalence_overall']:.3f}) "
              f"stub_acc={s3['stub_accuracy']:.3f} vs hybrid {s3['hybrid_accuracy_in_band']:.3f} "
              f"flips={s3['flips_vs_hybrid']} (+{s3['flips_that_helped']}/-{s3['flips_that_hurt']})")
        d = r["dominance"]
        b = d["best_single_threshold"]
        print(f"  dominance: {d['n_thresholds_dominating_cascade']} single "
              f"thresholds match/beat cascade on BOTH P and R; best-F1 "
              f"threshold {b['threshold']:.2f} -> F1={b['f1']:.4f} "
              f"(cascade {d['cascade_f1']:.4f}, "
              f"gain {d['f1_gain_over_cascade_from_threshold_alone']:+.4f})")
        print(f"  attribution: " + "  ".join(
            f"{k}: n={v2['n']} fp={v2['fp']} fn={v2['fn']}"
            for k, v2 in r["error_attribution"].items()))

    (RESULTS / "ch8_4_cascade_forensics.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print("\n[8.4-forensics] wrote results/ch8_4_cascade_forensics.json")


if __name__ == "__main__":
    main()
