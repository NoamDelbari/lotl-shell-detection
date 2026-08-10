# Noam's Remaining Prompts — Aug 10 Update
**Freeze: Aug 14 | Submission: Aug 15**

These are the outstanding tasks after the featurize() redesign landed. Run
them in Noam's session on `noam/ch7-rf-if-sweeps` (or a follow-on branch).

---

## ⚠️ Ben's Action Items (Not Prompts — Ben Reads This Too)

Before the freeze:

1. **Sign off on Noam's ch3 D1 repair** — pull `noam/ch7-rf-if-sweeps`, read
   his repaired `report/ch3_eda_findings.md` (Noam updated 11 stale feature
   names and dropped the 3 killed ones; see list below). It's marked
   "never-machine-overwritten" so it needs your explicit OK. **By Aug 12.**

2. **Confirm max_depth=12 still justified** — in `report/ch7_sensitivity_findings.md`,
   the recommended setting is defended as "best-F1 in the sweep (0.7354 vs
   0.7329)." That margin came from the 38-feature subsample run. If Noam's
   full-data RF/IF sweep (on noam/ch7-rf-if-sweeps) shows the XGBoost max_depth
   grid changed, check the new numbers and confirm the reasoning still holds.

3. **Cross-review Noam's chapters** on `noam/ch7-rf-if-sweeps` by Aug 12:
   - `report/ch3_eda_findings_d2.md` (Ch3 D2 EDA)
   - `report/ch6_model_justification.md` §6.4–6.6 (RF + IF justification)
   - `report/ch7_sensitivity_findings.md` RF/IF section

4. **Review Exec Summary and Ch5** (Noam says these are ready on his branch).

5. **Fix Ch1 feature names** — the 5-column reformat Noam flagged. Your row 1
   (`report/ch1_threat_mapping.md`, T1059.004) references three killed/renamed
   features in the "Can a classifier detect it?" column:
   - `dev_tcp_present` → `has_dev_tcp`
   - `redirect_count` → `n_redirect_out` (semantically closest surviving feature)
   - `shell_bins` → `has_shell_bin`
   Update those names and reformat to 5-column per the assignment schema
   (column 4 = Derived / Engineered Feature). See NOAM_TODO.md §1 for schema.

6. **Note on ch2**: Ben already pushed a fix to `report/ch2_literature_review.md`
   (commit `b73a994`) resolving the TOPS paper sourcing. Noam is also updating
   ch2 with new numbers. These edits touch different paragraphs so shouldn't
   conflict, but check when merging.

---

## Stale Numbers Reference

New values from `results/summary.json` (43-feature, full data):

| Model | D1 F1 | D2 F1 | D1 AUC | D2 AUC |
|---|---|---|---|---|
| XGBoost-hybrid | **0.8761** | **0.8482** | — | — |
| 1D-CNN | 0.8603 | 0.8384 | — | — |
| XGBoost (pure) | 0.7856 | 0.7557 | — | — |
| Random Forest | 0.7963 | 0.7531 | — | — |
| Isolation Forest | 0.2492 | 0.1431 | — | — |
| Baseline TF-IDF | **0.8808** | — | — | — |

Transfer (changed): hybrid D2→D1 was 0.184, now **0.2756**.
Baseline numbers are unchanged (runs on raw string, never imports features.py).

---

## Prompt G — Regenerate Stale Cascade Artifacts

The 3-stage cascade results were computed with the old 38-feature models.
Re-run them against the trained 43-feature models:

```bash
python analysis/ch8_4_cascade.py
```

This should overwrite:
- `results/cascade_results.json`
- `results/ch8_4_cascade.json` (if the script writes it)

Also regenerate the cross-dataset and confusion tables:
```bash
python analysis/ch8_confusion.py    # or whichever script produces ch8_confusion.json
python analysis/ch8_cross_dataset.py
```

After each run, print the new cascade routing summary (samples cleared at
stage 1 / referred to stage 2 / referred to LLM).

---

## Prompt H — Refresh Stale Numbers in Report Files

The following report files contain F1/AUC numbers from the 38-feature run.
Update every occurrence of the old values to the new ones from `results/summary.json`:

