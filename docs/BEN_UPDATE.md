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
**The rebuilt docx is in the repo root and is the one to read** —
`Group_209361864_315005066_Report.docx`, 21 pages, all sections present. Every
body section is now final; nothing is still being written. I have already done
the non-owner read of all ten body sections and fixed what it turned up (§4).

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
| `appendix_c_supplementary.md` + `ch8_appendix_pointer.md` | This moves Ch8.1 forensics and Ch8.4 cascade prose into an appendix. Ch8 is the 20-point chapter, and the professor's email scopes the 5 appendix pages to *"additional tables and graphs"* — graded prose parked there risks not being read at all. `body_ch8.md` keeps all four subsections in the body and still fits pages 13–14. |
| `appendix_a_code_execution.md`, `appendix_b_environment.md` | `report/appendix_a_execution.md` already covers both, and it lists **exact** pinned versions where yours gives `>=` bounds. Yours also credits imbalanced-learn for SMOTE — we don't use it, so that would have been a factual error in a graded appendix. |
| Your Ch4 and Ch6 edits | Mine are supersets. Your Ch4 is gain-only top-5; mine has the three-view consensus table plus the explicit no-leakage statement the rubric wants. |
| Your `BODY_FILES` / `stop_before` scheme | It truncates Ch6 at `"## 6.3 Explicit"`, which silently drops a graded rubric item from the output. I'm rewiring the builder anyway. |
| Your auto-caption machinery | It keys captions on header substrings. My Ch4 header contains "What it measures", so it stamps the 8-row consensus table with a caption written for a 5-row gain table. Captions are hand-written instead. |
| Your figures (`ch4_feature_importance_*`, `ch7_sensitivity_{cnn,xgboost}`, `ch8_errors_by_source_*`) | Mine cover the same ground per-model *and* per-dataset (`ch4_ranking_dataset{1,2}`, `ch7_sensitivity_<model>_dataset{1,2}`). `ch8_errors_by_source_*` is the one genuinely new view, but Table 8.1 already carries that breakdown numerically and page budget is the binding constraint. |

**Resolved: the two I said I might still take.** Your `ch6_2_rf_if.md` and
`ch7_2_class_imbalance.md` duplicate my `ch6_rf_if_justification.md` and
`ch7_2_imbalance_validation.md`. At the length the page budget actually allows,
neither source file ships verbatim — `body_ch6.md` and `body_ch7.md` are written
down to one and two pages respectively, drawing on both. Your framing of the
imbalance remedy as a *trade* rather than a gain is what §7.2 argues.

---

## 4. Where the report actually stands

The professor ruled by email: **15 body pages + 5 appendix pages**, the latter
scoped to additional tables and graphs.

**Both allowances are met exactly.** Measured with Word COM against the built
docx — real page numbers, not estimates:

```
BODY  = pages 2..16  => 15 pages (allowance 15)
APPX  = pages 17..21 => 5 pages  (allowance 5)
```

Where each section lands (page 1 is the title page):

| Section | pts | starts on | runs to |
|---|---:|---:|---:|
| Executive summary | 5 | 2 | 2 |
| Ch1 Threat & telemetry | 15 | 2 | 4 |
| Ch2 Literature review | 10 | 5 | 5 |
| Ch3 EDA | 15 | 6 | 7 |
| Ch4 Feature ranking | 10 | 8 | 9 |
| Ch5 Data harmonization | 10 | 10 | 10 |
| Ch6 Model selection | 5 | 11 | 11 |
| Ch7 Pipeline & sensitivity | 10 | 12 | 12 |
| Ch8 Error analysis | 20 | 13 | 14 |
| Bonus — LLM triage | 10 | 15 | 16 |
| Appendix A — execution | — | 17 | 17 |
| Appendix B — tables + EDA figures | — | 18 | 21 |

Getting from 21.86 pages to 15 was mostly typography, not deletion: 0.8 in
margins, paragraph `space_after` 6 → 3 pt (0.23 pp), zero intra-cell paragraph
spacing in tables (0.45 pp), and pinned column widths on every table. Roughly
2,300 words of prose were cut on top of that, none of it a rubric item.

**Appendix B now ends with B.5, three EDA figures** — both command-length
histograms and the D1 correlation heat-map. Ch3 was carrying 15 points with no
visualisation at all; the figures went to the appendix because the professor
scoped it to "additional tables and graphs", and **no prose moved with them**.

**The cross-review read turned up two real errors, both now fixed:**

- §8.2 said every supervised model loses "a third to two-thirds" of its F1 under
  transfer. The true range is a third to **four-fifths** — Random Forest D2→D1
  goes 0.753 → 0.143, an 81% loss. Understating our own worst case.
- §3.4 said `len_chars` ~ `len_tokens` "crosses the audit's |ρ| > 0.9 threshold"
  at 0.897 / 0.906. Two problems: 0.897 does not cross 0.9, and those are
  *Pearson* numbers from the EDA while the audit's line is **Spearman** — on
  which `results/ch3_feature_audit.json` reports `cluster_edges: []`, i.e. no
  pair among the shipped 43 crosses it at all. Rewritten to say that.

Everything else I checked traced back to a result file: every metric in the
Ch7/Ch8/Bonus tables against `results/*.json`, and every `file.py:line`
citation in Ch5 against the actual source.

**The shipped docx is good now.** The old warning here was about the Aug 13
build, whose `APPENDIX_FILES` pointed at a *body* chapter so it printed Chapter 2
twice and contained neither appendix. That was fixed when the builder was
rewired; the current file has both appendices and no duplication.

---

## 5. Where the work stands (all mine, no action for you)

Done:

1. ✅ All six remaining sections written — Ch7, Ch4, Ch5, Ch2, Ch6, Bonus.
2. ✅ `build_report.py` rewired: correct body list, both real appendices, Ch6
   truncation stop removed, Appendix B runs on after A.
3. ✅ Image support added to the builder (it had **no** `add_picture` at all),
   plus a `<!-- fig-width: N.N -->` directive; three figures embedded in B.5.
4. ✅ Cutting pass complete — 21.86 pp → 15.00 pp body, 5.00 pp appendix.
5. ✅ Docx rebuilt and page counts verified with Word COM (§4).
6. ✅ Non-owner cross-review of all ten body sections, two errors fixed (§4).

Still to run, in this order:

7. Final AI-log pass — re-export every session including the one still open,
   refresh the turn counts, clear the `IN_PROGRESS` set, rebuild the combined log
   until it reports no `NOT FINAL` lines.
8. Build the ZIP, commit, push. Your re-export (§1a) can land any time before
   this and I will rebuild.

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
  `ingestion.py`, even in comments — enforced by `tests/test_pipeline.py:43-50`.
  This is the graded strict-dataset-dependency rule. `analysis/*.py` is exempt.
- **Do not re-run `analysis/ch3_feature_audit.py`** to "refresh"
  `report/ch3_feature_decisions.md` — it overwrites the hand-entered FINAL
  KEEP/KILL verdicts.
- `report/ch3_eda_findings.md` is your hand-written prose and is never
  machine-overwritten.
- Never relocate graded prose to an appendix (see §3).
