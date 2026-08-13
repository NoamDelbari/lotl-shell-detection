# Appendix B — Frameworks and Hardware Environment

## Software frameworks

Python 3.9+. Lower bounds are pinned in `requirements.txt`.

| Library | Version | Role in the pipeline |
|---|---|---|
| scikit-learn | ≥ 1.4 | pipelines, Random Forest, Isolation Forest, metrics, CV |
| XGBoost | ≥ 2.1 | gradient-boosted trees (engineered + hybrid) |
| PyTorch | ≥ 2.2 | character-level 1D-CNN |
| imbalanced-learn | ≥ 0.12 | leakage-safe SMOTE / sampling inside the Pipeline |
| numpy / pandas / scipy | ≥ 1.26 / ≥ 2.1 / ≥ 1.11 | data handling and statistics |
| matplotlib / seaborn | ≥ 3.8 / ≥ 0.13 | EDA, ranking, and sensitivity figures |
| huggingface-hub | ≥ 0.24 | optional Hugging Face LLM inference |
| Ollama (`llama3.1:8b`) | — | local LLM arbitration, Bonus B.3 |

## Hardware environments

Results were produced on two machines. The tree models (Random Forest, Isolation Forest, XGBoost) are deterministic under `SEED = 42`, so which machine ran them does not affect reproducibility of those numbers.

- **Environment A — Ben:** macOS, Apple M3 Pro. The 1D-CNN trains on the GPU via `torch.device("mps")`; the local Ollama `llama3.1:8b` arbitrator (Bonus B.3) ran on the GPU at ≈ 11 s per call. Produced: XGBoost-hybrid, 1D-CNN, the TF-IDF baseline, cross-dataset transfer, the cascade, Ch7 XGBoost/CNN sensitivity, and Ch8 error forensics.
- **Environment B — Noam:** Windows 11, CPU only. Produced: Random Forest, Isolation Forest, the Ch3 EDA and Ch4 ranking figures, the Ch6 sub-sample probe, the Ch7 RF/IF sweeps, and the Ch8 RF/IF forensics.

Supporting exploration figures (class balance, variance-by-label, correlation heatmaps, feature-importance bars, sensitivity grids, confusion matrices for all five models on both datasets) ship in `report/figures/` inside the submission ZIP.
