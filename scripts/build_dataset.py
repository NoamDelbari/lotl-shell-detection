"""
build_dataset.py — Build TWO both-class Linux shell-command datasets for
malicious-vs-benign command classification (MITRE T1059.004, Living-off-the-Land).

Design (read before changing):
  No single public dataset has both malicious and benign Linux commands
  (benign telemetry is consistently private), so we assemble from public parts
  (standard practice: SLP 2021, Oliveira & Cafe 2024).

  We produce TWO complete datasets, each with attacks AND normal commands, and
  each split into train and test. The two datasets are PROVENANCE-MATCHED: within
  a dataset, the attack side and the normal side come from the same KIND of
  source, so a model cannot separate the classes on collection style alone.

    Dataset 1 — generated + curated, both sides:
        malicious = QuasarNix (synthetic reverse shells) + SLP + GTFOBins
                    + Atomic Red Team + HackTricks + InternalAllTheThings
                    (curated LotL / MITRE technique payloads)
        normal    = nl2bash + tldr-pages + bash-instruct + LinLM + bash_command_6k
    Dataset 2 — real-world, both sides:
        malicious = SSH honeypot (real Cowrie attacker commands)
        normal    = captured .bash_history + commandlinefu (real user commands)

  No command appears in more than one dataset or in more than one split.

THE LABEL RULE, in one sentence: a command is malicious because of WHERE IT CAME
FROM, never because of what it contains. Dataset 1 says "this string is published
as an attack payload"; Dataset 2 says "this string was typed by an attacker
during a real intrusion". An earlier build kept a honeypot command only if it
matched the keyword regex `RE_MAL_MARKERS`, which made the label a restatement of
that regex -- the regex then scored F1 0.9527 as a "classifier" on its own output.
That is gone. `RE_MAL_MARKERS` survives ONLY as a reported probe in
evaluate_baseline.py and must never gate a row again.

Two filters run over every source, and both are LABEL-INDEPENDENT by construction:
  * well_formed()  -- rejects strings that are not shell command lines at all
                      (terminal paint, JSON fragments, HTML, prompt echoes). No
                      rule may mention maliciousness or a command vocabulary.
  * cap_per_shape() -- at most MAX_PER_SHAPE rows per distinct command shape,
                      applied UNIFORMLY to every source (it used to be QuasarNix
                      only, which let the two generator-scale sources drown the
                      curated ones in near-copies).

Unit of analysis: a single Linux shell command line (string), label in {0,1}.

Outputs (paths relative to final_project/):
  dataset/dataset{1,2}_{train,test}.csv
                                    cols: id, command, label, source, split --
                                    the 80/20 group-aware split, one file per side
  docs/stats.json                   machine-readable counts
  docs/DATA_CARD.md                 provenance, processing, confound caveats, counts

Run:  python build_dataset.py   (from scripts/)
Re-runs reuse cached downloads in raw/. Delete raw/ to force re-download.
raw/extracted/*.cm are vendored extracts (see extractors/ and SOURCE_META).
"""

from __future__ import annotations
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests

# ----------------------------------------------------------------------------
# config
# ----------------------------------------------------------------------------
SEED = 42
HERE = Path(__file__).resolve().parent          # final_project/scripts/
PROJECT = HERE.parent                           # final_project/
RAW = HERE / "raw"
EXTRACTED = RAW / "extracted"
DATA = PROJECT / "dataset"                      # train/test splits
DOCS = PROJECT / "docs"                         # DATA_CARD.md, stats.json
RAW.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
DOCS.mkdir(exist_ok=True)

# Sampling policy. Two knobs, both applied UNIFORMLY to every source.
#
# MAX_PER_SHAPE caps how many rows may share one command shape. It used to be
# QuasarNix-only, which meant the two generator-scale sources (QuasarNix,
# honeypot) contributed tens of thousands of near-copies of a handful of
# templates while the curated sources contributed a few hundred distinct ones.
# Applied uniformly it is nearly free for the curated sources (72-98% of rows
# kept) and does all its work on the generators - which is exactly the imbalance
# it exists to remove.
#
# MAX_SOURCE_SHARE caps how much of a dataset's NORMAL class any one source may
# supply. The benign sampler used to allocate proportionally to pool size, so
# Dataset 2's normal side was ~88% one person's .bash_history. Measured: the cap
# binds on Dataset 2 (85.4% -> 70.0%) and is inert on Dataset 1 (largest source
# is tldr at ~40%). Same code path for both - no dataset-specific branch.
MAX_PER_SHAPE = 2
MAX_SOURCE_SHARE = 0.70
BENIGN_PER_ATTACK = 3    # normal:attack ratio (malicious is rare in real telemetry)
TRAIN_FRAC = 0.80
MAX_LEN = 4096
MIN_LEN = 2

# Declared ceilings on a single source's row count, applied after MAX_PER_SHAPE.
# This replaces the old standalone N_QUASARNIX = 20000. With the fixed shape()
# QuasarNix collapses to a few hundred rows, so the ceiling no longer binds; it
# is kept as a guard rail and the build prints whether it bound.
SOURCE_ROW_CEILING = {"quasarnix": 20000}

# Report-only. If one source supplies more than this share of a class that has
# two or more sources, the build warns. It never drops rows - concentration is a
# fact about what is publicly available, and hiding it by resampling would be
# worse than reporting it. See P5/P6 in KNOWN_ISSUES.md.
WARN_CLASS_SHARE = 0.50

# Cross-label SHAPE conflicts are dropped only when they exceed this share of a
# dataset's malicious pool. Exact-string conflicts are always dropped (that was
# already true); the shape-level branch is new, because after the shape() fix a
# malicious and a benign command can share a structure without being identical,
# and training on `wget R` as malicious while testing `wget R` as benign is not a
# task, it is a coin flip. Measured 2026-08-03 on the prototype: Dataset 2 17.00%,
# Dataset 1 7.44% - both above the threshold, so both fire.
SHAPE_CONFLICT_THRESHOLD = 0.05

# downloaded fresh each build (single-file sources)
SOURCES = {
    "nl2bash": "https://raw.githubusercontent.com/TellinaTool/nl2bash/master/data/bash/all.cm",
    "slp_malicious": "https://raw.githubusercontent.com/dtrizna/slp/master/data/malicious.cm",
    "quasarnix_train": "https://huggingface.co/datasets/dtrizna/QuasarNix/resolve/main/X_train_malicious_cmd_orig.json",
    "honeypot": "https://github.com/ML4Net/SSH-Shell-Attacks/raw/main/data/raw/ssh_attacks.parquet",
}

# vendored extracts: one command per line, produced by extractors/<n>_extract.py
# from the upstream artifact named below (tarballs / paged APIs are too heavy to
# refetch every build, so the extracted command list is committed instead).
SOURCE_META = {
    # name             (file,                          label, dataset, kind,        licence,     upstream)
    "tldr":            ("tldr_pages.cm",                0, 1, "curated",   "CC-BY-4.0",  "github.com/tldr-pages/tldr"),
    "bash_instruct":   ("frost2o24_bash_instruct.cm",   0, 1, "synthetic", "MIT",        "hf.co/datasets/Frost2o24/bash-instruct-55k"),
    "linlm":           ("missvector_linux_commands.cm", 0, 1, "synthetic", "Apache-2.0", "hf.co/datasets/missvector/linux-commands"),
    "bash6k":          ("emirkaan_bash6k.cm",           0, 1, "synthetic", "Apache-2.0", "hf.co/datasets/emirkaanozdemr/bash_command_data_6K"),
    "gtfobins":        ("gtfobins.cm",                  1, 1, "curated",   "GPL-3.0",    "github.com/GTFOBins/GTFOBins.github.io"),
    # Atomic Red Team is read at executor.command ONLY -- the string the test
    # actually runs against the target. It was deliberately NOT expanded to
    # cleanup_command / prereq_command / get_prereq_command: those fields are the
    # test HARNESS (setup/teardown), not the attack, so a row drawn from them
    # would carry a provenance label ("this is an attack payload") that the field
    # does not support. That is a provenance judgement, made to keep the label
    # independent of the command text -- the same rule that killed the old
    # keyword-regex build. See the sigma/elastic REJECT rulings (2026-08-04) for
    # the mirror-image failure (defender-authored detection strings).
    "atomic_red_team": ("atomic_red_team.cm",           1, 1, "curated",   "MIT",        "github.com/redcanaryco/atomic-red-team"),
    # HackTricks: mdbook markdown, shell-dialect code fences only, restricted by
    # the extractor to the `linux-hardening/` subtree (extractors/10_extract.py,
    # SUBTREES). That path-based allowlist keeps the label independent of the
    # command text and drops the off-topic surplus a whole-book walk pulled in
    # (macOS, binary-exploitation gdb, forensics file(1) output). reverse-shells
    # was also dropped: its dense one-liners trip Windows Defender's real-time
    # scanner and quarantine the .cm mid-build, and that behaviour column is
    # already carried by payloads + quasarnix + slp. Upstream is the `master`
    # tarball (unpinned) as of 2026-08-05.
    # NON-COMMERCIAL licence -- ship the build script + `source` column, not a
    # merged corpus (see the licence note in DATA_CARD.md).
    "hacktricks":      ("hacktricks.cm",                1, 1, "curated",   "CC-BY-NC-4.0", "github.com/HackTricks-wiki/hacktricks"),
    # "payloads": bash-fence one-liners from swisskyrepo/InternalAllTheThings
    # (commit 5ec9b6a), the live SUCCESSOR to PayloadsAllTheThings -- whose own
    # Linux pages are now redirect-only TOCs, so they were NOT scraped. Upstream
    # is recorded as IATT (the repo actually read), not PATT, even though the
    # vendored file keeps its historical name. Extractor extractors/11_extract.py.
    "payloads":        ("payloads_all_the_things.cm",   1, 1, "curated",   "MIT",        "github.com/swisskyrepo/InternalAllTheThings"),
    "bash_history":    ("spignelon_bash_history.cm",    0, 2, "real",      "MIT",        "hf.co/datasets/spignelon/bash_history"),
    "commandlinefu":   ("commandlinefu.cm",             0, 2, "real",      "site ToS",   "commandlinefu.com JSON API"),
}
# sources fetched above, placed by hand
PLACEMENT = {           # source -> (label, dataset, kind)
    "nl2bash":   (0, 1, "curated"),
    "quasarnix": (1, 1, "synthetic"),
    "slp":       (1, 1, "curated"),
    "honeypot":  (1, 2, "real"),
}

# Kept as a belt-and-braces guard. Nothing in this build draws from the global
# stream any more -- every sample goes through rng_for() -- but a stray
# random.shuffle() added later would otherwise be silently irreproducible.
random.seed(SEED)


def rng_for(*parts) -> random.Random:
    """A reproducible RNG scoped to one call site.

    The build used to draw from the single module-level `random` stream, so a
    source's sample depended on how many other draws had happened first: adding
    a source, or reordering the loaders, silently changed every later sample.
    Scoping by (SEED, call site) makes each sample independent of the rest of
    the build while keeping the whole thing reproducible from SEED alone.
    """
    return random.Random(f"{SEED}|" + "|".join(map(str, parts)))

