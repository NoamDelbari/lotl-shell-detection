# Chapter 4 — Feature Ranking

## 4.1 Three model-derived views and the no-leakage control

**Each view is biased differently, so only what survives all three is a finding.**
For each corpus `analysis/ch4_ranking.py` records **RF MDI**, **XGBoost gain** and
**permutation importance**; the **consensus rank** averages the three per-view
ranks. MDI favours high-cardinality columns, gain rewards rarity, permutation
under-credits whatever a correlated neighbour can replace.

**No importance score in this chapter sees the test hold-out, and no feature is
ranked on rows its own model was fitted on.** All three views are fitted inside
the training frame from `ingestion.load(dataset)` (`ch4_ranking.py:49`);
permutation is scored on a 25% slice held out from *within* it. The input is
`featurize(train["command"])` — the command string alone, never the `source`
column that carries the label's provenance. That inner slice is stratified but
ungrouped, so permutation magnitudes are optimistic; only their ordering is used.

**Table 4.1 — Consensus top eight per corpus, with each feature's gain and
permutation rank.** Ranks are out of 43; lower is more important.

<!-- cols: 0.50 1.45 0.75 0.75 1.45 0.80 0.80 -->
| # | Dataset 1 | gain | perm | Dataset 2 | gain | perm |
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

**Only `n_abs_paths` appears in both consensus top eights**, and the Spearman
correlation between the two gain rankings across all 43 features is **ρ = 0.43**.
Dataset 1 concentrates — its top three by gain carry **0.389 of the gain mass**,
`n_abs_paths` alone 0.181 — while Dataset 2 is flatter (**0.229**) yet discards
far more of the feature set: **8 of 43 features receive exactly zero gain, against
4 on Dataset 1** — `has_dev_tcp` and `has_decode_exec` among them, the two most
explicitly reverse-shell-flavoured features we built. The two models disagree
about which *family* of cues is discriminative — §8.2's transfer collapse is
legible here already.

## 4.3 Gain versus permutation

**MDI and permutation agree almost exactly (ρ = 0.92 on D1, 0.95 on D2) while
gain agrees with neither (ρ = 0.56 and 0.48 against permutation).** Part of that
is trivial — MDI and permutation read the same Random Forest, gain a different
model — but the residual is systematic.

*Gain inflates rare, high-purity flags.* The few splits taken on a low-prevalence
flag separate their subset cleanly, and gain is an average **per split**.
Permutation asks what destroying the column costs, and answers nothing
measurable: correlated features cover the few rows carrying the flag. **A high
gain rank is not evidence that a feature is load-bearing.**

*Gain deflates collinear composition statistics.* Continuous shape statistics
enter many shallow refinements worth little individually, so the per-split
average buries what permutation puts first.

**Table 4.2 — The gain-versus-permutation discrepancy runs in two systematic
directions.** Ranks out of 43; a 0.0000 score means shuffling the column costs no
measurable accuracy.

<!-- cols: 1.50 0.80 0.85 0.85 0.85 1.65 -->
| Feature | corpus | MDI rank | gain rank | perm rank | perm score |
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

**Five of Dataset 1's consensus top eight are structural** — path, pipe and
redirect counts and composition ratios — describing shape, not intent. The
features built for T1059.004 sit mid-pack or below: `n_sensitive_paths` 13th,
`head_is_privesc` 21st, `has_decode_exec` 28th, `has_dev_tcp` 31st of 43. That is
the style-shortcut risk this project set out to probe: provenance-derived labels
let a model learn the attack corpora's register — dense path arguments,
`2>/dev/null` boilerplate — instead of malice.

**Where this chapter parts company with Chapter 3 is itself the result.** Ch3
asks which features separate the classes alone; Ch4 asks what the fitted model
leans on. A feature can do the first and still be ignored — the trees elect one
representative from a collinear block and absorb the rest, a redundancy result,
not a refutation. On Dataset 1 `n_abs_paths` heads both rankings — first by
univariate effect size, first by consensus. Even that agreement is corpus-bound:
on Dataset 2 it holds 2nd by consensus but falls to 15th univariately and 10th by
gain. **No feature here is defensible independently of the corpus it was ranked
on.**
