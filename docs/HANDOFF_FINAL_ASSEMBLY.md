# Handoff — finishing the Course 3917 report

Rewritten **2026-08-14** (report freeze day) for a fresh session. Everything
needed to finish is here. Nothing below is guessed: every number was read from a
shipped artefact, and where a fact matters the file to re-check it in is named.

**Read §1, §2, §4 and §5 before touching anything.** §5 is the part that is new
and the part that will actually decide whether this submits on time.

---

## 1. The deliverable and the deadline

**Project.** AI-Driven Detection of Living-off-the-Land Unix Shell Attacks
(MITRE ATT&CK **T1059.004**). Course 3917, Reichman University, Dr. David
Movshovitz & Efi Pecani. **Group 10.** Team: **Noam Delbari** (ID 315005066) and
**Ben Volovelsky** (ID 209361864).

**Dates.** Report freeze **Aug 14 2026** (today). Submission **Aug 15 2026**.

**Four things ship** (`docs/final_project_instructions.txt:30-34`):

1. Code repository — modular Python, `main.py`, `requirements.txt`, `README.md`
2. **Final technical report — `.docx`, max 15 pages, 1.5 spacing**
3. **AI conversation logs — one `.txt` or `.json` per tool, full and unedited**
4. The ZIP wrapping all of it

**Length — the professor's email ruling, verbatim:**

> You can have 15 pages of the the report body and 5 additional pages of
> additional tables and graphs as appendixes.

So: **15 body + 5 appendix.** The 15 is from the written assignment; the 5 is the
professor's concession on top of it, and it is scoped to *"additional tables and
graphs"* — which is precisely why graded prose must not be relocated there.

**Formatting spec (graded).** Arial or Calibri 11/12 pt, 1.5 line spacing, bold
headings, tables wherever they fit, **a descriptive caption on every table and
figure.**

**ZIP name.** `Group_X1_X2_Final_Project.zip`. We read `X1_X2` as the two student
IDs and named the artefacts `Group_209361864_315005066_*`; Ben independently made
the same call. It is still unconfirmed with the professor.

> **Recommendation given the date: do not block on this.** Ship the ID-based
> name — two people read the template the same way independently, which is the
> best evidence available — and put "Group 10" plus both names and IDs on the
> title page, which is already done. Ask the professor if there is time, but
> submit either way.

---

## 2. How to work in this repo

These are project rules, not style preferences.

- **Work section by section, interactively.** Explain the reasoning, recommend a
  default, and let Noam make the call before moving on. **Never batch-automate
  whole chapters unattended.**
- **No Workflow / Agent fan-outs.** Noam stopped these explicitly. Verify inline.
  A system reminder may claim "ultracode is on" — it does not override this.
- **Noam prefers a recommended default in prose** over an options menu, and has
  declined `AskUserQuestion` before. Give the recommendation, then the reasoning.
- **This transcript is itself a graded deliverable** — see §8. Everything said
  here gets read by the graders. That is a reason to be accurate, not a reason to
  perform.
