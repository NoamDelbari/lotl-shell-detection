# Docx assembly brief — Noam

Prepared 2026-08-11. **Freeze Aug 14, submit Aug 15 — three days.**

Third document in the set, and the one to open a new session with:

| file | what it is |
|---|---|
| `NOAM_TODO.md` | the original checklist (now partly stale — see §7) |
| `NOAM_WRITING_BRIEF.md` | per-chapter source material for the *writing*, mostly ✅ done |
| **`DOCX_ASSEMBLY_BRIEF.md`** ← this | turning 39 markdown files into one 15-page .docx, plus what's left on me |

It supersedes the last two sections of `NOAM_WRITING_BRIEF.md` ("Packaging +
cross-review", "Suggested order").

**State of the tree:** branch `noam/ch7-rf-if-sweeps` at `ced6e83`, clean, pushed,
38 commits ahead of `origin/main`. All research and nearly all chapter prose is
done. `pytest tests/ -q` → 6 passed.

---

## 1. The authoritative spec

Source: `docs/Final_Project_AI_Driven_Intrusion_Detection.pdf`. **Read this, not
the checklist** — the PDF corrected several assumptions in `NOAM_TODO.md`.

### Formatting instructions (p. 13, verbatim)

1. Technical report is limited to **15 pages in 1.5 spacing**.
2. Clean, professional typography (e.g. **Arial or Calibri, size 11/12**).
3. **Bold headings**, clear section breaks, properly labelled code snippets / equations.
4. Short and clear answers.
5. **Use tables as much as possible.**
6. Supporting exploration graphs may go **in appendices** as required.
7. **All tables and figures must have a descriptive caption.**

> *"Note: Report quality and adherence to formatting are graded."*

Rules 4 + 5 are the operative ones for us: the grader wants tables, not essays.
Our source markdown is essay-heavy, which is exactly the wrong shape — see §2.

### Required structure and point values (p. 13–16)

| § | Title | Pts |
|---|---|---:|
| — | Title Page | — |
| — | Executive Summary — **max 1 page** | 5 |
| 1.1 / 1.2 / 1.3 | Deep-Dive Threat Analysis · Structural Telemetry Mapping · Theoretical Feature Rationale | 15 |
| 2.1 / 2.2 | Literature Extraction Matrix (**both papers, one matrix**) · Comparative Analytical Essay | 10 |
| 3.1 / 3.2 / 3.3 | Statistical & Visual Exploration · Noise & Redundancy Reduction · Empirical Justification | 15 |
| 4.1 / 4.2 | Tree-Based Feature Importance Ranking · Critical Discrepancy Analysis | 10 |
| 5.1 / 5.2 / 5.3 | Unified Feature Schema · Cross-Dataset Distribution Shift · Data Scaling & Remedies | 10 |
| 6.1 / 6.2 | Architectural Customization Justification · SOTA Literature Synthesis | 5 |
| 7.1 / 7.2 / 7.3 | Pipeline Block Diagram · **Class Imbalance Strategy & Validation Framework** · Hyperparameter Sensitivity | 10 |
| 8.1 / 8.2 / 8.3 / 8.4 | Forensic Error Categorization · Cross-Dataset Variance · Literature Benchmarking · Hybrid Behavioral Cascading | 20 |
| B.1–B.4 | Bonus: LLM Hosting · Prompt Engineering · Reasoning Accuracy · Operational Tradeoff | +10 |
| App A / B | Code Execution Instructions · Frameworks & Hardware Environment Specs | — |

**Title page fields (exact):** Course Name: *Using AI for Intrusion and Malware
Detection* · Project Title (attack + MITRE ID) · Group Identification: Group
Number [XX] · Team Members: Name & Email ×2 · Date of Submission.

### Submission (p. 12) — ⚠️ the TODO has this wrong

**`Group_X1_X2_Final_Project.zip`, where X1 and X2 are the student IDs** — not
`Group_[XX]_Final_Project.zip` as `NOAM_TODO.md:276` says. Three components:

1. **Code repo** — modular commented Python, entry-point script (`main.py`), `requirements.txt` with exact versions, `README.md` quick-start.
2. **Report** — `.docx`.
3. **AI logs** — `.txt`/`.json`, one file per tool, `ai_logs/<tool_name>_log.txt`, full and unedited, chronological with clear session separators. *"Truncated, summarized, or curated logs will be treated as missing."*

---

## 2. The page budget — the actual problem

**39 markdown files · 41,615 words · 39 figures → ~15 pages.**

At 1.5 spacing / 11 pt Calibri / 1" margins, a full page of prose is ≈385 words.
Reserve ~4 pages for tables and figures and the prose budget is **≈3,800–4,200
words**. That is roughly a **10:1 compression**.

**This is a rewriting job, not an editing job.** Do not try to trim the markdown
down. The right mental model: the markdown chapters are the *evidence base* and
they already ship in the ZIP under `report/`; the .docx is a 15-page **findings
document** that states conclusions in tables and points at the evidence. Every
subsection should open with its answer, not build to it.

### Allocation (proportional to points, per `WORK_DIVISION.md:46`)

| § | Pages | Source files (words) | Shape in the docx |
|---|---:|---|---|
| Title page | 1.0 | — | — |
| Exec summary | 1.0 | `exec_summary` (544) | prose + 6-row table — already sized right |
| 1.1 | 0.6 | `ch1_1_threat_analysis` (1104) | ~230 w prose |
| 1.2 | 0.9 | `ch1_threat_mapping` (707) + `ch1_2_mapping_rows_noam` (1423) + `ch1_telemetry_rows_ben` (668) | **one 7-row × 5-col table**, no prose |
| 1.3 | 0.5 | `ch1_3_feature_rationale` (1580) | 8-row family table + ~150 w |
| 2.1 | 0.5 | `ch2_shellcore_matrix_noam` (1118) + `ch2_literature_review` matrix (942) | **one merged matrix, both papers** |
| 2.2 | 0.75 | `ch2_1` (1231) + `ch2_2` (1362) + `ch2_3` (1232) | ~290 w essay |
| 3.1 | 0.8 | `ch3_eda_findings` (990) + `ch3_d2_eda_findings` (1207) | 2 figures + ~200 w |
| 3.2 | 0.6 | `ch3_feature_decisions` (2758) | 68→43 gate table + ~200 w |
| 3.3 | 0.6 | same + `ch3_feature_justification.csv` → appendix | ~230 w |
| 4.1 | 0.5 | `ch4_feature_ranking.csv` | top-15 table or the ranking figure |
| 4.2 | 0.75 | `ch4_ranking_findings` (699) + `ch4_ranking_notes` (265) | ~290 w |
| 5.1–5.3 | 1.25 | `ch5_1` (1050) + `ch5_2` (1266) + `ch5_3` (1048) | ~480 w + sign-inversion table |
| 6.1–6.2 | 0.75 | `ch6_rf_if_justification` (2769) + `ch6_model_justification` (1103) + `_ben` (451) | ~290 w — **worst compression ratio in the report, 15:1** |
| 7.1 | 0.5 | `ch7_pipeline_diagram` (185) | Figure 7.1 |
| 7.2 | 0.35 | **MISSING — see §3** | ~250 w + 5-row table |
| 7.3 | 0.4 | `ch7_sensitivity_findings` (1882) + `ch7_rf_if_sensitivity_findings` (1935) | table only |
| 8.1 | 0.8 | `ch8_1_rf_if_forensics` (2109) + `_ben` (407) + `_noam` (512) + `ch8_findings` (1425) | 10 confusion matrices + ~250 w |
| 8.2 | 0.5 | `ch8_2_cross_dataset_table` (474) | table — **already compliant, drop in as-is** |
| 8.3 | 0.7 | `ch8_3_shellcore_comparison` (1895) + `ch8_3_tops_comparison` (939) + `_ben` (350) | benchmark table + ~270 w |
| 8.4 | 0.5 | `ch8_4_cascade_analysis` (2372) + `ch8_4_cascade_findings` (410) | ablation table + ~190 w |
| Bonus | 0.75 | `bonus_b3_findings` (235) + B.1/B.2/B.4 unwritten | ~290 w |
| App A/B | 0.5 | unwritten | commands + 2-environment table |

**Total: 15.5 pages.** Half a page over before a single word is written.

Three ways to find it, in the order I'd try them:
1. **Ask whether the title page and appendices count** (§8). If they don't, we're at 14.0 with room to spare. Highest-leverage single answer in this document.
2. Drop the bonus (−0.75). Ground rule already says bonus goes first.
3. Squeeze Ch6 to 0.5 and Ch3.3 to 0.5.

Do **not** solve it by shrinking Ch8 — it's 20 points, the largest single block,
and it carries the findings the whole report is built around.

---

## 3. Gaps that must close before assembly

**① §7.2 does not exist.** A required subsection of a 10-point chapter, and no
report file contains it. Everything needed is in the code, verified:

| Concern | Implementation | Cite |
|---|---|---|
| Class imbalance (1:3) | `scale_pos_weight = 3.0` — "~ n_neg/n_pos at the 1:3 ratio" | `src/models.py:53,95` |
| Imbalance (RF) | `class_weight = "balanced_subsample"` | `src/models.py:139` |
| Imbalance (CNN) | pos-weighted loss, "the sequence analogue of XGBoost's `scale_pos_weight`" | `src/models.py:227` |
| Validation | `StratifiedKFold(n_splits, shuffle=True, random_state=SEED)` | `src/evaluation.py:17,69` |
| Leakage | every fit wrapped in `ImbPipeline([... ("scale", StandardScaler()) ...])` so anything that learns (scaler stats, char vocab, SMOTE sampler) sees only the training fold | `src/models.py:16,79-81,124,150-152,177-179` |
| Split integrity | 80/20 **grouped by command shape**, 0 straddles | `docs/DATA_CARD.md` |

Roughly 250 words plus that table. **~30 minutes.** Formally Ben's
pipeline-skeleton territory, but it's faster to write it than to hand it over.

**② Captions.** Only Figure 7.1 has one. Rule 7 requires a descriptive caption
on *every* table and figure, and formatting is graded. With ~12 figures and ~15
tables that's ~27 captions. Number them `Figure N` / `Table N` **sequentially
through the document**, not per chapter — simpler to keep consistent under time
pressure.

**③ §2.1 needs one merged matrix.** The spec asks for a comparative matrix over
**both** papers. Right now ShellCore lives in `ch2_shellcore_matrix_noam.md` and
Trizna/SLP + TOPS in `ch2_literature_review.md`, in different shapes. Merge into
one table with a column per paper and a "this project" column.

**④ §8.3 cross-reference.** The spec says benchmark against the literature
*"reviewed in Chapter 6"*; our text points at Ch2. Either reconcile the pointer
or make sure Ch6.2's SOTA synthesis names the same papers 8.3 benchmarks against.

**⑤ Appendix A and B don't exist.** B must name **both** environments or it
misdescribes how the numbers were produced: *Environment A (Ben)* macOS /
Apple-M-series, CNN on `torch.device("mps")`; *Environment B (Noam)* Windows 11,
Python 3.11.9, CPU only.

**⑥ Title page needs data I don't have:** group number, both student IDs, both
emails. Also blocks the ZIP filename. See §8.

---

## 4. Figures — pick from these, and watch the stale ones

⚠️ **Seven figures predate the 38→43 feature rebuild** (commit `9b58ddb`, Aug 8;
the rebuild is `fbc669d`, Aug 9). Putting one in the docx would contradict the
numbers on the same page:

`ch7_sensitivity_xgboost` · `ch7_sensitivity_cnn` (both superseded by the
`_dataset1/2` pairs regenerated Aug 10) · `ch8_errors_by_source_dataset1` ·
`ch8_errors_by_source_xgboost_hybrid` · `ch8_errors_by_source_cnn` ·
`ch8_transfer_heatmap` · `ch4_feature_importance_dataset{1,2}` (superseded by
`ch4_ranking_dataset{1,2}`, Aug 10).

**Rule for assembly: use no figure committed before `fbc669d` unless it has been
re-verified.** Fastest check: `git log -1 --format=%ad --date=short -- <path>`.

Current and safe:

| § | Figure | Note |
|---|---|---|
| 3.1 | `ch3_class_balance`, `ch3_length_hist_dataset{1,2}`, `ch3_corr_heatmap_dataset{1,2}`, `ch3_variance_by_label_dataset{1,2}` | Aug 9, on 43 features. Pick 2 for the body, rest to appendix |
| 4.1 | `ch4_ranking_dataset{1,2}` | Aug 10 |
| 7.1 | `ch7_pipeline_diagram.md` (Mermaid) | **must be rendered to PNG** — see §5 |
| 7.3 | `ch7_sensitivity_{xgboost,cnn1d,random_forest,isolation_forest}_dataset{1,2}` | Aug 9–10. Appendix; the body gets a table |
| 8.1 | all 10 `ch8_confusion_<model>_dataset{1,2}` | Aug 10, all current. **8.1 requires all models × both datasets** — this is the one place figures are non-negotiable |

Ten confusion matrices at readable size is ~0.6 pages as a 5×2 grid. Build it as
a single borderless 5×2 table of images with one caption, not ten floats.

---

## 5. Build toolchain

Probed this machine: **no pandoc**. **python-docx 1.2.0 installed.** **pywin32
OK**, Word at `C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE`.

That last one matters more than it sounds: Word COM can open the built file and
report `ActiveDocument.ComputeStatistics(2)` — the **real** page count. So the
15-page limit becomes a closed loop instead of guesswork:

```
write report/docx/*.md  →  python scripts/build_report_docx.py  →  Word COM page count  →  trim  →  repeat
```

Suggested shape for `scripts/build_report_docx.py`:

- Styles set once: Calibri 11, `paragraph_format.line_spacing = 1.5`, bold headings.
- Content authored as **new, short** markdown under `report/docx/` — one file per
  numbered subsection, named to sort (`01_exec.md`, `11_ch1_1.md`, …). Do **not**
  point the builder at the existing chapter files; they're the evidence base, 10×
  too long, and several are internal notes rather than report prose.
- A minimal md→docx converter is enough: headings, bold/inline-code, bullet
  lists, pipe tables, `![caption](figures/x.png)`. No pandoc-grade fidelity needed.
- Captions emitted from the image/table alt text into a `Caption` style with an
  auto-incrementing counter — that makes gap ② mechanical rather than manual.

**Mermaid → PNG.** Figure 7.1 is a Mermaid block and Word can't render it. No
mermaid CLI here. Cheapest route: paste the block into mermaid.live, export PNG
at 2× scale, save as `report/figures/ch7_pipeline.png`, commit. ~5 minutes. Do
this early — it's a rubric-required figure (Gap 3) sitting behind a manual step.

---

## 6. My remaining TODO, in order

**Day 1 (Aug 12) — close the gaps, get to a full draft**

1. Render Figure 7.1 to PNG (5 min, unblocks §7.1).
2. Write §7.2 (30 min, table in §3 above).
3. Merge the §2.1 matrix into one table covering both papers.
4. Write Appendix A (commands) + Appendix B (**both** environments).
5. Fix the three known stale-number sites (§7 below).
6. Build `scripts/build_report_docx.py` + the styles, get *anything* to compile
   and print a page count. An empty pipeline that reports "3 pages" is worth more
   at this stage than three perfect sections that never get measured.

**Day 2 (Aug 13) — write the docx content, biggest-first**

7. Ch8 (2.5 pp, 20 pts) → Ch1 (2.0, 15) → Ch3 (2.0, 15) → Ch2 / Ch4 / Ch5 / Ch7
   (1.25 each, 10) → Ch6 (0.75, 5) → exec summary last, once the findings are final.
8. Captions as you go, never in a sweep at the end.
9. Cross-review Ben's 8 files (required before freeze; assume numbers stale until proven).
10. Title page once the IDs land.

**Day 3 (Aug 14) — freeze**

11. Page-count loop until ≤15. Trim in the order given in §2.
12. Bonus only if ≥3 hours remain (see §9).
13. Delete the 8 orphan `results/` files: `holdout_baseline_dataset{1,2}.json`,
    `transfer_baseline_dataset{1_to_2,2_to_1}.json`, `holdout_cnn_dataset{1,2}.json`,
    `transfer_cnn_dataset{1_to_2,2_to_1}.json`.
14. Verify `requirements.txt` pins exact versions; `README.md` quick-start runs clean.
15. **Re-export AI logs last** — the Session 4 block in `claude_code_log.txt` is
    still a mid-session snapshot. `ai_logs/README.md` §"Regenerating the transcripts"
    has the four commands; step 0 is Ben's and only he can run it.
16. ZIP as `Group_X1_X2_Final_Project.zip`.

**Hard invariants at packaging — do not break these**

- `HF_TOKEN` never committed; read from env or `.env`.
- `docs/refs/shellcore_arxiv_2103.14221.pdf` **stays untracked** (arXiv licensing).
- `!! DO NOT re-run analysis/ch3_feature_audit.py !!` — it overwrites my
  hand-entered FINAL verdicts in `report/ch3_feature_decisions.md`.
- `source` is never a model input; `dataset1`/`dataset2` banned in `src/*.py`
  except `ingestion.py` (enforced by `tests/test_pipeline.py:43-48`).

---

## 7. Known-stale numbers still in the tree

Left for Ben but take them if he hasn't by Aug 13:

| File | Problem |
|---|---|
| `report/ch2_literature_review.md:17` | hybrid `0.871/0.978`, `0.846/0.965`; CNN `0.853/0.841`; baseline `0.881/0.863`; TPR@FPR=0.1% `0.575/0.507`. Live: **0.8761 / 0.9794**, **0.8482 / 0.9680**; CNN **0.8603 / 0.8384**; baseline **0.8975 / 0.8824**; TPR **0.5669 / 0.5261** |
| `report/ch2_literature_review.md:19` | the "Baseline configuration note" paragraph is **obsolete** — it argues about a residual ~0.02 gap to "the original 0.898/0.882 references", but `docs/baseline_metrics.json` *is* 0.8975/0.8824. The gap closed; delete the paragraph |
| `PIPELINE.md:89-90` | xgboost `0.760/0.736` → **0.7856/0.7557**; RF `0.748/0.737` → **0.7963/0.7531** |
| `report/ch8_3_tops_comparison.md` | Ben's table, unverified |
| `docs/NOAM_TODO.md:383` | asserts Ben's baseline figures "are correct" — written before the orphan-baseline discovery |
| `docs/NOAM_TODO.md:276` | wrong ZIP name |
| Ben's chapters | five dead feature names still cited: `n_ipv4`, `n_redirects`, `n_ports`, `n_backticks_subshell`, `char_entropy` |

**Canonical numbers** (from `results/summary.json`, regenerated on the 43-feature set):

| model | D1 F1 | D1 ROC-AUC | D2 F1 | D2 ROC-AUC |
|---|---:|---:|---:|---:|
| xgboost_hybrid | 0.8761 | 0.9794 | 0.8482 | 0.9680 |
| cnn1d | 0.8603 | 0.9751 | 0.8384 | 0.9640 |
| random_forest | 0.7963 | 0.9402 | 0.7531 | 0.9374 |
| xgboost | 0.7856 | 0.9319 | 0.7557 | 0.9301 |
| isolation_forest | 0.2492 | 0.8120 | 0.1431 | 0.6768 |
| *baseline (TF-IDF+LR)* | *0.8975* | *0.9833* | *0.8824* | — |

Do-nothing floor at 0.250 prevalence: **F1 = 0.400**. Transfer: D2→D1 0.2740, D1→D2 0.5844.

---

## 8. Open questions — I need answers to these

1. **Do the title page and appendices count toward the 15 pages?** Worth 1.5
   pages, i.e. the entire overflow. Formatting rule 6 ("supporting exploration
   graphs in appendixes as required") hints at relief but never says it. This is
   an email to Movshovitz/Pecani, and the answer changes how much I cut. Ask now
   so the answer arrives before Aug 14.
2. **Group number, both student IDs, both emails.** Blocks the title page *and*
   the ZIP filename (`Group_X1_X2_Final_Project.zip`).
3. **Bonus in or out?** Decide by Aug 13 morning, not Aug 14 evening.

---

## 9. Bonus — the go/no-go, decided by numbers

Only attempt if ≥3 hours are free on Aug 14 *after* the page count is under 15.

Scaffolding exists (`src/llm_triage.py`, `analysis/bonus_b3_llm_eval.py`, cascade
already wired to the arbitrator). Needs `HF_TOKEN`, then
`python analysis/bonus_b3_llm_eval.py --hf`, then replace the stub tables in
`bonus_b3_findings.md` and `ch8_4_cascade_findings.md`, then write B.1/B.2/B.4.

The bar is known and it is not zero:

- Band `[0.35, 0.65]` routes **146 calls on D1 / 101 on D2** (4.8% / 5.3% of traffic) ≈ 4–12 min for both test sets — so B.4's operational verdict is **viable** at this band width.
- The arbitrator must beat **58.9% (D1) / 63.4% (D2)** accuracy on those rows — that is stage 2's own accuracy there, which the offline stub exactly ties. Below that it is pure added latency.
- Oracle ceiling is **+3.7 F1** over the best single model (0.9132 / 0.8849). Score against +3.7, not against zero.

And keep §8.4 an honest negative result at assembly: every cascade stage makes
things worse (D1 F1: hybrid 0.8761 > stage1+2 0.8737 > stage2+3 0.8716 > full
0.8685), and three single thresholds on stage 2 alone match or beat the whole
cascade on both precision and recall.
