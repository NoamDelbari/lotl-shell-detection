# Appendix A — Execution Instructions and Environment

## A.1 Execution environment

**Table A.1 — The two machines the project ran on, and which results came from
each.** All commands run from the repository root, and `SEED = 42`
(`src/__init__.py`) is threaded through every model builder, the k-fold splitter
and the dataset build: the tree and anomaly results are bit-reproducible on
either machine, and only the 1D-CNN's last decimal moves, through GPU
floating-point non-determinism.

<!-- cols: 1.00 2.75 2.75 -->
| | **Environment A** (Ben Volovelsky) | **Environment B** (Noam Delbari) |
|---|---|---|
| OS · Python | macOS, Apple M3 Pro · 3.11 | Windows 11 Home (26200) · 3.11.9 |
| Compute | Apple-silicon GPU: PyTorch **MPS** for the 1D-CNN, Ollama GPU inference for Bonus B.3 | CPU only — `torch` CPU wheel |
| Results produced | pipeline skeleton; `xgboost`, `xgboost_hybrid`, `cnn1d` + sweeps; Figure 7.1; Bonus B.3 | 43-feature selection; Ch3 EDA; `random_forest`, `isolation_forest` + sweeps; Ch6; Ch8.1/8.3/8.4; all result files |

**Table A.2 — Library versions behind the shipped numbers (Environment B, where
`results/` was last regenerated).** `requirements.txt` uses `>=` rather than
exact pins so one file installs on both machines.

<!-- cols: 1.50 5.00 -->
| Role | Versions |
|---|---|
| Runtime and data | Python 3.11.9 · numpy 2.3.5 · pandas 2.3.3 · pyarrow 23.0.0 · requests 2.32.4 |
| Models | scikit-learn 1.8.0 · xgboost 3.2.0 · imbalanced-learn 0.14.2 (`ImbPipeline`) · torch 2.11.0 |
| Analysis, figures, tests | scipy 1.17.0 · matplotlib 3.10.8 · seaborn 0.13.2 · pytest 8.4.1 |
| Bonus B.3 arbitrator | Ollama + `llama3.1:8b`, local server (Environment A; called over HTTP, no Python dependency) |

## A.2 Reproducing every result

**Table A.3 — Every command needed to regenerate the report's artefacts, in
order.** A bare script name runs as `python analysis/<name>`. `--model` accepts
any of the five model keys and `--dataset` either of `dataset1`, `dataset2`;
`python main.py all` refreshes `results/summary.json`, the file every score in
this report is read from.

<!-- cols: 2.20 4.30 -->
| Step | Command |
|---|---|
| Install | `python -m venv .venv` then `pip install -r requirements.txt` |
| Rebuild the datasets, then the TF-IDF baseline | `cd scripts` · `python build_dataset.py` · `python evaluate_baseline.py` |
| **Headline table — every model × dataset** | `python main.py all` |
| Single hold-out run | `python main.py holdout --model xgboost_hybrid --dataset dataset1` |
| Stratified 5-fold CV | `python main.py cv --model random_forest --dataset dataset1 --folds 5` |
| Cross-dataset transfer | `python main.py transfer --model cnn1d --train dataset1 --test dataset2` |
| Ch3 — EDA statistics, then figures | `ch3_eda.py` · `ch3_eda_figures.py` |
| Ch4, Ch6 — feature ranking, IF sub-sample probe | `ch4_ranking.py` · `ch6_if_subsample_probe.py` |
| Ch7 — pipeline diagram, then the sweeps | `ch7_1_pipeline_figure.py` · `ch7_train.py` · `ch7_rf_if_sweeps.py` |
| Ch8.1 — error forensics | `ch8_error_analysis.py` · `ch8_1_rf_if_forensics.py` · `ch8_1_error_overlap.py` |
| Ch8.2, 8.4 — transfer heat-map, cascade ablation | `ch8_2_transfer_heatmap.py` · `ch8_4_cascade.py` · `ch8_4_cascade_forensics.py` |
| Bonus B.3 — LLM triage evaluation | `bonus_b3_llm_eval.py --ollama` |
| Appendix B tables, then the tests | `appendix_b_tables.py` · `python -m pytest tests/ -q` |

**Table A.4 — Three commands that need care before they are run.**

<!-- cols: 1.40 5.10 -->
| Command | What to know |
|---|---|
| `bonus_b3_llm_eval.py` | 704 local LLM calls at ~11 s each, ≈2.2 h. Needs `ollama pull llama3.1:8b` and a running `ollama serve`; `--max-calls N` caps it, `--ollama` omitted runs the offline stub. The hosted alternative `--hf` reads `HF_TOKEN` from the environment — **the token is never committed**, and no result here requires it. Edge-case selection is deterministic under `SEED`; the LLM's reasoning is not, even at temperature 0. |
| `pytest tests/` | Six tests cover pipeline contracts, the feature schema and the naming rules. One enforces a project rule worth naming: dataset identifiers may not appear in `src/*.py` outside `ingestion.py`, so no model or feature can condition on which corpus a command came from. |
| `ch3_feature_audit.py` | ⚠️ **Do not run it to "refresh" the Chapter 3 decision table.** It overwrites the hand-entered KEEP/KILL verdicts in `report/ch3_feature_decisions.md`. The audit JSON it consumes is already in `results/ch3_feature_audit.json`. |
