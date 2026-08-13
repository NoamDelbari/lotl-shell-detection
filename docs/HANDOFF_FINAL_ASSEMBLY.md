# Handoff — final assembly of the Course 3917 report

Written 2026-08-13 for a fresh session. Everything needed to finish the report is
here; nothing below is guessed, and every number was read from a shipped artefact
rather than transcribed from memory. Where a fact matters and could be checked,
the file to check it in is named.

---

## 1. The deliverable and the deadline

**Project.** AI-Driven Detection of Living-off-the-Land Unix Shell Attacks
(MITRE ATT&CK **T1059.004**). Course 3917, Reichman University, Dr. David
Movshovitz & Efi Pecani. **Group 10.** Team: **Noam Delbari** (ID 315005066) and
**Ben Volovelsky** (ID 209361864).

**Dates.** Report freeze **Aug 14 2026**. ZIP submission **Aug 15 2026**.

**Length — the professor's ruling, verbatim:**

> You can have 15 pages of the the report body and 5 additional pages of
> additional tables and graphs as appendixes.

**Formatting spec (graded).** Arial or Calibri 11/12 pt, 1.5 line spacing, bold
headings, tables used wherever they fit, and **a descriptive caption on every
table and figure**. Submission is a ZIP named `Group_X1_X2_Final_Project.zip`.

> ⚠️ **Unresolved:** we read `X1_X2` as the two student IDs and named the
> artefacts `Group_209361864_315005066_*`. Ben made the same call independently.
> Nobody has confirmed it with the professor. Worth one message.

---

## 2. How to work in this repo

These are not style preferences — several are hard project rules.

- **Work section by section, interactively.** Explain the reasoning, present the
  trade-offs, recommend a default, and let Noam make the call before moving to
  the next section. **Never batch-automate whole chapters unattended.**
- **No Workflow / Agent fan-outs.** Noam stopped these explicitly. Verify inline.
- **This transcript is a graded deliverable.** The course AI policy requires the
  full, unedited conversation log to ship in `ai_logs/`; the primary file is
  `ai_logs/claude_code_log.txt`. *"Truncated, summarized, or curated logs will be
  treated as missing."*
- Noam prefers a recommended default in prose over an options menu, and has
  declined the `AskUserQuestion` tool before. Give a recommendation, then the
  reasoning.

**Environment.** Windows 11 Home (26200), Python 3.11.9, console cp1252 — so
**always prefix Python invocations with `PYTHONIOENCODING=utf-8`**. CPU only.
Ben's machine is macOS M3 Pro with MPS. `SEED = 42` lives at `src/__init__.py:17`.
The PowerShell tool cannot parse bash heredocs (`<<'PY'`) — use the Bash tool or
write a scratchpad script.

---

## 3. Repo state

Branch **`noam/ch7-rf-if-sweeps`**, pushed to
`https://github.com/NoamDelbari/lotl-shell-detection.git`. `gh` CLI is **not**
installed. Recent commits:

```
946600d fix: actually commit the build_report changes described in 5a5bb61
5a5bb61 feat: cherry-pick Ben's title page, escaped-pipe fix, and Ch2.4 essay
901f622 feat: condensed Ch1 body section + fixed table column widths
307a6e9 docs: cut both appendices to the professor's 5-page allowance
f13a234 feat: condensed Ch8 body section + fix paragraph joining
29f053f feat: Appendix B (supporting tables, generated) + refresh AI logs
```

### Ben's branch — what was taken and what was not

Ben's `ben/pipeline-models-ch3-8` is at **`b1e9997`**. He branched from `a33d72f`
with no visibility into our then-unpushed commits, so much of his work
independently re-solves problems already closed here. **We cherry-picked rather
than merged.**

**Taken:** the title page (both IDs, both emails, real course name), the
escaped-pipe fix in `parse_table_row`, `report/ch2_4_comparative_essay.md`, and
the `Group_<id1>_<id2>_*` artefact renames.

