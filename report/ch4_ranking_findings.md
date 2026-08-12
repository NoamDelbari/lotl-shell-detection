# Chapter 4 — Feature Ranking Findings

## 4.1 Tree-based feature importance ranking

Three importance views are computed per corpus over the 43 engineered features
(`analysis/ch4_ranking.py`, full scores in `report/ch4_feature_ranking.csv`):
**RF MDI** (mean decrease in impurity), **XGBoost gain** (average loss reduction
per split, `feature_importances_`), and **permutation importance** on a held-out
25% of the training split. All three are fitted inside the training split only,
so nothing here sees the test hold-out. The **consensus rank** is the mean of the
three per-view ranks. Figures `ch4_ranking_dataset{1,2}.png` plot the RF MDI view
(top 20); the gain and permutation columns below come from the CSV.

**Table 4.1 — Dataset 1: top 8 engineered features by consensus rank.**
Lower consensus rank = more important. "—" marks a feature that describes the
*shape* of a command rather than a technique.

| Rank | Feature | MDI | Gain | Perm. | What it measures | MITRE ATT&CK |
|---:|---|---:|---:|---:|---|---|
| 1 | `n_abs_paths` | 0.124 | **0.181** | 0.034 | Count of absolute-path tokens (`/…`) | — (targeting) |
| 2 | `has_shell_bin` | 0.049 | 0.097 | 0.039 | A shell binary is named (`bash`, `sh`, `zsh`, `dash`) | Execution → T1059.004 |
| 3 | `n_pipes` | 0.057 | 0.035 | 0.034 | Number of `\|` pipe stages | — (composition) |
| 4 | `has_dev_null` | 0.033 | 0.111 | 0.020 | Output suppressed to `/dev/null` | Defense Evasion → T1562 (weak) |
| 5 | `special_ratio` | **0.123** | 0.014 | **0.060** | Share of non-alphanumeric characters | — (composition) |
| 6 | `n_redirect_out` | 0.042 | 0.026 | 0.012 | Count of `>` / `>>` redirects | — (composition) |
| 7 | `has_lotl_bin` | 0.022 | 0.038 | 0.005 | A dual-use LotL binary is named | Execution / Defense Evasion → T1059.004 |
| 8 | `digit_ratio` | 0.061 | 0.015 | 0.014 | Share of digit characters | — (composition) |

The gain curve is steeply front-loaded: on Dataset 1 the top three features by
gain (`n_abs_paths` 0.181, `has_dev_null` 0.111, `has_shell_bin` 0.097) carry
**0.389 of the total gain mass**, and four of the 43 features are never split on
at all. Dataset 2 is flatter — its top three (`has_fetch_bin` 0.093,
`has_shell_bin` 0.069, `head_is_shell` 0.067) carry **0.229** — but it discards
more of the feature set: **8 of 43 features receive exactly zero gain**,
including `has_dev_tcp` and `has_decode_exec`, the two most explicitly
reverse-shell-flavoured features we built.

**Table 4.2 — The two corpora disagree about which cues matter.**
XGBoost gain and its rank (of 43) per corpus. Spearman correlation between the
two rank orders across all 43 features is **ρ = 0.43**.

| Feature | Dataset 1 gain (rank) | Dataset 2 gain (rank) | Direction |
|---|---:|---:|---|
| `n_abs_paths` | 0.181 (1) | 0.036 (10) | D1-specific |
| `has_dev_null` | 0.111 (2) | 0.021 (16) | D1-specific |
| `has_interp_bin` | 0.041 (5) | 0.017 (20) | D1-specific |
| `has_shell_bin` | 0.097 (3) | 0.069 (2) | **shared** |
| `head_is_lotl` | 0.045 (4) | 0.066 (4) | **shared** |
| `head_is_shell` | 0.010 (30) | 0.067 (3) | D2-specific |
| `has_hidden_path` | 0.019 (17) | 0.061 (5) | D2-specific |
| `head_is_privesc` | 0.016 (19) | 0.059 (6) | D2-specific |
| `has_fetch_bin` | 0.020 (14) | **0.093 (1)** | D2-specific |
| `has_long_flag` | 0.012 (25) | 0.048 (7) | D2-specific |

