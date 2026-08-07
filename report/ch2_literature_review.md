# Chapter 2 — Academic Literature Review & Feature Extraction (Ben)

> Ben owns the **Trizna TOPS/QuasarNix** paper feature matrix and drafts the
> comparative essay; Noam owns the ShellCore paper. This draft covers both so the
> matrix and essay are self-contained; the ShellCore rows are cross-checked with
> Noam before the Aug 14 freeze.
>
> Source verification: numbers read from the papers' full text — TOPS via arXiv
> HTML `2402.18329` (the system is named **QuasarNix** in the paper), ShellCore
> via ar5iv full text of `2103.14221`. Items that could not be confirmed are
> marked "not reported".

## 2.1 Feature Extraction Matrix

| Feature / Representation | Paper | Semantic security meaning (per authors) | Model(s) it fed | Reported metric |
|---|---|---|---|---|
| Whitespace tokenization (split on space/tab/newline) | TOPS/QuasarNix | Baseline segmentation of a command into argv-like tokens | GBDT, RF, MLP (tabular) | Part of best config; GBDT TPR 99.94% @ FPR 1e-5 |
| Wordpunct tokenization (`\w+\|[^\w\s]+`) | TOPS/QuasarNix | Separates punctuation (`;`, `\|`, `/`) so shell operators become distinct tokens | Tabular models | AUC 1.000 (best configs) |
| Byte-Pair Encoding (BPE) vocab, V ∈ {2⁸…2¹⁴} | TOPS/QuasarNix | Data-driven subword units capture frequent malicious fragments (e.g. `/dev/tcp`) without a fixed dictionary | All models | AUC 1.000 |
| One-Hot / TF-IDF / Min-Hash count tabular encoding | TOPS/QuasarNix | Presence/frequency of tokens; sparse binary signal of suspicious token co-occurrence | GBDT, RF, MLP | GBDT F1 99.98%, Acc 99.98% |
| Token embeddings (+ positional encoding), sequence truncated at N=256 | TOPS/QuasarNix | Preserves token order/position — reverse-shell syntax is order-sensitive | 1D-CNN+MLP, BiLSTM(±attn), Transformer | 1D-CNN+MLP TPR 99.59% @1e-5; 99.30% @1e-6 |
| Template-synthesized attack variants (33 reverse-shell templates, placeholder sampling) | TOPS/QuasarNix | Encodes attack *invariants* (shell, proto, IP, port, fd, file, var) while randomizing surface form to fight scarcity/overfitting | Feeds all models as training data | +90% detection vs non-augmented (7.12% → 99.94%) |
| Term-level bag-of-words (words length > 2) | ShellCore | Whole-word tokens = human-recognizable command/utility names | LR, RF, DNN | Term LR: 99.86% Acc, F1 99.86, FPR 0.20 |
| Term-level word n-grams (1–5-grams) | ShellCore | Sequential word patterns = multi-step command idioms | LR, RF, DNN | Included in above |
| Character-level features (space/symbol/letter/digit as features) | ShellCore | Captures short/critical tokens term-level misses: `cd`, `ls`, `\|\|`, `&&`, obfuscation chars | LR, RF, DNN | Char DNN/LR: 99.87% Acc, FPR 0.14–0.15 |
| Character n-grams (1–5-grams) | ShellCore | Sub-token morphology; robust to word-splitting evasion; strongest on malware-only corpus (~98% vs ~89% term) | LR, RF, DNN | Char RF file-level: 99.91% Acc, FPR 0.07 |
| PCA (retain 99.9% variance) | ShellCore | Dimensionality reduction over huge sparse n-gram space | All | Enables tractable training |

## 2.2 Comparative Analytical Essay

**(a) Semantic meaning each paper assigns its features.** TOPS/QuasarNix treats a
command line as a *token sequence whose security signal lives in structure and
invariants*. Its tokenizers (whitespace, wordpunct, BPE) exist to isolate the
syntactic machinery of a reverse shell — the redirection operators, the
`/dev/tcp` path, the interpreter invocation — from noise, and its embeddings
preserve positional order because reverse-shell grammar is order-dependent.
Crucially, the authors push semantics into the *training data itself*: 33
templates parameterized by placeholders (SHELL, PROTO, IP, PORT, FD, FILE, VAR)
encode what makes an attack an attack while randomizing everything incidental.
ShellCore instead assigns meaning at two granularities: term-level features mean
"recognizable utility/command names and their co-occurrence" (human-readable
behaviour), while character-level features mean "sub-word morphology" —
deliberately introduced because term-level tokenization discards the short but
decisive tokens (`cd`, `ls`, `||`, `&&`) and is brittle to obfuscation.

**(b) Synthesis/token approach vs term+char representation.** The two papers
diverge philosophically. TOPS confronts *data scarcity and adversarial
robustness* head-on: rather than mine more real attacks, it *generates* a
balanced, high-variability malicious distribution (aligning synthetic parameter
distributions to legitimate activity with probability α), then stress-tests with
11 shell-escape perturbations, benign-content injection, and adversarial
training. Its representation is deliberately model-flexible (tabular
one-hot/TF-IDF for trees; embeddings for sequence nets). ShellCore invests in
*representation coverage over one fixed real corpus*: it runs the same LR/RF/DNN
over both term- and character-level bag-of-words+n-grams and lets the character
view rescue cases the term view misses (89% → 98% accuracy on the malware-only
corpus). ShellCore has no data synthesis and no adversarial evaluation; TOPS
makes those its centrepiece.

**(c) What we adopt, modify, or reject.** **Adopt:** the character-level intuition
directly justifies our `token/char Shannon entropy`, base64/hex-encoding
indicators, and operator counts (`n_pipes`, `n_redirects`, `n_semicolons`,
`n_backticks_subshell`) — exactly the short, symbol-dense signals ShellCore's
char model proved decisive, expressed as cheap scalars instead of sparse n-grams.
TOPS's placeholder invariants map almost one-to-one onto our behavioural binary
families (fetch tools curl/wget/nc, shell/interpreter binaries, `has_dev_tcp`,
`has_ipv4`/`has_url`), so we adopt the *semantic template* even while rejecting
the synthesis machinery. **Modify:** rather than TOPS's 2¹⁴-dim BPE vocab or
ShellCore's PCA-compressed n-gram space, we distil the same information into a
compact interpretable vector (length, entropy, family counts, sensitive-path
counts) — better suited to our small curated data and to explaining alerts.
**Reject:** full data-synthesis (out of scope, risks widening the curated-vs-real
bias) and character-embedding sequence models for our *tabular* XGBoost/RF/
Isolation-Forest track — though our separate 1D-CNN keeps the sequence view. Our
GTFOBins/LotL, enumeration, privesc and evasion-token families are a
knowledge-driven upgrade over both papers' purely lexical features, defensible
because they inject MITRE-grounded priors that neither corpus-only (ShellCore)
nor template-only (TOPS) features encode explicitly.
