# Bonus — LLM-Assisted Triage

## B.1 The layer that was built

**Implemented end to end: one arbitrator contract, three interchangeable
back-ends, no committed secret.** `src/llm_triage.py` defines an arbitrator as
any callable `(command, context) -> {label, reasoning, latency_s}` and ships
three: Llama 3.1 8B Instruct over the **Hugging Face Inference API**
(`InferenceClient`, temperature 0), the same model through **Ollama**, and a
deterministic offline stub. All three share one prompt ending in a mandated
`VERDICT:` line. `huggingface_arbitrator()` reads **`HF_TOKEN` from the
environment and raises if it is unset**; the client is built lazily, so import
needs no token. The graded run used the local back-end
(`analysis/bonus_b3_llm_eval.py --ollama`): 704 calls, every verdict in
`results/bonus_b3_edge_eval.json`.

**Chapter 8.4's cascade was measured with that stub, not with Llama** — it
returned MALICIOUS on 0 of Dataset 1's 146 routed commands and 2 of Dataset 2's
101, so stage 3 there is a threshold shift, not arbitration. The live model is
measured here, and the result is negative.

## B.2 What it was asked, and against what bar

**The uncertainty band is genuinely hard — which is why arbitrating it is worth
+3.7 F1 points, and why it is a poor place to send a general-purpose 8B model.**
Edge cases: the XGBoost-hybrid and the 1D-CNN differ by ≥ 0.40 in probability,
or either lands in [0.35, 0.65]. Inside the cascade's narrower band — 4.8% /
5.3% of traffic — attack prevalence rises to 0.411 / 0.386 from
0.250 overall and the hybrid's accuracy collapses to **0.589 / 0.634**, against
0.956 / 0.940 off the band. Chapter 8.4 sets the bar: clear that in-band
accuracy to earn the latency; a perfect arbitrator reaches F1 0.9132 / 0.8849.

## B.3 Measured verdicts

**The LLM is a genuinely independent voter that is wrong more often than the
models it arbitrates.** Pooled it scores **0.618** against the soft vote's
**0.679**, agreeing with that vote on only 65% / 61% of cases. The deficit is
false alarms, not misses (Table Bonus.1). Cost is real: 704 calls at a mean
11.24 s is 2.2 h per evaluation, tolerable only because the edge set is 14% of
traffic.

**Table Bonus.1 — Live Llama 3.1 8B against the two-model soft vote on the 434
(D1) and 270 (D2) edge cases, 14.2% / 14.1% of each test split.** The vote is
the two models' mean probability at 0.5; one LLM call per case.

<!-- cols: 2.30 1.05 1.05 1.05 1.05 -->
| Measure on the edge set | D1 LLM | D1 vote | D2 LLM | D2 vote |
|---|---:|---:|---:|---:|
| accuracy | 0.608 | 0.684 | 0.633 | 0.670 |
| recall on attacks | 0.533 | 0.565 | 0.604 | 0.615 |
| false alarms on benign | 98/280 | 70/280 | 61/174 | 52/174 |
| agreement with the vote | 0.652 | — | 0.615 | — |

## B.4 Scored against the +3.7 ceiling

**Measured against the ceiling Chapter 8.4 sets rather than against zero, the
live layer collects none of it.** On identical rows it ranks last of the four
buildable rules on D1, and on neither dataset does it reach the trivial policy
of calling the whole band benign — stage 2 alone at *p* ≥ 0.65.

**The honest qualifier: on this band nothing separates from anything else.**
Every buildable rule tested against the LLM returns *p* ≥ 0.13 (Table Bonus.2), so
the deficit is descriptive, not significant, at n = 246 / 150, and the vote's
lead is not banked either. Only the gap to the oracle is significant, and that
is the finding: the **router** works — the band it isolates is a measured pocket
of near-chance holding 0.317 / 0.333 of accuracy headroom — but a
general-purpose 8B model claims none of it. Closing that gap needs a better
arbitrator, not more calls to this one.

**Table Bonus.2 — Every decision rule scored on the same rows: the 246 (D1) and
150 (D2) edge cases whose hybrid score falls in the [0.35, 0.65] band.** Counted
from the per-case verdicts in `results/bonus_b3_edge_eval.json`; McNemar is an
exact paired test against the LLM row; the oracle is an upper bound, not a built
system.

<!-- cols: 2.30 0.85 0.85 1.25 1.25 -->
| Decision rule on the band | D1 acc | D2 acc | McNemar D1 | McNemar D2 |
|---|---:|---:|---:|---:|
| *Oracle arbitration (§8.4 ceiling)* | *1.000* | *1.000* | *<0.001* | *<0.001* |
| Two-model soft vote | 0.683 | 0.667 | 0.13 | 0.69 |
| Hybrid threshold at *p* ≥ 0.50 | 0.642 | 0.600 | 0.69 | 0.54 |
| Everything benign (= stage 2 at *p* ≥ 0.65) | 0.638 | 0.653 | 0.76 | 0.90 |
| **Llama 3.1 8B arbitration** | **0.622** | **0.640** | — | — |
