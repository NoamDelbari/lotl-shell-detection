# Design: `featurize()` redesign — Noam's Ch3 feature-extractor deliverable

**Date:** 2026-08-08 · **Owner:** Noam (with Claude Code, per AI policy: decisions made jointly, logged)
**Branch:** `noam/features-ch3` (off `origin/ben/pipeline-models-ch3-8`)
**Milestone:** WORK_DIVISION.md — "Aug 8: Noam: `featurize()` module done" (blocks Ben's Ch3, Ch4, Ch7)

## Context

Ben's branch ships a *provisional* `featurize()` in `src/features.py` (37 features) so his
pipeline skeleton could run end-to-end. The file header marks it as Noam's deliverable to
replace/own. This design covers the redesign: an **audit + extend** pass with EDA evidence
in the loop, grounded in the ShellCore paper (Noam's Ch2 paper). Approved decisions from
the session: free to change the feature set (Ben re-runs downstream); ShellCore grounding
now (paper walked through together 2026-08-08, matrix in
`report/ch2_shellcore_matrix_noam.md`); all four new candidate families (A–D) enter the
audit.

The deliverable is graded across four chapters: Ch1 (each feature needs a
behavior→telemetry→field→feature→rationale mapping row; Noam owes 4 rows), Ch2 (explicit
adopt/modify/reject vs ShellCore), Ch3 (hard empirical justification per feature +
systematic redundancy reduction), Ch4 (discrepancy analysis incl. leakage/testbed
artifacts — the spec explicitly warns about testbed shortcuts like literal IPs).

## Goals / non-goals

**Goals:** own the feature set; every surviving feature empirically justified (train-split
evidence); redundancy pruned systematically; leakage/testbed shortcuts probed and
documented (Ch4 seed); ShellCore adopt/modify/reject recorded (Ch2 seed); contract
preserved so Ben's pipeline runs unchanged.

**Non-goals (later sessions):** Dataset-2 EDA chapter writing (reuses this audit's
evidence); Ch4 discrepancy analysis prose; models (Ch7); Ben's char n-gram block and CNN
encoder (untouched); report assembly.

## Contract (unchanged — Ben's pipeline depends on it)

- `featurize(commands) -> pd.DataFrame`, `columns == FEATURE_NAMES`, numeric, finite,
  deterministic, row-independent. `FEATURE_NAMES` stays the single authoritative order.
- `src/preprocessing.py` (`EngineeredFeatures`), models, and `tests/test_pipeline.py`
  stay untouched and must pass unchanged. The *column list* may change freely.
- Error handling: empty/whitespace command → all-zero row; inputs coerced via `str()`;
  existing no-NaN/inf guard retained.

## Audit protocol (EDA-in-the-loop)

New script `analysis/ch3_feature_audit.py` (seeded, SEED=42), reads **train splits only**
(`pd.read_csv(..., na_filter=False)`), computes per feature × per dataset:

1. **Signal:** class-conditional mean/median, Mann-Whitney U p-value, effect size —
   Cliff's delta (continuous) or odds ratio (binary). A feature must show significant
   separation on ≥1 dataset to survive.
2. **Redundancy (Ch3.2):** Spearman matrix; clusters at |ρ| > 0.9 keep one representative,
   rest killed with the cluster named as reason.
3. **Leakage probes (Ch4 seed):** per feature, label-vs-source separation strength; the
   KNOWN_ISSUES P8 IPv4 check on D1 (QuasarNix carries IPv4 in 100% of rows; "any IPv4"
   rule alone = F1 0.938 on D1); overlap with D2's *retired* P1 selection markers
   (`wget`, `curl`, `chmod +x`, `| sh`, `/dev/tcp`, …) — echoing a retired marker is not
   disqualifying (P1 is fixed, labels are provenance-based) but must be flagged.
4. **Verdicts:** every feature gets KEEP / REDEFINE / KILL + one-line rationale →
   `results/ch3_feature_audit.json` (evidence) + `report/ch3_feature_decisions.md`
   (human-readable table). Verdicts are decided **jointly** (Claude computes and presents
   evidence; Noam calls each verdict). Target final set ≈ 35–45 features (page budget:
   each survivor must be individually defended in Ch3.3).

## Feature changes entering the audit

**Fixes to the existing 37:**
- Dedupe vocabulary overlaps so each token belongs to exactly one family (`/var/log` in
  both `_EVASION_TOK` and `_SENSITIVE_PATHS`; `lua` in `_LOTL_BINS` and `_INTERP_BINS`;
  `chattr` in `_PRIVESC_BINS` and `_EVASION_TOK`).
- `has_exec_flag`: currently ungated regex `(?:^|\s)-\w*[ec]\b` (fires on `grep -e`,
  `tar -c`). Redefine: `-c`/`-e` flag token must immediately follow a shell/interpreter/nc
  binary (`sh -c`, `python -c`, `nc -e`).
- `n_redirects`: split into `n_redirect_out` (`>`, `>>`), `n_redirect_in` (`<`),
  `has_stderr_merge` (`2>&1`, `>&`) — stderr-merge is a reverse-shell fingerprint; plain
  `>` is everyday scripting.
- IPv4: keep `has_ipv4`/`n_ipv4` but audit-flag against P8; add `has_private_ip` /
  `has_public_ip` split (honeypot C2s are public; tutorial examples usually private).
  Verdict decided on evidence; whatever survives becomes Ch4 discrepancy exhibit A.

**New candidate families (all four approved by Noam — "do them all"):**
- **A. Head-binary + argument shape:** head = first token after skipping leading
  `VAR=val` assignments and wrappers (`sudo`, `env`, `nohup`, `time`; if head is
  `busybox`, resolve to the next token). Features: `head_is_fetch`, `head_is_shell`,
  `head_is_interp`, `head_is_enum`, `head_is_privesc`, `head_is_lotl` (0/1);
  `n_flags` (tokens starting `-`), `has_long_flag` (`--word`), `n_assign_prefix`.
  Distinguishes `python -c '…'` from `echo python`.
- **B. Rev-shell / download-exec micro-structure** (proposal §3 behaviours as explicit
  composites; download-exec = 17.8% of real honeypot attacks, the head of D2's
  distribution): `has_stderr_merge` (shared with the redirect split), `has_pipe_to_shell`
  (`|` directly into a `_SHELL_BINS` member), `has_fetch_exec_chain` (fetch bin present
  AND pipe-to-shell), `has_decode_exec` (`base64 -d`/`-D` feeding a pipe),
  `has_ifs_expansion` (`${IFS}`), `has_heredoc` (`<<`), `has_dev_null` (`>/dev/null`).
- **C. Path & filesystem refinement** (split the lumped `n_sensitive_paths`):
  `n_abs_paths` (tokens starting `/`), `has_hidden_path` (dot-directories: `/.ssh`,
  `.bashrc`), `has_staging_dir` (`/tmp`, `/var/tmp`, `/dev/shm`), `has_home_ref`
  (`~`, `$HOME`), `n_cred_paths` (`/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `.ssh`,
  `authorized_keys`, `id_rsa`), `n_proc_paths` (`/proc/`), `n_log_paths` (`/var/log`).
  `n_sensitive_paths` retires if the split covers it (redundancy audit decides).
- **D. Obfuscation depth:** `n_var_assignments` (`VAR=`), `n_var_expansions`
  (`$VAR`, `${…}`), `has_quote_splice` (quote chars splitting a token: `w"h"oami`),
  `n_backslash`, `subshell_depth` (max nesting of `$( )`).

**ShellCore grounding (Ch2 narrative, full matrix in `report/ch2_shellcore_matrix_noam.md`):**
adopt the char-level insight (operators/symbols carry the signal → our structural
counts); modify term-level BoW into fixed threat-mapped binary families (their
malware-only ablation — term-level 99.86→89.52, char-level stable — is the measured
failure our modification fixes); reject PCA (kills Ch4 interpretability) and unbounded
1–5-grams (Ben's block caps char 3–5-grams, fit per fold).

## Deliverables

1. `src/features.py` — rewritten (fixes + surviving candidates), grouped by behavior
   family, one-line threat-rationale comment per feature (Ch1 source material).
2. `analysis/ch3_feature_audit.py` — the audit script (above).
3. `results/ch3_feature_audit.json` + `report/ch3_feature_decisions.md` — evidence +
   verdict table.
4. `report/ch2_shellcore_matrix_noam.md` — adopt/modify/reject matrix + Ch8.3 benchmark
   numbers (committed with this spec).
5. Tests: extend `test_featurize_contract` edge cases — empty/whitespace command, literal
   `nan`/`null` strings (README gotcha), unicode/emoji, 10k-char command.

## Acceptance criteria

- `python tests/test_pipeline.py` passes unchanged.
- `python main.py holdout --model random_forest --dataset dataset1` runs end-to-end.
- Every final `FEATURE_NAMES` entry has verdict + evidence in the audit JSON; no
  |ρ| > 0.9 pair survives undocumented.
- Ben notified that downstream results (Ch4 ranking, holdouts, sensitivity, figures)
  need re-running after merge.

## Notes / follow-ups

- `report/ch4_ranking_findings.md` on Ben's branch references feature names that don't
  exist in current `features.py` (`shell_bins`, `redirect_count`, `path_proc`…) — stale
  draft from an earlier iteration; flag to Ben, regenerates after this change anyway.
- ShellCore PDF kept untracked at `docs/refs/shellcore_arxiv_2103.14221.pdf` (arXiv
  redistribution licensing); cited by arXiv id in the report.
- Next sessions (in order): Dataset-2 EDA (Ch3, reuses audit evidence) → Ch7 RF/IF
  hyperparams + sensitivity → Ch4 discrepancy prose → Ch8.1/8.3/8.4 → bonus LLM wiring.
