"""
ch8_4_cascade.py -- run and evaluate the hybrid behavioural cascade (Ch8.4).

Stage 1  Isolation Forest (fast, unsupervised) clears confident-benign traffic.
Stage 2  XGBoost-hybrid categorises everything stage 1 flagged.
(Stage 3  LLM arbitration on the uncertain band -- offline stub here; Noam's
          live Llama plugs in via src/llm_triage.huggingface_arbitrator.)

Reports the cascade's own metrics against the single best model, plus the
routing stats (how many samples each stage decided) that Ch8.4 / B.4 need.

Outputs:
  results/ch8_4_cascade.json
  report/ch8_4_cascade_findings.md

Run: python analysis/ch8_4_cascade.py
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
from src.ensemble import CascadeDetector               # noqa: E402
from src.evaluation import compute_metrics             # noqa: E402
from src.llm_triage import stub_arbitrator             # noqa: E402
from src.models import build_model                     # noqa: E402

RESULTS = ROOT / "results"
REP = ROOT / "report"


def _xy(df):
    return df["command"].to_numpy(), df["label"].to_numpy()


def _proba(model, X):
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(X))[:, 1]
    return np.asarray(model.decision_scores(X))


def run(dataset: str, with_llm: bool):
    train, test = ingestion.load(dataset)
    Xtr, ytr = _xy(train)
    Xte, yte = _xy(test)

    # No stage1_clear_below here on purpose. CascadeDetector.fit() calibrates
    # that threshold from the training attack scores whenever
    # stage1_retain_recall is set (default 0.99), so any literal passed in is
    # overwritten before it is ever used. Passing 0.15 -- as this script used to
    # -- was dead on arrival and made the chapter describe a mechanism the code
    # does not run. The calibrated value is captured below and reported.
    cascade = CascadeDetector(
        stage1=build_model("isolation_forest"),
        stage2=build_model("xgboost_hybrid"),
        stage2_uncertain=(0.35, 0.65),
        stage1_retain_recall=0.99,
        arbitrator=stub_arbitrator if with_llm else None,
    ).fit(Xtr, ytr)

    labels, trace = cascade.predict_with_trace(Xte)
    scores = _proba(cascade, Xte)
    met = compute_metrics(yte, labels, scores)
    routing = Counter(trace["decided_by"])

    # single-model reference (best supervised) for the "did the cascade help?"
    ref = build_model("xgboost_hybrid").fit(Xtr, ytr)
    ref_met = compute_metrics(yte, np.asarray(ref.predict(Xte)).astype(int),
                              _proba(ref, Xte))
    return {
        "dataset": dataset, "with_llm_stub": with_llm,
        "cascade": met, "xgboost_hybrid_reference": ref_met,
        "routing": {k: int(v) for k, v in routing.items()},
        "n_cleared_stage1": trace["n_cleared_stage1"],
        "n_to_stage2": trace["n_to_stage2"],
        "stage1_retain_recall": cascade.stage1_retain_recall,
        "stage1_clear_below_calibrated": cascade.stage1_clear_below,
        "stage2_uncertain": list(cascade.stage2_uncertain),
    }


def main():
    out = {}
    for ds in ingestion.available_datasets():
        r = run(ds, with_llm=True)
        out[ds] = r
        c, ref = r["cascade"], r["xgboost_hybrid_reference"]
        print(f"[8.4] {ds}: cascade F1={c['f1']:.3f} R={c['recall']:.3f} "
              f"FPR={c['fpr']:.3f} | ref(xgb_hybrid) F1={ref['f1']:.3f} | "
              f"routing={r['routing']}")
    (RESULTS / "ch8_4_cascade.json").write_text(json.dumps(out, indent=2))

    lines = ["# Chapter 8.4 — Hybrid behavioural cascade (results)", "",
             "Stage 1 Isolation Forest → Stage 2 XGBoost-hybrid → Stage 3 LLM "
             "arbitration on the [0.35, 0.65] uncertainty band (offline stub "
             "here; swap Noam's live Llama).", "",
             "**Stage-1 threshold is calibrated, not fixed.** The filter clears "
             "a command as benign when its anomaly score falls below the "
             "1st-percentile score of the *training attacks* — i.e. the "
             "threshold is chosen so that `stage1_retain_recall` = 0.99 of "
             "known attacks survive stage 1. A high-sensitivity first stage "
             "must only ever discard confident-benign traffic, and a fixed "
             "literal cannot guarantee that across two corpora with different "
             "score distributions. Calibrated values this run: " +
             ", ".join(f"{ds} → {r['stage1_clear_below_calibrated']:.4f}"
                       for ds, r in out.items()) + ".", "",
             "| dataset | cascade F1 | cascade R | cascade FPR | ref F1 (xgb_hybrid) | "
             "stage-1 threshold | stage-1 cleared | routed to stage-2 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for ds, r in out.items():
        c, ref = r["cascade"], r["xgboost_hybrid_reference"]
        lines.append(f"| {ds} | {c['f1']:.3f} | {c['recall']:.3f} | "
                     f"{c['fpr']:.3f} | {ref['f1']:.3f} | "
                     f"{r['stage1_clear_below_calibrated']:.4f} | "
                     f"{r['n_cleared_stage1']} | {r['n_to_stage2']} |")
    lines += ["",
              "Routing counts (which stage decided each sample) are in "
              "`results/ch8_4_cascade.json`. The design goal was to match the "
              "strong single model's F1 while the cheap stage-1 filter absorbs "
              "the bulk of benign traffic — the analyst-fatigue argument — with "
              "the LLM seeing only the uncertainty band, keeping its call count "
              "small (the number B.4 reports).", "",
              "**The write-up lives in `report/ch8_4_cascade_analysis.md`** — "
              "this file is generated evidence, so put prose there, not here. "
              "It reports the stage-level audit from "
              "`analysis/ch8_4_cascade_forensics.py`, and the design goal above "
              "is **not met**. The cascade is the weakest of the four "
              "configurations of its own components; every stage it adds to the "
              "hybrid removes roughly as many true detections as false alarms "
              "(Dataset 1: −31 FP for −34 TP); and a single decision threshold "
              "on stage 2 alone (`p >= 0.65`) matches or beats the full cascade "
              "on precision, recall and FPR. Stage 1 clears only 6.8% / 4.3% of "
              "traffic, because the threshold is set for recall rather than "
              "throughput — the recall guarantee and the analyst-fatigue saving "
              "are in direct tension and this operating point deliberately buys "
              "the former. The offline stub fires on none of Dataset 1's 146 "
              "routed commands, so stage 3 as run is a threshold shift rather "
              "than arbitration; an oracle arbitrator on the same band would be "
              "worth +3.7 F1 points over the single best model, which is the "
              "target the live Llama layer should be scored against."]
    (REP / "ch8_4_cascade_findings.md").write_text("\n".join(lines),
                                                   encoding="utf-8")
    print("[8.4] wrote results/ch8_4_cascade.json + report/ch8_4_cascade_findings.md")


if __name__ == "__main__":
    main()
