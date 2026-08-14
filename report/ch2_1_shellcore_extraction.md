# Chapter 2.1 — Feature Extraction in ShellCore

> Paper: H. Alasmary, A. Anwar, A. Abusnaina, A. Alabduljabbar, H. Abuhamad,
> A. Wang, D. Nyang, A. Awad and D. Mohaisen, *ShellCore: Automating Malicious
> IoT Software Detection Using Shell Commands Representation*, IEEE Internet of
> Things Journal 9(4), 2022 (arXiv:2103.14221). Every figure quoted below was
> read first-hand from the authors' Tables 1–5 and Sections 4.1–4.5 and 5.5;
> the local copy (`docs/refs/`) is deliberately untracked for licensing reasons.
> Section 2.2 gives the adopt/modify/reject decision for each element.

ShellCore is the closest published antecedent to this project: it is the only
work we found that treats the **shell command string itself** as the unit of
detection for Linux/IoT malware, which is exactly the premise argued in
Section 1.1. It therefore serves both as the source of our representational
insight and as the benchmark in Chapter 8.3. This section extracts what it
actually does; Section 2.2 argues about it.

## The extraction pipeline, element by element

The authors build two parallel representations of the same command corpus and
run the same three classifiers on each.

| # | Element | § | Mechanism | Security meaning claimed by the authors |
|---|---|---|---|---|
| 1 | **Term-level model** | 3.1.1, 3.3.1 | Bag-of-words; spaces and special characters act as tokenizers; **words shorter than three characters are discarded**; 1- to 5-grams | The "locality of the words" — which command words co-occur |
| 2 | **Character-level model** | 3.1.2, 3.3.2 | Tokenizers redeclared so that no character is ignored; every letter, digit and symbol becomes an individual feature; same bag and n-gram machinery | Recovers the operators (`\|\|`, `&&`) and short keywords (`cd`, `ls`) that element 1 throws away |
| 3 | **Frequency encoding** | 3.1.4 | Sparse occurrence-count vector over the corpus vocabulary | Token frequency is the signal |
| 4 | **n-gram proximity** | 3.1.5 | Contiguous n-token sequences (n ≤ 5) appended to the bag | Command *structure*, not merely content |
| 5 | **PCA** | 3.1.6 | Projection retaining **99.9%** of training-set variance | Purely computational — dimensionality reduction, no security semantics |
| 6 | **Classifiers** | 3.2, 4.3 | Logistic Regression, Random Forest, and a DNN whose five hidden layers were reached by tuning; K = 10 cross-validation | — |

Element 2 deserves emphasis because it is the paper's genuine contribution and
the part this project inherits. The authors do not present the character model
as an alternative encoding; they present it as a **repair**. Their own words
are that discarding sub-three-character words "presents a major shortcoming,
since a large number of command keywords have a length of fewer than three
characters, including `cd` and `ls`, or consist of special characters, such as
`||` and `&&`." A tokenizer built for English prose deletes precisely the
tokens that carry shell semantics. That observation — that the informative part
of a command is its operators and its short built-ins, not its long words — is
the finding this project's structural feature family is built on.

## The corpus, and why its construction matters

The malicious class comes from **2,891 IoT malware binaries** drawn from the
IoTPOT honeypot project, spread across eight instruction-set architectures with
ARM (23.11%) and MIPS (20.75%) dominant — the signature of embedded botnet
malware. The commands are recovered **statically**: each binary is disassembled
with Radare2, `strings` is run over the disassembly, 18 samples are examined by
hand to establish patterns, and those patterns — **1,273 of them** — are applied
mechanically to the remaining 2,873 samples, yielding **178,261 malicious
commands**.

The benign class is assembled from three sources, and its composition is the
single most consequential fact in the paper:

| Source | Sources | Commands | Median length | Std |
|---|---:|---:|---:|---:|
| PCAP Network 1 | 5 | 1,625,143 | 185 | **4.88** |
| PCAP Network 2 | 5 | 4,735 | 167 | 146.26 |
| Bash history | 9 volunteers | 5,772 | 14 | 27.71 |
| *(Malware)* | 2,891 | 178,261 | 384 | 168.03 |

**99.65% of the benign class is unencrypted network traffic, not shell
commands.** Only 5,772 rows — 0.35% — are commands a human being actually typed,
collected from nine volunteers' shell histories (~143 MB, hand-anonymised).
Network 1 alone contributes 1.6 million rows harvested from 28,578,754 captured
payloads, of which only the unencrypted 1,625,143 were usable.

Two properties of that table are worth stating explicitly because they are
visible in the authors' own numbers rather than inferred. First, the dominant
benign source has a **standard deviation of 4.88 characters across 1.6 million
rows**, with mean 184.68 and median 185. A distribution that tight over a corpus
that large is not a population of distinct commands; it is one HTTP request
template repeated at scale. Second, the length separation between classes is
large and monotone: benign bash history has median 14, malware has median 384.

## What the paper reports

At the command level, with both corpora represented, all six model/representation
combinations land within a tenth of a point of each other (Table 4, left):

| | Accuracy | F1 | FNR | FPR |
|---|---:|---:|---:|---:|
| Term-level LR | 99.86 | 99.86 | 0.03 | 0.20 |
| Term-level RF | 99.84 | 99.84 | 0.09 | 0.20 |
| Term-level DNN | 99.85 | 99.85 | 0.08 | 0.19 |
| Char-level LR | 99.87 | 99.87 | 0.12 | 0.15 |
| Char-level RF | 99.78 | 99.78 | 0.27 | 0.19 |
| Char-level DNN | 99.87 | 99.87 | 0.12 | 0.14 |

The paper then extends from commands to files, treating an application as the
concatenation of its commands, and reports up to 99.91 F1 there as well.

## The authors' own ablation — the most useful result in the paper

Section 4.5 asks what happens when the vocabulary is built **only from the
malware samples**, with no benign data allowed to shape it. This is the
paper's stress test, and the two representations come apart completely
(Table 4, right):

| | Term-level | Character-level |
|---|---:|---:|
| Command level (DNN) | 99.85 → **89.52** | 99.87 → **98.24** |
| File level (RF) | 99.08 → **67.48** | 99.91 → **99.79** |
| File level (DNN) | 97.16 → **66.67** | 99.28 → **99.26** |

The authors describe the file-level term-level result as "reduced from 99% to
67%", and the character-level result as "only 1.6% performance degradation."
A learned word vocabulary loses two thirds of its discriminative power the
moment it can no longer see both corpora; a character representation loses
almost nothing. Section 2.2 treats this as the decisive evidence for our own
representational choice.

Critically, the authors did not run this ablation as a curiosity. Their
Section 5.5 explains why: **"the benign dataset may not be considered as a
representative ground-truth benign dataset with an absolute confidence.
Therefore, and to account for that shortcoming, we evaluated our models using
representations extracted exclusively from the malware samples."** The concern
that Section 2.2 raises about their benign class is one the authors raise
themselves, and the malware-only column is their answer to it. The same section
concedes two further limits: the approach "is limited to malware that do not
employ obfuscation", and the commands are obtained by static disassembly rather
than by observing execution.
