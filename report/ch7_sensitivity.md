# Chapter 7 — Hyperparameter configuration & sensitivity (Ben)

All configs are explicit (no library defaults). CNN sensitivity sweeps use 4 epochs for tractability; the headline CV/holdout use the full base config below.

## Base configurations

**xgboost** — `{'n_estimators': 400, 'max_depth': 6, 'learning_rate': 0.1, 'subsample': 0.9, 'colsample_bytree': 0.9, 'min_child_weight': 1.0, 'reg_lambda': 1.0, 'scale_pos_weight': 3.0}`  (CV: 5-fold stratified)

**cnn1d** — `{'max_len': 192, 'embed_dim': 32, 'n_filters': 128, 'kernel_sizes': (3, 5, 7), 'dropout': 0.3, 'lr': 0.001, 'epochs': 6, 'batch_size': 256, 'pos_weight': 3.0}`  (CV: 3-fold stratified)

## Headline results (base config)

| model / dataset | CV F1 (mean±std) | CV ROC-AUC | holdout F1 | holdout Recall | holdout FPR |
|---|---|---:|---:|---:|---:|
| xgboost/dataset1 | 0.7978±0.0078 | 0.9382 | 0.7856 | 0.7861 | 0.0717 |
| xgboost/dataset2 | 0.7970±0.0126 | 0.9410 | 0.7557 | 0.7557 | 0.0815 |
| cnn1d/dataset1 | 0.8365±0.0125 | 0.9690 | 0.8495 | 0.8556 | 0.0529 |
| cnn1d/dataset2 | 0.8262±0.0104 | 0.9580 | 0.8249 | 0.8706 | 0.0801 |

## Sensitivity sweeps (one axis at a time, holdout)

### xgboost/dataset1

- **max_depth**: 3→F1 0.784/FPR 0.079, 6→F1 0.786/FPR 0.072, 9→F1 0.787/FPR 0.067, 12→F1 0.783/FPR 0.069
- **learning_rate**: 0.03→F1 0.782/FPR 0.075, 0.1→F1 0.786/FPR 0.072, 0.3→F1 0.775/FPR 0.077
- **n_estimators**: 100→F1 0.782/FPR 0.075, 400→F1 0.786/FPR 0.072, 800→F1 0.782/FPR 0.075
- **scale_pos_weight**: 1.0→F1 0.789/FPR 0.038, 3.0→F1 0.786/FPR 0.072, 6.0→F1 0.765/FPR 0.108

### xgboost/dataset2

- **max_depth**: 3→F1 0.746/FPR 0.101, 6→F1 0.756/FPR 0.081, 9→F1 0.756/FPR 0.078, 12→F1 0.752/FPR 0.075
- **learning_rate**: 0.03→F1 0.763/FPR 0.088, 0.1→F1 0.756/FPR 0.081, 0.3→F1 0.749/FPR 0.081
- **n_estimators**: 100→F1 0.760/FPR 0.091, 400→F1 0.756/FPR 0.081, 800→F1 0.750/FPR 0.079
- **scale_pos_weight**: 1.0→F1 0.759/FPR 0.049, 3.0→F1 0.756/FPR 0.081, 6.0→F1 0.752/FPR 0.114

### cnn1d/dataset1

- **n_filters**: 64→F1 0.820/FPR 0.082, 128→F1 0.829/FPR 0.076, 256→F1 0.834/FPR 0.081
- **dropout**: 0.1→F1 0.843/FPR 0.068, 0.3→F1 0.829/FPR 0.076, 0.5→F1 0.822/FPR 0.076
- **lr**: 0.0005→F1 0.812/FPR 0.078, 0.001→F1 0.829/FPR 0.076, 0.002→F1 0.843/FPR 0.077
- **pos_weight**: 1.0→F1 0.830/FPR 0.033, 3.0→F1 0.829/FPR 0.076, 6.0→F1 0.806/FPR 0.119

### cnn1d/dataset2

- **n_filters**: 64→F1 0.798/FPR 0.091, 128→F1 0.809/FPR 0.091, 256→F1 0.826/FPR 0.074
- **dropout**: 0.1→F1 0.816/FPR 0.089, 0.3→F1 0.809/FPR 0.091, 0.5→F1 0.787/FPR 0.105
- **lr**: 0.0005→F1 0.791/FPR 0.078, 0.001→F1 0.809/FPR 0.091, 0.002→F1 0.833/FPR 0.066
- **pos_weight**: 1.0→F1 0.813/FPR 0.042, 3.0→F1 0.809/FPR 0.091, 6.0→F1 0.736/FPR 0.181

Figures: `report/figures/ch7_sensitivity_xgboost_dataset1.png`, `report/figures/ch7_sensitivity_xgboost_dataset2.png`, `report/figures/ch7_sensitivity_cnn1d_dataset1.png`, `report/figures/ch7_sensitivity_cnn1d_dataset2.png`.