# Chapter 8.3 — Literature Benchmarking Discussion (Ben, vs TOPS/QuasarNix)

> Contrasts our empirical results (from `results/ch7_holdout.json` and
> `results/ch8_cross_dataset.json`) against the Ch6 benchmarks, defending the
> discrepancies. Ben benchmarks his two models against the TOPS paper; the
> ShellCore contrast (8.3 vs ShellCore) is Noam's.

**Operating point differs — this is the main reason our F1 looks lower.** TOPS
reports at an industry-grade fixed **FPR of 10⁻⁵–10⁻⁶** (GBDT TPR 99.94% @1e-5;
1D-CNN 99.30% @1e-6). We report at threshold 0.5 and at fixed FPR 1e-2/1e-3
(`tpr_at_fpr_*` in our metrics). A headline F1 near 0.99 at their operating
point is not comparable to ours at 0.5; the honest comparison is TPR at a
matched FPR, which is why our evaluation records it.

**Prevalence and label provenance differ.** TOPS trains on a synthesis-balanced
(~1:1) distribution over 50k-host enterprise auditd; we hold a deliberate **1:3
attack:normal** ratio with **provenance-based** labels. A 0.2%-looking FPR is far
more costly at our prevalence, so precision/FPR are not directly transferable.
We therefore lead with PR-AUC and per-source FPR, not accuracy.

**Curated-vs-real gap is the substantive finding.** TOPS's near-perfect numbers
rest on *template-synthesized* attacks; our Dataset 1 is partly curated
tradecraft and Dataset 2 is real honeypot capture. Our in-distribution scores
are strong but our **cross-dataset transfer** drops sharply (see 8.2) — exactly
the generalisation gap TOPS's synthesis machinery exists to close and which we
did not reproduce. We flag this as the fair, honest limitation rather than
quoting only the in-distribution number.

**What we can and cannot match.** We reproduce boosted-tree and character-CNN
detection of Linux shell commands and report P/R/F1/ROC-AUC/FPR + TPR-at-low-FPR.
We do **not** replicate TOPS's adversarial-robustness suite (11 shell-escape
perturbations, benign injection, adversarial training); absent that stress test,
our clean-split numbers likely overstate field robustness — noted as future work.

**A reporting advantage we do have.** Neither TOPS nor ShellCore reports
per-attack-family recall; our engineered families (LotL/GTFOBins, privesc,
evasion) let us report **per-source recall and per-source FPR** (Ch8.1), a fairer
and more informative benchmark than a single aggregate, and the mechanism by
which we show the model learned the technique rather than one generator.
