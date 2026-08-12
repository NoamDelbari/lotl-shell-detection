# Bonus B.3 — LLM verdict evaluation on edge cases (Ben)

Arbitrator: **Llama 3.1-8B (llama3.1:8b via Ollama, local inference)**. Edge cases = primary models (XGBoost, 1D-CNN, Isolation Forest) disagree (score gap ≥ 0.4) or any is unconfident (score in [0.35, 0.65]).

| dataset | test rows | edge cases | edge % | LLM acc on edge | model-vote acc on edge | LLM–vote agreement | mean latency (s) | LLM calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| dataset1 | 3049 | 434 | 14.2% | 0.608 | 0.684 | 0.652 | 11.36 | 434 |
| dataset2 | 1915 | 270 | 14.1% | 0.633 | 0.670 | 0.615 | 11.05 | 270 |

On both corpora the local Llama-3.1-8B **trails the models' own majority vote** on exactly the cases where that vote is least certain (0.608 vs 0.684 on D1, 0.633 vs 0.670 on D2), and it agrees with the vote only ~62–65% of the time — so on this uncertain slice the LLM behaves as a genuinely independent voter rather than a rubber stamp, but it does not out-arbitrate the ensemble it was meant to break ties for. Each verdict cost a mean of **~11.2 s** on a local M3 Pro (Ollama, GPU), so the full edge set of 434 + 270 = **704 calls** ran in ≈82 min (D1) + ≈50 min (D2) ≈ **2.2 h total**; at the ~14% edge fraction that is the entire LLM cost per evaluation, because the other ~86% of the test set never reaches the model.

## B.4 operational tradeoff (support)

- The cascade only routes **edge cases** to the LLM, so total LLM calls per evaluation = the 'LLM calls' column, not the full test set — the assignment's hard requirement. At the measured ~11 s/call and ~14% edge fraction, the per-run LLM wall-clock is that fraction × latency (≈82 min for D1's 3,049 rows, ≈50 min for D2's 1,915), which is only tolerable because the fraction stays small.
- Whether this is production-viable depends on the edge fraction staying small; if the primary models disagree on a large slice, the LLM becomes the bottleneck and the honest conclusion is that the cascade needs a tighter uncertainty band, not more LLM.
