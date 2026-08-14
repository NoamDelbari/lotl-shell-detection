# Pipeline & Reproduction Guide (Ch7 + Appendix A)

Modular, dataset-agnostic detection pipeline for the four models. This is the
"Code Execution Instructions" appendix and the Ch7 architecture write-up in one
place. Owner: Ben (skeleton + XGBoost + 1D-CNN); Noam owns Random Forest +
Isolation Forest and the live LLM layer.

## Architecture (Ch7.1 — the strict module sequence)

```
                 ┌─────────────────────────────────────────────────────────┐
 raw CSV  ──────▶│  src/ingestion.py   (ONLY dataset-aware module)          │
 (dataset-       │    load(name) -> standard frame [command, label, source] │
  specific)      └───────────────────────┬─────────────────────────────────┘
                                          │  raw command strings + labels
                                          ▼
        ┌──────────────────────────────────────────────────────────────────┐
        │  src/preprocessing.py  (dataset-agnostic, fit INSIDE each fold)    │
        │    EngineeredFeatures  -> src/features.featurize()  (XGB/RF/IF)    │
        │    CharSequenceEncoder -> char-index matrix          (1D-CNN)      │
        │    StandardScaler / imblearn sampler  (learned on train fold only) │
        └───────────────────────┬──────────────────────────────────────────┘
                                 ▼
        ┌──────────────────────────────────────────────────────────────────┐
        │  src/models.py   XGBoost · 1D-CNN · RandomForest · IsolationForest │
        │    each = sklearn/imblearn Pipeline taking RAW strings as X        │
        └───────────────────────┬──────────────────────────────────────────┘
                                 ▼
        ┌──────────────────────────────────────────────────────────────────┐
        │  src/evaluation.py   stratified k-fold CV · P/R/F1/ROC-AUC/FPR ·   │
        │                      PR-AUC · TPR@low-FPR · per-source breakdown   │
        └───────────────────────┬──────────────────────────────────────────┘
                                 ▼
        src/ensemble.py  (Ch8.4 cascade)  +  src/llm_triage.py  (bonus)
```

**Dataset Dependency Rule (graded).** Only `src/ingestion.py` names a dataset.
Every downstream module consumes the standard frame and runs unchanged when the
dataset is swapped — register a third dataset in `ingestion._REGISTRY` and the
whole pipeline works with no other edit.

**No leakage (graded).** Feature extraction, scaling, and any imbalance sampler
live *inside* each model's `Pipeline`, so `cross_validate()` fits them on the
training fold of every split only. Nothing is fit on the full data and sliced.

**Imbalance.** Cost-sensitive by default: XGBoost `scale_pos_weight`, forests
`class_weight`, CNN class-weighted cross-entropy. imblearn's Pipeline is used
throughout so switching any model to SMOTE is a one-line, still-leakage-safe
change.

## Quick start

```bash
pip install -r requirements.txt

# one model, one dataset, stratified k-fold CV
python main.py cv --model xgboost --dataset dataset1

# train split -> test split, with per-source breakdown
python main.py holdout --model cnn1d --dataset dataset2

# cross-dataset transfer (Ch8.2)
python main.py transfer --model xgboost --train dataset1 --test dataset2

# every model x every dataset
python main.py all
```

## Reproduce the report artifacts

```bash
python analysis/ch3_eda.py            # Ch3 EDA figures + feature justification
python analysis/ch4_ranking.py        # Ch4 tree-based ranking + charts
python analysis/ch7_train.py          # Ch7 CV + hyperparameter sensitivity
python analysis/ch8_error_analysis.py # Ch8.1 forensics + 8.2 cross-dataset table
python analysis/ch8_4_cascade.py      # Ch8.4 cascade (runs the hybrid ensemble)
python analysis/bonus_b3_llm_eval.py  # Bonus B.3 (offline stub arbitrator)
python analysis/bonus_b3_llm_eval.py --hf   # Bonus B.3 with real HF Llama (needs HF_TOKEN)

python tests/test_pipeline.py         # guardrail tests: no-leakage + dataset-agnostic
```

## Models

| name (`--model`) | paradigm | owner | headline in-dist F1 (D1 / D2) |
|---|---|---|---|
| `xgboost_hybrid` | traditional supervised (engineered ∪ char n-grams) | Ben | **0.873 / 0.842** |
| `cnn1d` | deep learning (char sequences) | Ben | 0.860 / 0.838 |
| `xgboost` | traditional supervised (engineered only, interpretable) | Ben | 0.760 / 0.736 |
| `random_forest` | traditional supervised | Noam | 0.748 / 0.737 |
| `isolation_forest` | unsupervised anomaly | Noam | 0.183 / 0.051 |

`xgboost_hybrid` is the headline traditional model: char n-gram TF-IDF (Ch2 /
ShellCore) unioned with the engineered block lifts F1 from ~0.76 to ~0.87 while
keeping the engineered features available for the Ch4 importance story. The
Ch8.4 cascade chains Isolation Forest (stage 1) → `xgboost_hybrid` (stage 2) →
LLM arbitration (stage 3), with the stage-1 threshold auto-calibrated to retain
99% of attacks.

All scripts are seeded (`SEED=42`, `src/__init__.py`). Figures land in
`report/figures/`, machine-readable results in `results/`, report drafts in
`report/`.

## Environment

Python 3.9+. Key libs: scikit-learn, xgboost, imbalanced-learn, torch (CPU is
fine — the 1D-CNN is sized for it), scipy, matplotlib, seaborn. The bonus LLM
layer additionally needs `huggingface-hub` and an `HF_TOKEN` env var (never
commit the token).
