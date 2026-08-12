# Chapter 8.3 — Comparison vs. the Trizna ("TOPS") Paper

> **Assembly note (§8.3).** The rubric asks that this section benchmark against
> the literature *"reviewed in Chapter 6"*. Both papers it compares against are
> cited in Chapter 6 (ShellCore arXiv:2103.14221 in §6.4–6.5; QuasarNix/TOPS
> arXiv:2402.18329 in Ben's §6.2), so the substance is aligned — only the
> cross-reference wording needs to say "Chapter 6" rather than "Chapter 2"
> in the .docx.

> The assigned TOPS paper is Trizna, D., Demetrio, L., Biggio, B., & Roli, F. (2026), *Robust Large-Scale Detection of Living-Off-the-Land Reverse Shells via Data Synthesis*, ACM TOPS, DOI: 10.1145/3807450 (arXiv:2402.18329). This is the QuasarNix paper — its `quasarnix` corpus is one of our own attack sources. The comparison below also references Trizna's earlier **SLP paper** (arXiv:2107.02438, CAMLIS 2021) where relevant. Our own numbers are from [`results/summary.json`](../results/summary.json) and the forensics in [`report/ch8_findings.md`](ch8_findings.md).

## Error-profile comparison

| Failure mode | Trizna-style model (seq2seq anomaly detector / QuasarNix) | Our XGBoost-hybrid | Our 1D-CNN |
|---|---|---|---|
| **Overt attacks** (reverse shells, dropper cradles) | **Caught reliably.** QuasarNix's entire design goal is robust detection of reverse shells; a seq2seq model flags them as high-reconstruction-error outliers. | **Caught reliably** — `quasarnix` 0/58 and `payloads` 0/15 false negatives. | **Caught reliably** — same 0-FN pattern on the overt-attack sources. |
| **Benign-looking LotL** (recon `whoami`/`id`, GTFOBins-style escapes, `chmod +s`) | **Missed.** These *are* "normal" sequences, so an anomaly model assigns them low error and passes them through — the model's structural blind spot. | **Missed** — FN concentrate in `hacktricks` (17.2%), `atomic_red_team` (11.3%), `gtfobins` (10.1%); worst FNs are `apt-get changelog`, `chmod +s payload`, `last \| tail`. | **Missed** — the same class (`hacktricks` 14.8%, `gtfobins` 11.6%); worst FNs `pkaction --verbose`, `aptitude changelog`. |
| **Rare-but-benign / unusual legitimate syntax** | **False alarm.** Novelty ≠ maliciousness: an anomaly detector fires on any unusual-but-legitimate one-liner, its dominant false-positive mode. | **False alarm** on dual-use admin — `linlm` 14.5% FP (`sudo iptables …`), `bash6k` 12.1% (`chsh`, `head /etc/passwd`), `nl2bash` 9.2% (`find … -exec`). | **False alarm** on the same but more often (127 FP vs 95), tilted toward templated `nl2bash` `find` pipelines (`nl2bash` 12.1%, `linlm` 22.1%). |
| **Distribution shift / novel corpus** | **Fails without augmentation** — QuasarNix's headline finding: non-augmented models do not generalize. | **Fails** — transfer collapse (below). | **Fails, but least badly** — best cross-dataset transfer of any model. |
| **Adversarial evasion** | **Explicitly studied** — QuasarNix builds black-box evasion attacks and adversarially robust defenses. | **Untested** (a gap in our work). | **Untested** (a gap in our work). |
| **Total in-domain errors (D1, full-train)** | — | 94 FN / 95 FP (F1 0.876) | 91 FN / 127 FP (F1 0.860) |

The striking result is that the **two failure classes that matter are model-independent**: whether the detector is a supervised tree, a character CNN, or a seq2seq anomaly model, it misses benign-looking LotL and false-alarms on unusual-but-benign administration. That is not a modeling deficiency — it is the label boundary. Our XGBoost-hybrid and CNN differ only in *how* they spend the error budget (the hybrid is more precise, FPR 0.042 against the CNN's 0.056; the CNN more sensitive, recall 0.881 against 0.877), not in *which* commands they get wrong.

## What Trizna's generalization results predict, and whether ours confirm it

**The prediction.** QuasarNix's central, empirically demonstrated claim is that a model trained on one distribution of Linux commands **does not generalize to another** unless its training data is deliberately augmented to span the space — non-augmented baselines collapse, and evasion variants sail past them. A seq2seq anomaly detector inherits the same fragility from the opposite direction: it learns the *style* of its "normal" corpus, so a different-but-still-benign register reads as anomalous. Both framings therefore predict the same thing for our setup: because Dataset 1 (curated) and Dataset 2 (operational honeypot) are stylistically disjoint registers, a model fit on one should **collapse** when evaluated on the other, and the collapse should manifest as exploding false positives on the unseen benign style.

**Our numbers confirm it — decisively.** Every non-augmented supervised model loses between a third and two-thirds of its F1 under cross-dataset transfer (`results/transfer_*.json`):

| Model | In-domain (D1 / D2) | D1→D2 | D2→D1 |
|---|---|---|---|
| `xgboost_hybrid` | 0.876 / 0.848 | **0.532** | **0.276** |
| `cnn1d` | 0.860 / 0.838 | **0.541** | **0.359** |
| `random_forest` | 0.796 / 0.753 | 0.515 | 0.143 |
| `xgboost` | 0.786 / 0.756 | 0.495 | 0.235 |
| `isolation_forest` | 0.249 / 0.143 | 0.148 | 0.241 |
| *`baseline` (TF-IDF+LR)* | *0.898 / 0.882* | *0.584* | *0.274* |

⚠️ **Basis note.** The five model rows are evaluated on the **target dataset's test
split** (n = 1,915 for D2, 3,049 for D1). The baseline row is italicised because
`docs/baseline_metrics.json` evaluates transfer on **all rows of the target**
(n = 9,576 / 15,248) — a different population, so its two transfer cells are
indicative, not directly commensurable with the rows above. The
`results/transfer_baseline_*.json` files that would have matched the models'
basis are orphans with no producing code and are deleted at packaging.

The XGBoost-hybrid falls from 0.876 in-domain to **0.532 (D1→D2)** and **0.276 (D2→D1)** — a 0.60 F1 drop on the punishing direction, exactly the "does not generalize without augmentation" outcome the QuasarNix result predicts. The mechanism also matches: transfer ROC-AUC sinks toward chance (xgboost_hybrid D2→D1 AUC **0.686**) and precision craters as the model floods the unseen benign register with false positives (D1→D2 FPR jumps to **0.276**, from 0.042 in-domain). Our source-separability probe (0.821 vs. 0.298 chance) is the direct evidence for *why*: the models learned corpus style, and style does not transfer — the same conclusion QuasarNix reaches by showing that only distribution-spanning augmentation restores generalization.

**Two nuances our data adds beyond the prediction.** First, the collapse is **asymmetric**: D2→D1 is worse than D1→D2 for every *supervised* model (baseline 0.274 vs. 0.584; the Isolation Forest is the lone inversion, 0.241 vs. 0.148, and only because both figures sit far below the 0.400 floor), because a model raised on the messy operational register has never seen the tight, canonical GTFOBins/HackTricks surface, whereas the reverse direction at least transfers some structure. Second, the **CNN is the most transfer-robust model** — on the punishing D2→D1 direction it holds **0.359** vs. the hybrid's **0.276**, and it also edges the hybrid on D1→D2 (0.541 vs 0.532) — despite trailing in-domain, a direct echo of SLP's thesis that *representation* governs generalization: character-level features share sub-word structure across registers (an IP is an IP, `/dev/tcp` is `/dev/tcp`) where engineered-count and TF-IDF features latch onto corpus-specific token distributions. So our results not only confirm the generalization prediction, they refine it: the right *representation* buys back a meaningful slice of the transfer gap even without QuasarNix-style augmentation — which is the natural next experiment this project points to.
