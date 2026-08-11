# Chapter 2.3 — Comparative Analysis: the ShellCore Contribution

> **Contribution block for the comparative essay (Ben drafts the combined
> section).** This supplies the ShellCore vertex and the head-to-head
> arithmetic; Ben supplies the QuasarNix/LotL vertex and the joining argument.
> The reconstruction in the second section is original to this report and is the
> quantitative basis for Chapter 8.3 — that chapter cites these numbers rather
> than re-deriving them.

## Where the two papers sit, and where we sit between them

The two works we compare against are solving different problems with the same
raw material, and this project's design is legible as a choice between them.

**ShellCore** (Alasmary et al., IEEE IoT-J 2022) is a *representation* paper. Its
contribution is the demonstration that a shell command string, encoded at the
character level, is sufficient to detect IoT malware — and that the character
encoding is the one that survives when the benign corpus is taken away. It
carries no hand-engineered behavioural features, no threat-model mapping, and
after PCA no interpretable feature space at all. Its evaluation is
in-distribution, single-corpus, and reported as accuracy first.

**QuasarNix** (Trizna et al., 2024, arXiv:2402.18329) is an *evaluation* paper.
It is LotL-specific rather than malware-specific, it addresses data scarcity by
synthesising attack commands rather than harvesting them, and — the part this
project borrowed most directly — it insists on reporting at industrially
meaningful operating points, low fixed false-positive rates rather than
headline accuracy, and on adversarial robustness as a first-class result.

This project sits deliberately between them: **ShellCore's representational
insight, re-encoded as QuasarNix-style behaviour-aware interpretable features,
and evaluated under a protocol stricter than either** — shape-grouped splits, a
stated do-nothing floor on every F1, a second corpus sharing no source with the
first, and a TPR-at-fixed-FPR operating point (0.5669 at FPR = 0.1% on
Dataset 1). Chapters 5.2 and 8.2 exist because neither comparator reports what
happens when the corpus changes.

*Sourcing note:* the assigned "Trizna (2022) ACM TOPS" reference could not be
located; QuasarNix is named instead as the verifiable LotL comparator. See
`ch2_literature_review.md`.

## What ShellCore's 99.87 actually measures

ShellCore's headline is F1 = 99.87 at the command level. Before that can be set
beside our 0.8761 it has to be established what quantity it is, because the
paper's own numbers do not permit the obvious reading.

Table 2 gives 178,261 malicious commands against 1,635,650 benign — a
prevalence of **9.83%**. Table 5 gives the command-level dataset as
**190,897** rows. Those differ by a factor of nine and cannot both describe the
headline experiment, and the class balance is never stated in the text.

The reported triples are over-determined, so the question can be settled
arithmetically. Recall is fixed by the reported FNR; precision then depends only
on prevalence; F1 follows. Testing four candidate readings against all six
command-level rows:

| reading of the "F-1" column | mean abs. residual vs reported | max |
|---|---:|---:|
| binary (malicious-class) F1 on an ≈balanced set | **0.012 pts** | 0.025 |
| support-weighted F1 at Table 2's 9.83% prevalence | **0.024 pts** | 0.043 |
| macro-averaged F1 at 9.83% prevalence | 0.328 pts | 0.373 |
| **binary (malicious-class) F1 at 9.83% prevalence** | **0.716 pts** | 0.794 |

The first two fit within rounding; the last is excluded, missing every row in
the same direction by roughly seven tenths of a point. The conclusion does not
require choosing between the two survivors, which is what makes it robust:

> **Whichever reading is correct, ShellCore's printed F1 is not the
> malicious-class F1 at the prevalence its own Table 2 implies** — the only
> quantity directly comparable to the F1 reported throughout this project.

Both survivors are informative rather than damning. If the set was balanced,
the number is a fair binary F1 but its do-nothing floor is **0.667**, not the
0.179 that 9.83% prevalence would give. If the metric is support-weighted at
9.83% prevalence, then 90.2% of its weight sits on the benign class and it is
closer to accuracy than to a detection score. In that second case the
comparable quantity can be reconstructed from the reported FNR and FPR, and it
is still excellent: **99.00 to 99.30** across the six rows, best at char-level
DNN.

## Four structural reasons the operating points are not comparable

Independent of the metric question, four properties of ShellCore's corpus make
its decision boundary a different and easier one than ours. Each is sourced to
the authors' own tables or text.

1. **The benign class is 99.65% network traffic, not shell commands.**
   1,629,878 of 1,635,650 benign rows are unencrypted HTTP payloads; 5,772 are
   real shell history. Separating malware strings from HTTP requests is a
   different task from separating attacker commands from administrator
   commands, which is ours — both of our classes are genuine shell commands.
   The authors concede the point in Section 5.5: the benign set "may not be
   considered as a representative ground-truth benign dataset with an absolute
   confidence."

2. **Length nearly separates the classes.** Table 3: malware median 384
   characters, bash history median 14. More strikingly, the 1.6-million-row
   dominant benign source has a standard deviation of **4.88 characters** around
   a median of 185 — that is not a population of commands, it is one template at
   scale. Our `KNOWN_ISSUES` P3 documents the same shortcut in our own data;
   here it is available at a magnitude we never had.

3. **Near-duplication meets ungrouped folds.** 178,261 commands were extracted
   by applying 1,273 regex patterns across 2,891 binaries of a few botnet
   families. Plain 10-fold CV with no reported deduplication then places
   near-identical strings on both sides of the split. Our shape-grouped split
   forbids exactly this, at a measured cost to our headline number.

4. **The malicious commands were never observed executing.** They are strings
   pattern-matched out of static disassembly (Section 4.1), which biases the set
   toward commands that are pattern-matchable and includes strings that may never
   run. Dataset 2's attacks are commands intruders actually typed.

## Head-to-head

| system | corpus | reported F1 | its floor | headroom captured |
|---|---|---:|---:|---:|
| ShellCore char-DNN (balanced reading) | IoT malware vs HTTP+bash | 0.9987 | 0.667 | 99.6% |
| ShellCore char-DNN (reconstructed malicious-class F1 @ 9.83%) | as above | 0.9930 | 0.179 | 99.1% |
| **Ours, `xgboost_hybrid`, Dataset 1** | offensive corpora vs docs/history | **0.8761** | 0.400 | **79.3%** |
| **Ours, `xgboost_hybrid`, Dataset 2** | Cowrie honeypot vs user history | **0.8482** | 0.400 | **74.7%** |
| Ours, `xgboost_hybrid`, Dataset 1 → Dataset 2 | cross-corpus | 0.5319 | 0.400 | 22.0% |

The floor correction does not rescue our numbers, and it should not be presented
as if it did: under either reading ShellCore captures about 99% of the headroom
above its own floor and we capture three quarters of ours. The gap is real. The
argument of this section is that it is explained by the four confounds above
rather than by modelling quality — and the load-bearing evidence for that claim
is the last row. ShellCore never reports a cross-corpus result, and no published
figure tells us what its 99.87 would become on a corpus it had not been trained
on. Our own answer to that question, 0.5319, is the one number in this table
that was measured rather than assumed, and it is the number a defender would
actually experience.
