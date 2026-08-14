# Noam — writing brief for the remaining chapters

Prepared 2026-08-10. Companion to `NOAM_TODO.md`: that file is the checklist,
this one is the *pre-gathered source material* for each chapter I still have to
write, plus the traps I verified against the current tree rather than trusting
the checklist.

Freeze **Aug 14**, submit **Aug 15**. Everything below is mine except where noted.

---

## Corrections to `NOAM_TODO.md` found while preparing this

Verified against the tree today — fix these before relying on the checklist:

1. **`build_hybrid_pipeline()` does not exist.** Ch5 §5.3 in the TODO tells me to
   cite it. The real names are `build_hybrid_features()` (`src/preprocessing.py:75`)
   and `build_xgboost_hybrid()` (`src/models.py:86`). `EngineeredFeatures` *is* in
   `src/preprocessing.py:34` as the TODO says.
2. **Appendix B hardware is wrong for half the project.** It claims macOS +
   Apple-M-series MPS. That is Ben's machine; all of my work (Ch3 EDA, Ch7 sweeps,
   Ch6, the regenerated results) ran on **Windows 11 / CPU**. The appendix has to
   state both environments or it misdescribes how the numbers were produced.
3. **Handoff item (e) assigns the cascade to Ben — wrong.** `WORK_DIVISION.md`
   gives **8.4 cascading ensemble to me**. Ben drafted
   `report/ch8_4_cascade_findings.md` (commit by `benvolovel`), but the fix and
   the rewrite are mine.
4. **Ben's Ch1 rows need more than a column reshuffle.** Rubric Gap 1 calls it a
   reformat, but his three rows also cite six dead feature names:
   `dev_tcp_present`, `redirect_count`, `shell_bins`, `fetch_bins`, `url_present`,
   `pipe_count`. Live equivalents: `has_dev_tcp`, `n_redirect_out`,
   `has_shell_bin`, `has_fetch_bin`, `has_url`, `n_pipes`.
5. **`ch2_shellcore_matrix_noam.md` has one stale line.** The "Adopt" row for the
   char-level insight cites "subshell/quote counts, `special_ratio`, entropies" —
   but the entropy features and `paren_count` were **killed** in the audit.
   `n_quotes` and `special_ratio` survive. Fix when the matrix becomes prose.
6. **Both Ch7 figures for Ben's models are pre-redesign**, confirmed by git:
   `ch7_sensitivity_xgboost.png` (9b58ddb, Aug 8) and the older suffixed
   `_dataset1/2` variants (eeeaf25, Aug 7). The unsuffixed pair is the newer one
   his prose depends on. Neither survives the 38→43 change.

---

## Chapter 1 — Threat Characterization (15 pts)

### What exists
`report/ch1_threat_mapping.md` — Ben's 3 rows (T1059.004 reverse shells,
T1105 download cradles, T1033 whoami/id discovery), in a **4-column** format,
with a strong closing "detectability tracks lexical distinguishability" takeaway
I should preserve and build on. Also `report/ch1_telemetry_rows_ben.md`.

### §1.1 Deep-dive threat analysis
Source: my preliminary proposal §2–3. Must cover — define T1059.004 and its
place in the ATT&CK Execution tactic; how LotL execution works at the OS layer
(fork/exec of a legitimate interpreter, no dropped binary, so file-based
detection has nothing to inspect); why the shell command string is therefore
the correct telemetry; and the provenance-labeling premise with its cost.

### §1.2 My 4 mapping rows — the required 5-column schema
`Adversarial Behavioral Characteristic | Required Telemetry Source | Specific
Log Attributes / Raw Fields | Derived / Engineered Feature | Detailed Explanation`

Candidate rows, each mapped to features that **actually exist** in the 43-set
(verified against `FEATURE_NAMES`) and each with evidence already sitting in
`report/ch3_feature_decisions.md`:

| # | Sub-technique | Live features | Evidence on hand |
|---|---|---|---|
| 1 | **T1027 — Obfuscated Files or Information** | `has_base64_blob`, `b64_run_len`, `has_hex_escape`, `has_decode_exec`, `has_quote_splice`, `has_ifs_expansion` | whole obfuscation family (6 features) |
| 2 | **T1548.003 — Sudo and Sudo Caching** | `head_is_privesc` **only** | `has_privesc_bin` was killed as class-neutral — say so in the Explanation column, it's a good honesty beat |
| 3 | **T1552.001 — Credentials In Files** | `n_sensitive_paths`, `n_abs_paths` | `n_abs_paths` is the **#1 Gini feature on D1 (0.134)** and #1 by rank-biserial (+0.452) |
| 4 | **T1202 — Indirect Command Execution** (LotL binary abuse) | `has_lotl_bin`, `head_is_lotl`, `has_interp_bin` | **the strongest row available**: both LotL features lean *benign* on both corpora (OR 0.62 D1 / 0.50 D2) |

