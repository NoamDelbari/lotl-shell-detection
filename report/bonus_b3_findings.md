# Bonus B.3 — LLM verdict evaluation on edge cases (Ben)

Arbitrator: **stub_offline**. Edge cases = primary models (XGBoost, 1D-CNN, Isolation Forest) disagree (score gap ≥ 0.4) or any is unconfident (score in [0.35, 0.65]).

> ⚠️ These numbers are from the **offline stub** arbitrator, a transparent heuristic that exists to exercise the harness. Replace with Noam's live Llama-3.1-8B layer (`--hf`, HF_TOKEN set) for the graded bonus result.

| dataset | test rows | edge cases | edge % | LLM acc on edge | model-vote acc on edge | mean latency (s) | LLM calls |
|---|---:|---:|---:|---:|---:|---:|---:|
| dataset1 | 3049 | 1117 | 36.6% | 0.408 | 0.816 | 0.0000 | 1117 |
| dataset2 | 1915 | 813 | 42.4% | 0.451 | 0.817 | 0.0000 | 813 |

## B.4 operational tradeoff (support)

- The cascade only routes **edge cases** to the LLM, so total LLM calls per evaluation = the 'LLM calls' column, not the full test set — the assignment's hard requirement. At the measured edge fraction, a real Llama-3.1-8B endpoint at ~1–3 s/call implies the per-run wall-clock is that fraction × latency, discussed in B.4.
- Whether this is production-viable depends on the edge fraction staying small; if the primary models disagree on a large slice, the LLM becomes the bottleneck and the honest conclusion is that the cascade needs a tighter uncertainty band, not more LLM.