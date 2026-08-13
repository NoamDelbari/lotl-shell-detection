# Chapter 8 — Error Analysis, Generalization and Ensembling

## 8.1 Forensic error categorization

**Both leading models fail on the same commands, and the failures belong to the
label boundary rather than to model capacity.** On Dataset 1 the XGBoost-hybrid
makes 189 errors (94 FN, 95 FP) and the 1D-CNN 218 (91 FN, 127 FP) — the CNN
recovers three attacks for 32 extra false alarms. The errors are not independent:
59 false negatives are shared (63% of the hybrid's, 65% of the CNN's) and 61
false positives (64% and 48%). Two architectures with disjoint representations
converging on two-thirds of the same error set locates the residual in the data.
Full confusion matrices for all ten model × dataset combinations are in
**Table B.7**.

The errors sort into two categories (Table 8.1). **False negatives are
benign-looking LotL** — the curated privilege-escalation and recon one-liners of
`hacktricks`, `gtfobins` and `atomic_red_team` carry 93 of the hybrid's 94
misses, while the overtly malicious `quasarnix` and `payloads` reverse shells
produce none; 100% of the Random Forest's 207 misses sit at the benign end of
every high-signal feature and none contains a shell binary. **False positives are
dual-use administration**: `sudo iptables …`, `head /etc/passwd`, `find … -exec`.

Both categories are label artefacts as much as model errors. Forty-seven
Dataset-1 commands touch `/etc/passwd` — nine benign, 38 attack, with no lexical
feature separating them; the label follows the corpus a command was harvested
from, not the string. All seven occurrences of `chmod +s` are attack-labelled, so
the model has never seen a benign instance of a construct administrators
legitimately use. This is a ceiling, not a deficiency.

**Table 8.1 — Where the errors concentrate: Dataset-1 test-split errors by source
corpus for the two strongest models.** "shared" counts commands both get wrong;
attack rows are false negatives, benign rows false positives.

<!-- cols: 0.95 1.35 0.95 1.05 0.95 0.85 -->
| Class | Source corpus | rows in test | hybrid err. | CNN err. | shared |
|---|---|---:|---:|---:|---:|
| attack (FN) | `hacktricks` | 344 | 59 | 51 | 35 |
| attack (FN) | `gtfobins` | 189 | 19 | 22 | 14 |
| attack (FN) | `atomic_red_team` | 133 | 15 | 16 | 9 |
| attack (FN) | `slp` | 23 | 1 | 2 | 1 |
| attack (FN) | `quasarnix`, `payloads` | 73 | 0 | 0 | 0 |
| benign (FP) | `nl2bash` | 306 | 28 | 37 | 19 |
| benign (FP) | `tldr` | 935 | 29 | 39 | 15 |
| benign (FP) | `linlm` | 145 | 21 | 32 | 18 |
| benign (FP) | `bash6k` | 116 | 14 | 15 | 9 |
| benign (FP) | `bash_instruct` | 785 | 3 | 4 | 0 |

## 8.2 Cross-dataset variance

**No model here generalizes across corpora.** Every supervised model loses a
third to two-thirds of its F1 under transfer, and on the punishing D2→D1
direction all six score **below the do-nothing floor of 0.400** — a rule that
flags every command beats all of them. The cause is measured, not inferred: a
classifier predicting a command's *source corpus* from the same 43 features
reaches **0.821 accuracy against a 0.298 majority baseline** across 11 corpora.
The features carry corpus style, and style does not transfer. The failure mode is
precision — the hybrid's FPR climbs from 0.042 in-domain to 0.276 on D1→D2.

