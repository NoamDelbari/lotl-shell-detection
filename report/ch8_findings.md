# Chapter 8 — Error Analysis & Transfer Findings

## 8.1 Error forensics (XGBoost-hybrid vs CNN)

Forensics below are on the full Dataset-1 hold-out (`n = 3049`; 762 attack / 2287 benign, a 1:3 ratio) at the deployed threshold of 0.5, with each model trained on the full Dataset-1 train split. Dataset 1 is the useful lens because it carries eleven distinct provenance tags; Dataset 2 collapses all attacks into a single `honeypot` source and so reveals little about *which kind* of command is missed.

The two models spend their error budget very differently — the hybrid makes **197** mistakes (97 FN + 100 FP), the CNN **243** (70 FN + 173 FP). Their F1 is close (**XGBoost-hybrid F1 0.871**, precision 0.869, recall 0.873, FPR 0.044; **CNN F1 0.851**, precision 0.800, recall 0.908, FPR 0.076), but the trade-off is now sharp: the CNN is the far more *sensitive* model — only 70 misses (recall 0.908) — and pays for it in false alarms (173 FP, FPR 0.076); the hybrid is the more *precise* model (FPR 0.044, 100 FP) at the cost of a few more misses. So the **XGBoost-hybrid trades recall for a much tighter false-positive rate**, while the CNN maximizes recall — the hybrid is the better operating point when false alarms are the binding constraint.

The more important result is that the *identity* of the errors is nearly model-independent. Both models fail on the same two structural classes, and both classes are artifacts of how the labels were assigned.

**False negatives — the attack lines each model waves through** (see `ch8_errors_by_source_xgboost_hybrid.png`, `ch8_errors_by_source_cnn.png`):

| Attack source | XGBoost-hybrid FN | CNN FN |
|---|---|---|
| `hacktricks` | 61 / 344 (18%) | 39 / 344 (11%) |
| `atomic_red_team` | 19 / 133 (14%) | 11 / 133 (8%) |
| `gtfobins` | 16 / 189 (8%) | 19 / 189 (10%) |
| `slp` | 1 / 23 (4%) | 1 / 23 (4%) |
| `quasarnix` | 0 / 58 (0%) | 0 / 58 (0%) |
| `payloads` | 0 / 15 (0%) | 0 / 15 (0%) |
| **Total** | **97 / 762** | **70 / 762** |

The misses concentrate in `hacktricks`, `gtfobins`, and `atomic_red_team` — the GTFOBins / HackTricks / Atomic-Red-Team escape corpora — while the two overtly offensive sources (`quasarnix` reverse shells, `payloads`) are caught **perfectly (0 FN)**. That split is the whole story: the models recognize a reverse shell or an obvious payload, but they cannot flag a line that is *syntactically indistinguishable from routine administration*. The most-confidently-benign misses (p = the model's attack probability) are all of this kind:

```
# attack-labeled, but scored benign
find . -name "*.php" -print0 | xargs -0 grep -in "var $password"   slp         p=0.022   # credential grep
apt-get changelog apt                                             gtfobins    p=0.034   # changelog opens a pager -> shell escape
aptitude changelog aptitude                                       gtfobins    p=0.045   # same package-changelog pager trick
chmod +s payload                                                  hacktricks  p=0.065   # set-uid escalation prep
pkaction --verbose                                                hacktricks  p=0.025   # (CNN) polkit action enumeration
last | tail                                                       hacktricks  p=0.013   # (CNN) login-history recon
```

Each of these is innocuous *in isolation* — a changelog pager, a `chmod +s`, a `/proc`/login read — and is "attack" only because of where it was harvested. There is no content signal for the model to learn.

**False positives — the benign lines each model blocks:**

| Benign source | XGBoost-hybrid FP | CNN FP |
|---|---|---|
| `linlm` | 25 / 145 (17%) | 36 / 145 (25%) |
| `bash6k` | 15 / 116 (13%) | 21 / 116 (18%) |
| `nl2bash` | 31 / 306 (10%) | 50 / 306 (16%) |
| `tldr` | 27 / 935 (3%) | 59 / 935 (6%) |
| `bash_instruct` | 2 / 785 (0%) | 7 / 785 (1%) |
| **Total** | **100 / 2287** | **173 / 2287** |

The false alarms are the mirror image of the misses: **dual-use administration** and `nl2bash` `find`/`-exec` pipelines that carry attack-shaped surface features but were logged as benign. The high-recall CNN false-positives on **one in four `linlm` lines** (25%) — the worst benign rate by a wide margin — versus the hybrid's more restrained one in six (17%); both trip on roughly one in six `bash6k` lines, while the clean instructional corpus `bash_instruct` is essentially never tripped (0% / 1%). The most-confidently-attack false alarms are textbook dual-use:

```
# benign-labeled, but scored attack
ssh user@server /bin/bash <<'EOT'                nl2bash  p=0.96-1.00  # heredoc-piped remote shell
chsh -s /bin/bash john                           bash6k   p=0.96-0.99  # change a login shell
head -n 10 /etc/passwd                            bash6k   p=0.96       # read /etc/passwd
sudo iptables -A INPUT -s 38.201.6.82 -j DROP     linlm    p=0.98       # firewall edit
find ./ -type f | tee /tmp/grep1 /tmp/grep2       nl2bash  p=0.97       # find/tee pipeline
mkdir -p /tmp/project/{src,bin,doc}               bash6k   p=0.94       # brace-expansion mkdir
```

**This is label contamination, not model failure.** The dataset is provenance-labeled: the label describes the *source corpus*, not the *command line*. `head /etc/passwd` is benign here because it came from `bash6k`, yet the identical reconnaissance is attack-labeled when HackTricks ships it; `chmod +s payload` is attack-labeled because HackTricks documented it, yet it is byte-for-byte a legitimate admin action. A command's ground-truth label can flip purely by which corpus drew it. Both models have therefore learned the ceiling the labeling scheme allows — they reproduce the corpus boundary faithfully — and the residual errors are exactly the region where that boundary contradicts the semantics of the line.

## 8.2 Cross-dataset transfer

Trained on one corpus and tested on the other, every model's F1 falls off a cliff. The table gives in-domain F1 (train and test on the same corpus) against the two cross-domain directions; the five registry models are from the same full-data run (`main.py all`), so the in-domain columns match the §8.1 hold-out F1. See `ch8_transfer_heatmap.png`.

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
