# Chapter 2 — Literature Review

## 2.1 Two papers, two theories of where performance comes from

**Both papers take the shell command string as the detection unit, then disagree
about where the power lives — encoding (A, ShellCore) or corpus (B, Trizna's
line).** Rebuild ShellCore's vocabulary from the malware alone (Alasmary et al.,
*IEEE IoT-J* 9(4), 2022; arXiv:2103.14221): term-level file classification falls
99.08 → 67.48 while the character model holds 99.91 → 99.79. Trizna et al.
(*ACM TOPS* 2026; QuasarNix, arXiv:2402.18329) move to the data and FPR 10⁻⁵.

**Table 2.1 — The two papers compared.**

<!-- cols: 1.20 2.65 2.65 -->
| Dimension | A — ShellCore (2022) | B — QuasarNix / TOPS (2026) |
|---|---|---|
| Malicious data | 178,261 commands regexed from 2,891 IoT binaries, never observed executing | >1M synthetic reverse shells, ~34 templates |
| Benign data | 1.63M rows, **99.65% HTTP payloads**; 5,772 history lines | real corpora, variability preserved |
| Encoding | term/character-level bag-of-words, 1–5-grams, PCA to 99.9% variance | shell-aware tokenisation |
| Validation | 10-fold CV, no dedup or grouping | held-out split, black-box evasion |
| Headline | 99.87 F1 at command level | ~90% detection lift at FPR 10⁻⁵ |
| Blind spot | untested off-corpus; median length 384 vs 14 chars nearly separates classes | bounded by ~34 seed templates |

## 2.2 Adopt, modify, reject

**Every verdict rests on a measurement, three on ShellCore's own.**

**Table 2.2 — Adopt / modify / reject.**

<!-- cols: 1.70 1.00 3.80 -->
| Element | Verdict | Basis |
|---|---|---|
| Character-level representation | **Adopt**, re-encoded | Their ablation: 0.1 points lost against 32 for term-level. Distilled into structural features (`n_pipes`, `special_ratio`, `has_pipe_to_shell`), rankable unlike n-grams |
| Two representations, one string | **Adopt**, fused | Hybrid F1 0.8761 / 0.8482 against XGBoost's 0.7856 / 0.7557 on engineered features |
| Term-level learned vocabulary | **Modify** → fixed threat-mapped lists | The 99→67 collapse proves corpus absorption. Fixed lists are label-independent; their blind spot, unlisted binaries, keeps the n-gram block |
| Unbounded 1–5-grams | **Modify** → bounded, in-fold | `char_wb` 3–5-grams, `min_df=3`, `max_features=3000`, fitted in-pipeline (`src/preprocessing.py:58-87`) |
| PCA to 99.9% variance | **Reject** | Chapter 4 must rank features against intuition; a dense component cannot be |
| Ungrouped 10-fold CV | **Reject** | 1,273 regexes over 2,891 related binaries must yield near-duplication unconstrained folds straddle; we split by command shape, zero straddling |
| Low-FPR reporting | **Adopt** | Hybrid ROC-AUC 0.979 / 0.968 against TPR 0.5669 / 0.5261 at FPR = 0.1% |
| Synthesis, adversarial hardening | **Reject** — declared gap | Out of scope; our models untested against evasion |

## 2.3 Comparative essay: where this project sits between them

**Neither comparator reports what happens when the corpus changes; this project
studies exactly that.** Ours are *provenance* labels, malicious by collection
site, so we test it: cross-dataset D1↔D2 transfer, leave-one-source-out recall,
and a source-separability probe recovering a line's origin at **0.821 accuracy
against a 0.298 majority baseline** across 11 corpora.

ShellCore's Table 2 implies 9.83% prevalence against Table 5's 190,897
command-level rows, balance never stated. Solving its reported (F1, FNR, FPR) triples excludes malicious-class
F1 at that prevalence (mean residual 0.716 points) and admits two within
rounding, balanced or support-weighted. **The printed 99.87 is not the
malicious-class F1 commensurable with ours**; support-weighted it reconstructs to
99.00–99.30, and Chapter 8.3's decomposition barely moves.
