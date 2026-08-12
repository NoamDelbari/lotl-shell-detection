# Appendix B — Frameworks and Hardware Environment Specifications

The project was developed and run on **two independent machines**. This matters
for reading the results: the deep-learning model was trained on Apple-silicon
GPU while the tree and anomaly models were trained on CPU, so the two halves of
the results table were not produced on the same hardware. Nothing in the
comparison depends on it — every model is seeded and the tree models are
deterministic under that seed — but the report should not imply a single
environment.

**Table B.1 — Execution environments.**

| | **Environment A** (Ben Volovelsky) | **Environment B** (Noam Delbari) |
|---|---|---|
| OS | macOS, Apple M-series | Windows 11 Home (build 26200) |
| Compute | Apple-silicon GPU via Metal | CPU only |
| Accelerator used | PyTorch **MPS** backend (`torch.device("mps")`) for the 1D-CNN | none — `torch` CPU wheel |
| Python | 3.11 | 3.11.9 |
| Work produced here | Pipeline skeleton, `xgboost`, `xgboost_hybrid`, `cnn1d`, the Ch7 sweeps for those models, Figure 7.1 source | 43-feature selection, Ch3 EDA, `random_forest`, `isolation_forest`, their Ch7 sweeps, Ch6, Ch8.1/8.3/8.4, all regenerated result files |

**Table B.2 — Frameworks and libraries.** Versions are those of Environment B,
where the shipped `results/` files were last regenerated.

| Package | Version | Role |
|---|---|---|
| Python | 3.11.9 | runtime |
| numpy | 2.3.5 | numerics |
| pandas | 2.3.3 | data handling |
| scikit-learn | 1.8.0 | RandomForest, IsolationForest, TF-IDF, StandardScaler, StratifiedKFold, metrics |
| xgboost | 3.2.0 | gradient-boosted trees (`xgboost`, `xgboost_hybrid`) |
| imbalanced-learn | 0.14.2 | `ImbPipeline` — leakage-safe pipeline used by every model |
| torch | 2.11.0 | 1D-CNN (MPS in Environment A, CPU in Environment B) |
| scipy | 1.11+ | statistics for the Ch3 feature audit |
| matplotlib / seaborn | 3.10.8 / 0.13+ | all figures |
| huggingface-hub | 0.24+ | bonus LLM triage layer (optional; needs `HF_TOKEN`) |

**Reproducibility.** `SEED = 42` is set once in `src/__init__.py` and threaded
through every model builder, the k-fold splitter and the dataset build. The
XGBoost, RandomForest and IsolationForest results are bit-reproducible from a
clean checkout on either machine. The 1D-CNN is reproducible up to the usual
floating-point non-determinism of GPU kernels, so its figures may differ in the
last decimal between Environment A and Environment B.

**Note on `requirements.txt`.** The shipped file specifies minimum versions
(`>=`) rather than exact pins, so that one file installs on both macOS/MPS and
Windows/CPU. The exact versions the shipped results were produced under are the
ones tabulated above.