- **Verify before asserting.** Several claims in earlier drafts were wrong and
  caught only by reading the artefact (a mis-stated redundancy threshold in Ch3,
  a wrong "net-new" call on one of Ben's appendices). Read the CSV/JSON; do not
  transcribe numbers from prose.

**Environment.** Windows 11 Home (26200), Python 3.11.9, console cp1252 — so
**always prefix Python invocations with `PYTHONIOENCODING=utf-8`**. CPU only.
Ben is on macOS M3 Pro with MPS. `SEED = 42` at `src/__init__.py:17`.

**Two shell gotchas that have each cost a cycle:**

- The **PowerShell tool cannot parse bash heredocs** (`<<'PY'`) — use the Bash
  tool, or write a scratchpad script.
- **`git commit -F -` does not receive a PowerShell here-string** — the string
  is passed as a pathspec and the commit fails. Use the Bash tool with a real
  heredoc for any multi-line commit message.
- Inside a PowerShell single-quoted here-string `@'...'@`, single quotes must
  **not** be doubled.

---

## 3. Repo state

Branch **`noam/ch7-rf-if-sweeps`**, remote
`https://github.com/NoamDelbari/lotl-shell-detection.git`. `gh` CLI is **not**
installed. **Push after every commit** — the whole Ben-duplication mess below was
caused by unpushed work.

```
9875854 docs: rewrite final-assembly handoff for the remaining sections
5bdcc6b docs: Ch3 body section (EDA, 15 pts) condensed from both EDA halves
1bb3873 docs: session handoff for final report assembly
946600d fix: actually commit the build_report changes described in 5a5bb61
5a5bb61 feat: cherry-pick Ben's title page, escaped-pipe fix, and Ch2.4 essay
901f622 feat: condensed Ch1 body section + fixed table column widths
307a6e9 docs: cut both appendices to the professor's 5-page allowance
```

### Ben's branch — what was taken, what was not

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
| `appendix_c_supplementary.md` + `ch8_appendix_pointer.md` | Relocates Ch8.1 and Ch8.4 prose to an appendix. Ch8 is the 20-point chapter, the professor scoped appendices to "additional tables and graphs", and `WORK_DIVISION.md` assigns 8.4 to Noam (already corrected once at `NOAM_TODO.md:413`). `body_ch8.md` keeps all four subsections in the body at 3.52 pp. |
| `appendix_a_code_execution.md`, `appendix_b_environment.md` | `report/appendix_a_execution.md` already covers both, with **exact** library versions where his gives `>=` bounds. His also credits imbalanced-learn for SMOTE, which this project does not use. |
| His Ch4 and Ch6 edits | Ours are supersets. His Ch4 is gain-only top-5; ours has the three-view consensus table plus the no-leakage statement. |
| His `BODY_FILES` / `stop_before` scheme | Truncates Ch6 at `"## 6.3 Explicit"`, silently dropping a graded rubric item. |
| His auto-caption machinery | Keys captions on header substrings; our Ch4 header contains "What it measures", so it would stamp our 8-row consensus table with a caption written for a 5-row gain table. |
| `ch6_2_rf_if.md`, `ch7_2_class_imbalance.md` | Duplicate `ch6_rf_if_justification.md` and `ch7_2_imbalance_validation.md`. **But his are condensed and ours are long** — given the page squeeze, **his may be the better body versions.** Check them first when writing Ch6 and Ch7. |

**Noam said he would tell Ben himself.** Confirm that happened, or Ben will
rebuild Appendix C.

---

## 4. Where the page budget actually stands

Measured with the Word harness (§10), never estimated. **Re-measured after the
column-width pass, so these supersede every earlier figure.**

| Section | rubric pts | measured pp | words | w/p | state |
|---|---:|---:|---:|---:|---|
| `exec_summary.md` | 5 | 1.26 | 527 | 418 | done |
| `body_ch1.md` | 15 | 5.74 | 3060 | 533 | done, **still the biggest cut target** |
| `body_ch3.md` | 15 | 3.62 | 1442 | 398 | done (`5bdcc6b`) |
| `body_ch8.md` | 20 | 3.36 | 1276 | 380 | done, widths pinned |
| **four sections** | **55 / 110** | **13.98 / 15** | | | |
| Ch2, Ch4, Ch5, Ch6, Ch7, Bonus | **55** | **1.02 left** | | | unwritten |

Appendices A + B measure **4.49 pp** with widths pinned (was 4.97), against the
5-page allowance — **0.51 pp of headroom**.

Two earlier numbers were wrong and are corrected above: `body_ch1.md` measures
**5.74**, not 6.06, and the four-section total is **13.98**, not 14.46.

### Noam's governing decision — follow this

> *"I don't know yet what targets I want per section. Lets start from something
> sensible and if it exceeds (like Ch1 which probably would need to) we will cut
> after finishing the writing."*

**So: write each remaining chapter to a sensible length, then do one deliberate
cutting pass at the end.** Per-chapter targets are an aim, not a gate. Do not
stall a chapter trying to hit a number, and do not re-open this decision — it was
made after a full discussion of the trade-off.

Rough aim for the remaining six: **~1.5–2.0 pp each** (Ch2, Ch4, Ch5, Ch7 carry
10 points each; Ch6 carries 5 and should be the shortest; Bonus is +10 and worth
a real page). That lands the body around **24–26 pp**, needing a **~40–45% cut**.
§5 is how that cut gets paid for.

Figures are **not** extra — embedded figures come out of the same 15 pages.

---

## 5. The cutting playbook — read this before writing more

The endgame is a large cut, and the instinct to solve it by deleting findings is
wrong: **text trimming is the weakest lever available.** Cutting 172 words from
Ch1 moved it 0.24 pages (≈505 words/page). Deleting your way to 15 pages means
deleting roughly half the report's substance.

Use the levers in this order. The first three cost no content at all.

**1. Pin every table's column widths — free, and large. DONE for everything
written so far.**
The `<!-- cols: -->` directive (§10) was worth **−43%** on Ch1's five-column
mapping table (5.19 → 2.98 pp). Without it Word autofits, giving every column
similar width, so each row's height is set by its longest cell while the short
cells sit half empty.
Now applied everywhere: Ch1, Ch3, **`body_ch8.md` (−0.16 pp)** and **both
appendices (−0.48 pp)**. Appendix B is generated, so its seven directives live in
`analysis/appendix_b_tables.py`, not the markdown.
**Every new table written from here on must carry a `<!-- cols: -->` line** —
this is now upkeep, not a pass to run at the end.

**2. Watch words-per-page as the diagnostic.**
Measured densities: prose ≈ **477 w/p**; a well-packed 2-column 8.5 pt table ≈
**545–693 w/p**; an autofit 5-column table with one long text column ≈ **289
w/p**. Any section running *below* 477 is a candidate for losing page to
formatting rather than to content.

All four written sections are now measured (§4): **Ch1 533, exec 418, Ch3 398,
Ch8 380 w/p.** Ch1 is *above* the prose baseline — it is densely packed, so its
6-ish pages are genuinely 3,060 words of content and lever 6 is the only thing
that will move it.

**One caveat, learned here:** Word's word count includes table cells, so a table
of short numeric cells scores low w/p by construction. Ch8 at 380 is four numeric
tables, not sloppy layout, and its widths are already pinned — do not expect
lever 2 to pay there. Ch3 at 398 remains the real candidate.

**3. Convert prose to dense tables.**
Because a packed table beats prose on density, moving argument into tables
*saves* page while often reading better. This is also what the formatting spec
asks for ("tables used wherever they fit").

**4. Delete cross-chapter duplication.**
Real overlap exists and is cheap to remove because the content survives
elsewhere. Known instances: Ch1 §1.3, Ch3 and Ch4 all discuss features — Ch1 owns
the 68→43 funnel and the eight families, Ch3 owns univariate class separation,
Ch4 owns model-derived importance. Appendix B Table B.3 already carries the
funnel; Table B.7 already carries every confusion matrix. **`body_ch3.md` was
written to respect these boundaries — hold the same line in Ch4.**

**5. Move tables (not prose) to Appendix B.**
Legitimate, but headroom is thin: the appendices are at 4.49/5.00 with widths
pinned. And **never move graded prose** — that is the Appendix C mistake (§3).

**6. Delete content — last resort.**
When it comes to this, cut from `body_ch1.md` first. It is 6.06 pp — **42% of the
body for 15 of 110 points** — and it is the one section everyone agrees is over.

---

## 6. The remaining six sections

Naming convention: condensed body sections are `report/body_chN.md`.

**What made Ch3 work, and should be repeated:** the source files were two
separate EDA write-ups, and the chapter did *not* summarise them in sequence. It
found the tension between them — D1 says attacks are longer, D2 says the opposite
— and built the whole chapter on that axis. **Look for the tension in the source
material and make it the spine.** A chapter that merely compresses its sources
reads like notes; a chapter with an argument earns its points.

| Section | pts | sources | the angle |
|---|---:|---|---|
| **Ch7** | 10 | `ch7_sensitivity_findings.md`, `ch7_rf_if_sensitivity_findings.md`, `ch7_2_imbalance_validation.md`, `ch7_pipeline_diagram.md`; **check Ben's condensed `ch7_2_class_imbalance.md`** | **Directly rubric-mandated**: *"Explicit hyperparameter configuration with sensitivity analysis (no library defaults)"*. Show the swept grids, the chosen configs and that the choices are stable rather than lucky. `ch7_pipeline.png` (architecture) belongs here. Ch7.2's measured grouped-hold-out vs ungrouped-CV comparison is the strongest content. |
| **Ch2** | 10 | `ch2_literature_review.md`, `ch2_1_literature_matrix.md`, `ch2_1_shellcore_extraction.md`, `ch2_2_adopt_modify_reject.md`, `ch2_3_comparative_contribution_noam.md`, `ch2_shellcore_matrix_noam.md`, `ch2_4_comparative_essay.md` | Two papers (ShellCore, Trizna/TOPS), a comparison matrix, adopt/modify/reject verdicts, and the comparative essay. Ben's `ch2_4_comparative_essay.md` closes the essay rubric item — keep it. The matrix is table-shaped, so this chapter compresses well. |
| **Ch4** | ~10 | `ch4_ranking_findings.md`, `ch4_ranking_notes.md`, `report/ch4_feature_ranking.csv` | Three-view consensus (gain / permutation / consensus rank) plus the gain-versus-permutation discrepancy analysis and the no-leakage statement. **Must not restate Ch3's effect sizes** — Ch3 is univariate class separation, Ch4 is what the fitted model actually leans on. That distinction *is* the chapter. Figures: `ch4_ranking_dataset{1,2}.png`. |
| **Ch5** | 10 | `ch5_1_unified_schema.md`, `ch5_2_distribution_shift.md`, `ch5_3_scaling_normalisation.md` | Hits two hard rubric requirements: the **strict dataset-dependency rule** (only ingestion is dataset-aware) and **no data leakage** (scaling fit on training folds only). Ch3 §3.5 already sets up §5.3 — pick the thread up rather than re-arguing it. |
| **Ch6** | 5 | `ch6_model_justification.md`, `ch6_rf_if_justification.md`, `ch6_model_justification_ben.md`; **check Ben's condensed `ch6_2_rf_if.md`** | **~4,800 words for 5 points — the worst ratio in the project.** Collapse hard to rubric 6.1/6.2. This is the one chapter where aggressive cutting is obviously correct; target ≤1.0 pp. |
| **Bonus** | +10 | `bonus_b3_findings.md` | Content is finished and needs a body slot. Critical framing from `NOAM_TODO.md:274-276`: the cascade's *headline* is a **negative result** (three single thresholds match or beat it), but the **router works** — an oracle arbitrator on the uncertainty band gives F1 0.9132/0.8849, **+3.7 points** over the best single model on ~5% of traffic. **Score the LLM layer against +3.7, not against zero.** That honesty is worth more than a fake win. |

Ch4's rubric weight was not captured by the original grep of the assignment PDF;
10 is assumed, giving 100 base + 10 bonus. The PDF is at
`docs/Final_Project_AI_Driven_Intrusion_Detection.pdf` if it is worth confirming.

---

## 7. Assembly

1. **Rewire `build_report.py`.** `BODY_FILES` (line 21) still lists the stale
   pre-condensation eight and knows nothing about `body_ch1.md`, `body_ch3.md`,
   `body_ch8.md`, `title_page.md`, `appendix_a_execution.md` or
   `appendix_b_tables.md`. It must read `title_page.md`, `exec_summary.md`,
   `body_ch1.md` … `body_ch8.md`, `bonus_b3_findings.md`, then the two
   appendices. **Remove the `"## 6.3 Explicit"` truncation stop** — it drops a
   graded rubric item. Decide whether Appendix B page-breaks after A or runs on;
   **running on is what makes the two fit in 5 pages.**
   `OUT` is already `Group_209361864_315005066_Report.docx` (line 16).
2. **Embed and caption figures — 33 PNGs in `report/figures/`, currently 0
   embedded and 0 captioned.** The spec requires a descriptive caption on every
   one. Budget ~1.5 pp for ~6. Best candidates: `ch7_pipeline.png` (architecture),
   `ch8_transfer_heatmap.png`, `ch4_ranking_dataset{1,2}.png`,
   `ch3_class_balance.png`. Leave the eight `ch8_confusion_*.png` in the ZIP and
   reference them — Table B.7 already carries every matrix.
3. ~~Apply the `<!-- cols: -->` directives.~~ **Done** — Ch8 and both appendices
   pinned, Appendix B regenerated from the edited
   `analysis/appendix_b_tables.py`, output verified byte-identical to the
   previously validated scratch version. Only *new* tables still need one.
4. **Rebuild the docx and ZIP**, then confirm page counts with the Word harness
   before declaring the budget met.

Steps 2 and 4 depend on frozen text.

---

## 8. AI logs — the policy, and exactly how to satisfy it

**This is a graded deliverable and a disclosure requirement, not paperwork.**

The assignment (`docs/final_project_instructions.txt:34,42`):

> AI Conversation Logs (one .txt or .json file per AI tool used, **full unedited
> conversations**)
>
> you must submit the FULL conversation logs alongside your project… We want to
> estimate how you actually used agentic / LLM-driven development — not just
> whether the final code works. **Submissions with no logs but obvious AI
> fingerprints in the code or report will be treated as undisclosed AI use.**

Project rule, from `ai_logs/README.md`: *truncated, summarized, or curated logs
will be treated as missing.*

**What ships.** `ai_logs/claude_code_log.txt` is the primary submission file —
all sessions from both team members, chronological, under `# Session N`
separators. The per-session `.md` transcripts ship alongside it.

**The export is mechanical.** `ai_logs/export_claude_log.py` pulls verbatim user
and assistant *text* turns from the raw `.jsonl`; tool calls, tool results,
system/harness messages and reminders are excluded **block-level** (kept whole or
dropped whole). No hand-editing is possible or performed.
`ai_logs/rebuild_claude_code_log.py` then regenerates *every* block from the
per-session `.md` files, so the combined `.txt` cannot drift and repeated
rebuilds are idempotent.

**Run this last, immediately before zipping.** The newest session is always
incomplete by construction until the work stops.

⚠️ **There is now a fifth session** (`ee2b076e…`, opened Aug 14) — the final
assembly session. It has **no `.md` export and no README entry yet**, and
`rebuild_claude_code_log.py` only sees files that exist, so **skipping its export
silently ships an incomplete log** against a rubric item that treats missing logs
as undisclosed AI use. Export it as `claude_session_noam4.md` → log **Session
5**, and check `~/.claude/projects/E--lotl-shell-detection/` for any newer
`.jsonl` before the final run.

From the repo root:

```bash
# 0. BEN, on his machine only (the source .jsonl is on his laptop).
#    Needed if he has added AI-assisted work since commit `ebb5f38` (Aug 11).
python ai_logs/export_claude_log.py \
  ~/.claude/projects/-Users-bvolovelsky-Downloads-lotl-shell-detection-new/54d95d87-de6d-4b85-a4e8-3e2373c8e028.jsonl \
  ai_logs/claude_session.md

# 1-3. Noam's three sessions -> log Sessions 2, 3, 4
python ai_logs/export_claude_log.py \
  ~/.claude/projects/E--lotl-shell-detection/c016bad2-2622-4f28-8980-8734f78daa1e.jsonl \
  ai_logs/claude_session_noam.md
python ai_logs/export_claude_log.py \
  ~/.claude/projects/E--lotl-shell-detection/ef85a27d-db27-4746-960f-095b3fd3c864.jsonl \
  ai_logs/claude_session_noam2.md
python ai_logs/export_claude_log.py \
  ~/.claude/projects/E--lotl-shell-detection/c6d78cd0-b917-4879-9d90-753790734957.jsonl \
  ai_logs/claude_session_noam3.md

# 4. NEW — the final-assembly session -> log Session 5.
python ai_logs/export_claude_log.py \
  ~/.claude/projects/E--lotl-shell-detection/ee2b076e-3a93-4533-ba3b-27270b88db69.jsonl \
  ai_logs/claude_session_noam4.md

# 5. Rebuild the combined .txt from all five per-session .md files.
python ai_logs/rebuild_claude_code_log.py
```

**Two confirmed defects in `rebuild_claude_code_log.py` — fix both before the
final run.** Read, not assumed:

1. **`BLOCKS` (line 57) is a hardcoded three-entry list.** It does not glob. A
   `claude_session_noam4.md` sitting in `ai_logs/` would be **silently dropped**
   from `claude_code_log.txt` — no error, no warning, just a missing session in
   the file the rubric grades. A `SESSION5_HEADER` + `BLOCKS` entry is required.
2. **`SESSION4_NOTE` (line 50) still stamps "SESSION STILL IN PROGRESS"** into
   the combined log. Session 4 closed on Aug 14; that banner is now false and
   belongs on Session 5 until its own final export is taken.

Both are one-line edits, but neither announces itself — the script exits 0 either
way.

**Then update `ai_logs/README.md`** — this part is manual and is currently out of
date:

- Refresh the **turn counts** with what the export script prints (Session 4 was
  last recorded at 18/18 and has grown well past that).
- **Remove the "Session 4 is still in progress" warning banner** at the top once
  the final export is taken.
- **Extend the Session 4 summary.** It currently stops at the Aug-13 appendix
  work and does not mention: the Ch1 condensation, the page-budget analysis and
  the `<!-- cols: -->` mechanism, the **cherry-pick** from Ben's `b1e9997` (the
  existing text says "the merge of Ben's branch", which describes the earlier
  Aug-10 merge and is now misleading on its own), `body_ch3.md`, or the final
  assembly.
