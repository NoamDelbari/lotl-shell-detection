# Malicious Linux Shell Command Detection (LotL, T1059.004)

Final project — Course 3917 *Using AI for Malware and Intrusion Detection*, Reichman University, Semester 2 2026.
**Team:** Ben Volovelsky · Noam Delbari

Binary classification of single Linux shell command lines — **attack (1) vs normal (0)** — as recorded in host telemetry (auditd `EXECVE`, bash history). The target is **Living-off-the-Land** abuse of the Unix shell (MITRE ATT&CK **T1059.004**): reverse shells, download-and-execute, GTFOBins escapes, enumeration bursts, persistence and anti-forensics, all driven through trusted pre-installed binaries instead of droppable malware.

## The two datasets

Both are assembled from public sources (no single public corpus carries both classes at scale), provenance-matched within each dataset, 1 attack : 3 normal, and split 80/20 grouped by command *shape* so no structure straddles train/test.

| | Attacks from | Normal from | Size (train/test) |
|---|---|---|---|
| **Dataset 1** — curated | HackTricks, GTFOBins, Atomic Red Team, QuasarNix, SLP, Payloads | tldr-pages, bash-instruct, nl2bash, LinLM, bash6k | 15,248 (12,199 / 3,049) |
| **Dataset 2** — real | SSH honeypot sessions (233k Cowrie captures) | real `.bash_history` files, commandlinefu | 9,576 (7,661 / 1,915) |

Labels are **provenance-based, never lexical** — a command is malicious because of where it came from, not because it matches a keyword. Full provenance, licences, processing and caveats: [`docs/DATA_CARD.md`](docs/DATA_CARD.md).

## Repo layout

```
dataset/     the four deliverable CSVs (columns: id, command, label, source, split)
scripts/
  build_dataset.py        rebuilds both datasets end-to-end from public sources
  evaluate_baseline.py    TF-IDF + logistic baseline, ablations, confound probes
  extractors/             one-shot scripts that produced scripts/raw/extracted/*.cm
  raw/                    build inputs (extracted/*.cm vendored; rest re-downloads)
docs/
  Final_Project_AI_Driven_Intrusion_Detection.pdf   the assignment spec (rubric inside)
  WORK_DIVISION.md        who does what, deadlines, ground rules
  DATA_CARD.md            dataset provenance and processing
  BASELINE.md             baseline scores + regression probes
  KNOWN_ISSUES.md         audit trail of confounds found and fixed (P1–P8)
  stats.json / baseline_metrics.json                machine-readable sources of truth
preliminary_proposal.md   the approved proposal (threat analysis, log mapping, literature)
```

## Quickstart

```bash
pip install -r requirements.txt
cd scripts
python build_dataset.py        # re-downloads missing raw/ caches, rebuilds dataset/ + docs
python evaluate_baseline.py    # retrains baseline, rewrites BASELINE.md + metrics json
```

Both scripts are seeded (`SEED = 42`); a rebuild reproduces the shipped files exactly.

**Gotchas**

- Read the CSVs with `pd.read_csv(..., na_filter=False)` — dataset 2 contains the literal commands `nan` and `null`.
- The `.cm` files under `scripts/raw/` are attack-command corpora (inert text). Antivirus may quarantine one during a rebuild; re-running the extractor regenerates it.
- Before quoting any score, read the top of [`docs/BASELINE.md`](docs/BASELINE.md) and [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md) — every number comes with a prevalence floor and known-shortcut context.

**Compute environments.** Ben's results (XGBoost-hybrid, 1D-CNN, Baseline,
cross-dataset transfer, cascade, Ch7 sensitivity, Ch8 forensics) were produced
on macOS with an Apple M3 Pro. Noam's results (Random Forest, Isolation Forest,
Ch3 EDA figures, Ch4 ranking figures, Ch6 sub-sample probe, Ch7 RF/IF sweeps,
Ch8 RF/IF forensics) were produced on Windows 11, CPU only.

## Where the project is, and where it's going

**Done:** datasets built and audited (leakage, label-circularity and shortcut probes), preliminary baseline with confound analysis, approved proposal.

**Next (due Aug 15, 2026 — see [`docs/WORK_DIVISION.md`](docs/WORK_DIVISION.md) for owners and dates):**

1. Engineered feature extractor over raw command text + per-dataset EDA (Ch1–3)
2. Tree-based feature ranking vs domain intuition (Ch4)
3. Modular dataset-agnostic pipeline; four models — XGBoost, 1D-CNN, Random Forest, Isolation Forest — with k-fold CV and hyperparameter sensitivity (Ch6–7)
4. Forensic error analysis, cross-dataset transfer, cascading ensemble (Ch8)
5. Bonus: LLM triage layer for edge-case arbitration (HF Inference)

## AI usage

Per course policy, all AI-tool conversations are logged unedited and ship with the final submission under `ai_logs/`, one file per tool.