**Deliberately not taken, and why:**

| His change | Why not |
|---|---|
| `appendix_c_supplementary.md` + `ch8_appendix_pointer.md` | Relocates Ch8.1 and Ch8.4 prose to an appendix. Ch8 is the 20-point chapter, the professor scoped appendices to "additional tables and graphs", and `WORK_DIVISION.md` assigns 8.4 to Noam (already corrected once at `NOAM_TODO.md:413`). `report/body_ch8.md` keeps all four subsections in the body at 3.52 pp. |
| `appendix_a_code_execution.md`, `appendix_b_environment.md` | `report/appendix_a_execution.md` already covers both, with **exact** library versions where his gives `>=` bounds. His also credits imbalanced-learn for SMOTE, which this project does not use. |
| His Ch4 and Ch6 edits | Ours are supersets. His Ch4 is gain-only top-5; ours has the three-view consensus table plus the no-leakage statement. His Ch6 leaves the stale §6.3 in place. |
| His `BODY_FILES` / `stop_before` scheme | It truncates Ch6 at `"## 6.3 Explicit"`, silently dropping a graded rubric item. |
| His auto-caption machinery | Keys captions on header substrings; our Ch4 header contains "What it measures", so it would stamp our 8-row consensus table with a caption for a 5-row gain table. |
| `ch6_2_rf_if.md`, `ch7_2_class_imbalance.md` | Duplicate `ch6_rf_if_justification.md` and `ch7_2_imbalance_validation.md`. **But his are condensed and ours are long** — given the page squeeze, revisit these when cutting; his may be the better *body* versions. |

**Ben has not been told any of this.** Unless he is, he will rebuild Appendix C.

---

## 4. The page budget — the governing constraint

Measured with the Word harness (§6), not estimated:

| Section | rubric pts | measured pages |
|---|---:|---:|
| `exec_summary.md` | 5 | 1.26 |
| `body_ch1.md` | 15 | 6.06 |
| `body_ch8.md` | 20 | 3.52 (3.36 with widths pinned) |
| **three sections** | **40 / 110** | **10.84 / 15** |

Three finished sections carry 36% of the points and 72% of the body. All
`report/*.md` sources total ~53,900 words; at this density the body would run
~30 pages.

**Text trimming is a weak lever** — cutting 172 words from Ch1 moved it 0.24
pages (≈505 words/page). Fitting by prose edits alone means deleting roughly
two-thirds of Ch1.

### The agreed target split (Claude's recommendation; **Noam has not yet approved it**)

| Section | target pp |
|---|---:|
| Exec summary | 0.7 |
| Ch1 | 2.6 |
| Ch3 | 2.6 |
| Ch8 | 2.8 |
| Ch2, Ch4, Ch5, Ch6, Ch7, Bonus | ~1.0 each |

Rationale: protect the three chapters carrying 50 of 100 base points and cut the
light ones harder, rather than splitting proportionally and stripping Ch1 of the
per-feature evidence that earns its 15 points.

**Confirm this with Noam before cutting anything.** Then write each remaining
section *straight to its target*. Writing long and cutting twice is what cost the
Ch1 effort.

Note: figures are **not** on top of the 15 pages. Six embedded figures with
captions cost ~1.5 pages out of the same budget.

---

## 5. What is left

### 5a. Body sections — 3 of 9 written