Row 4 is the one to lead with in the write-up: the technique family the entire
project is named after is a **negative** predictor under provenance labels,
because GTFOBins-style binaries are overwhelmingly ordinary administration. That
extends Ben's T1033 "no content signature" case into something sharper — a
signature that points the *wrong way*. Confirm the exact ATT&CK ID against the
live page when writing (T1202 vs framing it under T1218); the feature evidence
holds either way.

Alternate row if I want a 5th or a swap: **T1074.001 Local Data Staging** →
`has_staging_dir` (`/tmp`, `/dev/shm`).

**Traps:** `base64_present` and `sudo_present` don't exist. **T1070.003 (shell
history deletion) has no feature in the 43-set** — don't invent one; either skip
it or state plainly that it's covered only indirectly.

### §1.3 Theoretical feature rationale — all 43 features
`report/ch3_feature_decisions.md` gives the section skeleton *and* the evidence
table per family. Verified counts:

| Family | Features | Family | Features |
|---|---:|---|---:|
| shape/size | 4 | A: head/args | 6 |
| structure/chaining | 4 | B: exec micro-structure | 8 |
| network/delivery | 4 | C: paths/filesystem | 5 |
| binary families | 6 | D: obfuscation | 6 |

Total 43. Write one short paragraph per family (8 paragraphs), not one per
feature — the per-feature evidence ships as the appendix CSV per Rubric Gap 4.

---

## Chapter 2 — ShellCore half (10 pts)

**This is closer to done than the checklist implies.** `report/ch2_shellcore_matrix_noam.md`
already contains the full extraction matrix (6 elements with paper sections), the
adopt/modify/reject table with reasoning, the Ch8.3 benchmark numbers, five
substantive reasons their operating point isn't face-value comparable, and a
contrast hook for Ben's comparative essay. **What's missing is prose, not
research.**

New since that file was written — I read the paper's evaluation section
directly, so these are now first-hand rather than second-hand:

- **Classifiers confirmed from Table 4**: LR, RF, DNN (5 hidden layers), 10-fold
  CV. Previously only in our own matrix, which would have been circular to cite.
- **RF specifically**: 99.78 Acc / 99.78 F-1 / 0.27 FNR / 0.19 FPR (char-level
  command detection); 99.91 / 99.91 / 0.14 / 0.07 at file level.
- **The malware-only ablation** (Table 4 right): term-level RF collapses to
  84.95 Acc / 84.96 F-1, char-level RF holds at 98.19 — the measured proof that
  learned vocabulary memorizes corpus style. Already cited in my Ch6 §6.4.
- **§4.3.2** confirms the DNN's five hidden layers were reached by tuning;
  **§4.3.3** confirms K=10.

Deliverables: (a) extraction matrix as report prose, (b) adopt/modify/reject
defense, (c) my half of the comparative analysis vs Trizna/SLP. Fix the stale
"entropies" line (correction 5 above) on the way through.

---

## Chapter 5 — Harmonization (10 pts) — entire chapter mine

**5.1 Unified feature schema.** The unified representation is the raw `command`
string, present in both datasets; `featurize()` extracts the same 43 features
regardless of source. The real harmonization argument is the **selection
protocol**: 68 candidates reduced to 43 under one gate applied identically to
both corpora (`report/ch3_feature_decisions.md`).

**5.2 Cross-dataset distribution shift.** Strongest ready-made material is in
`report/ch3_d2_eda_findings.md` — the **sign inversions** (`len_chars` r +0.247
D1 → −0.171 D2; `n_quotes` +0.081 → −0.112; `n_flags` +0.051 → −0.125) and the
LotL anti-signal. Live magnitude evidence: `has_shell_bin` OR **32.75 on D1 vs
5.99 on D2**. Artefacts available: `report/ch3_d1_feature_stats.csv`,
`ch3_d2_feature_stats.csv`, `ch3_feature_justification.csv`,
`ch4_feature_ranking.csv`, plus `ch3_corr_heatmap_dataset{1,2}.png` and
`ch3_variance_by_label_dataset{1,2}.png`.
⚠️ Do **not** reuse the old `shell_bins` / `lotl_bins` gain-inversion digits —
dead names, pre-redesign numbers. Re-read gains from the regenerated Ch4 CSV.

