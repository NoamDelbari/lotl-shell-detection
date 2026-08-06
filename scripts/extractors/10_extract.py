# -*- coding: utf-8 -*-
"""Extract LINUX/UNIX shell commands from the HackTricks wiki.

Upstream : https://github.com/HackTricks-wiki/hacktricks  (book.hacktricks.wiki)
Licence  : CC BY-NC 4.0  (record this in DATA_CARD.md -- non-commercial)
Content  : mdbook markdown under <repo>/src/**.md . Commands live in fenced code
           blocks whose info string is a shell dialect (bash/sh/shell/...).

House style follows extractors/9_extract.py (GTFOBins) and 8_extract.py (ART):
resolve placeholders, join line continuations, merge heredocs, drop markdown
fences / prose / command output / shell fragments / unresolved templates,
collapse whitespace, dedupe exact strings, and print a STATS + DROPPED breakdown.

LINUX/UNIX ONLY.  Windows/PowerShell/cmd is dropped at three levels:
  1. a whole page whose path is a Windows page                     (page_windows)
  2. a code fence whose language is powershell/cmd/bat/...          (fence lang)
  3. an individual line written in Windows/PowerShell/cmd syntax    (win_syntax)
None of these three tests, nor any other filter here, ever inspects a string for
"looking malicious": a line is rejected only for not being a well-formed Linux
shell command or for the OS/field/file it came from.  The label of the resulting
rows is PROVENANCE ("published in an offensive-tradecraft catalogue"), never a
function of the command text.

Usage:
    python 10_extract.py <hacktricks_src_or_repo_or_tarball> [--out PATH]
    python 10_extract.py                # no arg: download master tarball to temp

  <arg> may be: the repo root (contains src/), the src/ dir itself, or a
  .tar.gz / .tgz tarball of either.  --out defaults to the vendored location
  ../raw/extracted/hacktricks.cm relative to this script.
"""
import os
import re
import sys
import glob
import json
import tarfile
import tempfile
import argparse
import collections
import urllib.request

TARBALL = "https://github.com/HackTricks-wiki/hacktricks/archive/refs/heads/master.tar.gz"

# ---------------------------------------------------------------------------
# fence languages
# ---------------------------------------------------------------------------
# kept: Linux/Unix shell dialects.  Everything else (python, c, powershell, ...)
# is skipped.  The windows dialects are listed only so they can be counted.
SHELL_LANGS = {"bash", "sh", "shell", "shell-session", "sh-session",
               "bash-session", "console", "zsh", "shellsession"}
WIN_LANGS = {"powershell", "posh", "ps", "ps1", "pwsh",
             "cmd", "bat", "batch", "dosbatch", "dos"}

# ---------------------------------------------------------------------------
# page-level Windows filter (field/path based, never content-malice based)
# ---------------------------------------------------------------------------
# This clone is Linux-centric; the guard exists so a Windows page anywhere in the
# tree is dropped whole.  Linux tooling that targets Active Directory
# (kinit/nxc/ldapsearch on a Linux box) is NOT a Windows page and is kept.
PAGE_WINDOWS = re.compile(
    r"(?:^|/)(windows-hardening|windows|active-directory-methodology/"
    r"|.*\bpowershell\b)", re.IGNORECASE)


def is_windows_page(rel_path: str) -> bool:
    p = rel_path.replace("\\", "/").lower()
    if "/windows-hardening/" in p or p.startswith("windows-hardening/"):
        return True
    if "/windows/" in p or p.startswith("windows/"):
        return True
    if os.path.basename(p).startswith("powershell"):
        return True
    return False