# ----------------------------------------------------------------------------
# download (cached)
# ----------------------------------------------------------------------------
def fetch(name: str, url: str) -> Path:
    ext = Path(url).suffix or ".dat"
    dest = RAW / f"{name}{ext}"
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  cached  {dest.name} ({dest.stat().st_size:,} bytes)")
        return dest
    print(f"  GET     {url}")
    r = requests.get(url, timeout=300, allow_redirects=True)
    r.raise_for_status()
    dest.write_bytes(r.content)
    print(f"  saved   {dest.name} ({dest.stat().st_size:,} bytes)")
    return dest

# ----------------------------------------------------------------------------
# normalization
# ----------------------------------------------------------------------------
# Addresses are replaced so the model cannot memorise a specific attacker host,
# but the replacement is DERIVED FROM THE ORIGINAL rather than constant. An
# earlier version mapped every IPv4 to the literal "1.1.1.1"; because QuasarNix
# reverse shells all carry an address, that single token then appeared in 100.0%
# of malicious and ~1% of benign commands and was by itself a near-perfect
# classifier. Hashing keeps address VARIETY while still hiding the real value.
RE_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
RE_URLHOST = re.compile(r"((?:https?|ftp)://)([^/\s'\"]+)", re.IGNORECASE)
SMART = {"‘": "'", "’": "'", "“": '"', "”": '"',
         "´": "'", "′": "'"}
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

def _fake_ip(m: re.Match) -> str:
    h = hashlib.sha1(m.group(0).encode()).digest()
    return f"{h[0] % 223 + 1}.{h[1]}.{h[2]}.{h[3] % 254 + 1}"

def _fake_host(m: re.Match) -> str:
    h = hashlib.sha1(m.group(2).lower().encode()).hexdigest()[:8]
    return f"{m.group(1)}h{h}.example.net"

def normalize(cmd: str) -> str:
    for k, v in SMART.items():
        cmd = cmd.replace(k, v)
    cmd = CTRL.sub(" ", cmd)
    cmd = cmd.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    cmd = RE_URLHOST.sub(_fake_host, cmd)
    cmd = RE_IPV4.sub(_fake_ip, cmd)
    return re.sub(r"\s+", " ", cmd).strip()

def usable(cmd: str) -> bool:
    if not cmd or len(cmd) < MIN_LEN or len(cmd) > MAX_LEN:
        return False
    if cmd.lstrip().startswith("#"):
        return False
    return True

# ----------------------------------------------------------------------------
# command "shape" — structure with volatile values blanked
# ----------------------------------------------------------------------------
# Used for two things: (a) capping every source at MAX_PER_SHAPE rows per
# structure instead of keeping near-duplicates, (b) GROUP-AWARE splitting, so two
# commands with the same shape can never land on opposite sides of the train/test
# line and inflate the score.
#
# WHAT WAS WRONG BEFORE: the old shape() blanked a token only if the WHOLE token
# was randomish, so `/tmp/Muw3fuvA`, `$RANDOM_VAR`, `NAME=value` prefixes and
# `for i in ...` bind variables all survived verbatim. QuasarNix therefore
# collapsed to 1.01 rows per shape -- i.e. it did not collapse at all, and both
# the dedup and the anti-leakage split were silently no-ops on the one source
# that needed them. The rewrite below blanks random-looking alphanumeric RUNS
# inside a token (keeping the punctuation skeleton), normalises shell variable
# binding and expansion, protects the command word so `ls` never becomes `R`, and
# blanks arbitrary file names under scratch/home directories (RE_SCRATCH_NAME,
# below -- the character-level rules cannot see those).
# Measured pool rows per distinct shape: QuasarNix 1.01 -> 2,349.39,
# honeypot 1.00 -> 165.96.
#
# Everything here is a statement about characters and shell syntax. No rule sees
# the source, the label, or a vocabulary of "bad" commands.

# ---- volatile VALUES (RE_QUOTED / RE_HEX / RE_NUM unchanged from before) -----
RE_QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'")
# '/' deliberately NOT in the class: a 16+ run of base64 characters is a blob, a
# 16+ run of path characters is a path. With '/' included, `/usr/share/man/man1`
# was being blanked to `B`.
#
# A 16+ alphanumeric run is ALSO how a long program name looks. Blanking those
# merged genuinely different commands into one shape: tldr's
# `accessorysensormgrd`, `alwaysonexclavesd`, `filecoordinationd`,
# `idevicescreenshot`, `powerprofilesctl`, `systemsoundserverd`,
# `universalaccessd` and `virtualenvwrapper` all became the single shape `B`
# (9 rows in one group), linlm merged `4kvideodownloader` /`partitionmanager` /
# `simplescreenrecorder`, and bash_history merged 14 rows; MAX_PER_SHAPE then
# discarded all but two of each group. Real base64 of that length essentially
# always carries a digit or a case change, and a lowercase-only, digit-free run
# is a word, so _b64ish() requires one of the two before blanking. Measured
# impact of the old behaviour: ~26 rows; class prevalence was unaffected.
RE_B64 = re.compile(r"\b[A-Za-z0-9+]{16,}={0,2}\b")
RE_HEX = re.compile(r"\b[0-9a-fA-F]{8,}\b")
RE_NUM = re.compile(r"\b\d+\b")


def _b64ish(m: re.Match) -> str:
    t = m.group(0)
    has_digit = any(c.isdigit() for c in t)
    has_case_change = any(c.isupper() for c in t) and any(c.islower() for c in t)
    return "B" if (has_digit or has_case_change) else t


# ---- arbitrary names in scratch / home directories --------------------------
# A name directly below /tmp, /var/tmp, /dev/shm, /run/shm, /var/www, /root or a
# /home/<user> directory is, by filesystem convention, an arbitrary and ephemeral
# choice; it is not part of the command's structure. This rule is a statement
# about paths, it never sees the source or the label, and it runs on every
# source.
#
# WHY IT EXISTS: _randomish() is a character-level test, and QuasarNix's payload
# file names defeat every character-level test there is. It emits
# `/tmp/zanjaffk.v`, `/var/www/orverpzt.v`, `/home/user/aevpaoys.v` -- eight
# lowercase letters with an ordinary vowel ratio, so rules r1-r4 all decline --
# and ALSO one-letter names like `/tmp/f.v`, which are four characters shorter
# than any randomness test can use. The result was that one template family
# (`echo Q > DIR/NAME.v && ... && v run DIR/NAME.v && rm DIR/NAME.v`) split into
# 349 of QuasarNix's 448 shapes, MAX_PER_SHAPE never bound on it, and near-copies
# differing only in that name landed on opposite sides of the train/test split.
#
# MEASURED on the full pools (rows -> distinct shapes), before vs after:
#   quasarnix       239,638:    448 ->   102 shapes  (534.91 -> 2,349.39 rows/shape)
#   honeypot        407,442:  2,470 -> 2,455
#   over-collapse:  tldr 29,340 -> 29,340 (zero), bash_history 45,383 -> 45,324
#                   (-0.13%), nl2bash 9,568 -> 9,562, commandlinefu 6,708 ->
#                   6,706, atomic_red_team 719 -> 710; bash_instruct, bash6k,
#                   linlm, gtfobins and slp unchanged. The bash_history merges
#                   are groups like {`ls ~/Downloads`, `ls ~/bin`, `ls ~/intel`}
#                   -- one shape in substance as well as in form.
#
# MEASURED AND REJECTED: teaching _randomish() to recognise all-lowercase random
# words (vowel ratio <= 25%, or a 4-consonant / 3-vowel run, at length >= 7)
# collapses QuasarNix no further -- 102 shapes with or without it -- while
# merging a further 1.1% of bash_history and 1.5% of linlm shapes. It costs
# benign diversity and buys nothing, so it is not adopted; _randomish() stays
# blind to all-lowercase random words and that residual blindness is declared in
# DATA_CARD.md.
RE_SCRATCH_NAME = re.compile(
    r"(?:^|(?<=[^A-Za-z0-9_./~-]))"
    r"((?:~|/tmp|/var/tmp|/var/www|/dev/shm|/run/shm|/root"
    r"|/home/[A-Za-z0-9_.-]+)/)"
    r"[A-Za-z0-9_-]+")

# ---- shell structure --------------------------------------------------------
# Command-context separators. Splitting here gives (a) the boundaries inside
# which a leading `NAME=` really is an assignment and (b) the position of every
# command word. Bare `&` is NOT a separator: it would break `2>&1` and `<&5`.
RE_SEG = re.compile(r"(;;|;|&&|\|\||\||\n|`|\$\(|\)|\{|\})")

# Digit-leading names are accepted on purpose: QuasarNix emits `7mfr`, `3nu1_1`.
RE_ASSIGN_TOK = re.compile(r"^([A-Za-z0-9_]+)(\+?=)")
RE_BARE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
RE_BIND_FOR = re.compile(r"\bfor\s+(?![QBHNRV]\b)[A-Za-z0-9_]+\s+in\b")
RE_BIND_READ = re.compile(r"\b(read)((?:\s+-[A-Za-z0-9]+)*)\s+(?![QBHNRV]\b)[A-Za-z0-9_]+")
RE_EXP_BRACE = re.compile(r"\$\{([#!]?)[A-Za-z0-9_]+")
RE_EXP_PLAIN = re.compile(r"\$[A-Za-z0-9_]+")
RE_ALNUM_CHUNK = re.compile(r"[A-Za-z0-9]+")

# Builtins after which further `NAME=` tokens are still assignments.
KW_ASSIGN_CTX = frozenset({"export", "local", "declare", "readonly", "typeset", "env"})
# Builtins after which a BARE `NAME` operand is a variable name.
KW_BARE_VAR = frozenset({"export", "local", "declare", "readonly", "typeset", "unset"})
# Words that introduce another command, whose program name is protected too.
# `busybox` is intentionally absent: `/bin/busybox <RANDOM-APPLET>` must blank.
WRAPPERS = frozenset({
    "sudo", "doas", "env", "nohup", "time", "exec", "command", "builtin",
    "nice", "ionice", "setsid", "stdbuf", "timeout", "xargs", "watch",
    "strace", "ltrace", "then", "do", "else", "elif", "if", "while", "until",
    "!", "eval",
})
PLACEHOLDERS = frozenset("QBHNRV")

VOWELS = frozenset("aeiouyAEIOUY")   # 'y' counts: rsync, mysql, pypy, sync

_MIN_UPPER = 4       # r1
_MIN_NOVOWEL = 6     # r2  (6, not 4: keeps dpkg/chsh/nvcc/mysql/https/rsync)
_MIN_BLOB = 8        # r3  (8, not 6: keeps python3/base64/md5sum/ttyUSB0)
_MIN_CASEMIX = 6     # r4


def _class_transitions(chunk: str) -> int:
    """Number of lower/upper/digit class changes along the chunk."""
    t = "".join("D" if c.isdigit() else ("U" if c.isupper() else "L") for c in chunk)
    return sum(1 for a, b in zip(t, t[1:]) if a != b)


