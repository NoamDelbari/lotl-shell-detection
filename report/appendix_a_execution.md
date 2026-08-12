# Appendix A — Code Execution Instructions

All commands are run from the repository root unless stated. Everything is
seeded (`SEED = 42`, `src/__init__.py`); the tree models are deterministic under
it, so a clean rebuild reproduces the shipped result files.

## A.1 Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional, for the bonus LLM triage layer only:

```bash
export HF_TOKEN=...              # never committed; read from the environment
```

## A.2 Rebuild the datasets and the baseline

```bash
cd scripts
python build_dataset.py          # re-downloads missing raw/ caches, rebuilds dataset/ + docs
python evaluate_baseline.py      # retrains the TF-IDF+LR baseline, rewrites BASELINE.md + metrics json
cd ..
```

`build_dataset.py` writes `dataset/dataset{1,2}_{train,test}.csv` (columns
`id, command, label, source, split`) with the 80/20 split already materialised,
grouped by command shape.

## A.3 Train and evaluate

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

## A.4 Reproduce the per-chapter analyses

| Report section | Command |
|---|---|
| Ch3 — EDA statistics and figures | `python analysis/ch3_eda.py` then `python analysis/ch3_eda_figures.py` |
| Ch4 — feature importance ranking | `python analysis/ch4_ranking.py` |
| Ch6 — Isolation Forest sub-sample probe | `python analysis/ch6_if_subsample_probe.py` |
| Ch7.1 — pipeline block diagram (Figure 7.1) | `python analysis/ch7_1_pipeline_figure.py` |
| Ch7.3 — hyperparameter sweeps | `python analysis/ch7_train.py` and `python analysis/ch7_rf_if_sweeps.py` |
| Ch8.1 — error forensics | `python analysis/ch8_error_analysis.py` and `python analysis/ch8_1_rf_if_forensics.py` |
| Ch8.4 — cascade ablation | `python analysis/ch8_4_cascade.py` then `python analysis/ch8_4_cascade_forensics.py` |
| Bonus B.3 — LLM triage evaluation | `python analysis/bonus_b3_llm_eval.py --hf` (requires `HF_TOKEN`) |

⚠️ **Do not run `analysis/ch3_feature_audit.py` to "refresh" the Chapter 3
decision table.** It regenerates `report/ch3_feature_decisions.md` and overwrites
the hand-entered final KEEP/KILL verdicts recorded during the joint feature
review. The audit JSON it consumes is already in `results/ch3_feature_audit.json`.

## A.5 Tests

```bash
python -m pytest tests/ -q       # 6 tests: pipeline contracts, feature schema, naming rules
```

One test enforces a project rule worth naming here: dataset identifiers may not
appear anywhere in `src/*.py` except `ingestion.py`, so no model or feature can
condition on which corpus a command came from (`tests/test_pipeline.py`).
