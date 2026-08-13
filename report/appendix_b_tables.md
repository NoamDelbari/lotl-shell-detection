# Appendix B — Supporting Tables

Generated from the shipped artefacts by `python analysis/appendix_b_tables.py`;
every figure here is read from a result file, none is transcribed. These are the
tables the body chapters summarise but do not print in full.

## B.1 Feature importance — full consensus ranking

`analysis/ch4_ranking.py` scores all 43 features three ways on a held-out
25% of the training split: Random Forest impurity decrease (MDI), XGBoost average
gain per split, and permutation importance measured on the Random Forest.
*Consensus* is the mean of the three per-view ranks, so lower is better. Chapter 4
discusses the top eight and the disagreement between the three views; the top
fifteen on each corpus follow.

**Table B.1 — Dataset 1: top 15 features by consensus rank.** 4 of
the 43 features receive exactly zero XGBoost gain on this corpus.

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
| 9 | `head_is_lotl` | 0.0187 | 0.0452 | 0.0026 | 11.33 |
| 10 | `max_token_len` | 0.0868 | 0.0106 | 0.0125 | 12.33 |
| 11 | `len_tokens` | 0.0533 | 0.0152 | 0.0034 | 14.00 |
| 12 | `mean_token_len` | 0.0771 | 0.0099 | 0.0040 | 14.33 |
| 13 | `n_sensitive_paths` | 0.0259 | 0.0198 | 0.0032 | 14.33 |
| 14 | `n_flags` | 0.0335 | 0.0124 | 0.0062 | 14.67 |
| 15 | `len_chars` | 0.0734 | 0.0098 | 0.0037 | 15.33 |

**Table B.2 — Dataset 2: top 15 features by consensus rank.** 8 of
the 43 features receive exactly zero XGBoost gain here — twice Dataset 1's
count, and the reason §4.2 treats the ranking as corpus-specific.

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
| 9 | `len_chars` | 0.1077 | 0.0127 | 0.0296 | 11.00 |
| 10 | `has_shell_bin` | 0.0181 | 0.0692 | 0.0052 | 11.33 |
| 11 | `digit_ratio` | 0.0849 | 0.0140 | 0.0242 | 12.33 |
| 12 | `special_ratio` | 0.1012 | 0.0096 | 0.0288 | 12.33 |
| 13 | `mean_token_len` | 0.0934 | 0.0110 | 0.0162 | 13.33 |
| 14 | `n_flags` | 0.0352 | 0.0149 | 0.0129 | 14.67 |
| 15 | `has_url` | 0.0208 | 0.0222 | 0.0033 | 15.00 |

## B.2 Feature selection — what was rejected and why

Chapter 3 audits 68 candidate features on the training
split only and keeps 43. Two rejection rules: a candidate fails the
**gate** if it shows no usable effect on either corpus at these sample sizes, and
it is cut as **redundant** if its absolute correlation with a retained feature
exceeds 0.9 and that feature carries the same signal. Every verdict was ruled
jointly and is recorded with its evidence in `report/ch3_feature_decisions.md`.

**Table B.3 — Feature funnel.**

| stage | features |
|---|---:|
| Candidates implemented and audited | 68 |
| — rejected: no effect (gate) | 20 |
| — rejected: redundant (ρ > 0.9 cluster) | 4 |
| — rejected: no effect + redundant | 1 |
| **Final feature set** | **43** |
| &nbsp;&nbsp;&nbsp;&nbsp;of which shape/size | 4 |
| &nbsp;&nbsp;&nbsp;&nbsp;of which structure/chaining | 4 |
| &nbsp;&nbsp;&nbsp;&nbsp;of which network/delivery | 4 |
| &nbsp;&nbsp;&nbsp;&nbsp;of which binary families | 6 |
| &nbsp;&nbsp;&nbsp;&nbsp;of which A: head/args | 6 |
| &nbsp;&nbsp;&nbsp;&nbsp;of which B: exec micro-structure | 8 |
| &nbsp;&nbsp;&nbsp;&nbsp;of which C: paths/filesystem | 5 |
| &nbsp;&nbsp;&nbsp;&nbsp;of which D: obfuscation | 6 |

