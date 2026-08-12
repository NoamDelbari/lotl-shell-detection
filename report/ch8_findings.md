# Chapter 8 — Error Analysis & Transfer Findings

## 8.1 Error forensics (XGBoost-hybrid vs CNN)

Forensics below are on the full Dataset-1 hold-out (`n = 3049`; 762 attack / 2287 benign, a 1:3 ratio) at the deployed threshold of 0.5, with each model trained on the full Dataset-1 train split. Dataset 1 is the useful lens because it carries eleven distinct provenance tags; Dataset 2 collapses all attacks into a single `honeypot` source and so reveals little about *which kind* of command is missed.

The two models spend their error budget differently, but less differently than their architectures suggest. The hybrid makes **189** mistakes (94 FN + 95 FP), the CNN **218** (91 FN + 127 FP): **XGBoost-hybrid F1 0.876**, precision 0.876, recall 0.877, FPR 0.042; **CNN F1 0.860**, precision 0.841, recall 0.881, FPR 0.056. The CNN is nominally the more *sensitive* model, but only just — it recovers **three** attacks the hybrid misses (91 versus 94, +0.4 points of recall) and pays **32 extra false alarms** for them (+1.4 points of FPR). That is a poor exchange at a 1:3 prior, and it is why the hybrid, not the CNN, is stage 2 of the deployed cascade (§7.1): at essentially identical recall it raises a quarter fewer false alarms.

The more important result is that the *identity* of the errors is largely model-independent — and that claim is measured, not asserted. Comparing the two full error sets row by row (`results/ch8_1_error_overlap.json`), **59 of the hybrid's 94 misses (63%) are also missed by the CNN**, as are 59 of the CNN's 91 (65%); on the false-positive side 61 commands are flagged by both (64% of the hybrid's, 48% of the CNN's). A gradient-boosted ensemble over 43 hand-engineered features and a character-level convolutional network — which share no representation, no inductive bias and no training procedure — converge on the same majority of hard cases. Both classes of failure are artifacts of how the labels were assigned.

**Table 8.1 — False negatives by attack source, Dataset 1 test split.** "Both" counts commands missed by both models.

| Attack source | *n* | XGBoost-hybrid FN | CNN FN | Both |
|---|---:|---:|---:|---:|
| `hacktricks` | 344 | 59 (17.2%) | 51 (14.8%) | 35 |
| `gtfobins` | 189 | 19 (10.1%) | 22 (11.6%) | 14 |
| `atomic_red_team` | 133 | 15 (11.3%) | 16 (12.0%) | 9 |
| `slp` | 23 | 1 (4.3%) | 2 (8.7%) | 1 |
| `quasarnix` | 58 | **0** | **0** | 0 |
| `payloads` | 15 | **0** | **0** | 0 |
| **Total** | **762** | **94 (12.3%)** | **91 (11.9%)** | **59** |