- **Add a Session 5 entry** for the final-assembly session — the column-width
  pass, the remaining six chapters, the cutting pass, figure embedding, and the
  docx/ZIP build. Without it the README describes four sessions while the log
  contains five.
- The README already carries the honest note that the models were **Claude Opus
  4.8 / Sonnet 4.6** (Ben) and **Claude Fable 5 / Opus 5** (Noam), not the
  "Claude Sonnet" the rubric prompt assumed. Keep it.

**Do not** hand-edit any transcript, and do not tidy the logs. Mistakes,
corrections and dead ends in the conversation are the evidence the graders asked
for.

---

## 9. Compliance and close-out

- [x] ~~Push the branch.~~ In sync with origin as of Aug 14.
- [ ] **Fix the two `rebuild_claude_code_log.py` defects** (§8) — do this *now*,
      not at the end; the fix is independent of when the export runs, and the
      failure mode is silent.
- [ ] **Cross-review Ben's chapters.** `WORK_DIVISION.md` requires Noam to read
      them and flag issues before Aug 14 — i.e. today. Not done.
- [ ] **Confirm Ben was told what was integrated** (§3). Noam took this on.
- [ ] Ben re-exports his AI log if he has worked since `ebb5f38`.
- [ ] **Re-export all AI logs and update `ai_logs/README.md`** (§8) — *last*.
- [ ] Rebuild docx, verify page counts, build ZIP.
- [ ] ZIP filename call (§1) — ship the ID-based name rather than block.