**Table B.4 — The 25 rejected candidates.** Rejection is itself a
result: the themed path splits (`n_cred_paths`, `n_proc_paths`, `n_log_paths`)
each died while their lump `n_sensitive_paths` survived, refuting the
split-covers-lump hypothesis; and `has_privesc_bin` is class-neutral while
positional `head_is_privesc` passes — *where* a binary sits matters, *that* it
appears does not.

| candidate | why rejected | signal absorbed by |
|---|---|---|
| `token_entropy` | redundant (ρ > 0.9 cluster) | `len_tokens` |
| `char_entropy` | redundant (ρ > 0.9 cluster) | `len_chars` |
| `n_redirect_in` | no effect (gate) | — |
| `n_semicolons` | no effect (gate) | — |
| `n_and_or` | no effect (gate) | — |
| `n_backticks_subshell` | no effect (gate) | — |
| `n_parens` | no effect (gate) | — |
| `n_braces` | no effect (gate) | — |
| `n_ipv4` | no effect (gate) | `has_ipv4` |
| `has_public_ip` | redundant (ρ > 0.9 cluster) | `has_ipv4` |
| `n_ports` | no effect (gate) | — |
| `n_enum_bins` | no effect + redundant | `has_enum_bin` |
| `has_privesc_bin` | no effect (gate) | — |
| `head_is_fetch` | redundant (ρ > 0.9 cluster) | `has_fetch_bin` |
| `head_is_enum` | no effect (gate) | — |
| `n_assign_prefix` | no effect (gate) | — |
| `n_cred_paths` | no effect (gate) | `n_sensitive_paths` |
| `n_proc_paths` | no effect (gate) | `n_sensitive_paths` |
| `n_log_paths` | no effect (gate) | `n_sensitive_paths` |
| `has_eval` | no effect (gate) | — |
| `nonprintable_ratio` | no effect (gate) | — |
| `n_var_assignments` | no effect (gate) | — |
| `n_var_expansions` | no effect (gate) | — |
| `n_backslash` | no effect (gate) | — |
| `subshell_depth` | no effect (gate) | — |

## B.3 Hyperparameter sensitivity — every swept configuration

Chapter 7.3 reports the headline conclusion; these are the runs behind it. Each
axis is swept one-at-a-time from the shipped configuration, training on the full
training split and scoring on the held-out test split.

**Table B.5 — XGBoost: all swept configurations.**

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

**Table B.6 — 1D-CNN: all swept configurations.**

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

**Table B.7 — Random Forest and Isolation Forest sweeps.** Isolation Forest's
`contamination` moves only its own internal cut-off; the shipped pipeline scores
it through the same fixed 0.5 wrapper as every other model, which is the last row
of each block and the number `results/summary.json` reports.

