# Chapter 8.2 — Cross-dataset variance (all 5 registry models)

In-distribution (train and test on the same dataset's splits) and cross-dataset transfer. Diagonal = in-distribution; off-diagonal = transfer. Metrics at threshold 0.5.

| model | train → test | Accuracy | Precision | Recall/DR | FPR | F1 | ROC-AUC |
|---|---|---:|---:|---:|---:|---:|---:|
| xgboost | dataset1→dataset1 (in-dist) | 0.893 | 0.785 | 0.786 | 0.072 | 0.786 | 0.932 |
| xgboost | dataset1→dataset2 (transfer) | 0.662 | 0.395 | 0.662 | 0.338 | 0.495 | 0.722 |
| xgboost | dataset2→dataset1 (transfer) | 0.750 | 0.500 | 0.154 | 0.051 | 0.235 | 0.597 |
| xgboost | dataset2→dataset2 (in-dist) | 0.878 | 0.756 | 0.756 | 0.081 | 0.756 | 0.930 |
| xgboost_hybrid | dataset1→dataset1 (in-dist) | 0.938 | 0.875 | 0.877 | 0.042 | 0.876 | 0.979 |
| xgboost_hybrid | dataset1→dataset2 (transfer) | 0.709 | 0.445 | 0.662 | 0.276 | 0.532 | 0.767 |
| xgboost_hybrid | dataset2→dataset1 (transfer) | 0.779 | 0.766 | 0.168 | 0.017 | 0.276 | 0.686 |
| xgboost_hybrid | dataset2→dataset2 (in-dist) | 0.924 | 0.851 | 0.846 | 0.049 | 0.848 | 0.968 |
| cnn1d | dataset1→dataset1 (in-dist) | 0.929 | 0.841 | 0.881 | 0.056 | 0.860 | 0.975 |
| cnn1d | dataset1→dataset2 (transfer) | 0.703 | 0.441 | 0.697 | 0.295 | 0.540 | 0.770 |
| cnn1d | dataset2→dataset1 (transfer) | 0.792 | 0.787 | 0.232 | 0.021 | 0.359 | 0.733 |
| cnn1d | dataset2→dataset2 (in-dist) | 0.916 | 0.812 | 0.866 | 0.067 | 0.838 | 0.964 |
| random_forest | dataset1→dataset1 (in-dist) | 0.907 | 0.878 | 0.728 | 0.034 | 0.796 | 0.940 |
| random_forest | dataset1→dataset2 (transfer) | 0.752 | 0.504 | 0.526 | 0.173 | 0.515 | 0.720 |
| random_forest | dataset2→dataset1 (transfer) | 0.753 | 0.534 | 0.083 | 0.024 | 0.143 | 0.662 |
| random_forest | dataset2→dataset2 (in-dist) | 0.886 | 0.819 | 0.697 | 0.052 | 0.753 | 0.937 |
| isolation_forest | dataset1→dataset1 (in-dist) | 0.781 | 0.860 | 0.146 | 0.008 | 0.249 | 0.812 |
| isolation_forest | dataset1→dataset2 (transfer) | 0.760 | 0.656 | 0.084 | 0.015 | 0.148 | 0.677 |
| isolation_forest | dataset2→dataset1 (transfer) | 0.779 | 0.843 | 0.140 | 0.009 | 0.241 | 0.787 |
| isolation_forest | dataset2→dataset2 (in-dist) | 0.762 | 0.731 | 0.079 | 0.010 | 0.143 | 0.677 |

**Reading the table (diagnosis seed):** a large diagonal→off-diagonal drop is either *Environmental Distribution Shift* (curated Dataset 1 vs real honeypot Dataset 2 — different attack surface form) or *Model Overfitting* to the training source. The asymmetry (D1→D2 vs D2→D1) tells them apart: if D1→D2 >> D2→D1, the curated set has broader coverage and the honeypot model is narrow (overfit), not just shifted.