# ---------------------------------------------------------------------------
# page-level subtree allowlist (provenance, never content-malice based)
# ---------------------------------------------------------------------------
# Walking the whole book yielded 4,573 shapes, but auditing them showed most of
# the surplus was off-topic for T1059.004 rather than new tradecraft:
#
#   generic-methodologies-and-resources  1,130 new  forensics -- `disk.img: Linux
#                                                   rev 1.0 ext4 filesystem data`
#                                                   is *file(1) output*, not a
#                                                   command; also macOS codesign
#   macos-hardening                        608     not Linux
#   binary-exploitation                    310     gdb/pwntools exploit dev --
#                                                   `set $eip = 0x12345678` and
#                                                   `gdb.attach(p.pid, "c")` are
#                                                   not shell commands
#   generic-hacking (minus reverse-shells) ~360    brute-force/network tooling
#                                                   (medusa, legba, nmap NSE),
#                                                   plus mojibake in the source
#   AI / crypto / blockchain / hardware      91     off-topic
#
# Selecting by upstream PATH keeps this label-independent: a page is admitted or
# refused for where it lives in the book, never for how its commands look.  The
# same rule cut Atomic Red Team's cleanup_command/prereq_command fields.
# reverse-shells is admitted explicitly because it is the one part of
# generic-hacking that is squarely T1059.004, and it targets the project's
# measured weakest behaviour column (reverse/bind shell: 0.0% of real captured
# intrusions, and D1's share is otherwise almost entirely synthetic QuasarNix).
SUBTREES = ("linux-hardening/",)


def in_subtree(rel_path: str) -> bool:
    p = rel_path.replace("\\", "/").lstrip("./")
    return any(p.startswith(s) for s in SUBTREES)


def _wanted_member(m) -> bool:
    """Tar member filter: markdown pages inside SUBTREES, keyed off `.../src/`."""
    if not (m.isfile() and m.name.endswith(".md")):
        return False
    name = m.name.replace("\\", "/")
    i = name.find("/src/")
    return in_subtree(name[i + 5:] if i >= 0 else name)


# ---------------------------------------------------------------------------
# placeholder resolution
# ---------------------------------------------------------------------------
# <foo> angle placeholders -> a concrete value.  IPv4 / URL-host / numbers are
# canonicalised again by build_dataset.normalize(), so the exact value chosen
# here never changes a command's shape(); it only makes the line a well-formed
# command instead of a template.
ANGLE = {
    "ip": "10.10.14.14", "IP": "10.10.14.14", "target_ip": "10.10.14.14",
    "target-ip": "10.10.14.14", "attacker-ip": "10.10.14.14",
    "ATTACKER-IP": "10.10.14.14", "attacker_ip": "10.10.14.14",
    "rhost": "10.10.14.14", "RHOST": "10.10.14.14", "lhost": "10.10.14.14",
    "LHOST": "10.10.14.14", "host": "victim.local", "HOST": "victim.local",
    "hostname": "victim", "server": "victim.local",
    "port": "4444", "PORT": "4444", "ports": "4444", "rport": "4444",
    "RPORT": "4444", "lport": "4444", "LPORT": "4444",
    "pid": "1234", "PID": "1234", "pid-or-name": "1234",
    "pid-of-mysleep": "1234", "securityd PID": "1234", "ppid": "1000",
    "inode_number": "131074", "fd": "3", "FD": "3",
    "file": "/tmp/f", "FILE": "/tmp/f", "filename": "/tmp/f",
    "path": "/tmp/f", "PATH": "/tmp/f", "dir": "/tmp/d", "directory": "/tmp/d",
    "binary": "/bin/sh", "bin": "/bin/sh", "program": "/bin/sh",
    "cmd": "id", "command": "id", "COMMAND": "id", "shell_comand": "id",
    "script": "/tmp/s.sh", "payload": "/tmp/p",
    "user": "user", "username": "user", "USER": "user", "USERNAME": "user",
    "uid": "1000", "gid": "1000", "group": "users",
    "password": "Passw0rd", "Password": "Passw0rd", "PASSWORD": "Passw0rd",
    "pass": "Passw0rd", "domain": "example.com", "DOMAIN": "EXAMPLE.COM",
    "url": "http://example.com/", "URL": "http://example.com/",
    "iface": "eth0", "IFACE": "eth0", "interface": "eth0", "if": "eth0",
    "name": "name", "NAME": "name", "container": "web",
    "container-name": "web", "container_id": "1a2b3c4d5e6f",
    "image": "ubuntu:latest", "imagename": "ubuntu:latest",
    "namespace": "default", "ns": "default", "pod": "mypod", "pod-id": "mypod",
    "module_name": "mymod", "module": "mymod", "key": "AAAA", "KEY": "AAAA",
    "token": "TOKEN123", "API_TOKEN": "TOKEN123", "version": "1.0",
    "start": "0", "end": "1024", "START_HEAD": "0", "END_HEAD": "1024",
    "num": "1", "n": "1", "N": "1", "count": "1", "size": "1024",
    "volume": "myvol", "profile-name": "docker-default",
    "cert-name-keychain": "mycert", "id": "1234", "ID": "1234",
    "email": "a@example.com", "string": "str",
}
# ALLCAPS bareword placeholders used as fill-ins.
BAREWORD = {
    "ATTACKER_IP": "10.10.14.14", "ATTACKER": "10.10.14.14",
    "YOUR_IP": "10.10.14.14", "YOUR_PORT": "4444",
    "LHOST": "10.10.14.14", "LPORT": "4444",
    "RHOST": "10.10.14.14", "RPORT": "4444",
}

