# Noam's Remaining Work — LotL Shell Detection
**Due: Aug 14 (report freeze) / Aug 15 (ZIP submission)**

Ben's side was complete and audited against the full assignment PDF **as of the pre-redesign (38-feature) run**. The Ch3 feature redesign (43 features, `78d319f`/`cec996f`) invalidated part of it — see **"Handoff to Ben"** under Cross-Review below for exactly what. The items below are Noam's responsibility per `WORK_DIVISION.md`, plus **specific gaps flagged by the rubric audit** that need attention when assembling the final docx.

> **⚠️ Start here instead (2026-08-11):** `docs/DOCX_ASSEMBLY_BRIEF.md` is now the live plan. Nearly all chapter prose is written; what remains is the .docx build, and that brief carries the authoritative spec read straight from the assignment PDF (formatting rules, exact section list with point values, the corrected ZIP name `Group_X1_X2_Final_Project.zip`), the page budget, the four remaining gaps, and the day-by-day order. **This file is now partly stale** — the corrections are listed in its §7.

> **Companion document:** `docs/NOAM_WRITING_BRIEF.md` (2026-08-10) holds the *pre-gathered source material* for each remaining chapter — the four verified Ch1 mapping rows with live feature names, the §1.3 family skeleton with counts, the Ch2 ShellCore state, the Ch5 evidence, and the suggested writing order. This file stays the checklist; that one is the research already done.

> **Feature-set reality check (read once, applies everywhere below):** the final engineered set is **43 features**, listed in `src/features.py` `FEATURE_NAMES`, with the per-feature KEEP/KILL evidence in `report/ch3_feature_decisions.md`. Any document still saying "38 features", or naming `shell_bins` / `redirect_count` / `path_proc` / `char_count` / `token_count` / `char_entropy` / `b64_max_run` / `paren_count` / `quote_count` / `semicolon_count` / `token_len_*`, is stale.

---

## ⚠️ Rubric Audit Gaps — Fix When Assembling the Docx

### 1. Ch1 — Table column format
The assignment requires a **5-column** Telemetry & Feature Mapping table:
1. Adversarial Behavioral Characteristic
2. Required Telemetry Source
3. Specific Log Attributes / Raw Fields
4. Derived / Engineered Feature
5. Detailed Explanation

Ben's `report/ch1_threat_mapping.md` has 4 columns (adapted for shell commands). When you assemble the docx, **reformat Ben's 3 rows and your 4 rows into the exact 5-column schema above**. For shell commands: telemetry source = "shell command log (CSV `command` field)".

⚠️ **This is not only a column reshuffle** — this gap previously said "the content is all there, it just needs to be reorganized," which understated it. Ben's three rows cite **six feature names that no longer exist**. Rename map, verified against `FEATURE_NAMES`:

| In Ben's draft (dead) | Live name |
|---|---|
| `dev_tcp_present` | `has_dev_tcp` |
| `redirect_count` | `n_redirect_out` |
| `shell_bins` | `has_shell_bin` |
| `fetch_bins` | `has_fetch_bin` |
| `url_present` | `has_url` |
| `pipe_count` | `n_pipes` |

All six are straight renames — no killed features in his rows, so nothing has to come out of the argument (unlike his Ch3, item (a) below). Keep his closing "detectability tracks lexical distinguishability" framing and the IPv4-shortcut probe; both survive — but the probe's **0.546 was unreproducible**. Live values from `results/ch3_feature_audit.json` are ROC-AUC **0.535 (D1) / 0.523 (D2)** (`per_feature.has_ipv4.per_dataset.*.auc`); corrected in `ch1_threat_mapping.md` on 2026-08-10. **Check every feature name against `FEATURE_NAMES` before it goes in the docx.**

### 2. Ch8.1 — Missing RF and IF confusion matrix figures — ✅ CLOSED (2026-08-10)
All four models now have confusion matrices on both datasets. `report/figures/ch8_confusion_{random_forest,isolation_forest}_dataset{1,2}.png` were emitted by the post-redesign `analysis/ch8_error_analysis.py` run and are currently **untracked** — they need to land in the next commit or the rubric gap reopens at packaging time. Also recorded as Handoff item (d).

### 3. Ch7.1 — Pipeline diagram
The assignment requires a "visual software architecture diagram." There is an ASCII block diagram in `PIPELINE.md` (lines 10–35). When assembling the docx, **embed this diagram as a labeled figure (Figure X: Pipeline Architecture)** in Ch7.1. An ASCII diagram in a monospace block is acceptable for a technical report. Optionally draw a proper diagram with draw.io or similar.

### 4. Ch3 — Coverage of "every feature" (premise changed — evidence is now the CSVs, not the figure)
The rubric says "for every feature proposed, provide hard empirical evidence."

**The old plan no longer works.** It assumed the variance-by-label figure was the all-feature exhibit. The regenerated figures (`analysis/ch3_eda_figures.py`, `173e679`) plot only the **top-15 variance gap** per dataset, so *no figure shows all 43 features*. The figure is now an interpretive exhibit, not the coverage evidence.

**Cite these instead — they are the hard per-feature evidence, all 43 rows each:**
- **Dataset 2** — `report/ch3_d2_feature_stats.csv` (Mann-Whitney U p-value + rank-biserial effect + per-class means, all 43 features; committed `173e679`). Already cited in `report/ch3_d2_eda_findings.md`.
- **Dataset 1** — `report/ch3_feature_justification.csv` (regenerated by `analysis/ch3_eda.py`: `mean_malicious`, `mean_benign`, `var_all`, `rank_biserial`, `mwu_p` per feature) **plus** `report/ch3_d1_feature_stats.csv`. *Both are being regenerated on the 43-feature set right now by other agents* — treat them as the intended D1 evidence artifacts and verify they exist and are 43 rows before the docx freeze.
- **Both datasets, verdict-level** — `report/ch3_feature_decisions.md` carries per-feature effect / p / AUC / solo-F1 on both datasets for all 43 survivors *and* the 25 killed candidates. This is the strongest rubric answer available: it shows evidence for every feature proposed **and** for every feature rejected.

**How to use it in the docx:** keep the text interpreting the top features (as now), reference the top-15 variance figure as illustration, and ship the per-feature CSV as an appendix table with one line in Ch3 saying where it is. You still don't need a paragraph per feature — but the all-feature claim must point at a CSV, not at a figure.

### 5. ai_logs — File format (FIXED)
The assignment requires `.txt` or `.json` format named `ai_logs/claude_code_log.txt`. **This has been fixed** — `ai_logs/claude_code_log.txt` now exists with the full transcript. Include this file in the ZIP submission.

---

---

## Report Chapters to Write

### Title Page (required, no points)
Create the title page in the final .docx:
- Course: Using AI for Intrusion and Malware Detection
- Title: AI-Driven Detection of LotL Shell Attacks (MITRE ATT&CK T1059.004)
- Group Number: [insert]
- Team: Ben Volovelsky & Noam Delbari (with emails)
- Date: August 15, 2026

---