| model | dataset | configuration | F1 | recall | FPR | ROC-AUC |
|---|---|---|---:|---:|---:|---:|
| Random Forest | Dataset 1 | n_estimators=50, max_depth=None | 0.7806 | 0.7192 | 0.0411 | 0.9290 |
| Random Forest | Dataset 1 | n_estimators=100, max_depth=None | 0.7843 | 0.7231 | 0.0402 | 0.9306 |
| Random Forest | Dataset 1 | n_estimators=200, max_depth=None | 0.7845 | 0.7310 | 0.0442 | 0.9308 |
| Random Forest | Dataset 1 | n_estimators=500, max_depth=None | 0.7850 | 0.7283 | 0.0424 | 0.9301 |
| Random Forest | Dataset 1 | n_estimators=50, max_depth=10 | 0.7801 | 0.7402 | 0.0525 | 0.9237 |
| Random Forest | Dataset 1 | n_estimators=100, max_depth=10 | 0.7840 | 0.7480 | 0.0533 | 0.9233 |
| Random Forest | Dataset 1 | n_estimators=200, max_depth=10 | 0.7868 | 0.7507 | 0.0525 | 0.9231 |
| Random Forest | Dataset 1 | n_estimators=500, max_depth=10 | 0.7876 | 0.7520 | 0.0525 | 0.9232 |
| Random Forest | Dataset 1 | n_estimators=50, max_depth=20 | 0.7926 | 0.7297 | 0.0372 | 0.9386 |
| Random Forest | Dataset 1 | n_estimators=100, max_depth=20 | 0.7963 | 0.7283 | 0.0337 | 0.9408 |
| Random Forest | Dataset 1 | n_estimators=200, max_depth=20 | 0.7988 | 0.7270 | 0.0310 | 0.9414 |
| Random Forest | Dataset 1 | n_estimators=500, max_depth=20 | 0.8006 | 0.7297 | 0.0310 | 0.9418 |
| Random Forest | Dataset 2 | n_estimators=50, max_depth=None | 0.7419 | 0.6931 | 0.0585 | 0.9251 |
| Random Forest | Dataset 2 | n_estimators=100, max_depth=None | 0.7393 | 0.6868 | 0.0571 | 0.9256 |
| Random Forest | Dataset 2 | n_estimators=200, max_depth=None | 0.7435 | 0.6868 | 0.0536 | 0.9271 |
| Random Forest | Dataset 2 | n_estimators=500, max_depth=None | 0.7475 | 0.6952 | 0.0550 | 0.9282 |
| Random Forest | Dataset 2 | n_estimators=50, max_depth=10 | 0.7430 | 0.7453 | 0.0870 | 0.9160 |
| Random Forest | Dataset 2 | n_estimators=100, max_depth=10 | 0.7356 | 0.7203 | 0.0794 | 0.9165 |
| Random Forest | Dataset 2 | n_estimators=200, max_depth=10 | 0.7347 | 0.7140 | 0.0766 | 0.9172 |
| Random Forest | Dataset 2 | n_estimators=500, max_depth=10 | 0.7311 | 0.7182 | 0.0822 | 0.9184 |
| Random Forest | Dataset 2 | n_estimators=50, max_depth=20 | 0.7514 | 0.6973 | 0.0529 | 0.9333 |
| Random Forest | Dataset 2 | n_estimators=100, max_depth=20 | 0.7503 | 0.6931 | 0.0515 | 0.9346 |
| Random Forest | Dataset 2 | n_estimators=200, max_depth=20 | 0.7559 | 0.7015 | 0.0515 | 0.9357 |
| Random Forest | Dataset 2 | n_estimators=500, max_depth=20 | 0.7584 | 0.7077 | 0.0529 | 0.9371 |
| Isolation Forest | Dataset 1 | contamination=0.05 | 0.5488 | 0.4318 | 0.0472 | 0.8120 |
| Isolation Forest | Dataset 1 | contamination=0.1 | 0.6413 | 0.5971 | 0.0883 | 0.8120 |
| Isolation Forest | Dataset 1 | contamination=0.2 | 0.6023 | 0.6759 | 0.1893 | 0.8120 |
| Isolation Forest | Dataset 1 | contamination=0.3 | 0.5638 | 0.7310 | 0.2873 | 0.8120 |
| Isolation Forest | Dataset 1 | **shipped: fixed 0.5 wrapper** | 0.2492 | 0.1457 | 0.0079 | 0.8120 |
| Isolation Forest | Dataset 2 | contamination=0.05 | 0.2633 | 0.1649 | 0.0292 | 0.6768 |
| Isolation Forest | Dataset 2 | contamination=0.1 | 0.3842 | 0.3048 | 0.0940 | 0.6768 |
| Isolation Forest | Dataset 2 | contamination=0.2 | 0.4615 | 0.4760 | 0.1957 | 0.6768 |
| Isolation Forest | Dataset 2 | contamination=0.3 | 0.4569 | 0.5595 | 0.2967 | 0.6768 |
| Isolation Forest | Dataset 2 | **shipped: fixed 0.5 wrapper** | 0.1431 | 0.0793 | 0.0097 | 0.6768 |

## B.4 Confusion matrices behind every headline score

**Table B.8 — Full confusion matrices, in-domain hold-out.** Counts are test-split
rows; Dataset 1's test split is 3,049 rows (762 attack) and Dataset 2's is 1,915
(479 attack). The 1:3 attack:benign ratio means a do-nothing classifier that
flags everything scores F1 0.400, which is the floor every model here must beat.

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