# a line still carrying any of these after substitution is a template -> drop.
LEFTOVER = [
    re.compile(r"(?<!<)<[A-Za-z][A-Za-z0-9_.\- /]{0,30}>"),  # <anything>
    re.compile(r"\{\{.*?\}\}"),                               # {{ include }}
    re.compile(r"#\{[^}]+\}"),                                # atomic-style #{x}
    re.compile(r"%[A-Za-z_][A-Za-z0-9_]*%"),                  # cmd %VAR%
    re.compile(r"\bATTACKER\b", re.IGNORECASE),
    re.compile(r"\bYOUR_[A-Z]+\b"),
    re.compile(r"\b[LR]HOST\b|\b[LR]PORT\b"),
]

# ---------------------------------------------------------------------------
# Windows / PowerShell / cmd SYNTAX inside a line (dialect filter, OS-based)
# ---------------------------------------------------------------------------
WIN_SYNTAX = [
    re.compile(r"\b(?:Get|Set|New|Remove|Add|Import|Export|Start|Stop|Out|"
               r"Select|Where|ForEach|Write|Read|Invoke|ConvertTo|ConvertFrom|"
               r"Enable|Disable|Test|Copy|Move|Rename|Clear|Format|Measure|"
               r"Register|Unregister|Restart|Resolve|Update|Install|Find|"
               r"Search)-[A-Z][A-Za-z]+"),          # PowerShell Verb-Noun
    re.compile(r"\$env:", re.IGNORECASE),           # $env:PATH
    re.compile(r"\[System\.|\[Net\.|\[Convert\]|::"),  # .NET / static calls
    re.compile(r"-ExecutionPolicy\b|-NoProfile\b|-EncodedCommand\b|-nop\b",
               re.IGNORECASE),
    re.compile(r"^\s*(?:reg(?:\.exe)?|schtasks|wmic|certutil|bcdedit|vssadmin|"
               r"bitsadmin|rundll32|regsvr32|mshta|cscript|wscript|icacls|"
               r"takeown|dism|sc)\b(?:\s+(?:add|query|delete|create|config|"
               r"/[a-z]|-[a-z]))", re.IGNORECASE),
    re.compile(r"^\s*net\s+(?:user|localgroup|group|view|use|share|accounts)\b",
               re.IGNORECASE),
    re.compile(r"\bpowershell(?:\.exe)?\b|\bcmd\.exe\b|\bpwsh\b",
               re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:\\[A-Za-z]"),  # C:\ windows path
    re.compile(r"%(?:SystemRoot|windir|APPDATA|TEMP|USERPROFILE|"
               r"ProgramFiles|COMSPEC|PATH)%", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# command output / prose that must not be injected as fake commands
# ---------------------------------------------------------------------------
OUTPUT = [
    re.compile(r"^total \d"),
    re.compile(r"^[-dlbcps][rwxsStT@.+-]{9}[.+@]?\s"),   # ls -l perm string
    re.compile(r"^[Uu]id=\d|^[Gg]id=\d|^groups="),
    re.compile(r"^[a-z_]+_u:[a-z_]+_r:"),                # SELinux context
    re.compile(r"^\(gdb\)|^\(lldb\)|^gef\xe2|^pwndbg>"), # debugger prompt echo
    re.compile(r"^\s*(?:0x[0-9a-fA-F]+\b.*){2,}"),       # hexdump / registers
    re.compile(r"^(?:permit|deny)\s+(?:nopass|persist|nolog)\b"),  # doas.conf
    re.compile(r"^auth\s+(?:optional|required|sufficient|include)\b"),  # pam
    re.compile(r"^\[[A-Za-z][A-Za-z ]*\]$"),             # [Service] ini header
    re.compile(r"^(?:ExecStart|ExecStop|ExecReload|ExecStartPre|WantedBy|After|"
               r"Before|Description|Type|Restart|RestartSec|Environment|"
               r"RequiredBy|Requires|Wants|GenericName|Comment|Terminal|"
               r"Categories|Icon|StartupNotify|User|Group|PIDFile)="),  # unit
    re.compile(r"^[A-Za-z][\w .+-]{0,40}\.\.\.$"),       # "Doing something..."
    re.compile(r"^\s*\d+\s+rows?\s+in\s+set"),           # mysql output
    re.compile(r"^\s*(?:PING|Reply from|64 bytes from)\b"),  # ping output
    re.compile(r"^\s*(?:total size is|sent \d+ bytes|received \d+ bytes)\b"),
]

# ---------------------------------------------------------------------------
# shell fragments (halves of a multi-line construct)
# ---------------------------------------------------------------------------
FRAG = {"do", "done", "fi", "then", "else", "esac", ";;", "}", "{", ")", "(",
        ";", "&", "fi;", "done;", "EOF", "EOL", "EOT", "do;", "else;",
        "then;", '"', "'", "[", "]", "],", "*/", "/*", "```", "~~~", "..."}
OPENERS = re.compile(r"^\s*(?:if|for|while|until|case|elif|function)\b")
CLOSERS = re.compile(r"(?:;\s*(?:done|fi|esac)\b|\bdone\s*$|\bfi\s*$"
                     r"|\besac\s*$|\bdo\s*$|\bthen\s*$|\{\s*$)")
NL_HINT = re.compile(r"^\s*(?:Note|NOTE|This |The |That |These |Those |If you|"
                     r"You |Please |Ensure |Make sure|Run the|See |For |When |"
                     r"We |Here |There |It |Then |Now |First|Next|Finally|"
                     r"Example|e\.g\.|i\.e\.|In )")
MDLINK = re.compile(r"^\s*[-*>]?\s*\[[^\]]+\]\([^)]*\)\s*$")   # [text](url)
MDTABLE = re.compile(r"^\s*\|.*\|\s*$")                        # | a | b |
CMDCHARS = re.compile(r"^[A-Za-z0-9_./$~\"'\[({@!*-]")
# a line that is ONE bare quoted literal is not a command: it is a shellcode
# byte string ("\xb8\x30...") or a stray value ("rprivate") copied out of a
# larger snippet.  Structural test, never inspects the content for malice.
BARE_QUOTED = re.compile(r"^\"[^\"]*\"$|^'[^']*'$")
BSLASH = chr(92)


# ---------------------------------------------------------------------------
# text primitives
# ---------------------------------------------------------------------------
def ws(s):
    return re.sub(r"\s+", " ", s).strip()


def strip_inline_comment(s):
    """Remove a trailing ' #...' comment that is not inside quotes and is
    preceded by whitespace (so ${#v}, ${v#p}, url#frag survive)."""
    q = None
    for i, ch in enumerate(s):
        if q:
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
        elif ch == "#" and i > 0 and s[i - 1] in " \t":
            return s[:i].rstrip()
    return s


def strip_prompt(s):
    """Strip a leading interactive prompt: '$ ', 'user@host:~$ ', '> '."""
    s = re.sub(r"^\s*[\w.\-]+@[\w.\-]+:\S*\s*[#$]\s+", "", s)
    s = re.sub(r"^\s*\$\s+", "", s)
    s = re.sub(r"^\s*>\s+", "", s)   # PS2 continuation prompt echo
    return s


def join_continuations(text):
    """Join lines ending in a single backslash into one logical line."""
    out, buf = [], ""
    for line in text.split("\n"):
        s = line.rstrip("\r")
        if buf:
            s = buf + " " + s.strip()
        st = s.rstrip()
        # a real continuation is an ODD number of trailing backslashes
        if st.endswith(BSLASH) and (len(st) - len(st.rstrip(BSLASH))) % 2 == 1:
            buf = st[:-1].rstrip()
            continue
        buf = ""
        out.append(s)
    if buf:
        out.append(buf)
    return out


HD = re.compile(r"<<-?\s*[\"']?([A-Za-z_][A-Za-z0-9_]*)[\"']?")


def merge_heredocs(lines):
    """Collapse `cmd <<EOF ... EOF` into a single line."""
    out, i = [], 0
    while i < len(lines):
        m = HD.search(lines[i])
        # only treat as a heredoc if the delimiter is not itself part of a
        # here-string (<<<) and looks like a word terminator
        if m and "<<<" not in lines[i]:
            term = m.group(1)
            buf = [lines[i]]
            i += 1
            closed = False
            while i < len(lines):
                if lines[i].strip() == term:
                    buf.append(lines[i])
                    i += 1
                    closed = True
                    break
                buf.append(lines[i])
                i += 1
            out.append(" ".join(x.strip() for x in buf) if closed
                       else " ".join(x.strip() for x in buf))
        else:
            out.append(lines[i])
            i += 1
    return out


def substitute(line):
    for k, v in ANGLE.items():
        line = line.replace("<" + k + ">", v)
    for k, v in BAREWORD.items():
        line = re.sub(r"\b" + re.escape(k) + r"\b", v, line)
    return line


def unterminated_quote(s):
    q = None
    for ch in s:
        if q:
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
    return q is not None


# ---------------------------------------------------------------------------
# fence parser
# ---------------------------------------------------------------------------
def iter_shell_blocks(text, stats):
    """Yield (lang, block_text) for each shell-family fenced code block.
    Counts non-shell and windows fences into stats."""
    lines = text.split("\n")
    i, n = 0, len(lines)
    while i < n:
        st = lines[i].strip()
        if st.startswith("```") or st.startswith("~~~"):
            fence = st[0]
            body = st.lstrip("`~").strip()
            lang = (body.split()[0].lower() if body else "")
            i += 1
            buf = []
            while i < n:
                s2 = lines[i].strip()
                if (s2.startswith(fence * 3)) and s2.lstrip(fence) == "":
                    break
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            if lang in SHELL_LANGS:
                stats["fence_shell"] += 1
                yield lang, "\n".join(buf)
            elif lang in WIN_LANGS:
                stats["fence_windows_dropped"] += 1
            elif lang == "":
                stats["fence_nolang_dropped"] += 1
            else:
                stats["fence_other_lang_dropped"][lang] += 1
        else:
            i += 1


# ---------------------------------------------------------------------------
# source resolution (dir / repo root / tarball / download)
# ---------------------------------------------------------------------------
def resolve_src(arg):
    """Return a path to the mdbook `src` directory to walk."""
    tmp = None
    if arg is None:
        tmp = tempfile.mkdtemp(prefix="hacktricks_")
        tgz = os.path.join(tmp, "hacktricks.tar.gz")
        print("downloading %s" % TARBALL, file=sys.stderr)
        urllib.request.urlretrieve(TARBALL, tgz)
        arg = tgz

    if os.path.isfile(arg) and (arg.endswith(".tar.gz") or arg.endswith(".tgz")
                                or arg.endswith(".tar")):
        if tmp is None:
            tmp = tempfile.mkdtemp(prefix="hacktricks_")
        with tarfile.open(arg) as tf:
            # Unpack only the markdown we are actually going to walk.  Two
            # Windows MAX_PATH landmines otherwise: the book ships images named
            # "image (107) (2) (2) ... (1).png", and macos-hardening nests
            # ~280 chars deep.  Both are outside SUBTREES, so filtering the
            # members is the same decision as filtering the pages -- by path.
            tf.extractall(tmp, members=[m for m in tf if _wanted_member(m)])
        arg = tmp

    if not os.path.isdir(arg):
        sys.exit("not a directory / tarball: %s" % arg)

    # accept: a repo root containing src/, an extracted tarball whose single
    # child is the repo root, or the src dir itself.  Prefer an actual src/ dir
    # so top-level repo docs (README.md, AGENTS.md) are not walked.
    cand = [os.path.join(arg, "src")]
    for child in sorted(glob.glob(os.path.join(arg, "*"))):
        cand.append(os.path.join(child, "src"))
    cand.append(arg)
    for c in cand:
        if os.path.isdir(c) and glob.glob(os.path.join(c, "**", "*.md"),
                                          recursive=True):
            return c
    sys.exit("could not locate a src/ directory with .md files under %s" % arg)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?", default=None,
                    help="repo root / src dir / tarball (default: download)")
    default_out = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "raw", "extracted", "hacktricks.cm"))
    ap.add_argument("--out", default=default_out, help="output .cm path")
    a = ap.parse_args()

    src = resolve_src(a.src)
    files = sorted(glob.glob(os.path.join(src, "**", "*.md"), recursive=True))
    print("src dir  : %s" % src, file=sys.stderr)
    print("md files : %d" % len(files), file=sys.stderr)
    print("subtrees : %s" % ", ".join(SUBTREES), file=sys.stderr)

    stats = collections.Counter()
    stats["fence_other_lang_dropped"] = collections.Counter()
    dropped = collections.Counter()
    per_dir = collections.Counter()
    kept = []
    seen = set()

    for fp in files:
        rel = os.path.relpath(fp, src).replace("\\", "/")
        stats["md_files_seen"] += 1
        if not in_subtree(rel):
            stats["pages_offtopic_dropped"] += 1
            continue
        if is_windows_page(rel):
            stats["pages_windows_dropped"] += 1
            continue
        stats["md_files_processed"] += 1
        top = rel.split("/")[0]
        try:
            text = open(fp, encoding="utf-8", errors="replace").read()
        except OSError:
            stats["unreadable"] += 1
            continue

        for lang, block in iter_shell_blocks(text, stats):
            lines = merge_heredocs(join_continuations(block))
            for raw in lines:
                stats["raw_block_lines"] += 1
                line = strip_prompt(raw.rstrip())
                if not line.strip():
                    dropped["blank"] += 1
                    continue
                ls = line.lstrip()
                # comment / shebang / heading
                if ls.startswith("#") and not ls.startswith("#{"):
                    dropped["comment"] += 1
                    continue
                line = strip_inline_comment(line)
                s = ws(line)
                if not s:
                    dropped["blank"] += 1
                    continue
                if s in FRAG:
                    dropped["fragment"] += 1
                    continue
                if BARE_QUOTED.match(s):
                    dropped["bare_quoted_literal"] += 1
                    continue
                if re.match(r"^(?:done|fi|esac|do|then|else|;;)\b", s):
                    dropped["fragment"] += 1
                    continue
                if MDLINK.match(s) or MDTABLE.match(s):
                    dropped["markdown"] += 1
                    continue
                if any(p.search(s) for p in OUTPUT):
                    dropped["output_or_prose"] += 1
                    continue
                if OPENERS.match(s) and not CLOSERS.search(s):
                    dropped["open_block"] += 1
                    continue
                if not CMDCHARS.match(s):
                    dropped["not_cmdlike"] += 1
                    continue
                if NL_HINT.match(s) and not re.search(r"[|;>/]", s):
                    dropped["natural_lang"] += 1
                    continue
                if any(p.search(s) for p in WIN_SYNTAX):
                    dropped["windows_syntax"] += 1
                    continue
                s = substitute(s)
                if any(p.search(s) for p in LEFTOVER):
                    dropped["unresolved_placeholder"] += 1
                    continue
                if unterminated_quote(s):
                    dropped["unterminated_quote"] += 1
                    continue
                if len(s) < 4:
                    dropped["too_short"] += 1
                    continue
                if s in seen:
                    dropped["exact_dupe"] += 1
                    continue
                seen.add(s)
                kept.append(s)
                per_dir[top] += 1

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + "\n")

    # ---- report ----------------------------------------------------------
    print("\n=== STATS ===")
    for k in ("md_files_seen", "pages_windows_dropped", "md_files_processed",
              "fence_shell", "fence_windows_dropped", "fence_nolang_dropped",
              "raw_block_lines"):
        print("  %-28s %d" % (k, stats[k]))
    other = stats["fence_other_lang_dropped"]
    print("  fence_other_lang_dropped     %d (%d langs)"
          % (sum(other.values()), len(other)))
    print("  distinct commands kept       %d" % len(kept))

    print("\n=== DROPPED ===")
    for k, v in dropped.most_common():
        print("  %-28s %d" % (k, v))

    print("\n=== KEPT PER TOP-LEVEL DIR ===")
    for k, v in per_dir.most_common():
        print("  %-40s %d" % (k, v))

    print("\n=== 12 SAMPLES ===")
    import random
    for s in random.Random(10).sample(kept, min(12, len(kept))):
        print("  %s" % s[:160])

    print("\nwrote %s (%d commands)" % (a.out, len(kept)))


if __name__ == "__main__":
    main()