def _randomish(chunk: str) -> bool:
    """True if an alphanumeric chunk looks machine-generated rather than chosen.

    Purely a statement about the characters. It never sees the surrounding
    command, the source, or the label. The old version took a whole whitespace
    token and stripped `./_-` off it, so it could not see a random run embedded
    in a path; these four rules run on each alphanumeric run separately.
    """
    n = len(chunk)
    if n < _MIN_UPPER:
        return False
    has_alpha = any(c.isalpha() for c in chunk)
    has_digit = any(c.isdigit() for c in chunk)
    if chunk.isupper():                                             # r1
        return True                                                 # PIALH POST
    if n >= _MIN_NOVOWEL and has_alpha and not any(c in VOWELS for c in chunk):
        return True                                                 # r2
    if n >= _MIN_BLOB and has_alpha and has_digit:                  # r3
        return True                                                 # j6rslnsu
    if (n >= _MIN_CASEMIX and has_alpha and has_digit               # r4
            and any(c.isupper() for c in chunk)
            and any(c.islower() for c in chunk)
            and _class_transitions(chunk) >= 3):
        return True                                                 # Ab3cDe
    return False


def _blank_random(tok: str) -> str:
    """Blank random-looking alphanumeric runs, keeping the punctuation skeleton:
    `/tmp/Muw3fuvA` -> `/tmp/R`, not `R`."""
    return RE_ALNUM_CHUNK.sub(
        lambda m: "R" if _randomish(m.group(0)) else m.group(0), tok)


def _shape_segment(seg: str, _off: frozenset = frozenset()) -> str:
    """One command context: normalise leading assignments, locate and protect the
    command word(s), blank random-looking chunks everywhere else."""
    toks = seg.split()
    if not toks:
        return ""

    # -- phase 1: the leading assignment prefix -------------------------------
    last_kw, i = None, 0
    while i < len(toks) and "V" not in _off:
        t = toks[i]
        if t in KW_ASSIGN_CTX or t in KW_BARE_VAR:
            last_kw = t
            i += 1
            continue
        if last_kw is not None and t.startswith("-"):
            i += 1                                                  # declare -x FOO=1
            continue
        m = RE_ASSIGN_TOK.match(t)
        if m:
            if m.group(1) not in PLACEHOLDERS:
                toks[i] = "V" + m.group(2) + t[m.end():]
            i += 1
            continue
        if (last_kw in KW_BARE_VAR and RE_BARE_NAME.match(t)
                and t not in PLACEHOLDERS):
            toks[i] = "V"                                           # unset FOO
            i += 1
            continue
        break

    # -- phase 2: the command word, plus whatever a wrapper wraps -------------
    protected = set()
    while i < len(toks):
        protected.add(i)
        if toks[i].rsplit("/", 1)[-1] in WRAPPERS:
            i += 1
            while i < len(toks) and (toks[i].startswith("-") or toks[i].isdigit()):
                i += 1                                              # timeout 5 cmd
            continue
        break

    # -- phase 3: blank random-looking chunks in every unprotected token ------
    if "R" not in _off:
        for j, t in enumerate(toks):
            if j not in protected:
                toks[j] = _blank_random(t)
    return " ".join(toks)


def shape(cmd: str, _off: frozenset = frozenset()) -> str:
    """Reduce a command line to its structure. Label-independent by construction.

    `_off` is a TEST-ONLY hook naming rule families to disable
    ({"Q","B","H","N","S","V","R"}); production callers pass one argument.
    """
    s = cmd if "Q" in _off else RE_QUOTED.sub("Q", cmd)
    if "B" not in _off:
        s = RE_B64.sub(_b64ish, s)
    if "H" not in _off:
        s = RE_HEX.sub("H", s)
    if "S" not in _off:
        # blanks to "R", the placeholder _blank_random already uses, so no new
        # letter appears in a shape and the PLACEHOLDERS guards keep working
        s = RE_SCRATCH_NAME.sub(lambda m: m.group(1) + "R", s)
    if "V" not in _off:
        s = RE_BIND_FOR.sub("for V in", s)
        s = RE_BIND_READ.sub(lambda m: f"{m.group(1)}{m.group(2)} V", s)
        s = RE_EXP_BRACE.sub(lambda m: "${" + m.group(1) + "V", s)
        s = RE_EXP_PLAIN.sub("$V", s)
    parts = RE_SEG.split(s)
    s = "".join(p if k % 2 else _shape_segment(p, _off) for k, p in enumerate(parts))
    return s if "N" in _off else RE_NUM.sub("N", s)

# ----------------------------------------------------------------------------
# well-formedness — LABEL-INDEPENDENT
# ----------------------------------------------------------------------------
# Every rule answers exactly one question: "is this string a shell command line?"
# None of them may reference maliciousness, attack tooling, or a command-name
# vocabulary -- that is the circularity this build exists to remove. All rules are
# applied to ALL sources; per-rule, per-source removal counts go into stats.json.
#
# Rules that were considered and REJECTED, recorded so they are not re-proposed:
#   * a command-name allowlist (ls, cat, wget, ...) -- would remove attacker-
#     dropped binary names while leaving every benign row untouched, i.e. a
#     label-correlated filter in all but name;
#   * a minimum session-frequency threshold -- label-independent but it is a
#     popularity prior, not a "this is not a command" test, and it deletes rare
#     genuine attacks;
#   * a general "prose sentence" rule -- any formulation broad enough to catch
#     `Remote side unexpectedly closed network connection` also catches
#     `sudo apt update`.
RE_WF_CTRL   = re.compile(r"[\x1b\x07\x08]")
RE_WF_CARET  = re.compile(r"^\^[A-Z@\[\]\\^_]|\^[A-Z@\[\]\\^_]$")
RE_WF_SPCEQ  = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\[\]'\"]*\s+=\s")
RE_WF_JSON   = re.compile(r"^[\"'][^\"']*[\"']\s*:")
RE_WF_MARKUP = re.compile(
    r"^<!"                                          # <!DOCTYPE ...>, <!-- ... -->
    r"|^</?[A-Za-z][A-Za-z0-9]*\s*/?>"              # <hr>, </body>, <title>
    r"|^<[A-Za-z][A-Za-z0-9]*\s+[A-Za-z:_-]+\s*="   # <a href="...">
)
RE_WF_BLOCK  = re.compile(
    r"^(?:def|class|elif|else|try|except|finally|with|lambda|@\w+|pass|import|from)"
    r"\b[^;]*:$")
RE_WF_WORD   = re.compile(r"[A-Za-z0-9_]")
RE_WF_PROMPT = re.compile(r"^[A-Za-z][A-Za-z ]{2,}:$")

def _unterminated_quote(s: str) -> bool:
    """True if a ' or " opens and never closes -- i.e. s is a truncated fragment.
    Does not honour backslash escapes; a handful of heavily escaped commandlinefu
    recipes are lost to that (~0.8% of that source), which is documented."""
    quote = None
    for ch in s:
        if quote is not None:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
    return quote is not None

# name -> (normalized_cmd, raw_cmd) -> bool.  `raw` is the text BEFORE normalize(),
# which is the only place terminal control bytes still exist.
WF_RULES = {
    "W1_unterminated_quote": lambda c, raw: _unterminated_quote(c),
    "W2_terminal_control":   lambda c, raw: bool(RE_WF_CTRL.search(raw))
                                            or bool(RE_WF_CARET.search(c)),
    "W3_spaced_assignment":  lambda c, raw: bool(RE_WF_SPCEQ.match(c)),
    "W4_json_member":        lambda c, raw: bool(RE_WF_JSON.match(c)),
    "W5_markup_tag":         lambda c, raw: bool(RE_WF_MARKUP.match(c)),
    "W6_block_colon":        lambda c, raw: bool(RE_WF_BLOCK.match(c)),
    "W7_no_word_char":       lambda c, raw: not RE_WF_WORD.search(c),
    "W8_prompt_phrase":      lambda c, raw: bool(RE_WF_PROMPT.match(c)),
}

def well_formed(cmd: str, raw: str | None = None) -> list[str]:
    """Return the names of every well-formedness rule this string violates.
    Empty list == keep."""
    raw = cmd if raw is None else raw
    return [name for name, test in WF_RULES.items() if test(cmd, raw)]

def filter_well_formed(pairs) -> tuple[list[str], dict[str, int]]:
    """pairs: iterable of (normalized, raw). Returns (kept, per-rule drop counts).

    Run inside every loader, i.e. BEFORE the shape cap. Filtering first means a
    shape whose only sampled representatives happened to be junk keeps a valid
    representative instead of vanishing; it also guarantees the rules are applied
    identically to all twelve sources, which is the point.
    """
    kept, dropped = [], defaultdict(int)
    for cmd, raw in pairs:
        bad = well_formed(cmd, raw)
        if bad:
            for name in bad:
                dropped[name] += 1
        else:
            kept.append(cmd)
    return kept, dict(dropped)

# ----------------------------------------------------------------------------
# uniform per-shape sampling
# ----------------------------------------------------------------------------
def _deal_round_robin(buckets: dict, k: int | None, rng: random.Random,
                      n_max: int | None = None) -> list:
    """Deal at most `k` items per bucket, ROUND-ROBIN over buckets: every bucket
    gives up its 1st item before any bucket gives up its 2nd, and so on.

    Round-robin rather than "take k from each bucket in turn" is what makes the
    maximally-diverse claim true: truncate the result at ANY length and every
    bucket is still represented as evenly as the length allows. Truncating a
    per-bucket-blocks ordering would instead drop whole buckets off the end.

    `k=None` means "deal every item", which combined with `n_max` gives a
    diversity-ordered subsample rather than a cap.

    Mutates `buckets` (shuffles the lists in place).
    """
    keys = sorted(buckets, key=str)          # key=str: works for str shapes and
    rng.shuffle(keys)                        # for int DataFrame indices alike
    for key in keys:
        rng.shuffle(buckets[key])
    if k is None:
        k = max((len(v) for v in buckets.values()), default=0)
    out = []
    for rnd in range(k):
        for key in keys:
            bucket = buckets[key]
            if len(bucket) > rnd:
                out.append(bucket[rnd])
                if n_max is not None and len(out) >= n_max:
                    return out
    return out


def cap_per_shape(cmds: list[str], shape_fn, k: int, rng: random.Random,
                  n_max: int | None = None) -> tuple[list[str], int]:
    """Keep at most `k` commands per command shape, dealt round-robin.

    THIS IS THE ONLY PLACE MAX_PER_SHAPE IS APPLIED, and every source goes
    through it. It replaces the QuasarNix-only round-robin that used to live
    inside load_quasarnix() and the `by_shape.setdefault()` line inside
    load_honeypot() -- two different dedup policies, neither applied to the other
    ten sources, and the honeypot one keyed on quote-blanking alone rather than
    on shape().

    Returns (kept, n_distinct_shapes). One pass over shape_fn, which matters:
    the honeypot pool is ~408k atoms and QuasarNix ~250k strings.
    """
    buckets: dict[str, list[str]] = defaultdict(list)
    for c in cmds:
        buckets[shape_fn(c)].append(c)
    n_shapes = len(buckets)
    return _deal_round_robin(buckets, k, rng, n_max), n_shapes


