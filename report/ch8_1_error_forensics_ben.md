# Chapter 8.1 — Forensic error analysis (Ben's models)

Confusion matrices: `report/figures/ch8_confusion_*.png`. Sample-level FN/FP: `results/ch8_failures.json`.

## xgboost_hybrid/dataset1

- Confusion [tn, fp, fn, tp] = [2179, 108, 88, 674]; F1 0.873, Recall 0.885, FPR 0.047.
- **False negatives** dominated by source(s): {'hacktricks': 22, 'gtfobins': 11, 'atomic_red_team': 7}.
- **False positives** dominated by source(s): {'tldr': 13, 'nl2bash': 9, 'bash6k': 9, 'linlm': 8}.
- Example missed attacks (FN): `bconsole` ; `mount | grep cgroup` ; `yarn --cwd .`
- Example benign flagged (FP): `unset -f ls /bin/ls` ; `zeroclaw cron add "* * * * *" "command"` ; `echo "{:key 'val}" | bb -I "(:key (first *input*))"`

## xgboost_hybrid/dataset2

- Confusion [tn, fp, fn, tp] = [1368, 68, 81, 398]; F1 0.842, Recall 0.831, FPR 0.047.
- **False negatives** dominated by source(s): {'honeypot': 40}.
- **False positives** dominated by source(s): {'bash_history': 37, 'commandlinefu': 3}.
- Example missed attacks (FN): `nano u.txt` ; `31m>>>> Server Gasit incepem Testele \033[1` ; `/gisdfoewrsfdf`
- Example benign flagged (FP): `Zsh` ; `exercicio1403` ; `rm -rf /usr/bin/python`

## cnn1d/dataset1

- Confusion [tn, fp, fn, tp] = [2158, 129, 90, 672]; F1 0.860, Recall 0.882, FPR 0.056.
- **False negatives** dominated by source(s): {'hacktricks': 22, 'gtfobins': 13, 'atomic_red_team': 5}.
- **False positives** dominated by source(s): {'tldr': 11, 'linlm': 11, 'nl2bash': 10, 'bash6k': 8}.
- Example missed attacks (FN): `bconsole` ; `apparmor_parser` ; `yarn --cwd .`
- Example benign flagged (FP): `unset -f ls /bin/ls` ; `echo "{:key 'val}" | bb -I "(:key (first *input*))"` ; `docker run -e VAR=value nginx`

## cnn1d/dataset2

- Confusion [tn, fp, fn, tp] = [1340, 96, 64, 415]; F1 0.838, Recall 0.866, FPR 0.067.
- **False negatives** dominated by source(s): {'honeypot': 40}.
- **False positives** dominated by source(s): {'bash_history': 35, 'commandlinefu': 5}.
- Example missed attacks (FN): `nano u.txt` ; `31m>>>> Server Gasit incepem Testele \033[1` ; `/gisdfoewrsfdf`
- Example benign flagged (FP): `Zsh` ; `dpigs` ; `cp ~/.functions bash/`

**Cross-model contrast to write up:** compare which commands XGBoost misses that the CNN catches and vice-versa — the CNN reads raw char motifs (catches obfuscated/adjacent payloads), XGBoost reads engineered conjunctions (catches family co-occurrence). The disagreement set is exactly what the cascade (8.4) and the LLM triage (bonus) are designed to resolve.