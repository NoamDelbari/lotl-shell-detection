# -*- coding: utf-8 -*-
"""Extract executable single-line LINUX shell commands from InternalAllTheThings.

Upstream : https://github.com/swisskyrepo/InternalAllTheThings  (commit 5ec9b6a)
Licence  : MIT  (Copyright Swissky; same author/family as PayloadsAllTheThings,
           whose Linux pages now REDIRECT here -- see provenance note below)
Content  : offensive-tradecraft markdown; commands live in ```bash fenced blocks
           of four named cheatsheets (reverse shell, linux privesc, linux
           persistence, network discovery).

PROVENANCE (why not PayloadsAllTheThings): PayloadsAllTheThings' own Linux pages
are now redirect-only tables-of-contents ("Content of this page has been moved to
InternalAllTheThings" + an anchor-link list). Scraping those would be navigation
noise. This extractor pulls the live SUCCESSOR repo where the content was
relocated, so the .cm carries real payloads, not the TOC. The vendored file keeps
its historical name `payloads_all_the_things.cm`; the true upstream is IATT and is
recorded as such in build_dataset.py's SOURCE_META and in DATA_CARD.md.

Selection is by FILE and by FENCE LANGUAGE (```bash only) -- never by a
maliciousness keyword. Placeholders (<LHOST>, <PORT>, ...) are resolved to lab
defaults; any line still holding a placeholder is dropped. No filter inspects a
string for "looking malicious": rejection is purely OS/field/file-based or for
not being a well-formed single-line shell command. The label of the resulting
rows is PROVENANCE ("published in an offensive cheatsheet"), never a function of
the command text.

Usage:
    python 11_extract.py <iatt_repo_dir> [--out PATH]
    python 11_extract.py                 # no arg: shallow-clone IATT to a tempdir

  <iatt_repo_dir> is a checkout of swisskyrepo/InternalAllTheThings (contains
  docs/). Files are read via `git show HEAD:<path>` when the dir is a git repo
  (this bypasses on-access AV locks on the reverse-shell cheatsheet), else from
  disk. --out defaults to the vendored location
  ../raw/extracted/payloads_all_the_things.cm relative to this script.
"""
import os
import re
import sys
import subprocess
import tempfile
import argparse

REPO_URL = "https://github.com/swisskyrepo/InternalAllTheThings.git"

FILES = [
    "docs/cheatsheets/shell-reverse-cheatsheet.md",
    "docs/redteam/escalation/linux-privilege-escalation.md",
    "docs/redteam/persistence/linux-persistence.md",
    "docs/cheatsheets/network-discovery.md",
]


