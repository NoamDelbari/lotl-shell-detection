#!/usr/bin/env python3
"""Extract GTFOBins exploitation command lines -> raw/extracted/gtfobins.cm.

Provenance / history
--------------------
The FIRST version of this extractor read only ``entry["code"]`` for each function
entry and split it on newlines. That dropped two whole classes of genuine command:

  1. CONTEXT OVERRIDES.  A function entry may carry per-context ``code`` overrides
     under ``contexts.<sudo|suid|limited-suid|unprivileged>.code``. The most common
     override is the SUID variant that adds ``-p`` (e.g. ``/bin/sh -p``,
     ``bash -p``, ``git --exec-path=. x -p``). There are 97 such override blocks and
     they were all silently discarded -- ~63 distinct command *shapes* lost.

  2. SENDER / RECEIVER helper commands.  ``download``/``upload`` entries may carry a
     ``sender``/``receiver`` that is a *dict* with its own ``code`` (the attacker's
     listener/server side, e.g. ``nc -l -p 79 </path/to/input-file``,
     ``curl -X PUT victim.com/... --data-binary @...``, ``atftpd ... .``). When it is
     merely a *string* (``http-server``, ``tcp-client``, ...) it is a reference to a
     shared helper, not a command, and is correctly ignored.

This version therefore collects EVERY ``code`` field anywhere under ``functions``
(recursively), which captures base, context-override and sender/receiver code alike
with no per-key allow-list to fall out of date.

It also fixes a quality bug the naive line-split introduced: several code blocks
build a config/SQL/XML/kubeconfig file with a here-document
(``cat >file <<EOF ... EOF``). Splitting those blocks on newlines emitted the
here-doc BODY as if each data line were a command -- ``- cluster:``, ``- context:``,
``[Definition]``, ``CREATE TABLE x(x TEXT);``, ``EOF`` and so on. Those are data /
YAML keys, not shell commands, and padding the corpus with them is exactly what the
project forbids. The extractor now tracks here-doc state and skips the body and its
terminator, keeping only the real command lines that surround it
(``cat >file <<EOF``, ``nginx -c file``, ``dmsetup ls --exec '/bin/sh -p -s'`` ...).

LABEL INDEPENDENCE
------------------
Nothing here inspects whether a line "looks malicious". A line is emitted iff it is
a syntactically real command line inside a GTFOBins ``code`` block; it is rejected
only for structural reasons (empty, a here-doc data line, or a bare placeholder
token such as ``DATA`` / ``EOF``). No keyword/vocabulary filter is applied. The
label of every row is provenance: "it is a GTFOBins exploitation command".

Runnable
--------
    python 9_extract.py [REPO_OR_GTFOBINS_DIR] [OUTPUT.cm]

  * REPO_OR_GTFOBINS_DIR may be the repo root of
    github.com/GTFOBins/GTFOBins.github.io, its ``_gtfobins`` directory, or any
    parent containing one. If omitted, a few known local checkouts are tried and,
    failing that, the repo is downloaded fresh from GitHub into a temp dir.
  * OUTPUT.cm defaults to ``<repo>/../raw/extracted/gtfobins.cm`` relative to this
    file, i.e. the real vendored extract the build consumes.
"""
import io
import os
import re
import sys
import glob
import tempfile
import urllib.request
import zipfile

import yaml

MASTER_ZIP = ("https://github.com/GTFOBins/GTFOBins.github.io/"
              "archive/refs/heads/master.zip")

# Default output: scripts/raw/extracted/gtfobins.cm (this file lives in extractors/)
DEFAULT_OUT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "raw", "extracted", "gtfobins.cm"))

# Candidate local checkouts to probe before downloading.
LOCAL_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "GTFOBins.github.io-master"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtfobins_repo"),
    r"C:\Users\noham\AppData\Local\Temp\claude\E--ai-malware-and-intrusion"
    r"\d1298c16-943a-4cd0-8be1-f599b3caa5fd\scratchpad\gtfobins_repo",
]


# ---------------------------------------------------------------------------
# locate / fetch the _gtfobins directory of YAML entries
# ---------------------------------------------------------------------------
def find_gtfobins_dir(root: str) -> str | None:
    """Return the _gtfobins directory at/under `root`, or None."""
    if not root or not os.path.exists(root):
        return None
    root = os.path.abspath(root)
    if os.path.basename(root.rstrip("/\\")) == "_gtfobins" and os.path.isdir(root):
        return root
    direct = os.path.join(root, "_gtfobins")
    if os.path.isdir(direct):
        return direct
    for dirpath, dirnames, _ in os.walk(root):
        if "_gtfobins" in dirnames:
            return os.path.join(dirpath, "_gtfobins")
    return None


