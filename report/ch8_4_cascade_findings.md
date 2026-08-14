# Chapter 8.4 — Hybrid behavioural cascade (results)

Stage 1 Isolation Forest → Stage 2 XGBoost-hybrid → Stage 3 LLM arbitration on the [0.35, 0.65] uncertainty band (offline stub here; swap Noam's live Llama).

**Stage-1 threshold is calibrated, not fixed.** The filter clears a command as benign when its anomaly score falls below the 1st-percentile score of the *training attacks* — i.e. the threshold is chosen so that `stage1_retain_recall` = 0.99 of known attacks survive stage 1. A high-sensitivity first stage must only ever discard confident-benign traffic, and a fixed literal cannot guarantee that across two corpora with different score distributions. Calibrated values this run: dataset1 → 0.0033, dataset2 → 0.0032.

| dataset | cascade F1 | cascade R | cascade FPR | ref F1 (xgb_hybrid) | stage-1 threshold | stage-1 cleared | routed to stage-2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| dataset1 | 0.868 | 0.832 | 0.028 | 0.876 | 0.0033 | 207 | 2842 |
| dataset2 | 0.840 | 0.797 | 0.034 | 0.848 | 0.0032 | 83 | 1832 |

Routing counts (which stage decided each sample) are in `results/ch8_4_cascade.json`. The design goal was to match the strong single model's F1 while the cheap stage-1 filter absorbs the bulk of benign traffic — the analyst-fatigue argument — with the LLM seeing only the uncertainty band, keeping its call count small (the number B.4 reports).

**The write-up lives in `report/ch8_4_cascade_analysis.md`** — this file is generated evidence, so put prose there, not here. It reports the stage-level audit from `analysis/ch8_4_cascade_forensics.py`, and the design goal above is **not met**. The cascade is the weakest of the four configurations of its own components; every stage it adds to the hybrid removes roughly as many true detections as false alarms (Dataset 1: −31 FP for −34 TP); and a single decision threshold on stage 2 alone (`p >= 0.65`) matches or beats the full cascade on precision, recall and FPR. Stage 1 clears only 6.8% / 4.3% of traffic, because the threshold is set for recall rather than throughput — the recall guarantee and the analyst-fatigue saving are in direct tension and this operating point deliberately buys the former. The offline stub fires on none of Dataset 1's 146 routed commands, so stage 3 as run is a threshold shift rather than arbitration; an oracle arbitrator on the same band would be worth +3.7 F1 points over the single best model, which is the target the live Llama layer should be scored against.