| Section | pts | status | source files to condense from |
|---|---:|---|---|
| Exec summary | 5 | ✅ `exec_summary.md`, 1.26 pp | — |
| Ch1 | 15 | ✅ `body_ch1.md`, 6.06 pp — **needs cutting to target** | — |
| Ch8 | 20 | ✅ `body_ch8.md`, 3.52 pp | — |
| Ch2 | 10 | ❌ | `ch2_literature_review.md`, `ch2_1_literature_matrix.md`, `ch2_1_shellcore_extraction.md`, `ch2_2_adopt_modify_reject.md`, `ch2_3_comparative_contribution_noam.md`, `ch2_shellcore_matrix_noam.md`, `ch2_4_comparative_essay.md` (Ben's, new) |
| Ch3 | 15 | ❌ | `ch3_eda_findings.md` (D1), `ch3_d2_eda_findings.md`, `ch3_feature_decisions.md` |
| Ch4 | ~10 | ❌ | `ch4_ranking_findings.md` (good as-is, needs condensing) |
| Ch5 | 10 | ❌ | `ch5_1_unified_schema.md`, `ch5_2_distribution_shift.md`, `ch5_3_scaling_normalisation.md` |
| Ch6 | 5 | ❌ | `ch6_model_justification.md`, `ch6_rf_if_justification.md`, `ch6_model_justification_ben.md` — ~4,800 words for a 5-point section; collapse to rubric 6.1/6.2 |
| Ch7 | 10 | ❌ | `ch7_sensitivity_findings.md`, `ch7_rf_if_sensitivity_findings.md`, `ch7_2_imbalance_validation.md`, `ch7_pipeline_diagram.md` |
| Bonus | +10 | ❌ | `bonus_b3_findings.md` — content is done, needs a body slot |

Ch4's rubric weight was not captured by the original grep; 10 is assumed, giving
100 base + 10 bonus.

Naming convention: condensed body sections are `report/body_chN.md`.

### 5b. Assembly

1. **Rewire `build_report.py`.** `BODY_FILES` still lists the stale eight files
   from before this effort. It must read `title_page.md`, `exec_summary.md`,
   `body_ch1.md` … `body_ch8.md`, `bonus_b3_findings.md`, then
   `appendix_a_execution.md` and `appendix_b_tables.md`. **Remove the
   `"## 6.3 Explicit"` truncation stop** — it drops a graded rubric item. Decide
   whether Appendix B page-breaks after A or runs on; **running on is what makes
   the two fit in 5 pages.**
2. **Embed figures — 33 PNGs in `report/figures/`, currently 0 embedded and 0
   captioned.** The spec requires a descriptive caption on each. Budget ~1.5 pages
   for ~6. Strongest candidates: `ch7_pipeline.png` (Rubric Gap 3, architecture
   diagram), `ch8_transfer_heatmap.png`, `ch4_ranking_dataset{1,2}.png`,
   `ch3_class_balance.png`. The eight `ch8_confusion_*.png` are better left in the
   ZIP and referenced, since Table B.7 already carries every confusion matrix.
3. **Apply `<!-- cols: -->` width directives** to `report/appendix_a_execution.md`,
   `report/appendix_b_tables.md` and `report/body_ch8.md`. Validated on scratch
   copies (appendices 4.97 → 4.49 pp; Ch8 3.52 → 3.36) but **not yet written to
   the repo**. `appendix_b_tables.md` is generated — edit
   `analysis/appendix_b_tables.py`, not the markdown.
4. **Rebuild the docx and the ZIP**, then confirm real page counts with the Word
   harness before declaring the budget met.

### 5c. Compliance and close-out

5. **Cross-review.** `WORK_DIVISION.md` requires Noam to read Ben's chapters and
   flag issues before Aug 14. Not done.
6. **Tell Ben what was integrated** (§3), or he will redo Appendix C.
7. **Re-export the AI logs immediately before zipping** — per `ai_logs/README.md`,
   this must be the last step. Ben must re-export his own block if he has added
   AI-assisted work since `ebb5f38`.
8. **Confirm the ZIP filename reading** with the professor.

---

## 6. Tooling

### Measuring pages exactly

Scratchpad scripts (session-specific path; recreate if absent):

- `measure_pages.py` — renders a named `report/*.md` with `build_report`'s
  styling at `Pt(11)`, writing `m_<stem>.docx`. **Requires an absolute path, or a
  bare filename that resolves under `report/`** — a scratchpad-relative name
  resolves to `report/<name>` and raises `FileNotFoundError`.
- `pages.ps1` — fractional page count via Word COM:

```powershell
$r = $d.Content; $r.Collapse(0)
$pg = $r.Information(3); $vp = $r.Information(6)
$usable = $ps.PageHeight - $ps.TopMargin - $ps.BottomMargin
$frac = [math]::Round($pg - 1 + ($vp - $ps.TopMargin) / $usable, 2)
```

Microsoft Word COM automation is available on this machine, so page counts can be
exact rather than estimated. **Always measure; never estimate.**

### Measured density facts

- 11 pt Calibri body prose at 1.5 spacing ≈ **477 words/page**.
- A well-packed 2-column 8.5 pt table ≈ **545–693 words/page** — denser than
  spec-compliant prose, so moving prose into tables *saves* pages.
- An autofit 5-column table with one long text column ≈ **289 words/page** — the
  trap that `<!-- cols: -->` exists to fix.

### The `<!-- cols: -->` directive

Added to `build_report.py` this session. A line like

```
<!-- cols: 1.30 0.80 1.20 1.15 2.05 -->
```

immediately before a table pins its column widths in inches; without it Word
autofits, giving every column a similar width so each row's height is driven by
its longest cell while the short cells sit half empty. On the Ch1 §1.2 five-column
mapping table this was worth **−43%** (5.19 → 2.98 pp). The directive applies to
the next table only, and a blank line between directive and table is harmless.

---

## 7. Canonical numbers — read these, never re-derive

Every figure below is verified against `results/summary.json` and the shipped
result files. **Do not transcribe metrics from prose; read them from the JSON.**

### In-domain hold-out

| dataset | model | TN | FP | FN | TP | precision | recall | F1 | FPR |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D1 | xgboost_hybrid | 2192 | 95 | 94 | 668 | 0.8755 | 0.8766 | 0.8761 | 0.0415 |
| D1 | cnn1d | 2160 | 127 | 91 | 671 | 0.8409 | 0.8806 | 0.8603 | 0.0555 |
| D1 | random_forest | 2210 | 77 | 207 | 555 | 0.8782 | 0.7283 | 0.7963 | 0.0337 |
| D1 | xgboost | 2123 | 164 | 163 | 599 | 0.7851 | 0.7861 | 0.7856 | 0.0717 |
| D1 | isolation_forest | 2269 | 18 | 651 | 111 | 0.8605 | 0.1457 | 0.2492 | 0.0079 |
| D2 | xgboost_hybrid | 1365 | 71 | 74 | 405 | 0.8508 | 0.8455 | 0.8482 | 0.0494 |
| D2 | cnn1d | 1340 | 96 | 64 | 415 | 0.8121 | 0.8664 | 0.8384 | 0.0669 |
| D2 | random_forest | 1362 | 74 | 145 | 334 | 0.8186 | 0.6973 | 0.7531 | 0.0515 |
| D2 | xgboost | 1319 | 117 | 117 | 362 | 0.7557 | 0.7557 | 0.7557 | 0.0815 |
| D2 | isolation_forest | 1422 | 14 | 441 | 38 | 0.7308 | 0.0793 | 0.1431 | 0.0097 |

Baseline TF-IDF + LR: **0.8975 / 0.8824**. It is scored over **all** target rows
rather than the held-out split, so it is indicative, not directly commensurable —
always italicise it and say so.

### Cross-dataset transfer (D1→D2 / D2→D1)

`xgboost_hybrid` 0.532 / 0.276 · `cnn1d` **0.541 / 0.359** · `random_forest`
0.515 / 0.143 · `xgboost` 0.495 / 0.235 · `isolation_forest` 0.148 / 0.241 ·
*baseline* 0.584 / 0.274.

Source-separability probe: **0.821 accuracy against a 0.298 majority baseline**
across 11 corpora — the measured evidence that the features carry corpus style.

### Corpus

**Dataset 1** — 15,248 rows (12,199 train / 3,049 test; 762 attack in test), 11
sources. Attack: `hacktricks` 1805, `gtfobins` 957, `atomic_red_team` 685,
`quasarnix` 204, `slp` 101, `payloads` 60. Benign: `tldr` 4576, `bash_instruct`
3935, `nl2bash` 1567, `linlm` 752, `bash6k` 606.

**Dataset 2** — 9,576 rows (7,661 / 1,915; 479 attack). Benign: `bash_history`
5027, `commandlinefu` 2155. Attack: **`honeypot` 2394 — the entire D2 attack
class.** This is why any sentence about "the honeypot corpus" must be scoped
explicitly to Dataset 2.

Class ratio 1:3, so the **do-nothing F1 floor is 0.400** — every score is measured
against it. Split is 80/20 **grouped by command shape**, with zero groups
straddling. CV is `StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)`
— stratified but **ungrouped**. **SMOTE is not used**; imbalance is handled
cost-sensitively only.

### Code facts

- **43 engineered features**, canonical list in `src.features.FEATURE_NAMES`.
- `MODEL_BUILDERS` keys: `cnn1d`, `isolation_forest`, `random_forest`, `xgboost`,
  `xgboost_hybrid`. **`cnn` and `baseline` are dead keys.** The CNN builder is
  `build_cnn1d` (`src/models.py:314`) and the class is `CNN1DClassifier`.
- `src/ingestion.py` exposes `available_datasets()`, `_read(csv_name)` and
  **`load(dataset) -> (train_df, test_df)`**. There is no `load_dataset`.
- Random Forest ships `n_estimators=400, max_depth=24, max_features="sqrt",
  class_weight="balanced_subsample"`; Isolation Forest `n_estimators=300,
  max_samples=0.8, contamination=0.25` (`src/models.py:135-174`).
- ShellCore's full citation: Alasmary et al. (2022), *ShellCore: Automating
  Malicious IoT Software Detection by Using Shell Commands Representation*, IEEE
  Internet of Things Journal 9(4):2485–2496, doi:10.1109/JIOT.2021.3086398,
  preprint arXiv:2103.14221. Prefer the journal venue over the bare arXiv ID;
  `report/body_ch8.md` currently cites only the arXiv number.

---

## 8. Hard constraints — do not violate

- **Never commit `HF_TOKEN`.** The assignment says so explicitly: read it from an
  environment variable or a `.env` file.
- **`docs/refs/shellcore_arxiv_2103.14221.pdf` stays untracked** (arXiv licensing).
- **The `source` column is never a model input.**
- **The strings `dataset1` / `dataset2` are banned in `src/*.py` outside
  `ingestion.py`, even in comments** — enforced by `tests/test_pipeline.py:43-48`.
  `analysis/*.py` is exempt.
- **Do not re-run `analysis/ch3_feature_audit.py` to "refresh"
  `report/ch3_feature_decisions.md`.** It overwrites Noam's hand-entered FINAL
  KEEP/KILL verdicts. The audit JSON it consumes is already in
  `results/ch3_feature_audit.json`.
- `report/ch3_eda_findings.md` is Ben's hand-written prose and is marked never
  machine-overwritten (see the `analysis/ch3_eda.py` docstring).

---

## 9. Suggested order of work

1. Get Noam's sign-off on the §4 target split.
2. Cut `body_ch1.md` 6.06 → 2.6 pp.
3. Write `body_ch3.md` (15 pts) straight to 2.6 pp.
4. Then Ch7 → Ch2 → Ch4 → Ch5 → Ch6 → bonus, one at a time, each to target, each
   reviewed by Noam before moving on.
5. Rewire `build_report.py`; apply the `<!-- cols: -->` directives.
6. Embed and caption the chosen figures; re-measure.
7. Cross-review Ben's chapters; send him the §3 integration summary.
8. Rebuild docx and ZIP, verify page counts.
9. **Re-export AI logs last**, then submit.

Steps 5–6 depend on the text being frozen, so do not start them early.
