# Chapter 4 — Feature Ranking

## 4.1 Three model-derived views and the no-leakage control

**Only what survives all three biased views is a finding:** `analysis/ch4_ranking.py`
records **RF MDI**, **XGBoost gain** and **permutation importance** per corpus; the
**consensus rank** averages them.

**No score sees the test hold-out; none is fitted on the rows it ranks:** all three
fit inside `ingestion.load(dataset)`'s training frame (`ch4_ranking.py:49`),
permutation on a 25% slice held from *within* it, on `featurize(train["command"])`
— never the label-provenance `source` column. Ungrouped, it leaves
permutation magnitudes optimistic; only ordering is used.

**Table 4.1 — Consensus top eight per corpus.** Ranks out of 43, lower better.

<!-- cols: 0.50 1.45 0.75 0.75 1.45 0.80 0.80 -->
| # | D1 | gain | perm | D2 | gain | perm |
|---:|---|---:|---:|---|---:|---:|
| 1 | `n_abs_paths` | 1 | 3 | `has_fetch_bin` | 1 | 1 |
| 2 | `has_shell_bin` | 3 | 2 | `n_abs_paths` | 10 | 5 |
| 3 | `n_pipes` | 7 | 4 | `head_is_privesc` | 6 | 8 |
| 4 | `has_dev_null` | 2 | 5 | `has_hidden_path` | 5 | 11 |
| 5 | `special_ratio` | 22 | 1 | `len_tokens` | 17 | 7 |
| 6 | `n_redirect_out` | 9 | 8 | `head_is_shell` | 3 | 12 |
| 7 | `has_lotl_bin` | 6 | 10 | `head_is_lotl` | 4 | 14 |
| 8 | `digit_ratio` | 20 | 6 | `has_evasion_tok` | 8 | 13 |

## 4.2 Corpus-specific rankings

**Only `n_abs_paths` appears in both consensus top eights** (gain rankings
**ρ = 0.43**). D1 concentrates — top three by gain hold **0.389 of the gain mass**,
`n_abs_paths` alone 0.181 — D2 is flatter (**0.229**) yet gives exactly zero gain
to **8 of 43 features against 4 on D1**, including reverse-shell `has_dev_tcp` and
`has_decode_exec`; §8.2's transfer collapse starts here.

## 4.3 Gain versus permutation

**MDI and permutation agree almost exactly (ρ = 0.92 on D1, 0.95 on D2); gain
agrees with neither (ρ = 0.56 and 0.48 against permutation)** — partly shared
provenance, but the residual is systematic.

*Gain inflates rare, high-purity flags* — averaged **per split**, yet shuffling one
costs nothing measurable, correlated features covering its rows — and *deflates
collinear composition statistics*, buried by that same average where permutation
leads them. **A high gain rank is not evidence that a feature is load-bearing.**

**Table 4.2 — The discrepancy runs in two systematic directions.** 0.0000 means no
measurable cost.

<!-- cols: 1.50 0.80 0.85 0.85 0.85 1.65 -->
| Feature | corpus | MDI | gain | perm | perm score |
|---|---|---:|---:|---:|---:|
| `has_interp_bin` | D1 | 24 | 5 | 31 | 0.0001 |
| `has_decode_exec` | D1 | 31 | 13 | 39 | 0.0000 |
| `has_dev_tcp` | D1 | 38 | 15 | 39 | 0.0000 |
| `has_dev_null` | D2 | 34 | 16 | 42 | −0.0001 |
| `special_ratio` | D1 | 2 | 22 | 1 | 0.0596 |
| `max_token_len` | D1 | 3 | 27 | 7 | 0.0125 |
| `len_chars` | D2 | 1 | 30 | 2 | 0.0296 |
| `digit_ratio` | D2 | 5 | 28 | 4 | 0.0242 |

## 4.4 What the model leans on

**Five of Dataset 1's consensus top eight are structural**, shape not intent, while
the T1059.004 features sit mid-pack or below: `n_sensitive_paths` 13th,
`head_is_privesc` 21st, `has_decode_exec` 28th, `has_dev_tcp` 31st of 43. That is
the style-shortcut risk: provenance-derived labels teach register, not malice.

**A Chapter 3 separator can still be ignored here:** the trees elect one representative
per collinear block — redundancy, not refutation. `n_abs_paths` heads both on D1
but falls to 15th univariately and 10th by gain on D2. **No feature here is
defensible independently of its corpus.**
