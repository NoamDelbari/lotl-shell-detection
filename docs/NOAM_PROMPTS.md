# Ben's Remaining Prompts — Aug 10
**Freeze: Aug 14 | Submission: Aug 15**

## Status
- ✅ Prompt 1 — Ch1 5-column reformat + feature name fix (DONE)
- ✅ Prompt 2 — Confirm max_depth=12 (DONE)
- ✅ Prompt 3 — Pipeline architecture diagram (DONE)
- ✅ Prompt 4 — Apply Noam's Ch3 D1 repair (DONE)
- ✅ Prompt 5 — Cross-review Noam's chapters (DONE)
- ▶️ Prompt 6 — Merge Noam's branch (RUN THIS NEXT)

---

## Prompt 2 — Confirm max_depth=12 Justification Still Holds

In `report/ch7_sensitivity_findings.md`, the recommended XGBoost setting is
`max_depth=12`, justified as the best-F1 point in the subsample sweep (F1 0.7354
vs 0.7329 at depth 6, on a 5000-row / 38-feature run).

The hybrid now uses 43 features and achieves F1 **0.8761** on full data.

Do the following:
1. Read `report/ch7_sensitivity_findings.md` — find the max_depth table and
   the "Recommended settings" row for max_depth.
2. Read `results/summary.json` — note the current hybrid D1 F1 is **0.871** (38-feature,
   pre-merge). The updated number after Noam's feature merge is **0.8761** (confirmed by
   Noam's Aug 10 message). Use **0.8761** for the text updates below, not the value in
   summary.json.
3. The sweep table numbers (0.7082 / 0.7329 / 0.7332 / 0.7354) came from the
   38-feature subsample and don't need to change — they document the sweep, not
   the final model. What needs updating is:
   - The recommended setting note: change "Adopt 12 (F1 0.7354, FPR 0.0796)
     only after confirming it holds on full data" → confirm it held, cite 0.8761
   - The closing "Full-data revalidation confirms..." paragraph: update the hybrid
     F1 from 0.871 to 0.8761 and CNN from 0.853 to 0.8603
4. Commit and push. Message: "ch7: update full-data revalidation numbers to 43-feature results"

---

## Prompt 3 — Build Ch7.1 Pipeline Architecture Diagram

The assignment rubric requires a visual software architecture diagram. Currently
`PIPELINE.md` has an ASCII block diagram which is acceptable but not ideal.

Do the following:
1. Read `PIPELINE.md` to understand the 3-stage cascade architecture.
2. Write a Mermaid flowchart representing the pipeline. The flow is:
   - Input: raw shell command string
   - Stage 1: Isolation Forest → if anomaly score < threshold: BENIGN (cleared)
     → else: pass to Stage 2
   - Stage 2: XGBoost-hybrid → if P(attack) > 0.7: ATTACK (high confidence)
     → if P(attack) < 0.3: BENIGN (high confidence)
     → else: edge case → pass to Stage 3
   - Stage 3: LLM arbitration (Llama 3.1-8B) → final verdict ATTACK / BENIGN
3. Save as a new file `report/ch7_pipeline_diagram.md` containing only the
   Mermaid block and a one-line caption.
4. In `report/ch7_sensitivity_findings.md`, add a new section at the very top
   (before "## Headline answers"):

   ```
   ## 7.1 Pipeline Architecture

   The detection pipeline is a 3-stage cascade (full design: `PIPELINE.md`).

   [paste the mermaid diagram here]

   **Figure 7.1 — Detection pipeline architecture.** Stage 1 (Isolation Forest)
   bulk-filters obvious benign traffic; Stage 2 (XGBoost-hybrid) handles the
   confident majority; Stage 3 (LLM arbitration) resolves edge cases where both
   supervised models are uncertain.
   ```

5. Commit and push. Message: "ch7: add pipeline architecture diagram (Mermaid) as Fig 7.1"

---

## Prompt 4 — Apply Noam's Ch3 D1 Repair ⏳ WAIT FOR noam/ch7-rf-if-sweeps

Once Noam pushes his branch, run this.

Noam repaired `report/ch3_eda_findings.md` on `noam/ch7-rf-if-sweeps` to fix
11 stale feature names and remove 3 killed features (char_entropy, semicolon_count,
paren_count). The file is marked never-machine-overwritten and needs Ben's sign-off.

1. Fetch and read Noam's repaired version:
   ```
   git fetch origin
   git show origin/noam/ch7-rf-if-sweeps:report/ch3_eda_findings.md
   ```
2. Compare to current `report/ch3_eda_findings.md` in Ben's branch.
3. Apply Noam's corrections to Ben's branch file, preserving Ben's prose and
   interpretation. The rename mapping is:
   - `char_count` → `len_chars`
   - `token_count` → `len_tokens`
   - `token_len_max` → `max_token_len`
   - `token_len_mean` → `mean_token_len`
   - `b64_max_run` → `b64_run_len`
   - `quote_count` → `n_quotes`
   - `redirect_count` → `n_redirect_out`
   - `shell_bins` → `has_shell_bin`
   - `paren_count` → KILLED: remove or rephrase any claim that depends on it
   - `semicolon_count` → KILLED: remove or rephrase any claim that depends on it
   - `char_entropy` → KILLED: remove or rephrase any claim that depends on it
