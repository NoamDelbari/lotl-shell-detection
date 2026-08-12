# Executive Summary

**Problem.** Living-off-the-Land attacks (MITRE ATT&CK **T1059.004**, Unix Shell)
execute entirely through binaries the operating system already ships — `curl`,
`tar`, `python`, `base64`. Nothing malicious is written to disk, so signature
and file-reputation controls have nothing to inspect; the only surviving
telemetry is the command line itself. This project asks whether a shell command
string, in isolation, carries enough signal to separate an attacker's use of a
system binary from an administrator's.

**Data and method.** We built two corpora with **provenance-based labelling** —
a command's label comes from where it was collected, never from a keyword rule,
so the labels cannot encode the answer. **Dataset 1** (15,248 commands) is
curated: offensive material from HackTricks, GTFOBins and Atomic Red Team
against documentation and tutorial corpora. **Dataset 2** (9,576 commands) is
operational: a Cowrie honeypot against real user shell history. Both are 25%
malicious, so a detector that flags everything scores **F1 = 0.400** — the
do-nothing floor every result below is measured against. Train/test splits are
**grouped by command shape**, not random, so no near-duplicate straddles the
split; this is stricter than the ungrouped cross-validation the comparable
literature uses and it costs us several F1 points. We engineered **43
behavioural features**, selected from 68 candidates by a documented audit, and
trained five detectors plus a character n-gram baseline.

| model | D1 F1 | D2 F1 | D1 FPR | D2→D1 transfer F1 |
|---|---:|---:|---:|---:|
| char n-gram baseline (TF-IDF + LR) | **0.8975** | **0.8824** | 0.0385 | 0.2740* |
| XGBoost-hybrid | 0.8761 | 0.8482 | 0.0415 | 0.2756 |
| 1D-CNN | 0.8603 | 0.8384 | 0.0555 | 0.3587 |
| Random Forest | 0.7963 | 0.7531 | 0.0337 | 0.1432 |
| XGBoost | 0.7856 | 0.7557 | 0.0717 | 0.2349 |
| Isolation Forest | 0.2492 | 0.1431 | 0.0079 | 0.2407 |

\* The baseline's transfer cell is measured on all rows of the target corpus
rather than its test split, so it is indicative rather than directly comparable
with the five model rows above (§8.2).

**Findings.** In-domain detection works: the best engineered model reaches F1
0.876 at a 4.2% false-alarm rate. Three results matter more than that headline,
and the report leads with all three rather than qualifying them at the end.
First, **the untuned character n-gram baseline beats all five
engineered-feature models on both corpora**, and beats the strongest of them on
false alarms as well (3.9% against the hybrid's 4.2%). Forty-three
hand-designed, threat-mapped features do not out-perform a bag of character
n-grams — which independently confirms the central representational claim of
the ShellCore paper we benchmark against.
Second, **cross-corpus transfer collapses below the do-nothing floor**: trained
on operational traffic and tested on curated attacks, all six models score
between 0.14 and 0.36 against a floor of 0.400. Models this accurate in-domain
are learning corpus style, not attacker behaviour. Third, **the recommended
three-stage cascade is beaten by a single decision threshold** on the
supervised model it contains, so we recommend against deploying it.

**Contribution.** The project's value is not a state-of-the-art number. It is a
measured decomposition of the 20-point gap to published work into two halves —
≈10 points representation, ≈10 points corpus-and-protocol; an error forensics
showing that 100% of the Random Forest's missed attacks sit at the benign end of
every high-signal feature; and a
quantified ceiling — **+3.7 F1** — for the LLM arbitration layer, on the 5% of
traffic where the best model is near-chance.