### Executive Summary — 5 pts — ✅ **DONE 2026-08-10** → `report/exec_summary.md`
Max 1 page. Cover:
- Threat: T1059.004 Living-off-the-Land Unix shell attacks, provenance-based labeling
- Two datasets: D1 (curated: HackTricks, GTFOBins, Atomic Red Team, etc.) and D2 (operational: Cowrie honeypot + bash history)
- Feature set: **43 engineered behavioral features** (`src/features.py`), selected from 68 candidates by the audit in `report/ch3_feature_decisions.md`
- ~~Four models~~ **Five models** — XGBoost, XGBoost-hybrid, 1D-CNN, Random Forest, Isolation Forest — **plus the char n-gram baseline**, which the summary has to include because it wins
- ~~Cascade: 3-stage, tighter FPR than any single stage~~ ⚠️ **This bullet was wrong and the summary says the opposite.** The cascade's FPR *is* tighter, but 8.4 shows a single decision threshold on stage 2 alone matches or beats the whole cascade on both precision and recall — so it is reported as a negative result and we recommend against deploying it
- Key finding: strong in-domain F1 but transfer collapses across corpora due to corpus-style shortcuts

**What the written summary actually leads with** (~490 words + a 6-row table):
in-domain works (best engineered model F1 0.876 at 4.2% FPR), then three
findings the report refuses to bury — (1) the untuned char n-gram baseline beats
all five engineered-feature models on both corpora *and* beats the hybrid on
false alarms (3.9% vs 4.2%), independently confirming ShellCore's
representational thesis; (2) D2→D1 transfer puts all six models between 0.14 and
0.36 against a floor of 0.400, so they are learning corpus style; (3) the
cascade is beaten by a `>=` sign. Closes on the three contributions: the 20-point
gap decomposed into ≈10 representation + ≈10 corpus-and-protocol, the 8.1 error
forensics, and the **+3.7 F1** ceiling quantified for the LLM layer.

⚠️ **At assembly, check this fits one page** at 1.5 spacing / 11pt. If it
spills, cut the "Problem" paragraph to two sentences — the threat model is
covered properly in Ch1 and the summary does not need to re-teach T1059.004.

> ⚠️ **Do not paste the old F1 numbers into this summary.** Every figure previously listed here (XGBoost-hybrid 0.871/0.846, CNN 0.853/0.841, RF 0.761/0.696, IF 0.264/0.082, cascade 0.873/0.838, transfer 0.534/0.184) came from the **pre-redesign 38-feature run**. Take the final numbers from the regenerated `results/summary.json` after `python main.py all` completes. Directional claims above are safe; the digits are not.

---

### Chapter 1 — Threat Characterization (15 pts, partial)
Ben has written **3 rows** of the mapping table (`report/ch1_threat_mapping.md`):
T1059.004 (reverse shells), T1105 (download cradles), T1033 (whoami/id discovery).

**You need to add:**
1. **Section 1.1 — Deep-Dive Threat Analysis**: from your preliminary proposal §2–3. Define T1059.004 and sub-techniques, explain how LotL attacks execute at the OS layer, and why shell command logs are the right telemetry.
2. **Your 4 mapping-table rows**: Pick 4 additional sub-techniques (e.g., T1027 obfuscated commands/base64, T1548.003 sudo abuse, T1070.003 shell history deletion, T1083 file/dir discovery). For each row use the 5-column assignment format:
   - Adversarial Behavioral Characteristic
   - Required Telemetry Source (shell command log / Cowrie JSONL)
   - Specific Log Attributes / Raw Fields (the `command` field)
   - Derived / Engineered Feature — use real names from `src/features.py` `FEATURE_NAMES`, e.g. `has_base64_blob` / `has_hex_escape` (T1027), `head_is_privesc` (T1548.003), `has_enum_bin` (T1083)
   - Detailed Explanation of the relationship

   ⚠️ Two traps here: the old draft names `base64_present` / `sudo_present` don't exist, and the sudo-family feature that *survived* the audit is the **positional** `head_is_privesc` — `has_privesc_bin` was killed as class-neutral (see `report/ch3_feature_decisions.md`). Also, **T1070.003 (shell history deletion) has no dedicated feature in the 43-set** — either pick a sub-technique that does map to a real feature, or say plainly in the Explanation column that this behavior is only covered indirectly. Don't invent a feature name to fill the cell.
