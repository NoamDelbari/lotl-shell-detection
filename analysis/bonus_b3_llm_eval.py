"""
bonus_b3_llm_eval.py -- Bonus B.3: evaluate LLM triage verdicts on edge cases.

Ben's bonus scope: select the high-uncertainty edge cases (where the primary
models disagree or are unconfident), run the arbitrator over them, and score its
verdicts against ground truth AND against the models. Also records the latency /
call-count numbers B.4 needs.

By default it uses the offline `stub_arbitrator` so the harness runs with no
token; pass --hf to use the real Hugging Face Llama arbitrator (needs HF_TOKEN).
The report must label stub results as a placeholder for Noam's live layer.

Outputs:
  results/bonus_b3_edge_eval.json   per-edge-case verdicts + accuracy summary
  report/bonus_b3_findings.md       written B.3 analysis (+ B.4 latency notes)

Run: python analysis/bonus_b3_llm_eval.py            # offline stub
     python analysis/bonus_b3_llm_eval.py --hf       # real HF Llama
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import ingestion                                # noqa: E402
from src.features import featurize                       # noqa: E402
from src.llm_triage import (huggingface_arbitrator,      # noqa: E402
                            select_edge_cases, stub_arbitrator)
from src.models import build_model                       # noqa: E402

RESULTS = ROOT / "results"
REP = ROOT / "report"
PRIMARY = ("xgboost", "cnn1d", "isolation_forest")   # the disagreement panel


def _xy(df):
    return df["command"].to_numpy(), df["label"].to_numpy()


def _proba(model, X):
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(X))[:, 1]
    return np.asarray(model.decision_scores(X))


def evaluate(dataset: str, arbitrator, arb_name: str):
    train, test = ingestion.load(dataset)
    Xtr, ytr = _xy(train)
    Xte, yte = _xy(test)

    scores = {}
    for name in PRIMARY:
        m = build_model(name)
        m.fit(Xtr, ytr)
        scores[name] = _proba(m, Xte)

    edge = select_edge_cases(scores, y_true=yte)
    idxs = sorted(edge)
    print(f"[b3] {dataset}: {len(idxs)} edge cases / {len(yte)} test rows "
          f"({100*len(idxs)/len(yte):.1f}%)")

    feats = featurize(Xte)
    records, latencies = [], []
    correct_llm = correct_models = 0
    for i in idxs:
        cmd = str(Xte[i])
        context = {
            "xgboost_p": round(float(scores["xgboost"][i]), 3),
            "cnn1d_p": round(float(scores["cnn1d"][i]), 3),
            "isoforest_p": round(float(scores["isolation_forest"][i]), 3),
            "len_chars": int(feats.iloc[i]["len_chars"]),
            "has_dev_tcp": int(feats.iloc[i]["has_dev_tcp"]),
            "has_fetch_bin": int(feats.iloc[i]["has_fetch_bin"]),
        }
        verdict = arbitrator(cmd, context)
        latencies.append(verdict["latency_s"])
        # majority vote of the primary models at 0.5, for comparison
        model_vote = int(np.mean([scores[n][i] for n in PRIMARY]) >= 0.5)
        truth = int(yte[i])
        correct_llm += int(verdict["label"] == truth)
        correct_models += int(model_vote == truth)
        records.append({
            "command": cmd, "truth": truth,
            "llm_label": verdict["label"], "model_vote": model_vote,
            "reason": edge[i], "signals": context,
            "llm_reasoning": verdict["reasoning"][:400],
            "latency_s": round(verdict["latency_s"], 4),
        })

    n = len(idxs) or 1
    summary = {
        "dataset": dataset, "arbitrator": arb_name,
        "n_test": int(len(yte)), "n_edge": len(idxs),
        "edge_fraction": round(len(idxs) / len(yte), 4),
        "llm_accuracy_on_edge": round(correct_llm / n, 4),
        "model_vote_accuracy_on_edge": round(correct_models / n, 4),
        "mean_latency_s": round(float(np.mean(latencies)) if latencies else 0, 4),
        "total_llm_calls": len(idxs),
    }
    return summary, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hf", action="store_true",
                    help="use real Hugging Face Llama (needs HF_TOKEN)")
    args = ap.parse_args()
    if args.hf:
        arbitrator, arb_name = huggingface_arbitrator(), "hf_llama3.1_8b"
    else:
        arbitrator, arb_name = stub_arbitrator, "stub_offline"

    out = {"arbitrator": arb_name, "datasets": {}}
    for ds in ingestion.available_datasets():
        summary, records = evaluate(ds, arbitrator, arb_name)
        out["datasets"][ds] = {"summary": summary, "records": records}
        print(f"[b3] {ds}: LLM acc on edge {summary['llm_accuracy_on_edge']:.3f} "
              f"vs model-vote {summary['model_vote_accuracy_on_edge']:.3f} "
              f"(mean latency {summary['mean_latency_s']:.4f}s, "
              f"{summary['total_llm_calls']} calls)")
    (RESULTS / "bonus_b3_edge_eval.json").write_text(json.dumps(out, indent=2))

    lines = ["# Bonus B.3 — LLM verdict evaluation on edge cases (Ben)", "",
             f"Arbitrator: **{arb_name}**. Edge cases = primary models "
             "(XGBoost, 1D-CNN, Isolation Forest) disagree (score gap ≥ 0.4) or "
             "any is unconfident (score in [0.35, 0.65]).", ""]
    if arb_name == "stub_offline":
        lines += ["> ⚠️ These numbers are from the **offline stub** arbitrator, "
                  "a transparent heuristic that exists to exercise the harness. "
                  "Replace with Noam's live Llama-3.1-8B layer (`--hf`, HF_TOKEN "
                  "set) for the graded bonus result.", ""]
    lines += ["| dataset | test rows | edge cases | edge % | LLM acc on edge | "
              "model-vote acc on edge | mean latency (s) | LLM calls |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for ds, blob in out["datasets"].items():
        s = blob["summary"]
        lines.append(
            f"| {ds} | {s['n_test']} | {s['n_edge']} | "
            f"{100*s['edge_fraction']:.1f}% | {s['llm_accuracy_on_edge']:.3f} | "
            f"{s['model_vote_accuracy_on_edge']:.3f} | {s['mean_latency_s']:.4f} "
            f"| {s['total_llm_calls']} |")
    lines += ["",
              "## B.4 operational tradeoff (support)",
              "",
              "- The cascade only routes **edge cases** to the LLM, so total LLM "
              "calls per evaluation = the 'LLM calls' column, not the full test "
              "set — the assignment's hard requirement. At the measured edge "
              "fraction, a real Llama-3.1-8B endpoint at ~1–3 s/call implies the "
              "per-run wall-clock is that fraction × latency, discussed in B.4.",
              "- Whether this is production-viable depends on the edge fraction "
              "staying small; if the primary models disagree on a large slice, "
              "the LLM becomes the bottleneck and the honest conclusion is that "
              "the cascade needs a tighter uncertainty band, not more LLM."]
    (REP / "bonus_b3_findings.md").write_text("\n".join(lines))
    print("[b3] wrote results/bonus_b3_edge_eval.json + report/bonus_b3_findings.md")


if __name__ == "__main__":
    main()
