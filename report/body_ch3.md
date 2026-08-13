# Chapter 3 — Exploratory Data Analysis

## 3.1 Two corpora, deliberately unlike each other

The project analyses two datasets that were chosen to disagree. **Dataset 1** is
curated security literature: published proof-of-concept one-liners on the attack
side, documentation and instruction corpora on the benign side. **Dataset 2** is
operational telemetry: every attack is a command actually issued against a Cowrie
SSH honeypot, and the benign side is real practitioner shell usage. A detector
that works on one and fails on the other has learned the corpus, not the
technique — so the disagreement between them is the measurement, not a nuisance.

**Table 3.1 — The two corpora: composition, protocol, and the floor every
result is measured against.** Both are engineered to the same 1:3 attack:benign
prevalence, so scores are directly comparable across them.

<!-- cols: 1.35 2.55 2.60 -->

| | **Dataset 1** — curated | **Dataset 2** — operational |
|---|---|---|
| Rows (train / test) | 15,248 (12,199 / 3,049) | 9,576 (7,661 / 1,915) |
| Attack rows in test | 762 | 479 |
| Attack sources | `hacktricks` 1805, `gtfobins` 957, `atomic_red_team` 685, `quasarnix` 204, `slp` 101, `payloads` 60 | `honeypot` 2394 — a single Cowrie capture, the entire attack class |
| Benign sources | `tldr` 4576, `bash_instruct` 3935, `nl2bash` 1567, `linlm` 752, `bash6k` 606 | `bash_history` 5027, `commandlinefu` 2155 |
| Class ratio | 1:3 | 1:3 |
| Split | 80/20, **grouped by command shape** — no group straddles the boundary | same |
| Do-nothing F1 floor | 0.400 | 0.400 |

The split is grouped by command shape rather than by source. Grouping by shape
stops near-duplicate one-liners leaking across the boundary; grouping by *source*
was deliberately not done, because the resulting model would be evaluated on a
corpus it had never seen and the in-domain numbers would cease to mean anything.
The cost of that choice is measured directly in §3.3 and again in Chapter 8.2.

## 3.2 The headline regularity, and the fact that it inverts

On Dataset 1 the obvious pattern holds: attack commands are longer. Benign
commands centre at a mean of 37.8 characters (median 29) against the attacks'
52.4 (median 41), and the right tail is decisively heavier — p99 of 227
characters versus 147. That is what a payload-carrying reverse shell or a base64
blob looks like beside a bare `ls`. But the separation lives almost entirely in
the tail: both classes pile into the same 20–50 character body, where the benign
curve fully envelops the attack curve, and **a probe trained on length alone
reaches only AUC 0.611** on the held-out split.

On Dataset 2 the same rule runs backwards. Benign commands are the longer ones
(mean 42.0, median 27) and attacks the shorter (mean 36.8, median 21). What the
attacks have instead is dispersion: length variance of 11,780 against 1,822
benign — 6.5× — with the longest command in the corpus a 3,450-character dropper
payload against a benign maximum of 350. Honeypot traffic is mostly short
scripted fingerprinting (`uname -a`, `cat /proc/cpuinfo`) punctuated by rare
enormous droppers. **The same length probe scores AUC 0.430** — not merely weak,
but below chance *in the direction that worked on Dataset 1*.

This single reversal is the most consequential finding in the chapter. The
strongest, most intuitive univariate rule available on curated data is answered
by live traffic with the opposite sign, and it forecasts the transfer collapse
that Chapter 8.2 measures.

## 3.3 Per-feature discrimination: many weak signals, and three that flip

Variance gap measures *spread*, not separation, so all per-feature claims below
use Mann-Whitney U with rank-biserial effect sizes
(`report/ch3_d1_feature_stats.csv`, `report/ch3_d2_feature_stats.csv`). The
distinction matters: `len_chars` leads Dataset 1's variance-gap table and places
only fourth by effect, while `special_ratio` ranks 41st of 43 by gap and second
by effect — its whole signal lives inside a [0,1] band the variance chart cannot
show.

**Table 3.2 — Strongest per-feature effects on each corpus (rank-biserial;
sign gives the leaning class).** Dataset 1 separates 41 of 43 features at
p < 0.05, Dataset 2 only 35 — and Dataset 2's best effect is weaker than Dataset
1's fifth.

<!-- cols: 2.05 1.20 2.05 1.20 -->

| Dataset 1 | effect | Dataset 2 | effect |
|---|---:|---|---:|
| `n_abs_paths` | +0.452 | `digit_ratio` | +0.234 |
| `special_ratio` | +0.318 | `len_tokens` | −0.207 |
| `max_token_len` | +0.303 | `mean_token_len` | +0.198 |
| `len_chars` | +0.247 | `has_fetch_bin` | +0.185 |
| `digit_ratio` | +0.238 | `len_chars` | −0.171 |
| `n_redirect_out` | +0.229 | `n_flags` | −0.125 |