3. **Section 1.3 — Theoretical Feature Rationale**: For each of the 43 features in `src/features.py` `FEATURE_NAMES`, explain the semantic security relationship. (Ben's ch1 covers detectability; you cover the feature→behavior mapping.) The family groupings in `report/ch3_feature_decisions.md` (shape/size, structure/chaining, network/delivery, binary families, head/args, exec micro-structure, paths/filesystem, obfuscation) give you the section skeleton for free.

---

### Chapter 2 — Literature Review (10 pts) ✅ ShellCore half DONE (2026-08-10)
Ben has written the **Trizna/SLP + QuasarNix** half (`report/ch2_literature_review.md`).

Noam's half is written as three files:
- `report/ch2_1_shellcore_extraction.md` — the 6-element extraction matrix as prose, the corpus accounting (Tables 1–3), the headline results, and the authors' own malware-only ablation + §5.5 concessions.
- `report/ch2_2_adopt_modify_reject.md` — six verdicts (adopt char-level insight + two-representation design; modify term BoW → fixed threat-mapped lists; modify n-grams → bounded/in-fold; reject PCA; reject their evaluation protocol), each grounded in either their Table 4 ablation or our own audit.
- `report/ch2_3_comparative_contribution_noam.md` — the ShellCore vertex of the comparative essay for Ben to fold in, plus the head-to-head arithmetic that **Ch8.3 should cite rather than re-derive**.

**Whole paper re-verified first-hand 2026-08-10** (Tables 1–5, §§4.1–4.5, §5.5) — every number in the matrix file checked against the PDF, including the last outstanding one ("1,273 patterns from 18 samples", §4.1). Classifiers LR/RF/DNN confirmed (5 hidden layers §4.3.2, K=10 §4.3.3); char-level RF 99.78/99.78/0.27/0.19 command and 99.91/99.91 file; malware-only ablation drops term-level RF to 84.95 while char-level holds at 98.19.

**Two findings that are new and are the strongest material in the chapter:**
1. **Their printed F1 is not the malicious-class F1 at their own stated prevalence.** Table 2 implies 9.83%; Table 5 says the command-level set is 190,897 rows (9× discrepancy, balance never stated). Solving the six reported (F1, FNR, FPR) triples excludes that reading (mean residual 0.716 pts) and admits only ≈balanced binary F1 (0.012) or support-weighted F1 at 9.83% (0.024). So the floor is 0.667, not 0.179 — or the comparable number reconstructs to 99.00–99.30. Derivation lives in `ch2_3_*`.
2. **§5.5 concedes our own critique #1** in the authors' words ("the benign dataset may not be considered as a representative ground-truth benign dataset with an absolute confidence"), and the malware-only column is their mitigation — where file-level term collapses 99.08→67.48 (RF) / 97.16→66.67 (DNN) while char-level loses 0.1 pts. Also new: their dominant benign source has **std 4.88 chars across 1.6M rows**.

~~Stale claim on line 24 (entropies)~~ — already fixed; the prose states the correct reason (`char_entropy`/`token_entropy` killed for cluster redundancy against `len_chars`/`len_tokens`, and `char_entropy` sign-inverts d +0.29 → −0.09 across corpora).

---

### Chapter 3 — EDA (15 pts, partial)
Ben has written Dataset 1 EDA (`report/ch3_eda_findings.md` — **stale, see Handoff to Ben**).

#### ✅ DONE — Dataset 2 EDA write-up (`cee7285`, corrections `088446e`)
Written on the final 43-feature set, 4 paragraphs + a per-feature effect table, matching the depth of Ben's D1 analysis. Artifacts:
- `report/ch3_d2_eda_findings.md` — the prose (length distribution, per-feature discrimination, correlation/leakage, three modeling takeaways)
- `report/ch3_d2_feature_stats.csv` — all 43 features, Mann-Whitney U + rank-biserial + per-class means
- `analysis/ch3_eda_figures.py` — the regeneration script

#### ✅ DONE — Ch3 figures regenerated on the 43-feature set (`173e679`)
6 per-dataset figures rebuilt (the old ones were 38-era): `ch3_length_hist_dataset{1,2}.png`, `ch3_variance_by_label_dataset{1,2}.png`, `ch3_corr_heatmap_dataset{1,2}.png`. Note the real filename is `ch3_length_hist_*`, **not** `ch3_length_dist_*` as this TODO previously said. Reminder from Rubric Gap 4: the variance-by-label figures show only the **top-15** variance gap, not all 43.

**Still open on Ch3:**
- Joint review of the D2 draft with Noam before it goes in the docx (it was committed as "draft for joint review").
- Fold the D1 half back in once Ben's `ch3_eda_findings.md` rewrite lands (Handoff item (a)) — the two halves must use the same feature vocabulary and the same 43-feature framing.

---

### Chapter 5 — Multi-Dataset Harmonization (10 pts) — FULL CHAPTER, YOUR RESPONSIBILITY

This chapter is entirely yours. Write:

**5.1 Unified Feature Schema Definition**
The unified feature is the raw shell command string (`command` column), present in both datasets. From it, `src/features.py` extracts **43 identical behavioral features** (`FEATURE_NAMES`) regardless of dataset. Map this back to your Step 1–4 findings. Reference the features that appear in both datasets' top-20 importance charts, and cite the selection protocol in `report/ch3_feature_decisions.md` (68 candidates → 43 survivors under one gate applied identically to both datasets — that *is* the harmonization argument).

**5.2 Cross-Dataset Distribution Shift Analysis**
Pick 5–8 key features (e.g., `has_shell_bin`, `has_lotl_bin`, `n_pipes`, `has_url`, `len_chars`, `digit_ratio`). For each, show how its mean/variance/distribution differs between D1 and D2 using the figures in `report/figures/` and the per-feature CSVs from Rubric Gap 4. Explain WHY: D1 is curated/stylized text; D2 is live attacker input.

The strongest ready-made material for this section is now in `report/ch3_d2_eda_findings.md` — it already documents the **sign inversions** (`len_chars` r +0.247 D1 → −0.171 D2; `n_quotes` +0.081 → −0.112; `n_flags` +0.051 → −0.125) and the LotL anti-signal (`head_is_lotl` benign-leaning on both corpora). Reuse those pairs; they are the feature-level mechanism behind the transfer collapse.

⚠️ The old `shell_bins` D1→D2 gain-inversion note (D1 gain 0.194; D2 `lotl_bins` 0.177 / `shell_bins` 0.052) used **dead feature names and pre-redesign Ch4 numbers** — do not reuse those digits. The equivalent live evidence: `has_shell_bin` OR 32.75 on D1 vs 5.99 on D2 (`report/ch3_feature_decisions.md`), and re-read the gains from the regenerated `report/ch4_feature_ranking.csv` once Ch4 has been re-run.

**5.3 Data Scaling & Scaling Remedies**
The pipeline uses `StandardScaler` fitted only on the training fold (inside the sklearn Pipeline) to prevent leakage. Explain why Z-score normalization is appropriate here (the features are counts/ratios with different scales).

⚠️ **`build_hybrid_pipeline()` does not exist** — this TODO named it wrongly. Verified live names: `EngineeredFeatures` (`src/preprocessing.py:34`) and `build_hybrid_features()` (`src/preprocessing.py:75`); the hybrid *model* builder is `build_xgboost_hybrid()` (`src/models.py:86`). `StandardScaler` is instantiated at `src/models.py:81`, `:152`, `:179`, always inside `Pipeline([...])` so CV splits can't leak. Cite those names.

Don't just assert that scaling matters — Ch6 §6.4 already **measured** it: removing the scaler moves RF F1 by 0.0017 (D1) / 0.0003 (D2) and leaves Isolation Forest scores bit-identical, because tree splits depend only on rank order. So the honest §5.3 framing is: the scaler is a *contract* that keeps one pipeline shape across all models — load-bearing for distance/gradient-based learners, a provable no-op for the two tree models. That is a stronger answer than the generic leakage paragraph.

---

### Chapter 6 — Model Selection (5 pts) — ✅ **DONE**
Ben has written justification for XGBoost + CNN (`report/ch6_model_justification.md`).
Noam's half is `report/ch6_rf_if_justification.md` (§6.4–6.6), matching Ben's
inline `*Cite:*` convention. All four citations verified against authoritative
records (dblp BibTeX for Breiman / Liu et al.; the ShellCore RF claim checked
first-hand against Table 4 of the paper PDF, not just our Ch2 matrix).

**Delivered:**
- **Random Forest justification** ✅ — no-extrapolation robustness to the heavy tails, Gini importance independently reproducing the Ch3 rank-biserial top-2, importance mass spread across all 43 features (anti-shortcut evidence), and "no scaling needed" *measured* rather than asserted. Cites Breiman (2001) + ShellCore (IEEE IoT J. 9(4), 2022) for RF on shell commands specifically.
- **Isolation Forest justification** ✅ — cites Liu, Ting & Zhou (ICDM 2008 / TKDD 2012). Weakness reported at face value and decomposed into threshold placement vs genuine ranking limits. Quotes the current 0.249 (D1) / 0.143 (D2), **not** the old 0.264 / 0.082 pair.
- **Explicit hyperparameters** ✅ — production values from `src/models.py`, confirmed by the Ch7 sweep:
  - RF: `n_estimators=400`, `max_depth=24`, `class_weight="balanced_subsample"`, `min_samples_leaf=1`, `max_features="sqrt"`
  - IF: `n_estimators=300`, `max_samples=0.8`, `contamination=0.25`, `max_features=1.0`
  - Cross-reference `report/ch7_rf_if_sensitivity_findings.md` for the "chosen setting + rationale" tables — Ch6 states the choice, Ch7 proves it.

**New result produced while citing Liu et al. (worth a sentence in Ch7 if there's room):**
the paper recommends a small fixed sub-sample (ψ=256, t=100) to suppress swamping
and masking. We swept `max_samples` to check whether production's 0.8 (ψ≈7,319 D1 /
≈4,596 D2) was a mistake. It is not — **ψ=256 is the worst cell on both datasets**
(ROC-AUC 0.7983 D1 / 0.6631 D2 vs production 0.8120 / 0.6768), and the whole axis
spans only 0.017 AUC. Best cells: ψ=1024 → 0.8149 (D1), ψ=all → 0.6782 (D2). The
published default does not transfer here, most likely because swamping/masking are
*contamination* effects and this detector is fitted on benign rows only, so a small
ψ just under-covers a multi-modal benign distribution. The probe reproduces
`summary.json`'s production AUCs exactly, which is a useful independent check on
both. §6.6 states this honestly rather than citing the paper's rationale for a
setting that contradicts it.

---

### Chapter 7 — Pipeline (10 pts, partial)
Ben has written sensitivity analysis for XGBoost and CNN (`report/ch7_sensitivity_findings.md` — **numbers stale, see Handoff to Ben**).

#### ✅ DONE — RF sensitivity analysis (`d81ff5c`, corrections `088446e`)
Full 12-config `n_estimators` (50/100/200/500) × `max_depth` (None/10/20) grid on **full training data** (not a 5k subsample), both datasets, F1 + FPR per cell. Result: `max_depth=20` dominates on both F1 and FPR on both datasets; `n_estimators` plateaus by ~200; the whole grid spans only 0.780–0.801 F1 (D1) / 0.731–0.758 (D2) — the 43-feature representation is the ceiling, not tree capacity. Production `(400, 24)` is validated by the plateau cells.

#### ✅ DONE — IF sensitivity analysis (`d81ff5c`, corrections `088446e`)
`contamination` swept 0.05/0.10/0.20/0.30 on both datasets, each at its own calibrated threshold plus the shipped fixed-0.5 wrapper row. Result: `contamination` is a pure false-alarm-budget dial (FPR ≈ c; ROC-AUC identical to 4 dp across all settings — asserted in the script), F1 peaks at only 0.641 (D1) / 0.462 (D2), and even c=0.30 retains just 73%/56% of attacks — which is exactly why the cascade ignores `contamination` and calibrates on `stage1_retain_recall=0.99` (`src/ensemble.py`). The "operating point set for recall, not F1" argument is written up in full.

**Artifacts for both:**
- `analysis/ch7_rf_if_sweeps.py` (reproduce with `python analysis/ch7_rf_if_sweeps.py`)
- `results/ch7_rf_if_sensitivity.json`
- `report/ch7_rf_if_sensitivity_findings.md` (headline answers, both grids, interpretation, chosen-setting tables, cross-model synthesis)
- 4 figures: `report/figures/ch7_sensitivity_random_forest_dataset{1,2}.png`, `report/figures/ch7_sensitivity_isolation_forest_dataset{1,2}.png`

**Still open on Ch7:** the pipeline architecture figure (Rubric Gap 3), and merging this file with Ben's XGBoost/CNN half once his numbers are refreshed (Handoff item (c)).

---

### Chapter 8 — Error Analysis & Ensemble (20 pts, partial)
Ben has written:
- 8.1 for XGBoost + CNN → `report/ch8_findings.md`
- 8.2 cross-dataset table → same file
- 8.3 vs Trizna/TOPS → `report/ch8_3_tops_comparison.md`
- 8.4 cascade results (stub) → `report/ch8_4_cascade_findings.md`

**You need:**

**8.1 for RF and IF** — ✅ **DONE (2026-08-10)** → `report/ch8_1_rf_if_forensics.md`

Backed by a new script, `analysis/ch8_1_rf_if_forensics.py` → `results/ch8_1_rf_if_forensics.json`. It refits RF, IF and XGBoost-hybrid per dataset and keeps **every** test-row prediction, so the overlap figures are exact rather than sampled from the 40-row caps in `ch8_failures.json`. Four results worth knowing:

1. **The FN sets are nested, the FP sets are not.** On D1 RF's 207 false negatives are a *strict subset* of IF's 651 — IF catches **zero** attacks RF misses. On D2 it catches 8. But their false positives are near-disjoint (Jaccard 0.056 / 0.011). The complementarity the cascade exploits is disagreement about **benign** traffic, not about attacks. On D1 the two models even rank the benign sources near-identically and *still* share only 5 of 90 flagged rows — same sources, different rows, which is invisible to the per-source tables in the generated file.
2. **RF's misses are measurably benign-shaped.** Rescaling so benign = 0 and caught-attack = 1, the 207 misses score **−0.07 to +0.16** on the eight features that carry the most signal. `has_shell_bin` is 0.0 across all 207. None of the 207 (or D2's 145) appears in the benign training rows, so it is genuine semantic ambiguity, not duplicate confusion.
3. **The length signature inverts between corpora** in lockstep with Ch5.2's sign flip (δ +0.247 → −0.171): D1 misses are the *short* ones (38.6 ≈ benign 37.3), D2 misses the *long* ones (52.7 > caught 46.5). Same phenomenon, two directions.
4. **Cascade premise measured:** the hybrid recovers 123/207 (59.4%) on D1 and 83/145 (57.2%) on D2, evenly across sources. Residual "missed by both" = 84 / 62 ≈ 11–13% of test attacks, and these are bare invocations (`xz`, `bconsole`, `nano u.txt`) — Ch1.1's failure mode 1, now counted.