Files to update (Noam owns these or they're shared):
- `report/ch8_findings.md` — hybrid 0.871→0.8761, CNN 0.853→0.8603, RF 0.761→0.7963, IF 0.264→0.2492
- `report/ch8_3_tops_comparison.md` — all model numbers in the transfer table
- `report/ch8_4_cascade_findings.md` — cascade F1 and routing numbers
- `report/ch6_model_justification.md` §6.4–6.6 — RF and IF stated metrics
- `report/ch7_sensitivity_findings.md` — any "full-data revalidation" reference that cites old hybrid/CNN numbers

**Do NOT change the baseline TF-IDF numbers** — it runs on the raw command
string and does not depend on features.py. Its numbers (0.881 D1 / 0.863 D2)
are correct and stable.

---

## Prompt I — Generate RF and IF Confusion Matrix Figures

The rubric requires confusion matrices for **all four models** on both datasets.
XGBoost-hybrid, CNN, XGBoost-pure figures already exist in `report/figures/`.
The missing ones are Random Forest and Isolation Forest on D1 and D2.

Add a section to `analysis/ch8_confusion.py` (or write a standalone script
`analysis/ch8_rf_if_confusion.py`) that:
1. Loads D1 and D2, trains RF and IF on the train split
2. Predicts on the test split
3. Plots a 2×2 confusion matrix for each (4 figures total)
4. Saves as:
   - `report/figures/ch8_confusion_rf_dataset1.png`
   - `report/figures/ch8_confusion_rf_dataset2.png`
   - `report/figures/ch8_confusion_if_dataset1.png`
   - `report/figures/ch8_confusion_if_dataset2.png`

Use the same figure style as the existing confusion matrix plots (title,
axis labels, color map). Print FN/FP counts for each so they can go into
the Ch8.1 error forensics text.

---

## Prompt J — Rewrite Ch8.4 Cascade Section

`report/ch8_4_cascade_findings.md` currently describes the stage-1 filter
as clearing samples with score < 0.15. That's wrong — the script passes
`stage1_clear_below=0.15` but `fit()` overwrites it via
`stage1_retain_recall=0.99`, making the effective threshold ~0.003 (~45×
lower). The behaviour is correct; the prose is wrong.

Rewrite the cascade mechanism description to say:

> Stage 1 uses an Isolation Forest with `n_estimators=100, contamination=0.10`.
> Its decision boundary is calibrated post-fit to retain 99% of training
> attacks (`stage1_retain_recall=0.99`), which yields an effective anomaly
> score threshold of approximately 0.003–0.004 (dataset-dependent). This
> recall-anchored calibration is the operationally correct choice: as a
> first-pass bulk filter, stage 1 should admit nearly all attacks even at
> the cost of high FPR — the downstream stages handle precision.

Then update the routing table with the new cascade_results.json numbers
(from Prompt G above). If the LLM stage still uses the stub arbitrator,
say so explicitly in the text ("stub arbitrator; real Llama evaluation pending").

---

## Prompt K — Baseline-Beats-Hybrid Paragraph (Ch8)

The new numbers create an uncomfortable headline: the TF-IDF+LR baseline
(D1 F1 **0.8808**) outperforms the XGBoost-hybrid (**0.8761**) in-domain.
This must be acknowledged, not buried.

Add one honest paragraph to `report/ch8_findings.md` (in the Ch8.1 or Ch8.2
section, whichever fits the flow), covering:

1. **State the fact plainly**: baseline D1 F1 0.8808 > hybrid 0.8761
2. **Explain why it isn't surprising**: the baseline runs `char 3–5-gram TF-IDF`
   over the full raw command string with no vocabulary cap — essentially the same
   operation as the hybrid's char n-gram block, but without the supervised
   behavioral features competing for weight. On in-distribution data, the char
   n-grams alone capture the most predictive signal.
3. **Show why the behavioral features still matter**: the transfer results are
   the evidence. Baseline D1→D2: 0.572; hybrid D1→D2: 0.534 — roughly tied
   (both bad). But the hybrid's engineered features make the model *interpretable*
   and allow source-ablation, per-technique forensics, and cascade routing that
   the baseline's opaque TF-IDF vector cannot. The features earn their place in
   the analysis, even if they don't improve raw in-domain F1.
4. **Frame it as an honest finding, not a failure**: "the baseline performance
   ceiling tells us that the dominant in-domain signal is lexical — which is
   itself a finding, and one that explains the transfer collapse."

---

## Prompt L — Delete Orphan Files

Clean up stale result files from the 38-feature run that are no longer valid:

```bash
ls results/cnn*.json        # identify the orphan files
git rm results/cnn.json     # (or whatever the exact filenames are)
git commit -m "chore: remove orphan 38-feature CNN result files"
```

Confirm which files are orphaned vs current before deleting.

---

## Merge Note

When Noam's branch merges into `ben/pipeline-models-ch3-8`, there will be
conflicts in `ai_logs/README.md` and `ai_logs/claude_code_log.txt`. Use
**Noam's versions** of both — his README covers all three sessions (Ben × 2,
Noam × 1) and his `claude_code_log.txt` is the combined submission file.
Ben's standalone versions should be discarded in favour of Noam's combined ones.
