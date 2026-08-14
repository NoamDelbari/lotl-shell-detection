# Ben — status update and handover (Aug 14, freeze day)

From Noam. Everything below is checked against the repo, not from memory.

**Branch to look at: `noam/ch7-rf-if-sweeps`.** That is where the report lives now.
`main` is behind it and the last `.docx` I pushed is defective — see "Don't use the
shipped docx" below.

---

## 1. What I need from you (only three things)

**a. Re-export your AI log — only you can do this.**
Your transcript was last exported at `ebb5f38` (Aug 11). If you have done *any*
AI-assisted work since then, the log is incomplete, and the assignment is blunt
about that: *"Submissions with no logs but obvious AI fingerprints in the code or
report will be treated as undisclosed AI use."* Truncated counts as missing.

```bash
python ai_logs/export_claude_log.py \
  ~/.claude/projects/-Users-bvolovelsky-Downloads-lotl-shell-detection-new/54d95d87-de6d-4b85-a4e8-3e2373c8e028.jsonl \
  ai_logs/claude_session.md
```

Then commit `ai_logs/claude_session.md` and tell me. **Nothing else to do by hand** —
the combined `claude_code_log.txt` is rebuilt from that file automatically now, so
your re-export propagates on its own. Don't edit the transcript: mistakes, dead
ends and corrections are exactly what the graders asked to see.

If you used any AI tool *other* than Claude Code, it needs its own file in
`ai_logs/` — one file per tool. Tell me if so.

**b. Your final full-report review pass** (`WORK_DIVISION.md` packaging row).
I'll ping you when the rebuilt docx lands tonight — review that, not the current
one. If you'd rather start now, read `report/body_ch1.md`, `body_ch3.md`,
`body_ch8.md` and `exec_summary.md`; those four are final.

**c. Don't rebuild Appendix C.** I dropped it deliberately — reasoning in §3
below. If you disagree, say so tonight rather than re-adding it.

That's it. Everything else on the list is mine.

---

## 2. What I took from your branch

Your `ben/pipeline-models-ch3-8` is at `b1e9997`. You branched from `a33d72f`
without visibility into my then-unpushed commits — my fault, I was sitting on
work — so a lot of your branch independently re-solves problems that were
already closed on my side. Rather than merge and create duplicates, **I
cherry-picked four things** (commits `5a5bb61`, `946600d`):

- **Your title page** — both IDs, both emails, the real course name. Better than
  mine; it's what ships.
- **The escaped-pipe fix in `parse_table_row`** — real bug, kept.
- **`report/ch2_4_comparative_essay.md`** — this closes the Ch2 comparative-essay
  rubric item. It goes into the body as-is.
- **The `Group_<id1>_<id2>_*` artefact renames** — and independently we both read
  the ZIP-name template the same way, which is the best evidence we have that
  it's right.

An earlier merge of your branch at `a33d72f` (commit `c9288da`, Aug 10) already
brought in the Ollama bonus run, the docx builder and the ZIP step. Those are all
still in.

---

## 3. What I declined, and why

Not a quality judgement on any of these — mostly they collided with something
already in place, or with a constraint you couldn't have known about.

| Your change | Why it didn't go in |
|---|---|
| `appendix_c_supplementary.md` + `ch8_appendix_pointer.md` | This moves Ch8.1 forensics and Ch8.4 cascade prose into an appendix. Ch8 is the 20-point chapter, and the professor's email scopes the 5 appendix pages to *"additional tables and graphs"* — graded prose parked there risks not being read at all. `body_ch8.md` keeps all four subsections in the body and still measures 3.36 pp. |
| `appendix_a_code_execution.md`, `appendix_b_environment.md` | `report/appendix_a_execution.md` already covers both, and it lists **exact** pinned versions where yours gives `>=` bounds. Yours also credits imbalanced-learn for SMOTE — we don't use it, so that would have been a factual error in a graded appendix. |
| Your Ch4 and Ch6 edits | Mine are supersets. Your Ch4 is gain-only top-5; mine has the three-view consensus table plus the explicit no-leakage statement the rubric wants. |
| Your `BODY_FILES` / `stop_before` scheme | It truncates Ch6 at `"## 6.3 Explicit"`, which silently drops a graded rubric item from the output. I'm rewiring the builder anyway. |
| Your auto-caption machinery | It keys captions on header substrings. My Ch4 header contains "What it measures", so it stamps the 8-row consensus table with a caption written for a 5-row gain table. Captions are hand-written instead. |
| Your figures (`ch4_feature_importance_*`, `ch7_sensitivity_{cnn,xgboost}`, `ch8_errors_by_source_*`) | Mine cover the same ground per-model *and* per-dataset (`ch4_ranking_dataset{1,2}`, `ch7_sensitivity_<model>_dataset{1,2}`). `ch8_errors_by_source_*` is the one genuinely new view, but Table 8.1 already carries that breakdown numerically and page budget is the binding constraint. |

