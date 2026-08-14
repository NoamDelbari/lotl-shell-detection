# Report assembly index — Ben's contributions

Chapter drafts and where each maps in the final `.docx` (max 15 pp, 1.5 spacing).
Noam assembles the full report; this folder is Ben's material, cross-reviewed
before the Aug 14 freeze. Every draft is backed by reproducible code under
`analysis/` and results under `results/` / `report/figures/`.

| Report section | Ben's draft file | Backing code / data |
|---|---|---|
| Ch1.2 (3 mapping rows) | `ch1_telemetry_rows_ben.md` | `src/features.py` |
| Ch2 (TOPS matrix + essay) | `ch2_literature_review.md` | arXiv 2402.18329, 2103.14221 |
| Ch3 (Dataset 1 EDA) | `ch3_eda_findings.md` + `ch3_feature_justification.csv` | `analysis/ch3_eda.py`, `figures/ch3_*.png` |
| Ch4 (tree ranking) | `ch4_ranking_notes.md` + `ch4_feature_ranking.csv` | `analysis/ch4_ranking.py`, `figures/ch4_*.png` |
| Ch6.1/6.2 (XGB + CNN) | `ch6_model_justification_ben.md` | arXiv 2402.18329, 1804.04177 |
| Ch7 (pipeline + sensitivity) | `ch7_sensitivity.md` + `../PIPELINE.md` | `analysis/ch7_train.py`, `results/ch7_*.json` |
| Ch8.1 (Ben's models forensics) | `ch8_1_error_forensics_ben.md` | `analysis/ch8_error_analysis.py`, `figures/ch8_confusion_*.png` |
| Ch8.2 (cross-dataset table) | `ch8_2_cross_dataset_table.md` | `results/ch8_cross_dataset.json` |
| Ch8.3 (vs TOPS) | `ch8_3_benchmarking_ben.md` | `results/ch7_holdout.json` |
| Bonus B.3 (LLM edge eval) | `bonus_b3_findings.md` | `analysis/bonus_b3_llm_eval.py`, `src/llm_triage.py` |

## Ben's remaining hand-offs to Noam
- **Ch4 discrepancy analysis** (intuition vs ranking, leakage/multicollinearity) —
  Noam writes, seeded by `ch4_ranking_notes.md`.
- **Ch8.4 cascade** — code shipped in `src/ensemble.py`; Noam assembles the
  chapter and wires his Isolation Forest as stage 1.
- **Bonus live LLM** — Noam wires `huggingface_arbitrator` (HF_TOKEN); Ben's B.3
  harness (`--hf`) then produces the graded edge-case evaluation.

## AI-logs reminder (graded)
Keep the full Claude Code transcript for this work under `ai_logs/claude_code_log.*`
per the AI policy — one file per tool, unedited.
