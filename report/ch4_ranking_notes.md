# Chapter 4 — Tree-based feature ranking (Ben's code + chart)

Three importance views per dataset (RF MDI, XGBoost gain, permutation on held-out split). Full scores: `report/ch4_feature_ranking.csv`. Charts: `report/figures/ch4_ranking_dataset{1,2}.png`.

Permutation importance is included specifically because MDI is biased toward high-cardinality features (a leakage magnet); where MDI and permutation disagree sharply, Ch4's discrepancy analysis (Noam) should look for a leakage or multicollinearity cause.

## Dataset 1 — top 10 by consensus rank

| rank | feature | RF MDI | XGB gain | permutation |
|---:|---|---:|---:|---:|
| 1 | `n_abs_paths` | 0.1243 | 0.1806 | 0.0342 |
| 2 | `has_shell_bin` | 0.0493 | 0.0974 | 0.0386 |
| 3 | `n_pipes` | 0.0567 | 0.0348 | 0.0340 |
| 4 | `has_dev_null` | 0.0330 | 0.1112 | 0.0195 |
| 5 | `special_ratio` | 0.1225 | 0.0139 | 0.0596 |
| 6 | `n_redirect_out` | 0.0415 | 0.0261 | 0.0116 |
| 7 | `has_lotl_bin` | 0.0216 | 0.0378 | 0.0045 |
| 8 | `digit_ratio` | 0.0609 | 0.0152 | 0.0136 |
| 9 | `head_is_lotl` | 0.0187 | 0.0452 | 0.0026 |
| 10 | `max_token_len` | 0.0868 | 0.0106 | 0.0125 |

**For the intuition-vs-ranking reconciliation (cross-ref Ch3):** the Ch3 Dataset-1 top features by |rank-biserial| effect size were `n_abs_paths` (+0.452), `special_ratio` (+0.318), `max_token_len` (+0.303), `len_chars` (+0.247), `digit_ratio` (+0.238), `n_redirect_out` (+0.229). Compare against the tree ranking above and flag: (a) features the trees rank high that Ch3 rated weak (possible latent pattern or leakage), (b) domain features Ch3 rated strong that the trees ignore (possible multicollinearity — a correlated feature absorbed the signal).