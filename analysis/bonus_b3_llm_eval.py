#!/usr/bin/env python3
"""Bonus B.3 — LLM triage evaluation on edge cases.

Pipeline (per dataset):
  1. Train XGBoost-hybrid and the 1D-CNN on the train split.
  2. Score both on the test split -> P(attack) per model.
  3. select_edge_cases() flags uncertain/disagreeing samples (spread >= 0.4 OR
     any model in [0.35, 0.65]).
  4. Arbitrate each edge case with the LLM. Three back-ends:
       --ollama   local Llama 3.1-8B through Ollama  <- produced the shipped run
       --hf       Llama 3.1-8B via the HuggingFace Inference API (needs HF_TOKEN)
       (default)  offline deterministic stub, for smoke-testing the harness
  5. Score LLM verdicts against ground truth AND against a 2-model soft-vote
     baseline (mean prob >= 0.5), on the edge cases only.

Saves per-case verdicts + accuracy summary to results/bonus_b3_edge_eval.json.

Reproducing the shipped result (`results/bonus_b3_edge_eval.json`, arbitrator
"llama3.1:8b (ollama, local)"): start Ollama with llama3.1:8b pulled, then

    python analysis/bonus_b3_llm_eval.py --ollama

That is 704 LLM calls at ~11 s each (~2.2 h). The LLM's free-text reasoning is
not bit-reproducible even at temperature 0, so verdict *text* will differ run to
run; the selection stage (which rows are edge cases) is deterministic under
SEED.
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
from src import ingestion                                     # noqa: E402
from src.llm_triage import (huggingface_arbitrator,           # noqa: E402
                            ollama_arbitrator, select_edge_cases,
                            stub_arbitrator)
from src.models import build_cnn1d, build_xgboost_hybrid      # noqa: E402

RESDIR = REPO_ROOT / "results"


def load(dataset, split, limit):
    train_df, test_df = ingestion.load(dataset)
    df = train_df if split == "train" else test_df
    if limit and len(df) > limit:
        df = df.sample(limit, random_state=42).reset_index(drop=True)
    return df["command"].tolist(), df["label"].to_numpy(), df["source"].tolist()


def run_dataset(dataset, arbitrate, limit, max_calls):
    Xtr, ytr, _ = load(dataset, "train", limit)
    Xte, yte, src_te = load(dataset, "test", limit)
    print(f"\n=== {dataset} (train={len(Xtr)}, test={len(Xte)}) ===")

    print("  training XGBoost-hybrid ...")
    p_xgb = build_xgboost_hybrid().fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    print("  training 1D-CNN ...")
    p_cnn = build_cnn1d().fit(Xtr, ytr).predict_proba(Xte)[:, 1]

    # Edge cases: models disagree or either is unsure.
    edge = select_edge_cases({"xgboost_hybrid": p_xgb, "cnn1d": p_cnn})
    p_mean = (p_xgb + p_cnn) / 2.0
    print(f"  edge cases selected: {len(edge)} / {len(Xte)} "
          f"({len(edge)/len(Xte):.1%})")

    cases, n_llm_calls, latencies = [], 0, []
    llm_correct = vote_correct = agree = 0
    for i in edge:
        vote_label = int(p_mean[i] >= 0.5)
        # The arbitrator contract (src/llm_triage.py) is
        #     (command, context) -> {"label", "reasoning", "latency_s"}
        # and the context keys below are the ones the shipped run used, so the
        # prompt the model sees is identical.
        context = {"xgboost_p": round(float(p_xgb[i]), 4),
                   "cnn_p": round(float(p_cnn[i]), 4)}
        if max_calls is not None and n_llm_calls >= max_calls:
            res = {"label": 0, "reasoning": "", "latency_s": 0.0}
            used = "skipped(max_calls)"
        else:
            res = arbitrate(Xte[i], context)
            used = "arbitrated"
            n_llm_calls += 1
            latencies.append(res["latency_s"])
        llm_label = int(res["label"])
        y = int(yte[i])
        llm_correct += int(llm_label == y)
        vote_correct += int(vote_label == y)
        agree += int(llm_label == vote_label)
        cases.append({
            "command": Xte[i][:300], "source": src_te[i], "y_true": y,
            "p_xgb": round(float(p_xgb[i]), 4), "p_cnn": round(float(p_cnn[i]), 4),
            "model_vote": vote_label, "llm_verdict": res["reasoning"],
            "llm_label": llm_label,
            "llm_correct": int(llm_label == y), "vote_correct": int(vote_label == y),
            "routed_to_llm": used,
            "llm_latency_s": round(float(res["latency_s"]), 3),
        })

    n = len(edge)
    rec = {
        "n_test": len(Xte), "n_edge": n,
        "edge_fraction": round(n / len(Xte), 4) if len(Xte) else 0.0,
        "llm_accuracy": round(llm_correct / n, 4) if n else None,
        "model_vote_accuracy": round(vote_correct / n, 4) if n else None,
        "llm_vote_agreement": round(agree / n, 4) if n else None,
        "mean_latency_s": round(float(np.mean(latencies)), 3) if latencies else None,
        "cases": cases,
    }
    print(f"  LLM accuracy on edge cases   : {rec['llm_accuracy']}")
    print(f"  model-vote accuracy on edges : {rec['model_vote_accuracy']}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama", action="store_true",
                    help="use local Llama 3.1-8B via Ollama (the shipped run)")
    ap.add_argument("--ollama-model", default="llama3.1:8b")
    ap.add_argument("--ollama-url", default="http://localhost:11434")
    ap.add_argument("--hf", action="store_true",
                    help="use Llama 3.1-8B via HuggingFace (needs HF_TOKEN)")
    ap.add_argument("--max-calls", type=int, default=None,
                    help="cap edge cases sent to a real LLM (default: no cap)")
    ap.add_argument("--limit", type=int, default=0,
                    help="0 = full data (the shipped run); N = subsample N rows")
    ap.add_argument("--out", type=Path, default=RESDIR / "bonus_b3_edge_eval.json",
                    help="output JSON (point elsewhere to avoid clobbering the "
                         "shipped result during a stub smoke-test)")
    args = ap.parse_args()
    if args.ollama and args.hf:
        ap.error("choose one back-end: --ollama or --hf")
    RESDIR.mkdir(exist_ok=True)
    limit = args.limit or None

    if args.ollama:
        arbitrate = ollama_arbitrator(args.ollama_model, args.ollama_url)
        tag = f"{args.ollama_model} (ollama, local)"
    elif args.hf:
        arbitrate = huggingface_arbitrator()
        tag = "meta-llama/Llama-3.1-8B-Instruct (huggingface)"
    else:
        arbitrate = stub_arbitrator
        tag = "stub (offline heuristic — NOT the graded LLM)"
    # The cap only makes sense for a real back-end; the stub is free.
    max_calls = args.max_calls if (args.ollama or args.hf) else None
    print(f"arbitrator = {tag}")

    per = {d: run_dataset(d, arbitrate, limit, max_calls)
           for d in ("dataset1", "dataset2")}

    # Overall (pooled) accuracy across both datasets' edge cases: a call-weighted
    # mean, recomputed from the per-case verdicts so it can never drift from them.
    all_cases = [c for r in per.values() for c in r["cases"]]
    tot_edge = len(all_cases)
    overall = {
        "n_edge": tot_edge,
        "llm_accuracy": (round(sum(c["llm_correct"] for c in all_cases) / tot_edge, 4)
                         if tot_edge else None),
        "model_vote_accuracy": (round(sum(c["vote_correct"] for c in all_cases) / tot_edge, 4)
                                if tot_edge else None),
    }
    payload = {"arbitrator": tag, "datasets": per, "overall": overall}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))

    print("\nSUMMARY")
    for d, r in per.items():
        print(f"  {d}: {r['n_edge']}/{r['n_test']} edge cases  |  "
              f"LLM acc={r['llm_accuracy']}  vs  model-vote acc={r['model_vote_accuracy']}")
    print(f"  OVERALL: {overall['n_edge']} edge cases  |  "
          f"LLM acc={overall['llm_accuracy']}  vs  model-vote acc={overall['model_vote_accuracy']}")
    print(f"  saved -> {args.out}  (arbitrator={tag})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
