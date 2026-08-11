# Chapter 8.1 — Forensic error analysis (Ben's models)

Confusion matrices: `report/figures/ch8_confusion_xgboost_hybrid_dataset1.png`, `report/figures/ch8_confusion_xgboost_hybrid_dataset2.png`, `report/figures/ch8_confusion_cnn1d_dataset1.png`, `report/figures/ch8_confusion_cnn1d_dataset2.png`. Sample-level FN/FP command strings (capped at 40 per cell): `results/ch8_failures.json`. The by-source counts below are over every error, from `results/ch8_confusion.json`.

## xgboost_hybrid/dataset1

- Confusion [tn, fp, fn, tp] = [2192, 95, 94, 668]; F1 0.876, Recall 0.877, FPR 0.042.
- **False negatives** by source (all 94): {'hacktricks': 59, 'gtfobins': 19, 'atomic_red_team': 15, 'slp': 1}.
- **False positives** by source (all 95): {'tldr': 29, 'nl2bash': 28, 'linlm': 21, 'bash6k': 14, 'bash_instruct': 3}.
- Example missed attacks (FN): `bconsole` ; `apparmor_parser` ; `[ ! -z "$COMMAND" ] && echo VERSIONSTART "$p" "$("${COMMAND%%[[:space:`
- Example benign flagged (FP): `unset -f ls /bin/ls` ; `zeroclaw cron add "* * * * *" "command"` ; `fluent-bit -c /etc/fluent-bit/fluent-bit.conf`

## xgboost_hybrid/dataset2

- Confusion [tn, fp, fn, tp] = [1365, 71, 74, 405]; F1 0.848, Recall 0.846, FPR 0.049.
- **False negatives** by source (all 74): {'honeypot': 74}.
- **False positives** by source (all 71): {'bash_history': 58, 'commandlinefu': 13}.
- Example missed attacks (FN): `nano u.txt` ; `31m>>>> Server Gasit incepem Testele \033[1` ; `/gisdfoewrsfdf`
- Example benign flagged (FP): `Zsh` ; `tar -zxvf 'download (1)'` ; `cat i3log* 2> /dev/null | tail`

## cnn1d/dataset1

- Confusion [tn, fp, fn, tp] = [2160, 127, 91, 671]; F1 0.860, Recall 0.881, FPR 0.056.
- **False negatives** by source (all 91): {'hacktricks': 51, 'gtfobins': 22, 'atomic_red_team': 16, 'slp': 2}.
- **False positives** by source (all 127): {'tldr': 39, 'nl2bash': 37, 'linlm': 32, 'bash6k': 15, 'bash_instruct': 4}.
- Example missed attacks (FN): `bconsole` ; `apparmor_parser` ; `yarn --cwd .`
- Example benign flagged (FP): `unset -f ls /bin/ls` ; `echo "{:key 'val}" | bb -I "(:key (first *input*))"` ; `docker run -e VAR=value nginx`

## cnn1d/dataset2

- Confusion [tn, fp, fn, tp] = [1340, 96, 64, 415]; F1 0.838, Recall 0.866, FPR 0.067.
- **False negatives** by source (all 64): {'honeypot': 64}.
- **False positives** by source (all 96): {'bash_history': 72, 'commandlinefu': 24}.
- Example missed attacks (FN): `nano u.txt` ; `31m>>>> Server Gasit incepem Testele \033[1` ; `/gisdfoewrsfdf`
- Example benign flagged (FP): `Zsh` ; `dpigs` ; `cp ~/.functions bash/`

**Cross-model contrast to write up:** compare which commands XGBoost misses that the CNN catches and vice-versa — the CNN reads raw char motifs (catches obfuscated/adjacent payloads), XGBoost reads engineered conjunctions (catches family co-occurrence). The disagreement set is exactly what the cascade (8.4) and the LLM triage (bonus) are designed to resolve.