def roundrobin_by_key(items: list, key_fn, k: int | None, rng: random.Random,
                      n_max: int | None = None) -> list:
    """cap_per_shape for arbitrary items (used on DataFrame indices in [4/6])."""
    buckets: dict = defaultdict(list)
    for it in items:
        buckets[key_fn(it)].append(it)
    return _deal_round_robin(buckets, k, rng, n_max)

# ----------------------------------------------------------------------------
# benign source allocation
# ----------------------------------------------------------------------------
def allocate_capped(want: int, avail: dict[str, int],
                    max_share: float) -> tuple[dict[str, int], bool]:
    """Split `want` picks across sources, proportional to availability, with no
    source exceeding `max_share` of the result.

    Any source whose proportional target exceeds its ceiling is pinned at the
    ceiling and the freed quota is re-apportioned proportionally among the rest,
    iterated to a fixed point. Only if every other source is exhausted does a
    source exceed the ceiling, and then `breached` is True.

    Integer rounding is largest-remainder, so the parts sum EXACTLY to
    min(want, sum(avail)). The previous code used per-source round() and then
    absorbed the +-3-row drift with `(chosen + rest)[:want]`, which charged all
    overshoot to whichever source happened to be last in dict order and drew all
    undershoot from the largest pool - i.e. it leaked back exactly the source
    concentration this cap exists to remove.

    Deterministic and independent of `avail`'s iteration order.
    """
    srcs = sorted(avail)
    want = max(0, min(want, sum(avail.values())))
    if want == 0:
        return {s: 0 for s in srcs}, False

    # max(1, ...): a ceiling of 0 is unsatisfiable by construction - you cannot
    # allocate a fraction of a row - so a tiny `want` would always "breach".
    ceiling = max(1, int(want * max_share))
    limit = {s: min(avail[s], ceiling) for s in srcs}
    take = _apportion(want, avail, limit, srcs)

    breached = False
    short = want - sum(take.values())
    if short > 0:                       # ceiling unreachable: others exhausted
        breached = True
        head = {s: avail[s] - take[s] for s in srcs}
        for s, n in _apportion(short, head, head, srcs).items():
            take[s] += n
    return take, breached


def _apportion(need: int, weight: dict[str, int], limit: dict[str, int],
               srcs: list[str]) -> dict[str, int]:
    """Largest-remainder apportionment of `need` over `srcs`, proportional to
    `weight`, respecting `limit`. Returns exactly min(need, sum(limit)) units."""
    take = {s: 0 for s in srcs}
    free = [s for s in srcs if limit[s] > 0]
    need = min(need, sum(limit.values()))
    while need > 0 and free:
        total = sum(weight[s] for s in free)
        if total <= 0:
            break
        over = [s for s in free if need * weight[s] / total > limit[s]]
        if over:                                     # pin and redistribute
            for s in over:
                take[s] = limit[s]
                need -= limit[s]
            free = [s for s in free if s not in over]
            continue
        quota, remainder = {}, []
        for s in free:
            exact = need * weight[s] / total
            quota[s] = int(exact)
            remainder.append((exact - quota[s], s))
        remainder.sort(key=lambda t: (-t[0], t[1]))  # deterministic tie-break
        for _, s in remainder[: need - sum(quota.values())]:
            quota[s] += 1
        for s in free:
            take[s] += quota[s]
        need = 0
    return take