## 4.2 Critical discrepancy analysis

**The three views disagree, and the pattern of disagreement is diagnostic.** MDI
and permutation agree almost perfectly (Spearman ρ = 0.92 on Dataset 1, 0.95 on
Dataset 2) while gain agrees with neither (ρ = 0.56 and 0.48 against
permutation). Part of that is trivial — MDI and permutation are both measured on
the *same* Random Forest, gain on a different model — but the residual is a real
methodological artefact and it runs in a consistent direction.

*Rare high-purity flags are inflated by gain.* `has_interp_bin` ranks **5th by
gain (0.041) and 31st by permutation (0.0001)**; `has_decode_exec` is 13th by
gain and 39th by permutation (0.0000); `has_dev_tcp` 15th versus 39th (0.0000);
`head_is_interp` 10th versus 32nd. These are low-prevalence binary flags: the
few splits taken on them separate their subset cleanly, and gain is an *average
per split*, so a rare, decisive feature scores high. Permutation asks the
different question that matters operationally — how much accuracy is lost if the
column is destroyed — and answers **nothing measurable**, because so few rows
carry the flag and correlated features cover those that do. Gain rank is not
evidence a feature is load-bearing.

*Collinear length statistics are deflated by gain.* The mirror case:
`special_ratio` is 2nd by MDI and **1st by permutation (0.060)** but only 22nd by
gain; `max_token_len`, `mean_token_len` and `len_chars` sit at MDI ranks 3–5 and
gain ranks 27–29. Continuous composition statistics are used in many shallow
refinements, each with a small gain, so the per-split average buries them. This
also reconciles Chapter 3: its Dataset-1 effect-size leaders were `n_abs_paths`
(+0.452), `special_ratio` (+0.318), `max_token_len` (+0.303), `len_chars`
(+0.247) and `digit_ratio` (+0.238) — five features that are mutually collinear
length-and-density proxies. The trees do not ignore them; they elect one
representative (`n_abs_paths`, which is simultaneously the strongest univariate
separator and the top consensus feature) and the rest are absorbed. Only
`n_abs_paths` is top-ranked under all three views on both a univariate and a
multivariate test — the one feature we can defend without a caveat.

**What the ranking says about the model.** Read across Table 4.1, five of the
Dataset-1 top eight are structural: absolute-path counts, pipe counts, redirect
counts, and character-composition ratios. These describe a command's *shape*, not
its intent. The genuinely intent-bearing features we built for T1059.004 —
`n_sensitive_paths` (consensus 13th of 43), `head_is_privesc` (21st),
`has_decode_exec` (28th), `has_dev_tcp` (31st) — sit in the mid-pack or below. This is the
**style-shortcut risk** the project set out to probe: because the labels are
provenance-derived, a model can separate the classes by learning the attack
corpus's stylistic fingerprint — explicit interpreters, dense path arguments,
`2>/dev/null` boilerplate — without learning malice. Redirects and pipes are the
connective tissue of shell tradecraft and equally of routine admin scripting;
their *counts* proxy for "looks like a dense one-liner," not "is an attack."

**Divergence foreshadows transfer collapse.** Table 4.2 makes the failure mode in
§8.2 predictable. The two corpora share only two of their top-four cues
(`has_shell_bin`, `head_is_lotl`); everything else swaps. Dataset 1's leader
`n_abs_paths` falls from rank 1 to rank 10 on Dataset 2, while Dataset 2's leader
`has_fetch_bin` — download cradles, the honeypot's dominant behaviour — sits at
rank 14 on Dataset 1. Dataset 2 additionally leans on `head_is_privesc` and
`has_hidden_path` (persistence and stealth, ranks 6 and 5) that Dataset 1 barely
uses, and on `has_long_flag`, a purely stylistic tell about `--word` flag usage.
An overall rank correlation of **ρ = 0.43** means the two models do not merely
weight a shared signal differently — they substantially disagree about *which
family of cues is discriminative at all*. Each has latched onto the
provenance-specific register of its own training corpus, which is exactly why a
boundary fitted on one collapses on the other (§8.2: every supervised model at
least halves its F1 under transfer).
