# Chapter 4 — Tree-based feature ranking (Ben's code + chart)

Three importance views per dataset (RF MDI, XGBoost gain, permutation on held-out split). Full scores: `report/ch4_feature_ranking.csv`. Charts: `report/figures/ch4_ranking_dataset{1,2}.png`.

Permutation importance is included specifically because MDI is biased toward high-cardinality features (a leakage magnet); where MDI and permutation disagree sharply, Ch4's discrepancy analysis (Noam) should look for a leakage or multicollinearity cause.

## Dataset 1 — top 10 by consensus rank

| rank | feature | RF MDI | XGB gain | permutation |
|---:|---|---:|---:|---:|
| 1 | `n_pipes` | 0.0678 | 0.0653 | 0.0476 |
| 2 | `special_ratio` | 0.1508 | 0.0239 | 0.0927 |
| 3 | `n_redirects` | 0.0619 | 0.0836 | 0.0316 |
| 4 | `n_sensitive_paths` | 0.0441 | 0.1117 | 0.0312 |
| 5 | `has_lotl_bin` | 0.0264 | 0.0544 | 0.0097 |
| 6 | `max_token_len` | 0.1023 | 0.0197 | 0.0178 |
| 7 | `digit_ratio` | 0.0628 | 0.0217 | 0.0232 |
| 8 | `n_parens` | 0.0175 | 0.0441 | 0.0057 |
| 9 | `char_entropy` | 0.1045 | 0.0125 | 0.0100 |
| 10 | `has_shell_bin` | 0.0083 | 0.0520 | 0.0020 |

**For the intuition-vs-ranking reconciliation (cross-ref Ch3):** the Ch3 top features by effect size were `special_ratio`, `max_token_len`, `char_entropy`, `n_redirects`, `len_chars`, `digit_ratio`. Compare against the tree ranking above and flag: (a) features the trees rank high that Ch3 rated weak (possible latent pattern or leakage), (b) domain features Ch3 rated strong that the trees ignore (possible multicollinearity — a correlated feature absorbed the signal).