def download_gtfobins() -> str:
    """Download the repo master.zip and return the extracted _gtfobins dir."""
    print(f"downloading {MASTER_ZIP} ...", flush=True)
    with urllib.request.urlopen(MASTER_ZIP) as resp:  # noqa: S310 (trusted host)
        data = resp.read()
    dest = tempfile.mkdtemp(prefix="gtfobins_")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(dest)
    found = find_gtfobins_dir(dest)
    if not found:
        raise SystemExit("downloaded archive did not contain a _gtfobins directory")
    return found


def resolve_gtfobins_dir(arg: str | None) -> str:
    if arg:
        found = find_gtfobins_dir(arg)
        if found:
            return found
        raise SystemExit(f"no _gtfobins directory found under: {arg}")
    for cand in LOCAL_CANDIDATES:
        found = find_gtfobins_dir(cand)
        if found:
            print(f"using local checkout: {found}", flush=True)
            return found
    return download_gtfobins()


# ---------------------------------------------------------------------------
# YAML parsing
# ---------------------------------------------------------------------------
def load_functions(text: str):
    """Parse a GTFOBins page and return its `functions` mapping (or None).

    The pages are Jekyll front-matter documents: the whole file is one YAML
    document delimited by a leading `---` and a trailing `...`, so a plain
    safe_load works. A stripped fallback is kept for robustness.
    """
    try:
        doc = yaml.safe_load(text)
    except Exception:
        doc = None
    if not isinstance(doc, dict):
        body = text
        if body.startswith("---"):
            body = body[3:]
        m = re.search(r"\n(?:\.\.\.|---)\s*$", body)
        if m:
            body = body[:m.start()]
        try:
            doc = yaml.safe_load(body)
        except Exception:
            return None
    if not isinstance(doc, dict):
        return None
    funcs = doc.get("functions")
    return funcs if isinstance(funcs, dict) else None


def collect_code_blocks(funcs) -> list[str]:
    """Every `code` string anywhere under `functions`, in document order.

    Recursion means base code, context overrides and sender/receiver dict code
    are all captured, while string-valued sender/receiver references
    (`http-server`, `tcp-client`) are ignored -- they are not `code` fields.
    """
    out: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "code" and isinstance(v, str):
                    out.append(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(funcs)
    return out


# ---------------------------------------------------------------------------
# split a code block into COMMAND lines (skipping here-document bodies)
# ---------------------------------------------------------------------------
# A here-doc opens with `<<WORD`, `<< WORD`, `<<-WORD` or `<<'WORD'`/`<<"WORD"`.
# The line that opens it IS a command (e.g. `cat >file <<EOF`) and is kept; the
# following lines up to and including the terminator (WORD alone on a line, with
# leading whitespace tolerated) are the body -- data, not commands -- and are
# skipped. This is pure shell syntax; it never inspects what the data says.
HEREDOC_OPEN = re.compile(r"<<-?\s*([\"']?)([A-Za-z_][A-Za-z0-9_]*)\1")

# A bare GTFOBins placeholder token (e.g. DATA, EOF, LFILE) is a stand-in, not a
# command line. Structural, content-blind.
PLACEHOLDER_ONLY = re.compile(r"^[A-Z][A-Z0-9_]*$")


def command_lines(code: str) -> list[str]:
    lines = code.splitlines()
    out: list[str] = []
    delim: str | None = None
    for line in lines:
        if delim is not None:                    # inside a here-doc body
            if line.strip() == delim:            # terminator -> body ends
                delim = None
            continue                             # skip body + terminator
        stripped = line.strip()
        if not stripped:
            continue
        if PLACEHOLDER_ONLY.match(stripped):     # bare placeholder, not a command
            # (also catches a stray terminator if a block's here-doc was malformed)
            continue
        out.append(stripped)
        m = HEREDOC_OPEN.search(line)
        if m:
            delim = m.group(2)
    return out


def normalize_ws(s: str) -> str:
    return re.sub(r"[ \t]+", " ", s).strip()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    out_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT

    base = resolve_gtfobins_dir(arg)
    files = sorted(glob.glob(os.path.join(base, "*")))
    print(f"_gtfobins directory: {base}")
    print(f"binary YAML files:   {len(files)}")

    n_blocks = 0
    n_files_ok = 0
    n_files_nofunc = 0
    seen: set[str] = set()
    ordered: list[str] = []

    for fp in files:
        try:
            text = open(fp, encoding="utf-8").read()
        except OSError:
            continue
        funcs = load_functions(text)
        if not funcs:
            n_files_nofunc += 1
            continue
        n_files_ok += 1
        for code in collect_code_blocks(funcs):
            n_blocks += 1
            for line in command_lines(code):
                cmd = normalize_ws(line)
                if not cmd or cmd in seen:
                    continue
                seen.add(cmd)
                ordered.append(cmd)

    print(f"files with functions:        {n_files_ok}")
    print(f"files without functions:     {n_files_nofunc}")
    print(f"code blocks (recursive):     {n_blocks}")
    print(f"distinct command lines:      {len(ordered)}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(ordered) + "\n")
    print(f"wrote -> {out_path}")


if __name__ == "__main__":
    main()
