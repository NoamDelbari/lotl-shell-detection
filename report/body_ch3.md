# Chapter 3 — Exploratory Data Analysis

## 3.1 Two corpora, deliberately unlike each other

**The two corpora were chosen to disagree:** curated literature against
operational telemetry.

**Table 3.1 — Corpus composition, protocol, and baseline floor.**

<!-- cols: 1.35 2.55 2.60 -->

| | **Dataset 1** — curated | **Dataset 2** — operational |
|---|---|---|
| Rows (train / test) | 15,248 (12,199 / 3,049) | 9,576 (7,661 / 1,915) |
| Attack rows in test | 762 | 479 |
| Attack sources | `hacktricks` 1805, `gtfobins` 957, `atomic_red_team` 685, `quasarnix` 204, `slp` 101, `payloads` 60 | `honeypot` 2394 — the entire attack class |
| Benign sources | `tldr` 4576, `bash_instruct` 3935, `nl2bash` 1567, `linlm` 752, `bash6k` 606 | `bash_history` 5027, `commandlinefu` 2155 |
| Class ratio | 1:3 | 1:3 |
| Split | 80/20, **grouped by command shape** | same |
| Do-nothing F1 floor | 0.400 | 0.400 |

**Splits group by command shape, not source**, so near-duplicates cannot
straddle it; source-grouping would test on an unseen corpus — a cost measured
in §3.3 and Chapter 8.2.

## 3.2 The headline regularity, and the fact that it inverts

**On Dataset 1 attacks are longer:** benign mean 37.8 characters
(median 29) against 52.4 (median 41), p99 227 versus 147. Separation is
tail-only: both classes crowd the same 20–50 character body, and **a
length-only probe reaches AUC 0.611**.

**On Dataset 2 the rule inverts:** benign longer (mean 42.0, median 27), attack
shorter (mean 36.8, median 21), dispersion the attack signal: variance
11,780 against 1,822 benign, 6.5×, the longest a 3,450-character dropper against
a benign maximum of 350. **The same probe scores AUC 0.430**, below chance *in
the direction that worked on Dataset 1* (Figure B.1).

## 3.3 Per-feature discrimination: many weak signals, and three that flip

**Variance gap measures *spread*, not separation**, so claims use
Mann-Whitney U with rank-biserial effects (`report/ch3_d1_feature_stats.csv`,
`report/ch3_d2_feature_stats.csv`): `special_ratio` ranks 41st of 43 by gap,
second by effect.

**Table 3.2 — Strongest per-feature effects (rank-biserial; sign gives the
leaning class).** Dataset 1 separates 41 of 43 features at p < 0.05, Dataset 2
only 35 — its best weaker than Dataset 1's fifth.

<!-- cols: 2.05 1.20 2.05 1.20 -->

| Dataset 1 | effect | Dataset 2 | effect |
|---|---:|---|---:|
| `n_abs_paths` | +0.452 | `digit_ratio` | +0.234 |
| `special_ratio` | +0.318 | `len_tokens` | −0.207 |
| `max_token_len` | +0.303 | `mean_token_len` | +0.198 |
| `len_chars` | +0.247 | `has_fetch_bin` | +0.185 |
| `digit_ratio` | +0.238 | `len_chars` | −0.171 |
| `n_redirect_out` | +0.229 | `n_flags` | −0.125 |

**The two profiles describe different adversaries:** Dataset 2's is the
automated dropper — fetch binaries (21.9% of attacks vs 3.4% benign), URLs
(13.6% vs 2.4%), hidden staging directories (14.7% vs 4.1%). Base64 features
rank near-informationless (|r| ≤ 0.033) despite huge attack-side
`b64_run_len` variance (1,059 vs 68): too rare to move the body.

**Table 3.3 — Features behaving differently across corpora.**

<!-- cols: 1.35 0.85 0.85 3.45 -->

| Feature | D1 | D2 | Reading |
|---|---:|---:|---|
| `digit_ratio` | +0.238 | +0.234 | **Stable.** Attack-leaning on both, near-identical strength. |
| `len_chars` | +0.247 | −0.171 | **Inverted.** §3.2's length rule at feature level. |
| `n_quotes` | +0.081 | −0.112 | **Inverted.** Administrators quote; scripted attackers do not. |
| `n_flags` | +0.051 | −0.125 | **Inverted.** Cowrie's probes are terse and flagless. |
| `n_pipes` | −0.166 | −0.106 | **Benign on both.** Pipes are ordinary plumbing. |
| `head_is_lotl` | −0.046 | −0.118 | **Benign on both, reinforced.** LotL-headed commands are ten times commoner in Dataset 2 benign traffic (13.1% vs 1.3%). |

**The inversions come from the benign pool, not noise:** curated benign corpora
underrepresent administrator plumbing. So **living-off-the-land vocabulary is
itself an anti-signal on both corpora** — the basis for §1.3's conjunction
features and Chapter 8.2's D1→D2 collapse.

## 3.4 Redundancy: real, bounded, and not leakage

**One size cluster dominates the heat-maps (Figure B.2).** Its strongest pair,
`len_chars` ~ `len_tokens`, reaches Pearson 0.897 on Dataset 1 and 0.906 on
Dataset 2, yet **no pair among the shipped 43 crosses the audit's Spearman
|ρ| > 0.9 redundancy line** — that cut was spent upstream, on scale-free
`char_entropy` and `token_entropy`. The rest is by-construction, bar two
informative Dataset-2 pairs: `max_token_len` ~ `b64_run_len` (0.743) and
`has_url` ~ `has_fetch_bin` (0.675).

**One caveat is distributional, not structural:** `digit_ratio`, `has_ipv4` and
`has_url` owe part of their Dataset-2 strength to Cowrie campaigns hard-coding
command-and-control addresses — a property of the capture, not malice, so they
are strong *on this telemetry* only, as Chapter 8's transfer results vindicate.

## 3.5 What the EDA commits the model to

**No small feature subset will carry the classifier.** Dataset 2 offers 35 weak,
partly redundant signals topping out at 0.234; Dataset 1 six above |r| = 0.2 and
a flat tail. Lift needs *conjunctions*, hence the hybrid representation:
engineered-only XGBoost reaches F1 0.786 on Dataset 1 against the hybrid's
0.876.

**Scale must be handled in the pipeline, not assumed away:** raw-magnitude
leaders (`len_chars`, `max_token_len`) would swamp distance-, linear- and neural
learners; bounded ratios (`special_ratio`, `digit_ratio`) encode obfuscation
without it — hence Chapter 5.3's standardisation, fitted inside the training
fold only.

**A sign-flipping feature must not carry a cross-domain
model.** `len_chars`, `n_quotes` and `n_flags` are useful in-domain — that
weight is why hold-out strength coexists with transfer collapse,
Dataset 2's *benign* traffic sitting adversarially close to attack vocabulary.
