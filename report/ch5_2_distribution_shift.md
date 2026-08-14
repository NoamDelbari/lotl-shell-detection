# Chapter 5.2 — Cross-Dataset Distribution Shift

> Because Section 5.1 established that both corpora pass through the same
> stateless extractor, every difference reported here is a property of the data
> rather than of the processing. Sources: `report/ch3_d1_feature_stats.csv`,
> `ch3_d2_feature_stats.csv`, `report/ch4_feature_ranking.csv`,
> `results/ch8_cross_dataset.json`.

Three distinct kinds of shift are measurable between Dataset 1 and Dataset 2,
and they compound: the feature *distributions* differ, the *direction* of class
separation differs, and the features the models *use* differ.

## Covariate shift: the corpora are nearly separable in feature space

The blunt diagnostic is to discard the malicious/benign label entirely and train
a Random Forest on the 43 engineered features alone to answer a different
question — *which corpus did this command come from?* Under 5-fold
cross-validation on the pooled training splits:

| rows scored | n | ROC-AUC |
|---|---:|---:|
| all rows | 19,860 | 0.861 |
| benign rows only | 14,895 | 0.852 |
| **malicious rows only** | 4,965 | **0.970** |

The last row is the important one. In the same 43-dimensional space in which the
detector has to separate attacks from benign commands, a Dataset 1 attack and a
Dataset 2 attack are almost perfectly distinguishable from one another. A
published reverse-shell payload and a command typed into a compromised honeypot
are, as feature vectors, further apart than attacks and benign commands are
within either corpus. Nothing a model learns about the shape of one is
guaranteed to describe the other.

## Effect shift I: fifteen of forty-three features change sign

