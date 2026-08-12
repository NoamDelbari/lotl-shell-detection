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
    "executive summary & Ben merge (Aug 10, 2026, Claude Opus 5)"
)
SESSION4_NOTE = (
    "*SESSION STILL IN PROGRESS at export time -- this block is a snapshot; "
    "re-run ai_logs/export_claude_log.py and this rebuild immediately before "
    "submission (see ai_logs/README.md).*"
)

# (header, optional italic metadata line, transcript produced by the exporter)
BLOCKS = [
    (SESSION2_HEADER, None, AI / "claude_session_noam.md"),
    (SESSION3_HEADER, None, AI / "claude_session_noam2.md"),
    (SESSION4_HEADER, SESSION4_NOTE, AI / "claude_session_noam3.md"),
]


def main() -> None:
    # Ben's Session 1 block is regenerated from the re-exported transcript so
    # the combined log never drifts from claude_session.md. (It used to be
    # copied byte-for-byte out of the existing claude_code_log.txt, which meant
    # a fresh Ben re-export never actually reached this file.) The exporter
    # writes each turn ending in a blank line, so the block already ends "\n\n".
    ben_md = CLAUDE_SESSION.read_text(encoding="utf-8")
    ben = SESSION1_HEADER + "\n\n" + ben_md.rstrip("\n") + "\n\n"
    assert ben.endswith("\n\n"), repr(ben[-10:])

    parts = [ben]
    for header, note, md in BLOCKS:
        parts.append("---\n\n" + header + "\n\n")
        if note:
            parts.append(note + "\n\n\n")
        parts.append(md.read_text(encoding="utf-8").rstrip("\n") + "\n")
        parts.append("\n")  # blank line before the next `---` separator
    out = "".join(parts).rstrip("\n") + "\n"

    # open(..., newline="\n") rather than Path.write_text(newline=...), which
    # only accepts the newline kwarg on Python 3.10+ (this repo runs on 3.9).
    with open(LOG, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    print(f"wrote {LOG}: {out.count(chr(10))} lines, "
          f"{len(out.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
