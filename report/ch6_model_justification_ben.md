# Chapter 6 — Model Selection & Academic Grounding (Ben's 2 models)

> Ben owns the justification + 1 grounding paper for XGBoost and 1D-CNN
> (traditional-supervised and deep-learning paradigms). Noam covers Random
> Forest and Isolation Forest.

## 6.1 Architectural justification

**XGBoost (gradient-boosted decision trees) — traditional supervised.** Our
engineered features (`src/features.py`) are a low-dimensional, heterogeneous
tabular vector: integer counts (`n_pipes`, `n_redirect_out`), boolean flags
(`has_dev_tcp`, `has_fetch_bin`) and real-valued ratios
(`special_ratio`, `digit_ratio`), with strong *threshold* and *conjunction*
effects — e.g. "a fetch tool **and** a pipe **and** a shell" (Row B1). Gradient-
boosted trees are structurally ideal: axis-aligned splits learn exactly those
conjunctive threshold rules, they need no feature scaling and are invariant to
monotonic transforms of mixed-scale inputs, and additive boosting composes weak
rules into the multi-condition logic a security analyst actually uses. Class
imbalance is handled natively through `scale_pos_weight` (cost-sensitive
gradient reweighting) rather than resampling, so no synthetic shell commands are
fabricated.

**1D-CNN over character sequences — deep learning.** A shell command is a short
1-D character signal whose malicious meaning is carried by *local* motifs —
`-e /bin/sh`, `>&`, `0<&1`, `/dev/tcp`, a base64 blob — that can occur at any
offset in the line. A 1-D convolution is translation-invariant: each filter is a
learned character-n-gram detector that fires on its motif wherever it appears,
and global max-pooling keeps the strongest evidence regardless of position. This
is the right inductive bias when attackers pad, reorder, or relocate payloads,
and it complements the engineered-feature track by reading the raw text the hand
features summarise. Imbalance is handled with a class-weighted cross-entropy
(the sequence analogue of `scale_pos_weight`).

## 6.2 State-of-the-art literature grounding

**XGBoost.** Trizna, Demetrio, Biggio & Roli, *"Robust Large-Scale Detection of
Living-Off-the-Land Reverse Shells via Data Synthesis,"* **ACM TOPS 2026**
(arXiv:2402.18329), the QuasarNix system — the same threat as ours. Their
gradient-boosted decision tree (100 estimators, max depth 10) over tokenized
one-hot/TF-IDF command features was the strongest tabular detector in the paper:
**TPR 99.94%, F1 99.98%, AUC 1.000 at FPR 1e-5** on enterprise auditd telemetry
augmented with template-synthesized reverse shells. This directly validates
boosted trees on tokenized Linux shell commands and is the benchmark our Ch8.3
compares against.

**1D-CNN.** Hendler, Kels & Rubin, *"Detecting Malicious PowerShell Commands
using Deep Neural Networks,"* **ACM AsiaCCS 2018** (arXiv:1804.04177). Character-
level CNN detectors over **6,290 malicious / 60,098 clean** commands reached
**AUC 0.985–0.990**, with a CNN+NLP ensemble best. Though the interpreter is
PowerShell, the setting is identical to ours — classify a single command line
from its raw characters — and it is the canonical demonstration that a
character-CNN captures command-line maliciousness. *(Their exact TPR-at-fixed-FPR
could not be re-verified from the encoded PDF; the AUC range and dataset counts
are confirmed from the paper.)*
