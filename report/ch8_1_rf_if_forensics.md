# Chapter 8.1 — Forensic Error Analysis: Random Forest and Isolation Forest

> Noam's half of 8.1 (Ben covers XGBoost-hybrid and the CNN in
> `ch8_1_error_forensics_ben.md`). Confusion matrices and per-source error
> counts are generated into `ch8_1_error_forensics_noam.md` by
> `analysis/ch8_error_analysis.py`; the overlap, recovery and feature-signature
> figures below come from `analysis/ch8_1_rf_if_forensics.py`
> (`results/ch8_1_rf_if_forensics.json`), which refits all three models and
> keeps **every** test-row prediction rather than the 40-row samples in
> `results/ch8_failures.json`.

## The two models fail in different currencies

| model | dataset | TN | FP | FN | TP | F1 | recall | FPR |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Random Forest | 1 | 2210 | 77 | 207 | 555 | 0.796 | 0.728 | 0.034 |
| Random Forest | 2 | 1362 | 74 | 145 | 334 | 0.753 | 0.697 | 0.052 |
| Isolation Forest | 1 | 2269 | 18 | 651 | 111 | 0.249 | 0.146 | 0.008 |
| Isolation Forest | 2 | 1422 | 14 | 441 | 38 | 0.143 | 0.079 | 0.010 |

