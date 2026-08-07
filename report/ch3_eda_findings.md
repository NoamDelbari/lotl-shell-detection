# Chapter 3 — EDA & Domain Justification (Dataset 1, Ben)

Train split: **12199** commands (3050 malicious / 9149 benign, 1:3).

## 3.3 Empirical feature justification (hard evidence)

Every engineered feature was tested with a two-sided **Mann-Whitney U** test (features are counts/ratios, not normal) and a **rank-biserial effect size** r in [-1,1] (sign = direction; +r means larger for malicious). Full table: `report/ch3_feature_justification.csv`.

- **36 / 37** features differ between classes at p < 0.05.
- **6** features reach |r| >= 0.2 (a meaningful separation).

### Strongest features (top 10 by |effect size|)

| feature | mean malicious | mean benign | rank-biserial r | MWU p |
|---|---:|---:|---:|---:|
| `special_ratio` | 0.1863 | 0.1436 | +0.318 | 1.58e-152 |
| `max_token_len` | 16.0911 | 11.5774 | +0.303 | 8.16e-140 |
| `char_entropy` | 4.0607 | 3.8523 | +0.288 | 1.89e-125 |
| `n_redirects` | 0.521 | 0.0823 | +0.252 | 1.65e-290 |
| `len_chars` | 52.4285 | 37.7934 | +0.247 | 5.21e-93 |
| `digit_ratio` | 0.06 | 0.0206 | +0.238 | 1.25e-121 |
| `n_sensitive_paths` | 0.2564 | 0.0226 | +0.182 | 5.17e-272 |
| `n_pipes` | 0.3111 | 0.5567 | -0.166 | 7.79e-69 |
| `mean_token_len` | 7.2652 | 6.2483 | +0.161 | 1.87e-40 |
| `len_tokens` | 6.7144 | 5.3119 | +0.135 | 1.09e-29 |

### 3.2 Noise & redundancy reduction

- **Low-signal features** (|r| < 0.05, candidates to prune for compute): `has_shell_bin`, `n_backticks_subshell`, `n_enum_bins`, `has_enum_bin`, `has_dev_tcp`, `n_ports`, `has_interp_bin`, `has_url`, `n_and_or`, `has_shell_flag_i`, `has_exec_flag`, `has_privesc_bin`, `has_evasion_tok`, `n_braces`, `has_hex_escape`, `nonprintable_ratio`, `has_eval`.
- **Redundant / multicollinear pairs** (|corr| > 0.85) — keep one of each pair; the tree ranking in Ch4 confirms which:
  - `len_chars` ~ `len_tokens` (corr 0.897)
  - `has_ipv4` ~ `n_ipv4` (corr 0.976)
  - `has_enum_bin` ~ `n_enum_bins` (corr 0.984)

Figures: `report/figures/ch3_*.png` (class balance, variance, correlation heatmap, top-feature box plots, length histogram).

> Note on length: Dataset 1's malicious commands are **not** simply longer — see `ch3_length_hist.png` and the low stand-alone power of `len_chars` in the table. This matches the baseline audit (length-only F1 ~ 0.39), so the signal is behavioural, not a length artifact.