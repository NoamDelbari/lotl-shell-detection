# Chapter 7 — Hyperparameter configuration & sensitivity (Ben)

All configs are explicit (no library defaults). CNN sensitivity sweeps use 4 epochs for tractability; the headline CV/holdout use the full base config below.

## Base configurations

**xgboost** — `{'n_estimators': 400, 'max_depth': 6, 'learning_rate': 0.1, 'subsample': 0.9, 'colsample_bytree': 0.9, 'min_child_weight': 1.0, 'reg_lambda': 1.0, 'scale_pos_weight': 3.0}`  (CV: 5-fold stratified)

**cnn1d** — `{'max_len': 192, 'embed_dim': 32, 'n_filters': 128, 'kernel_sizes': (3, 5, 7), 'dropout': 0.3, 'lr': 0.001, 'epochs': 6, 'batch_size': 256, 'pos_weight': 3.0}`  (CV: 3-fold stratified)

## Headline results (base config)

| model / dataset | CV F1 (mean±std) | CV ROC-AUC | holdout F1 | holdout Recall | holdout FPR |
|---|---|---:|---:|---:|---:|
| xgboost/dataset1 | 0.7647±0.0149 | 0.9270 | 0.7599 | 0.7769 | 0.0892 |
| xgboost/dataset2 | 0.7687±0.0167 | 0.9283 | 0.7363 | 0.7578 | 0.1003 |
| cnn1d/dataset1 | 0.8362±0.0123 | 0.9691 | 0.8512 | 0.8556 | 0.0516 |
| cnn1d/dataset2 | 0.8263±0.0105 | 0.9580 | 0.8238 | 0.8685 | 0.0801 |

## Sensitivity sweeps (one axis at a time, holdout)

### xgboost/dataset1

- **max_depth**: 3→F1 0.752/FPR 0.117, 6→F1 0.760/FPR 0.089, 9→F1 0.760/FPR 0.074, 12→F1 0.753/FPR 0.074
- **learning_rate**: 0.03→F1 0.754/FPR 0.108, 0.1→F1 0.760/FPR 0.089, 0.3→F1 0.747/FPR 0.083
- **n_estimators**: 100→F1 0.749/FPR 0.112, 400→F1 0.760/FPR 0.089, 800→F1 0.760/FPR 0.079
- **scale_pos_weight**: 1.0→F1 0.760/FPR 0.051, 3.0→F1 0.760/FPR 0.089, 6.0→F1 0.751/FPR 0.126

### xgboost/dataset2

- **max_depth**: 3→F1 0.725/FPR 0.116, 6→F1 0.736/FPR 0.100, 9→F1 0.729/FPR 0.095, 12→F1 0.725/FPR 0.093
- **learning_rate**: 0.03→F1 0.737/FPR 0.107, 0.1→F1 0.736/FPR 0.100, 0.3→F1 0.721/FPR 0.100
- **n_estimators**: 100→F1 0.722/FPR 0.116, 400→F1 0.736/FPR 0.100, 800→F1 0.724/FPR 0.099
- **scale_pos_weight**: 1.0→F1 0.733/FPR 0.053, 3.0→F1 0.736/FPR 0.100, 6.0→F1 0.716/FPR 0.140

### cnn1d/dataset1

- **n_filters**: 64→F1 0.819/FPR 0.081, 128→F1 0.829/FPR 0.076, 256→F1 0.832/FPR 0.081
- **dropout**: 0.1→F1 0.843/FPR 0.067, 0.3→F1 0.829/FPR 0.076, 0.5→F1 0.821/FPR 0.076
- **lr**: 0.0005→F1 0.812/FPR 0.078, 0.001→F1 0.829/FPR 0.076, 0.002→F1 0.844/FPR 0.076
- **pos_weight**: 1.0→F1 0.832/FPR 0.032, 3.0→F1 0.829/FPR 0.076, 6.0→F1 0.807/FPR 0.118

### cnn1d/dataset2

- **n_filters**: 64→F1 0.798/FPR 0.091, 128→F1 0.809/FPR 0.091, 256→F1 0.826/FPR 0.074
- **dropout**: 0.1→F1 0.815/FPR 0.090, 0.3→F1 0.809/FPR 0.091, 0.5→F1 0.788/FPR 0.104
- **lr**: 0.0005→F1 0.791/FPR 0.078, 0.001→F1 0.809/FPR 0.091, 0.002→F1 0.834/FPR 0.067
- **pos_weight**: 1.0→F1 0.814/FPR 0.041, 3.0→F1 0.809/FPR 0.091, 6.0→F1 0.736/FPR 0.180

Figures: `report/figures/ch7_sensitivity_*.png`.