⚠️ **Correction this made to an earlier claim:** RF is the lowest-FPR supervised model on **D1 only** (0.034). On D2 at 0.052 both the hybrid (0.049) and the TF-IDF baseline (0.048) run cleaner. The old wording ("lowest-false-alarm supervised model in the project") was wrong and has been fixed in `analysis/ch8_error_analysis.py` so it stops regenerating. Related: on D1 the hybrid buys recall *with* false alarms (95 FP vs RF's 77), but on D2 it runs 71 vs 74 and simply dominates — so 8.4 has something to justify on the curated corpus and nothing to justify on the operational one.

✅ **Rubric Gap 2 / Handoff (d) CLOSED** — `report/figures/ch8_confusion_{random_forest,isolation_forest}_dataset{1,2}.png` all exist (currently untracked; they land with the next commit).

📌 The generated `report/ch8_1_error_forensics_noam.md` is **evidence, not prose** — its trailer now points at the write-up. Don't put prose in it; `analysis/ch8_error_analysis.py` overwrites it.
- Context already written: `report/ch7_rf_if_sensitivity_findings.md` explains *why* IF's shipped operating point sits in an extreme-precision corner (recall ~0.15 / FPR ~0.008 on D1); the write-up cites it rather than re-deriving it.

**8.3 vs ShellCore** — ✅ **DONE (2026-08-10)** → `report/ch8_3_shellcore_comparison.md` (distinct from Ben's `ch8_3_tops_comparison.md`, which is the Trizna/QuasarNix vertex for his models).

Cites the `ch2_3` metric reconstruction rather than re-deriving it. Three things in it are new:

1. **The gap is decomposed, not asserted.** Our `baseline` is `char_wb` 3–5-gram TF-IDF + LR — the same representation family as ShellCore's char-level LR — so the walk from our RF to theirs is two one-variable steps: swap engineered features for char n-grams on *our own corpus and protocol* (0.7963 → 0.8975, **+10.12**), then swap the corpus and protocol (0.8975 → 0.9978, **+10.03**). Sums to +20.15, the whole gap, in two steps the same size to within a tenth of a point. So the split is almost exactly **half representation / half corpus-and-protocol** — "just their easier dataset" is about half the truth, not all of it. Robust to the metric question (the reconstructed 0.9930 moves step 2 to +9.55, split 51/49). ⚠️ **Revised 2026-08-10 from +8.45 / +11.70 (40/60)** — the old figures pivoted on the orphan baseline 0.8808; see the orphan-files entry below.
2. **ShellCore's actual thesis is independently confirmed.** Their claim is that the *character* representation carries the signal (their malware-only ablation: term-level file RF collapses 99.08→67.48, char-level holds 99.91→99.79). Our char n-gram baseline beats **all five** engineered-feature models on **both** datasets. 43 hand-designed features do not beat 44,781 untuned character n-grams. So the split verdict is: reject their protocol, confirm their representation finding. The 43 features earn their place on interpretability/threat-traceability (Ch1.3), not raw discriminative power — better to say that plainly than blur it.
3. **The Isolation Forest is below the do-nothing floor** — F1 0.2492 / 0.1431 against a floor of 0.400. Stated outright. The qualification is that fixed-0.5 F1 is the worst way to score it (Ch7: ranking is sound, AUC 0.812/0.677) and 8.4 consumes its score, not its decision. ShellCore has *no* unsupervised comparator and structurally cannot — its malicious class is defined by 1,273 regexes over disassembled binaries, so it presupposes labels. IF is our only cold-start measurement.

⚠️ **Project-level finding surfaced while writing this — belongs in the exec summary too.** On D2→D1 transfer **all six shipped models score below the do-nothing floor of 0.400**: baseline 0.3360, `cnn1d` 0.3587, `xgboost_hybrid` 0.2756, isolation_forest 0.2407, `xgboost` 0.2349, `random_forest` 0.1432. (The retired `cnn` key scores 0.3306 and is also below the floor, but it is an orphan result file — count six, not seven, so the claim doesn't depend on a model we don't ship. 8.3's pull-quote was corrected from "seven" to "six" on 2026-08-10 for this reason.) On a corpus none was fitted to, flagging every command beats all of them on F1. Stated outright in 8.3 rather than tucked into limitations — don't soften it at assembly.

### 8.4 Hybrid behavioural cascade — ✅ **DONE 2026-08-10** → `report/ch8_4_cascade_analysis.md`

Prose-only: the dead `stage1_clear_below=0.15` was already dropped and `report/ch8_4_cascade_findings.md` already regenerated (see item (e) below), so no code change or re-run was needed. New evidence script: `analysis/ch8_4_cascade_forensics.py` → `results/ch8_4_cascade_forensics.json`. It fits IF + hybrid **once** per dataset and derives all five routing variants from the cached stage-1 scores and stage-2 probabilities, which is exact (the routing rule is deterministic given those arrays) and cheap.

**The chapter is a negative result, deliberately.** Four findings:

1. **Every stage makes the system worse, on both corpora.** D1 F1: hybrid alone 0.8761 > stage1+2 0.8737 > stage2+3 0.8716 > **full cascade 0.8685**. D2: 0.8482 > 0.8463 > 0.8415 > **0.8396**. The full three-stage cascade is the weakest of the four configurations of its own components.
2. **The precision gain is bought at worse than one-for-one.** D1 −31 false alarms for −34 true detections (1.10 missed attacks per alarm avoided); D2 −22 for −23 (1.05). Attributed exactly per stage: stage 1 = −1 FP/−4 TP (D1), −2/−3 (D2); stage 3 = −30/−30 (D1), −20/−20 (D2).
3. **Stage 3 never fires, so it is a threshold shift in disguise.** The offline stub labelled malicious 0 of 146 routed D1 commands and 2 of 101 on D2. Structural, not luck: 39 D1 test commands match one of its six motifs and **all 39 are attacks**, which is exactly why stage 2 is already confident about them and none land in the [0.35, 0.65] band. Its rule set is anti-correlated with the router by construction.
4. **The dominance test — the headline.** Sweeping stage 2's threshold 0.05→0.95: **3 single thresholds (0.65/0.66/0.67) match or beat the full cascade on both precision and recall on D1**; on D2 `p >= 0.66` reproduces the cascade's confusion matrix to four decimals on every headline metric. Best-F1 threshold (0.53 / 0.52) beats the cascade by 0.98 / 0.89 points with no second model and no inference calls.

**The constructive half — this is the bonus chapter's target, don't lose it.** The *router* works: band attack prevalence 0.411 / 0.386 vs 0.250 overall, and the hybrid's accuracy inside the band is **58.9% / 63.4%** against **95.6% / 94.1%** outside it. An **oracle** arbitrator on that band gives F1 **0.9132 / 0.8849** — **+3.7 points over the best single model** on 4.8% / 5.3% of traffic. So the bonus LLM layer should be scored against +3.7, not against zero, and its bar to be worth any latency at all is 58.9% (D1) / 63.4% (D2) accuracy on those specific rows — precisely what stage 2 already achieves there, and precisely what the stub ties (its 60 and 42 overrides split 30/30 and 21/21 helped/hurt).

Recommendations stated in the chapter: don't ship the cascade; drop stage 1 rather than re-tune it (Ch8.1's nested-FN result is the structural reason); keep the routing rule and replace the arbitrator. Generated-file trailer now points at the write-up and carries the corrections, so `ch8_4_cascade_findings.md` can't regenerate into contradicting the chapter.

⚠️ Also measured, worth one line at assembly: stage 1's recall calibration under-delivers out of sample — 98.82% / 98.54% of test attacks retained against the 0.99 target, i.e. 9 and 7 real attacks silently discarded.

---

## Bonus Chapter — LLM Triage (+10 pts)

This is optional but worth 10 pts. The code scaffolding is already in place.

### What exists already:
- `src/llm_triage.py`: `build_prompt()`, `parse_verdict()`, `select_edge_cases()`, `stub_arbitrator`, `huggingface_arbitrator`
- `src/ensemble.py`: `CascadeDetector` wired to use the arbitrator
- `analysis/bonus_b3_llm_eval.py`: evaluation script (Ben wrote this)
- `report/bonus_b3_findings.md`: has stub results (NOT graded — replace with real)
- `report/ch8_4_cascade_findings.md`: stub cascade results — **generated, do not hand-edit**; re-run `analysis/ch8_4_cascade.py` with the live arbitrator instead. The stage-level audit and the prose are in `report/ch8_4_cascade_analysis.md` + `analysis/ch8_4_cascade_forensics.py`; both quote stub figures that a real-LLM run will change, so revisit them together.

### What you need to do:

**Step 1: Get HF_TOKEN**
Create a free account at huggingface.co and generate a personal access token. Export it:
```bash
export HF_TOKEN="hf_..."
```
Do NOT commit the token to the repo.

**Step 2: Run the real evaluation**
```bash
cd lotl-shell-detection-new
python analysis/bonus_b3_llm_eval.py --hf
```
This routes edge cases (model disagreements / uncertainty band) to Llama 3.1-8B via HF Inference and saves results to `results/bonus_b3_edge_eval.json`.

**Step 3: Update the report files** with real numbers (replace the stub table in `bonus_b3_findings.md` and `ch8_4_cascade_findings.md`).

**Step 4: Write B.1, B.2, B.4:**
- **B.1**: Model = `meta-llama/Llama-3.1-8B-Instruct` via `huggingface_hub.InferenceClient`. Token from env var `HF_TOKEN`. Latency ~1–3s per call. Document exact call count from the evaluation run.
- **B.2**: The prompt template is in `src/llm_triage.py`'s `build_prompt()`. Copy it into the report and explain the chain-of-thought structure.
- **B.4**: Report wall-clock latency per call, total calls, and conclude honestly whether this is production-viable. ⚠️ **The old estimate here (36–42% edge fraction, ~800–1100 calls, 15–55 min) was `select_edge_cases`, not the cascade band — measured 2026-08-10, the cascade's [0.35, 0.65] band is only 146 calls on D1 and 101 on D2 (4.8% / 5.3% of traffic), i.e. ~4–12 minutes for both test sets.** That changes the B.4 verdict from "not viable" to "viable at this band width", so don't paste the old sentence. Two numbers from `report/ch8_4_cascade_analysis.md` frame the whole bonus: the oracle ceiling on that band is **+3.7 F1 over the best single model** (0.9132 / 0.8849 vs 0.8761 / 0.8482), and the arbitrator must clear **58.9% / 63.4%** accuracy on those rows — stage 2's own accuracy there — or routing to it is a pure latency cost. The offline stub scores exactly that and is therefore worth nothing; that comparison is B.3's control.

---

## Packaging (your responsibility)

1. **Assemble the .docx**: Merge all markdown chapters (title page + exec summary + Ch1–Ch8 + Bonus + Appendices) into one Word document. Max **15 pages** at 1.5 spacing, Arial/Calibri 11pt.

2. **Appendix A — Code Execution**:
   ```
   pip install -r requirements.txt
   python main.py all                  # run all models on both datasets
   python main.py holdout xgboost_hybrid --dataset 1
   python analysis/bonus_b3_llm_eval.py --hf   # requires HF_TOKEN
   ```

3. **Appendix B — Hardware/Software**:
   - Python 3.11, scikit-learn 1.5, XGBoost 2.0, PyTorch 2.3

   ⚠️ **The single-machine description here was wrong.** It claimed macOS + Apple M-series throughout — that is **Ben's** environment. Every result Noam produced (Ch3 EDA + regenerated figures, Ch7 RF/IF sweeps, Ch6 §6.6 sub-sample probe, all 20 regenerated `results/*.json`) ran on **Windows 11, CPU only**. The appendix must name **both** environments or it misdescribes how the numbers were produced:
   - *Environment A (Ben)* — macOS, Apple M-series; CNN trained on the GPU via `torch.device("mps")`
   - *Environment B (Noam)* — Windows 11, CPU; scikit-learn / XGBoost workloads
   - State which results came from which, and note that the tree models are deterministic under a fixed seed so the split does not affect reproducibility of the RF/IF numbers.

4. **AI logs naming** — ✅ already in place (see Rubric Gap 5): `ai_logs/claude_code_log.txt` exists alongside the `.md`. Just make sure the `.txt` is refreshed with the latest sessions before zipping, and that the `.md` is kept too.

5. **ZIP it**:
   ```
   Group_X1_X2_Final_Project.zip        # X1, X2 = the two student IDs (assignment PDF p.12)
   ├── code/              (this repo)
   ├── report.docx
   └── ai_logs/
       └── claude_code_log.txt
   ```

---

## Cross-Review (required before Aug 14 freeze)

Per WORK_DIVISION.md: **read Ben's chapters before Aug 14 and flag any issues.**
Ben's files to review:
- `report/ch1_threat_mapping.md` — 3 rows
- `report/ch2_literature_review.md` — Trizna section (note: sourcing note at top about TOPS paper — if instructor assigned a specific DOI, ask them)
- `report/ch3_eda_findings.md`
- `report/ch4_ranking_findings.md`
- `report/ch6_model_justification.md`
- `report/ch7_sensitivity_findings.md`
- `report/ch8_findings.md`

### 🔴 Reviewed 2026-08-10 — `report/ch8_3_tops_comparison.md` (Ben's)

**His argument survives; his numbers don't.** Every figure predates the 43-feature retrain. Ben's conclusion that the CNN is the most transfer-robust model still holds on live numbers, but the margin shrinks a lot (D2→D1: 0.3587 vs 0.2756, not 0.331 vs 0.184), so the prose around it needs softening as well as renumbering.

| claim in his file | live value |
|---|---|
| `random_forest` 0.761 / 0.696 | **0.7963 / 0.7531** |
| `xgboost_hybrid` 0.871 / 0.846 | 0.8761 / 0.8482 |
| hybrid D2→D1 **0.184** | **0.2756** |
| hybrid D1→D2 0.534 | 0.5319 |
| hybrid D2→D1 AUC 0.643 | 0.6858 |
| hybrid D1→D2 FPR 0.283 | 0.2758 |
| hybrid in-domain "97 FN / 100 FP", FPR 0.044 | 94 FN / 95 FP, FPR 0.0415 |
| RF transfer 0.509 / 0.175 | 0.5148 / 0.1432 |
| `cnn` 0.853 / 0.841, 0.529 / 0.331, "70 FN / 173 FP (F1 0.851)", recall 0.908 | **`cnn` is the retired model.** `cnn1d`: 0.8603 / 0.8384, 0.5405 / 0.3587, 91 FN / 127 FP, recall 0.8806 |
| "a ~0.69 F1 drop" | ~0.60 |

Also: his per-source FP percentages for the hybrid (`linlm` 17%, `bash6k` 13%, `nl2bash` 10%) are pre-redesign and need re-reading off the regenerated `ch8_confusion.json`. Falls under the "Noam absorbs every number-refresh" scope decision below — but the *softening* of the CNN-transfer claim is a wording change on his prose, so flag it to him rather than silently editing.

### 🔴 Reviewed earlier — `report/ch2_literature_review.md` (Ben's)
Line 9 lists "entropies" among our features (both were killed); CNN F1 "0.853 / 0.841" is the retired `cnn`, not `cnn1d` (0.8603 / 0.8384); XGB-hybrid "0.871 / 0.978" and "0.846 / 0.965" → live 0.8761 / 0.9794 and 0.8482 / 0.9680; TPR@FPR=0.1% "0.575 / 0.507" → live 0.5669 / 0.5261. ⚠️ **Corrected 2026-08-11:** his TF-IDF+LR baseline figures (0.881 / 0.980, 0.863 / 0.964) are **not** correct — that line predates the orphan-baseline discovery. The reproducible figures from `docs/baseline_metrics.json` are **0.8975 / 0.9833** (D1) and **0.8824** (D2). Line 19 of that file, the "Baseline configuration note" paragraph, is therefore obsolete outright: it argues about a residual ~0.02 gap to references that turn out to be the live numbers. Delete the paragraph rather than patching it.
- `report/ch8_3_tops_comparison.md`

When reviewing, assume **numbers are stale unless proven otherwise** — the four items below are the ones already found.

### 🔴 Handoff to Ben — cross-cutting breakage found by the verification pass (2026-08-09)

Recorded here so none of it is lost between sessions. Items **(a)–(c)** are fallout from the 38 → 43 feature redesign (`78d319f` / `cec996f`) and land on Ben's chapters, not Noam's; **(d)** is a pre-existing figure gap that is Noam's to close, listed here so Ben doesn't assume the figure set is complete.

> **Scope decision (2026-08-10): Noam absorbs every re-run and number-refresh below.** The redesign was Noam's change, so the blast radius is his to clean up — the four stale Ch8 artefacts, the stale digits in Ben's six prose files, the two Ch7 figures at full data, the 8.4 cascade fix, and the orphan `_cnn_` deletions. What is still genuinely Ben's is **net-new writing**: the Ch3 D1 sign-off in (a), the Ch7.1 architecture diagram (Rubric Gap 3), the Ch1 5-column reformat of his own 3 rows (Rubric Gap 1), and the final cross-review pass. Sent as `scratchpad/handoff_to_ben.md`.

**(a) `report/ch3_eda_findings.md` is written on the dead feature set.**
Ben's hand-written Dataset-1 Ch3 chapter names **eleven** features that no longer exist in `src/features.py`: `char_count`, `token_count`, `token_len_mean`, `token_len_max`, `char_entropy`, `semicolon_count`, `paren_count`, `quote_count`, `redirect_count`, `shell_bins`, `b64_max_run`. Some are renames (`char_count` → `len_chars`, `token_count` → `len_tokens`, `token_len_mean` → `mean_token_len`, `token_len_max` → `max_token_len`, `quote_count` → `n_quotes`, `redirect_count` → `n_redirect_out`, `shell_bins` → `has_shell_bin`, `b64_max_run` → `b64_run_len`); three were **killed outright** (`char_entropy`, `semicolon_count`, `paren_count` — see the killed-candidates table in `report/ch3_feature_decisions.md`). Killed features must be *removed* from the prose, not renamed. The parent session is repairing the numbers and names in place. **Ben must review that rewrite** — it is his prose and his interpretation, and the file is explicitly marked as never machine-overwritten (`analysis/ch3_eda.py` docstring).

**(b) Every downstream chapter number is pre-redesign and is being regenerated.**
`results/summary.json` and all model metrics were computed on the 38-feature set; `python main.py all` is regenerating them on the 43-feature set. **Ben's chapter prose that quotes the old figures must be refreshed against the new `results/summary.json`**, specifically (non-exhaustive): the **Isolation Forest 0.264 / 0.082** standalone headline and the **XGBoost-hybrid 0.871 / 0.846** results table, plus the transfer table (0.534 / 0.184), the cascade figures, and anything in `ch2` / `ch6` / `ch8` / `ch8_3` / `ch8_4` / `bonus_b3` that cites them. Do not hand-patch digits — re-read them from the regenerated file.

**(c) Two Ch7 figures are still on the old feature set and the old protocol.**
`report/figures/ch7_sensitivity_xgboost.png` and `report/figures/ch7_sensitivity_cnn.png` were produced on the 38-feature set from a **5,000-row subsample**. Re-run needed before the docx — `ch7_sensitivity_findings.md` prose depends on them. (For contrast, the RF/IF sweeps above ran the full grid on full training data, so the two halves of Ch7 currently disagree on protocol; say so explicitly in the merged chapter, or re-run the XGB/CNN half at full data.) Owner now Noam per the absorption note above.

⚠️ **Don't reach for the `_dataset1` / `_dataset2` suffixed variants as a substitute — they are older, not newer.** Confirmed from git: the suffixed pair was committed in `eeeaf25` (2026-08-07) and the *unsuffixed* pair in `9b58ddb` (2026-08-08). So the unsuffixed files are the current ones Ben's prose refers to, and **both sets predate the redesign** — there is no already-refreshed version hiding in the figures directory. All four have to be regenerated. The **unsuffixed 38-era ch3 figures** (`ch3_feature_variance.png`, `ch3_correlation_heatmap.png`, `ch3_top_feature_boxplots.png`, `ch3_length_hist.png`, `ch3_class_balance.png`) **have now been regenerated** by `analysis/ch3_eda.py` on the 43-feature set — no action needed there, but re-check any figure caption that quotes a count.

**(d) Chapter 8 confusion-matrix figures for `random_forest` / `isolation_forest`** — ✅ **RESOLVED 2026-08-10.** All four models now have figures on both datasets; the four new PNGs are untracked and must be committed. Owner was Noam, as part of Ch8.1.

**(e) `report/ch8_4_cascade_findings.md` documents a stage-1 threshold the code never uses.** — ✅ **RESOLVED.** The `stage1_clear_below=0.15` argument is gone from `analysis/ch8_4_cascade.py` (replaced by an explanatory comment at lines 54-59), the generated file now states the calibrated mechanism and reports the calibrated values, and the write-up in `report/ch8_4_cascade_analysis.md` describes the mechanism the code actually runs. Original diagnosis retained below for the record.

The chapter said "Stage 1 Isolation Forest (clear benign if anomaly score **< 0.15**)", and `analysis/ch8_4_cascade.py` does pass `stage1_clear_below=0.15`. But `CascadeDetector.__init__` defaults `stage1_retain_recall=0.99`, and `fit()` **overwrites** `stage1_clear_below` with the calibrated attack-score quantile whenever that is not `None` (`src/ensemble.py`). The 0.15 argument is therefore dead on arrival. Measured effective threshold: **0.0033 (D1) / 0.0032 (D2)** — roughly 45× lower than documented, which is why stage 1 clears so few rows (179 / 65 in the results table). Not a bug in the *behaviour* — recall-calibrated clearing is the intended and better design, argued in Ch6.5 and Ch7 — but the prose describes the wrong mechanism and the dead argument invites the reader to think 0.15 did something. Fix: drop the `stage1_clear_below=0.15` argument from the call (or pass `stage1_retain_recall=None` if the fixed threshold really was intended, which would change every cascade number), and restate the chapter sentence as "clears whatever scores below the 1st-percentile attack score, calibrated at `stage1_retain_recall=0.99`".

⚠️ **Owner corrected: Noam, not Ben.** This entry previously read "Owner: Ben (his chapter)" — wrong. `WORK_DIVISION.md` assigns **8.4 cascading ensemble to Noam**; Ben only drafted the file. The fix, the re-run and the rewrite are all Noam's, and they fold into the re-run absorption noted at the top of this section.

---

## Quick Results Reference

> ✅ **CURRENT (43-feature).** Regenerated by `python main.py all` on 2026-08-09
> and committed in `fbc669d`. Read from `results/summary.json`.

| Model | D1 F1 | D2 F1 | D1 ROC-AUC | D2 ROC-AUC | D1 FPR | D2 FPR |
|---|---:|---:|---:|---:|---:|---:|
| XGBoost-hybrid | **0.8761** | **0.8482** | 0.9794 | 0.9680 | 0.0415 | 0.0494 |
| 1D-CNN | 0.8603 | 0.8384 | 0.9751 | 0.9640 | 0.0555 | 0.0669 |
| Random Forest | 0.7963 | 0.7531 | 0.9402 | 0.9374 | **0.0337** | 0.0515 |
| XGBoost | 0.7856 | 0.7557 | 0.9319 | 0.9301 | 0.0717 | 0.0815 |
| Isolation Forest | 0.2492 | 0.1431 | 0.8120 | 0.6768 | 0.0079 | 0.0097 |

Every model **improved** vs the 38-feature set (old → new D1 F1: XGB 0.761→0.786,
hybrid 0.871→0.876, CNN 0.853→0.860, RF 0.761→0.796; D2 similarly). Isolation
Forest moved 0.264→0.249 (D1) and 0.082→0.143 (D2) — not a regression but a
different fixed-threshold landing point; see `ch7_rf_if_sensitivity_findings.md`.

**The TF-IDF baseline was never invalidated by the redesign.** `scripts/evaluate_baseline.py`
is char_wb 3–5-gram TF-IDF + logistic regression over the **raw command string** —
it never imports `src/features.py`, so the 38→43 change cannot move it. Its
numbers stand as published, and they still **beat every engineered-feature
model** — which is the uncomfortable headline Ch8 has to address honestly, not a
staleness artefact. ⚠️ **Corrected 2026-08-10: this line used to read "D1 F1
0.8808 / ROC-AUC 0.9797, `docs/baseline_metrics.json`" — a mis-attribution, and
the one that propagated into Ch8.3.** That file says **0.8975 / 0.9833**
(D2 0.8824 / 0.9714); 0.8808 came from `results/holdout_baseline_dataset1.json`,
an orphan with no producing code. See the orphan-files entry below.

✅ **Per-model result files regenerated too** (2026-08-09). Worth knowing why they
needed it: `main.py all` writes *only* `results/summary.json` — it does **not**
rewrite `results/holdout_<model>_<dataset>.json` or `results/transfer_*.json`, so
after the redesign those files contradicted `summary.json` (e.g.
`holdout_isolation_forest_dataset1.json` said F1 0.2639 while `summary.json` said
0.2492). All 20 have now been re-run with `main.py holdout` / `main.py transfer`,
which also refreshes the `per_source` breakdown Ch8.1 needs. The regenerated
holdout numbers match `summary.json` to 4 dp — two independent code paths
agreeing, which is a decent correctness check on both.

🔴 **Still stale — Ben's Ch8 artefacts:** `ch8_cross_dataset.json`,
`ch8_confusion.json`, `ch8_4_cascade.json`, `cascade_results.json`.

🔴 **Orphan files under a dead model name.** `results/holdout_cnn_dataset{1,2}.json`
and `results/transfer_cnn_dataset*_to_dataset*.json` use the old model key `cnn`;
the live key is `cnn1d`, so these are pre-redesign leftovers that no current
command can regenerate and that sit next to the fresh `cnn1d` files saying
different things. Delete them, or the docx assembler will eventually read one.

🔴 **Orphan files under a model that has no code — and they were load-bearing.**
`results/holdout_baseline_dataset{1,2}.json` and
`results/transfer_baseline_dataset*_to_dataset*.json` are tracked (committed by
Ben in `9b58ddb` / `32be2a9`) but **no file in the repo produces them** — there
is no `baseline` key in `MODEL_BUILDERS` and nothing in `main.py` writes them.
They disagree with the live, reproducible baseline: orphan D1 F1 **0.8808** /
AUC 0.9797 / FPR 0.0424 versus `scripts/evaluate_baseline.py` →
`docs/baseline_metrics.json` at **0.8975** / 0.9833 / 0.0385 (D2: 0.8631 vs
0.8824). Caught 2026-08-10 while writing the exec summary; the whole
`docs/BASELINE.md`, `docs/DATA_CARD.md` and `preliminary_proposal.md` family
already uses the reproducible 0.8975/0.8824 pair, so the orphans were the odd
ones out.

⚠️ **This had already propagated into Ch8.3, which is now corrected.** The
central decomposition was pivoting on the orphan 0.8808. On the reproducible
number the two steps become **+10.12 representation / +10.03
corpus-and-protocol** — the gap splits almost exactly in half rather than
40/60, which is a cleaner result and strengthens the "not just their easier
dataset" argument. Also corrected in 8.3: the baseline-vs-engineered margins
(D1 0.8975 vs hybrid 0.8761; D2 0.8824 vs 0.8482), the hybrid control sentence
(the tree with *both* representations is now 2 points below char-only LR, not
"within half a point"), and the transfer table/pull-quote (baseline D2→D1
**0.2740**, not 0.3360 — still below the floor, so the six-model claim is
unaffected). Ch8.1's parenthetical baseline FPR moved 0.048 → 0.040. **Delete
the four orphan files at packaging** and take every baseline number from
`docs/baseline_metrics.json`.

> Note the baseline's transfer rows use a different protocol from the models':
> `evaluate_baseline.py` scores *all* rows of the target corpus (n = 9,576 /
> 15,248), the model runs score the target's held-out split. The model never
> saw either, so the comparison is fair, but 8.3 now says so explicitly.

Transfer (cross-dataset) — ✅ **regenerated 2026-08-09 on the 43-feature set**
(`results/transfer_*.json`; old 38-feature value in brackets where it moved):

| Model | D1→D2 F1 | D2→D1 F1 | D1→D2 ROC-AUC | D2→D1 ROC-AUC |
|---|---:|---:|---:|---:|
| 1D-CNN | **0.5405** (0.529) | **0.3587** (0.331) | 0.7703 | 0.7326 |
| XGBoost-hybrid | 0.5319 (0.534) | 0.2756 (0.184) | 0.7665 | 0.6858 |
| Random Forest | 0.5148 (0.509) | 0.1432 (0.175) | 0.7197 | 0.6622 |
| XGBoost | 0.4949 | 0.2349 | 0.7216 | 0.5967 |
| Isolation Forest | 0.1481 (0.078) | 0.2407 (0.248) | 0.6765 | 0.7871 |

The asymmetry survives the redesign and is the Ch8.2 story: **D1→D2 transfers
roughly twice as well as D2→D1** for every supervised model. Two results worth
writing up: the CNN transfers best in both directions (character n-grams
generalise across corpora better than either engineered-feature model), and the
Isolation Forest is the **only** model that transfers *better* D2→D1 (0.2407 vs
0.1481) — consistent with Ch6.5, since a benign-only model trained on messy
operational traffic carries a broader notion of "normal" than one trained on a
curated corpus.
