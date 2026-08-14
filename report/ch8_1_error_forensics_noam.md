# Chapter 8.1 — Forensic error analysis (Noam's models)

Confusion matrices: `report/figures/ch8_confusion_random_forest_dataset1.png`, `report/figures/ch8_confusion_random_forest_dataset2.png`, `report/figures/ch8_confusion_isolation_forest_dataset1.png`, `report/figures/ch8_confusion_isolation_forest_dataset2.png`. Sample-level FN/FP command strings (capped at 40 per cell): `results/ch8_failures.json`. The by-source counts below are over every error, from `results/ch8_confusion.json`.

## random_forest/dataset1

- Confusion [tn, fp, fn, tp] = [2210, 77, 207, 555]; F1 0.796, Recall 0.728, FPR 0.034.
- **False negatives** by source (all 207): {'hacktricks': 111, 'gtfobins': 52, 'atomic_red_team': 39, 'payloads': 3, 'slp': 2}.
- **False positives** by source (all 77): {'nl2bash': 24, 'tldr': 19, 'linlm': 18, 'bash6k': 14, 'bash_instruct': 2}.
- Example missed attacks (FN): `var port=12345;` ; `bconsole` ; `for ip in $(seq 1 254); do ping -c 1 192.168.1.$ip; [ $? -eq 0 ] && ec`
- Example benign flagged (FP): `fluent-bit -c /etc/fluent-bit/fluent-bit.conf` ; `mkdir "${HOME}/.npm-packages"` ; `sqlite3 /var/www/file_hashes.db "CREATE TABLE IF NOT EXISTS file_hashe`

## random_forest/dataset2

- Confusion [tn, fp, fn, tp] = [1362, 74, 145, 334]; F1 0.753, Recall 0.697, FPR 0.052.
- **False negatives** by source (all 145): {'honeypot': 145}.
- **False positives** by source (all 74): {'bash_history': 61, 'commandlinefu': 13}.
- Example missed attacks (FN): `nano u.txt` ; `31m>>>> Server Gasit incepem Testele \033[1` ; `cat tmp.rwG6eULB7M.sh`
- Example benign flagged (FP): `Zsh` ; `exercicio1403` ; `python ldr2.0`

## isolation_forest/dataset1

- Confusion [tn, fp, fn, tp] = [2269, 18, 651, 111]; F1 0.249, Recall 0.146, FPR 0.008.
- **False negatives** by source (all 651): {'hacktricks': 324, 'gtfobins': 178, 'atomic_red_team': 111, 'slp': 15, 'quasarnix': 14, 'payloads': 9}.
- **False positives** by source (all 18): {'nl2bash': 8, 'bash6k': 7, 'tldr': 2, 'linlm': 1}.
- Example missed attacks (FN): `tar xf /path/to/temp-file.tar --to-command /bin/sh` ; `/usr/bin/python2.7 = cap_sys_ptrace+ep` ; `oxdf@hacky$ gcc a.c -o /mnt/nfsshare/a;`
- Example benign flagged (FP): `yes '' | ruby -e "$(curl -fsSL https://h658b4b87.example.net/Homebrew/` ; `find "$DIR_TO_CLEAN" -mtime +$DAYS_TO_SAVE -exec bash -c 'printf "coun` ; `git_latest_hash(){ local repo="$1"; local branch="$2"; local dir=$(mkt`

## isolation_forest/dataset2

- Confusion [tn, fp, fn, tp] = [1422, 14, 441, 38]; F1 0.143, Recall 0.079, FPR 0.010.
- **False negatives** by source (all 441): {'honeypot': 441}.
- **False positives** by source (all 14): {'commandlinefu': 12, 'bash_history': 2}.
- Example missed attacks (FN): `nano u.txt` ; `/bin/busybox echo -e '\x47\x72\x6f\x70/sys/firmware' > /sys/firmware/.` ; `./.dhpcd`
- Example benign flagged (FP): `rm -rf /tmp/playlist.tmp && find ~/mp3 -name *.mp3 > /tmp/playlist.tmp` ; `perl -Mojo -E 'say g("http://ha20fa670.example.net/popclock/data/popul` ; `markdown doc.md >/tmp/md.$$.html && firefox -new-tab /tmp/md.$$.html >`

**The write-up lives in `report/ch8_1_rf_if_forensics.md`** — this file is generated evidence, so put prose there, not here. The overlap, recovery and feature-signature figures it quotes come from `analysis/ch8_1_rf_if_forensics.py`, which keeps every test-row prediction instead of the 40-row samples below. Headline results: RF and IF have *nested* false negatives (on Dataset 1 IF catches nothing RF misses) but *near-disjoint* false positives, so their complementarity is about benign traffic; XGBoost-hybrid recovers ~58% of RF's misses, which is the 8.4 cascade premise. Note RF is the lowest-FPR supervised model on Dataset 1 only — on Dataset 2 the hybrid and the TF-IDF baseline both run cleaner. Cross-reference `report/ch7_rf_if_sensitivity_findings.md` for why IF's shipped operating point sits in an extreme-precision corner rather than re-deriving it.