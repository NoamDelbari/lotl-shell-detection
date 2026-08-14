# Appendix A — Code Execution Instructions

Every result reproduces end-to-end from the shipped repository. All scripts are seeded (`SEED = 42`, `src/__init__.py`), so a rerun regenerates the shipped files exactly.

## Environment setup

```
pip install -r requirements.txt
```

## Rebuild the datasets (optional — shipped under `dataset/`)

```
cd scripts
python build_dataset.py         # rebuilds both datasets from public sources
python evaluate_baseline.py     # char n-gram TF-IDF + logistic-regression baseline
```

## Train and evaluate the five models

```
python main.py all                                          # every model x both datasets
python main.py cv       --model xgboost --dataset dataset1  # stratified k-fold CV
python main.py holdout  --model cnn1d   --dataset dataset2  # train split -> test split
python main.py transfer --model xgboost --train dataset1 --test dataset2   # cross-dataset
```

## Regenerate the report artefacts (figures, tables, JSON)

```
python analysis/ch3_eda.py            # Ch3 EDA figures + feature justification
python analysis/ch4_ranking.py        # Ch4 tree-based feature-ranking charts
python analysis/ch7_train.py          # Ch7 CV + hyperparameter sensitivity
python analysis/ch8_error_analysis.py # Ch8.1 forensics + 8.2 cross-dataset table
python analysis/ch8_4_cascade.py      # Ch8.4 hybrid cascade ensemble
```

## Bonus — LLM triage layer

```
python analysis/bonus_b3_llm_eval.py         # offline stub arbitrator
python analysis/bonus_b3_llm_eval.py --hf     # real Llama-3.1-8B via Hugging Face (needs HF_TOKEN)
```

The B.3 results in this report were produced with a fully-local Llama-3.1-8B through Ollama (`src/llm_triage.py` `ollama_arbitrator()`, endpoint `http://localhost:11434`). No secret is stored in the repo — a Hugging Face token, if used, is read from the `HF_TOKEN` environment variable and is never committed.

## Guardrail tests

```
python tests/test_pipeline.py         # no-leakage + dataset-agnostic contract checks
```