4. Also update the variance table with the new feature names.
5. Commit and push. Message: "ch3 D1: apply featurize() rename/kill corrections (sign-off)"

---

## Prompt 5 — Cross-Review Noam's Chapters

Fetch Noam's branch and read every new chapter file. For each file check:
(a) numbers match new `results/summary.json` values (hybrid 0.8761/0.8482,
CNN 0.8603/0.8384, RF 0.7963/0.7531, IF 0.2492/0.1431, baseline 0.8808/0.8631),
(b) feature names are from the 43-feature FEATURE_NAMES in `src/features.py`,
(c) content meets the rubric requirements in `docs/NOAM_TODO.md`.

```bash
git fetch origin
```

**One issue found:** Noam's `exec_summary.md` shows baseline F1 **0.8975 / 0.8824**
but his own `results/holdout_baseline_dataset1/2.json` say **0.8808 / 0.8631**.
Flag this to Noam before or after the merge — the exec summary needs correcting.

Read these files in order:

```bash
git show origin/noam/ch7-rf-if-sweeps:report/exec_summary.md
git show origin/noam/ch7-rf-if-sweeps:report/ch1_1_threat_analysis.md
git show origin/noam/ch7-rf-if-sweeps:report/ch1_2_mapping_rows_noam.md
git show origin/noam/ch7-rf-if-sweeps:report/ch1_3_feature_rationale.md
git show origin/noam/ch7-rf-if-sweeps:report/ch3_d2_eda_findings.md
git show origin/noam/ch7-rf-if-sweeps:report/ch5_1_unified_schema.md
git show origin/noam/ch7-rf-if-sweeps:report/ch5_2_distribution_shift.md
git show origin/noam/ch7-rf-if-sweeps:report/ch5_3_scaling_normalisation.md
git show origin/noam/ch7-rf-if-sweeps:report/ch6_rf_if_justification.md
git show origin/noam/ch7-rf-if-sweeps:report/ch7_rf_if_sensitivity_findings.md
git show origin/noam/ch7-rf-if-sweeps:report/ch8_1_rf_if_forensics.md
git show origin/noam/ch7-rf-if-sweeps:report/ch8_3_shellcore_comparison.md
git show origin/noam/ch7-rf-if-sweeps:report/ch8_4_cascade_analysis.md
```

For each file produce a short verdict: PASS or list specific issues (wrong number,
stale feature name, missing rubric item). Do NOT edit any files — compile all
issues into a single report at the end so they can be sent back to Noam.

---

## Prompt 6 — Merge Noam's Branch into Ben's Branch

Merge `origin/noam/ch7-rf-if-sweeps` into `ben/pipeline-models-ch3-8`.
Several files will conflict — resolve each one as instructed below.

```bash
git fetch origin
git merge origin/noam/ch7-rf-if-sweeps --no-commit --no-ff
```

Then resolve conflicts file by file:

**`report/ch1_threat_mapping.md`** — if conflicted, use Noam's version (his has
updated IPv4 probe numbers 0.535/0.523 which are more accurate than Ben's 0.546):
```bash
git checkout origin/noam/ch7-rf-if-sweeps -- report/ch1_threat_mapping.md
```

**`report/ch2_literature_review.md`** — both versions removed the sourcing note
and should be near-identical. If conflicted, use Noam's version:
```bash
git checkout origin/noam/ch7-rf-if-sweeps -- report/ch2_literature_review.md
```

**`report/ch7_sensitivity_findings.md`** — Ben added the pipeline diagram and
updated numbers; Noam may have added the RF/IF section header. Manually merge:
keep Ben's pipeline diagram section at the top AND keep whatever Noam added.
If the conflict is just about whose edits to the closing paragraph survive, keep
Ben's numbers (0.8761 / 0.8603).

**`report/ch7_pipeline_diagram.md`** — if conflicted, use Ben's version (he
created it first):
```bash
git checkout HEAD -- report/ch7_pipeline_diagram.md
```

**`ai_logs/README.md`** — use Noam's version (covers all 3 sessions):
```bash
git checkout origin/noam/ch7-rf-if-sweeps -- ai_logs/README.md
```

**`ai_logs/claude_code_log.txt`** — use Noam's version (combined log):
```bash
git checkout origin/noam/ch7-rf-if-sweeps -- ai_logs/claude_code_log.txt
```

**`results/summary.json`** — use Noam's version (43-feature results):
```bash
git checkout origin/noam/ch7-rf-if-sweeps -- results/summary.json
```

**`src/features.py`** — use Noam's version (43-feature redesign):
```bash
git checkout origin/noam/ch7-rf-if-sweeps -- src/features.py
```

**`docs/NOAM_TODO.md`** — if conflicted, use Noam's version:
```bash
git checkout origin/noam/ch7-rf-if-sweeps -- docs/NOAM_TODO.md
```

After resolving all conflicts, verify no conflict markers remain:
```bash
grep -r "<<<<<<" report/ src/ results/ ai_logs/ docs/ 2>/dev/null
```

Then stage and commit:
```bash
git add -A
git commit -m "Merge noam/ch7-rf-if-sweeps: 43-feature models, Ch3-Ch8 report sections, cascade analysis"
git push origin ben/pipeline-models-ch3-8
```
