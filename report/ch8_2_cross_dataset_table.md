# Chapter 8.2 — Cross-dataset variance (all four models)

In-distribution (train and test on the same dataset's splits) and cross-dataset transfer. Diagonal = in-distribution; off-diagonal = transfer. Metrics at threshold 0.5.

| model | train → test | Accuracy | Precision | Recall/DR | FPR | F1 | ROC-AUC |
|---|---|---:|---:|---:|---:|---:|---:|
| xgboost | dataset1→dataset1 (in-dist) | 0.877 | 0.744 | 0.777 | 0.089 | 0.760 | 0.919 |
| xgboost | dataset1→dataset2 (transfer) | 0.636 | 0.368 | 0.633 | 0.363 | 0.465 | 0.686 |
| xgboost | dataset2→dataset1 (transfer) | 0.741 | 0.454 | 0.182 | 0.073 | 0.260 | 0.553 |
| xgboost | dataset2→dataset2 (in-dist) | 0.864 | 0.716 | 0.758 | 0.100 | 0.736 | 0.908 |
| xgboost_hybrid | dataset1→dataset1 (in-dist) | 0.936 | 0.862 | 0.885 | 0.047 | 0.873 | 0.978 |
| xgboost_hybrid | dataset1→dataset2 (transfer) | 0.696 | 0.431 | 0.668 | 0.295 | 0.524 | 0.761 |
| xgboost_hybrid | dataset2→dataset1 (transfer) | 0.777 | 0.782 | 0.151 | 0.014 | 0.253 | 0.657 |
| xgboost_hybrid | dataset2→dataset2 (in-dist) | 0.922 | 0.854 | 0.831 | 0.047 | 0.842 | 0.969 |
| cnn1d | dataset1→dataset1 (in-dist) | 0.928 | 0.839 | 0.882 | 0.056 | 0.860 | 0.975 |
| cnn1d | dataset1→dataset2 (transfer) | 0.698 | 0.435 | 0.697 | 0.302 | 0.536 | 0.769 |
| cnn1d | dataset2→dataset1 (transfer) | 0.792 | 0.786 | 0.231 | 0.021 | 0.357 | 0.733 |
| cnn1d | dataset2→dataset2 (in-dist) | 0.916 | 0.812 | 0.866 | 0.067 | 0.838 | 0.964 |
| random_forest | dataset1→dataset1 (in-dist) | 0.886 | 0.836 | 0.677 | 0.044 | 0.748 | 0.925 |
| random_forest | dataset1→dataset2 (transfer) | 0.720 | 0.446 | 0.501 | 0.208 | 0.472 | 0.690 |
| random_forest | dataset2→dataset1 (transfer) | 0.755 | 0.556 | 0.104 | 0.028 | 0.175 | 0.614 |
| random_forest | dataset2→dataset2 (in-dist) | 0.876 | 0.784 | 0.695 | 0.064 | 0.737 | 0.913 |
| isolation_forest | dataset1→dataset1 (in-dist) | 0.769 | 0.782 | 0.104 | 0.010 | 0.183 | 0.748 |
| isolation_forest | dataset1→dataset2 (transfer) | 0.736 | 0.299 | 0.042 | 0.033 | 0.073 | 0.650 |
| isolation_forest | dataset2→dataset1 (transfer) | 0.759 | 0.717 | 0.056 | 0.007 | 0.105 | 0.714 |
| isolation_forest | dataset2→dataset2 (in-dist) | 0.749 | 0.481 | 0.027 | 0.010 | 0.051 | 0.654 |

**Reading the table (diagnosis seed):** a large diagonal→off-diagonal drop is either *Environmental Distribution Shift* (curated Dataset 1 vs real honeypot Dataset 2 — different attack surface form) or *Model Overfitting* to the training source. The asymmetry (D1→D2 vs D2→D1) tells them apart: if D1→D2 >> D2→D1, the curated set has broader coverage and the honeypot model is narrow (overfit), not just shifted.