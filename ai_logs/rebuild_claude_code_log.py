"""
rebuild_claude_code_log.py -- reassemble the combined submission log.

`claude_code_log.txt` is the assignment-required single .txt containing every
session from both team members in chronological order, separated by
`# Session N` headers. This script rebuilds it mechanically so it can never
drift from the per-session transcripts:

  * Ben's Session 1 block is regenerated from `claude_session.md` (the exporter
    output), so the combined log always reflects the latest full re-export;
  * Noam's blocks are re-emitted verbatim from the `.md` files produced by
    export_claude_log.py, using the separator convention already in the file:

        <previous block, ending in a single newline>
        <blank line>
        ---
        <blank line>
        # Session N -- <label>
        <blank line>
        [*italic metadata line*, then two blank lines]
        <verbatim session .md, trailing blank line collapsed>

Registering a new session is manual -- add a header and a BLOCKS entry -- so the
script cross-checks BLOCKS against the transcripts actually on disk and refuses
to run if one is unregistered. It also prints, after the write, every reason the
log is not yet submittable: blocks still marked as mid-session snapshots, and
registered sessions whose export has not been taken.

Usage (run after re-exporting the session .md files; see README.md):
    python ai_logs/rebuild_claude_code_log.py
"""
from pathlib import Path

AI = Path(__file__).resolve().parent
LOG = AI / "claude_code_log.txt"
CLAUDE_SESSION = AI / "claude_session.md"  # Ben's re-exported transcript

SESSION1_HEADER = (
    "# Session 1 -- Ben: dataset card, pipeline, features, models, evaluation, "
    "ensemble, LLM triage & report sections (Aug 7-8, 2026, Claude Opus 4.8)"
)
SESSION2_HEADER = (
    "# Session 2 -- Noam: Ch3 featurize() redesign & joint feature verdicts "
    "(Aug 8-9, 2026, Claude Fable 5)"
)
SESSION3_HEADER = (
    "# Session 3 -- Noam: Ch7 RF/IF sensitivity sweeps, Ch3 EDA rebuild & Ch6 "
    "RF/IF justification (Aug 9-10, 2026, Claude Fable 5)"
)
SESSION4_HEADER = (
    "# Session 4 -- Noam: Ch1/Ch2/Ch5 rubric splits, Ch8.1/8.3/8.4 forensics, "
    "executive summary, the Aug-10 merge of Ben's branch, the Ch4/Ch7/Ch8.1 "
    "rewrite against live artefacts, the Bonus B.3 reproducibility repair, the "
    "appendices, the cherry-pick from Ben's b1e9997 and the condensed Ch1/Ch3 "
    "body sections (Aug 10-14, 2026, Claude Opus 5)"
)
SESSION5_HEADER = (
    "# Session 5 -- Noam: final report assembly -- table column-width pass, the "
    "remaining body chapters, the cutting pass to the 15+5 page budget, figure "
    "embedding, the non-owner cross-review of all ten body sections and the "
    "docx/ZIP build (Aug 14, 2026, Claude Opus 5)"
)

SNAPSHOT_NOTE = (
    "*SESSION STILL IN PROGRESS at export time -- this block is a snapshot; "
    "re-run ai_logs/export_claude_log.py and this rebuild immediately before "
    "submission (see ai_logs/README.md).*"
)

# Sessions whose .md is a mid-session snapshot rather than a final export.
#
# Session 4 was in here on evidence, not caution: claude_session_noam3.md had
# been written 2026-08-13 09:50 while its .jsonl kept growing until 2026-08-14
# 00:06. That session is now closed and re-exported in full (18 -> 30 turns), so
# the set is empty and no block carries the re-export note.
#
# KEEP IT EMPTY unless a session is genuinely re-openable. The note it drives is
# a disclosure statement about completeness, so it has to be true at submission
# time -- in both directions.
IN_PROGRESS = set()

