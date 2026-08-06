# Work Division — Noam / Ben

Final project, due **Aug 15, 2026** (55% of course grade). Rubric: 100 pts + 10 bonus.
Rule of thumb: every chapter is split between us unless splitting would hurt (skeletons stay single-owner). Model owners carry their models through Ch6 → Ch7 → Ch8.

## Who does what

| Unit | Pts | Noam | Ben |
|---|---:|---|---|
| Executive summary | 5 | writes | reviews |
| Ch1 Threat & telemetry mapping | 15 | 1.1 deep-dive (from proposal §2–3) + 4 mapping-table rows w/ rationale | 3 mapping-table rows w/ rationale |
| Ch2 Literature review | 10 | ShellCore paper (feature matrix) | Trizna TOPS paper (feature matrix) + drafts comparative essay |
| Ch3 EDA & feature justification | 15 | **feature extractor (`featurize()`)** + all EDA on Dataset 2 | all EDA on Dataset 1 |
| Ch4 Feature ranking | 10 | discrepancy analysis (intuition vs ranking, leakage checks) | tree-based ranking code + chart |
| Ch5 Harmonization | 10 | writes (documents existing build + shift plots) | reviews |
| Ch6 Model selection | 5 | justification + 1 paper for own 2 models | justification + 1 paper for own 2 models |
| Ch7 Pipeline & models | 10 | own 2 models: impl, explicit hyperparams, sensitivity | **pipeline skeleton** (ingestion→…→eval, CV, imbalance) + own 2 models |
| Ch8 Error analysis & ensemble | 20 | 8.1 on own models · 8.3 vs ShellCore · **8.4 cascading ensemble** | 8.1 on own models · 8.2 assembles cross-dataset table · 8.3 vs TOPS |
| Bonus LLM triage | +10 | implements (HF Inference, Llama 3.1 8B, plugs into ensemble) | B.3 evaluates LLM verdicts on edge cases |
| Packaging | — | report assembly, page budget, ZIP, AI-logs folder | final full-report review pass |

## Models (2 each, all trained on both datasets via the shared skeleton)

| Owner | Models | Paradigms |
|---|---|---|
| Ben | XGBoost · 1D-CNN (char sequences) | traditional · deep |
| Noam | Random Forest · Isolation Forest | traditional · unsupervised |

Owner responsibilities per model: Ch6 justification + literature, Ch7 implementation + explicit hyperparameters + sensitivity analysis, Ch8.1 error forensics, runs on both datasets for 8.2.

## Deadlines & sync points

| Date | Milestone | Blocks |
|---|---|---|
| **Aug 8** | Noam: `featurize()` module done | Ben's Ch3, Ch4, Ch7 |
| Aug 9 | Ben: pipeline skeleton runs end-to-end (any 1 model) | all model work |
| **Aug 11** | Both: all 4 models trained + tuned on both datasets | all of Ch8 |
| Aug 12–13 | Ch8 error analysis, ensemble, bonus | — |
| **Aug 14** | Report freeze: all chapters merged, ≤15 pages, cross-reviewed | — |
| Aug 15 | ZIP + submit | — |

## Ground rules

- **AI logs are graded.** Keep full, unedited logs from every AI tool, starting now. They go in `ai_logs/`, one file per tool.
- **Cross-review.** Every chapter is read by the non-owner before the Aug 14 freeze.
- **Page budget** ≈ proportional to points (Ch8 ~3 pp, Ch1/Ch3 ~2 pp each, rest ~1–1.5 pp). Tables over prose; graphs to appendix.
- **Overflow rule.** Whoever finishes first picks up flagged overdue items — Noam's chapters finish earlier by design, so he's the default absorber if Ch7/Ch8 slip. If time runs out, the bonus is dropped first.
- **No leakage / dataset-agnostic pipeline** are hard grading rules — anything touching scaling, sampling, or splits goes through the skeleton, never ad-hoc per model.
