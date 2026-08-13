## 7.2 Class-imbalance strategy and leakage control

Both corpora are deliberately imbalanced at 1 attack : 3 benign (25% positive), so a detector that flags everything scores only F1 = 0.400 — the do-nothing floor every result is measured against. The pipeline counters this **cost-sensitively rather than by resampling**, applied identically across models:

- **XGBoost / XGBoost-hybrid** — `scale_pos_weight` = train-fold negative/positive ratio, so a missed attack costs the loss as much as three false alarms.
- **Random Forest** — `class_weight="balanced_subsample"`, re-weighting the Gini split criterion per bootstrap.
- **1D-CNN** — class-weighted cross-entropy at the same ratio.
- **Isolation Forest** — fit on benign rows only, so class prior does not apply; its operating point is set by `stage1_retain_recall`, not by resampling.

Cost-sensitive weighting is preferred over SMOTE because the positive class is *semantically diverse* (reverse shells, download cradles, enumeration bursts), not merely under-sampled noise — synthesising interpolated "average attacks" would blur the very feature conjunctions the models depend on. The pipeline stays SMOTE-ready: any sampler lives inside an `imbalanced-learn` `Pipeline`, fit **on the training fold only** within each CV split and never on the test fold — the same leakage-safe contract that governs the scaler (Chapter 5.3).
