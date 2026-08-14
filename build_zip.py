"""
build_zip.py  --  assemble the single submission ZIP.

    python build_zip.py

The assignment asks for one ZIP containing the code repository, the report
.docx and the full AI conversation logs. The previously shipped ZIP was built by
hand and drifted: it carried the old `Group_10_Report.docx` name and was missing
`tests/` and `analysis/` entirely. This script removes the hand step.

Design: **the file list comes from `git ls-files`.** That is deliberate, not
convenience -- anything deliberately untracked stays out by construction. In
particular `docs/refs/shellcore_arxiv_2103.14221.pdf` is gitignored because
redistributing it is not ours to grant under the arXiv licence, and a `.env`
holding HF_TOKEN would be untracked for the same class of reason. A glob-based
walk would have swept up both.

**Two tracked things are still held back** (`EXCLUDE`, `EXCLUDE_PREFIXES`), each
for a stated reason rather than by taste:

  * the **datasets** -- `dataset/` (the four derived CSVs) and
    `scripts/raw/extracted/*.cm` (the ~5 MB of downloaded source corpora). The
    assignment asks for the code and a note on how the data was obtained, not
    the data itself; `README.md` documents the one-command rebuild
    (`scripts/build_dataset.py`) that regenerates every excluded file exactly.
  * a handful of **internal working notes** (per-partner TODO/brief/handoff
    files, the `superpowers/` planning scratch, one report notes file). They are
    scaffolding for us, not deliverables, and only clutter a graded submission.

Everything a grader needs to read, run or reproduce the project still ships.

Three gates run before anything is written, because every one of them has a
failure mode that is invisible in the finished ZIP:

  1. required deliverables are present;
  2. no secret material is in any file being shipped;
  3. the .docx is not older than the report sources it was built from.
"""
from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCX = ROOT / "Group_209361864_315005066_Report.docx"
OUT = ROOT / "Group_209361864_315005066_Final_Project.zip"

# Tracked, but deliberately not shipped -- exact paths.
EXCLUDE = {
    # The previous submission ZIP. Including it would nest a copy of an older
    # submission inside the new one.
    "Group_209361864_315005066_Final_Project.zip",
    # A second, longer .docx. The report has a hard 15-page limit, so shipping
    # an alternative full-length build alongside it only invites the grader to
    # mark the wrong file.
    "Group_209361864_315005066_Report_FULL.docx",
    # Internal working notes -- scaffolding, not deliverables.
    "docs/NOAM_TODO.md",
    "docs/WORK_DIVISION.md",
    "docs/NOAM_PROMPTS.md",
    "docs/NOAM_WRITING_BRIEF.md",
    "docs/BEN_UPDATE.md",
    "docs/HANDOFF_FINAL_ASSEMBLY.md",
    "docs/DOCX_ASSEMBLY_BRIEF.md",
    "report/ch4_ranking_notes.md",
}

# Tracked, but not shipped -- whole subtrees, matched by path prefix.
EXCLUDE_PREFIXES = (
    # The datasets. Rebuilt by scripts/build_dataset.py; README documents how.
    "dataset/",
    "scripts/raw/",
    # Planning/spec scratch from the design phase.
    "docs/superpowers/",
)

REQUIRED = [
    "main.py",
    "requirements.txt",
    "README.md",
    "ai_logs/claude_code_log.txt",
]

# Anything that looks like a live credential. HF_TOKEN is the one the assignment
# calls out by name; the generic patterns catch a pasted key of another kind.
SECRET_PATTERNS = [
    re.compile(r"hf_[A-Za-z0-9]{30,}"),           # Hugging Face user token
    re.compile(r"sk-[A-Za-z0-9]{32,}"),           # OpenAI-style key
    re.compile(r"HF_TOKEN\s*=\s*['\"]?hf_[A-Za-z0-9]"),
]

TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".csv", ".yml", ".yaml",
                 ".cfg", ".ini", ".toml", ".sh", ".ps1"}


def is_excluded(path: str) -> bool:
    return path in EXCLUDE or path.startswith(EXCLUDE_PREFIXES)


def tracked_files():
    """Every file git tracks, as repo-relative POSIX paths, minus EXCLUDE(S)."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout.decode("utf-8")
    return sorted(p for p in out.split("\0") if p and not is_excluded(p))


def check_required(names) -> None:
    have = set(names)
    missing = [r for r in REQUIRED if r not in have]
    if not DOCX.exists():
        missing.append(DOCX.name + " (run: python build_report.py)")
    if missing:
        raise SystemExit(
            "ERROR: required deliverables missing from the submission: "
            + ", ".join(missing)
        )


def check_secrets(names) -> None:
    """Refuse to ship a credential.

    Cheap to run, and the failure it prevents -- publishing a live token to a
    graded submission that gets read by other people -- is not recoverable by
    editing the ZIP afterwards.
    """
    hits = []
    for name in names:
        path = ROOT / name
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat in SECRET_PATTERNS:
            m = pat.search(text)
            if m:
                hits.append(f"{name}: {m.group(0)[:12]}...")
                break
    if hits:
        raise SystemExit(
            "ERROR: possible credentials in files about to be shipped:\n  "
            + "\n  ".join(hits)
            + "\nRemove them and rebuild. Do not ship this ZIP."
        )


def check_docx_fresh() -> None:
    """Warn loudly if the .docx predates any report source it renders.

    A stale .docx is the single easiest way to submit work that was already
    finished -- the text is in the repo, just not in the file being graded.
    """
    docx_mtime = DOCX.stat().st_mtime
    stale = [p.name for p in sorted((ROOT / "report").glob("*.md"))
             if p.stat().st_mtime > docx_mtime]
    if stale:
        print("  WARNING: these report sources are newer than the .docx:")
        for name in stale:
            print(f"    {name}")
        print("  Re-run `python build_report.py` unless you know why.")


def main() -> None:
    names = tracked_files()
    check_required(names)
    check_secrets(names)
    check_docx_fresh()

    # The built .docx is tracked, so it is already in `names`; guard anyway in
    # case it is ever gitignored.
    entries = list(names)
    if DOCX.name not in entries:
        entries.append(DOCX.name)

    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in entries:
            zf.write(ROOT / name, name)

    size_mb = OUT.stat().st_size / (1024 * 1024)
    print(f"\nWrote {OUT.name}: {len(entries)} files, {size_mb:.1f} MB")
    print("  report:   " + DOCX.name)
    print("  ai logs:  ai_logs/claude_code_log.txt")
    print("  excluded (datasets, rebuildable): " + ", ".join(EXCLUDE_PREFIXES))
    print("  excluded (working notes / duplicates): "
          + ", ".join(sorted(EXCLUDE)))
    print("  untracked files are excluded by construction "
          "(docs/refs/ and any .env stay out)")


if __name__ == "__main__":
    sys.exit(main())
