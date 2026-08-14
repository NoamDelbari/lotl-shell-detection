# Bonus — LLM-Assisted Triage

## B.1 The layer that was built

**Implemented end to end: one arbitrator contract, three interchangeable
back-ends, no committed secret.** `src/llm_triage.py` ships them behind a prompt
mandating a `VERDICT:` line: Llama 3.1 8B Instruct over the **Hugging Face
Inference API** (`huggingface_arbitrator()` raises without **`HF_TOKEN`**), the
same model through **Ollama**, and a deterministic offline stub. The graded run
(`analysis/bonus_b3_llm_eval.py --ollama`) logged 704 calls to
`results/bonus_b3_edge_eval.json`.

**Chapter 8.4's cascade was measured with that stub, not Llama** — it
returned MALICIOUS on 0 of Dataset 1's 146 routed commands and 2 of Dataset 2's
101, so stage 3 is a threshold shift, not arbitration.

## B.2 What it was asked, and against what bar

**The band is hard — worth +3.7 F1 points to arbitrate.** Edge cases:
XGBoost-hybrid and 1D-CNN probabilities differ by ≥ 0.40, or either lands in
[0.35, 0.65]. In the cascade's narrower band — 4.8% / 5.3% of traffic —
prevalence rises to 0.411 / 0.386 from 0.250 and hybrid accuracy collapses to
**0.589 / 0.634** from 0.956 / 0.940. Chapter 8.4's bar: clear it to earn the
latency; a perfect arbitrator reaches F1 0.9132 / 0.8849.

## B.3 Measured verdicts

**The LLM votes independently — and wrong more often than the models it
arbitrates.** Pooled it scores **0.618** against the soft vote's **0.679**; the
deficit is false alarms, not misses (Table Bonus.1). Cost: 704 calls at mean
11.24 s, 2.2 h per evaluation.

**Table Bonus.1 — Live Llama 3.1 8B against the soft vote on the 434 (D1) and
270 (D2) edge cases, 14.2% / 14.1% of each split.**

<!-- cols: 1.50 1.25 1.25 1.25 1.25 -->
| Measure | D1 LLM | D1 vote | D2 LLM | D2 vote |
|---|---:|---:|---:|---:|
| accuracy | 0.608 | 0.684 | 0.633 | 0.670 |
| attack recall | 0.533 | 0.565 | 0.604 | 0.615 |
| false alarms | 98/280 | 70/280 | 61/174 | 52/174 |
| vote agreement | 0.652 | — | 0.615 | — |

## B.4 Scored against the +3.7 ceiling

**Against Chapter 8.4's ceiling rather than zero, the live layer collects none
of it** — last of four buildable rules on D1, and below the trivial
call-it-all-benign policy on both.

**Honest qualifier: on this band nothing separates from anything else.** Every
buildable rule returns *p* ≥ 0.13 against the LLM (Table Bonus.2): the deficit
is descriptive, not significant, at n = 246 / 150. Only the oracle gap is
significant: the **router** works — it isolates a measured near-chance pocket
holding 0.317 / 0.333 of headroom — but an 8B generalist claims none of it; the
fix is a better arbitrator, not more calls.

**Table Bonus.2 — Every decision rule on the same rows: the 246 (D1) and 150
(D2) edge cases in the [0.35, 0.65] hybrid band.** McNemar: exact paired test
against the LLM row; the oracle is an upper bound, not a built system.

<!-- cols: 2.05 0.95 0.95 1.30 1.25 -->
| Decision rule | D1 acc | D2 acc | McNemar D1 | McNemar D2 |
|---|---:|---:|---:|---:|
| *Oracle (§8.4 ceiling)* | *1.000* | *1.000* | *<0.001* | *<0.001* |
| Soft vote | 0.683 | 0.667 | 0.13 | 0.69 |
| Hybrid at *p* ≥ 0.50 | 0.642 | 0.600 | 0.69 | 0.54 |
| All benign (stage 2 at *p* ≥ 0.65) | 0.638 | 0.653 | 0.76 | 0.90 |
| **Llama 3.1 8B** | **0.622** | **0.640** | — | — |