**Two of yours I may still take.** Your `ch6_2_rf_if.md` and
`ch7_2_class_imbalance.md` duplicate my `ch6_rf_if_justification.md` and
`ch7_2_imbalance_validation.md` — **but yours are condensed and mine are long**,
and we are badly over on pages. I'm checking both when I write Ch6 and Ch7
tonight, and if yours read better at length, yours ship.

---

## 4. Where the report actually stands

The professor ruled by email: **15 body pages + 5 appendix pages**, the latter
scoped to additional tables and graphs.

Measured with Word (real page counts, not estimates):

| Section | pts | pp | state |
|---|---:|---:|---|
| Executive summary | 5 | 1.26 | done |
| Ch1 Threat & telemetry | 15 | 5.74 | done — biggest cut target |
| Ch3 EDA | 15 | 3.62 | done |
| Ch8 Error analysis | 20 | 3.36 | done |
| **subtotal** | **55 / 110** | **13.98 / 15** | |
| Ch2, Ch4, Ch5, Ch6, Ch7, Bonus | **55** | **1.02 left** | not yet written |

So the remaining half of the points has one page of room. That's the real
problem, and it's a formatting problem before it's a content problem — pinning
table column widths alone bought back 43% of one five-column table's height.
There will be one deliberate cutting pass once everything is written; Ch1 absorbs
most of it.

Appendices A + B measure 4.49 / 5.00.

**Don't use the shipped docx.** `Group_209361864_315005066_Report.docx` (built
Aug 13) is broken, not just stale: the builder's `APPENDIX_FILES` list points at
`ch2_literature_review.md`, a *body* chapter, so the file **prints Chapter 2
twice** and contains **neither real appendix**. I'm rewiring the builder tonight.

---

## 5. What I'm doing tonight (all mine, no action for you)

1. Write the six remaining sections — Ch7, Ch4, Ch5, Ch2, Ch6, Bonus.
2. Rewire `build_report.py` (correct body list, real appendices, drop the Ch6
   truncation stop, run Appendix B on after A).
3. Add image support to the builder — it currently has **none**, no `add_picture`
   at all — then embed and caption ~6 figures.
4. One cutting pass to 15 pages.
5. Rebuild docx, verify page counts with Word, build the ZIP.
6. Final AI-log pass, last thing before zipping: re-export every session, refresh
   the turn counts, rebuild the combined log until it reports no `NOT FINAL`
   lines.

**Framing to be aware of, since it's your bonus half too:** Ch8.4's headline is a
*negative* result — the three-stage cascade is the weakest configuration
buildable from its own components, and a single threshold on stage 2 matches or
beats it. But the router works: an oracle arbitrator on the same uncertainty band
hits F1 0.9132 / 0.8849, **+3.7 points** over the best single model. Your B.3 LLM
layer is scored against that +3.7, not against zero. Reporting it that way is
worth more than dressing it up as a win.

---

## 6. Constraints in force (so nothing gets undone by accident)

- **Never commit `HF_TOKEN`** — environment variable or `.env` only.
- `docs/refs/shellcore_arxiv_2103.14221.pdf` stays **untracked** (arXiv licensing).
- The `source` column is **never** a model input.
- The strings `dataset1` / `dataset2` are banned in `src/*.py` outside
  `ingestion.py`, even in comments — enforced by `tests/test_pipeline.py:43-48`.
  This is the graded strict-dataset-dependency rule. `analysis/*.py` is exempt.
- **Do not re-run `analysis/ch3_feature_audit.py`** to "refresh"
  `report/ch3_feature_decisions.md` — it overwrites the hand-entered FINAL
  KEEP/KILL verdicts.
- `report/ch3_eda_findings.md` is your hand-written prose and is never
  machine-overwritten.
- Never relocate graded prose to an appendix (see §3).