# The last session cannot contain its own ending. Session 5 exported itself from
# inside itself, so its transcript necessarily stops at the export command and
# the short wrap-up after it is absent. That is a permanent, unfixable property
# of any final session -- re-exporting only moves the cut later -- so it gets a
# precise disclosure instead of the "re-export before submitting" note above,
# and it is deliberately NOT a `NOT FINAL` condition.
TAIL_NOTE = (
    "*This session exported itself, so the transcript below necessarily stops "
    "at the export command. What happened afterwards and is therefore absent: "
    "this export, the rebuild of ai_logs/claude_code_log.txt, the turn-count "
    "refresh in ai_logs/README.md, the submission ZIP build and the final "
    "commit. Nothing else about the session is omitted.*"
)
SELF_EXPORTED = {5}

# (session number, header, transcript produced by the exporter)
BLOCKS = [
    (2, SESSION2_HEADER, AI / "claude_session_noam.md"),
    (3, SESSION3_HEADER, AI / "claude_session_noam2.md"),
    (4, SESSION4_HEADER, AI / "claude_session_noam3.md"),
    (5, SESSION5_HEADER, AI / "claude_session_noam4.md"),
]


def check_registration() -> None:
    """Refuse to write a log that silently omits an exported session.

    BLOCKS is hand-maintained, so a newly exported transcript is easy to forget
    -- and a forgotten one used to vanish from claude_code_log.txt with no error
    and a zero exit code. The assignment treats a missing log as undisclosed AI
    use, which is too expensive a failure to leave silent.
    """
    registered = {CLAUDE_SESSION} | {md for _, _, md in BLOCKS}
    stray = sorted(p.name for p in AI.glob("claude_session*.md")
                   if p not in registered)
    if stray:
        raise SystemExit(
            "ERROR: these transcripts exist but are not registered in BLOCKS, "
            f"so the combined log would omit them: {', '.join(stray)}. "
            "Add a header and a BLOCKS entry for each, then re-run."
        )


def main() -> None:
    check_registration()

    # Ben's Session 1 block is regenerated from the re-exported transcript so
    # the combined log never drifts from claude_session.md. (It used to be
    # copied byte-for-byte out of the existing claude_code_log.txt, which meant
    # a fresh Ben re-export never actually reached this file.) The exporter
    # writes each turn ending in a blank line, so the block already ends "\n\n".
    ben_md = CLAUDE_SESSION.read_text(encoding="utf-8")
    ben = SESSION1_HEADER + "\n\n" + ben_md.rstrip("\n") + "\n\n"
    assert ben.endswith("\n\n"), repr(ben[-10:])

    parts = [ben]
    included, missing = [1], []
    for n, header, md in BLOCKS:
        # A registered-but-unexported session is expected mid-project (the
        # current session cannot export itself until it ends), so this is a
        # loud skip rather than an error -- but it is never silent.
        if not md.exists():
            missing.append((n, md.name))
            continue
        parts.append("---\n\n" + header + "\n\n")
        if n in IN_PROGRESS:
            parts.append(SNAPSHOT_NOTE + "\n\n\n")
        elif n in SELF_EXPORTED:
            parts.append(TAIL_NOTE + "\n\n\n")
        parts.append(md.read_text(encoding="utf-8").rstrip("\n") + "\n")
        parts.append("\n")  # blank line before the next `---` separator
        included.append(n)
    out = "".join(parts).rstrip("\n") + "\n"

    # open(..., newline="\n") rather than Path.write_text(newline=...), which
    # only accepts the newline kwarg on Python 3.10+ (this repo runs on 3.9).
    with open(LOG, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    print(f"wrote {LOG}: {out.count(chr(10))} lines, "
          f"{len(out.encode('utf-8'))} bytes")
    print("  sessions included: "
          + ", ".join(str(n) for n in sorted(included)))

    # Everything below is a reason this log is not submittable yet. Printed last
    # so it is the final thing on screen.
    snapshots = sorted(n for n in included if n in IN_PROGRESS)
    if snapshots:
        print("  NOT FINAL -- snapshot blocks, re-export before zipping: "
              + ", ".join(f"Session {n}" for n in snapshots))
    for n, name in missing:
        print(f"  NOT FINAL -- Session {n} OMITTED: {name} has not been "
              "exported yet")


if __name__ == "__main__":
    main()
