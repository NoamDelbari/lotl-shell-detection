#!/usr/bin/env python3
"""Bonus B.3 — LLM triage evaluation on edge cases.

Pipeline (per dataset):
  1. Train XGBoost-hybrid and CNN on the train split.
  2. Score both on the test split -> P(attack) per model.
  3. select_edge_cases() flags uncertain/disagreeing samples (spread >= 0.4 OR
     any model in [0.35, 0.65]).
  4. Arbitrate each edge case with the LLM (stub by default; --hf for real
     Llama 3.1-8B via the HuggingFace Inference API, needs HF_TOKEN).
  5. Score LLM verdicts against ground truth AND against a 2-model soft-vote
     baseline (mean prob >= 0.5), on the edge cases only.

Saves per-case verdicts + accuracy summary to results/bonus_b3_edge_eval.json.

Usage:  python analysis/bonus_b3_llm_eval.py [--hf] [--limit N]
        (--limit defaults to 6000 for a tractable run; --limit 0 for full;
         --hf-max caps how many edge cases hit the real LLM)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
# NOTE: importing src.models pulls in torch first, which preloads the OpenMP
# runtime xgboost needs — so build_xgboost_hybrid().fit() runs in-process here.
from src.ingestion import load_dataset                       # noqa: E402
from src.llm_triage import (huggingface_arbitrator,          # noqa: E402
                            select_edge_cases, stub_arbitrator)
from src.models import build_cnn, build_xgboost_hybrid       # noqa: E402

RESDIR = REPO_ROOT / "results"
DATASET_NUM = {"dataset1": 1, "dataset2": 2}


def load(dataset, split, limit):
    n = DATASET_NUM[dataset]
    df = load_dataset(REPO_ROOT / "dataset" / f"dataset{n}_{split}.csv")
    if limit and len(df) > limit:
        df = df.sample(limit, random_state=42).reset_index(drop=True)
    return df["command"].tolist(), df["label"].to_numpy(), df["source"].tolist()


def run_dataset(dataset, arbitrate, limit, hf_max):
    Xtr, ytr, _ = load(dataset, "train", limit)
    Xte, yte, src_te = load(dataset, "test", limit)
    print(f"\n=== {dataset} (train={len(Xtr)}, test={len(Xte)}) ===")

    print("  training XGBoost-hybrid ...")
    p_xgb = build_xgboost_hybrid().fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    print("  training CNN ...")
    p_cnn = build_cnn().fit(Xtr, ytr).predict_proba(Xte)[:, 1]

    # Edge cases: models disagree or either is unsure.
    edge = select_edge_cases({"xgboost_hybrid": p_xgb, "cnn": p_cnn})
    p_mean = (p_xgb + p_cnn) / 2.0
    print(f"  edge cases selected: {len(edge)} / {len(Xte)} "
          f"({len(edge)/len(Xte):.1%})")

    cases, n_llm_calls = [], 0
    llm_correct = vote_correct = agree = 0
    for i in edge:
        vote_label = int(p_mean[i] >= 0.5)
        if hf_max is not None and n_llm_calls >= hf_max:
            verdict = "BENIGN"; used = "skipped(hf_max)"
        else:
            verdict = arbitrate(Xte[i]); used = "arbitrated"; n_llm_calls += 1
        llm_label = 1 if str(verdict).strip().upper() == "MALICIOUS" else 0
        y = int(yte[i])
        llm_correct += int(llm_label == y)
        vote_correct += int(vote_label == y)
        agree += int(llm_label == vote_label)
        cases.append({
            "command": Xte[i][:300], "source": src_te[i], "y_true": y,
            "p_xgb": round(float(p_xgb[i]), 4), "p_cnn": round(float(p_cnn[i]), 4),
            "model_vote": vote_label, "llm_verdict": verdict, "llm_label": llm_label,
            "llm_correct": int(llm_label == y), "vote_correct": int(vote_label == y),
            "routed_to_llm": used,
        })

    n = len(edge)
    rec = {
        "n_test": len(Xte), "n_edge": n,
        "edge_fraction": round(n / len(Xte), 4) if len(Xte) else 0.0,
        "llm_accuracy": round(llm_correct / n, 4) if n else None,
        "model_vote_accuracy": round(vote_correct / n, 4) if n else None,
        "llm_vote_agreement": round(agree / n, 4) if n else None,
        "cases": cases,
    }
    print(f"  LLM accuracy on edge cases   : {rec['llm_accuracy']}")
    print(f"  model-vote accuracy on edges : {rec['model_vote_accuracy']}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hf", action="store_true",
                    help="use real Llama 3.1-8B via HuggingFace (needs HF_TOKEN)")
    ap.add_argument("--hf-max", type=int, default=100,
                    help="cap edge cases sent to the real LLM (--hf only)")
    ap.add_argument("--limit", type=int, default=6000, help="0 = full data")
    args = ap.parse_args()
    RESDIR.mkdir(exist_ok=True)
    limit = args.limit or None

    arbitrate = huggingface_arbitrator if args.hf else stub_arbitrator
    hf_max = args.hf_max if args.hf else None
    print(f"arbitrator = {'huggingface (Llama 3.1-8B)' if args.hf else 'stub (random)'}")

    per = {d: run_dataset(d, arbitrate, limit, hf_max) for d in ("dataset1", "dataset2")}

    # Overall (pooled) accuracy across both datasets' edge cases.
    tot_edge = sum(r["n_edge"] for r in per.values())
    tot_llm = sum((r["llm_accuracy"] or 0) * r["n_edge"] for r in per.values())
    tot_vote = sum((r["model_vote_accuracy"] or 0) * r["n_edge"] for r in per.values())
    overall = {
        "n_edge": tot_edge,
        "llm_accuracy": round(tot_llm / tot_edge, 4) if tot_edge else None,
        "model_vote_accuracy": round(tot_vote / tot_edge, 4) if tot_edge else None,
    }
    payload = {"arbitrator": "huggingface" if args.hf else "stub",
               "datasets": per, "overall": overall}
    (RESDIR / "bonus_b3_edge_eval.json").write_text(json.dumps(payload, indent=2))

    print("\nSUMMARY")
    for d, r in per.items():
        print(f"  {d}: {r['n_edge']}/{r['n_test']} edge cases  |  "
              f"LLM acc={r['llm_accuracy']}  vs  model-vote acc={r['model_vote_accuracy']}")
    print(f"  OVERALL: {overall['n_edge']} edge cases  |  "
          f"LLM acc={overall['llm_accuracy']}  vs  model-vote acc={overall['model_vote_accuracy']}")
    print(f"  saved -> {RESDIR/'bonus_b3_edge_eval.json'}  "
          f"(arbitrator={'huggingface' if args.hf else 'stub'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
