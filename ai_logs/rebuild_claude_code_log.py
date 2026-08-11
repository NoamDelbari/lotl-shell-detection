"""
rebuild_claude_code_log.py -- reassemble the combined submission log.

`claude_code_log.txt` is the assignment-required single .txt containing every
session from both team members in chronological order, separated by
`# Session N` headers. This script rebuilds it mechanically so it can never
drift from the per-session transcripts:

  * everything before the `# Session 2` header (Ben's Session 1 and Session 1
    continued) is copied out of the existing file **byte for byte** -- Ben's
    blocks are never regenerated or edited here;
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

Usage (run after re-exporting both Noam sessions; see README.md):
    python ai_logs/rebuild_claude_code_log.py
"""
from pathlib import Path

AI = Path(__file__).resolve().parent
LOG = AI / "claude_code_log.txt"

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
    old = LOG.read_text(encoding="utf-8")
    cut = old.index("---\n\n" + SESSION2_HEADER)
    ben = old[:cut]  # verbatim; ends with the blank line before the separator
    assert ben.endswith("\n\n"), repr(ben[-10:])

    # Ben's opening block predates the `# Session N` convention and carries no
    # header, which makes the combined log inconsistent with what README.md
    # promises. Prepend one; the guard keeps this idempotent across reruns
    # (the header is read back as part of `ben` next time). Ben's transcript
    # text itself is still copied byte for byte.
    if not ben.startswith(SESSION1_HEADER):
        ben = SESSION1_HEADER + "\n\n" + ben

    parts = [ben]
    for header, note, md in BLOCKS:
        parts.append("---\n\n" + header + "\n\n")
        if note:
            parts.append(note + "\n\n\n")
        parts.append(md.read_text(encoding="utf-8").rstrip("\n") + "\n")
        parts.append("\n")  # blank line before the next `---` separator
    out = "".join(parts).rstrip("\n") + "\n"

    LOG.write_text(out, encoding="utf-8", newline="\n")
    print(f"wrote {LOG}: {out.count(chr(10))} lines, "
          f"{len(out.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
