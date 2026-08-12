# Chapter 8.3 — Benchmarking Random Forest and Isolation Forest against ShellCore

> **Assembly note (§8.3).** The rubric asks that this section benchmark against
> the literature *"reviewed in Chapter 6"*. Both papers it compares against are
> cited in Chapter 6 (ShellCore arXiv:2103.14221 in §6.4–6.5; QuasarNix/TOPS
> arXiv:2402.18329 in Ben's §6.2), so the substance is aligned — only the
> cross-reference wording needs to say "Chapter 6" rather than "Chapter 2"
> in the .docx.

> Noam's half of 8.3 — the **ShellCore** comparator, for the two models he owns.
> Ben's `ch8_3_tops_comparison.md` covers the Trizna/QuasarNix comparator for
> XGBoost-hybrid and the CNN; the two are complementary, not overlapping.
> The metric reconstruction and the four non-comparability arguments are
> established in `ch2_3_comparative_contribution_noam.md` and are **cited here,
> not re-derived**. What is new in this chapter is the decomposition in the
> third section, which attributes the gap to measured causes rather than
> asserting one.

## The headline numbers, side by side

| system | corpus | protocol | F1 | do-nothing floor | headroom captured |
|---|---|---|---:|---:|---:|
| ShellCore char-level RF | IoT malware vs HTTP+bash | 10-fold CV, ungrouped | **0.9978** | 0.667 | 99.3% |
| ShellCore term-level RF | as above | as above | 0.9984 | 0.667 | 99.5% |
| **Our Random Forest, D1** | offensive corpora vs docs/history | shape-grouped 80/20 | **0.7963** | 0.400 | 66.0% |
| **Our Random Forest, D2** | Cowrie honeypot vs user history | shape-grouped 80/20 | **0.7531** | 0.400 | 58.9% |
| **Our Isolation Forest, D1** | as above | as above | **0.2492** | 0.400 | **−25.1%** |
| **Our Isolation Forest, D2** | as above | as above | **0.1431** | 0.400 | **−42.8%** |

Two things in that table need saying before anything else, because both are
uncomfortable and both are true.

First, **ShellCore's Random Forest beats ours by roughly 20 F1 points.** No
amount of protocol criticism makes that go away, and §8.3 does not attempt it.

Second, **our Isolation Forest scores below its own do-nothing floor on both
corpora.** At 25% prevalence a classifier that labels every command malicious
scores F1 = 0.400; the Isolation Forest scores 0.2492 and 0.1431. As a
standalone detector at its shipped operating point it is worse than trivial,
and the report states that rather than burying it in a table. The
qualification that matters is that F1 at a fixed 0.5 threshold is close to the
worst possible way to score this model: Chapter 7 shows its **ranking** is
sound (ROC-AUC 0.812 / 0.677, invariant to `contamination` to four decimals),
and Chapter 8.4 consumes its *score*, not its decision. A ranker with AUC 0.81
that is useless as a thresholded classifier is a coherent object, and it is
what we have.

## The metric question, in one paragraph

ShellCore's printed F1 cannot be read as the malicious-class F1 at the
prevalence its own Table 2 implies. `ch2_3` tests four candidate readings
against all six command-level rows: two fit within rounding (binary F1 on an
≈balanced set, 0.012 pts mean residual; support-weighted F1 at 9.83%
prevalence, 0.024 pts), and the natural reading is excluded at 0.716 pts. The
argument does not require choosing between the survivors. What matters for
this chapter is the consequence for the floor: under the balanced reading
ShellCore's do-nothing floor is **0.667**, not the 0.400 ours sits on, so the
raw 0.9978-vs-0.7963 comparison flatters ShellCore twice over — once on the
metric and once on the baseline it is measured against. Correcting for the
floor narrows the gap in *headroom* terms from 20 points to 33 percentage
points of headroom (99.3% vs 66.0%) — which is to say the correction does not
rescue our numbers and is not offered as if it did.

## Decomposing the gap: representation, or corpus?

The question the rubric actually asks is *why* the results differ, and
"different dataset, different features" is only an answer if it can be
apportioned. It can be, because this project already contains the missing
control.

Our `baseline` model is a `char_wb` 3–5-gram TF-IDF over the raw command string
feeding a logistic regression (`scripts/evaluate_baseline.py:312-316`), with a
44,781-term vocabulary on Dataset 1. Every baseline figure in this chapter is
read from `docs/baseline_metrics.json`, which that script writes at seed 42.
That is the same representation family as
**ShellCore's char-level LR** — character n-grams bounded at 5, frequency-encoded,
into a linear classifier — differing in two respects we can state exactly: our
weighting is sublinear TF-IDF rather than raw frequency, and we do not apply
their PCA step (rejected in `ch2_2` as a variance criterion imposed on a
sparse count space). Neither difference favours us. It never imports
`src/features.py`. So we can walk from our Random Forest to ShellCore's in two
steps, changing one thing at a time:

| step | what changes | F1 | delta |
|---|---|---:|---:|
| our Random Forest, D1 | — | 0.7963 | — |
| our `baseline`, D1 | engineered features → char n-grams (**same corpus, same protocol**) | 0.8975 | **+10.12** |
| ShellCore char-level RF | our corpus + grouped split → their corpus + ungrouped 10-fold CV | 0.9978 | **+10.03** |

The two steps sum to +20.15 points, which is the entire gap — and they are the
same size to within a tenth of a point. So the honest apportionment is almost
exactly **half representation, half corpus-and-protocol**. Neither cause
dominates, and the common defence that the difference is "just their easier
dataset" turns out to be about half of the truth rather than all of it.

The decomposition is robust to the metric question. Substituting the
reconstructed malicious-class F1 for the printed one (0.9930 rather than
0.9978, `ch2_3`) moves step 2 from +10.03 to +9.55, leaving the split at 51/49
and changing nothing about the conclusion.

Step 1 is a family comparison rather than a controlled ablation, since it swaps
the classifier (RF → LR) along with the representation. Two controls say the
classifier is not doing the work. Our `xgboost_hybrid` carries *both*
representations under a tree classifier and still reaches only 0.8761 — two
points *below* the char-only linear model despite having access to everything
that model uses and the 43 engineered features besides. And on Dataset 2 the
ordering repeats (baseline 0.8824, hybrid 0.8482, RF 0.7531). Across both
corpora and both classifier families, what moves the number is the presence of
character n-grams.

## ShellCore's central claim survives contact with our data

That last observation is the most substantive finding in this comparison, and
it runs *in ShellCore's favour*.

ShellCore's actual thesis is not "we got 99.87." It is that the **character-level
representation is the one that carries the signal**, evidenced by their
malware-only ablation, where term-level file classification collapses
99.08 → 67.48 (RF) and 97.16 → 66.67 (DNN) while the character-level columns
lose a tenth of a point (99.91 → 99.79, 99.28 → 99.26). We reproduce that claim
independently, on two corpora they never saw, under a grouped split they never
used: **our character n-gram baseline outperforms all five engineered-feature
models on both datasets** (D1 0.8975 vs the hybrid's 0.8761 and RF's 0.7963;
D2 0.8824 vs 0.8482 and 0.7531). Forty-three hand-designed, threat-mapped,
individually-justified features do not beat an untuned bag of 44,781 character
n-grams fitted by a linear model.

The correct conclusion is therefore split, and Chapter 8 should not blur it:

- **We reject ShellCore's evaluation protocol** — ungrouped folds over
  near-duplicate strings, a benign class that is 99.65% HTTP traffic with a
  standard deviation of 4.88 characters, and accuracy-first reporting
  (`ch2_3`, arguments 1–4). Those choices are why 0.9978 is not a number a
  defender would experience.
- **We confirm ShellCore's representational finding**, on our own data, with
  our own protocol. It is the part of the paper that transfers.

Our engineered features earn their place on interpretability and threat
traceability — Chapter 1.3 maps each of the 43 to a technique, which no
n-gram vector can do — and not on raw discriminative power. Stating that
plainly is more useful than the alternative.

## The four confounds, applied to these two models

`ch2_3` establishes them; their specific bite on RF and IF is worth one pass.
ShellCore's benign class is unencrypted network traffic, so its decision
boundary separates malware strings from HTTP payloads — a different and easier
problem than separating an attacker's `xz` from an administrator's, which is
the boundary Chapter 8.1 shows both our models actually fail on. That failure
mode is *unavailable* to ShellCore's setup: with a benign class of median
length 185 and standard deviation 4.88, no benign row can be confused with a
384-character malware string. Chapter 8.1's central result — that 100% of RF's
207 Dataset-1 misses sit at the benign end of every high-signal feature, and
that none of them contains a shell binary — is a measurement that ShellCore's
corpus construction makes impossible to obtain.

The Isolation Forest sharpens the point. ShellCore has no unsupervised
comparator, and structurally cannot: its malicious class is defined by 1,273
regex patterns applied to disassembled binaries, so the method presupposes a
labelled malicious corpus. Our Isolation Forest is the measurement of what
remains when that presupposition is dropped — one detector in this project
that could be deployed on a network where no attack has yet been labelled. Its
answer, AUC 0.81 in-distribution, is modest, and it is the only number here
that speaks to the cold-start case at all. Interestingly, it is also the only
model in the project that transfers *better* on the harder direction
(D2→D1 F1 0.2407 vs D1→D2 0.1481), because a notion of "normal" fitted to
operational traffic is less corpus-specific than a fitted decision boundary.

## The number neither paper reports

ShellCore reports no cross-corpus result, so nothing in it predicts what its
0.9978 becomes on a corpus it was not trained on. We measured ours:

| model | in-distribution (D1 / D2) | D1→D2 | D2→D1 |
|---|---|---:|---:|
| Random Forest | 0.7963 / 0.7531 | 0.5148 | 0.1432 |
| Isolation Forest | 0.2492 / 0.1431 | 0.1481 | 0.2407 |
| `baseline` (char n-gram) | 0.8975 / 0.8824 | 0.5844 | 0.2740 |

The baseline's two transfer figures are measured over *every* row of the target
corpus rather than its held-out split, which is how `evaluate_baseline.py`
reports them; the model never saw either set, so the comparison is fair, but
the row counts differ from the model rows above.

Our Random Forest falls to 0.1432 on the punishing direction. The character
representation — the one that survived every other test in this chapter —
reaches only 0.2740, worse than three of the engineered-feature models. Both
are below the do-nothing floor, and they are not exceptions:

> **On D2→D1 transfer, every one of the six models in this project scores
> below the do-nothing floor of 0.400** — `cnn1d` 0.3587, `xgboost_hybrid`
> 0.2756, baseline 0.2740, Isolation Forest 0.2407, XGBoost 0.2349, Random
> Forest 0.1432. On a corpus none of them was fitted to, a rule that flags
> every command beats all of them on F1.

That is the most important sentence in this chapter, and it is deliberately
placed against ShellCore's 0.9978 rather than tucked into a limitations
paragraph. It is the only figure in the comparison that was *measured rather
than assumed*, and it is what a defender deploying any of these systems on
unfamiliar traffic would actually experience. ShellCore reports no counterpart
to it — not a worse number, no number — and until it does, the two results are
not describing the same kind of claim. A single-corpus 0.9978 and a
cross-corpus 0.1432 are answers to different questions, and only the second
one is the question operational deployment asks.
