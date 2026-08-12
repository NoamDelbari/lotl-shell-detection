# Appendix A — Execution Instructions and Environment

All commands are run from the repository root unless stated. Everything is
seeded (`SEED = 42`, `src/__init__.py`); the tree models are deterministic under
it, so a clean rebuild reproduces the shipped result files.

## A.1 Execution environment

The project was developed and run on **two independent machines**. This matters
for reading the results: the deep-learning model was trained on Apple-silicon
GPU while the tree and anomaly models were trained on CPU, so the two halves of
the results table were not produced on the same hardware. Nothing in the
comparison depends on it — every model is seeded and the tree models are
deterministic under that seed — but the report should not imply a single
environment.

**Table A.1 — Execution environments.**

| | **Environment A** (Ben Volovelsky) | **Environment B** (Noam Delbari) |
|---|---|---|
| OS | macOS, Apple M-series (M3 Pro) | Windows 11 Home (build 26200) |
| Compute | Apple-silicon GPU via Metal | CPU only |
| Accelerator used | PyTorch **MPS** backend (`torch.device("mps")`) for the 1D-CNN; Ollama GPU inference for Bonus B.3 | none — `torch` CPU wheel |
| Python | 3.11 | 3.11.9 |
| Work produced here | Pipeline skeleton, `xgboost`, `xgboost_hybrid`, `cnn1d`, the Ch7 sweeps for those models, Figure 7.1 source, the Bonus B.3 LLM run | 43-feature selection, Ch3 EDA, `random_forest`, `isolation_forest`, their Ch7 sweeps, Ch6, Ch8.1/8.3/8.4, all regenerated result files |

**Table A.2 — Frameworks and libraries.** Versions are those of Environment B,
where the shipped `results/` files were last regenerated.

| Package | Version | Role |
|---|---|---|
| Python | 3.11.9 | runtime |
| numpy | 2.3.5 | numerics |
| pandas | 2.3.3 | data handling |
| pyarrow | 23.0.0 | Parquet/Arrow I/O in the dataset build |
| requests | 2.32.4 | raw-corpus downloads in `scripts/build_dataset.py` |
| scikit-learn | 1.8.0 | RandomForest, IsolationForest, TF-IDF, StandardScaler, StratifiedKFold, metrics |
| xgboost | 3.2.0 | gradient-boosted trees (`xgboost`, `xgboost_hybrid`) |
| imbalanced-learn | 0.14.2 | `ImbPipeline` — leakage-safe pipeline used by every model |
| torch | 2.11.0 | 1D-CNN (MPS in Environment A, CPU in Environment B) |
| scipy | 1.17.0 | statistics for the Ch3 feature audit |
| matplotlib / seaborn | 3.10.8 / 0.13.2 | all figures |
| pytest | 8.4.1 | test suite (§A.6) |
| Ollama + `llama3.1:8b` | local server | Bonus B.3 arbitrator (Environment A; optional, no Python dependency — called over HTTP) |

**Note on `requirements.txt`.** The shipped file specifies minimum versions
(`>=`) rather than exact pins, so that one file installs on both macOS/MPS and
Windows/CPU. The exact versions the shipped results were produced under are the
ones tabulated above.

## A.2 Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional, for the bonus LLM triage layer only (§A.5, Bonus B.3). The shipped
B.3 result was produced with a **local** Llama 3.1-8B through Ollama, which
needs no credentials:

```bash
ollama pull llama3.1:8b          # then leave `ollama serve` running
```

A hosted alternative is available via `--hf`, which reads `HF_TOKEN` from the
environment. The token is never committed and is not required for any result in
this report.

## A.3 Rebuild the datasets and the baseline

```bash
cd scripts
python build_dataset.py          # re-downloads missing raw/ caches, rebuilds dataset/ + docs
python evaluate_baseline.py      # retrains the TF-IDF+LR baseline, rewrites BASELINE.md + metrics json
cd ..
```

`build_dataset.py` writes `dataset/dataset{1,2}_{train,test}.csv` (columns
`id, command, label, source, split`) with the 80/20 split already materialised,
grouped by command shape.

## A.4 Train and evaluate

`main.py` is the entry point. Four subcommands; `--model` accepts
`xgboost`, `xgboost_hybrid`, `cnn1d`, `random_forest`, `isolation_forest`, and
`--dataset` accepts `dataset1`, `dataset2`.

| Purpose | Command |
|---|---|
| Every model × every dataset (the headline table) | `python main.py all` |
| Single hold-out run | `python main.py holdout --model xgboost_hybrid --dataset dataset1` |
| Stratified k-fold CV | `python main.py cv --model random_forest --dataset dataset1 --folds 5` |
| Cross-dataset transfer | `python main.py transfer --model cnn1d --train dataset1 --test dataset2` |

Results are written to `results/` as JSON; `python main.py all` also refreshes
`results/summary.json`, the file every score in this report is read from.

## A.5 Reproduce the per-chapter analyses

| Report section | Command |
|---|---|
| Ch3 — EDA statistics and figures | `python analysis/ch3_eda.py` then `python analysis/ch3_eda_figures.py` |
| Ch4 — feature importance ranking | `python analysis/ch4_ranking.py` |
| Ch6 — Isolation Forest sub-sample probe | `python analysis/ch6_if_subsample_probe.py` |
| Ch7.1 — pipeline block diagram (Figure 7.1) | `python analysis/ch7_1_pipeline_figure.py` |
| Ch7.3 — hyperparameter sweeps | `python analysis/ch7_train.py` and `python analysis/ch7_rf_if_sweeps.py` |
| Ch8.1 — error forensics | `python analysis/ch8_error_analysis.py`, `python analysis/ch8_1_rf_if_forensics.py`, `python analysis/ch8_1_error_overlap.py` |
| Ch8.2 — cross-dataset transfer heat-map | `python analysis/ch8_2_transfer_heatmap.py` |
| Ch8.4 — cascade ablation | `python analysis/ch8_4_cascade.py` then `python analysis/ch8_4_cascade_forensics.py` |
| Bonus B.3 — LLM triage evaluation | `python analysis/bonus_b3_llm_eval.py --ollama` |

The B.3 command is the one that produced the shipped
`results/bonus_b3_edge_eval.json`: 704 local LLM calls at ~11 s each, ≈2.2 h.
Add `--max-calls N` to cap it, or omit `--ollama` to exercise the harness
against the offline stub. Which rows are selected as edge cases is deterministic
under `SEED`; the LLM's free-text reasoning is not bit-reproducible even at
temperature 0.

⚠️ **Do not run `analysis/ch3_feature_audit.py` to "refresh" the Chapter 3
decision table.** It regenerates `report/ch3_feature_decisions.md` and overwrites
the hand-entered final KEEP/KILL verdicts recorded during the joint feature
review. The audit JSON it consumes is already in `results/ch3_feature_audit.json`.

## A.6 Tests

```bash
python -m pytest tests/ -q       # 6 tests: pipeline contracts, feature schema, naming rules
```

One test enforces a project rule worth naming here: dataset identifiers may not
appear anywhere in `src/*.py` except `ingestion.py`, so no model or feature can
condition on which corpus a command came from (`tests/test_pipeline.py`).

## A.7 Reproducibility

`SEED = 42` is set once in `src/__init__.py` and threaded through every model
builder, the k-fold splitter and the dataset build. The XGBoost, RandomForest
and IsolationForest results are bit-reproducible from a clean checkout on either
machine. The 1D-CNN is reproducible up to the usual floating-point
non-determinism of GPU kernels, so its figures may differ in the last decimal
between Environment A and Environment B.