---

## 10. Tooling

### Measuring pages exactly

Microsoft Word COM automation works on this machine, so page counts are exact.
**Always measure; never estimate.** Scratchpad scripts (session-specific path —
recreate if absent):

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

Usage:

```powershell
$env:PYTHONIOENCODING='utf-8'; python <scratch>\measure_pages.py body_ch3.md | Out-Null
& <scratch>\pages.ps1 <scratch>\m_body_ch3.docx
```

### The `<!-- cols: -->` directive

A line like `<!-- cols: 1.30 0.80 1.20 1.15 2.05 -->` immediately before a table
pins its column widths in inches. Usable text width is **6.50 in** — make the
numbers sum to that. Applies to the next table only; a blank line between
directive and table is harmless. See §5 lever 1 for why it matters.

### Escaped pipes in tables

`parse_table_row` splits on **unescaped** pipes only, so a literal shell pipe
inside a cell must be written `\|`. It is unescaped again for display.

---

## 11. Canonical numbers — read these, never re-derive

Verified against `results/summary.json` and the shipped result files. **Do not
transcribe metrics from prose; read them from the JSON.**

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

Baseline TF-IDF + LR: **0.8975 / 0.8824**. Scored over **all** target rows rather
than the held-out split, so it is indicative and **not** directly commensurable —
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
class.** Any sentence about "the honeypot corpus" must be scoped to Dataset 2.

