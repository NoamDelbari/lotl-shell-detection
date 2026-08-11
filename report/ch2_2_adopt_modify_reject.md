# Chapter 2.2 — Adopt, Modify, Reject: What This Project Takes from ShellCore

> Decisions apply to `src/features.py` (43 engineered features),
> `src/preprocessing.py` (character n-gram block) and `src/models.py`
> (`xgboost_hybrid`, `cnn1d`). Evidence for each verdict is either ShellCore's
> own Table 4 ablation (Section 2.1) or our own selection audit
> (`report/ch3_feature_decisions.md`).

Six extraction elements were catalogued in Section 2.1. Each was accepted,
altered or refused on stated grounds, and the grounds are in every case
measurements rather than preference — in three of the five cases, ShellCore's
own measurements.

## Adopt — the character-level insight, and the two-representation design

**Verdict: adopt, but re-encode.**

The paper's central representational finding is that shell semantics live in
short tokens and operators, which is why its character model exists at all. We
accept that finding completely. We reject only the idea that a raw character bag
is the sole way to honour it.

The reason for re-encoding is the same reason the paper gives for the character
model in the first place, applied one step further. If `||`, `&&`, `cd` and `>`
are the informative units, then a feature that *counts* them is a strictly more
interpretable carrier of the same information than a feature that reports the
TF-IDF weight of the trigram `||&`. Our structural family — `n_pipes`,
`n_redirect_out`, `has_stderr_merge`, `n_quotes`, `special_ratio`,
`digit_ratio`, `has_pipe_to_shell` — is that distillation, and Chapter 4 ranks
each of those against domain intuition, which no character n-gram admits.

The re-encoding is not lossless, and we do not pretend otherwise, which is why
the character representation is retained *alongside* it rather than replaced.
`xgboost_hybrid` unions the 43 engineered features with a 3,000-column character
3–5-gram TF-IDF block, and `cnn1d` consumes raw character indices directly. That
architecture is itself inherited: ShellCore's design is two representations of
the same string evaluated in parallel, and ours is two representations of the
same string **fused**. The measured value of the fusion is not rhetorical — the
hybrid reaches F1 0.8761 on Dataset 1 and 0.8482 on Dataset 2, against 0.7856
and 0.7557 for XGBoost on the engineered features alone. That is roughly nine
F1 points on both corpora that our hand-written counts do not capture. It is a
family comparison rather than a controlled ablation, since the hybrid also
carries slightly larger trees (500 estimators at depth 7 against 400 at depth 6),
but a difference of that size is not a tree-budget effect.

Two things we tried in the spirit of the character model did not survive our own
gate, and are reported here rather than quietly dropped. `char_entropy` and
`token_entropy` — a natural "is this string compressed or obfuscated?" reading of
the character insight — were killed in the 68→43 selection for correlation-cluster
redundancy against `len_chars` and `len_tokens` respectively, and they were poor
candidates for a second reason visible in the audit: `char_entropy` separates the
classes at d = +0.29 on Dataset 1 and **d = −0.09 on Dataset 2**, a sign
inversion of exactly the kind Chapter 5.2 shows does not transfer.
`subshell_depth` and `n_backticks_subshell` failed the gate outright.

## Modify — term-level bag-of-words becomes a fixed, threat-mapped vocabulary

**Verdict: keep the question, replace the mechanism.**

Element 1 asks a good question — *which programs and keywords appear in this
command?* — and answers it with a vocabulary learned from the training corpus.
We keep the question and fix the vocabulary in advance: `has_shell_bin`,
`has_fetch_bin`, `has_lotl_bin`, `has_pkg_bin`, `head_is_privesc` and their
relatives are membership tests against lists chosen from the ATT&CK mapping in
Chapter 1.2, before any data was inspected.

The justification is ShellCore's own malware-only ablation. When the vocabulary
can no longer be shaped by both corpora, term-level file classification falls
from 99.08 to 67.48 (RF) and from 97.16 to 66.67 (DNN), while the character
representation moves by 0.1 points. A representation that loses two thirds of
its accuracy when it stops seeing the benign corpus was, to that extent,
encoding the benign corpus. That is the same failure mode our own
`P8-source-fingerprint` probe was written to catch, and it is the reason a
corpus-learned vocabulary is the wrong basis for a detector meant to survive a
change of corpus.

