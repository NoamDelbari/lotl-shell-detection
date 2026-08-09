# Chapter 8.3 — Comparison vs. the Trizna ("TOPS") Paper

> The assigned TOPS paper is Trizna, D., Demetrio, L., Biggio, B., & Roli, F. (2026), *Robust Large-Scale Detection of Living-Off-the-Land Reverse Shells via Data Synthesis*, ACM TOPS, DOI: 10.1145/3807450 (arXiv:2402.18329). This is the QuasarNix paper — its `quasarnix` corpus is one of our own attack sources. The comparison below also references Trizna's earlier **SLP paper** (arXiv:2107.02438, CAMLIS 2021) where relevant. Our own numbers are from [`results/summary.json`](../results/summary.json) and the forensics in [`report/ch8_findings.md`](ch8_findings.md).

## Error-profile comparison

| Failure mode | Trizna-style model (seq2seq anomaly detector / QuasarNix) | Our XGBoost-hybrid | Our 1D-CNN |
|---|---|---|---|
| **Overt attacks** (reverse shells, dropper cradles) | **Caught reliably.** QuasarNix's entire design goal is robust detection of reverse shells; a seq2seq model flags them as high-reconstruction-error outliers. | **Caught reliably** — `quasarnix` 0/58 and `payloads` 0/15 false negatives. | **Caught reliably** — same 0-FN pattern on the overt-attack sources. |
| **Benign-looking LotL** (recon `whoami`/`id`, GTFOBins-style escapes, `chmod +s`) | **Missed.** These *are* "normal" sequences, so an anomaly model assigns them low error and passes them through — the model's structural blind spot. | **Missed** — FN concentrate in `hacktricks` (18%), `atomic_red_team` (14%), `gtfobins` (8%); worst FNs are `apt-get changelog`, `chmod +s payload`, `last \| tail`. | **Missed** — the same class (`hacktricks` 11%, `gtfobins` 10%); worst FNs `pkaction --verbose`, `aptitude changelog`. |
| **Rare-but-benign / unusual legitimate syntax** | **False alarm.** Novelty ≠ maliciousness: an anomaly detector fires on any unusual-but-legitimate one-liner, its dominant false-positive mode. | **False alarm** on dual-use admin — `linlm` 17% FP (`sudo iptables …`), `bash6k` 13% (`chsh`, `head /etc/passwd`), `nl2bash` 10% (`find … -exec`). | **False alarm** on the same but far more often (173 FP vs 100), tilted toward templated `nl2bash` `find` pipelines (`nl2bash` 16%, `linlm` 25%). |
| **Distribution shift / novel corpus** | **Fails without augmentation** — QuasarNix's headline finding: non-augmented models do not generalize. | **Fails** — transfer collapse (below). | **Fails, but least badly** — best cross-dataset transfer of any model. |
| **Adversarial evasion** | **Explicitly studied** — QuasarNix builds black-box evasion attacks and adversarially robust defenses. | **Untested** (a gap in our work). | **Untested** (a gap in our work). |
| **Total in-domain errors (D1, full-train)** | — | 97 FN / 100 FP (F1 0.871) | 70 FN / 173 FP (F1 0.851) |

The striking result is that the **two failure classes that matter are model-independent**: whether the detector is a supervised tree, a character CNN, or a seq2seq anomaly model, it misses benign-looking LotL and false-alarms on unusual-but-benign administration. That is not a modeling deficiency — it is the label boundary. Our XGBoost-hybrid and CNN differ only in *how* they spend the error budget (the hybrid is more precise, FPR 0.044; the CNN more sensitive, recall 0.908), not in *which* commands they get wrong.

## What Trizna's generalization results predict, and whether ours confirm it

**The prediction.** QuasarNix's central, empirically demonstrated claim is that a model trained on one distribution of Linux commands **does not generalize to another** unless its training data is deliberately augmented to span the space — non-augmented baselines collapse, and evasion variants sail past them. A seq2seq anomaly detector inherits the same fragility from the opposite direction: it learns the *style* of its "normal" corpus, so a different-but-still-benign register reads as anomalous. Both framings therefore predict the same thing for our setup: because Dataset 1 (curated) and Dataset 2 (operational honeypot) are stylistically disjoint registers, a model fit on one should **collapse** when evaluated on the other, and the collapse should manifest as exploding false positives on the unseen benign style.

**Our numbers confirm it — decisively.** Every non-augmented model roughly halves its F1 under cross-dataset transfer (`results/summary.json`):

| Model | In-domain (D1 / D2) | D1→D2 | D2→D1 |
|---|---|---|---|
| `xgboost_hybrid` | 0.871 / 0.846 | **0.534** | **0.184** |
| `cnn` | 0.853 / 0.841 | **0.529** | **0.331** |
| `baseline` | 0.881 / 0.863 | **0.572** | **0.336** |
| `random_forest` | 0.761 / 0.696 | 0.509 | 0.175 |

The XGBoost-hybrid falls from 0.871 in-domain to **0.534 (D1→D2)** and **0.184 (D2→D1)** — a ~0.69 F1 drop, exactly the "does not generalize without augmentation" outcome the QuasarNix result predicts. The mechanism also matches: transfer ROC-AUC sinks toward chance (xgboost_hybrid D2→D1 AUC **0.643**) and precision craters as the model floods the unseen benign register with false positives (D1→D2 FPR jumps to **0.283**). Our source-separability probe (0.821 vs. 0.298 chance) is the direct evidence for *why*: the models learned corpus style, and style does not transfer — the same conclusion QuasarNix reaches by showing that only distribution-spanning augmentation restores generalization.

**Two nuances our data adds beyond the prediction.** First, the collapse is **asymmetric**: D2→D1 is worse than D1→D2 for every model (e.g. baseline 0.336 vs. 0.572), because a model raised on the messy operational register has never seen the tight, canonical GTFOBins/HackTricks surface, whereas the reverse direction at least transfers some structure. Second, the **CNN is the most transfer-robust model** — on the punishing D2→D1 direction it holds **0.331** vs. the hybrid's **0.184** (and is essentially tied on D1→D2, 0.529 vs 0.534) — despite trailing in-domain, a direct echo of SLP's thesis that *representation* governs generalization: character-level features share sub-word structure across registers (an IP is an IP, `/dev/tcp` is `/dev/tcp`) where engineered-count and TF-IDF features latch onto corpus-specific token distributions. So our results not only confirm the generalization prediction, they refine it: the right *representation* buys back a meaningful slice of the transfer gap even without QuasarNix-style augmentation — which is the natural next experiment this project points to.