Class ratio 1:3, so the **do-nothing F1 floor is 0.400**. Split is 80/20
**grouped by command shape**, zero groups straddling. CV is
`StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)` — stratified but
**ungrouped**. **SMOTE is not used**; imbalance is cost-sensitive only.

### EDA headlines (from `body_ch3.md`, both verified)

Length-alone probe: **AUC 0.611 on D1, 0.430 on D2** — below chance in the
direction that worked on D1. Three features invert sign across corpora
(`len_chars` +0.247/−0.171, `n_quotes` +0.081/−0.112, `n_flags` +0.051/−0.125);
`digit_ratio` is stable (+0.238/+0.234); `n_pipes` and `head_is_lotl` lean benign
on both. D1 separates 41/43 features at p<0.05, D2 only 35/43. Redundancy
threshold is the audit's **|ρ| > 0.9** (`ch3_feature_decisions.md:116`), and
exactly one pair reaches it.

### Code facts

- **43 engineered features**, canonical list in `src.features.FEATURE_NAMES`.
- `MODEL_BUILDERS` keys: `cnn1d`, `isolation_forest`, `random_forest`, `xgboost`,
  `xgboost_hybrid`. **`cnn` and `baseline` are dead keys.** CNN builder is
  `build_cnn1d` (`src/models.py:314`), class `CNN1DClassifier` (`:217`).