A fixed list has three properties a learned one does not: it is
label-independent, so it cannot absorb provenance; it is small, so it cannot
memorise; and every member carries a written rationale, so Chapter 4 can rank
it against intuition. The cost is real and is stated as a limitation — a fixed
list cannot recognise a binary nobody listed. The character n-gram block is the
coverage backstop for exactly that gap, which is the second reason the hybrid
keeps both representations.

## Modify — n-grams, bounded

**Verdict: adopt, with limits the paper does not impose.**

Unbounded 1–5-grams over a full corpus vocabulary produce a feature space large
enough that PCA becomes mandatory, which is how element 5 comes to exist. Our
block caps the order at 3–5 characters with `min_df=3` and
`max_features=3000`, and — the part that matters for validity — is fitted
**inside** the cross-validation fold as a `FeatureUnion` stage of the pipeline,
never on the full corpus (Chapter 5.3).

## Reject — PCA

**Verdict: reject.**

Chapter 4 of this project is required to rank interpretable features against
domain intuition and defend the ordering. A principal component is a dense
linear combination of thousands of character n-grams; it can be ranked by
importance but not argued about. There is also an internal tension in the paper
worth naming: ShellCore motivates the shell-command representation partly on the
grounds that it is explainable, and then projects it into a basis that is not.
We would rather carry 3,000 sparse columns a tree can split on than 200 dense
ones nobody can name. Dimensionality was never our binding constraint.

## Reject — the evaluation protocol

**Verdict: reject, and this is the largest departure.**

The elements above concern representation; this one concerns whether any
reported number means what it appears to mean, and it is where our design
diverges most sharply.

ShellCore evaluates with plain 10-fold cross-validation over 178,261 commands
extracted statically from 2,891 binaries of a small number of botnet families.
No deduplication is reported, and no grouping constraint. Commands recovered by
applying the same 1,273 regex patterns across thousands of related samples must
contain heavy near-duplication, and unconstrained folding then places
near-identical strings on both sides of the split. Our build reduces every
command to a structural skeleton and assigns whole shape groups to one side —
zero groups straddle either split, verified on the current build — precisely so
that test recall cannot be recall on a variant already seen (Chapter 1.1).

Second, the paper reports accuracy, F1, FNR and FPR without stating the class
balance of the evaluated set, and the balance cannot be recovered from the
paper: Table 2's totals imply 178,261 malicious against 1,635,650 benign
(9.83% prevalence), while Table 5 gives the command-level dataset as 190,897
rows. Those two accountings differ by a factor of nine and cannot both describe
the headline experiment. Section 2.3 resolves which one the reported metrics are
actually consistent with, and shows why the answer changes how the 99.87 should
be read.

Our reporting rule follows from that difficulty rather than from virtue: every
F1 in this report is quoted against the do-nothing floor for the prevalence it
was measured at — **0.400** at our 25% prevalence — and no headline number
appears without it.

## Summary of verdicts

| ShellCore element | Verdict | Basis |
|---|---|---|
| Character-level representation | **Adopt** (re-encoded + retained raw) | Their Table 4 ablation: 1.6% degradation vs 32 points for term-level |
| Two-representation architecture | **Adopt** (fused, not parallel) | Measured: hybrid 0.8761 vs engineered-only 0.7856 on D1 |
| Term-level learned BoW | **Modify** → fixed threat-mapped lists | Their 99→67 collapse shows the vocabulary encoded the corpus |
| n-grams (1–5, unbounded) | **Modify** → char 3–5, `max_features=3000`, in-fold | Dimensionality control without PCA; leakage safety |
| PCA (99.9% variance) | **Reject** | Chapter 4 requires rankable, nameable features |
| Plain 10-fold CV, unstated balance | **Reject** | Near-duplication across statically-extracted samples; F1 is uninterpretable without its floor |
