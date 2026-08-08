# Ch2 — ShellCore feature-extraction matrix (Noam's paper)

> Seed for Ch2.1 (literature extraction matrix) and Ch2.2 (adopt/modify/reject defense),
> plus the Ch8.3 benchmark numbers. Paper: Alasmary et al., *ShellCore: Automating
> Malicious IoT Software Detection by Using Shell Commands Representation*, IEEE Internet
> of Things Journal 2022 (arXiv:2103.14221). Read jointly (Noam + Claude Code) 2026-08-08;
> local copy `docs/refs/shellcore_arxiv_2103.14221.pdf` (untracked).

## Extraction matrix — what ShellCore does

| # | Element | Paper § | What it is | Semantic security meaning (per authors) |
|---|---|---|---|---|
| 1 | Term-level model | 3.1.1, 3.3.1 | BoW over space/special-char tokens, words ≥3 chars only, + 1–5-grams | "Locality of the words" — which command words appear together |
| 2 | Character-level model | 3.1.2, 3.3.2 | Every letter/digit/space/symbol is a token; same BoW + n-gram machinery | Operators (`\|\|`, `&&`) and short keywords (`cd`, `ls`) that term-level discards carry "discriminating and dominant characteristics" |
| 3 | BoW frequency encoding | 3.1.4 | Sparse frequency vector over corpus vocabulary | Token occurrence frequency as the signal |
| 4 | n-gram proximity | 3.1.5 | Contiguous n-token sequences added to the bag | Command *structure*/syntax, not just content |
| 5 | PCA reduction | 3.1.6 | Keep 99.9% variance | Purely computational (curse of dimensionality) — no security meaning |
| 6 | Classifiers | 3.2 | LR, RF, DNN (5 hidden layers), 10-fold CV | — |

## Adopt / modify / reject for our extractor (`src/features.py`)

| ShellCore element | Verdict | Reasoning |
|---|---|---|
| Char-level insight (#2) | **Adopt** (as engineered distillation) | The signal lives in operators & symbol structure. Our structural counts (`n_pipes`, redirect counts, subshell/quote counts, `special_ratio`, entropies) encode it interpretably; team-wide, Ben's char 3–5-gram TF-IDF block and the 1D-CNN char encoder implement it directly. |
| Term-level BoW (#1, #3) | **Modify** → fixed threat-mapped binary families | Keep "which programs appear," drop the corpus-learned vocabulary. Their own malware-only ablation (Table 4 right) shows term-level collapsing 99.86→89.52 (command) and →67 (file) when benign data can't shape the vocabulary — measured proof that learned vocab memorizes corpus style (same disease as our KNOWN_ISSUES P8). Fixed lists are label-independent (chosen from the threat model before seeing data), tiny (dozens of dims), and each member carries a documented rationale (Ch1 mapping). Honest limitation: fixed lists can't cover unlisted binaries — the hybrid's char n-gram block is the coverage backstop. |
| n-grams 1–5 (#4) | **Modify** (bounded) | Unbounded n-grams explode dimensionality; Ben's block caps char 3–5-grams, `min_df=3`, `max_features=3000`, fit per fold (leakage-safe). |
| PCA (#5) | **Reject** | Ch4 requires ranking interpretable features against domain intuition; PCA components cannot be ranked against intuition. Their claim that the feature space is "easy to explain" does not survive their own reduction step. |

## Ch8.3 benchmark numbers (command level, Table 4 left)

| Model | Acc | F1 | FNR | FPR |
|---|---:|---:|---:|---:|
| Char-level LR | 99.87 | 99.87 | 0.12 | 0.15 |
| Char-level DNN | 99.87 | 99.87 | 0.12 | 0.14 |
| Term-level LR | 99.86 | 99.86 | 0.03 | 0.20 |

Malware-only-corpus ablation (Table 4 right): term-level DNN 89.52 acc; char-level DNN
98.24 acc ("only 1.6% degradation").

## Why their operating point is not face-value comparable to ours (Ch8.3 discussion)

1. **Benign class is ~99.6% HTTP payloads, not shell commands** (§4.2, Table 2):
   1,625,143 of ~1.63M benign "commands" are unencrypted network payloads (`GET /…
   HTTP/1.1`); only 5,772 are real bash-history commands from 9 volunteers. Separating
   malware shell strings from HTTP requests is a far easier boundary than ours (both our
   classes are genuine shell commands).
2. **Length confound** (Table 3): malware median 384 chars vs bash-history median 14 —
   the same shortcut our KNOWN_ISSUES P3 documents; length alone nearly separates their
   classes.
3. **No dedup / grouped splits reported** (§4.3): 178,261 commands statically extracted
   from 2,891 binaries of a few botnet families must contain massive near-duplication;
   plain 10-fold CV then places near-identical commands in train and test — the P2
   disease our build fixes with `shape()`-grouped splits. Their 99.87% carries that
   inflation; our lower numbers on a grouped split are the more honest measurement.
4. **Malicious commands were never observed executing** (§4.1): strings pattern-matched
   out of disassembled binaries (1,273 hand-derived regexes from 18 samples) — extraction
   bias toward pattern-matchable commands; our D2 attacks are commands attackers actually
   typed (Cowrie sessions).
5. **Prevalence** ≈ 9.8% malicious vs our 25% (1:3) — F1 rulers differ (see
   KNOWN_ISSUES "do-nothing floor").

## Contrast hook for the comparative essay (Ben drafts, Ch2.2)

ShellCore = surface NLP representation, no hand-engineered behavior, interpretability
sacrificed to PCA; TOPS (Trizna) = LotL-specific, synthesis for data scarcity,
robustness evaluation at industrial FPR operating points. Our extractor sits between:
ShellCore's structural insight, encoded as TOPS-style behavior-aware engineered
features, evaluated with grouped splits and prevalence floors.
