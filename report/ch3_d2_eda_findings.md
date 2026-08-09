# Chapter 3 — Exploratory Data Analysis Findings (Dataset 2)

Dataset 2 is the operational counterpart to Dataset 1's curated corpus: 7,661
training commands at the same engineered 1:3 attack:benign prevalence, where
every one of the 1,915 attacks is a command really typed (or scripted) by an
attacker into a Cowrie SSH honeypot, and the 5,746 benign commands are real
usage — 4,001 lines of practitioner `bash_history` plus 1,745 commandlinefu
one-liners. The command-length histogram (`ch3_length_hist_dataset2.png`,
density-normalized, clipped at the 99th percentile) immediately breaks the
headline regularity of Dataset 1: here the **benign** commands are longer on
average (mean 42.0 characters, median 27) than the **attacks** (mean 36.8,
median 21). What attacks have instead is dispersion — attack length variance is
11,780 versus 1,822 benign (6.5×), the attack p99 reaches 278 characters against
224 benign, and the single longest command in the corpus is a 3,450-character
attack payload against a benign maximum of 350. The distribution shape explains
the mechanism: honeypot traffic is dominated by short scripted fingerprinting
probes (`uname -a`, `cat /proc/cpuinfo`-style one-liners produce the sharp spike
at ~10 characters) punctuated by rare, enormous dropper payloads (the clipped
mass at the right edge of the figure). A length-alone probe now scores **AUC
0.415** — not merely weak, as its 0.611 on Dataset 1 was, but *below chance in
the direction that worked on Dataset 1*. The "attacks are longer" rule learned
from curated PoC one-liners is answered by live traffic with the opposite sign,
and this single reversal is the cleanest preview of the cross-dataset transfer
collapse quantified in Chapter 8.2.

The per-feature evidence (all 43 features: Mann-Whitney U with rank-biserial
effect sizes in `report/ch3_d2_feature_stats.csv`; top-15 variance gaps in
`ch3_variance_by_label_dataset2.png`) shows discrimination survives on
operational data but changes both magnitude and character. 35 of 43 features
separate the classes significantly (p < 0.05), yet the strongest effect is only
r = +0.234 — far below Dataset 1's leading effects — so Dataset 2 offers many
weak, partially redundant signals rather than a few strong ones. The profile
that emerges from the attack-leaning side is that of the automated botnet
dropper: `digit_ratio` leads (attack mean 0.083 vs 0.037 benign; a standalone
AUC of 0.617 — IP addresses, ports, hex identifiers, and numbered payload
filenames saturate honeypot traffic), followed by `has_fetch_bin` (21.9% of
attacks invoke `wget`/`curl`/`tftp`-class binaries vs 3.4% of benign),
`has_url` (13.6% vs 2.4%), `has_hidden_path` (14.7% vs 4.1% — dot-directories
for staging), `n_abs_paths`, `n_sensitive_paths` (attack mean 0.113 vs 0.032 —
`/etc/passwd`, `/proc` reconnaissance), `has_shell_bin`, `head_is_privesc`, and
`has_ipv4`. Base64 features, prominent on Dataset 1, are nearly informationless
here by rank (|r| ≤ 0.03) despite a huge attack-side variance in `b64_run_len`
(1,059 vs 68): encoded payloads exist in the honeypot stream but are too rare
to move the distribution's body.

| Feature | Attack mean | Benign mean | Effect (rank-biserial) | Direction |
|---|---:|---:|---:|---|
| `digit_ratio` | 0.083 | 0.037 | **+0.234** | attack |
| `len_tokens` | 4.29 | 5.85 | **−0.207** | benign |
| `mean_token_len` | 7.84 | 7.05 | +0.198 | attack |
| `has_fetch_bin` | 0.219 | 0.034 | +0.185 | attack |
| `len_chars` | 36.8 | 42.0 | −0.171 | benign |
| `n_flags` | 0.48 | 0.92 | −0.125 | benign |
| `head_is_lotl` | 0.013 | 0.131 | −0.118 | benign |
| `has_url` | 0.136 | 0.024 | +0.113 | attack |
| `n_quotes` | 0.31 | 0.78 | −0.112 | benign |
| `n_pipes` | 0.09 | 0.32 | −0.107 | benign |

