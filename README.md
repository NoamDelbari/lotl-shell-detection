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

**Datasets are not included in this submission ZIP.** The four `dataset/*.csv` files (and the large raw corpora) are excluded to keep the archive small — every source is public and rebuildable. To reproduce them locally, run `cd scripts && python build_dataset.py`, which downloads the attack sources (HackTricks, GTFOBins, Atomic Red Team, QuasarNix, SLP, PayloadsAllTheThings) and the benign sources (tldr-pages, bash-instruct, nl2bash, LinLM, bash6k, commandlinefu, real `.bash_history`), plus the Cowrie SSH-honeypot captures for Dataset 2, and rebuilds `dataset/` deterministically (`SEED = 42`). Per-source URLs, licences and processing steps are documented in [`docs/DATA_CARD.md`](docs/DATA_CARD.md).

## What's in this submission

The submission is a single archive — `Group_209361864_315005066_Final_Project.zip` — with the three parts the assignment requires: the code repository, the technical report, and the AI conversation logs.

**Technical report (Word)**
- `Group_209361864_315005066_Report.docx` — the graded report: title page + 15-page body (Executive Summary, Ch1–8, Bonus) + 5-page appendix (A Code Execution, B Environment, C supplementary Ch8.1/8.4 detail). Assembled from `report/*.md` by `build_report.py`.

**Code repository**
- `main.py` — CLI entry point: `python main.py {cv|holdout|transfer|all}` (see report Appendix A and `PIPELINE.md`).
- `src/` — the dataset-agnostic pipeline: `ingestion.py`, `features.py` (43 engineered features), `preprocessing.py`, `models.py` (XGBoost, XGBoost-hybrid, 1D-CNN, Random Forest, Isolation Forest), `evaluation.py`, `ensemble.py` (cascade), `llm_triage.py` (LLM arbitration).
- `analysis/` — one script per report artefact: `ch3_eda.py`, `ch4_ranking.py`, `ch7_train.py`, `ch8_error_analysis.py`, `ch8_4_cascade.py`, `bonus_b3_llm_eval.py`, …
- `scripts/` — `build_dataset.py` (rebuilds the datasets from public sources), `evaluate_baseline.py` (char n-gram TF-IDF baseline), `extractors/`.
- `tests/` — `test_pipeline.py` (no-leakage + dataset-agnostic guardrails).
- `requirements.txt`, `PIPELINE.md` (architecture + reproduction guide), `build_report.py` (builds the report docx).

**Results and report source**
- `results/` — machine-readable metrics: `summary.json` (headline F1 / ROC-AUC / FPR for every model on both datasets), per-model `holdout_*` / `transfer_*` JSON, cascade and forensics JSON.
- `report/` — the Markdown source of every chapter, plus `report/figures/` (class-balance, variance-by-label, correlation, feature-importance, sensitivity and confusion-matrix PNGs).

**Documentation (`docs/`)**
- `DATA_CARD.md` — dataset provenance, sources, licences, processing.
- `BASELINE.md`, `baseline_metrics.json`, `stats.json` — baseline scores and dataset statistics.
- `KNOWN_ISSUES.md` — audit trail of the confounds/shortcuts found and mitigated.
- `Final_Project_AI_Driven_Intrusion_Detection.pdf` — the assignment brief.

**AI conversation logs (`ai_logs/`, course requirement)**
- `claude_code_log.txt` — the full, unedited transcript of every Claude Code session (both team members, chronological; `.txt` as required).
- `claude_session.md`, `README.md` — per-session transcript and an index.

**Deliberately excluded** (public and rebuildable, to keep the archive small): the dataset CSVs (`dataset/`) and the raw source corpora (`scripts/raw/`). Rebuild them with `cd scripts && python build_dataset.py` — see **The two datasets** above and `docs/DATA_CARD.md`.

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

## Reproducing the results

```bash
pip install -r requirements.txt
python main.py all                      # train all five models on both datasets -> results/summary.json
python analysis/ch3_eda.py              # EDA figures + feature justification
python analysis/ch4_ranking.py          # tree-based feature ranking
python analysis/ch7_train.py            # CV + hyperparameter sensitivity
python analysis/ch8_error_analysis.py   # forensic error analysis + cross-dataset table
python analysis/ch8_4_cascade.py        # hybrid cascade ensemble
python analysis/bonus_b3_llm_eval.py --hf   # bonus LLM triage (needs HF_TOKEN)
python tests/test_pipeline.py           # no-leakage + dataset-agnostic guardrails
python build_report.py                  # assemble the report .docx from report/*.md
```

Everything is seeded (`SEED = 42`). `PIPELINE.md` and report Appendix A give the full command reference; the bonus B.3 results in the report used a local Llama-3.1-8B via Ollama (`src/llm_triage.py` `ollama_arbitrator`).

## AI usage

Per course policy, all AI-tool conversations are logged unedited and ship in the submission under `ai_logs/`. The only tool used was **Claude Code**; its full, chronological transcript across all sessions is `ai_logs/claude_code_log.txt` (`.txt`, as required).
