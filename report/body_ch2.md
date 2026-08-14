# Chapter 2 — Literature Review

## 2.1 Two papers, two theories of where performance comes from

**Both assigned papers take the shell command string as the unit of detection,
then disagree about where the detection power lives — ShellCore in the encoding,
Trizna's line in the corpus — and each proves its case with the ablation the
other never runs.** Paper A, ShellCore (Alasmary et al., *IEEE IoT-J* 9(4), 2022;
arXiv:2103.14221), rebuilds its vocabulary from the malware samples alone and
term-level file classification falls from 99.08 to 67.48, while the character
model holds 99.91 → 99.79: a representation that collapses once it stops seeing
the benign corpus was encoding that corpus. Paper B, Trizna et al. (*ACM TOPS*
2026; QuasarNix, arXiv:2402.18329), began there too — its SLP predecessor (2021)
lifted a classifier from F1 0.392 to 0.874 on `auditd` telemetry by tokenising
shell-aware — then moved to the data, and to scoring at FPR 10⁻⁵ where headline
accuracy stops flattering.

**Table 2.1 — Comparison matrix: the two assigned papers on the dimensions this
project had to decide.**

<!-- cols: 1.20 2.65 2.65 -->
| Dimension | A — ShellCore (2022) | B — QuasarNix / TOPS (2026) |
|---|---|---|
| Malicious data | 178,261 commands regex-extracted from 2,891 IoT binaries, never observed executing | >1M synthetic reverse shells from ~34 templates |
| Benign data | 1.63M rows, **99.65% HTTP payloads**; 5,772 real history lines | real command corpora, variability preserved |
| Encoding | term- and character-level bag-of-words, 1–5-grams, PCA to 99.9% variance | shell-aware tokenisation plus classical encodings |
| Validation | plain 10-fold CV, no dedup or grouping | held-out split plus black-box evasion |
| Headline | 99.87 F1 at command level | ~90% detection lift at FPR 10⁻⁵ |
| Blind spot | never tested off its own corpus; median length 384 vs 14 chars nearly separates its classes | bounded by its ~34 seed templates |

## 2.2 Adopt, modify, reject

**Every verdict below rests on a measurement, three of them on ShellCore's own.**

**Table 2.2 — Adopt / modify / reject verdicts on the two papers, element by
element.**

<!-- cols: 1.70 1.00 3.80 -->
| Element | Verdict | Basis |
|---|---|---|
| Character-level representation | **Adopt**, re-encoded, raw block kept | Their ablation: 0.1 points lost against 32 for term-level. Distilled into the structural family (`n_pipes`, `special_ratio`, `has_pipe_to_shell`), rankable where an n-gram weight is not |
| Two representations of one string | **Adopt**, fused not parallel | Hybrid F1 0.8761 / 0.8482 against 0.7856 / 0.7557 for XGBoost on engineered features alone |
| Term-level learned vocabulary | **Modify** → fixed threat-mapped lists | The 99→67 collapse is proof it absorbed the corpus. Fixed lists are label-independent; their blind spot, unlisted binaries, is why the n-gram block stays |
| Unbounded 1–5-grams | **Modify** → bounded, in-fold | `char_wb` 3–5-grams, `min_df=3`, `max_features=3000`, fitted inside the pipeline as a `FeatureUnion` stage (`src/preprocessing.py:58-87`) |
| PCA to 99.9% variance | **Reject** | Chapter 4 must rank features against intuition; a dense component cannot be. ShellCore calls its space explainable, then projects it into one that is not |
| Ungrouped 10-fold CV | **Reject** | 1,273 regexes over 2,891 related binaries must yield near-duplication that unconstrained folds straddle. We split by command shape, zero groups straddling |
| Low-FPR reporting | **Adopt** | The hybrid's ROC-AUC is 0.979 / 0.968, its TPR at FPR = 0.1% only 0.5669 / 0.5261 |
| Synthesis, adversarial hardening | **Reject** — declared gap | Out of scope; our models are therefore untested against evasion |

## 2.3 Comparative essay: where this project sits between them

**Neither comparator reports what happens when the corpus changes; this project
makes that its object of study.** Both trust their labels; ours are *provenance*
labels — malicious because of where the command was collected — so the design
tests that assumption: cross-dataset D1↔D2 transfer, leave-one-source-out
recall, and a source-separability probe that recovers a line's corpus of origin
at **0.821 accuracy against a 0.298 majority baseline** across 11 corpora.

That stance also forces a reading of ShellCore's headline before Chapter 8.3 can
benchmark it. Its Table 2 implies 9.83% prevalence, its Table 5 gives 190,897
command-level rows — a factor of nine apart — and the balance is never stated.
Solving the reported (F1, FNR, FPR) triples row by row excludes the natural
reading — malicious-class F1 at 9.83%, mean residual 0.716 points — and admits
two within rounding: binary F1 on a balanced set, or support-weighted F1. **The
printed 99.87 is therefore not the malicious-class F1 at the prevalence the
paper's own tables imply**, the only quantity commensurable with ours; under the
support-weighted reading it reconstructs to 99.00–99.30. Chapter 8.3 decomposes
its gap to ShellCore against both readings, and the split barely moves.