# ---------------------------------------------------------------------------
# read a repo file (git show if a git repo, else from disk)
# ---------------------------------------------------------------------------
def read_file(repo: str, path: str) -> str:
    if os.path.isdir(os.path.join(repo, ".git")):
        out = subprocess.run(["git", "-C", repo, "show", f"HEAD:{path}"],
                             capture_output=True, text=True, encoding="utf-8")
        if out.returncode == 0:
            return out.stdout
        sys.stderr.write(f"git show failed for {path}: {out.stderr[:200]}\n")
    disk = os.path.join(repo, path)
    if os.path.exists(disk):
        with open(disk, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    sys.stderr.write(f"MISSING {path}\n")
    return ""


# ---------------------------------------------------------------------------
# fenced code blocks
# ---------------------------------------------------------------------------
def fences(md):
    """Yield (lang, [lines]) for every ``` fenced block."""
    out, cur, lang, infence = [], [], None, False
    for line in md.splitlines():
        m = re.match(r"^\s*```+\s*([A-Za-z0-9_+-]*)\s*$", line)
        if m:
            if not infence:
                infence, lang, cur = True, m.group(1).lower(), []
            else:
                out.append((lang, cur)); infence = False
            continue
        if infence:
            cur.append(line)
    return out


# ---------------------------------------------------------------------------
# placeholder substitution (community-convention tokens -> lab defaults)
# ---------------------------------------------------------------------------
SUBS = [
    (re.compile(r"<\s*(?:LHOST|RHOST|R?HOST|IP|ATTACKER[-_]?IP|ATTACKING[-_]?IP|"
                r"YOUR[-_]?IP|TARGET[-_]?IP|REMOTE[-_]?HOST|LOCAL[-_]?IP|"
                r"ATTACKER|attacker|listen[-_]?ip|your[-_]?ip|target[-_]?ip|ip)\s*>",
                re.I), "10.10.14.9"),
    (re.compile(r"\{\{?\s*(?:LHOST|IP|RHOST)\s*\}?\}", re.I), "10.10.14.9"),
    (re.compile(r"\$\{?(?:LHOST|IP|RHOST)\}?"), "10.10.14.9"),
    (re.compile(r"\[\s*IP\s*\]", re.I), "10.10.14.9"),
    (re.compile(r"\bATTACKER_?IP\b"), "10.10.14.9"),
    (re.compile(r"\bINTERNET_?IP\b", re.I), "10.10.14.9"),
    (re.compile(r"\battacker\.com\b", re.I), "10.10.14.9"),
    (re.compile(r"<\s*(?:LPORT|RPORT|PORT|listen(?:ing)?[-_]?port|your[-_]?port|"
                r"target[-_]?port|port)\s*>", re.I), "4444"),
    (re.compile(r"\{\{?\s*(?:LPORT|PORT|RPORT)\s*\}?\}", re.I), "4444"),
    (re.compile(r"\$\{?(?:LPORT|PORT|RPORT)\}?"), "4444"),
    (re.compile(r"\[\s*PORT\s*\]", re.I), "4444"),
    (re.compile(r"\bATTACKER_?PORT\b"), "4444"),
    (re.compile(r"\bIP_ADDRESS\b"), "10.10.14.9"),
    (re.compile(r"\[[^\]]*(?:host|ip|target)[^\]]*\]", re.I), "10.10.14.9"),
    (re.compile(r"\[[^\]]*port[^\]]*\]", re.I), "4444"),
]
# after substitution, a line still holding one of these is not executable -> drop
PLACEHOLDER_LEFT = re.compile(r"<[A-Za-z][A-Za-z0-9 ._/-]*>|\{\{.*?\}\}|\[[A-Z][A-Z_]{2,}\]")

# Windows / PowerShell syntax -> not Linux, drop (OS-based, not malice-based)
WINDOWS = re.compile(
    r"powershell|Invoke-|\.exe\b|[A-Za-z]:\\\\|IEX\b|Import-Module|New-Object|"
    r"\bcmd\.exe|rundll32|certutil|\breg\s+add|\bDownloadString|\.dll\b|-nop\b", re.I)

# command output / prose / config that lives inside a bash fence but is not a command
OUTPUT = re.compile(
    r"^\s*(\||\d+/(tcp|udp)\b|PORT\s+STATE|Starting Nmap|Nmap (scan|done)|"
    r"Host is up|MAC Address|Not shown|Nmap scan report|\[[-+*!]\]|"
    r"In |After |Then |Note:|Now |On the |The |Victim|Listener|Output|Example|"
    r"User |permit |\(root\)|may run|Defaults|>>>|\$>|=>|-{3,})", re.I)

# multi-line block fragments / heredoc noise (structural, not vocabulary)
FRAGMENT = re.compile(
    r"^\s*(do|done|then|fi|else|elif\b.*|esac|;;|\}|\)|EOF|'EOF'|\"EOF\"|"
    r"done\s*;|fi\s*;|\{|\bBEGIN\b)\s*$")
COMPOUND_START = re.compile(r"^\s*(for|while|until|if|case)\b")
COMPOUND_END = re.compile(r"\b(done|fi|esac)\b")


def clean_block(lines):
    """Join backslash line-continuations, then yield candidate single lines."""
    joined, buf = [], ""
    for l in lines:
        if l.rstrip().endswith("\\"):
            buf += l.rstrip()[:-1] + " "
        else:
            joined.append(buf + l); buf = ""
    if buf:
        joined.append(buf)
    for l in joined:
        yield l


def process(all_blocks):
    kept, n_sub, n_drop_ph, n_drop_other = [], 0, 0, 0
    for (ff, lg, lines) in all_blocks:
        if lg != "bash":
            continue
        for raw in clean_block(lines):
            s = raw.strip()
            # strip a leading shell prompt "$ " (but not $(...), ${...}, $VAR)
            if re.match(r"^\$\s+\S", s):
                s = s[1:].lstrip()
            if not s or s.startswith("#"):
                continue
            if any(ord(c) > 126 for c in s):        # console art / box drawing
                n_drop_other += 1; continue
            if FRAGMENT.match(s):
                n_drop_other += 1; continue
            if s.split()[0].startswith("-"):        # option-only doc line
                n_drop_other += 1; continue
            if re.match(r"^[Cc]trl[+-]", s):        # keystroke instruction
                n_drop_other += 1; continue
            if " : " in s or re.match(r"^[A-Za-z][A-Za-z ]{2,}:$", s):
                n_drop_other += 1; continue
            if re.search(r"<<-?\s*['\"]?[A-Za-z_]", s):   # heredoc start -> multiline
                n_drop_other += 1; continue
            if COMPOUND_START.match(s) and not COMPOUND_END.search(s):
                n_drop_other += 1; continue
            if OUTPUT.match(s):
                n_drop_other += 1; continue
            if WINDOWS.search(s):
                n_drop_other += 1; continue
            before = s
            for rx, rep in SUBS:
                s = rx.sub(rep, s)
            if s != before:
                n_sub += 1
            if PLACEHOLDER_LEFT.search(s):
                n_drop_ph += 1; continue
            kept.append(s)
    return kept, n_sub, n_drop_ph, n_drop_other


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", nargs="?", default=None,
                    help="InternalAllTheThings checkout (contains docs/). "
                         "Omit to shallow-clone the repo to a tempdir.")
    ap.add_argument("--out", default=None,
                    help="output .cm path (default ../raw/extracted/"
                         "payloads_all_the_things.cm)")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    out = args.out or os.path.normpath(
        os.path.join(here, "..", "raw", "extracted", "payloads_all_the_things.cm"))

    tmp = None
    repo = args.repo
    if repo is None:
        tmp = tempfile.mkdtemp(prefix="iatt_")
        print(f"cloning {REPO_URL} -> {tmp}")
        subprocess.run(["git", "clone", "--depth", "1", REPO_URL, tmp], check=True)
        repo = tmp

    all_blocks = []
    for f in FILES:
        md = read_file(repo, f)
        for lang, lines in fences(md):
            all_blocks.append((f, lang, lines))

    kept, n_sub, n_drop_ph, n_drop_other = process(all_blocks)
    seen, uniq = set(), []
    for c in kept:
        if c not in seen:
            seen.add(c); uniq.append(c)

    print(f"STATS kept(raw)={len(kept)} unique={len(uniq)} substituted={n_sub} "
          f"dropped_placeholder={n_drop_ph} dropped_other={n_drop_other}")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(uniq) + "\n")
    print(f"wrote {out} ({len(uniq)} commands)")


if __name__ == "__main__":
    main()
