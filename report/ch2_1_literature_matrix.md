# 2.1 — Literature Extraction Matrix

The two assigned papers, extracted along one set of dimensions so they can be
compared row by row, with our own design in the third column.

- **Paper A — ShellCore.** Alasmary, H., et al. (2022), *ShellCore: Automating Malicious IoT Software Detection by Using Shell Commands Representation*, IEEE Internet of Things Journal (arXiv:2103.14221). Read first-hand; Tables 1–5, §§3.1–3.3, 4.1–4.5, 5.5.
- **Paper B — QuasarNix / TOPS.** Trizna, D., Demetrio, L., Biggio, B., & Roli, F. (2026), *Robust Large-Scale Detection of Living-Off-the-Land Reverse Shells via Data Synthesis*, ACM Transactions on Privacy and Security, DOI 10.1145/3807450 (arXiv:2402.18329). Its predecessor, the **SLP** paper (Trizna 2021, arXiv:2107.02438), is cited where the representation argument originates.

**Table 2.1 — Comparative extraction matrix: the two assigned papers against this project.**

| Dimension | **A — ShellCore** (Alasmary et al., 2022) | **B — QuasarNix / TOPS** (Trizna et al., 2026) | **This project** |
|---|---|---|---|
| **Problem framed as** | A *representation* problem: shell commands are text, so build a better bag-of-tokens | A *data* problem: LotL reverse shells are rare, so synthesise the space | A *labelling* problem: what does a provenance label actually buy, and what does it cost? |
| **Unit of analysis** | Shell command string (also aggregated to file level) | Shell command string (reverse-shell one-liners) | Shell command string — one command, one row, no session context |
| **Feature extraction** | BoW over term-level *and* character-level tokens, plus 1–5-grams; frequency-encoded | Shell-aware tokenisation (SLP) + classical encodings; the contribution is the corpus, not a new encoder | **Hybrid**: 43 engineered behavioural features (counts, ratios, MITRE binary-family flags) ∪ char 3–5-gram TF-IDF; raw char-index sequences for the 1D-CNN |
| **Dimensionality handling** | **PCA** to 99.9% retained variance | Bounded n-grams / hashing | Explicit 68 → 43 selection under one documented gate applied identically to both corpora; no projection, so every feature stays nameable |
| **Models** | LR, RF, DNN (5 hidden layers), 10-fold CV | Ensemble of classifiers plus adversarially-trained variants | XGBoost, XGBoost-hybrid, RandomForest, 1D-CNN, IsolationForest, TF-IDF+LR baseline, and a 3-stage cascade |
| **Malicious data** | 178,261 commands *statically extracted* from 2,891 IoT-botnet binaries via 1,273 hand-written regexes — never observed executing | **>1M synthetic reverse-shell variants** generated from ~34 threat-intel templates | Real published payloads (QuasarNix, SLP, GTFOBins, Atomic Red Team, HackTricks) and **commands attackers actually typed** into a Cowrie honeypot |
| **Benign data** | ~1.63M rows of which **99.6% are HTTP payloads**, not shell commands; only 5,772 real bash-history lines from 9 volunteers | Benign command corpora, variability deliberately preserved | Curated benign corpora (nl2bash, tldr, bash-instruct, LinLM, bash_command_6k) and real `.bash_history` / commandlinefu |
| **Class balance** | Not stated; Table 2 implies ≈9.83% malicious, Table 5 implies a 9× different row count | Not the headline; the low-FPR operating point is | **Fixed 1 : 3** attack:benign in both datasets, stated up front, with the do-nothing F1 floor of **0.400** reported alongside every score |
| **Validation** | Plain 10-fold CV; **no dedup or grouped split reported** | Held-out plus adversarial evaluation | 80/20 hold-out **grouped by command shape** (0 straddles) + stratified 5-fold CV, with a measured near-duplicate audit disclosing residual leakage |
| **Headline result** | 99.87% accuracy / 99.87 F-1 at command level (char-level LR and DNN) | ~90% higher detection than non-augmented baselines at **FPR = 10⁻⁵** | Best model F1 **0.876 (D1) / 0.848 (D2)**; the *simplest* model (char n-gram baseline) wins at **0.898 / 0.882** |
| **Generalisation tested** | No — in-distribution only. Their one robustness probe is a malware-only ablation, where **term-level collapses 99.86 → 89.52** and char-level holds at 98.24 | **Yes** — black-box evasion attacks and adversarially robust defences | **Yes** — explicit cross-dataset D1↔D2 transfer, leave-one-source-out recall, and a source-separability confound probe (0.821 accuracy vs 0.298 chance) |
| **Interpretability** | Sacrificed: PCA components cannot be ranked against domain intuition, despite the paper claiming an explainable feature space | Not a stated goal | Preserved by construction — every one of the 43 features has a threat-model rationale and a Ch4 importance rank |
| **Limitation that matters to us** | The benign class is a different *kind of text*, and median length differs 384 vs 14 chars — length alone nearly separates their classes. Their 99.87% is not a shell-vs-shell boundary | Synthetic variants inherit their templates; coverage is bounded by the ~34 seeds | Provenance labels are noisier per line than supervised `auditd` labels, and in-domain scores are inflated by corpus style — which is the finding, not a caveat |

**Reading of the matrix.** The two papers disagree about where detection
performance comes from — A says the *encoding*, B says the *corpus* — and each
supports its claim with the ablation the other lacks. Our results let us
adjudicate: the char n-gram baseline beating all five engineered-feature models
on both datasets is independent confirmation of A's representation thesis, while
the cross-dataset collapse (every supervised model losing a third to two-thirds
of its F1) is independent confirmation of B's generalisation thesis. Chapter 8.3
decomposes the gap to ShellCore into almost exactly equal representation and
corpus halves, which is the quantitative form of that adjudication.