One ordering inverts: the **CNN, which trails in-domain, transfers best** (0.359
against the hybrid's 0.276 on D2→D1), because character-level features share
sub-word structure across registers where engineered counts latch onto
corpus-specific token distributions. Representation governs generalization more
than in-domain accuracy does.

**Table 8.2 — Cross-dataset transfer: in-domain F1 against transfer F1.** Bold
marks the best transfer score per direction. Model rows are scored on the target's
held-out split (n = 1,915 / 3,049); the *italicised* baseline row is scored over
**all** target rows (n = 9,576 / 15,248), so it is indicative rather than
directly commensurable.

<!-- cols: 1.90 1.25 1.25 1.05 1.05 -->
| Model | in-domain D1 | in-domain D2 | D1→D2 | D2→D1 |
|---|---:|---:|---:|---:|
| `xgboost_hybrid` | 0.876 | 0.848 | 0.532 | 0.276 |
| `cnn1d` | 0.860 | 0.838 | **0.541** | **0.359** |
| `random_forest` | 0.796 | 0.753 | 0.515 | 0.143 |
| `xgboost` | 0.786 | 0.756 | 0.495 | 0.235 |
| `isolation_forest` | 0.249 | 0.143 | 0.148 | 0.241 |
| *`baseline` (TF-IDF + LR)* | *0.898* | *0.882* | *0.584* | *0.274* |

## 8.3 Benchmarking against the literature

**Against ShellCore (arXiv:2103.14221).** Their character-level Random Forest
reports F1 0.9978 against our Random Forest's 0.7963 — a 20-point gap this report
does not explain away. It decomposes cleanly, because the project contains the
missing control: our `baseline` is a `char_wb` 3–5-gram TF-IDF into a logistic
regression — ShellCore's representation family — that never imports
`src/features.py`. Changing one thing at a time (Table 8.3) splits the gap almost
exactly in half: **≈10 points representation, ≈10 points corpus-and-protocol**.
Substituting the reconstructed malicious-class F1 (0.9930) for the printed one
moves the split only to 51/49.

**Table 8.3 — Decomposing the 20-point gap to ShellCore, one change at a time.**
The two deltas are equal to within a tenth of a point.

<!-- cols: 1.40 3.70 0.70 0.70 -->
| Step | What changes | F1 | Δ |
|---|---|---:|---:|
| Our Random Forest, D1 | — | 0.7963 | — |
| Our `baseline`, D1 | engineered features → char n-grams (*same* corpus and protocol) | 0.8975 | **+10.12** |
| ShellCore char-level RF | our corpus + grouped split → their corpus + ungrouped 10-fold CV | 0.9978 | **+10.03** |

Stated plainly: **our character n-gram baseline outperforms all five
engineered-feature models on both datasets** (D1 0.8975 vs the hybrid's 0.8761;
D2 0.8824 vs 0.8482). Forty-three hand-designed, threat-mapped features do not
beat an untuned bag of 44,781 character n-grams. We therefore **confirm
ShellCore's representational thesis** on two corpora it never saw, while
**rejecting its evaluation protocol** — ungrouped folds over near-duplicate
strings, and a benign class that is 99.65% HTTP traffic with a standard deviation
of 4.88 characters. Our features earn their place on interpretability and threat
traceability (§1.3), not raw discriminative power.

**Against Trizna et al. (ACM TOPS 2026 / QuasarNix, arXiv:2402.18329).** Their
central claim — that models trained without distribution-spanning augmentation do
not generalize across command distributions — is confirmed decisively by §8.2,
and their error profile matches ours mode for mode. That the same two failure
classes appear in a seq2seq anomaly detector, a gradient-boosted tree and a
character CNN is the strongest support for §8.1's conclusion that the label
boundary, not the architecture, is the binding limit. One asymmetry runs against
us: QuasarNix studies black-box evasion and adversarially robust defences, and
our models are untested against evasion — a genuine gap in this work.

## 8.4 Hybrid behavioural cascade

**This is a negative result and is reported as one.** The three-stage cascade
(Isolation Forest pre-filter → XGBoost-hybrid → LLM arbitration on the
[0.35, 0.65] uncertainty band) is the *weakest* of the four configurations
buildable from its own components, on both datasets (Table 8.4). Every stage
removes about as many true detections as false alarms — on Dataset 1, −31 FP for
−34 TP — so it buys precision by returning recall at par. Stage 1 clears only
6.8% / 4.3% of traffic, because its threshold is calibrated to retain 0.99 of
known training attacks rather than for throughput: the recall guarantee and the
analyst-fatigue saving are in direct tension, and this operating point
deliberately buys the former. And the whole apparatus is dominated by one number
— thresholding stage 2 alone at *p* ≥ 0.65 matches or beats the full cascade on
precision, recall *and* FPR on both datasets.

What would justify the architecture is arbitration that is actually correct: an
oracle on the same uncertainty band reaches F1 0.9132 / 0.8849, **+3.7 points
over the best single model**. That is the target the live LLM arbitration layer
(Bonus B.3) must be scored against, and the reason this design is reported
despite failing at its current operating point.

**Table 8.4 — Cascade ablation: every configuration of the same three
components.** The full cascade ranks last among the built configurations on F1
for both datasets; the oracle row is the ceiling arbitration would have to reach.

<!-- cols: 1.90 0.70 0.85 0.75 0.70 0.85 0.75 -->
| Configuration | D1 F1 | D1 recall | D1 FPR | D2 F1 | D2 recall | D2 FPR |
|---|---:|---:|---:|---:|---:|---:|
| XGBoost-hybrid alone | **0.8761** | 0.8766 | 0.0415 | **0.8482** | 0.8455 | 0.0494 |
| Stage 1 + 2 (no arbitration) | 0.8737 | 0.8714 | 0.0411 | 0.8463 | 0.8392 | 0.0481 |
| Stage 2 + 3 (no pre-filter) | 0.8716 | 0.8373 | 0.0280 | 0.8415 | 0.8038 | 0.0355 |
| Full three-stage cascade | 0.8685 | 0.8320 | 0.0280 | 0.8396 | 0.7975 | 0.0341 |
| *Cascade with oracle arbitration* | *0.9132* | — | — | *0.8849* | — | — |