The misses concentrate in `hacktricks`, `gtfobins` and `atomic_red_team` — the escape-technique corpora — while the two overtly offensive sources (`quasarnix` reverse shells, `payloads`) are caught **perfectly, by both models, with zero misses**. That split is the whole story: the models recognise a reverse shell or an obvious dropper, but they cannot flag a line that is *syntactically indistinguishable from routine administration*. The lowest-scoring misses (p = the model's attack probability; both columns shown where both models failed) are all of this kind:

```
# attack-labelled, scored benign                              hybrid    CNN
aptitude changelog aptitude          gtfobins                 p=0.010  p=0.015   # changelog opens a pager -> shell escape
findmnt -t nfs                       atomic_red_team          p=0.021  p=0.019   # mount enumeration
apt-get changelog apt                gtfobins                 p=0.021  p=0.025   # the same package-changelog pager trick
docker scan hello-world              hacktricks               p=0.034  p=0.121   # container-tooling recon
useradd -u 1000 standarduser         hacktricks               p=0.077  p=0.456   # UID-collision persistence prep
bconsole                             gtfobins                 p=0.182  p=0.144   # bare binary; Bacula console -> shell escape
```

Each is innocuous *in isolation* — a changelog pager, a mount listing, a bare binary name — and is "attack" only because of where it was harvested. `bconsole` is the limiting case: a single word, nine characters, no arguments, no operators. There is no content signal for any model to learn.

**Table 8.2 — False positives by benign source, Dataset 1 test split.**

| Benign source | *n* | XGBoost-hybrid FP | CNN FP | Both |
|---|---:|---:|---:|---:|
| `linlm` | 145 | 21 (14.5%) | 32 (22.1%) | 18 |
| `bash6k` | 116 | 14 (12.1%) | 15 (12.9%) | 9 |
| `nl2bash` | 306 | 28 (9.2%) | 37 (12.1%) | 19 |
| `tldr` | 935 | 29 (3.1%) | 39 (4.2%) | 15 |
| `bash_instruct` | 785 | 3 (0.4%) | 4 (0.5%) | 0 |
| **Total** | **2287** | **95 (4.2%)** | **127 (5.6%)** | **61** |

The false alarms are the mirror image of the misses: **dual-use administration**, plus `nl2bash` pipelines that carry attack-shaped surface features but were logged as benign. The rate tracks how *operational* the corpus is — the free-form Linux-command corpus `linlm` is tripped on one line in seven by the hybrid and better than one in five by the CNN, while the clean instructional corpus `bash_instruct` is essentially never tripped (0.4% / 0.5%, and not one line by both models). The highest-scoring false alarms are textbook dual-use:

```
# benign-labelled, scored attack                              hybrid    CNN
mkdir -p /tmp/project/{src,bin,doc}          bash6k           p=0.973  p=0.985   # brace expansion in /tmp
cat /proc/interrupts                         linlm            p=0.910  p=0.946   # /proc read
head -n 10 /etc/passwd                       bash6k           p=0.878  p=0.952   # read /etc/passwd
sudo ln -s /usr/bin/perl /usr/local/bin/perl`echo -e '\r'`
                                             nl2bash          p=0.912  p=0.981   # sudo + symlink + backtick subshell
yes '' | ruby -e "$(curl -fsSL https://…/Homebrew/install)"
                                             nl2bash          p=0.765  p=0.873   # curl | interpreter
```

The last line is the argument in miniature. Piping a remotely fetched script straight into an interpreter is the canonical LotL delivery primitive, and both models score it as an attack — correctly, on every behavioural criterion. It is labelled benign because the URL happens to be the Homebrew installer. No feature set and no architecture can separate that from a dropper using the command string alone.

**This is label contamination, not model failure.** The dataset is provenance-labelled: the label describes the *source corpus*, not the *command line*. The corpus measures its own contradiction. Across all 15,248 Dataset-1 commands, **47 touch `/etc/passwd` — 9 of them labelled benign** (all `bash6k`) **and 38 labelled attack** (`hacktricks` 21, `atomic_red_team` 14, `slp` 2, `gtfobins` 1). The same read of the same file is ground-truth benign or ground-truth malicious depending only on which corpus supplied it. `chmod +s` runs the same way: all 7 occurrences are attack-labelled because HackTricks and a payload corpus documented them, yet setting a set-uid bit is a legitimate administrative action with no benign counterexample in the corpus to teach the boundary.

Both models have therefore learned the ceiling the labelling scheme allows — they reproduce the corpus boundary faithfully — and the residual errors, 63–65% of which they share, are exactly the region where that boundary contradicts the semantics of the line. This is the empirical basis for the cascade's third stage (§8.4): if the remaining errors are cases where the command string is genuinely ambiguous, the only way past them is to supply information the string does not contain.

Confusion matrices for all five models on both corpora are in `ch8_confusion_<model>_dataset{1,2}.png`.

## 8.2 Cross-dataset transfer

Trained on one corpus and tested on the other, every model's F1 falls off a cliff. The table gives in-domain F1 (train and test on the same corpus) against the two cross-domain directions; the five registry models are from the same full-data run (`main.py all`), so the in-domain columns match the §8.1 hold-out F1. Figure `ch8_transfer_heatmap.png` renders the same grid (`analysis/ch8_2_transfer_heatmap.py` reads the identical JSON, so figure and table cannot diverge); 8 of its 20 cells fall below the 0.400 do-nothing floor.

| Model | In-domain D1→D1 | In-domain D2→D2 | Cross D1→D2 | Cross D2→D1 |
|---|---:|---:|---:|---:|
| `xgboost_hybrid` | 0.876 | 0.848 | 0.532 | 0.276 |
| `cnn1d` | 0.860 | 0.838 | **0.541** | **0.359** |
| `random_forest` | 0.796 | 0.753 | 0.515 | 0.143 |
| `xgboost` | 0.786 | 0.756 | 0.495 | 0.235 |
| `isolation_forest` | 0.249 | 0.143 | 0.148 | 0.241 |
| *`baseline` (TF-IDF+LR)* | *0.898* | *0.882* | *0.584* | *0.274* |

⚠️ **Basis note.** The five registry rows are scored on the **target corpus's test split** (n = 1,915 for D2, 3,049 for D1). The baseline row is italicised because `docs/baseline_metrics.json` scores transfer on **all rows of the target** (n = 9,576 / 15,248) — a different population, so its two cross cells are indicative rather than directly commensurable.

Every supervised model at least halves its F1 under transfer. **The single largest degradation is `random_forest` going D2→D1: in-domain 0.753 collapses to 0.143 — a fall of 0.61 F1**, with the hybrid close behind (0.848 → 0.276). Note the **asymmetry**: for every *supervised* model D2→D1 (operational → curated) is worse than D1→D2 (curated → operational), because a model raised on the messy operational register has never seen the tight, canonical GTFOBins/HackTricks surface it is now asked to score, whereas a model raised on the clean curated register at least recognizes some structure in the operational data. The Isolation Forest is the lone inversion (0.241 vs 0.148), and only because both figures sit far below the 0.400 do-nothing floor — it is not detecting in either direction. The strongest in-domain models degrade the *most* in absolute terms — a warning that in-domain leaderboard position is anti-correlated with robustness here. The exception proves the rule: `cnn1d`, which trails the hybrid in-domain, is the best transferrer in **both** directions (0.541 and 0.359), the representation effect Chapter 2 predicted.

Why does this happen? The **source-separability probe** answers it directly. A plain char-n-gram classifier asked only to name which of the eleven corpora a line came from hits **0.821 accuracy against a 0.298 majority-class baseline** — 2.8× chance. Each corpus carries a strong stylistic fingerprint, and because the maliciousness label *is* the corpus tag (§8.1), the label is confounded with register. In-domain, a model can score well by learning "which corpus wrote this" — a curated escape corpus and an operational shell history simply *read* differently (canonical flag ordering, quoting and path conventions, `example.net`/`{{placeholder}}`/`T####` tells on the D1 side; hard-coded IPs, random dropper names like `./qJWIJu99`, and captured `[user@host]$` prompt noise on the D2 side) — instead of "is this malicious." Those surface tells are corpus-specific, so under distribution shift they evaporate and the classifier is left guessing; the collapse manifests as a spike in false positives on the unseen benign register (D2's messy real-user commands look "attack-shaped" to a D1-trained model, and vice versa).

This is the defining property of the T1059.004 problem: **LotL detection is context, not content.** The same `head /etc/passwd`, `find … -exec`, or `chmod +s` is benign or malicious depending on who ran it, why, and when — none of which is in the command string. A supervised model handed provenance labels can only learn the *style* of each corpus, and style does not transfer. The in-domain scores therefore overstate real-world capability, and the D1↔D2 gap is the honest measure of how much of that performance was corpus-fitting rather than attack detection.
