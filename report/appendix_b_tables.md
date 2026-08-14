# Appendix B — Supporting Tables

Generated from the shipped artefacts by `python analysis/appendix_b_tables.py`;
every figure is read from a result file, none is transcribed.

## B.1 Feature importance — consensus ranking

**Table B.1 — Dataset 1: top 8 features by consensus rank.**
`analysis/ch4_ranking.py` scores all 43 features three ways on a held-out
25% of the training split — Random Forest impurity decrease (MDI), XGBoost gain
per split, permutation importance — and *consensus* is the mean of the three
ranks, so lower is better. 4 features receive
exactly zero XGBoost gain here. The full 43-row ranking is the shipped
`report/ch4_feature_ranking.csv`.

<!-- cols: 0.45 1.79 1.01 1.01 1.18 1.06 -->
| # | feature | RF MDI | XGB gain | permutation | consensus |
|---:|---|---:|---:|---:|---:|
| 1 | `n_abs_paths` | 0.1243 | 0.1806 | 0.0342 | 1.67 |
| 2 | `has_shell_bin` | 0.0493 | 0.0974 | 0.0386 | 4.67 |
| 3 | `n_pipes` | 0.0567 | 0.0348 | 0.0340 | 6.00 |
| 4 | `has_dev_null` | 0.0330 | 0.1112 | 0.0195 | 6.33 |
| 5 | `special_ratio` | 0.1225 | 0.0139 | 0.0596 | 8.33 |
| 6 | `n_redirect_out` | 0.0415 | 0.0261 | 0.0116 | 9.00 |
| 7 | `has_lotl_bin` | 0.0216 | 0.0378 | 0.0045 | 10.00 |
| 8 | `digit_ratio` | 0.0609 | 0.0152 | 0.0136 | 10.67 |

**Table B.2 — Dataset 2: top 8 features by consensus rank.** 8 features
receive zero gain — twice Dataset 1's count, and the reason §4.2 treats the
ranking as corpus-specific.

<!-- cols: 0.45 1.79 1.01 1.01 1.18 1.06 -->
| # | feature | RF MDI | XGB gain | permutation | consensus |
|---:|---|---:|---:|---:|---:|
| 1 | `has_fetch_bin` | 0.0583 | 0.0927 | 0.0302 | 3.00 |
| 2 | `n_abs_paths` | 0.0359 | 0.0355 | 0.0168 | 7.67 |
| 3 | `head_is_privesc` | 0.0272 | 0.0586 | 0.0132 | 8.33 |
| 4 | `has_hidden_path` | 0.0304 | 0.0610 | 0.0107 | 8.67 |
| 5 | `len_tokens` | 0.0751 | 0.0212 | 0.0150 | 10.00 |
| 6 | `head_is_shell` | 0.0181 | 0.0670 | 0.0092 | 10.33 |
| 7 | `head_is_lotl` | 0.0254 | 0.0655 | 0.0086 | 10.33 |
| 8 | `has_evasion_tok` | 0.0257 | 0.0431 | 0.0090 | 11.00 |

## B.2 Feature selection — the 68 → 43 funnel

**Table B.3 — Feature funnel: 68 candidates audited,
25 rejected by reason, 43 retained by family.** A candidate fails
the **gate** if it shows no usable effect on either corpus at these sample sizes,
and is **redundant** if it correlates above 0.9 with a retained feature carrying
the same signal; every verdict is recorded with its evidence in
`report/ch3_feature_decisions.md`. Two rejections are results in themselves: the
themed path splits (`n_cred_paths`, `n_proc_paths`, `n_log_paths`) each died while
their lump `n_sensitive_paths` survived, refuting split-covers-lump; and
`has_privesc_bin` is class-neutral while positional `head_is_privesc` passes —
*where* a binary sits matters, *that* it appears does not.

<!-- cols: 1.90 4.60 -->
| stage | features |
|---|---:|
| Candidates implemented and audited | 68 |
| — rejected (25), by reason | no effect (gate) 20 · redundant (ρ > 0.9 cluster) 4 · no effect + redundant 1 |
| **Final feature set** | **43** |
| &nbsp;&nbsp;of which, by family | shape/size 4 · structure/chaining 4 · network/delivery 4 · binary families 6 · A: head/args 6 · B: exec micro-structure 8 · C: paths/filesystem 5 · D: obfuscation 6 |