# ----------------------------------------------------------------------------
# honeypot session handling — PROVENANCE LABELLING
# ----------------------------------------------------------------------------
# Cowrie records a whole session as one string. Split it into command atoms on
# `;`, `&&`, `||` and newline, but NOT when the separator is inside a quoted
# string -- the old regex splitter (RE_SEP, now deleted) cut `awk '{print $4;}'`
# in half and turned `echo "pa;ss" > /tmp/up.txt` into two fragments, inventing
# 466 spurious command shapes. Pipelines are deliberately kept intact:
# `cat x | grep y` is one command line for our purposes.
def atomize(session: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i, n = 0, len(session)
    while i < n:
        ch = session[i]
        if quote is not None:
            buf.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == ";" or ch == "\n":
            out.append("".join(buf))
            buf = []
            i += 1
            continue
        if session.startswith("&&", i) or session.startswith("||", i):
            out.append("".join(buf))
            buf = []
            i += 2
            continue
        buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [c.strip() for c in out if c and c.strip()]

# PROBE ONLY. This keyword regex used to SELECT which honeypot atoms became
# malicious rows, which made the Dataset 2 label a restatement of the regex: run
# back over its own output it scored recall 1.0000, F1 0.9527. It must never gate
# a row again, in any source, at any stage. It is kept solely so
# evaluate_baseline.py can report it as a permanent baseline probe -- if anyone
# ever reintroduces lexical selection, that probe's recall jumps back towards 1.0
# and the regression is visible in BASELINE.md.
RE_MAL_MARKERS = re.compile(
    r"(wget|curl|tftp|ftpget|\bscp\b)"
    r"|\|\s*(sh|bash)\b"
    r"|chmod\s+(\+?x|777|755)"
    r"|/dev/(tcp|udp)/"
    r"|\bnc\b[^|]*-e\b"
    r"|(bash|sh)\s+-i\b"
    r"|authorized_keys|echo\s+ssh-rsa"
    r"|\bcrontab\b|chpasswd"
    r"|history\s+-c|>\s*/var/log"
    r"|\brm\s+-rf\s+/",
    re.IGNORECASE,
)

# Benign label-noise scrub. Deliberately MUCH stricter than RE_MAL_MARKERS: a
# honeypot session is known-hostile so a bare `wget` there is attacker activity,
# but `wget https://…/file.tar.gz` in tldr is an ordinary command. Scrubbing every
# download from the benign side would teach the model "any download is malicious",
# which is the confound we are trying to avoid. Only unambiguous attack forms go.
# Left exactly as it was: it is a benign-side noise scrub, not a label rule, and
# changing it is a separate decision.
RE_BENIGN_SCRUB = re.compile(
    r"(wget|curl)[^|]*\|\s*(ba)?sh\b"          # download piped straight to a shell
    r"|/dev/(tcp|udp)/"                        # bash network redirect
    r"|\bnc\b[^|;]*\s-\w*e\w*\s"               # netcat with -e
    r"|(bash|sh)\s+-i\s*>&"                    # interactive reverse shell
    r"|>>?\s*[^\s;]*authorized_keys"           # key implant
    r"|\bchpasswd\b"                           # password reset
    r"|history\s+-c"                           # log wipe
    r"|\brm\s+-[rRf]{2,}\s+/(\s|$)",           # wipe root
    re.IGNORECASE,
)

# Every usable command atom of every Cowrie session is kept and labelled 1. The
# label means "this string was typed by an attacker during a real intrusion",
# which is the same KIND of rule Dataset 1 uses ("this string came from GTFOBins").
#
# It is NOT "this string is intrinsically dangerous": `uname -a` and `cd /tmp`
# inside an attack session are label 1 here. That is deliberate, and it costs
# label noise. HOW MUCH is measured by three routes computed in this file
# (label_noise_report()); they measure three different things and they do NOT
# agree, so all three are reported and the largest is the one to quote. An
# earlier version of this comment and of DATA_CARD asserted "~1%, measured two
# independent ways, both agree" -- nothing computed it, one of the two routes was
# never implemented, and the real figure is several times larger. See
# label_noise_report() below.
#
# WHAT WAS WRONG BEFORE: the previous implementation kept an atom only if it
# matched RE_MAL_MARKERS, and deduplicated on quote-blanking rather than shape().
# DO NOT REINTRODUCE EITHER.
#
# One non-lexical exclusion is applied: `Set_Fingerprint` is the upstream
# session-level tactic annotation, and 225 sessions are fingerprinted exactly
# ['Harmless']. A command seen ONLY in such sessions is dropped. That decision
# comes from someone else's session labels, never from the command text, so it
# does not reintroduce circularity.
def load_honeypot(path: Path) -> tuple[list[str], dict]:
    """Return (uncapped pool of normalized atoms, report).

    No shape dedup and no row cap happen here: MAX_PER_SHAPE is applied uniformly
    to every source in main() step [2b/6], with the real shape().
    """
    df = pd.read_parquet(path, columns=["full_session", "Set_Fingerprint"])

    # normalized command -> set of Set_Fingerprint tuples of the sessions it is in
    fingerprints: dict[str, set[tuple]] = defaultdict(set)
    # normalized command -> one pre-normalisation raw text (for rule W2)
    raw_text: dict[str, str] = {}

    for session, fp in zip(df["full_session"], df["Set_Fingerprint"]):
        if session is None or isinstance(session, float):
            continue
        try:
            key = tuple(fp)          # list or numpy array of tactic names
        except TypeError:
            key = ()                 # NaN / None -> unannotated session
        for raw in atomize(str(session)):
            cmd = normalize(raw)
            if not usable(cmd):
                continue
            fingerprints[cmd].add(key)
            raw_text.setdefault(cmd, raw)

    report = {"sessions": int(len(df)), "distinct_atoms": len(fingerprints)}

    pool, wf_dropped = filter_well_formed((c, raw_text[c]) for c in fingerprints)
    report["well_formed_dropped"] = wf_dropped
    report["after_well_formed"] = len(pool)

    harmless_only = {c for c in pool if fingerprints[c] == {("Harmless",)}}
    pool = [c for c in pool if c not in harmless_only]
    report["harmless_only_dropped"] = len(harmless_only)
    report["harmless_only_examples"] = sorted(harmless_only)[:20]
    report["after_harmless_drop"] = len(pool)

    # probe only -- never gates a row
    report["marker_probe_pool_coverage"] = sum(
        1 for c in pool if RE_MAL_MARKERS.search(c))
    return pool, report

# ----------------------------------------------------------------------------
# label-noise measurement -- REPORT ONLY. Nothing below gates, selects or drops
# a row; these functions exist so DATA_CARD can state a measured number instead
# of an asserted one.
# ----------------------------------------------------------------------------
# Route 3. A command that any analyst would call harmless if shown it on its own,
# with no session around it. This is a hand-written pattern and it is DELIBERATELY
# a lower bound: it matches only a whole command that is one bare read-only
# builtin with no pipeline, separator, redirect or substitution, so
# `uname -a & lscpu`, `cat /proc/cpuinfo | grep name | head -n 1` and
# `ls -l /bin/dhpcd` are all counted as NOT innocuous even though a human would
# say otherwise. It is scored against Dataset 2's malicious rows only, and it is
# reported next to the two upstream-annotation routes precisely because the three
# disagree.
_INNOC = (r"cd(?:\s+[^\s;|&<>$`()]+)?"
          r"|ls(?:\s+-[A-Za-z]+)*(?:\s+[^\s;|&<>$`()]+)?"
          r"|pwd|whoami|id|w|who|users|tty|date|uptime|hostname|logname"
          r"|exit|logout|clear|history|nproc|lscpu|lsblk|arch"
          r"|uname(?:\s+-[A-Za-z]+)*"
          r"|ps(?:\s+-?[A-Za-z]+)*"
          r"|(?:df|du|free|last|env|printenv|top)(?:\s+-[A-Za-z]+)*"
          r"|cat\s+/proc/(?:cpuinfo|meminfo|version|uptime|stat|loadavg)")
RE_INNOCUOUS_SOLO = re.compile(rf"^(?:{_INNOC})\s*$", re.IGNORECASE)


def logprecis_harmless_rate(path: Path) -> dict:
    """Route 2: the LogPrecis expert annotations.

    raw/logprecis.json is 359 Cowrie sessions annotated statement by statement by
    the LogPrecis authors, keyed by raw session text, value
    {"session": ..., "labels": "Discovery - 2 -- Persistence - 5"} where the
    number is a RUN LENGTH in statements. The share of statements annotated
    `Harmless` is the closest published estimate of "commands inside an attack
    session that are not themselves attack behaviour".

    Returns {} if the file is absent, so the build still runs without it.
    """
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    counts: dict[str, int] = defaultdict(int)
    for v in data.values():
        for part in str(v.get("labels", "")).split("--"):
            m = re.match(r"^\s*(.*?)\s*-\s*(\d+)\s*$", part)
            if m:
                counts[m.group(1)] += int(m.group(2))
    total = sum(counts.values())
    if not total:
        return {}
    return {"sessions": len(data), "statements": total,
            "by_tactic": {k: int(v) for k, v in
                          sorted(counts.items(), key=lambda kv: -kv[1])},
            "harmless": int(counts.get("Harmless", 0)),
            "harmless_share": round(counts.get("Harmless", 0) / total, 4)}


def innocuous_solo_rate(cmds: list[str]) -> dict:
    hits = [c for c in cmds if RE_INNOCUOUS_SOLO.match(c)]
    return {"n": len(cmds), "hits": len(hits),
            "share": round(len(hits) / len(cmds), 4) if cmds else 0.0,
            "examples": sorted(set(hits))[:20]}


# ----------------------------------------------------------------------------
# loaders
# ----------------------------------------------------------------------------
def load_lines(path: Path) -> tuple[list[str], dict[str, int]]:
    """One command per line. Returns (commands, per-rule well-formedness drops).
    The raw line is passed to well_formed() because rule W2 inspects bytes that
    normalize() has already stripped."""
    pairs, seen = [], set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        cmd = normalize(line)
        if usable(cmd) and cmd not in seen:
            seen.add(cmd)
            pairs.append((cmd, line))
    return filter_well_formed(pairs)


def load_quasarnix(path: Path) -> tuple[list[str], dict[str, int]]:
    """Plain loader. Sampling is NOT done here any more: MAX_PER_SHAPE is applied
    uniformly to every source in main() step [2b/6]."""
    arr = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    pairs, seen = [], set()
    for raw in arr:
        cmd = normalize(raw)
        if usable(cmd) and cmd not in seen:
            seen.add(cmd)
            pairs.append((cmd, raw))
    return filter_well_formed(pairs)

# ----------------------------------------------------------------------------
# assemble
# ----------------------------------------------------------------------------
def group_split(sub: pd.DataFrame, frac: float, tag: str) -> pd.Series:
    """80/20 by SHAPE GROUP within each label: whole groups go to one side, so an
    identical command structure never straddles train and test.

    `tag` scopes the RNG. This used to shuffle the global `random` stream, which
    meant the split depended on how many draws the samplers had made first.
    """
    split = pd.Series("train", index=sub.index, dtype=object)
    for lb in (0, 1):
        part = sub[sub["label"] == lb]
        groups = defaultdict(list)
        for i, sh in part["shape"].items():
            groups[sh].append(i)
        keys = sorted(groups)
        rng_for("split", tag, lb).shuffle(keys)
        # Greedy fit in random order, SKIPPING any group that would overshoot,
        # rather than stopping at the first overshoot. One honeypot template can
        # hold hundreds of commands; breaking on it pushed test to 37% of the
        # attack class. Skipping keeps the ratio while still moving whole groups.
        target_test = round(len(part) * (1 - frac))
        in_test, n_test = [], 0
        for k in keys:
            g = groups[k]
            if n_test + len(g) <= target_test:
                in_test.extend(g)
                n_test += len(g)
        split.loc[in_test] = "test"
    return split


def main():
    print("[1/6] downloading single-file sources (cached after first run)")
    paths = {name: fetch(name, url) for name, url in SOURCES.items()}

    print("[2/6] loading + normalizing (well-formedness filter runs on every source)")
    raw_pools: dict[str, list[str]] = {}
    wf_report: dict[str, dict] = {}
    raw_pools["nl2bash"], wf_report["nl2bash"] = load_lines(paths["nl2bash"])
    raw_pools["slp"], wf_report["slp"] = load_lines(paths["slp_malicious"])
    raw_pools["quasarnix"], wf_report["quasarnix"] = load_quasarnix(paths["quasarnix_train"])
    raw_pools["honeypot"], hp_rep = load_honeypot(paths["honeypot"])
    wf_report["honeypot"] = hp_rep["well_formed_dropped"]
    hp_sessions = hp_rep["sessions"]
    for name, (fn, *_rest) in SOURCE_META.items():
        p = EXTRACTED / fn
        if not p.exists():
            raise SystemExit(f"missing vendored extract: {p}  (see extractors/)")
        raw_pools[name], wf_report[name] = load_lines(p)

    meta = {k: (v[1], v[2], v[3]) for k, v in SOURCE_META.items()}
    meta.update(PLACEMENT)
    total_wf = sum(sum(v.values()) for v in wf_report.values())
    print(f"  well-formedness: {total_wf:,} rows rejected as 'not a shell command "
          f"line' across all sources (per-rule counts in stats.json)")
    print(f"  honeypot: {hp_rep['distinct_atoms']:,} distinct atoms from "
          f"{hp_sessions:,} real Cowrie sessions; "
          f"{hp_rep['harmless_only_dropped']:,} seen only in ['Harmless'] sessions -> dropped")

    print(f"[2b/6] uniform shape cap: <= {MAX_PER_SHAPE} rows per command shape, "
          f"every source")
    pools: dict[str, list[str]] = {}
    shape_cap: dict[str, dict] = {}
    for name in sorted(raw_pools):
        lb, ds, kind = meta[name]
        ceiling = SOURCE_ROW_CEILING.get(name)
        kept, n_shapes = cap_per_shape(raw_pools[name], shape, MAX_PER_SHAPE,
                                       rng_for("cap", name), ceiling)
        pools[name] = kept
        n_raw = len(raw_pools[name])
        shape_cap[name] = {
            "raw": n_raw, "shapes": n_shapes, "kept": len(kept),
            "raw_per_shape": round(n_raw / n_shapes, 2) if n_shapes else 0.0,
            "ceiling": ceiling, "ceiling_bound": bool(ceiling and len(kept) >= ceiling),
        }
        print(f"  {'MAL' if lb else 'ben'} d{ds} {kind:9s} {name:16s} "
              f"raw {n_raw:>7,} -> shapes {n_shapes:>6,} -> kept {len(kept):>6,} "
              f"({n_raw / max(n_shapes, 1):7.2f} raw/shape)"
              + ("  [CEILING BOUND]" if shape_cap[name]["ceiling_bound"] else ""))
    del raw_pools

    print("[3/6] removing cross-label conflicts and duplicates")
    # (a) exact-string conflicts. Computed ACROSS both datasets, as before: a
    #     string that is malicious in one dataset and benign in the other would
    #     otherwise survive in whichever source sorts first and be silently
    #     dropped from the other by the keep-first dedup, i.e. its label would be
    #     decided by alphabetical order.
    mal_all, ben_all = set(), set()
    for name, cmds in pools.items():
        (mal_all if meta[name][0] else ben_all).update(cmds)
    drop_exact = mal_all & ben_all

    # (b) shape-level conflicts, judged PER DATASET and applied only when they
    #     exceed SHAPE_CONFLICT_THRESHOLD of that dataset's malicious pool. Below
    #     the threshold they are noise; above it, the same structure is being
    #     taught with both labels and the split cannot separate them (shape groups
    #     are formed per label, so the two copies land on opposite sides).
    conflict_report, drop_shape = {}, set()
    for ds in (1, 2):
        mal = set().union(*[set(pools[n]) for n in pools
                            if meta[n][1] == ds and meta[n][0] == 1])
        ben = set().union(*[set(pools[n]) for n in pools
                            if meta[n][1] == ds and meta[n][0] == 0])
        exact = mal & ben
        mal_r, ben_r = mal - exact, ben - exact
        conf_shapes = {shape(c) for c in mal_r} & {shape(c) for c in ben_r}
        mal_hit = {c for c in mal_r if shape(c) in conf_shapes}
        ben_hit = {c for c in ben_r if shape(c) in conf_shapes}
        share = (len(exact) + len(mal_hit)) / max(len(mal), 1)
        fired = share > SHAPE_CONFLICT_THRESHOLD
        if fired:
            drop_shape |= mal_hit | ben_hit
        conflict_report[f"dataset{ds}"] = {
            "malicious_pool": len(mal), "exact": len(exact),
            "shape_conflict_shapes": len(conf_shapes),
            "shape_conflict_malicious_rows": len(exact) + len(mal_hit),
            "shape_conflict_share": round(share, 4),
            "threshold": SHAPE_CONFLICT_THRESHOLD,
            "shape_branch_fired": bool(fired),
        }
        print(f"  dataset{ds}: exact conflicts {len(exact):,}; "
              f"shape conflicts {len(conf_shapes):,} shapes / "
              f"{len(exact) + len(mal_hit):,} malicious rows ({100 * share:.2f}%) "
              f"-> shape drop {'FIRES' if fired else 'skipped'}")
    conflict = drop_exact | drop_shape
    print(f"  strings dropped from BOTH labels: {len(conflict):,} "
          f"({len(drop_exact):,} exact, {len(drop_shape - drop_exact):,} shape-level)")

    # A benign source that contains an actual attack pattern is label noise; drop
    # those rows rather than trusting the source's implicit "it's benign" claim.
    scrub = 0
    for name, cmds in pools.items():
        if meta[name][0] == 1:
            continue
        keep = [c for c in cmds if not RE_BENIGN_SCRUB.search(c)]
        scrub += len(cmds) - len(keep)
        pools[name] = keep
    print(f"  benign rows carrying an unambiguous attack pattern: {scrub:,} -> dropped")

    rows, seen = [], set()
    for name in sorted(pools):
        lb, ds, kind = meta[name]
        for c in pools[name]:
            if c in conflict or c in seen:
                continue
            seen.add(c)
            rows.append({"command": c, "label": lb, "source": name,
                         "dataset": ds, "kind": kind})
    df = pd.DataFrame(rows)
    df["shape"] = df["command"].map(shape)

    print("[4/6] balancing each dataset to the target normal:attack ratio")
    keep_idx: list = []
    allocation: dict[str, dict] = {}
    for ds in (1, 2):
        d = df[df["dataset"] == ds]
        att = d.index[d["label"] == 1].tolist()
        ben = d.index[d["label"] == 0].tolist()
        by_src: dict[str, list] = defaultdict(list)
        for i in ben:
            by_src[df.at[i, "source"]].append(i)

        want = min(len(ben), len(att) * BENIGN_PER_ATTACK)
        avail = {s: len(v) for s, v in by_src.items()}
        take, breached = allocate_capped(want, avail, MAX_SOURCE_SHARE)

        chosen: list = []
        for src in sorted(by_src):
            if take[src] == 0:
                continue
            # Subsample WITHIN the source round-robin over shapes too, so the
            # rows that survive are the structurally most diverse ones rather
            # than a uniform draw. Whole shape groups still move to train or test
            # together in [5/6], so this adds no leakage.
            chosen.extend(roundrobin_by_key(by_src[src],
                                            lambda i: df.at[i, "shape"],
                                            None, rng_for("ben", ds, src),
                                            take[src]))
        # The old code absorbed rounding drift with `(chosen + rest)[:want]`.
        # allocate_capped is exact, so this is now an invariant, not a repair.
        assert len(chosen) == want == len(set(chosen)), (len(chosen), want)

        keep_idx.extend(att + chosen)
        allocation[f"dataset{ds}"] = {
            "want": want, "available": avail, "allocated": dict(take),
            "shares": {s: round(n / want, 4) for s, n in take.items()} if want else {},
            "cap": MAX_SOURCE_SHARE, "cap_breached": breached,
        }
        print(f"  dataset{ds}: {len(att):,} attacks + {len(chosen):,} normal "
              f"(of {len(ben):,} available)")
        for src in sorted(take, key=lambda s: -take[s]):
            print(f"      {src:16s} {take[src]:>7,} / {avail[src]:>7,} available"
                  f"   {take[src] / max(want, 1):6.1%} of the normal class")
        if breached:
            print(f"      NOTE: {MAX_SOURCE_SHARE:.0%} share cap could not be met "
                  f"(other sources exhausted); largest source exceeds it.")
    df = df.loc[sorted(keep_idx)].reset_index(drop=True)

    # Report-only invariant: warn, never resample. Source concentration is a fact
    # about what is publicly available; hiding it by resampling would be worse
    # than reporting it.
    concentration: dict[str, dict] = {}
    for ds in (1, 2):
        for lb, cls in ((1, "malicious"), (0, "normal")):
            part = df[(df["dataset"] == ds) & (df["label"] == lb)]
            vc = part["source"].value_counts()
            concentration[f"dataset{ds}_{cls}"] = {
                "counts": {k: int(v) for k, v in vc.items()},
                "shares": {k: round(v / len(part), 4) for k, v in vc.items()},
            }
            if len(vc) >= 2 and vc.iloc[0] / len(part) > WARN_CLASS_SHARE:
                print(f"  WARNING: dataset{ds} {cls} class is "
                      f"{vc.iloc[0] / len(part):.1%} `{vc.index[0]}` "
                      f"(> {WARN_CLASS_SHARE:.0%}); report per-source metrics, "
                      f"never the aggregate alone")

    # Report-only measurements. None of these select, drop or relabel a row.
    # (a) label noise from provenance labelling, three routes that disagree.
    d2_mal = df.loc[(df["dataset"] == 2) & (df["label"] == 1), "command"].tolist()
    label_noise = {
        "route1_set_fingerprint": {
            "what": "honeypot atoms seen ONLY in sessions fingerprinted exactly "
                    "['Harmless'] by the upstream annotators, as a share of the "
                    "atoms that reached that filter",
            "hits": hp_rep["harmless_only_dropped"],
            "n": hp_rep["after_well_formed"],
            "share": round(hp_rep["harmless_only_dropped"]
                           / max(hp_rep["after_well_formed"], 1), 5),
        },
        "route2_logprecis": {
            "what": "statements annotated `Harmless` by the LogPrecis experts, as "
                    "a share of all annotated statements in their 359 sessions",
            **logprecis_harmless_rate(RAW / "logprecis.json"),
        },
        "route3_innocuous_in_isolation": {
            "what": "Dataset 2 malicious rows that are a single bare read-only "
                    "command (RE_INNOCUOUS_SOLO). A LOWER BOUND: any pipeline, "
                    "separator or redirect disqualifies a row.",
            **innocuous_solo_rate(d2_mal),
        },
    }
    print("  label noise from provenance labelling (report only, three routes):")
    for k in ("route1_set_fingerprint", "route2_logprecis",
              "route3_innocuous_in_isolation"):
        r = label_noise[k]
        sh = r.get("share", r.get("harmless_share"))
        if sh is not None:
            print(f"      {k:34s} {sh:.4%}")

    # (b) how often each source carries an IPv4 -- the residual address
    #     correlation named in DATA_CARD's limitations.
    ip_share = {}
    for ds in (1, 2):
        for src, g in df[df["dataset"] == ds].groupby("source"):
            ip_share[src] = {
                "dataset": ds,
                "label": int(g["label"].iloc[0]),
                "rows": int(len(g)),
                "with_ipv4": int(g["command"].str.contains(RE_IPV4).sum()),
                "share": round(float(g["command"].str.contains(RE_IPV4).mean()), 4),
            }

    print("[5/6] group-aware 80/20 train/test split (by command shape)")
    df["split"] = None
    for ds in (1, 2):
        sub = df[df["dataset"] == ds]
        df.loc[sub.index, "split"] = group_split(sub, TRAIN_FRAC, f"dataset{ds}")

    print("[6/6] writing outputs")
    cols = ["id", "command", "label", "source", "split"]
    stats = {"seed": SEED,
             "config": {"MAX_PER_SHAPE": MAX_PER_SHAPE,
                        "MAX_SOURCE_SHARE": MAX_SOURCE_SHARE,
                        "SOURCE_ROW_CEILING": SOURCE_ROW_CEILING,
                        "WARN_CLASS_SHARE": WARN_CLASS_SHARE,
                        "SHAPE_CONFLICT_THRESHOLD": SHAPE_CONFLICT_THRESHOLD,
                        "BENIGN_PER_ATTACK": BENIGN_PER_ATTACK,
                        "train_frac": TRAIN_FRAC},
             "honeypot_sessions": hp_sessions,
             "honeypot": hp_rep,
             "well_formed_dropped": wf_report,
             # per-source raw/shapes/kept, measured BEFORE the cap. The pool
             # rows-per-shape figure here is what evaluate_baseline.py asserts on
             # to prove shape() is still collapsing template-generated sources.
             "shape_cap": shape_cap,
             "conflicts": conflict_report,
             "benign_allocation": allocation,
             "source_concentration": concentration,
             "label_noise": label_noise,
             "ipv4_share_by_source": ip_share,
             "dropped": {"cross_label_conflicts": len(conflict),
                         "cross_label_exact": len(drop_exact),
                         "cross_label_shape": len(drop_shape - drop_exact),
                         "benign_attack_patterns": scrub,
                         "not_a_command_line": total_wf},
             "datasets": {}}

    # --- cross-dataset independence (asserted BEFORE anything is written) ----
    # The proposal claims zero command-string overlap between D1 and D2 -- the
    # build proves it here, so a violation fails the run instead of shipping.
    # Shape overlap is a different animal: generic one-liner structures
    # ('chmod +x Q', 'cat F') legitimately occur in both an attack catalogue
    # and real user history, so it is RECORDED as a stat, never asserted to
    # zero -- forcing shape disjointness would distort both datasets and
    # manufacture a provenance artifact where none exists.
    d1_rows = df[df["dataset"] == 1]
    d2_rows = df[df["dataset"] == 2]
    cmd_shared = set(d1_rows["command"]) & set(d2_rows["command"])
    assert not cmd_shared, \
        f"dataset1 and dataset2 share {len(cmd_shared)} command string(s)"
    shape_shared = set(d1_rows["shape"]) & set(d2_rows["shape"])
    # each shape must carry one label per dataset for first() to BE the label.
    # [3/6] guarantees that only when its conflict share exceeded
    # SHAPE_CONFLICT_THRESHOLD, so enforce the invariant here instead of
    # trusting it -- otherwise first() silently picks an order-dependent label
    # and shape_label_conflicts becomes ill-defined.
    for _name, _rows in (("dataset1", d1_rows), ("dataset2", d2_rows)):
        _multi = _rows.groupby("shape")["label"].nunique()
        assert (_multi <= 1).all(), (
            f"{_name}: {int((_multi > 1).sum())} shape(s) carry both labels "
            "within one dataset -- [3/6] shape-conflict drop did not fire")
    lab1 = d1_rows.groupby("shape")["label"].first()
    lab2 = d2_rows.groupby("shape")["label"].first()
    shape_label_conflicts = sum(
        1 for sh in shape_shared if int(lab1[sh]) != int(lab2[sh]))
    stats["cross_dataset"] = {
        "command_overlap": int(len(cmd_shared)),  # asserted 0 above
        "shape_overlap": int(len(shape_shared)),
        "shape_label_conflicts": int(shape_label_conflicts),
    }
    print(f"  cross-dataset independence: 0 shared commands (asserted); "
          f"{len(shape_shared)} shared shapes recorded "
          f"({shape_label_conflicts} with cross-dataset label disagreement)")

    for ds in (1, 2):
        sub = df[df["dataset"] == ds].sample(frac=1.0, random_state=SEED).reset_index(drop=True)
        sub["id"] = [f"d{ds}_{i:06d}" for i in range(len(sub))]
        out = sub[cols]
        for part in ("train", "test"):
            part_rows = out[out["split"] == part]
            part_rows.to_csv(DATA / f"dataset{ds}_{part}.csv", index=False, encoding="utf-8")
        stats["datasets"][f"dataset{ds}"] = {
            "sources": sorted(sub["source"].unique().tolist()),
            "total": int(len(out)),
            "train": int((out["split"] == "train").sum()),
            "test": int((out["split"] == "test").sum()),
            "attacks": int((out["label"] == 1).sum()),
            "normal": int((out["label"] == 0).sum()),
            "train_attacks": int(((out["split"] == "train") & (out["label"] == 1)).sum()),
            "train_normal": int(((out["split"] == "train") & (out["label"] == 0)).sum()),
            "test_attacks": int(((out["split"] == "test") & (out["label"] == 1)).sum()),
            "test_normal": int(((out["split"] == "test") & (out["label"] == 0)).sum()),
            "distinct_shapes": int(sub["shape"].nunique()),
            "by_source": {k: int(v) for k, v in sub["source"].value_counts().items()},
        }

    (DOCS / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    write_data_card(stats)
    print("\nDONE.")
    print(json.dumps(stats["datasets"], indent=2))


def write_data_card(s: dict):
    d1, d2 = s["datasets"]["dataset1"], s["datasets"]["dataset2"]
    cfg = s["config"]

    def srcrows(ds: int):
        out = []
        for name, (fn, lb, d, kind, lic, up) in SOURCE_META.items():
            if d == ds:
                out.append((name, lb, kind, lic, up))
        for name, (lb, d, kind) in PLACEMENT.items():
            if d == ds:
                lic = {"nl2bash": "GPL-3.0", "quasarnix": "Apache-2.0",
                       "slp": "MIT", "honeypot": "MIT"}[name]
                up = {"nl2bash": "github.com/TellinaTool/nl2bash",
                      "quasarnix": "hf.co/datasets/dtrizna/QuasarNix",
                      "slp": "github.com/dtrizna/slp",
                      "honeypot": "github.com/ML4Net/SSH-Shell-Attacks"}[name]
                out.append((name, lb, kind, lic, up))
        return "\n".join(
            f"| `{n}` | {'malicious' if lb else 'normal'} | {k} | {li} | {u} |"
            for n, lb, k, li, u in sorted(out, key=lambda r: (-r[1], r[0])))

    def caprows():
        meta = {k: (v[1], v[2]) for k, v in SOURCE_META.items()}
        meta.update({k: (v[0], v[1]) for k, v in PLACEMENT.items()})
        return "\n".join(
            f"| `{n}` | {meta[n][1]} | {'malicious' if meta[n][0] else 'normal'} | "
            f"{c['raw']:,} | {c['shapes']:,} | {c['raw_per_shape']:,} | {c['kept']:,} |"
            for n, c in sorted(s["shape_cap"].items(),
                               key=lambda kv: (-kv[1]["raw"], kv[0])))

    def wfrows():
        rules = list(WF_RULES)
        head = ("| source | " + " | ".join(r.split("_")[0] for r in rules)
                + " | total |\n|---|" + "---:|" * (len(rules) + 1))
        body = []
        for n, drops in sorted(s["well_formed_dropped"].items()):
            cells = " | ".join(f"{drops.get(r, 0):,}" for r in rules)
            body.append(f"| `{n}` | {cells} | {sum(drops.values()):,} |")
        return head + "\n" + "\n".join(body)

    def concrows():
        out = []
        for key in sorted(s["source_concentration"]):
            block = s["source_concentration"][key]
            ds, cls = key.rsplit("_", 1)
            parts = ", ".join(
                f"`{k}` {v:.1%}" for k, v in sorted(block["shares"].items(),
                                                    key=lambda kv: -kv[1]))
            out.append(f"| {ds} | {cls} | {parts} |")
        return "\n".join(out)

    hp = s["honeypot"]
    conf1, conf2 = s["conflicts"]["dataset1"], s["conflicts"]["dataset2"]
    alloc2 = s["benign_allocation"]["dataset2"]
    ln1 = s["label_noise"]["route1_set_fingerprint"]
    ln2 = s["label_noise"]["route2_logprecis"]
    ln3 = s["label_noise"]["route3_innocuous_in_isolation"]
    ipsh = s["ipv4_share_by_source"]

    def ip_sentence() -> str:
        """QuasarNix's residual lexical distinctness, in this build's numbers."""
        q = ipsh.get("quasarnix")
        if not q:
            return ""
        others = {k: v for k, v in ipsh.items()
                  if v["dataset"] == 1 and k != "quasarnix" and v["label"] == 0}
        if not others:
            return f"`quasarnix` {q['share']:.1%}"
        lo = min(v["share"] for v in others.values())
        hi = max(v["share"] for v in others.values())
        return (f"`quasarnix` {q['with_ipv4']:,}/{q['rows']:,} = {q['share']:.1%}, "
                f"against {lo:.2%}-{hi:.2%} for every benign Dataset 1 source")

    md = f"""# Data Card — two Linux shell command datasets (malicious vs benign)

**Task.** Binary classification of a single Linux shell command line as
malicious (1) or benign (0). MITRE ATT&CK T1059.004 (Unix Shell),
Living-off-the-Land. Built {pd.Timestamp.utcnow().date()} by `build_dataset.py` (seed={s['seed']}).

## Two datasets, each with attacks and normal commands
No single public dataset has both malicious and benign Linux commands, so we
assemble from public parts (standard practice: SLP 2021, Oliveira & Cafe 2024).
Both datasets are used for training and testing.

The two datasets are **built** provenance-matched: inside a dataset, the attack
side and the normal side are drawn from the same KIND of source (Dataset 1 =
generated and curated on both sides, Dataset 2 = real captured on both sides).
That is a statement about how the datasets were assembled, and it is intended to
stop a model from separating the classes on collection style instead of
maliciousness. **Whether it succeeds is a separate, measured question, and the
answer is currently no** — see "Measured outcomes" below and the P8
source-separability probe in `BASELINE.md`. Treat provenance matching as an
intention, not as a verified property of the finished data.

| | Dataset 1 (generated + curated) | Dataset 2 (real-world) |
|---|---|---|
| attack commands | QuasarNix, SLP, GTFOBins, Atomic Red Team, HackTricks, InternalAllTheThings | SSH honeypot (Cowrie) |
| normal commands | nl2bash, tldr-pages, bash-instruct, LinLM, bash_command_6k | captured `.bash_history`, commandlinefu |
| total | {d1['total']:,} | {d2['total']:,} |
| train / test | {d1['train']:,} / {d1['test']:,} | {d2['train']:,} / {d2['test']:,} |
| attacks / normal | {d1['attacks']:,} / {d1['normal']:,} | {d2['attacks']:,} / {d2['normal']:,} |
| distinct command shapes | {d1['distinct_shapes']:,} | {d2['distinct_shapes']:,} |

Class ratio is 1 attack : {cfg['BENIGN_PER_ATTACK']} normal in both datasets — malicious commands are rare
in real host telemetry, so a 50/50 split would overstate precision. Report
PR-AUC and TPR at a low fixed FPR, not accuracy.

## What the label MEANS
A command is malicious because of **where it came from**, never because of what
it contains.

- **Dataset 1, label 1** = the string is published as an attack payload
  (QuasarNix generator output, SLP, GTFOBins, Atomic Red Team, HackTricks,
  InternalAllTheThings). For the catalogue sources the payload is read from the
  field that carries the attack itself — GTFOBins/HackTricks/IATT code blocks,
  Atomic Red Team's `executor.command` — never from a test harness's
  setup/teardown field (`prereq_command`/`cleanup_command`), so the label stays a
  fact about provenance rather than a function of the text.
- **Dataset 2, label 1** = the string was typed by an attacker during a real
  Cowrie SSH intrusion. Every usable command atom of every attacker session
  carries label 1, including reconnaissance that looks innocuous in isolation
  (`uname -a`, `cd /tmp`). Session-level provenance is the whole rule.

This matters because an earlier build kept a honeypot command only if it matched
a hand-written keyword regex (`RE_MAL_MARKERS`: wget, curl, chmod +x, /dev/tcp,
…). The label was then a restatement of that regex, and run back over its own
output the regex scored **F1 0.9527 at p = 0.250, against a do-nothing floor of
0.400** — a number that measured nothing but its own definition. The keyword rule
no longer selects any row anywhere in the build. It survives only as a
permanently reported probe in `BASELINE.md`, so that if lexical selection is ever
reintroduced, that probe's recall jumps and the regression is visible.

**Known label noise from this rule — measured, and the three routes disagree.**
Provenance labelling means a command that is harmless read in isolation carries
label 1 if an attacker typed it. Three ways of sizing that cost are computed by
this build, and they do not agree; the largest is the one to quote.

| route | what it measures | result |
|---|---|---:|
| upstream `Set_Fingerprint` | honeypot atoms seen **only** in sessions the upstream annotators fingerprinted exactly `['Harmless']`, as a share of atoms reaching that filter | {ln1['hits']:,} / {ln1['n']:,} = **{ln1['share']:.3%}** |
| LogPrecis expert annotations | statements the LogPrecis authors annotated `Harmless`, over all {ln2.get('statements', 0):,} annotated statements in their {ln2.get('sessions', 0)} sessions | {ln2.get('harmless', 0):,} = **{ln2.get('harmless_share', 0):.2%}** |
| direct, on this dataset | Dataset 2 malicious rows that are a single bare read-only command (`cd X`, `ls`, `pwd`, `uname -a`, `cat /proc/cpuinfo`, …) | {ln3['hits']:,} / {ln3['n']:,} = **>= {ln3['share']:.2%}** |

The first two measure *someone else's session-level or statement-level
annotation*; only the third measures rows of this dataset. The third is a **lower
bound** by construction: it requires the whole command to be one bare read-only
command, so `uname -a & lscpu`, `cat /proc/cpuinfo | grep name | head -n 1` and
`ls -l /bin/dhpcd` are all counted as *not* innocuous. Sample of what it does
catch: {', '.join('`' + e + '`' for e in ln3['examples'][:8])}.

So the honest statement is **at least {ln3['share']:.1%} of Dataset 2's malicious rows are
innocuous read in isolation**, not the "~1%, measured two independent ways, both
agree" that earlier versions of this card asserted. That sentence was a hardcoded
literal: nothing computed it, `raw/logprecis.json` was never opened by any code,
and the two routes it named differ from each other by a factor of
{(ln2.get('harmless_share', 0) / max(ln1['share'], 1e-9)):.0f}.

Commands seen **only** in sessions fingerprinted exactly `['Harmless']` are
excluded ({hp['harmless_only_dropped']:,} of {hp['after_well_formed']:,}); that exclusion comes from someone else's
session labels, never from the command text.

## Files
- `dataset/dataset1_{{train,test}}.csv` and `dataset/dataset2_{{train,test}}.csv` — columns `id, command, label, source, split`; the 80/20 group-aware split, one file per side.
- `docs/stats.json` — machine-readable counts for everything below.
- `docs/baseline_metrics.json`, `docs/BASELINE.md` — baseline scores, ablations and regression probes (`scripts/evaluate_baseline.py`).
- `scripts/raw/extracted/*.cm` — vendored one-command-per-line extracts; `scripts/extractors/` holds the script that produced each.

## Sources, provenance, licence
### Dataset 1
| source | class | kind | licence | upstream |
|---|---|---|---|---|
{srcrows(1)}

### Dataset 2
| source | class | kind | licence | upstream |
|---|---|---|---|---|
{srcrows(2)}

Licences are mixed: one arm is copyleft (GPL-3.0: nl2bash, GTFOBins) and one is
non-commercial (CC-BY-NC-4.0: HackTricks). Ship the build script and the per-row
`source` column rather than redistributing a merged corpus file, and treat the
result as non-commercial while a CC-BY-NC arm is present.

## Processing
1. **Normalise** every command: IPv4 and URL host are replaced by a value
   *derived from a hash of the original*, smart quotes to ASCII, control bytes
   stripped, whitespace collapsed.
2. **Honeypot sessions** ({s['honeypot_sessions']:,} real Cowrie sessions) are split into command
   atoms on `;`, `&&`, `||` and newline — **quote-aware**, so `awk '{{print $4;}}'`
   is no longer cut in half. Pipelines are kept intact. Every usable atom is kept
   and labelled by provenance (see "What the label MEANS"); {hp['distinct_atoms']:,} distinct atoms
   result.
3. **Well-formedness filter, applied to every source.** Eight rules, each of
   which answers only "is this string a shell command line?" — unterminated
   quote, terminal control bytes / caret notation, spaced assignment
   (`args = options`), JSON member, markup tag, Python block line, no word
   character at all, bare prompt phrase (`Enter new UNIX password:`).
   **{s['dropped']['not_a_command_line']:,} rows** removed in total; per-rule, per-source counts are in the
   table below and in `stats.json > well_formed_dropped`. No rule may reference
   maliciousness or a command vocabulary — a filter that removes attacker-dropped
   binary names while leaving benign rows untouched would be the same
   circularity as the old keyword selection, so a command-name allowlist was
   considered and rejected.
4. **Uniform per-shape cap.** Every source is reduced to at most
   {cfg['MAX_PER_SHAPE']} commands per distinct command shape, dealt round-robin over shapes so
   every structure is represented before any structure repeats. This used to
   apply to QuasarNix alone (and the honeypot used a different, weaker dedup),
   which let the two generator-scale sources contribute tens of thousands of
   near-copies while the curated sources contributed a few hundred distinct ones.
   Per-source figures below and in `stats.json > shape_cap`.
5. **Label hygiene.** {s['dropped']['cross_label_exact']:,} distinct strings appeared verbatim in both a malicious
   and a benign source (`vim`, `curl`, `ping`, `apt-get update`, …) and were
   dropped from both. A further {s['dropped']['cross_label_shape']:,} distinct strings were dropped because their
   *shape* appeared under both labels. (Both figures count **strings**, not rows;
   the per-dataset `shape_conflict_malicious_rows` in `stats.json` count rows and
   will not reconcile with them.) Dataset 1 {conf1['shape_conflict_share']:.2%} of its malicious pool
   ({'fired' if conf1['shape_branch_fired'] else 'below threshold'}), Dataset 2 {conf2['shape_conflict_share']:.2%} ({'fired' if conf2['shape_branch_fired'] else 'below threshold'}); the branch fires above
   {cfg['SHAPE_CONFLICT_THRESHOLD']:.0%}. {s['dropped']['benign_attack_patterns']:,} further rows inside benign sources carried an
   unambiguous download-and-run attack pattern and were dropped as label noise.
6. **Dedup** by exact normalized string, keep-first, across everything.
7. **Per-source share cap on the normal class.** No single source may supply more
   than {cfg['MAX_SOURCE_SHARE']:.0%} of a dataset's normal commands; the remainder is re-apportioned
   across the other sources by largest-remainder apportionment, and the cap is
   exceeded only if every other source is exhausted (reported as `cap_breached`,
   currently `{alloc2['cap_breached']}` for Dataset 2). Within a source the draw is again
   round-robin over shapes, so the surviving rows are the structurally most
   diverse ones rather than a uniform sample.
8. **Split** each dataset 80/20 train/test, **grouped by command shape** so an
   identical structure never straddles the split.

### Per-source effect of the shape cap
| source | dataset | class | pool rows | distinct shapes | rows/shape | kept |
|---|---|---|---:|---:|---:|---:|
{caprows()}

### Per-source effect of the well-formedness filter
{wfrows()}

### Source concentration in the finished datasets
| dataset | class | shares |
|---|---|---|
{concrows()}

## Measured outcomes from `BASELINE.md`
<!-- BEGIN measured-outcomes -->
_Not yet measured for this build. Run `python evaluate_baseline.py`; it rewrites
this block in place with the current P8 separability verdicts, the style gap and
the cross-dataset transfer result. Until then this card states no score._
<!-- END measured-outcomes -->

## Known limitations / confound caveats (read before trusting a score)
The **counts** below come from this build's `stats.json`. Every **score**
mentioned is produced by `evaluate_baseline.py` into `docs/BASELINE.md` and
`docs/baseline_metrics.json`; read the current values there rather than trusting
a number copied into prose.

- **F1 has no absolute scale here.** At 1:{cfg['BENIGN_PER_ATTACK']} the prevalence is
  {d1['attacks'] / max(d1['total'], 1):.3f}/{d2['attacks'] / max(d2['total'], 1):.3f}, so a model that shouts MALICIOUS at everything already
  scores 2p/(1+p). Every row of every table in `BASELINE.md` therefore carries
  n, prevalence, that do-nothing floor, and F1 normalised by the remaining
  headroom. Never quote an F1 from this project without its floor.
- **Address shortcut (mitigated at the token level, still present as a
  correlation).** Every QuasarNix reverse shell carries a network address; benign
  commands rarely do. An earlier build mapped all IPv4 to the constant `1.1.1.1`,
  so that one token appeared in 100.0% of malicious and ~1% of benign commands
  and was by itself a near-perfect classifier. Addresses are now hashed per
  value, which removes the constant token — but "contains any IPv4" remains a
  meaningful single-feature rule on Dataset 1. `BASELINE.md` reports it as a
  probe and repeats every score with all addresses stripped from both classes.
- **Length shortcut.** Malicious commands in Dataset 1 are far longer than benign
  ones, so command length alone is a usable feature. The length ablation pairs
  each attack with an *unused* benign command of the same length (within
  max(5 chars, 10%)) and **drops attacks it cannot pair**, making the subset
  exactly 1:1. An earlier version kept the unmatched attacks, which produced a
  "length-matched" Dataset 1 subset that was 83% malicious — its F1 was being
  read against a 0.908 floor while presented next to 0.400-floor numbers.
  `BASELINE.md` now reports the **coverage** of the match; where coverage is low
  the ablation speaks only for the short end of the malicious class.
- **Source concentration.** See the table above. Where one source supplies more
  than {cfg['WARN_CLASS_SHARE']:.0%} of a class the build prints a warning; the rows are kept
  (concentration is a fact about what is publicly available) but per-source
  recall must be reported, never the aggregate alone. `BASELINE.md` gives
  per-source rates as k/n with Wilson 95% intervals and flags every pair of
  sources whose intervals overlap, because "source A scores better than source B"
  is usually not supported at these sample sizes.
- **Cross-dataset transfer is poor, and that is the interesting result.** A
  detector trained on synthetic reverse shells does not recognise real honeypot
  activity, and vice versa. The two directions are **not** symmetric and must be
  quoted separately with their headroom fractions — see "Measured outcomes"
  above, which carries the current numbers. This is the finding the two-dataset
  design exists to produce; do not treat it as a bug to be tuned away.
- **Collection-style separability — measured, and it FAILED.** `BASELINE.md`'s P8
  probe asks a classifier which *pile* a command came from, ignoring the
  malicious/benign label. The current verdicts are in "Measured outcomes" above.
  Because the probe fails, the consequences it names are live, not hypothetical:
  the headline F1 is partly corpus identification and **must** be presented as an
  upper bound, it may not be quoted without the transfer result beside it, and
  the ablations are load-bearing rather than confirmatory.
- **QuasarNix is still lexically distinct from every benign Dataset 1 source.**
  The shape fix removed QuasarNix's numerical dominance and its near-copy
  leakage; it did not remove the fact that every generated reverse shell carries
  a network address while ordinary commands do not. In this build: {ip_sentence()}.
  A per-source recall of 1.000 on `quasarnix` in `BASELINE.md` is therefore not
  evidence of detection capability — see the pairwise macro-F1 rows for that
  source in P8 (b).
- **Residual junk in the malicious pool.** Roughly 3-5% of Dataset 2's malicious
  rows are still not command lines: single-token password guesses typed at a
  login prompt (`admi`, `adminpasswd`, `!@#$1234`), terminal residue that is not
  at a string boundary, and loop-body fragments (`do echo $i`, `done < .s`).
  Removing them would require exactly the command-vocabulary judgement rejected
  in processing step 3, so they stay and are declared here instead.
- **Accepted well-formedness false positives.** W8 (prompt phrase) removes
  tldr's `incus image list images:` and `... local:` — an `incus` remote name
  legitimately ends in `:`. W1's quote scanner does not honour backslash escapes,
  so a few heavily escaped commandlinefu recipes are lost (~0.8% of that source).
- **Placeholder style.** GTFOBins and tldr both use `path/to/…` placeholders on
  opposite labels, so the placeholder itself carries a little label signal in
  Dataset 1.
- **Synthetic share, and which dataset to trust.** Dataset 1's normal side is
  partly LLM/template-generated (bash-instruct, LinLM, bash_command_6k);
  Dataset 2's is fully organic on both sides. That is one point in Dataset 2's
  favour, and it does **not** settle the question: Dataset 2 is also the dataset
  whose P8 source-separability probe scores worse and whose style gap is smaller,
  i.e. less of its headline score is attributable to maliciousness rather than to
  collection style (see "Measured outcomes" above), and its labels carry the
  provenance noise measured in "What the label MEANS". Neither dataset dominates
  the other; quote both. (On size: Dataset 1 has {d1['total']:,} rows and Dataset 2
  has {d2['total']:,}, so **{'Dataset 1' if d1['total'] > d2['total'] else 'Dataset 2'}
  is the larger of the two**. That comparison is computed from this build rather
  than asserted: the sentence used to hardcode the opposite conclusion and stayed
  in the card unchanged after the row counts moved, so it stated the reverse of
  the two numbers printed immediately before it.)
- **`shape()` is lossy and is not a security control.** It blanks quoted strings,
  base64/hex blobs, numbers, variable names, random-looking alphanumeric runs and
  the arbitrary file name directly below a scratch or home directory (`/tmp/…`,
  `/var/tmp/…`, `/var/www/…`, `/dev/shm/…`, `/root/…`, `/home/<user>/…`, `~/…`),
  and it collapses whitespace. Two genuinely different commands can share a
  shape; that costs recall in the split, never correctness of a label. Measured
  over-collapse of the scratch-name rule on the benign pools: tldr 0 shapes,
  bash_history -0.13%, nl2bash -0.06%, commandlinefu -0.03%.
- **`shape()`'s randomness test is blind to all-lowercase random words.**
  `_randomish()` is character-level: it catches `PIALH`, `j6rslnsu`, `Ab3cDe`,
  but not `zanjaffk` or `orverpzt`, which have the length and vowel ratio of
  ordinary words. Adding a rule for those was measured and rejected — it
  collapsed nothing further (the scratch-name rule already covers the case that
  mattered) and merged another 1.1% of `bash_history` and 1.5% of `linlm` shapes.
  If a future source puts random lowercase words somewhere other than a scratch
  path, this blindness will let near-copies through, and the near-duplicate
  metric in `BASELINE.md`'s P2/P7 section is what will show it.
- **Shape groups are formed per label,** so a shape appearing on both labels can
  be train-side for one and test-side for the other. This works against the
  model, not for it: it sees a structure labelled benign in training and must
  call it malicious at test. `BASELINE.md` counts these.
"""
    (DOCS / "DATA_CARD.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        raise