Random Forest trades recall for precision, and the trade only pays on one
corpus. On Dataset 1 it returns the lowest false-positive rate of any
supervised model in the project (0.034, against the hybrid's 0.042 and
XGBoost's 0.072) and buys it by missing 27% of the attacks. On Dataset 2 the
advantage evaporates: at 0.052 it is no longer the most conservative — the
hybrid (0.049) and the TF-IDF baseline (0.040) both run cleaner — while it
still misses 30% of the attacks. The conservatism is a property of the
curated corpus, not of the model, which is the first hint that Chapter 8.4
should cascade rather than simply ship the Random Forest. The
Isolation Forest is not making the same trade more aggressively — it is doing
something different. It never saw a malicious label, so its errors are not
mistakes about attacks but disagreements about what "normal" covers, and at the
shipped fixed-0.5 threshold it sits in an extreme-precision corner (Chapter 7
shows this is threshold placement, not ranking quality: ROC-AUC 0.812 / 0.677).

## What the Random Forest misses is not a modelling failure

The natural assumption is that 207 missed attacks represent capacity the model
lacks. Measuring them says otherwise. Comparing the missed attacks against the
attacks the same model caught, the misses are displaced *toward the benign
mean* on every feature that carries signal. Two columns quantify that: `z vs
caught` is the gap in units of the caught-attack standard deviation, and
`position` rescales each feature so **0 = the benign mean and 1 = the
caught-attack mean**, which puts all eight on one comparable axis.

**Dataset 1** — the eight features on which the misses look most benign

| feature | missed | caught | benign | z vs caught | position |
|---|---:|---:|---:|---:|---:|
| `special_ratio` | 0.138 | 0.203 | 0.143 | −0.84 | −0.07 |
| `n_abs_paths` | 0.130 | 0.851 | 0.091 | −0.83 | 0.05 |
| `has_shell_bin` | **0.000** | 0.305 | 0.008 | −0.66 | −0.03 |
| `n_redirect_out` | 0.048 | 0.391 | 0.058 | −0.55 | −0.03 |
| `max_token_len` | 11.55 | 17.76 | 11.68 | −0.46 | −0.02 |
| `has_dev_null` | 0.005 | 0.182 | 0.004 | −0.46 | 0.01 |
| `n_sensitive_paths` | 0.029 | 0.339 | 0.018 | −0.45 | 0.03 |
| `digit_ratio` | 0.030 | 0.080 | 0.021 | −0.40 | 0.16 |

On a scale where the caught attacks sit at 1, RF's missed attacks score between
**−0.07 and +0.16** on all eight — they are at the benign end of every one of
them. The point is not that the misses are literally indistinguishable from
benign traffic; on `n_abs_paths`, `n_sensitive_paths` and `digit_ratio` they do
sit slightly above the benign mean. It is that the margin above benign is a
few percent of the distance to a typical caught attack. **Not one of the 207
missed attacks contains a shell binary.** These are not attacks the model
failed to recognise; they are attacks that, in the 43-dimensional space the
model is given, are located inside the benign cloud.

Two controls confirm the reading. First, **none** of the 207 missed strings
(nor any of Dataset 2's 145) appears anywhere in the benign training rows, so
this is not a duplicate-label artefact — the shape-grouped split guarantees
these are structurally novel commands. Second, the length statistics invert
between corpora exactly as Chapter 5.2 predicts they must:

| | missed | caught | benign |
|---|---:|---:|---:|
| Dataset 1 mean `len_chars` | **38.6** | 57.2 | 37.3 |
| Dataset 2 mean `len_chars` | **52.7** | 46.5 | 38.9 |

On Dataset 1, where length is a positive attack signal (δ +0.247), the missed
attacks are the short ones and sit essentially on the benign mean. On Dataset 2,
where the same feature reverses (δ −0.171), the missed attacks are the *long*
ones. In both cases the model misses whatever falls on the benign side of its
own corpus's length prior — the same prior Chapter 5.2 shows does not transfer.
The error analysis and the shift analysis are describing one phenomenon from
two directions.

Dataset 2's signature is the same shape with different carriers, and on the
same rescaled axis its eight span **−0.50 to +0.24**: `has_fetch_bin` (missed
0.035, caught 0.255, benign 0.030 — position 0.02), `has_hidden_path` (0.01),
`head_is_shell` (0.01), `has_url` (0.10), `digit_ratio` (0.24), with
`has_hex_escape` at exactly zero across all 145 misses. Every carrier is a
delivery marker: the missed honeypot attacks are the ones that do not fetch,
do not spawn a shell and do not carry an obfuscated payload. They are
reconnaissance, not delivery — which is consistent with Dataset 2 being live
Cowrie traffic, where the early-stage probing that never escalates is the bulk
of what an attacker actually types.

## The two models disagree about false alarms, not about attacks

The interesting question for a cascade is whether the two models are
complementary. Measured exactly, they are — but not in the direction one would
expect.

| | Dataset 1 | Dataset 2 |
|---|---|---|
| RF misses also missed by IF | **207 of 207** | 137 of 145 |
| attacks IF catches that RF misses | **0** | **8** |
| false positives shared by both | 5 | 1 |
| FP Jaccard | 0.056 | 0.011 |

**On Dataset 1, the Random Forest's false negatives are a strict subset of the
Isolation Forest's.** There is not a single attack in the Dataset 1 test split
that the unsupervised detector catches and the supervised one misses. As a
source of additional recall, the Isolation Forest contributes exactly nothing
there — a result worth stating plainly, because the intuition that an anomaly
detector will "cover a different part of the space" is precisely what the
measurement refutes.

Their **false positives**, by contrast, are almost disjoint — 5 shared out of
90 on Dataset 1, 1 out of 87 on Dataset 2. The two models have essentially
uncorrelated notions of which benign command looks suspicious. Reading the
false alarms by benign source shows the two corpora behave differently:

| Dataset 1 benign source | n | RF flags | IF flags |
|---|---:|---:|---:|
| `linlm` | 145 | **12.4%** (18) | 0.7% (1) |
| `bash6k` | 116 | **12.1%** (14) | **6.0%** (7) |
| `nl2bash` | 306 | 7.8% (24) | 2.6% (8) |
| `tldr` | 935 | 2.0% (19) | 0.2% (2) |
| `bash_instruct` | 785 | 0.3% (2) | 0.0% (0) |

| Dataset 2 benign source | n | RF flags | IF flags |
|---|---:|---:|---:|
| `bash_history` | 1,026 | **5.9%** (61) | 0.2% (2) |
| `commandlinefu` | 410 | 3.2% (13) | **2.9%** (12) |

On Dataset 1 the two models rank the benign sources almost identically —
`bash6k` and `linlm` are hardest for both — yet they still share only 5 of 90
flagged rows. Same sources, different rows: the disagreement is at the level
of the individual command, not the corpus. That is precisely the condition
under which combining two models helps, and it is invisible to the per-source
error tables in `ch8_1_error_forensics_noam.md`.

Dataset 2 shows the sharper effect. 82% of the Random Forest's false alarms
land on `bash_history` and 86% of the Isolation Forest's land on
`commandlinefu` — an inversion, given that `bash_history` supplies 71% of the
benign rows and `commandlinefu` only 29%. In rate terms the Isolation Forest
fires on `commandlinefu` roughly fifteen times as often as on user history,
though with only two `bash_history` alarms that multiple is loosely
determined; the composition figures are the robust version of the claim.
Either way the direction is what the two training objectives predict.
`commandlinefu` is a corpus of deliberately clever shell tricks, so it is
genuinely far from the centre of "normal" — the Isolation Forest is not wrong
about that, it is answering the question it was asked. The Random Forest,
trained against labels, has learned that unusual is not the same as malicious,
and its residual false alarms fall instead on everyday history that happens to
share surface features with attacks.

## What the Isolation Forest is actually for

Dataset 2's eight IF-unique catches are the clearest evidence in this chapter
of the anomaly detector's real value, because they are not marginal:

```
echo "cd /tmp ; wget http://…/wget.sh || curl http://…/wget.sh ; chmod +x …"
LC_ALL=C /home/admin/.dhpcd -o 76.132.177.92:4444 -t4 --safe -B >/dev/null 2>/dev/null
echo "admin" | sh -c "sed '#/lib/libxml.so#d' /etc/ld.so.preload > /etc/ld.so.preload"
base64 --decode .threatstackcloudsecops | bash
```

A download cradle with a fallback fetcher, a hidden miner dialling a
non-standard port, `ld.so.preload` rootkit persistence, and a base64 pipe into
a shell. These are far from any benign pattern in norm terms, which is what an
isolation-based method measures — and they arrive on the operational corpus,
not the curated one. Eight rows is not a case for deploying the model
standalone. It is a case for consuming its *score* alongside a supervised
one, which is what Chapter 8.4's cascade does.

## The cascade premise, measured

The motivating question for Chapter 8.4 is whether a stronger model recovers
what the Random Forest misses. It substantially does:

| | Dataset 1 | Dataset 2 |
|---|---:|---:|
| RF false negatives | 207 | 145 |
| recovered by XGBoost-hybrid | **123 (59.4%)** | **83 (57.2%)** |
| missed by both | 84 | 62 |
| newly missed by the hybrid (RF caught them) | 10 | 12 |

Recovery is broad rather than concentrated. Against each source's share of the
Dataset 1 miss set, the hybrid rescues 58 of 111 `hacktricks` misses (52%), 35
of 52 `gtfobins` (67%), 26 of 39 `atomic_red_team` (67%), 3 of 3 `payloads` and
1 of 2 `slp` — a similar fraction everywhere rather than one source carrying
the result, so the character n-gram block is adding general lexical coverage
rather than rescuing a single style of payload.

What the recovery costs differs by corpus, and the difference matters for 8.4.
On Dataset 1 the hybrid runs 95 false positives against the Random Forest's 77,
so there the extra recall is genuinely bought with false alarms. On Dataset 2 it
runs 71 against 74 — fewer errors of *both* kinds, so the hybrid simply
dominates. The cascade therefore has something to justify on the curated corpus
and nothing to justify on the operational one, which is the reverse of the
usual expectation and should be stated as such rather than averaged away.

The residual is the honest part. The 84 attacks both models miss on Dataset 1
and the 62 on Dataset 2 are dominated by bare invocations carrying no argument
content at all — `bconsole`, `apparmor_parser`, `aptitude changelog aptitude`,
`xz`, `nano u.txt`, `ls -1 /etc/pam.d`. There is no feature, engineered or
learned, that separates `xz` typed by an intruder from `xz` typed by an
administrator, because the strings are identical and the intent is not in the
artefact. This is the **unlearnable overlap** named as failure mode 1 in
Chapter 1.1, now counted: it accounts for 11.0% of Dataset 1's test attacks and
12.9% of Dataset 2's, and it is the ceiling that no amount of modelling in this
project can raise. Lifting it requires telemetry this project deliberately does
not use — process ancestry, session context, timing — and that boundary is a
scoping decision recorded in Chapter 1.1, not a defect to be tuned away. It is
the single most useful thing to hand to future work.