- `src/ingestion.py` exposes `available_datasets()`, `_read(csv_name)` and
  **`load(dataset) -> (train_df, test_df)`**. There is no `load_dataset`.
- Random Forest ships `n_estimators=400, max_depth=24, max_features="sqrt",
  class_weight="balanced_subsample"`; Isolation Forest `n_estimators=300,
  max_samples=0.8, contamination=0.25` (`src/models.py:135-174`).
- ShellCore's full citation: Alasmary et al. (2022), *ShellCore: Automating
  Malicious IoT Software Detection by Using Shell Commands Representation*, IEEE
  Internet of Things Journal 9(4):2485–2496, doi:10.1109/JIOT.2021.3086398,
  preprint arXiv:2103.14221. Prefer the journal venue; `body_ch8.md` currently
  cites only the arXiv number.

---

## 12. Hard constraints — do not violate

- **Never commit `HF_TOKEN`.** The assignment says so explicitly: read it from an
  environment variable or a `.env` file.
- **`docs/refs/shellcore_arxiv_2103.14221.pdf` stays untracked** (arXiv licensing).
- **The `source` column is never a model input.**
- **The strings `dataset1` / `dataset2` are banned in `src/*.py` outside
  `ingestion.py`, even in comments** — enforced by `tests/test_pipeline.py:43-48`.
  `analysis/*.py` is exempt. This is the graded "strict dataset dependency rule".