**5.3 Scaling.** `StandardScaler` fitted inside the sklearn `Pipeline` so it
only ever sees the training fold — that's the leakage argument. Cite
`src/preprocessing.py` (`EngineeredFeatures`, `build_hybrid_features`) and
`src/models.py` (`build_xgboost_hybrid`) — **not** `build_hybrid_pipeline`.
I have a measured result to make this concrete rather than assertive: removing
the scaler moves RF F1 by 0.0017 (D1) / 0.0003 (D2) and leaves IF scores
bit-identical, because tree splits depend only on rank order (Ch6 §6.4). So the
honest framing is: the scaler is a *contract* for pipeline uniformity, load-bearing
for distance/gradient models, a no-op for my two.

---

## Chapter 8 — my parts (20 pts, shared)

**8.1 RF + IF error forensics.** Read the regenerated
`results/holdout_random_forest_*.json` / `holdout_isolation_forest_*.json` —
already re-run, and they carry the `per_source` breakdown. Questions to answer:
FN/FP counts on both datasets; which benign sources IF flags hardest; and
**when RF fails, does XGBoost succeed?** (that's the cascade motivation).
Build on `report/ch7_rf_if_sensitivity_findings.md` for *why* IF sits in an
extreme-precision corner (recall 0.146 / FPR 0.008 on D1) instead of re-deriving it.
Key numbers: RF D1 P 0.8782 / R 0.7283 / FPR 0.0337; IF D1 R 0.1457 / FPR 0.0079.

⚠️ **Corrected 2026-08-10:** this line used to read "lowest false-alarm rate of
any supervised model in the project". That holds on **D1 only**. On D2, RF's
0.0515 is beaten by xgboost_hybrid (0.0494) and the TF-IDF baseline (0.0481).
Don't reuse the unqualified phrasing in 8.3 or the exec summary.

✅ **DONE 2026-08-10** → `report/ch8_1_rf_if_forensics.md`, backed by
`analysis/ch8_1_rf_if_forensics.py`. Headline: RF/IF false negatives are
*nested* (D1: IF catches nothing RF misses) but their false positives are
*near-disjoint* (Jaccard 0.056 / 0.011), so the cascade's complementarity is
about benign traffic, not attacks. Hybrid recovers 59.4% / 57.2% of RF's misses.

**Rubric Gap 2 — missing figures.** ✅ **CLOSED 2026-08-10.** All four
`ch8_confusion_{random_forest,isolation_forest}_dataset{1,2}.png` now exist and
match the existing naming. They are **untracked** — commit them or the gap
reopens at packaging time.

**8.3 vs ShellCore.** ✅ **DONE 2026-08-10** → `report/ch8_3_shellcore_comparison.md`.
Cites `ch2_3` for the metric reconstruction and the four confounds instead of
re-deriving. New material: the gap to their char-level RF decomposes exactly
into **+10.12 representation / +10.03 corpus-and-protocol** (using our char
n-gram `baseline` as the one-variable-at-a-time control) — the 20.15-point gap
splits almost exactly in half; ShellCore's *representation* thesis is
independently confirmed on our data (the baseline beats all five
engineered-feature models on both corpora, D1 0.8975 vs the hybrid's 0.8761);
and the Isolation Forest is reported as **below its own do-nothing floor**
(0.2492 / 0.1431 vs 0.400), as is RF's D2→D1 transfer (0.1432).

⚠️ **Revised 2026-08-10 (was +8.45 / +11.70, i.e. 40/60).** The chapter had been
pivoting on baseline D1 F1 0.8808, which comes from
`results/holdout_baseline_dataset1.json` — an orphan file with **no producing
code**. The reproducible figure from `scripts/evaluate_baseline.py` →
`docs/baseline_metrics.json` is **0.8975** (D2 **0.8824**), which is also what
`docs/BASELINE.md`, `docs/DATA_CARD.md` and the preliminary proposal already
publish. All baseline numbers in 8.3, 8.1 and the exec summary now come from
that file; delete the four orphan `results/*baseline*` files at packaging.

**8.4 Cascade — mine per WORK_DIVISION. ✅ DONE 2026-08-10 →
`report/ch8_4_cascade_analysis.md`.** The threshold fix (dropping the dead
`stage1_clear_below=0.15` in favour of recall-calibrated clearing,
`stage1_retain_recall=0.99`, effective 0.0033 D1 / 0.0032 D2) was already
applied and the generated results file already current, so this was prose only.
New evidence: `analysis/ch8_4_cascade_forensics.py` →
`results/ch8_4_cascade_forensics.json`.

The chapter is a **negative result** and should stay one at assembly. Every
stage makes the system worse (D1 F1: hybrid alone 0.8761 > stage1+2 0.8737 >
stage2+3 0.8716 > full cascade 0.8685; D2 the same ordering), the precision
gain costs 1.10 / 1.05 missed attacks per false alarm avoided, and **three
single decision thresholds on stage 2 alone match or beat the whole cascade on
both precision and recall** (D1 t = 0.65/0.66/0.67; on D2 t = 0.66 reproduces
its confusion matrix to four decimals). Stage 3 as run is a threshold shift, not
arbitration: the offline stub fired on 0 of 146 routed D1 commands because all
39 motif-matching test commands are attacks stage 2 is already sure about.

⚠️ **Keep the constructive half — it is the bonus chapter's target.** The
router is sound (band prevalence 0.411 / 0.386 vs 0.250; hybrid accuracy 58.9%
/ 63.4% inside the band vs 95.6% / 94.1% outside), and an oracle arbitrator on
it is worth **+3.7 F1 over the best single model** (0.9132 / 0.8849). Score the
bonus against +3.7, not against zero.

---

## Bonus — LLM triage (+10 pts, optional)

Scaffolding exists (`src/llm_triage.py`, `analysis/bonus_b3_llm_eval.py`, cascade
wired to the arbitrator). Needs `HF_TOKEN` (**never commit it**), then
`python analysis/bonus_b3_llm_eval.py --hf`, then replace the stub tables in
`bonus_b3_findings.md` and `ch8_4_cascade_findings.md`, then write B.1/B.2/B.4.
⚠️ **The old B.4 conclusion here was wrong about the call count** — the
36–42% edge fraction / ~800–1100 calls figure is `select_edge_cases`, not the
cascade band. Measured 2026-08-10: the [0.35, 0.65] band is **146 calls on D1
and 101 on D2** (4.8% / 5.3% of traffic), ≈4–12 min for both test sets, so B.4's
verdict flips to viable at this band width. Targets from 8.4: oracle ceiling
**+3.7 F1**, and the arbitrator must beat **58.9% / 63.4%** accuracy on those
rows (stage 2's own accuracy there, which the stub exactly ties) or it is pure
latency. Drop this chapter first if time runs out (ground rule).

---

## Executive summary — ✅ **DONE 2026-08-10** → `report/exec_summary.md`

~490 words + a 6-row results table. Leads with in-domain success (best
engineered model F1 0.876 at 4.2% FPR) then the three findings the report
refuses to bury: the char n-gram baseline beats all five engineered-feature
models on both corpora *and* the hybrid on false alarms; D2→D1 transfer puts all
six models below the 0.400 floor; the cascade is beaten by a single threshold.
Closes on the three contributions (the ≈10 + ≈10 gap decomposition, the 8.1
forensics, the +3.7 F1 LLM ceiling).

Two bullets in `NOAM_TODO.md`'s exec-summary brief were wrong and the written
summary contradicts them deliberately — it is **five** models plus the baseline,
not four, and the cascade is reported as a **negative** result rather than as
"tighter FPR than any single stage". Both now annotated in the TODO.

⚠️ At assembly, verify it fits one page at 1.5 spacing / 11pt. If it spills, cut
the "Problem" paragraph to two sentences — Ch1 covers T1059.004 properly.

## Packaging + cross-review (mine)

docx assembly (≤15 pages, 1.5 spacing, Arial/Calibri 11), Appendix A commands,
Appendix B hardware (**fix per correction 2**), refresh `ai_logs/claude_code_log.txt`
immediately before zipping, ZIP as `Group_[XX]_Final_Project.zip`.

Cross-review of Ben's 8 files is required before the freeze; assume numbers are
stale unless proven otherwise.

## Absorbed from Ben (my call, 2026-08-10)

Re-running his four stale artefacts, refreshing stale digits in his six files,
re-running his two Ch7 figures at full data, the 8.4 cascade fix, and deleting
the orphan `results/*_cnn_*.json`. Asked *him* for: Ch3 D1 sign-off, confirmation
his conclusions survive the new numbers, cross-review, the Ch7.1 pipeline
architecture diagram, and the Ch1 5-column reformat.

## Suggested order

1. Ben's artefact re-runs (unblocks his prose *and* my 8.1/8.3/8.4)
2. Ch1 (largest single unit at 15 pts, and §1.3 is mostly assembly)
3. Ch5 (10 pts, entire chapter, material already gathered)
4. Ch2 ShellCore (10 pts, prose over finished research)
5. Ch8.1 + figures → 8.3 → 8.4
6. Exec summary → docx → bonus if time survives
