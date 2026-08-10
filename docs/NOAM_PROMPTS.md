# Ben's Prompts — Action Items from Noam's Aug 10 Update
**Run these in Claude Code on `ben/pipeline-models-ch3-8`. Freeze: Aug 14.**

---

## Prompt 1 — Fix Ch1 Feature Names and 5-Column Reformat

In `report/ch1_threat_mapping.md`, the T1059.004 row (reverse shells) references
three feature names that were killed or renamed in the featurize() redesign:
- `dev_tcp_present` → `has_dev_tcp`
- `redirect_count` → `n_redirect_out`
- `shell_bins` → `has_shell_bin`

Fix those three names in the table's "Can a classifier detect it reliably?" column.

Also, the assignment requires a **5-column** table. The current table has 4 columns.
Add a fifth column "Derived / Engineered Feature" between columns 3 and 4, listing
the specific feature names from `src/features.py` FEATURE_NAMES that are relevant
to each row. Use the 43-feature FEATURE_NAMES list (visible in Noam's redesigned
`src/features.py`). The 5-column schema is:
1. Sub-technique ID and name
2. How it appears in shell telemetry
3. Dataset source & how it is captured
4. Derived / Engineered Feature (new column — feature names from FEATURE_NAMES)
5. Can a provenance-labeled classifier detect it reliably?

Apply this reformat to all three of Ben's rows. Commit and push.

---

## Prompt 2 — Apply Noam's Ch3 D1 Repair to Ben's Branch

Noam repaired `report/ch3_eda_findings.md` on `noam/ch7-rf-if-sweeps` to fix
11 stale feature names and drop 3 killed features (char_entropy, semicolon_count,
paren_count). The file is marked never-machine-overwritten and needs Ben's sign-off.

Do the following:
1. Read Noam's repaired version:
   `git show origin/noam/ch7-rf-if-sweeps:report/ch3_eda_findings.md`
   (if that branch isn't available yet, use: `git show origin/noam/features-ch3:...`
   and note that the repair may be on the newer branch only)
2. Compare it to the current `report/ch3_eda_findings.md` in Ben's branch.
3. Apply the feature-name corrections to Ben's branch version, preserving Ben's
   interpretation and prose. The mapping is:
   - `char_count` → `len_chars`
   - `token_count` → `len_tokens`
   - `token_len_max` → `max_token_len`
   - `token_len_mean` → `mean_token_len`
   - `b64_max_run` → `b64_run_len`
   - `quote_count` → `n_quotes`
   - `paren_count` → KILLED: remove claims that depend on it
   - `semicolon_count` → KILLED: remove claims that depend on it
   - `redirect_count` → KILLED: replace with `n_redirect_out` where the claim still holds
   - `shell_bins` → `has_shell_bin`
   - `char_entropy` → KILLED: remove claims that depend on it
4. Update the variance table to use new feature names and new numbers if available
   from `results/ch3_feature_audit.json` (on Noam's branch).
5. Commit and push with message "ch3 D1: apply featurize() rename/kill corrections".

---

## Prompt 3 — Cross-Review Noam's Chapters

Noam says the following are ready on `noam/ch7-rf-if-sweeps`:
- `report/ch3_eda_findings_d2.md` (Ch3 D2 EDA)
- `report/ch6_model_justification.md` §6.4–6.6 (RF + IF justification)
- `report/ch7_sensitivity_findings.md` RF/IF sensitivity section
- Executive Summary
- Chapter 5 (Harmonization)

Fetch the branch and read each file:
```
git fetch origin
git show origin/noam/ch7-rf-if-sweeps:report/ch3_eda_findings_d2.md
git show origin/noam/ch7-rf-if-sweeps:report/ch6_model_justification.md
git show origin/noam/ch7-rf-if-sweeps:report/ch7_sensitivity_findings.md
git show origin/noam/ch7-rf-if-sweeps:report/exec_summary.md  (or wherever he put it)
git show origin/noam/ch7-rf-if-sweeps:report/ch5_harmonization.md
```

For each file, check:
- Numbers match new `results/summary.json` values (hybrid 0.8761/0.8482, CNN 0.8603/0.8384,
  RF 0.7963/0.7531, IF 0.2492/0.1431)
- Feature names match FEATURE_NAMES (43-feature list)
- Ch6 RF/IF sections cite at least one paper each and include explicit hyperparameters
- Ch7 RF/IF sensitivity tables are present with varied parameters and chosen settings
- Ch5 covers: unified feature schema, cross-dataset distribution shift, scaling remedies
- Executive Summary covers all 4 models, both datasets, cascade, and transfer collapse

Report any specific issues (wrong numbers, stale feature names, missing content)
so they can be sent back to Noam before Aug 12.

---

## Prompt 4 — Confirm max_depth=12 Justification Still Holds

In `report/ch7_sensitivity_findings.md`, the recommended XGBoost setting is
`max_depth=12`, justified as the best-F1 point in the subsample sweep (0.7354 vs
0.7329 at depth 6). That margin came from a 38-feature, 5000-row subsample run.

The hybrid now achieves F1 0.8761 on full data with max_depth=12. Check:
1. Does Noam's full-data RF/IF sensitivity run on `noam/ch7-rf-if-sweeps` include
   a re-run of the XGBoost depth sweep? If so, read those numbers.
2. If the new sweep still shows depth-12 as best or tied-best, the justification
   stands — update the closing paragraph to cite the new full-data F1 (0.8761)
   instead of the old subsample number.
3. If the new sweep shows a different optimum, update the recommended setting and
   rationale accordingly.

The change should be minimal — just confirm the recommendation and update the
one "Full-data revalidation confirms..." sentence at the end of the chapter with
new numbers. Commit if any change is needed.

---

## Prompt 5 — Build Ch7.1 Pipeline Architecture Diagram

The assignment rubric requires a "visual software architecture diagram" for the
detection pipeline. Currently only the ASCII block diagram in `PIPELINE.md`
(lines 10–35) exists. The rubric says ASCII in a monospace block is acceptable
but not more — a proper diagram would score better.

Do the following:
1. Read `PIPELINE.md` to understand the 3-stage cascade architecture.
2. Produce a Mermaid flowchart diagram representing the pipeline (Mermaid renders
   in GitHub markdown and in most docx converters). Structure:
   - Input: raw shell command
   - Stage 1: Isolation Forest filter (pass/flag)
   - Stage 2: XGBoost-hybrid classifier (confident-benign / confident-attack / uncertain)
   - Stage 3: LLM arbitration (edge cases only)
   - Output: BENIGN / ATTACK + confidence
3. Save the diagram as a fenced ```mermaid block in a new file
   `report/ch7_pipeline_diagram.md` with a brief caption.
4. Also embed the diagram (or the ASCII fallback if Mermaid isn't available in
   the final docx tool) directly in `report/ch7_sensitivity_findings.md` at the
   top under a new "## 7.1 Pipeline Architecture" heading, before the current
   "## Headline answers" section.
5. Commit and push.