- **Do not re-run `analysis/ch3_feature_audit.py` to "refresh"
  `report/ch3_feature_decisions.md`.** It overwrites Noam's hand-entered FINAL
  KEEP/KILL verdicts. The audit JSON it consumes is already in
  `results/ch3_feature_audit.json`.
- `report/ch3_eda_findings.md` is Ben's hand-written prose, marked never
  machine-overwritten (see the `analysis/ch3_eda.py` docstring).
- **Never relocate graded prose to an appendix.** The professor scoped appendices
  to "additional tables and graphs".

---

## 13. Suggested order

1. ~~Push, then apply the `<!-- cols: -->` directives.~~ **Done** — branch in
   sync, all widths pinned. The two savings land in *different* budgets: −0.16 pp
   off the 15-page body (Ch8) and −0.48 pp off the 5-page appendix allowance.
   Do not add them together (§4, §5).
2. Write **Ch7 → Ch4 → Ch5 → Ch2 → Ch6 → Bonus**, one at a time, each reviewed by
   Noam before the next. Ch7 first because it is rubric-mandated and its sources
   are the most finished; Ch6 late because it needs the most aggressive
   compression and benefits from knowing how much room is left.
3. Measure every section as it lands; keep a running total against 15.
4. **One cutting pass** using §5, in lever order. Ch1 absorbs the most.
5. Embed and caption the chosen figures; re-measure.
6. Cross-review Ben's chapters.
7. Rebuild docx and ZIP; verify page counts.
8. **Re-export AI logs and update `ai_logs/README.md` — last.** Then submit.
