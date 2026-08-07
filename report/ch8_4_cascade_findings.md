# Chapter 8.4 — Hybrid behavioural cascade (results)

Stage 1 Isolation Forest (clear benign if anomaly score < 0.15) → Stage 2 XGBoost-hybrid → Stage 3 LLM arbitration on the [0.35,0.65] uncertainty band (offline stub here; swap Noam's live Llama).

| dataset | cascade F1 | cascade R | cascade FPR | ref F1 (xgb_hybrid) | stage-1 cleared | routed to stage-2 |
|---|---:|---:|---:|---:|---:|---:|
| dataset1 | 0.873 | 0.841 | 0.029 | 0.873 | 179 | 2870 |
| dataset2 | 0.838 | 0.791 | 0.032 | 0.842 | 65 | 1850 |

Routing counts (which stage decided each sample) are in `results/ch8_4_cascade.json`. The design goal is to match the strong single model's F1 while the cheap stage-1 filter absorbs the bulk of benign traffic — the analyst-fatigue argument. The LLM only sees the uncertainty band, keeping its call count small (the number B.4 reports).