The benign-leaning column of that table is the finding with the deepest
modeling consequences, because it inverts Dataset 1's flagship attack markers.
On Dataset 2, `head_is_lotl` (a command *led* by a living-off-the-land binary)
is ten times more common in benign traffic (13.1% vs 1.3%), and `has_lotl_bin`,
`n_pipes`, `n_quotes`, `n_flags`, and `has_long_flag` all point the same way.
The explanation is the benign pool, not the attacks: real administrators piping
`find` into `xargs`, quoting commit messages, and stacking long flags produce
exactly the shell plumbing and LotL vocabulary that a curated benign corpus
underrepresents, while Cowrie's scripted attackers issue terse, flagless
probes. A model trained on Dataset 1 — where LotL vocabulary and plumbing
density lean attack — meets the opposite conditional distribution here, which
is the feature-level mechanism behind both the shell-vocabulary inversion Ch4
documents and the D1→D2 F1 collapse; the cross-dataset distribution-shift
analysis in Chapter 5.2 builds directly on these pairs.

The correlation heatmap (`ch3_corr_heatmap_dataset2.png`) shows a redundancy
structure that is real but bounded, with no leakage-grade pairing. The
strongest correlation is `len_chars` ~ `len_tokens` at +0.906 — the familiar
"how big is this command" cluster Ben flagged on Dataset 1, joined by
`mean_token_len` ~ `max_token_len` (+0.783) and `len_tokens` ~ `n_quotes`
(+0.706) — and the by-construction family pairs `head_is_*` ~ `has_*_bin`
(+0.716 to +0.816; a command headed by an interpreter necessarily contains
one). Two pairs are informative rather than nuisance: `max_token_len` ~
`b64_run_len` (+0.743) says the longest tokens *are* the encoded blobs when
they occur, and `has_url` ~ `has_fetch_bin` (+0.675) says URLs arrive almost
exclusively inside fetch commands — the download-cradle conjunction itself.
Nothing exceeds 0.91 and nothing approaches the ≥0.95 near-duplicate band, so
no feature is dead weight; tree ensembles tolerate this level of collinearity,
and the linear/distance-based stages see it only after the in-pipeline
standardization (Ch5.3). The honest leakage caveat is distributional rather
than structural: `digit_ratio`, `has_ipv4`, and `has_url` earn part of their
Dataset-2 strength from Cowrie campaigns hard-coding C2 addresses — a corpus
property, not a property of malice — so their prominence here should be read
as "strong on this telemetry," not "strong in general," a caution Chapter 8's
transfer results vindicate.

Three takeaways carry into modeling. First, Dataset 2's signal is *wider and
flatter* than Dataset 1's: with a top effect of 0.234 and 35 significant
features, no small feature subset will carry the classifier, and the ceiling
on engineered-feature models is visibly lower — consistent with every model's
D2 holdout trailing its D1 counterpart (RF 0.758 vs 0.801 in the Ch7 grids;
Isolation Forest ranking AUC 0.677 vs 0.812). Second, the direction reversals
between the two datasets are not noise but a structural property of operational
telemetry: any feature whose sign flips between corpora (`len_chars`,
`n_pipes`, `head_is_lotl`) is a feature a cross-domain model must not lean on,
and their combined weight in-domain explains why in-domain excellence coexists
with transfer collapse. Third, the class-imbalance remedy is unchanged — the
1:3 prevalence is identical by construction — but the *benign* side is where
Dataset 2 is hard: its benign traffic is adversarially close to attack
vocabulary (admin LotL usage), which shifts the burden from detecting exotic
attack tokens to modeling conjunctions, exactly the regime where the hybrid
lexical+engineered representation earns its keep.
