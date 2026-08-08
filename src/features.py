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