## B.3 Hyperparameter sensitivity

**Table B.4 — XGBoost: all swept configurations.** Each axis is swept
one-at-a-time from the shipped configuration, training on the full training split
and scoring on the held-out test split; the same holds for Tables B.5 and B.6.

<!-- cols: 1.50 0.70 1.05 1.10 1.05 1.10 -->
| hyperparameter | value | Dataset 1 F1 | Dataset 1 FPR | Dataset 2 F1 | Dataset 2 FPR |
|---|---:|---:|---:|---:|---:|
| `max_depth` | 3 | 0.7837 | 0.0787 | 0.7457 | 0.1010 |
|  | 6 | 0.7856 | 0.0717 | 0.7557 | 0.0815 |
|  | 9 | 0.7873 | 0.0669 | 0.7558 | 0.0780 |
|  | 12 | 0.7831 | 0.0691 | 0.7519 | 0.0745 |
| `learning_rate` | 0.03 | 0.7823 | 0.0752 | 0.7633 | 0.0884 |
|  | 0.1 | 0.7856 | 0.0717 | 0.7557 | 0.0815 |
|  | 0.3 | 0.7747 | 0.0770 | 0.7492 | 0.0815 |
| `n_estimators` | 100 | 0.7823 | 0.0752 | 0.7597 | 0.0905 |
|  | 400 | 0.7856 | 0.0717 | 0.7557 | 0.0815 |
|  | 800 | 0.7823 | 0.0752 | 0.7503 | 0.0794 |
| `scale_pos_weight` | 1.0 | 0.7892 | 0.0385 | 0.7593 | 0.0487 |
|  | 3.0 | 0.7856 | 0.0717 | 0.7557 | 0.0815 |
|  | 6.0 | 0.7647 | 0.1076 | 0.7522 | 0.1135 |

**Table B.5 — 1D-CNN: all swept configurations.**

<!-- cols: 1.50 0.70 1.05 1.10 1.05 1.10 -->
| hyperparameter | value | Dataset 1 F1 | Dataset 1 FPR | Dataset 2 F1 | Dataset 2 FPR |
|---|---:|---:|---:|---:|---:|
| `n_filters` | 64 | 0.8197 | 0.0818 | 0.7976 | 0.0905 |
|  | 128 | 0.8293 | 0.0761 | 0.8086 | 0.0912 |
|  | 256 | 0.8339 | 0.0813 | 0.8265 | 0.0738 |
| `dropout` | 0.1 | 0.8429 | 0.0678 | 0.8156 | 0.0891 |
|  | 0.3 | 0.8293 | 0.0761 | 0.8086 | 0.0912 |
|  | 0.5 | 0.8217 | 0.0756 | 0.7873 | 0.1052 |
| `lr` | 0.0005 | 0.8124 | 0.0778 | 0.7914 | 0.0780 |
|  | 0.001 | 0.8293 | 0.0761 | 0.8086 | 0.0912 |
|  | 0.002 | 0.8432 | 0.0765 | 0.8333 | 0.0662 |
| `pos_weight` | 1.0 | 0.8302 | 0.0328 | 0.8128 | 0.0418 |
|  | 3.0 | 0.8293 | 0.0761 | 0.8086 | 0.0912 |
|  | 6.0 | 0.8060 | 0.1189 | 0.7357 | 0.1811 |

**Table B.6 — Random Forest and Isolation Forest sweeps.** Omitted for space, and
present in `results/ch7_rf_if_sensitivity.json`: `n_estimators` ∈ {50, 200}, which at
fixed `max_depth` move F1 by at most 0.012, and
`contamination=0.05`, which sits below the rise on both corpora.
Contamination moves only Isolation Forest's own cut-off — the shipped pipeline
scores it through the same fixed 0.5 wrapper as every other model, the last row
of each block.