Rank-biserial correlation (equivalently Cliff's δ) measures the direction and
strength of class separation. **Fifteen of the 43 features invert their sign**
between the two corpora — the feature does not merely weaken, it points at the
other class. The largest reversals:

| feature | Dataset 1 | Dataset 2 | swing |
|---|---:|---:|---:|
| `len_chars` | +0.247 | −0.171 | 0.418 |
| `len_tokens` | +0.135 | −0.207 | 0.342 |
| `n_quotes` | +0.081 | −0.112 | 0.193 |
| `n_flags` | +0.051 | −0.125 | 0.176 |
| `has_dev_null` | +0.143 | −0.004 | 0.147 |
| `b64_run_len` | +0.102 | −0.032 | 0.134 |
| `head_is_privesc` | −0.012 | +0.065 | 0.077 |

The top four are all measures of size and verbosity, and they invert for a
reason that is a fact about corpus construction rather than about attackers.
Dataset 1 sets long generated payloads and multi-stage catalogue one-liners
against short documentation examples, so "malicious commands are longer" is
true there. Dataset 2 sets terse honeypot reconnaissance (`uname -a`, `cd /tmp`,
`cat /proc/cpuinfo`) against real user history full of long interactive
pipelines, so the same statement is false there — and measurably so. A detector
tuned on Dataset 1's length signal is not merely uninformed about Dataset 2, it
is actively miscalibrated against it.

## Effect shift II: the signal is weaker everywhere on Dataset 2

Sign is not the only thing that moves. Aggregated over all 43 features:

| statistic | Dataset 1 | Dataset 2 |
|---|---:|---:|
| mean \|effect\| | 0.0867 | 0.0617 |
| strongest single feature | 0.452 (`n_abs_paths`) | 0.234 (`digit_ratio`) |
| features with \|effect\| ≥ 0.10 | 14 | 11 |
| solo-rule features beating the 0.400 floor | 3 | **0** |

The two 43-length effect-size vectors correlate at Pearson *r* = 0.317
(Spearman 0.307) — barely related. Operational data simply carries less
per-feature signal than curated data, which is consistent with the labelling
premise in Chapter 1.1: Dataset 2's malicious class contains real attacker
reconnaissance that is genuinely indistinguishable, in isolation, from
administration.

## Importance shift: the models learn different features

The consequence surfaces in Chapter 4's importance ranking, which combines
Random Forest MDI, XGBoost gain and permutation importance into a consensus
rank per dataset. Across the two corpora that consensus ranking correlates at
**Spearman 0.596 / Kendall τ 0.417**, and the top of the list barely overlaps:

| | Dataset 1 top 5 | Dataset 2 top 5 |
|---|---|---|
| 1 | `n_abs_paths` | `has_fetch_bin` |
| 2 | `has_shell_bin` | `n_abs_paths` |
| 3 | `n_pipes` | `head_is_privesc` |
| 4 | `has_dev_null` | `has_hidden_path` |
| 5 | `special_ratio` | `len_tokens` |

**One feature is common to both top fives** (`n_abs_paths`); three are common to
both top tens. The largest individual moves are `has_dev_null` (consensus rank
6.3 → 30.7), `head_is_shell` (30.7 → 10.3), `has_url` (33.3 → 15.0) and
`has_fetch_bin` (19.3 → 3.0) — and each is interpretable. Dataset 1's attacks
suppress output and invoke shells because that is what published payloads do;
Dataset 2's attacks fetch things, because a real intrusion's first act after
gaining a shell is to pull down a second stage.

## What does transfer, and why

The picture is not uniformly negative, and the exceptions are the informative
part. Features that keep both sign and rough magnitude across corpora:

| feature | Dataset 1 | Dataset 2 |
|---|---:|---:|
| `digit_ratio` | δ +0.238 | δ +0.234 |
| `mean_token_len` | δ +0.161 | δ +0.198 |
| `n_pipes` | δ −0.166 | δ −0.107 |
| `has_lotl_bin` | OR 0.62 | OR 0.50 |
| `has_pipe_to_shell` | OR 8.65 | OR 8.68 |
| `has_hex_escape` | OR 22.3 | OR 11.7 |
| `has_hidden_path` | OR 4.36 | OR 3.99 |
| `has_fetch_bin` | OR 5.56 | OR 7.96 |

The pattern is consistent and it is the chapter's central claim. What survives a
change of corpus is **encoding artefacts** (`digit_ratio`, `has_hex_escape`),
**structural necessities** (`has_pipe_to_shell` — a pipe terminating in an
interpreter is a download cradle in any corpus; `has_hidden_path`), and
**stable negatives** (`n_pipes` and `has_lotl_bin`, both reliably benign in both
places). What does not survive is anything derived from **size, verbosity or
vocabulary** — precisely the properties that a corpus's authors, rather than its
attackers, determine.

## The measured consequence

Training on one corpus and testing on the other gives the following, against a
do-nothing floor of 0.400 in both directions:

| model | D1→D1 | D1→D2 | D2→D2 | D2→D1 |
|---|---:|---:|---:|---:|
| `xgboost_hybrid` | 0.876 | 0.532 | 0.848 | 0.276 |
| `cnn1d` | 0.860 | **0.541** | 0.838 | **0.359** |
| `random_forest` | 0.796 | 0.515 | 0.753 | 0.143 |
| `xgboost` | 0.786 | 0.495 | 0.756 | 0.235 |
| `isolation_forest` | 0.249 | 0.148 | 0.143 | 0.241 |

(F1; full metrics in `results/ch8_cross_dataset.json`, analysed in Chapter 8.2.)

Transfer is poor and **asymmetric**. The best D1→D2 result clears the floor but
reaches only 0.541, against 0.848 for a model trained on Dataset 2 itself. In
the other direction the best result is 0.359 — *below* the do-nothing floor, as
is **every one of the five models**, meaning a detector trained on real honeypot
activity and pointed at published attack payloads is worse than useless in the
strict sense that labelling everything "attack" would score higher. Dataset 1
generalises to Dataset 2 slightly better than the
reverse, which is what the shift analysis predicts: Dataset 1 is the broader,
more heterogeneous corpus, while a model trained only on honeypot activity has
never seen a published multi-stage payload.

No domain adaptation, importance reweighting or per-corpus feature was
introduced to close this gap. That is deliberate. The gap is the result the
two-dataset design exists to produce, and the analysis above is an explanation
of it rather than an apology for it — a detector validated on one corpus of
shell commands should not be assumed to work on another, and this chapter
quantifies how badly that assumption fails.