The two profiles describe different adversaries. Dataset 1's leaders are reach
and shape — absolute paths, special-character density, long tokens — the
signature of a curated exploit one-liner. Dataset 2's are the automated botnet
dropper: digits (IP addresses, ports, hex identifiers), fetch binaries (21.9% of
attacks invoke `wget`/`curl`/`tftp` against 3.4% of benign), URLs (13.6% vs
2.4%), and hidden staging directories (14.7% vs 4.1%). Base64 features, prominent
on Dataset 1, are near-informationless on Dataset 2 by rank (|r| ≤ 0.033) despite
enormous attack-side variance in `b64_run_len` (1,059 vs 68) — encoded payloads
exist in the honeypot stream but are too rare to move the body of the
distribution.

Comparing the two corpora feature by feature separates two mechanisms, and only
one of them is a reversal.

**Table 3.3 — Features whose behaviour differs across corpora.** Positive leans
attack, negative leans benign. The last group is the one detection cannot ignore.

<!-- cols: 1.35 0.85 0.85 3.45 -->

| Feature | D1 | D2 | Reading |
|---|---:|---:|---|
| `digit_ratio` | +0.238 | +0.234 | **Stable.** Attack-leaning on both, at almost identical strength — one of the few features that means the same thing in both registers. |
| `len_chars` | +0.247 | −0.171 | **Inverted.** The length rule of §3.2, at feature level. |
| `n_quotes` | +0.081 | −0.112 | **Inverted.** Administrators quote commit messages; scripted attackers do not. |
| `n_flags` | +0.051 | −0.125 | **Inverted.** Cowrie's probes are terse and flagless. |
| `n_pipes` | −0.166 | −0.106 | **Benign on both.** Pipes are the connective tissue of ordinary administration. |
| `head_is_lotl` | −0.046 | −0.118 | **Benign on both, reinforced.** A command *led* by a LotL binary is ten times more common in Dataset 2's benign traffic (13.1% vs 1.3%). |

The inversions are not noise; they are a property of the benign pool. Real
administrators piping `find` into `xargs`, quoting arguments and stacking long
flags produce exactly the shell plumbing that a curated benign corpus
underrepresents. The consequence for the detector is blunt: **mere presence of
living-off-the-land vocabulary is an anti-signal on both corpora.** Detection
cannot ride on *which* binary appears, only on how it is used — which is the
empirical basis for the positional and conjunction features of §1.3, and the
feature-level mechanism behind the D1→D2 collapse in Chapter 8.2.

## 3.4 Redundancy: real, bounded, and not leakage

The heat-maps (`ch3_corr_heatmap_dataset{1,2}.png`) show one size cluster and
nothing else close. Exactly one pair reaches the audit's |ρ| > 0.9 redundancy
threshold — `len_chars` ~ `len_tokens`, at 0.897 on Dataset 1 and 0.906 on
Dataset 2 — and both members were nonetheless retained, because the audit had
already spent its cut inside that cluster on the scale-free proxies
(`char_entropy` dropped in favour of `len_chars`, `token_entropy` in favour of
`len_tokens`). Everything below it is ordinary structure: on Dataset 1 the
by-construction pairs `has_lotl_bin` ~ `head_is_lotl` (0.871) and
`has_interp_bin` ~ `head_is_interp` (0.685) — a command headed by an interpreter
necessarily contains one — and on Dataset 2 `mean_token_len` ~ `max_token_len`
(0.783). Two Dataset-2 pairs are informative rather than nuisance:
`max_token_len` ~ `b64_run_len` (0.743) says the longest tokens *are* the encoded
blobs when they occur, and `has_url` ~ `has_fetch_bin` (0.675) says URLs arrive
almost exclusively inside fetch commands — the download cradle itself.

One caveat is distributional rather than structural. `digit_ratio`, `has_ipv4`
and `has_url` earn part of their Dataset-2 strength from Cowrie campaigns
hard-coding command-and-control addresses — a property of the capture, not of
malice. Read them as strong *on this telemetry*, not strong in general; Chapter
8's transfer results vindicate the caution.

## 3.5 What the EDA commits the model to

**No small feature subset will carry the classifier.** Dataset 2 offers 35 weak,
partially redundant signals with a top effect of 0.234; Dataset 1 offers six
features above |r| = 0.2 and a long flat tail. Lift has to come from
*conjunctions* — a long token **and** a base64 run **and** a `/dev/tcp` redirect
— not from any feature in isolation. That is the argument for the hybrid
lexical-plus-engineered representation, and it is visible in the results: the
engineered-only XGBoost reaches F1 0.786 on Dataset 1 where the hybrid reaches
0.876.

**Scale must be handled in the pipeline, not assumed away.** The raw-magnitude
features that dominate the variance ranking (`len_chars`, `max_token_len`) would
swamp any distance-, linear- or neural-based learner, while the bounded ratios
(`special_ratio`, `digit_ratio`) already encode obfuscation without the scale
baggage. Trees are indifferent; everything else is not. This is what Chapter 5.3
standardises, fitted inside the training fold only.

**Any feature that flips sign between corpora is one a cross-domain model must
not lean on.** `len_chars`, `n_quotes` and `n_flags` are individually useful
in-domain and individually harmful across domains, and their combined in-domain
weight is precisely why strong hold-out performance coexists with transfer
collapse. Dataset 2 is the harder corpus for a reason visible here: its *benign*
traffic is adversarially close to attack vocabulary, which shifts the burden from
recognising exotic attack tokens to modelling how ordinary ones combine.
