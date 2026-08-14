# Executive Summary

**Problem.** Living-off-the-Land attacks (MITRE ATT&CK **T1059.004**, Unix
Shell) execute through binaries the OS ships, leaving signature and
file-reputation controls nothing to inspect.

**Data and method.** Labels are **provenance-based**, never keyword rules
encoding the answer. **Dataset 1** (15,248 commands), curated: HackTricks,
GTFOBins and Atomic Red Team against documentation and tutorials; **Dataset 2**
(9,576 commands), operational: Cowrie honeypot against real shell history. Both
are 25% malicious: flagging everything scores **F1 = 0.400**, the do-nothing
floor. Splits are **grouped by command shape**, stricter than comparable work's
ungrouped cross-validation. **43 behavioural features** feed five detectors,
benchmarked against a character n-gram baseline.

| model | D1 F1 | D2 F1 | D1 FPR | D2→D1 transfer F1 |
|---|---:|---:|---:|---:|
| char n-gram baseline (TF-IDF + LR) | **0.8975** | **0.8824** | 0.0385 | 0.2740* |
| XGBoost-hybrid | 0.8761 | 0.8482 | 0.0415 | 0.2756 |
| 1D-CNN | 0.8603 | 0.8384 | 0.0555 | 0.3587 |
| Random Forest | 0.7963 | 0.7531 | 0.0337 | 0.1432 |
| XGBoost | 0.7856 | 0.7557 | 0.0717 | 0.2349 |
| Isolation Forest | 0.2492 | 0.1431 | 0.0079 | 0.2407 |

\* Measured on all target-corpus rows, not the test split; indicative, not
comparable (§8.2).

**Findings.** In-domain detection works; three results matter more. **The
untuned character n-gram baseline beats all five engineered-feature models on
both corpora**, confirming ShellCore's representational claim. **Cross-corpus
transfer collapses below the do-nothing floor**: all six score between 0.14 and
0.36, learning corpus style, not attacker behaviour. **The recommended
three-stage cascade is beaten by a single decision threshold** on its own
supervised model; we recommend against deploying it.

**Contribution.** A measured decomposition of the 20-point gap to published
work (≈10 points representation, ≈10 points corpus-and-protocol) and a
**+3.7 F1** ceiling for LLM arbitration.