<!-- cols: 1.40 1.90 0.80 0.80 0.80 0.80 -->
| model | configuration | F1 | recall | FPR | ROC-AUC |
|---|---|---:|---:|---:|---:|
| Random Forest, D1 | n_estimators=100, max_depth=None | 0.7843 | 0.7231 | 0.0402 | 0.9306 |
| Random Forest, D1 | n_estimators=500, max_depth=None | 0.7850 | 0.7283 | 0.0424 | 0.9301 |
| Random Forest, D1 | n_estimators=100, max_depth=10 | 0.7840 | 0.7480 | 0.0533 | 0.9233 |
| Random Forest, D1 | n_estimators=500, max_depth=10 | 0.7876 | 0.7520 | 0.0525 | 0.9232 |
| Random Forest, D1 | n_estimators=100, max_depth=20 | 0.7963 | 0.7283 | 0.0337 | 0.9408 |
| Random Forest, D1 | n_estimators=500, max_depth=20 | 0.8006 | 0.7297 | 0.0310 | 0.9418 |
| Random Forest, D2 | n_estimators=100, max_depth=None | 0.7393 | 0.6868 | 0.0571 | 0.9256 |
| Random Forest, D2 | n_estimators=500, max_depth=None | 0.7475 | 0.6952 | 0.0550 | 0.9282 |
| Random Forest, D2 | n_estimators=100, max_depth=10 | 0.7356 | 0.7203 | 0.0794 | 0.9165 |
| Random Forest, D2 | n_estimators=500, max_depth=10 | 0.7311 | 0.7182 | 0.0822 | 0.9184 |
| Random Forest, D2 | n_estimators=100, max_depth=20 | 0.7503 | 0.6931 | 0.0515 | 0.9346 |
| Random Forest, D2 | n_estimators=500, max_depth=20 | 0.7584 | 0.7077 | 0.0529 | 0.9371 |
| Isolation Forest, D1 | contamination=0.1 | 0.6413 | 0.5971 | 0.0883 | 0.8120 |
| Isolation Forest, D1 | contamination=0.2 | 0.6023 | 0.6759 | 0.1893 | 0.8120 |
| Isolation Forest, D1 | contamination=0.3 | 0.5638 | 0.7310 | 0.2873 | 0.8120 |
| Isolation Forest, D1 | **shipped: fixed 0.5 wrapper** | 0.2492 | 0.1457 | 0.0079 | 0.8120 |
| Isolation Forest, D2 | contamination=0.1 | 0.3842 | 0.3048 | 0.0940 | 0.6768 |
| Isolation Forest, D2 | contamination=0.2 | 0.4615 | 0.4760 | 0.1957 | 0.6768 |
| Isolation Forest, D2 | contamination=0.3 | 0.4569 | 0.5595 | 0.2967 | 0.6768 |
| Isolation Forest, D2 | **shipped: fixed 0.5 wrapper** | 0.1431 | 0.0793 | 0.0097 | 0.6768 |

## B.4 Confusion matrices behind every headline score

**Table B.7 — Full confusion matrices, in-domain hold-out.** Dataset 1's test
split is 3,049 rows (762 attack), Dataset 2's is 1,915 (479). At that 1:3 ratio a
do-nothing classifier flagging everything scores F1 0.400 — the floor every model
here must beat.

<!-- cols: 0.90 1.17 0.45 0.45 0.45 0.45 0.80 0.69 0.58 0.56 -->
| dataset | model | TN | FP | FN | TP | precision | recall | F1 | FPR |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dataset 1 | XGBoost-hybrid | 2192 | 95 | 94 | 668 | 0.8755 | 0.8766 | 0.8761 | 0.0415 |
|  | 1D-CNN | 2160 | 127 | 91 | 671 | 0.8409 | 0.8806 | 0.8603 | 0.0555 |
|  | Random Forest | 2210 | 77 | 207 | 555 | 0.8782 | 0.7283 | 0.7963 | 0.0337 |
|  | XGBoost | 2123 | 164 | 163 | 599 | 0.7851 | 0.7861 | 0.7856 | 0.0717 |
|  | Isolation Forest | 2269 | 18 | 651 | 111 | 0.8605 | 0.1457 | 0.2492 | 0.0079 |
| Dataset 2 | XGBoost-hybrid | 1365 | 71 | 74 | 405 | 0.8508 | 0.8455 | 0.8482 | 0.0494 |
|  | 1D-CNN | 1340 | 96 | 64 | 415 | 0.8121 | 0.8664 | 0.8384 | 0.0669 |
|  | Random Forest | 1362 | 74 | 145 | 334 | 0.8186 | 0.6973 | 0.7531 | 0.0515 |
|  | XGBoost | 1319 | 117 | 117 | 362 | 0.7557 | 0.7557 | 0.7557 | 0.0815 |
|  | Isolation Forest | 1422 | 14 | 441 | 38 | 0.7308 | 0.0793 | 0.1431 | 0.0097 |
